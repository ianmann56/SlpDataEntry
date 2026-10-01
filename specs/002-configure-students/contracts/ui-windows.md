# Contract: UI Windows

**Feature**: [../spec.md](../spec.md) | **Date**: 2026-09-30

These are the constructors and visible behavior of the windows this feature adds or
changes. All signatures are fully annotated (Principle VI). Every window builds into a
padded `ttk.Frame` packed with `fill=tk.BOTH, expand=True`, so it follows the theme
(FR-018). Callbacks are stored as `_`-prefixed attributes.

## `app_shell.home_window.HomeWindow` (changed)

- The second button's label changes from **Manage Setup & Data Sheet Templates** to
  **Manage Setup & Configuration** (FR-012). The signature and everything else are
  unchanged.

## `app_shell.setup_window.SetupWindow` (new)

```python
class SetupWindow:
    def __init__(
        self,
        master: tk.Toplevel,
        on_templates: Callable[[], None],
        on_students: Callable[[], None],
        on_back: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None: ...
```

- Title: `Setup`. It shows exactly two choices, **Data Sheet Templates** →
  `on_templates()` and **Students** → `on_students()`, then a **Back** button →
  `on_back()` (FR-013).
- Title-bar close → `on_exit()` (FR-016).
- Imports only `tkinter`, `tkinter.ttk`, and `collections.abc` (layers.md rule 7).

## `students.students_window.StudentsWindow` (new)

```python
class StudentsWindow:
    def __init__(
        self,
        master: tk.Toplevel,
        student_store: StudentStore,
        list_template_choices: Callable[[], list[TemplateChoice]],
        on_back: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None: ...
```

- Title: `Students` (FR-001).
- It has a `ttk.Treeview` with the columns **Student Key** and **Current Template**,
  filled from `list_students()` (FR-002). The template column shows the template's name,
  `None selected`, or `Missing template` (FR-008, research R10).
- When the list is empty, the empty list is shown with the buttons still available
  (US1 scenario 1).
- The button row holds:
  - **Add Student** → opens `StudentEditorWindow` with `student=None`.
  - **Edit Selected**, or a double-click → opens the editor for that student (FR-004).
  - **Remove Selected** → asks `Remove the student "<key>"?`, and on yes calls
    `delete_student` (FR-005).
  - **Back** → `on_back()` (FR-014).
- With nothing selected, Edit or Remove shows a "No Selection" warning, the same as
  template management.
- Title-bar close → `on_exit()` (FR-016).
- After the editor saves, the list refreshes.
- Errors from the student store are shown through `tk_utils.error_handling.throw` (except
  the expected key errors, which the editor shows).

### Module helper: `ask_to_start_fresh`

```python
def ask_to_start_fresh(parent: tk.Misc, error: UnreadableStudentRecordsError) -> bool: ...
```

- Shows a yes/no prompt saying that the student records in `<file_path>` could not be
  loaded, and asking whether to start with an empty student list, keeping the
  unreadable file as a backup. Returns the answer (FR-020, research R5).

## `students.student_editor_window.StudentEditorWindow` (new, modal)

```python
class StudentEditorWindow:
    def __init__(
        self,
        parent: tk.Misc,
        student_store: StudentStore,
        template_choices: list[TemplateChoice],
        student: Student | None,
        on_saved: Callable[[], None],
    ) -> None: ...
```

- A `tk.Toplevel(parent)` that is `transient` and `grab_set`, like
  `TemplateCreatorWindow`. Its title is `Add Student`, or `Edit Student: <key>`.
- The form is built from the field editors, in order: `StudentKeyFieldEditor`, then
  `CurrentTemplateFieldEditor` (research R7). The template combobox is read-only, with
  the options `None selected` followed by each choice's name. When editing a student
  whose template is missing, a selected `Missing template` entry is also offered.
- Buttons: **Save** and **Cancel**. Cancel, or closing the dialog's title bar, destroys
  the dialog with no prompt (FR-004b).
- **Save**:
  1. Builds the student by calling each editor's `apply` on a copy of the student, or
     on `Student(student_key="")` when adding. A `StudentKeyError` is shown with
     `messagebox.showerror` and the dialog stays open.
  2. When editing, if `not student_keys_match(old_key, new_key)`, it asks:
     `The Student Key is the student's identifying key in the system. Change it from "<old>" to "<new>"? New data sheets for this student must use the new key "<new>".`
     If the SLP says no, nothing is saved and the dialog stays open (FR-004a).
  3. Calls `add_student` or `update_student(old_key, …)`. A `DuplicateStudentKeyError`
     is shown and the dialog stays open (US1 scenario 5, US2 scenario 3).
  4. On success, calls `on_saved()` and closes.

## `students.student_field_editors` (new)

```python
class StudentFieldEditor(ABC):
    @abstractmethod
    def build(self, parent: ttk.Frame, row: int) -> None: ...
    @abstractmethod
    def load(self, student: Student) -> None: ...
    @abstractmethod
    def apply(self, student: Student) -> Student: ...
```

| Editor | Label | Widget | `apply` |
| --- | --- | --- | --- |
| `StudentKeyFieldEditor` | `Student Key` | `ttk.Entry` | `replace(student, student_key=validate_student_key(text))` |
| `CurrentTemplateFieldEditor(template_choices)` | `Current Template` | read-only `ttk.Combobox` | `replace(student, current_template_id=<chosen id, None, or the kept missing id>)` |

## `interpretation.template_manager.template_management_window.DataSheetTemplateManagementWindow`

- No change. `program.py` passes a `back_callback` that returns to the Setup menu
  instead of home.

## Composition root wiring (`program.py`)

| Callback | Wired to |
| --- | --- |
| `HomeWindow.on_manage` | `setup = _open_child_window(root)` → `SetupWindow(setup, on_templates, on_students, on_back=lambda: _return_to(root, setup), on_exit=root.destroy)` |
| `SetupWindow.on_templates` | `top = _open_child_window(setup)` → `DataSheetTemplateManagementWindow(template_store, top, close_callback=root.destroy, interpreter_configs=STUB_INTERPRETER_CONFIGS, back_callback=lambda: _return_to(setup, top))` |
| `SetupWindow.on_students` | `try: student_store.list_students()`, `except UnreadableStudentRecordsError as e:` if `not ask_to_start_fresh(setup, e)`: `return`, otherwise `student_store.recover_unreadable_records()`. An `OSError` from that is shown with `throw(e, "Could not back up the student records")`, and the handler returns, leaving Setup showing. Then `top = _open_child_window(setup)` → `StudentsWindow(top, student_store, list_template_choices, on_back=lambda: _return_to(setup, top), on_exit=root.destroy)` |
| `list_template_choices` | `lambda: [TemplateChoice(t.id, t.name) for t in template_store.get_all_templates()]` |
| `HomeWindow.on_import` | Unchanged from feature 001 |
