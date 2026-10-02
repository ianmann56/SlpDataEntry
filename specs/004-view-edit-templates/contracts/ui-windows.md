# Contract: Template Windows and Wiring

**Feature**: [../spec.md](../spec.md) | **Rules**: [template-rules.md](template-rules.md)

The windows collect input and show results. Every decision goes through
`template_rules.py` (layers rule 5, R1). Errors are reported through
`tk_utils.error_handling.throw` (dependency-injection rule 5).

## `DataSheetTemplateManagementWindow` (changed)

```python
def __init__(
    self,
    template_store: TemplateStore,
    master: tk.Misc,
    load_template_usage: Callable[[], TemplateUsage | None],         # NEW (R8)
    clear_template_from_students: Callable[[str], list[str]],        # NEW (R8)
    close_callback: Callable[[], None] | None = None,
    interpreter_configs: list[InterpreterConfig] | None = None,
    back_callback: Callable[[], None] | None = None,
) -> None: ...
def show(self) -> None: ...
```

**Unreadable templates file**: each time the list is filled, the window first calls
`template_store.check_readable()`. On `UnreadableTemplatesError`, it shows
"Could not read the templates file: <reason>" once per fill, and the list stays empty.
Create, Edit, and Delete then fail with the same reason rather than overwriting the file
(R10).

**List columns**: Template (name), ID, and **Students**. The Students column shows the
count from `usage.count_for(id)`, or `Unknown` when usage is `None` (FR-010a, FR-010d).
The list reloads both the templates and the usage every time it is filled: when the
window opens, and after any create, save, or delete.

**Buttons**:

| Button | Action |
| --- | --- |
| Create New Template | Opens `TemplateCreatorWindow` (unchanged flow, now saving the description) |
| View | Opens the Template Details window in `VIEW` (FR-001) |
| Edit | Opens the Template Details window directly in `EDIT` (FR-004) |
| Delete | Runs the delete flow below |
| Back / Close | Unchanged |

A double-click on a row does what View does. View, Edit, and Delete with no selection
show "Please select a template first." Before opening anything, the window reloads the
template by ID. If it is gone, the window says so and refreshes the list (FR-013).

**Delete flow** (FR-010e, FR-010f):
1. `usage = load_template_usage()` is read now, not taken from the list.
2. `askyesno` shows `delete_confirmation(name, id, usage)`. On No, the flow stops.
3. `delete_template_and_clear_students(id, usage, clear_template_from_students, template_store.delete_template)`.
   - Any exception passed back, whether from clearing or from deleting when nothing was
     cleared (for example `UnreadableTemplatesError` or `OSError`), shows "The template
     was not deleted: <reason>". The exception is caught in the window and never reaches
     Tk as an unhandled callback error.
   - `NOT_FOUND` shows "This template no longer exists."
   - `FAILED_AFTER_CLEARING` shows "Students JA, MK no longer have a Current Template,
     but the template could not be deleted: <detail>".
   - `DELETED` shows "Template '<name>' has been deleted."
4. Refresh the list.

## `TemplateDetailsWindow` (new: `template_details_window.py`, replaces the `template_editor_window.py` stub)

```python
class DetailsMode(Enum):
    VIEW = "view"
    EDIT = "edit"

class TemplateDetailsWindow:
    def __init__(
        self,
        parent: tk.Misc,
        template: StudentDataSheetTemplate,
        template_store: TemplateStore,
        interpreter_configs: list[InterpreterConfig],
        load_template_usage: Callable[[], TemplateUsage | None],
        on_saved: Callable[[], None],                 # refreshes the management list
        start_mode: DetailsMode = DetailsMode.VIEW,
    ) -> None: ...
```

It is a modal `Toplevel` (transient, with `grab_set`), like the Create window. The title
is "Template: <name>".

**Layout**: the same in both modes (FR-004a). It scrolls when the content is taller
than the window.

| Area | View mode | Edit mode |
| --- | --- | --- |
| Name | Read-only entry | Editable entry |
| ID | Label | Label (never editable) |
| Description | Read-only text | Editable text, with the hint "Describe the sheet layout. Don't include student names." |
| Interpreters | Tree: one row per interpreter (type and title), with `describe` lines as expanded child rows (R5) | Same tree, plus Up, Down, Remove, and an "Add" type picker |
| Interpreter form | Hidden | Panel below the tree: the selected interpreter's form loaded (R3), or an empty form for the type being added. It has Apply and Cancel (FR-006f). |
| Used by | `JA, MK` / "No students use this template." / "Could not determine which students use this template." | Same (FR-010b) |
| Buttons | Edit, Close | Save, Cancel |

**Mode behavior**:
- **Edit**: build `TemplateDraft.from_template(saved)`, make the fields editable, and
  show the form panel.
- **Selecting a tree row in edit mode**: first auto-apply any unapplied form changes
  (FR-006e, R4). On `TitleConflictError`, show the message, put the selection back,
  and stop. Then `load` the newly selected interpreter's form. For an interpreter no
  config handles, show "This interpreter's type can't be edited here", disable the
  form, and still allow Up, Down, and Remove (FR-015).
- **Apply**: build the interpreter from the form with the same `id`, then call
  `draft.replace(index, ...)`, or call `draft.add(...)` with a new `uuid4` id when
  adding. Then refresh the tree.
- **Form Cancel**: `load` the interpreter again, or `reset` the form when adding.
- **Save**:
  1. Auto-apply (as above).
  2. If `draft.problems()` is not empty, show them and stop.
  3. Read `usage = load_template_usage()` now.
  4. If `save_confirmation(...)` returns text, `askyesno` with it. On No, stay in edit
     mode.
  5. Call `template_store.edit_template(id, draft.to_edit_dto())`.
     - `None` means the template is gone: tell the SLP, call `on_saved()`, and close.
     - `OSError` goes to `throw(e, "The change was not saved")`, and the window stays in
       edit mode.
     - `UnreadableTemplatesError` goes to `throw(e, "The change was not saved")`, and the
       window stays in edit mode.
     - Success: keep the result as the saved template, call `on_saved()`, read the usage
       again for the Used by line, and switch to view mode.
- **Cancel, or the window's close button, in edit mode**: if
  `draft.has_changes_from(saved)` is true, or the form has unapplied changes, ask
  "Discard your changes to this template?" On Yes, Cancel returns to view mode and the
  close button closes the window. On No, nothing happens. Without changes, the window
  changes mode or closes without asking (FR-011).
- **Close in view mode**: closes without asking.

## `TemplateCreatorWindow` (changed)

- It passes `description=self.description_text.get("1.0", tk.END).strip()` in
  `TemplateCreateDto` (FR-006c).
- It shows the hint "Describe the sheet layout. Don't include student names." under
  the Description field (Principle I).
- `_validate_form` uses `validate_template(...)` and shows every problem it returns.
- `_add_interpreter` uses `find_title_conflict(...)` in place of its own check (R1).
- Its constructor and public members gain type annotations.

## `program.py` (changed wiring)

```python
def load_template_usage() -> TemplateUsage | None:
    try:
        students = student_store.list_students()
    except UnreadableStudentRecordsError:
        return None
    return group_usage([(s.student_key, s.current_template_id) for s in students])

DataSheetTemplateManagementWindow(
    template_store,
    path_window,
    load_template_usage=load_template_usage,
    clear_template_from_students=student_store.clear_current_template,
    close_callback=root.destroy,
    interpreter_configs=STUB_INTERPRETER_CONFIGS,
    back_callback=lambda: _return_to(setup, path_window),
)
```

`program.py` is the only place that touches both `students/` and template management
(layers rule 6).
