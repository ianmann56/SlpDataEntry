---

description: "Task list for the Students feature"
---

# Tasks: Students

**Input**: Design documents from `/specs/002-configure-students/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/cli.md](contracts/cli.md),
[contracts/student-store.md](contracts/student-store.md),
[contracts/ui-windows.md](contracts/ui-windows.md), [quickstart.md](quickstart.md)

**Tests**: No automated tests. The spec doesn't ask for them, and research R11 makes
verification manual through [quickstart.md](quickstart.md), plus `python -c` checks run
from `therepy_sessions/` against scratch files.

**Organization**: Tasks are grouped by user story. Two stories are P1: US4 makes the
Students window reachable, and US1 makes it useful. US4 comes first because US1's test
starts by opening the window.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US4 from spec.md

## Path Conventions

- All code is under `therepy_sessions/`. Modules import each other by package path from
  that directory (e.g. `from students.student import Student`).
- Every public function, method, attribute, and `__init__` added or changed is fully
  annotated per [type-declarations.md](../../docs/conventions/architecture/type-declarations.md).
  Callbacks and injected collaborators are stored as `_`-prefixed attributes.
- UI: `ttk` widgets only. Each window packs a padded `ttk.Frame` with
  `fill=tk.BOTH, expand=True` (FR-018). The theme is set once in `program.py`.
- `students/` MUST NOT import from `clients/`, `collection/`, `interpretation/`, or
  `storage/` (research R1, R6).
- Use only placeholder keys (`JA`, `BK`, `JM`, `ZZ`) and scratch files in checks
  (Principle I).

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Create the `students` package by adding an empty `therepy_sessions/students/__init__.py` (plan.md Project Structure, research R1).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The student record, its rules, the student store, and the two-argument launch. Every story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Create `therepy_sessions/students/student.py` per [data-model.md](data-model.md):
  - A `@dataclass(frozen=True) class Student` with `student_key: str` and `current_template_id: str | None = None`. It has no catch-all field for unknown keys (research R4).
  - `class TemplateChoice(NamedTuple)` with `template_id: str` and `name: str`.
  - The functions `normalize_student_key(raw: str) -> str`, `validate_student_key(raw: str) -> str`, and `student_keys_match(a: str, b: str) -> bool`, with the exact behavior and messages in the data-model "Rules and exceptions" table. The length limit is the module constant `MAX_STUDENT_KEY_LENGTH: int = 5`.
  - The exceptions `StudentKeyError(ValueError)`, `DuplicateStudentKeyError(StudentKeyError)` (its `__init__(self, student_key: str) -> None` builds the message `The Student Key "<key>" is already in use.`), `StudentNotFoundError(LookupError)`, and `UnreadableStudentRecordsError(Exception)` (its `__init__(self, file_path: str, reason: str) -> None` stores `self.file_path: str`, with the message `Could not read student records from <file_path>: <reason>`).
  - Imports are standard library only.
  - The module docstring notes that a Student holds no names or other direct identifiers (Principle I).
- [X] T003 [P] Create the `StudentStore` ABC in `therepy_sessions/students/student_store.py`, with the six abstract methods and the exact signatures and docstrings (behavior plus raised exceptions) from [contracts/student-store.md](contracts/student-store.md). Imports: `abc` and `students.student`.
- [X] T004 Create `JsonStudentStore(StudentStore)` in `therepy_sessions/students/json_student_store.py` (depends on T002, T003), per [contracts/student-store.md](contracts/student-store.md), [data-model.md](data-model.md) "Student records file", and research R4/R5:
  - `__init__(self, file_path: str) -> None` stores `self._file_path` and does no file I/O.
  - `_load() -> list[Student]`:
    - A missing file returns `[]`.
    - Otherwise it reads UTF-8 JSON. The data must be a `dict` whose `students` is a `list` of `dict`s, each with a `str` `student_key`. Anything else (including `json.JSONDecodeError`) raises `UnreadableStudentRecordsError(self._file_path, <reason>)`.
    - `format_version` defaults to 1 when it is missing. If it is not an `int`, or is greater than 1, it raises `UnreadableStudentRecordsError(self._file_path, "written by a newer version of the app")` (or `"invalid format_version"` if it is not an int).
    - Each entry becomes `Student(student_key=entry["student_key"], current_template_id=entry.get("current_template_id"))`. Missing fields take their defaults (FR-010), and unknown keys are ignored.
  - `_save(students: list[Student]) -> None`:
    - It writes `{"format_version": 1, "students": [...]}`, where each entry is `{"student_key": s.student_key, "current_template_id": s.current_template_id}`, with `indent=2` and `ensure_ascii=False`.
    - It writes to a temp file in the same directory (`tempfile.NamedTemporaryFile(dir=..., delete=False, mode="w", encoding="utf-8", suffix=".tmp")`), then calls `os.replace(tmp, self._file_path)`. It creates parent directories if they're missing.
  - `list_students` returns `sorted(self._load(), key=lambda s: s.student_key.casefold())`.
  - `get_student` uses `student_keys_match`.
  - `add_student`: `key = validate_student_key(student.student_key)`. If any existing key matches, it raises `DuplicateStudentKeyError(key)`. Otherwise it appends `replace(student, student_key=key)`, saves, and returns it.
  - `update_student(original_key, student)`: finds the index matching `original_key` (`StudentNotFoundError` if there is none) and validates the new key. If any *other* index matches the new key, it raises `DuplicateStudentKeyError`. It replaces the entry, saves, and returns it.
  - `delete_student`: finds the matching student (`StudentNotFoundError` if there is none), removes it, and saves.
  - `recover_unreadable_records() -> str`:
    - If the file is missing, or `_load()` succeeds, it returns `""`.
    - Otherwise it builds `<dir>/<stem>.unreadable-<time.strftime('%Y%m%d-%H%M%S')>.json`, adding `-1`, `-2`, … before `.json` while that path exists. It then calls `os.replace(self._file_path, backup)` and returns `backup`.
  - It does no Tkinter and no network I/O.
- [X] T005 Update the launch contract in `therepy_sessions/program.py` per [contracts/cli.md](contracts/cli.md) and research R9 (depends on T004):
  - `parse_command_line_args() -> list[str]` now requires `len(sys.argv) >= 3`. Otherwise it prints `Usage: python program.py <template_storage_file_path> <student_storage_file_path>` and `Example: python program.py templates.json students.json`, then `sys.exit(1)`.
  - It calls `validate_storage_file_path` on `sys.argv[1]` and then on `sys.argv[2]`.
  - It adds `validate_distinct_storage_files(template_path: str, student_path: str) -> None`. When `os.path.normcase(os.path.realpath(template_path)) == os.path.normcase(os.path.realpath(student_path))`, it prints `Error: The template file and student records file must be different files` and calls `sys.exit(1)`. `parse_command_line_args` calls it. It has full annotations and a docstring.
  - In `main()`: `template_storage_file_path, student_storage_file_path = args[0], args[1]`, then `student_store: StudentStore = JsonStudentStore(student_storage_file_path)`, created right after `template_store`. This is the only place it is constructed (research R2).
  - It adds the imports `os`, `students.json_student_store.JsonStudentStore`, and `students.student_store.StudentStore`.

**Checkpoint**: Quickstart V1 passes (all four rows). Then run this from `therepy_sessions/` to check the pure rules and the student store:

```sh
../.venv/bin/python3 -c "
from students.student import *; from students.json_student_store import JsonStudentStore
import tempfile, os
r = JsonStudentStore(os.path.join(tempfile.mkdtemp(), 's.json'))
r.add_student(Student(' JA ')); print(r.list_students())
try: r.add_student(Student('ja'))
except DuplicateStudentKeyError as e: print(e)
"
```

**Expect**: `[Student(student_key='JA', ...)]`, then the "already in use" message.

---

## Phase 3: User Story 4 - Reach the Students window from the Setup menu (Priority: P1) 🎯 MVP part 1

**Goal**: Home → **Manage Setup & Configuration** → Setup menu (*Data Sheet Templates*, *Students*, *Back*). Students and template management each go Back to Setup. Every title-bar ✕ exits.

**Independent Test**: Quickstart V2 (steps 1–6). At this point the Students window shows an empty list and a Back button.

- [X] T006 [P] [US4] Relabel the second button in `therepy_sessions/app_shell/home_window.py` from `Manage Setup & Data Sheet Templates` to `Manage Setup & Configuration` (FR-012). Update its docstring wording for `on_manage` to "setup and configuration choice". Nothing else changes.
- [X] T007 [P] [US4] Create `SetupWindow` in `therepy_sessions/app_shell/setup_window.py` per [contracts/ui-windows.md](contracts/ui-windows.md), following the structure of `app_shell/home_window.py`:
  - `__init__(self, master: tk.Toplevel, on_templates: Callable[[], None], on_students: Callable[[], None], on_back: Callable[[], None], on_exit: Callable[[], None]) -> None`.
  - The title is `Setup`, and `WM_DELETE_WINDOW` calls `on_exit`.
  - It stacks three `ttk.Button`s with `fill=tk.X`: **Data Sheet Templates**, **Students**, then **Back** (with `pady=(20, 0)` above it).
  - Imports: only `tkinter`, `tkinter.ttk`, and `collections.abc.Callable`.
  - The class docstring describes it as a navigation menu that holds no business logic.
- [X] T008 [P] [US4] Create the first version of `StudentsWindow` in `therepy_sessions/students/students_window.py` (depends on T002, T003), with the signature from [contracts/ui-windows.md](contracts/ui-windows.md):
  - `__init__(self, master: tk.Toplevel, student_store: StudentStore, list_template_choices: Callable[[], list[TemplateChoice]], on_back: Callable[[], None], on_exit: Callable[[], None]) -> None`.
  - It stores everything as `_` attributes. The title is `Students`, and `WM_DELETE_WINDOW` calls `on_exit`.
  - It has a `ttk.Treeview` (`show="headings"`, height 10, with a vertical scrollbar) with the columns `key` ("Student Key") and `template` ("Current Template").
  - It has a button row with **Back** → `on_back`, packed `side=tk.RIGHT`.
  - It adds `refresh(self) -> None`, which clears the tree and inserts one row per `self._student_store.list_students()` (`iid` = student key), with the template text from `_template_label(student, choices)`. `choices` is `self._list_template_choices()`, called once per refresh. `_template_label` returns the matching choice's name, `None selected` for `None`, or `Missing template` (research R10). `__init__` calls `refresh()` at the end.
  - The class docstring states that it receives its student store and template provider by injection, and never builds them.
- [X] T009 [US4] Wire the Setup menu in `therepy_sessions/program.py` (depends on T005, T006, T007, T008), per the wiring table in [contracts/ui-windows.md](contracts/ui-windows.md) and the navigation tables in [data-model.md](data-model.md):
  - Replace the helpers. `_open_path_window(root)` becomes `_open_child_window(root: tk.Tk, parent: tk.Misc) -> tk.Toplevel`, which calls `parent.withdraw()` and returns `tk.Toplevel(root)`. `_return_home` becomes `_return_to(parent: tk.Misc, child: tk.Toplevel) -> None`, which destroys `child` and calls `parent.deiconify()`. Update `open_import_path` to use `_open_child_window(root, root)` and `_return_to(root, path_window)`.
  - `open_management_path` now creates `setup = _open_child_window(root, root)` and `SetupWindow(setup, on_templates=lambda: open_templates(setup), on_students=lambda: open_students(setup), on_back=lambda: _return_to(root, setup), on_exit=root.destroy)`.
  - `open_templates(setup: tk.Toplevel) -> None` is the old management body with `top = _open_child_window(root, setup)` and `back_callback=lambda: _return_to(setup, top)`. `close_callback` is still `root.destroy`.
  - `open_students(setup: tk.Toplevel) -> None` creates `top = _open_child_window(root, setup)` and `StudentsWindow(top, student_store, list_template_choices, on_back=lambda: _return_to(setup, top), on_exit=root.destroy)`.
  - `list_template_choices` is a nested `def list_template_choices() -> list[TemplateChoice]: return [TemplateChoice(t.id, t.name) for t in template_store.get_all_templates()]`.
  - It imports `SetupWindow`, `StudentsWindow`, and `TemplateChoice`.

**Checkpoint**: Quickstart V2 passes. An empty Students window opens and goes Back to Setup.

---

## Phase 4: User Story 1 - Add a student and see the list (Priority: P1) 🎯 MVP part 2

**Goal**: Add students with a validated, unique key and an optional Current Template. They are listed and kept across relaunches. A damaged records file is recovered safely.

**Independent Test**: Quickstart V3 (steps 1–7) and V7.

- [X] T010 [P] [US1] Create `therepy_sessions/students/student_field_editors.py` per [contracts/ui-windows.md](contracts/ui-windows.md) "student_field_editors" and research R7/R10:
  - It defines `StudentFieldEditor(ABC)` with the abstract `build(self, parent: ttk.Frame, row: int) -> None`, `load(self, student: Student) -> None`, and `apply(self, student: Student) -> Student`.
  - `StudentKeyFieldEditor`:
    - `build` puts a `ttk.Label(text="Student Key")` in column 0 and a `ttk.Entry` (width 10, `textvariable` a `tk.StringVar`) in column 1 of `row`. Column 1 has `sticky="ew"`.
    - `load` sets the text to `student.student_key`.
    - `apply` returns `replace(student, student_key=validate_student_key(text))`, letting `StudentKeyError` propagate.
    - It adds `focus(self) -> None` to focus the entry.
  - `CurrentTemplateFieldEditor(template_choices: list[TemplateChoice])`:
    - `build` puts a label `Current Template` and a `ttk.Combobox(state="readonly")`.
    - `load` sets the options to `["None selected"] + [c.name for c in choices]`, and appends `"Missing template"` only when `student.current_template_id` is not `None` and matches no choice. It selects the option for the current value.
    - `apply` maps the selected index back:
      - index 0 → `None`;
      - a choice → `choice.template_id`;
      - `Missing template` → the original id it was loaded with (kept, research R10).
    - Map by index, not by name, so duplicate template names work.
  - Imports: `tkinter`, `tkinter.ttk`, `abc`, `dataclasses.replace`, and `students.student`.
- [X] T011 [US1] Create `StudentEditorWindow` in `therepy_sessions/students/student_editor_window.py`, in add mode (depends on T010), per [contracts/ui-windows.md](contracts/ui-windows.md):
  - `__init__(self, parent: tk.Misc, student_store: StudentStore, template_choices: list[TemplateChoice], student: Student | None, on_saved: Callable[[], None]) -> None`.
  - It stores `self._original: Student | None = student`, along with the student store and callback as `_` attributes. It creates `self._window = tk.Toplevel(parent)`, then `transient(parent)`, `wait_visibility()`, and `grab_set()`, the same as `interpretation/template_manager/template_creator_window.py`. The title is `Add Student` when `student is None`, otherwise `Edit Student: <key>`.
  - `self._field_editors: list[StudentFieldEditor] = [StudentKeyFieldEditor(), CurrentTemplateFieldEditor(template_choices)]`. Build each one into a grid frame (rows 0..n-1, column 1 with weight 1), then `load(student or Student(student_key=""))`, and focus the key entry.
  - Buttons: **Save** → `_on_save`, and **Cancel** → `self._window.destroy`. `WM_DELETE_WINDOW` → `self._window.destroy`, with no prompt (FR-004b).
  - `_on_save`:
    - It folds `apply` over the editors, starting from `self._original or Student(student_key="")`.
    - On `StudentKeyError` it calls `messagebox.showerror("Invalid Student Key", str(e), parent=self._window)` and returns.
    - In add mode it calls `add_student(draft)`, and on `DuplicateStudentKeyError` shows the same kind of error and returns.
    - On success it calls `self._on_saved()` and then `self._window.destroy()`.
    - Any other exception goes to `tk_utils.error_handling.throw(e, "Could not save the student")`.
  - Leave a clearly marked spot in `_on_save` for the edit path (US2).
- [X] T012 [US1] Add **Add Student** to `StudentsWindow` in `therepy_sessions/students/students_window.py` (depends on T008, T011):
  - Add a **Add Student** button on the left of the button row. It opens `StudentEditorWindow(self._window, self._student_store, self._list_template_choices(), None, on_saved=self.refresh)`.
  - Wrap the body of `refresh` so that an `UnreadableStudentRecordsError` raised there (for example, if the file is damaged while the window is open) goes to `tk_utils.error_handling.throw(e, "Could not load students")`.
- [X] T013 [US1] Add the damaged-file recovery (FR-020, research R5):
  - Add the module function `ask_to_start_fresh(parent: tk.Misc, error: UnreadableStudentRecordsError) -> bool` to `therepy_sessions/students/students_window.py`. It returns `messagebox.askyesno("Student Records Could Not Be Loaded", f"The student records in {error.file_path} could not be loaded.\n\nStart with an empty student list? The unreadable file will be kept as a backup.", parent=parent)`.
  - In `therepy_sessions/program.py`, `open_students(setup)` first runs `try: student_store.list_students()`. On `except UnreadableStudentRecordsError as e:`, if `not ask_to_start_fresh(setup, e)` it returns, leaving Setup visible. Otherwise it calls `student_store.recover_unreadable_records()` inside `try`/`except OSError as e:`. On `OSError` it calls `tk_utils.error_handling.throw(e, "Could not back up the student records")` and returns, leaving Setup visible and the file untouched (FR-020: the backup comes before the empty list). Only then does it call `_open_child_window` and create the `StudentsWindow`.

**Checkpoint**: Quickstart V3 and V7 pass. US4 and US1 together are the MVP.

---

## Phase 5: User Story 2 - View and update a student (Priority: P2)

**Goal**: Open a student, change their template or key (with the identifying-key warning), and save. Cancel, Back, or ✕ discards changes silently.

**Independent Test**: Quickstart V4 (steps 1–5), V6, and V8.

- [X] T014 [US2] Add the edit path to `therepy_sessions/students/student_editor_window.py` (depends on T011), per [contracts/ui-windows.md](contracts/ui-windows.md) Save steps 2–4:
  - When `self._original` is not `None` and `not student_keys_match(self._original.student_key, draft.student_key)`, ask `messagebox.askyesno("Change Student Key", f'The Student Key is the student\'s identifying key in the system. Change it from "{old}" to "{new}"?\n\nNew data sheets for this student must use the new key "{new}".', parent=self._window)`. On no, return with nothing saved and the dialog left open (FR-004a).
  - Then call `update_student(self._original.student_key, draft)`. `DuplicateStudentKeyError` is shown and returns, and `StudentNotFoundError` goes to `throw`.
  - Changes to letter case or surrounding spaces skip the prompt.
- [X] T015 [US2] Add editing to `StudentsWindow` in `therepy_sessions/students/students_window.py` (depends on T012, T014):
  - Add **Edit Selected** next to Add, plus `<Double-Button-1>` on the tree. Both call `_on_edit`.
  - `_on_edit` reads the selected `iid` and calls `self._student_store.get_student(iid)`. With nothing selected it shows `messagebox.showwarning("No Selection", "Please select a student to edit.", parent=self._window)`. It then opens `StudentEditorWindow(self._window, self._student_store, self._list_template_choices(), student, on_saved=self.refresh)`.
  - Wrap the `get_student` call in `try`/`except Exception as e`, and send any error to `tk_utils.error_handling.throw(e, "Could not open the student")` before returning. This covers a records file that becomes unreadable while the window is open.

**Checkpoint**: Quickstart V4, V6, and V8 pass.

---

## Phase 6: User Story 3 - Remove a student (Priority: P3)

**Goal**: Remove a student after confirming.

**Independent Test**: Quickstart V5 (steps 1–2).

- [X] T016 [US3] Add **Remove Selected** to `StudentsWindow` in `therepy_sessions/students/students_window.py` (depends on T015), after Edit:
  - `_on_remove` handles no selection with a "No Selection" warning ("Please select a student to remove.").
  - Otherwise it asks `messagebox.askyesno("Confirm Remove", f'Remove the student "{key}"?', parent=self._window)`. On yes it calls `self._student_store.delete_student(key)` and then `refresh()`. Any exception from the store (including `UnreadableStudentRecordsError` and `StudentNotFoundError`) goes to `tk_utils.error_handling.throw(e, "Could not remove the student")`.

**Checkpoint**: Quickstart V5 passes. All four stories work.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T017 [P] Amend `docs/conventions/architecture/layers.md` (plan Constitution Check III, research R1/R6):
  - Add `students/        student setup records, student store, and windows; no pipeline imports` to the layout block.
  - Change the `app_shell/` line to `navigation shell windows (home screen, Setup menu); Tkinter only`.
  - Extend rule 5's list of UI windows to `(`interpretation/template_manager/*_window.py`, `interpretation/importing/*_window.py`, `students/*_window.py`)`.
  - Add rule 8: **Students stand apart from the pipeline.** `students/` MUST NOT import from `clients/`, `collection/`, `interpretation/`, or `storage/`. It reaches templates only through the `TemplateChoice` provider wired in `program.py`, and its data only through the injected `StudentStore`.
- [X] T018 [P] Amend rule 6 in `docs/conventions/architecture/dependency-injection.md` to read: "**Inject stores and config lists too.** Windows receive `TemplateStore`, `StudentStore`, their `InterpreterConfig` list, and providers such as `list_template_choices` through their constructors. They MUST NOT create their own. `program.py` builds the one `JsonStudentStore`."
- [X] T019 [P] Add rows to the "Software concepts" table in `docs/domain/glossary.md` (Principle II):
  - `| **Current Template** | `Student.current_template_id` | The Data Sheet Template used to interpret a student's data sheets. It is optional, and may refer to a template that has since been deleted. |`
  - `| **Student Store** | `StudentStore` | Saves and loads Students, identified by Student Key. The current implementation, `JsonStudentStore`, keeps them in a local JSON file given at launch. |`
- [X] T020 Amend `.specify/memory/constitution.md` per its Governance procedure (depends on T017, T018, T019):
  - Prepend a new Sync Impact Report: version 1.2.0 → 1.3.0 (MINOR: new layer rule and an expanded injection rule in referenced docs). Modified principles: none. Supporting docs: `layers.md` (`students/` and rule 8; `students/*_window.py` in rule 5; Setup menu in `app_shell/`), `dependency-injection.md` (rule 6), and `glossary.md` (Current Template, Student Store). Keep the prior history.
  - Set the footer to `**Version**: 1.3.0` and `**Last Amended**:` to the date of the change.
- [X] T021 Run the boundary checks from quickstart V9 from `therepy_sessions/`:
  - `grep -rnE "^(from|import) (interpretation|clients|collection|storage)" students/` → no matches.
  - `grep -rn "JsonStudentStore(" --include=*.py .` → only `program.py`.
  - `grep -rnE "^(from|import) " app_shell/setup_window.py` → only `tkinter` and `collections.abc`.
  - Check that every public signature and attribute added in T002–T016 is annotated.
- [X] T022 Run the full manual validation in [quickstart.md](quickstart.md) V1–V9 with scratch files and placeholder keys only, and fix any failure in the file responsible.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)** → **Foundational (T002–T005)** → all stories.
- **US4 (T006–T009)** → **US1 (T010–T013)**. US1's test opens the window through the Setup menu, and T012 extends the window from T008.
- **US2 (T014–T015)** and **US3 (T016)** both need US1. T016 places Remove after the Edit button that T015 adds, so do T015 before T016.
- **Polish**: T017–T019 can start any time after Phase 2. T020 needs T017–T019. T021 and T022 come last.

### Same-file sequencing

| File | Tasks, in order |
| --- | --- |
| `program.py` | T005 → T009 → T013 |
| `students/students_window.py` | T008 → T012 → T013 → T015 → T016 |
| `students/student_editor_window.py` | T011 → T014 |

### Parallel Opportunities

- After T001: T002 and T003 (different files).
- After Phase 2: T006, T007, T008, and T010 (four different files), plus the docs tasks T017, T018, and T019.

## Parallel Example: after Phase 2

```bash
Task: "T006 Relabel home button in therepy_sessions/app_shell/home_window.py"
Task: "T007 Create SetupWindow in therepy_sessions/app_shell/setup_window.py"
Task: "T008 Create StudentsWindow skeleton in therepy_sessions/students/students_window.py"
Task: "T010 Create field editors in therepy_sessions/students/student_field_editors.py"
Task: "T017/T018/T019 Docs amendments"
# Then sequentially: T009 (program.py) → T011 → T012 → T013
```

## Implementation Strategy

### MVP (US4 + US1)

1. T001–T005: record, rules, student store, launch. Check V1 and the `python -c` check.
2. T006–T009: the Setup menu and an empty Students window. Check V2.
3. T010–T013: add, list, and damaged-file recovery. Check V3 and V7. **Stop and validate.**

### Incremental Delivery

4. US2 (T014–T015): editing and the key-change warning. Check V4, V6, and V8.
5. US3 (T016): remove. Check V5.
6. Polish (T017–T022): docs, constitution 1.3.0, boundary checks, and the full quickstart.

## Notes

- `[P]` tasks touch different files and have no dependencies on incomplete tasks.
- Never use real student keys or real records files in checks.
- Commit after each task or logical group, and stop at any checkpoint to validate.
