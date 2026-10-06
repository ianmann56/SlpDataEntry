# Contract: Template Configuration UI, Import Outcome, and Storage

## Configuration UI — `interpretation/template_manager/` (Tkinter shell, layers rule 5)

### `option_list_editor.py` (NEW)

```python
class OptionListEditor:
    def __init__(self, parent: tk.Misc, mode: ColumnType) -> None   # CHOICE or TALLY
    frame: ttk.Frame
    def get(self) -> list[tuple[str, str]]        # (value or mark, description), in order
    def set(self, options: Sequence[tuple[str, str]]) -> None
    def set_mode(self, mode: ColumnType) -> None
    def set_read_only(self, read_only: bool) -> None
```

- It is a Treeview with the columns **Code** and **Meaning**, plus code and meaning
  entries and **Add**, **Update**, **Remove**, **Up**, and **Down** buttons.
- Add and Update call `option_rules.check_new_option` and show its message instead of
  adding (US3-2). The widget holds no rules of its own.

### `typed_item_editor.py` (NEW)

```python
class TypedItem(NamedTuple): name: str; item_type: ColumnType; options: list[tuple[str, str]]

class TypedItemEditor:
    def __init__(self, parent: tk.Misc, item_label: str, allowed_types: Sequence[ColumnType]) -> None
    frame: ttk.Frame
    def get(self) -> list[TypedItem]
    def set(self, items: Sequence[TypedItem]) -> None
    def reset(self) -> None
```

- The top is a list of items with the columns **Name** and **Type**, and **Add**,
  **Remove**, **Up**, and **Down** buttons.
- The bottom shows the selected item: a name entry, a type picker (`allowed_types`, Text
  first and the default), and an `OptionListEditor` shown only for Choice or Tally
  (FR-002a, FR-027).
- Changing the type away from Choice or Tally while options exist asks to confirm, then
  clears the options (spec Edge Cases).

### `interpreter_configs.py` (CHANGE)

| Config | Form | `get_config()` | `construct_interpreter` | `describe()` lines |
| --- | --- | --- | --- | --- |
| `TableInterpreterConfig` | Title + `TypedItemEditor("Column", all 7 types)` | `{"title", "columns": list[TypedItem]}` | `ColumnDefinition`s from items | `Accuracy — Choice: + (correct), - (incorrect)`; `Trials — Integer` |
| `SimpleFormInterpreterConfig` | Title + `TypedItemEditor("Field", FIELD_TYPES)` | `{"title", "fields": list[TypedItem]}` | `FieldConfiguration`s, in order | `Prompts given — Integer` |
| `RunningTallyInterpreterConfig` | Title + `OptionListEditor(TALLY)` | `{"title", "tally_options": list[(mark, description)]}` | `RunningTallyInterpreter(id, title, [TallyOption…])` | `Tally options: Y (yes), N (no), P (prompted)` |

`load(interpreter)` fills each form from a saved interpreter, so every saved type,
option, and description round-trips through the form (interpreters rule 7 still
applies to untouched interpreters).

### `template_form.py` (CHANGE)

`_apply_form`:

- builds the interpreter as today, then checks `interpreter.config_problems()`
- if there are any, shows them (`messagebox.showerror("Fix the Section", …)`), returns
  `False`, and leaves the form open, exactly like a duplicate title

Auto-apply on select and Save (feature 004) inherits this behavior.

## Import outcome — `interpretation/importing/sheet_import_batch.py` (CHANGE)

- `FailureReason.INVALID_VALUES` (NEW), with the message
  `Some values on the sheet don't fit template "{template_name}": {detail}. Fix the template, or retake the photo.`
- In `_interpret`, `except InvalidValuesError` comes before the generic
  `except Exception`. `detail` is `str(error)`, which lists every problem, e.g.
  `"Words", column "Trials", row 3: "l" is not a whole number; "Words", column "Accuracy", row 5: "X" is not one of +, -, P`.
- Nothing is saved for that sheet, and the run goes on to the next file (FR-012).
  Messages name students only by Student Key, and cell values come from the sheet's data
  section, which never holds a name.

## Storage — `storage/session_layout.py` (CHANGE, pure)

```python
class CellNumberFormat(Enum): DATE = "date"; PERCENT = "percent"
class CellValue(NamedTuple):
    text: str | None; number: int | float | None
    boolean: bool | None = None; number_format: CellNumberFormat | None = None

def cell_for(value: DataSheetScalarDto | str | None) -> CellValue           # R4 table
def workbook_key_rows(template: StudentDataSheetTemplate) -> list[list[CellValue]]
WORKBOOK_KEY_TAB_NAME: str = "Workbook Key"
```

- `cell_for`:
  - `None` or a blank → `EMPTY_CELL`
  - `str` → text
  - a scalar with `typed_value is None` and non-blank `value` → text (never drops a
    value)
  - otherwise by `type`, as in R4. A `date` becomes its serial day number with
    `number_format=DATE`.
- `workbook_key_rows` reads only `interpreter.title`, `section_kind`, and
  `option_descriptions()` from `template.interpreters`, never interpreter types. An
  untitled section is labeled by its kind's display name.
- `session_rows` is unchanged: Tally-derived keys are ordinary keys.

## Storage — `storage/google_drive_data_sheet_store.py` (CHANGE)

- `_cell_payload`:
  - `boolean` → `{"userEnteredValue": {"boolValue": b}}`
  - `number_format` adds `"userEnteredFormat": {"numberFormat": {"type": "DATE", "pattern": "m/d/yyyy"}}`,
    or `{"type": "PERCENT", "pattern": "0%"}`
- `_add_tab_requests` writes with `fields: "userEnteredValue,userEnteredFormat.numberFormat"`.
- `KEY_TAB_METADATA_KEY: str = "slpWorkbookKey"`
- `_key_tab_requests(sheet_id, title, index, rows)`: `addSheet` + `updateCells` +
  `createDeveloperMetadata` (`location: {"sheetId": sheet_id}`, `visibility: DOCUMENT`).
- `_create_workbook`: one batch adds the session tab at 0 and the key tab at 1, deletes
  the default tabs, and stores the layout metadata.
- `_add_to_workbook`:
  - reads `sheets.developerMetadata` along with what it reads today
  - finds the key tab by metadata, and excludes it from the tab tops, duplicate
    detection, empty-tab removal, and the tabs `insert_index` sees
  - in the same batch as the new session tab, deletes the old key tab (if any) and adds
    a new one at the last index, with a fresh unique name
  - when the session is already saved, writes nothing, as today
- Every request stays in one atomic `batchUpdate`, so a failed save leaves neither a
  session tab nor a changed key (FR-002 of feature 005).

## Wiring

No change to `program.py`. The new modules are reached through existing constructors
(`STUB_INTERPRETER_CONFIGS`, the serializer registry, and the store).
