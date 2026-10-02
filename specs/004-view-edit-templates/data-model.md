# Data Model: View and Edit Data Sheet Templates

**Feature**: [spec.md](spec.md) | **Research**: [research.md](research.md) | **Date**: 2026-10-01

## Data Sheet Template (changed)

`StudentDataSheetTemplate` in `interpretation/template_manager/student_data_sheet_template.py`.

| Field | Type | Rules |
| --- | --- | --- |
| `id` | `str` | Assigned by `TemplateStore.generate_new_id`. It never changes and is never reused (R10). |
| `name` | `str` | Required. Leading and trailing spaces are trimmed. It does not have to be unique. |
| `description` | `str` | **New.** Optional free text, `""` when absent (R6). No validation. It describes a sheet layout and must not identify a student (Principle I). |
| `interpreters` | `list[SessionDataSectionInterpreterBase]` | At least one. The saved order is the order shown and the order used to interpret. |

The constructor becomes `StudentDataSheetTemplate(id, name, configured_interpreters, description="")`,
so existing callers keep working.

## Section Interpreter in a template (unchanged shape)

| Field | Rules |
| --- | --- |
| `id` | Unique within the template, and kept across edits (FR-008). New interpreters get `uuid4` strings, as in the Create window. |
| type | Fixed once created (FR-006a). Shown by the config's `name`, or by the stored type name when no config handles it (R5). |
| `title` | May be blank. Non-blank titles are unique within the template, after trimming and with exact letter case (R2). |
| config | Specific to the type. An interpreter that is never re-applied is saved exactly as loaded (R4). |

## Templates file (changed format, R10)

```json
{
  "format_version": 2,
  "last_template_id": 7,
  "templates": [
    { "id": "4", "name": "Blah", "description": "", "interpreters": [ { "type": "...", "id": "...", "title": "...", "config": {} } ] }
  ]
}
```

| Read | Result |
| --- | --- |
| Missing file | Empty, with `last_template_id = 0` |
| Bare JSON list (format 1, from before this feature) | Read as is. `last_template_id` is the highest numeric `id`. Entries have no `description`. |
| Object with `format_version` 2 | Read as is |
| `format_version` > 2, or another shape | `UnreadableTemplatesError` from `check_readable` and every write method. Nothing is written. |

Every save writes format 2, using a temporary file that then replaces the real one.

## Student (unchanged record, new store operation)

`Student(student_key, current_template_id)`. This feature adds no fields.

`StudentStore.clear_current_template(template_id) -> list[str]` sets
`current_template_id = None` on every student whose value equals `template_id`. It saves
once, and returns the cleared keys sorted ignoring letter case. If there are no matches,
it returns `[]` and does not write (R9). It changes no other field (FR-010g).

## Template Usage (new, in `template_rules.py`)

```python
class TemplateUsage(NamedTuple):
    student_keys_by_template_id: dict[str, list[str]]   # keys sorted ignoring case

    def keys_for(self, template_id: str) -> list[str]: ...   # [] when unused
    def count_for(self, template_id: str) -> int: ...
```

`load_template_usage()` returns `TemplateUsage | None`. `None` means the student records
could not be read, which the UI shows as **Unknown** (FR-010d). A student whose
`current_template_id` matches no template is grouped under that ID, but no list row
shows that ID, so the student is not counted toward any template (Assumptions).

## Template Draft (new, in `template_rules.py`)

This is the working copy that edit mode changes. It is never saved directly.

| Member | Meaning |
| --- | --- |
| `template_id: str \| None` | The template being edited, or None for a new template (R13) |
| `name: str`, `description: str` | Current field values |
| `interpreters: list[SessionDataSectionInterpreterBase]` | Working list, starting as a copy of the saved list |
| `add(interpreter)` | Appends an interpreter. Raises `TitleConflictError` on a duplicate non-blank title. |
| `replace(index, interpreter)` | Swaps in a rebuilt interpreter at the same position. The caller builds it with the old interpreter's `id`. A different `id` raises `ValueError`, so an interpreter's id never changes (FR-008). Raises `TitleConflictError` like `add`. |
| `remove(index)`, `move(index, offset)` | Remove an interpreter, or move it up (`-1`) or down (`+1`). A move past either end does nothing. |
| `problems() -> list[str]` | Returns `validate_template(name, interpreters)` |
| `has_changes_from(template) -> bool` | Compares name, description, and `[serialize(i) for i in interpreters]` with the saved template. With `None` (a new template), returns whether anything has been entered. |
| `to_edit_dto() -> TemplateEditDto` | Returns the trimmed name and the description and interpreters as they are |
| `new()` (class method) | Starts an empty draft for the Create window |
| `to_create_dto() -> TemplateCreateDto` | Returns the trimmed name and the description and interpreters as they are |

## Template Details window modes (state transitions)

```text
                 View button / double-click
 management ───────────────────────────────▶ VIEW ──Close──▶ (window closed)
     │                                        │ ▲
     │ Edit button                      Edit  │ │ Save succeeded
     ▼                                        ▼ │ / Cancel (confirmed or no changes)
   EDIT ◀─────────────────────────────────── EDIT
     │
     ├─ Save, with problems ───────────────▶ EDIT   (problems shown, nothing saved)
     ├─ Save, students use it, declined ───▶ EDIT   (nothing saved)
     ├─ Save fails (OSError) ──────────────▶ EDIT   (draft intact, FR-014)
     ├─ Save, template missing ────────────▶ closed (list refreshed, FR-013)
     └─ Close with changes, confirmed ─────▶ closed
```

**Interpreter form** (edit mode only). Its states are *empty* (adding), *loaded*
(an interpreter is selected), and *changed* (it differs from what was loaded or emptied,
R4).

- Apply, or automatic apply when the selection changes or the SLP saves (FR-006e):
  changed → loaded. On a title conflict, the form stays changed, the selection stays,
  and nothing is saved.
- Form Cancel (FR-006f): changed → loaded or empty, with the earlier values back.

## Delete outcome (new, in `template_rules.py`)

```python
class DeleteResult(Enum):
    DELETED = "deleted"
    NOT_FOUND = "not_found"                         # template was gone; students untouched
    FAILED_AFTER_CLEARING = "failed_after_clearing" # students cleared, template delete raised

class DeleteOutcome(NamedTuple):
    result: DeleteResult
    cleared_student_keys: list[str]
    detail: str = ""
```

When clearing fails, the error is raised before the template is touched, so there is
no outcome for that case. The window reports "the delete did not happen" with the
reason.
