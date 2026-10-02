# Research: View and Edit Data Sheet Templates

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-01

Each decision has a number (R1–R12) that the plan, data model, and contracts refer to.
The Technical Context had no open `NEEDS CLARIFICATION` items. The spec's eight
clarifications settled the behavior, so this research is about where the rules live
and how they fit the existing code.

## R1. Where the shared template rules live

**Decision**: A new module, `interpretation/template_manager/template_rules.py`, holds
every rule that both the Create window and the Template Details window apply. It does
not import Tkinter.

- `validate_template(name, interpreters) -> list[str]` returns the problems in a form
  the SLP can read. The rules are: a name is required, at least one interpreter is
  required, and no two interpreters share a non-blank title.
- `find_title_conflict(title, interpreters, ignore_index) -> bool` checks a title
  against the other interpreters. Both windows call it when an interpreter form is
  applied.
- `TemplateDraft`, a working copy of a template that edit mode changes. Adding,
  replacing, removing, and moving interpreters all happen here, and the draft
  reports whether anything has changed. See [data-model.md](data-model.md).
- `save_confirmation(template_name, usage, template_id) -> str | None` and
  `delete_confirmation(...) -> str`. These choose which confirmation to show and build
  its text (R8, R9).

Both windows call these functions. Neither window decides a rule in a widget callback.

**Rationale**: The SLP asked for the two windows to share business logic, starting with
validation. Layers rule 5 already forbids business rules in widget callbacks. A
Tkinter-free module can be checked offline with fakes, as `SheetImportBatch` was in
feature 003.

**Alternatives considered**:
- Merging the Create window into the Template Details window. The SLP rejected this
  during clarification.
- A base window class shared by both windows. This was rejected because it shares
  widgets rather than rules, and it would still leave the rules untestable without a
  display.

## R2. Blank interpreter titles and the duplicate-title rule

**Decision**: The spec's FR-009 now states this rule. The duplicate rule compares titles after trimming spaces, with exact
letter case, and it ignores blank titles. Any number of interpreters may have a blank
title.

**Rationale**: FR-009 requires the same rules as creation, and the Create window has
always skipped blank titles (`if title and any(...)`). Saved templates already contain
several blank-titled interpreters in one template: the sample template "Test3" has two.
A strict rule would block every edit to those templates until the SLP renamed them,
which the spec does not ask for.

**Alternatives considered**: Requiring unique titles including blanks. This was rejected
because it breaks templates that already exist. Ignoring letter case was also rejected,
because it would change what creation allows today.

## R3. Opening an interpreter form with saved values

**Decision**: The `InterpreterConfig` contract gains two members. Every config must
provide them, as Principle V requires.

1. `interpreter_type: type[SessionDataSectionInterpreterBase]`. The window uses it to
   find a saved interpreter's config with `isinstance`.
2. A `load(interpreter)` function in the form that `create_config_form` returns, next
   to `get_config` and `reset`. It fills the form with that interpreter's title and
   configuration.

The returned dict becomes the `ConfigForm` `TypedDict` (type-declarations rule 4).
Table, Running Tally, and Simple Form each implement `load` from their public
properties: `columns`, `tally_choice_options`, and `fields`.

**Rationale**: FR-006a and FR-006b. The form already exists for each type, so filling it
is the smallest change, and it reuses the create path exactly.

**Alternatives considered**: A separate read-only editor for each type. This was
rejected because it duplicates every form.

## R4. Detecting unapplied form changes, and keeping unchanged interpreters exact

**Decision**: A form has unapplied changes when the interpreter it would build now
differs from the one it would have built just after `load` or `reset`. The window
compares the two by their `serialize(...)` output. No per-type comparison code is needed.

When the SLP does not change an interpreter, the draft keeps the original object, which
is saved through the same serializer. The form rebuilds an interpreter only when it has
unapplied changes, so an interpreter the SLP did not touch is saved exactly as it was.

**Rationale**: FR-006e applies changes automatically, and FR-011 counts unapplied
changes as changes. Both need a check for changes. The forms cannot show every saved
detail. Table forms always produce `column_choices = []`, and Simple Form fields are
always `TEXT`, so rebuilding an untouched interpreter could quietly lose data saved in
another way. Keeping the original object protects FR-008 and FR-015.

**Alternatives considered**: Tracking changes in each widget. This was rejected because
it needs code in every config for each widget. Comparing the dicts that `get_config`
returns was also rejected, because they hold `ColumnDefinition` objects, which cannot be
compared.

## R5. Showing an interpreter's configuration in view mode

**Decision**: `InterpreterConfig` gains `describe(interpreter) -> list[str]`, which
returns readable lines such as `Columns: Sentence, Pitch, Speed, Body`. The Template
Details window shows interpreters in a tree. Each interpreter is a row (type and title),
and its `describe` lines are child rows, expanded when the window opens. Edit mode keeps
the same tree. Selecting a row loads that interpreter's form into a panel below the
tree.

When no config handles an interpreter that loaded (FR-015), the window shows the stored type name.
The `config` part of `serialize(interpreter)` is shown as `key: value` lines. In edit
mode, that interpreter can be moved or removed, but its form cannot be opened.

**Rationale**: FR-002 and SC-001 require the full contents to be visible without opening
each interpreter. A tree keeps one layout for both modes (FR-004a). It also scrolls for
long configurations (edge case).

An interpreter type with no registered serializer still fails the whole template's
load, as it does today. The spec puts that case out of scope.

**Alternatives considered**: Showing a disabled copy of each form in view mode. This was
rejected because the SLP would see one interpreter at a time, which breaks SC-001.

## R6. Saving a template description

**Decision**: Each template entry in the file gains an optional `"description"` string.
When an entry has no description, it loads as `""` (FR-006d).
`StudentDataSheetTemplate` gains a `description` property, and the create and edit
DTOs gain a `description` field. The DTOs become typed `@dataclass` records. The
Create window passes the text it already collects (FR-006c).

**Rationale**: An optional key with a default is how the student store handles
additions to its records. Templates saved earlier load without any change, as
interpreters rule 4 requires.

## R7. One window with two modes

**Decision**: A new `template_details_window.py` replaces the stub
`template_editor_window.py`, and the stub is deleted. The window is a modal `Toplevel`,
like the Create window. It has a `mode` of `VIEW` or `EDIT`. Switching mode makes the
same widgets editable or read-only and swaps the buttons. In view mode, the buttons are
Edit and Close. In edit mode, they are Save and Cancel. Entering either mode gives the
shared `TemplateForm` (R13) a fresh `TemplateDraft` of the saved template, read-only in
view mode. See [contracts/ui-windows.md](contracts/ui-windows.md).

**Rationale**: This follows clarification 3, the single-window decision. A modal window
matches the Create window, and it stops two windows from editing the same template at
once.

## R8. Template usage without template management importing `students/`

**Decision**: Template management receives two injected callables. It never receives a
`StudentStore` or a `Student`.

| Need | Injected as | Wired in `program.py` to |
| --- | --- | --- |
| Which students use each template | `load_template_usage: Callable[[], TemplateUsage \| None]` | `list_students()` grouped by `current_template_id`; `None` when the records file is unreadable |
| Clear a template from every student | `clear_template_from_students: Callable[[str], list[str]]` | `student_store.clear_current_template(template_id)` |

`TemplateUsage` is defined in `template_rules.py`. It is a typed record of Student Keys
for each template ID. `None` means "unknown" (FR-010d). The list counts, the details
list, and the save confirmation all ask for the usage again at the moment they need it.
Usage is never cached (edge case: a student assigned during edit mode).

**Rationale**: Layers rule 1 keeps `interpretation/` pointing downstream, and rule 9 lets
only `interpretation/importing/` use `students/`. Injected callables keep template
management free of any `students/` import, so `layers.md` needs no new rule. Rule 8 also
still holds: `students/` imports nothing from the pipeline. Dependency-injection rule 6
already has windows receive providers. It now lists these two.

**Alternatives considered**:
- Injecting the `StudentStore`. This was rejected because it would need a new layer
  rule and would give template management more access than it needs.
- Grouping students in the window. This was rejected because it puts a rule in the UI.

## R9. Deleting a template that students use, and making it safe

**Decision**:
- `StudentStore` gains `clear_current_template(template_id) -> list[str]`. It loads the
  records once, sets `current_template_id = None` on every match, saves once with the
  existing atomic save, and returns the cleared Student Keys in sorted order. Because
  there is one save, a failure leaves every student unchanged. This makes the spec's
  "if clearing fails, the template is not deleted" a clean all-or-nothing step.
- A Tkinter-free function, `delete_template_and_clear_students(template_id, usage,
  clear, delete)`, in `template_rules.py` runs these steps:
  1. If usage is known and not empty, call `clear`. An exception stops the delete
     before the template is touched.
  2. Delete the template.
  3. Return a `DeleteOutcome` (`DELETED`, `NOT_FOUND`, or `FAILED_AFTER_CLEARING`) with
     the cleared keys.

  The window shows the confirmation from `delete_confirmation(...)` first, and reports
  the outcome afterwards.
- If usage is unknown (`None`), no student is changed and the template is deleted after
  confirmation, as the spec's edge case says.

**Rationale**: FR-010e, FR-010f, FR-010g, and SC-002b. One save in the store is the only
way to make "clear every user" all or nothing with a JSON file.

**Alternatives considered**: Calling `update_student` once per student. This was
rejected because it writes once per student, and a failure partway leaves some students
cleared and the template not deleted.

## R10. Template IDs are never reused (interpreters rule 6)

**Decision**: The templates file moves to the same versioned shape as the student
records:

```json
{ "format_version": 2, "last_template_id": 7, "templates": [ ... ] }
```

`generate_new_id` returns `max(last_template_id, highest numeric id) + 1`. The store
records it in `last_template_id` when it saves the new template. A bare list from
before this feature is read as format 1, with `last_template_id` taken from its highest
numeric ID. The next save writes format 2. A `format_version` newer than 2 is
unreadable (`UnreadableTemplatesError`), as in `JsonStudentStore`. `check_readable`
accepts both shapes.

Every write (`create_template`, `edit_template`, `delete_template`) and
`generate_new_id` loads the file strictly and lets `UnreadableTemplatesError`
propagate, so the app never overwrites a file it couldn't read. That includes a corrupt
file and one written by a newer version of the app. Only `get_all_templates` and
`get_template_by_id` keep their current behaviour of returning an empty result. Saves move to the temporary-file-then-replace pattern that
`JsonStudentStore` uses, so a failed save never leaves a half-written file (FR-014).

**Rationale**: Today `generate_new_id` returns the highest existing ID plus one, so
deleting the highest template frees its ID for the next template. That breaks
interpreters rule 6. The delete path now clears students, but a student who refers to a
template removed outside the app would quietly pick up a new, unrelated template with
the reused ID. Keeping the highest ID ever given out means IDs stay short and readable
in the list (they are the only way to tell same-named templates apart), and no ID is
used twice.

**Alternatives considered**:
- UUID template IDs. This was rejected because they are long and unreadable in the
  list's ID column, and existing IDs are short numbers.
- A separate file that records the highest ID. This was rejected because it adds a
  second file that can drift from the templates file.

## R11. Not-found, unreadable, and failed-save handling

**Decision**:
- **Opening a template that no longer exists**: when `get_template_by_id` returns
  `None`, the window shows "This template no longer exists", refreshes the list, and
  opens nothing (FR-013).
- **Saving a template that no longer exists**: when `edit_template` returns `None`, the
  window says the template was not found, writes nothing, refreshes the list, and
  closes, because there is nothing left to show (FR-013).
- **A save that fails**: an `OSError` from saving is reported through
  `tk_utils.error_handling.throw` as "The change was not saved", and the window stays
  in edit mode with the draft unchanged (FR-014).
- **Unreadable student records**: they make usage `None`. The list shows `Unknown`, and
  the details list says usage could not be determined (FR-010d).

## R12. Verification approach

**Decision**: The same approach as feature 003. There is no test framework. Scratch
scripts, which are not committed, check `template_rules.py`, `TemplateStore` (including
reading a format 1 file and never reusing an ID), and
`JsonStudentStore.clear_current_template` offline. They use copies of
`sample_data/templates.json` and `sample_data/students.json`. A manual
[quickstart.md](quickstart.md) covers the windows. No AWS or Google access is needed.

**Rationale**: The project has no test runner, and adding one is not justified for this
feature. Everything that can go wrong without a display is in the Tkinter-free modules.

## R13. One template form shared by the Create and Template Details windows

**Decision** (revisited after implementation, at the SLP's request): the fields of a
template live in one component, `TemplateForm` (`template_form.py`). It receives a
`TemplateDraft` and lets the SLP change it: the name, the description, and the
interpreter list with its Up, Down, Remove, Add, and filled-in config forms. It can be
read-only. It never saves anything and knows nothing about students. `commit()` copies
the fields into the draft and applies any unapplied interpreter form.

The two windows are thin parents around it, and each keeps only what is not shared:

| Window | Owns |
| --- | --- |
| `TemplateCreatorWindow` | An empty draft (`TemplateDraft.new()`), Create (`create_template`), and the "unsaved changes" prompt on Cancel |
| `TemplateDetailsWindow` | The ID and "Used by" rows, view/edit modes, the save confirmation, `edit_template`, and the not-found and failed-save handling |

`TemplateDraft` gains `template_id: str | None` (None for a new template), `new()`,
`to_create_dto()`, and `has_changes_from(None)` meaning "anything entered at all".
A shared `tk_utils.scrollable.create_scrollable_frame` gives both windows the same
scrolling area.

**Rationale**: Before this, the Create window had its own copy of the name, description,
and interpreter widgets, and a different way to add interpreters (no reorder, no
filled-in forms). Sharing the form makes creating look and work exactly like editing.
The one place the two differ, persistence, stays in each parent window.

**Effect on the Create window**: an interpreter is added by choosing a type, pressing
Add, filling the form, and pressing Apply, the same as in edit mode. Unapplied form
changes are applied on Create, and interpreters can be reordered before the template is
first saved. The old window-wide Return-to-create shortcut is dropped, because Return
is also used inside the form's text and list fields.

**Alternatives considered**: a base window class with the persistence in subclasses.
This was rejected because inheritance would still mix widgets and persistence in one
object. Composition keeps the form free of any saving.
