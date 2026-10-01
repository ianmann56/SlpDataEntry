# Data Model: Students

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-09-30

## Student (`students/student.py`)

A frozen `@dataclass` (Principle VI: typed record). Edits make a new copy with
`dataclasses.replace`.

| Field | Type | Default | Rules |
| --- | --- | --- | --- |
| `student_key` | `str` | — (required) | Trimmed. 1–5 characters, any characters. Unique across all students, ignoring letter case (FR-006). Stored as typed after trimming. |
| `current_template_id` | `str \| None` | `None` | `None` means "None selected". Otherwise the id of a Data Sheet Template, which may no longer exist (FR-007, FR-008). |
| `extra_fields` | `dict[str, Any]` | empty dict | Keys from the file that this version doesn't know about, kept so they are written back unchanged (research R4). Not shown in the UI. |

- **Identity**: a student is identified by `student_key`. Two keys are the same key when
  `student_keys_match(a, b)` is true: equal after trimming, ignoring case.
- **Never stored**: names or any other direct identifier (FR-003, Principle I). A later
  field that would add one needs a constitution amendment (spec Assumptions).
- **Adding a field later**: add a dataclass field *with a default*, a
  `StudentFieldEditor` for it, and an entry in the editor's field list (research R7).
  Older records load with the default (FR-010, SC-006).

## TemplateChoice (`students/student.py`)

`NamedTuple(template_id: str, name: str)`. It is a read-only view of one Data Sheet
Template, supplied by `program.py` through the `list_template_choices` provider (research
R6). `students/` never sees `StudentDataSheetTemplate`.

## Rules and exceptions (`students/student.py`)

| Name | Kind | Behavior |
| --- | --- | --- |
| `normalize_student_key(raw: str) -> str` | function | `raw.strip()` |
| `validate_student_key(raw: str) -> str` | function | Returns the normalized key. Raises `StudentKeyError("A Student Key is required.")` if it is empty, and `StudentKeyError("A Student Key can be at most 5 characters.")` if it is longer than 5. |
| `student_keys_match(a: str, b: str) -> bool` | function | `normalize(a).casefold() == normalize(b).casefold()` |
| `StudentKeyError(ValueError)` | exception | The key is invalid. Its message is shown to the SLP. |
| `DuplicateStudentKeyError(StudentKeyError)` | exception | Another student already uses the key. Message: `The Student Key "<key>" is already in use.` |
| `StudentNotFoundError(LookupError)` | exception | `update` or `delete` was given a key that matches no student. |
| `UnreadableStudentRecordsError(Exception)` | exception | The records file exists but can't be parsed. Carries `file_path: str`. |

## Student records file

The path comes from the second launch argument ([contracts/cli.md](contracts/cli.md)).
The format is UTF-8 JSON with `indent=2`:

```json
{
  "format_version": 1,
  "students": [
    { "student_key": "JA", "current_template_id": "3" },
    { "student_key": "BK", "current_template_id": null }
  ]
}
```

| Condition | Result |
| --- | --- |
| File missing | Empty list. The file is created on the first add. |
| Not JSON, not an object, `students` not a list, or an entry without a string `student_key` | `UnreadableStudentRecordsError` |
| Entry missing `current_template_id` (or any later field) | That field's default |
| Unknown keys in an entry | Kept in `extra_fields` and written back |
| `format_version` higher than 1 | Loaded best effort, with unknown keys kept. No error. |

Writes go to a temporary file in the same folder, which then replaces the real file with
`os.replace` (research R4).

## Lifecycle of a student

```text
            add (valid, unique key)
 (none) ───────────────────────────▶ SAVED ◀──────────────────────────┐
                                       │  update, same key             │
                                       ├───────────────────────────────┤
                                       │  update, new unique key       │
                                       │  (only after the key-change   │
                                       │   warning is confirmed)       │
                                       ├───────────────────────────────┘
                                       │  delete (after confirm)
                                       ▼
                                    (gone)
```

- Changing only letter case or surrounding spaces counts as the same key, so there's no
  warning (spec Edge Cases).
- Cancel, Back, or closing the editor discards the draft without a prompt (FR-004b).

## Navigation state (extends feature 001's state machine)

| State | Visible window | Hidden | Notes |
| --- | --- | --- | --- |
| `HOME` | Home screen (root) | — | |
| `IMPORTING` | Import window | root | Unchanged from feature 001 |
| `SETUP` | Setup menu (Toplevel) | root | New |
| `MANAGING_TEMPLATES` | Template management (Toplevel) | root, Setup | Now opened from the Setup menu |
| `MANAGING_STUDENTS` | Students window (Toplevel), and possibly the modal editor | root, Setup | New |
| `EXITED` | none | — | `root.destroy()` |

| From | Trigger | To | Effect |
| --- | --- | --- | --- |
| `HOME` | **Manage Setup & Configuration** | `SETUP` | Withdraw root; create the Setup Toplevel |
| `SETUP` | Back | `HOME` | Destroy Setup; deiconify root |
| `SETUP` | **Data Sheet Templates** | `MANAGING_TEMPLATES` | Withdraw Setup; create the template management Toplevel |
| `MANAGING_TEMPLATES` | Back | `SETUP` | Destroy it; deiconify Setup |
| `SETUP` | **Students**, records readable | `MANAGING_STUDENTS` | Withdraw Setup; create the Students Toplevel |
| `SETUP` | **Students**, records unreadable, SLP confirms fresh start | `MANAGING_STUDENTS` | Back up the file, then as above |
| `SETUP` | **Students**, records unreadable, SLP declines | `SETUP` | Nothing changes |
| `MANAGING_STUDENTS` | Back | `SETUP` | Destroy it; deiconify Setup |
| any path state | title-bar close, or template management's Close | `EXITED` | `root.destroy()` |
