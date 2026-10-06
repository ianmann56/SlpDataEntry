# Research: Table Column Types

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-05

Each decision records what was chosen, why, and what else was considered. The Technical
Context in [plan.md](plan.md) has no open NEEDS CLARIFICATION items. These decisions
settle the design questions the spec left to planning.

## R1. One type enum for columns and fields, separate from the scalar type

**Decision**: Add a pure module `interpretation/value_types.py` that owns the
**Column Type**:

```python
class ColumnType(Enum):
    TEXT = "text"; INT = "int"; DECIMAL = "decimal"; BOOLEAN = "boolean"
    DATE = "date"; CHOICE = "choice"; TALLY = "tally"

FIELD_TYPES: tuple[ColumnType, ...]  # every ColumnType except TALLY: the Field Types
```

`DataSheetScalarType` (the type of one *emitted* value) stays separate and gains
`DECIMAL` and `PERCENT`. A column's type decides which scalars it emits: a Tally column
emits one `TEXT`, several `INT`, and several `PERCENT` scalars (R3).

**Rationale**:

- A Column Type describes what the SLP configured. A Scalar Type describes one value
  Storage writes. Tally breaks the one-to-one match between them, so one enum can't do
  both.
- The member names that already exist in saved templates (`TEXT`, `INT`, `CHOICE`,
  `DATE`, `BOOLEAN`, used by `SimpleFormInterpreter`'s `fieldType`) are kept, so old
  files load by name (R7).
- The Field Type is the same enum restricted to `FIELD_TYPES`, not a second enum, so
  one reader and one editor serve both (FR-028).

**Alternatives considered**: Reusing `DataSheetScalarType` for columns (it would need a
`TALLY` member that no value ever has). A separate `FieldType` enum (duplicates every
rule for no gain).

## R2. Reading values is pure and lives in one place

**Decision**: `value_types.py` holds every reading rule from FR-008 to FR-011:

- `read_value(column_type, text, choices) -> TypedValue` returns the typed value, or
  `None` for a blank cell. When the text doesn't fit, it raises
  `ValueReadError(expected)`, where `expected` is a phrase such as `"a whole number"`.
- `read_tally(text, options) -> TallySummary` reads a tally and always returns a summary.
  A blank cell gives no marks and zero counts. A mark that isn't an option raises
  `ValueReadError`.

The rules:

| Type | Accepted (after trimming, FR-011) | Typed value |
| --- | --- | --- |
| Text | anything, kept as read (not trimmed) | `str` |
| Integer | `[+-]?\d+`, or that followed by `.0…` | `int` |
| Decimal | optional sign, then digits with an optional decimal point and digits, or a decimal point and digits (`3`, `2.5`, `.5`) | `float` |
| True/False | true: `y yes t true 1 ✓ ✔ ☑`; false: `n no f false 0`; ignoring letter case | `bool` |
| Date | `M/D/YYYY`, `M/D/YY`, `M-D-YYYY`, `M-D-YY`; a two-digit year is `20YY` | `datetime.date` |
| Choice | equals a choice's value, ignoring letter case and surrounding spaces | the choice value as configured (`str`) |
| Tally | every non-space character equals an option's mark, ignoring letter case | `TallySummary` |

Thousands separators, `%`, units, and `X` in a True/False cell are all rejected (spec
Edge Cases, FR-009). Two-digit years are expanded by hand, because `strptime`'s `%y` puts
69–99 in the 1900s.

**Rationale**: One pure module can be checked offline with plain strings (layers rule 3)
and keeps every interpreter's reading the same (FR-028).

**Alternatives considered**: Parsing in each interpreter (three copies of the rules).
Parsing in Storage (Storage would decide meaning, which breaks layers rule 1, and a
failure would be found only after the sheet was accepted).

## R3. A Tally Summary is several keys, so the Template Structure follows the options

**Decision**: A Tally column, or a Running Tally section, contributes these keys to
`section_keys()`, in this order:

```
<base>                 marks in order, e.g. "YYNP"            TEXT
<base> <mark>          one count per option, option order    INT
<base> Total           number of marks                       INT
<base> <mark> %        one percentage per option              PERCENT (blank when Total is 0)
```

`<base>` is the column name for a Tally column, and the existing `"Tally"`
(`TALLY_COLUMN_NAME`) for a Running Tally section. A Running Tally section now emits one
row per table holding these keys, instead of one row per mark.

**Rationale**:

- Storage already writes every key as its own column and derives the Template Structure
  from `section_keys()` (interpreters rule 8). So adding, removing, or renaming a tally
  option, or switching a column to or from Tally, changes the structure (FR-017,
  FR-022), while every other type, choice, or description change does not. Storage
  needs no new tally logic.
- Running Tally templates change keys (`["Tally"]` → the expanded list), so their next
  session starts a new workbook and the old workbook is untouched (FR-022, US5-5).
- Templates without tallies keep exactly the same keys, so their workbooks are still
  found (SC-003). The fingerprint version (`s1`) is not bumped.

**Collision rule**: A derived key must not equal another column's name in the same
section (for example, a Text column literally named `Attempts Y`). `config_problems()`
(R8) reports it, naming both columns.

**Alternatives considered**: One cell holding `YYNP (Y=2, N=1, P=1)` (can't be totaled,
fails SC-006). Counting in Storage (Storage would need to know tally options, and the
structure wouldn't follow them).

## R4. Typed cells in the workbook

**Decision**: `storage/session_layout.py`'s `CellValue` grows from (text, number) to:

```python
class CellValue(NamedTuple):
    text: str | None
    number: int | float | None
    boolean: bool | None = None
    number_format: CellNumberFormat | None = None   # DATE or PERCENT
```

`cell_for` picks the cell from the scalar's `type` and its typed value:

| Scalar type | Cell |
| --- | --- |
| `INT`, `DECIMAL` | `numberValue` |
| `BOOLEAN` | `boolValue` |
| `DATE` | `numberValue` = days since 1899-12-30, format `DATE` pattern `m/d/yyyy` |
| `PERCENT` | `numberValue` = fraction (0.5), format `PERCENT` pattern `0%` |
| `TEXT`, `CHOICE` | `stringValue` |

`_cell_payload` writes `userEnteredFormat.numberFormat` when it's set, and
`_add_tab_requests` widens `fields` to `userEnteredValue,userEnteredFormat.numberFormat`.
A scalar with no typed value (anything built the old way) still writes its text, so
`cell_for` keeps its "never drop a value" rule.

**Rationale**: Native numbers, booleans, and dates can be sorted, totaled, and charted
without conversion (FR-014, SC-002). A serial number plus a date format is how the Sheets
API stores a real date without parsing user text. Percentages are kept exact and only
displayed rounded.

**Alternatives considered**: `USER_ENTERED` value input, so Sheets parses `"10/3/2026"`
(locale-dependent, and it could turn Text cells into formulas or dates). Storing
percentages as 0–100 numbers (they wouldn't format or chart as percentages).

## R5. Collect every bad value, then fail the sheet once

**Decision**:

- `value_types.py` defines `ValueProblem(section, item, row, value, expected)` and
  `InvalidValuesError(ValueError)`, which carries `problems: list[ValueProblem]`.
- Each interpreter reads every cell of its section, collects problems, and raises one
  `InvalidValuesError` at the end.
- `StudentDataSheetInterpreter` catches `InvalidValuesError` from each section, keeps
  going, and raises one combined error after the last section. Other errors (a missing
  column, an unmatched table) still raise at once, as today.
- `SheetImportBatch` maps it to a new `FailureReason.INVALID_VALUES`, with the message
  `Some values on the sheet don't fit template "{template_name}": {detail}. Fix the template, or retake the photo.`
  The detail lists every problem, separated by `; `, for example:
  `"Words", column "Trials", row 3: "l" is not a whole number`.

`row` is the 1-based data row under the header row. When a section received more than
one table, it is written `table 2, row 3`. A form field has no row. A Running Tally
problem names the section and the mark (FR-021).

**Rationale**: Lists every cell in one pass (spec Edge Cases, SC-004), keeps
interpretation pure, and fits the existing failure model: the sheet fails, nothing is
saved, and the other sheets in the run go on (FR-012).

**Alternatives considered**: Failing at the first bad cell (the SLP would need one retry
per cell). Saving the bad cell as flagged text (rejected in clarification Q1).

## R6. The Workbook Key comes from the template, through a generic member

**Decision**:

- `SessionDataSectionInterpreterBase` gains a public, non-abstract
  `option_descriptions() -> list[OptionDescription]` that returns `[]` by default.
  `OptionDescription(section, item, item_type, option, description)` lives in
  `value_types.py`.
- The Table, Simple Form, and Running Tally interpreters override it.
- `session_layout.workbook_key_rows(template) -> list[list[CellValue]]` builds the tab:
  a header row `Section | Column or Field | Type | Code | Meaning`, then one row per
  option in template order. If the template has none, a single row says
  `This template has no choice or tally codes to explain.`
- `GoogleDriveDataSheetStore` marks the key tab with sheet-level developer metadata
  `slpWorkbookKey` and names it `Workbook Key`, made unique if the SLP already has a tab
  with that name.
- Every save that writes a session tab also, in the same atomic `batchUpdate`, deletes
  the existing key tab (if any) and adds a new one at the end, along with its metadata.
  Creating a workbook adds it too. A save that finds the session already there writes
  nothing.
- The key tab is excluded by its metadata from duplicate detection (its A1:B6 has no
  `Date` label anyway), from empty-tab cleanup, and from tab ordering. With no Session
  Moment it already counts as oldest, so new session tabs are inserted before it.

**Rationale**:

- Storage still never checks interpreter types (interpreters.md). It only calls a public
  method every interpreter has.
- Rebuilding the tab is simpler and safer than diffing it. One batch means the tab is
  never half-written (FR-024, FR-025).
- A workbook created before this feature gets its key on the next save (spec Edge Cases).

**Alternatives considered**: Notes on column headers (rejected in clarification Q5).
Updating the key tab in place (would need clearing ranges and tracking sizes). Finding
the tab by its name alone (breaks if the SLP renames it).

**Privacy**: Descriptions describe the sheet layout and never identify a student (spec
Assumptions), so the key tab adds no student data. It goes only to Google Sheets, an
approved service.

## R7. Serialization: new shapes, old shapes still load

**Decision**: Each serializer writes the new shape and reads both the new and the old.

| Section | Old `config` | New `config` |
| --- | --- | --- |
| Table column | `{"column_name", "column_choices": [str]}` | `{"column_name", "column_type": "INT", "options": [{"value", "description"}]}` |
| Simple Form field | `{"name", "fieldType": "TEXT" \| null}` | `{"name", "fieldType": "INT", "options": [{"value", "description"}]}` |
| Running Tally | `{"tally_type", "tally_choice_options": [str]}` | `{"tally_options": [{"mark", "description"}]}` |

Loading rules:

- Table column: no `column_type` → `CHOICE` if `column_choices` is non-empty, otherwise
  `TEXT`. Old choices become options with blank descriptions (FR-018).
- Form field: a `null` or unknown `fieldType` → `TEXT` (FR-019).
- Running Tally: no `tally_options` → one option per string in `tally_choice_options`,
  with blank descriptions. `tally_type` is ignored, since the only form that ever wrote
  it wrote `CHOICE` (FR-023).

`tally` is a Table-only type. A form field saved as `TALLY` (it can't be configured, but
the file could be hand-edited) loads as `TEXT`.

An old option longer than one character (the old Running Tally form allowed any string)
still loads. `config_problems()` reports it, so the template can't be saved until it's
fixed. Before this feature such a tally could never be matched anyway, since the grid is
read one character at a time.

**Rationale**: Interpreters rule 4, SC-003, US4. Writing only the new shape keeps one
format going forward.

**Alternatives considered**: A file-wide format version with a migration step (the file
belongs to the SLP, and per-key fallbacks are enough here).

## R8. Configuration rules are pure; the editor is shared

**Decision**:

- **Rules**: `SessionDataSectionInterpreterBase` gains a public, non-abstract
  `config_problems() -> list[str]` (default `[]`). The Table, Simple Form, and Running
  Tally interpreters implement it using shared pure helpers in
  `interpretation/template_manager/option_rules.py`:
  - a Choice or Tally needs at least one option
  - options are unique ignoring case and surrounding spaces
  - a tally mark is exactly one character
  - an option value is not blank
  - column or field names are unique and not blank
  - Tally-derived keys don't collide with other names (R3)
- **Where the rules are enforced**:
  - `validate_template` appends every interpreter's `config_problems()`, so a template
    breaking them can't be saved (FR-005).
  - `TemplateForm._apply_form` refuses to apply a form whose built interpreter has
    problems, and shows them, alongside the existing duplicate-title check.
  - Adding an option in the editor checks length and duplicates at once (US3-2) by
    calling the same helpers.
- **Editors**: Two Tkinter widgets in `interpretation/template_manager/`:
  - `option_list_editor.py`, `OptionListEditor`: a two-column list (Code | Meaning)
    with value and description entries, and Add, Update, Remove, Up, and Down. It is
    used for Choice options, Tally options, Choice fields, and Running Tally sections
    (FR-002a, FR-020, FR-027).
  - `typed_item_editor.py`, `TypedItemEditor`: the list of columns or fields
    (Name | Type) with Add, Remove, Up, and Down. Below it is the selected item's detail:
    a name entry, a type picker limited to the allowed types, and the `OptionListEditor`
    when the type is Choice or Tally.
  - Changing the type of an item away from Choice or Tally, while it has options, asks
    to confirm and then clears them (spec Edge Cases).
- **Configs**: `TableInterpreterConfig` uses `TypedItemEditor` with all seven types.
  `SimpleFormInterpreterConfig` uses it with `FIELD_TYPES`. `RunningTallyInterpreterConfig`
  uses one `OptionListEditor` in tally-mark mode. Each `describe()` prints one line per
  column, field, or option, with types and descriptions, which view mode shows (FR-007).

**Rationale**:

- Layers rule 5: widgets collect input, and the rules live in pure code shared by the
  Create and Template Details windows through `TemplateForm` (feature 004's "share
  validation" direction).
- One option editor means one behavior to check (FR-002a).

**Alternatives considered**: Validation in widget callbacks (breaks layers rule 5). A
pop-up options window (rejected in clarification Q3).

## R9. Checkboxes in table cells become a checkmark

**Decision**: `collection/images/aws_image_collection.py`'s `_get_cell_text` also reads
`SELECTION_ELEMENT` children of a cell: `SELECTED` adds `✓`, and `NOT_SELECTED` adds
nothing. An unticked box therefore stays blank, which saves as empty (clarification:
blank True/False is never false).

**Rationale**:

- Textract reports a ticked box as a selection element, not a word. Today it's dropped,
  so a ticked checkbox column would read as blank and FR-009's checkmark could never
  arrive.
- Rendering a checkbox as a mark is normalization, not meaning (layers rule 2). The
  True/False reader decides what `✓` means.

**Alternatives considered**: Passing selection status as a separate structure (changes
the Import shape for one case).

## R10. Scalars become a typed record

**Decision**: `DataSheetScalarDto` becomes a `NamedTuple` (type-declarations rule 4):

```python
class DataSheetScalarDto(NamedTuple):
    key: str
    value: str                        # the text as read
    type: DataSheetScalarType
    choice_options: list[str] | None = None
    typed_value: TypedValue = None    # int | float | bool | date | str | None
```

`SimpleFormInterpreter` now emits `DataSheetScalarDto`s instead of raw strings, so
`StudentDataSheet.scalars` becomes `dict[str, DataSheetScalarDto]`. `cell_for` still
accepts a raw `str` for header values.

**Rationale**: The positional order and field names are unchanged, so existing callers
work. Typed values reach Storage without re-parsing.

## R11. How it is verified

**Decision**: Same approach as feature 005. There is no test framework.

- Offline scratch-script checks of the pure parts with synthetic strings:
  - `value_types` (every row of R2's table, every Edge Case)
  - each interpreter's `interpret_student_data_sheet_content`, `section_keys`,
    `config_problems`, and `option_descriptions`
  - serializer round trips, including old-shape JSON
  - `session_layout.cell_for` and `workbook_key_rows`
  - `template_structure` fingerprints before and after option changes
- `GoogleDriveDataSheetStore` with an in-memory fake Sheets service, checking the key
  tab's requests and exclusions.
- `SheetImportBatch` with a fake store, checking `INVALID_VALUES` messages.
- Live validation on synthetic sheets and a test Google account, per
  [quickstart.md](quickstart.md).

## R12. Documentation and constitution

**Decision**: In the same change:

- **Glossary**:
  - adds Column Type, Field Type, Choice Option, Tally Option, Tally Summary, and
    Workbook Key
  - updates Scalar Type to add `DECIMAL` and `PERCENT`
  - updates Template Structure to say that tally options count through their keys
  - updates Tally to mention Tally columns
- **`interpreters.md`**: the "Adding a new interpreter type" row adds
  `config_problems()` and `option_descriptions()`. A new rule 10 says values are read
  through `value_types` and that bad values are collected into one
  `InvalidValuesError`.
- **Constitution**: the Sync Impact Report is updated and the version goes 1.6.0 → 1.7.0
  (MINOR: new rules in a referenced doc).

**Rationale**: Principle II (new terms land with the change) and the constitution's
amendment procedure.
