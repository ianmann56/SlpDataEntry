# Research: Students

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-09-30

Technical Context had no open unknowns. The stack is fixed by the constitution (Python
3.12, Tkinter, `sv-ttk`, `darkdetect`, local JSON files). The items below are the design
decisions the spec and the planning request left open, resolved against the existing code.

## R1. Where the student code lives

- **Decision**: A new top-level package, `therepy_sessions/students/`, holds everything
  about students: the `Student` record and its rules, the store interface and its
  JSON implementation, and the Students window and its editor dialog. The Setup menu
  goes in `app_shell/`, beside the home screen, because it is navigation only.
- **Rationale**: This was asked for directly. Students are setup data, not a pipeline
  stage, so they don't belong in `collection/`, `interpretation/`, or `storage/`. One
  package keeps the record, its storage, and its UI together, so later student settings
  are added in one place.
- **Alternatives considered**:
  - *`interpretation/students/`*. Rejected: students aren't part of turning an Import
    into a StudentDataSheet, and it would put a file-writing store inside the layer
    that layers.md rule 3 keeps pure.
  - *Put `SetupWindow` in `students/`*. Rejected: the Setup menu also opens template
    management, so it is navigation, which is what `app_shell/` is for.
- **Constitution impact**: `layers.md` gains a `students/` entry and an import rule.
  `dependency-injection.md` rule 6 extends to the student store. Both are MINOR
  amendments (1.2.0 → 1.3.0), made in the same change.

## R2. Student store interface, injected (repository pattern)

- **Decision**: `students/student_store.py` defines `StudentStore`, an abstract
  base class (`abc.ABC`) with the operations the UI needs: list, get by key, add, update
  (by the original key), delete, and recover from an unreadable file. A concrete
  `JsonStudentStore` in `students/json_student_store.py` stores records in the
  file given at launch. `program.py` builds exactly one `JsonStudentStore` and passes
  it, typed as `StudentStore`, into `StudentsWindow`. `StudentsWindow` passes the
  same instance to `StudentEditorWindow`. No window constructs a store or knows
  about files.
- **Rationale**: This was asked for directly ("use a repository … dependency injected"). It is the repository pattern, named *Store* to match `TemplateStore` and the glossary.
  It matches dependency-injection.md rule 6 for `TemplateStore`, and goes one step
  further: the windows depend on an interface rather than a concrete class, so an
  in-memory fake can stand in for checks and later features can swap the storage.
  An ABC (rather than `typing.Protocol`) matches the existing pattern in
  `interpreter_configs.py` and makes a missing method fail when the subclass is
  created.
- **Alternatives considered**:
  - *A concrete `StudentStore` like `TemplateStore`*. Rejected: it doesn't decouple the
    data access, which was the stated goal.
  - *`typing.Protocol`*. Workable, but nothing else in the codebase uses it, and an ABC
    gives an earlier error.

## R3. Where the student rules live

- **Decision**: The rules from the spec are plain functions and exceptions in
  `students/student.py`. They have no Tkinter and no file access:
  - `normalize_student_key(raw: str) -> str` trims spaces (FR-006).
  - `validate_student_key(raw: str) -> str` returns the trimmed key, or raises
    `StudentKeyError` if the key is empty or over 5 characters (FR-006).
  - `student_keys_match(a: str, b: str) -> bool` compares trimmed keys without regard
    to letter case (FR-006; edge case "changes only letter case").

  The store enforces uniqueness. It raises `DuplicateStudentKeyError` on `add` or
  `update` when another student already has the key. The windows only call these
  functions and show the messages.
- **Rationale**: layers.md rule 5 says business rules MUST NOT live in widget callbacks.
  The key is the record's identity, so uniqueness belongs with storage. Keeping the rules
  pure means they can be checked from a Python prompt with no display.
- **Alternatives considered**: *A separate `StudentService`*. Rejected for now: with
  three rules it adds a layer of indirection for no gain. It can be extracted when more
  configuration brings more rules.

## R4. Record file format and forward compatibility

- **Decision**: The student records file is UTF-8 JSON with `indent=2` (Technology
  Constraints), shaped `{"format_version": 1, "students": [ {...}, ... ]}`. Each student
  is an object whose keys are the `Student` dataclass field names. Loading builds a
  `Student` from the known keys and gives any missing key its dataclass default
  (FR-010). Unknown keys are ignored and dropped on the next save. A file with a
  `format_version` above 1 is treated as unreadable (FR-020's backup and fresh-start
  path), so this version never overwrites a newer file's data. Writes go to a temporary
  file in the same folder, which then replaces the real file with `os.replace`, so a
  crash mid-save can't leave a half-written file.
- **Rationale**: A top-level object with a version gives later features a clean place to
  migrate the format if a change ever can't be expressed as "new field with a default".
  The atomic replace protects the data the spec is most worried about (FR-020).
- **Alternatives considered**:
  - *A bare JSON list, like `templates.json`*. Rejected: it has no place for a format
    version.
  - *Keep unknown keys and write them back*. Rejected during analysis: it needs an
    untyped catch-all field on `Student`. Only one version of the app is in use, so there
    is no newer version whose fields could be lost.

## R5. A file that can't be read (FR-020)

- **Decision**: `JsonStudentStore` raises `UnreadableStudentRecordsError` from
  `list_students()` when the file exists but is not valid JSON or is not in the expected
  shape. A missing file is not an error. It reads as an empty list, and the file is
  created on the first save (spec edge case). `recover_unreadable_records() -> str`
  renames the damaged file to `<name>.unreadable-<YYYYmmdd-HHMMSS>.json` beside it, adding
  `-1`, `-2`, … if that name is taken. It returns the backup path, and the store
  then behaves as empty.

  `program.py`'s "open Students" handler does the check. It calls `list_students()`
  before opening the window. On `UnreadableStudentRecordsError` it calls
  `students_window.ask_to_start_fresh(parent, error)`, a small helper beside the window
  that shows the yes/no prompt. If the SLP declines, the Setup menu stays as it is. If
  they confirm, it calls `recover_unreadable_records()` and then opens the window.
- **Rationale**: The decision is made before any window is created, so declining really
  does leave the Setup menu showing (FR-020). A timestamped backup name never overwrites
  an earlier backup. The prompt text lives in the students UI module, not the
  composition root.
- **Alternatives considered**: *Let `StudentsWindow` handle it after it opens*. Rejected:
  on decline it would have to tear itself down, and the Setup menu would already be
  hidden.

## R6. Template choices without importing interpretation

- **Decision**: `students/` never imports `interpretation/`. `StudentsWindow` takes a
  provider, `list_template_choices: Callable[[], list[TemplateChoice]]`, where
  `TemplateChoice` is a `NamedTuple(template_id: str, name: str)` defined in
  `students/student.py`. `program.py` wires it as
  `lambda: [TemplateChoice(t.id, t.name) for t in template_store.get_all_templates()]`.
  A student stores only `current_template_id: str | None`. The window resolves the
  display name through the provider on every refresh, so a deleted template shows as
  missing (FR-008) and a renamed one shows its new name.
- **Rationale**: It keeps `students/` decoupled the same way the store does, and
  follows dependency-injection.md rule 2 (accept a provider, call it when needed).
  Template ids are already stable strings in `TemplateStore`.
- **Alternatives considered**: *Inject `TemplateStore` itself*. Rejected: `students/`
  would depend on `interpretation`'s concrete store and template classes.

## R7. A form that grows with later settings (FR-010, FR-011)

- **Decision**: `StudentEditorWindow` is a modal dialog, like `TemplateCreatorWindow`.
  It builds its form from an ordered list of field editors. Each one is a small class in
  `students/student_field_editors.py` that implements `StudentFieldEditor` (ABC):
  `build(parent: ttk.Frame, row: int) -> None`, `load(student: Student) -> None`, and
  `apply(student: Student) -> Student`, which returns a copy with that field set from the
  widget and may raise `StudentKeyError`. This feature ships two of them:
  `StudentKeyFieldEditor` (an entry) and `CurrentTemplateFieldEditor` (a read-only
  combobox). The list of students in `StudentsWindow` shows Student Key and Current
  Template columns.
- **Rationale**: Adding a setting later means adding a dataclass field with a default,
  one field-editor class, and one entry in the editor's list. Finding, adding, opening,
  and removing students doesn't change (FR-011).
- **Alternatives considered**: *Hard-code two widgets in the dialog*. Rejected: the
  request explicitly says not to narrow the design to these fields.

## R8. Navigation with a Setup menu

- **Decision**: The home screen's second button is relabeled **Manage Setup &
  Configuration**, and `on_manage` now opens `app_shell.setup_window.SetupWindow` in a
  Toplevel. `SetupWindow(master, on_templates, on_students, on_back, on_exit)` shows
  **Data Sheet Templates**, **Students**, and **Back**. `program.py` generalizes the
  feature 001 helpers:
  - `_open_child_window(parent: tk.Misc) -> tk.Toplevel` withdraws `parent` and returns
    a new `tk.Toplevel(root)`.
  - `_return_to(parent: tk.Misc, child: tk.Toplevel) -> None` destroys `child` and
    deiconifies `parent`.

  Template management and Students both get `back_callback`/`on_back` →
  `_return_to(setup_window, child)`. Every title-bar close and the management window's
  Close button stay `root.destroy` (FR-016; feature 001 FR-005a).
- **Rationale**: The same withdraw-and-Toplevel pattern as feature 001 (research R1
  there), one level deeper. Only one screen is ever visible (FR-015), and every path
  window is fresh on each visit, so the template list and student list are always
  re-read.
- **Alternatives considered**: *Swap frames inside the Setup Toplevel*. Rejected: the
  template management window takes over its `master`.

## R9. Launch contract

- **Decision**: `program.py` takes `<template_storage_file_path> <student_storage_file_path>`.
  Both must end in `.json` (case-insensitive), the same check as today. If the two paths
  resolve to the same file (`os.path.realpath` and `os.path.normcase` equal), it prints
  `Error: The template file and student records file must be different files` and exits
  with status 1. The usage text becomes
  `Usage: python program.py <template_storage_file_path> <student_storage_file_path>`
  with `Example: python program.py templates.json students.json`.
- **Rationale**: Clarification 5 chose a required second argument, and the spec's edge
  case covers the same-file mistake. Reusing `validate_storage_file_path` keeps both
  arguments behaving the same (FR-019).

## R10. Display defaults the spec left open

- **Decision**: Students are listed sorted by Student Key, ignoring letter case. Keys are
  shown exactly as the SLP typed them, after trimming. The Current Template column shows
  the template's name, `None selected`, or `Missing template`. In the editor, a missing
  template appears as the selected `Missing template` entry and is kept unless the SLP
  picks another. Opening and saving without touching it never silently clears the
  reference.
- **Rationale**: These were the clarify pass's low-impact defaults. Keeping a missing id
  until the SLP changes it avoids losing information through an unrelated edit.

## R11. Verification approach

- **Decision**: Manual validation through [quickstart.md](quickstart.md), plus a few
  `python -c` checks of `students/student.py` and `JsonStudentStore` against a
  scratch file. No test framework is added, the same as feature 001's research R8.
- **Rationale**: The repository still has no test dependency. The interface-plus-pure-
  rules design means a test suite can be added later without restructuring.
