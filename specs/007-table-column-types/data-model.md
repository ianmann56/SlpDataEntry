# Data Model: Table Column Types

**Feature**: [spec.md](spec.md) | **Research**: [research.md](research.md)

Every record below is public, so it is fully annotated (Principle VI). Names follow the
glossary terms this feature adds (Principle II).

## Template configuration (saved with the template)

### ColumnType (enum) — `interpretation/value_types.py`

`TEXT`, `INT`, `DECIMAL`, `BOOLEAN`, `DATE`, `CHOICE`, `TALLY`. The UI labels are Text,
Integer, Decimal, True/False, Date, Choice, and Tally.

- `FIELD_TYPES`: every member except `TALLY`. These are the allowed **Field Types**.
- `has_options(t)`: true for `CHOICE` and `TALLY`.

### ChoiceOption — `interpretation/value_types.py`

| Field | Type | Rules |
| --- | --- | --- |
| `value` | `str` | Not blank. Unique within its column or field, ignoring letter case and surrounding spaces. May be several characters (`NR`). |
| `description` | `str` | Optional (`""`). Free text that never identifies a student. |

### TallyOption — `interpretation/value_types.py`

| Field | Type | Rules |
| --- | --- | --- |
| `mark` | `str` | Exactly one character. Unique within its tally, ignoring letter case. |
| `description` | `str` | Optional (`""`). |

### ColumnDefinition — `interpretation/interpreter_types/table_interpreter.py` (changed)

| Field | Type | Rules |
| --- | --- | --- |
| `column_name` | `str` | Not blank. Unique within the section. Must not equal another column's Tally-derived key (R3). |
| `column_type` | `ColumnType` | Defaults to `TEXT`. |
| `choices` | `list[ChoiceOption]` | Non-empty when `CHOICE`. Empty otherwise. |
| `tally_options` | `list[TallyOption]` | Non-empty when `TALLY`. Empty otherwise. |

`column_choices: list[str]` stays as a read-only property returning the choice values,
for existing callers.

### FieldConfiguration — `interpretation/interpreter_types/simple_form_interpreter.py` (changed)

| Field | Type | Rules |
| --- | --- | --- |
| `name` | `str` | Not blank. Unique within the section. |
| `field_type` | `ColumnType` | One of `FIELD_TYPES`. Defaults to `TEXT`. |
| `choices` | `list[ChoiceOption]` | Non-empty when `CHOICE`. Empty otherwise. |

`fieldType` stays as a read-only alias of `field_type`, for existing callers.

### RunningTallyInterpreter (changed)

It replaces `tally_type` / `tally_choice_options` with `tally_options: list[TallyOption]`,
which must be non-empty. `tally_choice_options` stays as a read-only property returning
the marks.

### Saved JSON shapes

These are written by the serializers. The old shapes still load (R7).

```json
{"type": "TableInterpreter", "id": "…", "title": "Words", "config": {"columns": [
  {"column_name": "Word",     "column_type": "TEXT",   "options": []},
  {"column_name": "Trials",   "column_type": "INT",    "options": []},
  {"column_name": "Accuracy", "column_type": "CHOICE", "options": [{"value": "+", "description": "correct"}]},
  {"column_name": "Attempts", "column_type": "TALLY",  "options": [{"value": "Y", "description": "yes"}]}
]}}

{"type": "SimpleFormInterpreter", "id": "…", "title": "", "config": {"fields": {
  "Prompts given": {"name": "Prompts given", "fieldType": "INT", "options": []}
}}}

{"type": "RunningTallyInterpreter", "id": "…", "title": "", "config": {
  "tally_options": [{"mark": "Y", "description": "yes"}, {"mark": "N", "description": "no"}]
}}
```

Table options use `value` for both kinds, matching the shared editor. The Running Tally
section uses `mark`, because it only has tally options.

## Interpreted values (per sheet, never saved locally)

### DataSheetScalarType (enum, changed) — `interpretation/student_data_sheet.py`

`TEXT`, `INT`, `DECIMAL` (new), `CHOICE`, `DATE`, `BOOLEAN`, `PERCENT` (new).

### DataSheetScalarDto (now a `NamedTuple`)

| Field | Type | Meaning |
| --- | --- | --- |
| `key` | `str` | Column, field, or Tally-derived key. |
| `value` | `str` | The text as read (for derived tally keys, the formatted number). |
| `type` | `DataSheetScalarType` | How Storage writes it. |
| `choice_options` | `list[str] \| None` | Choice values, for Choice scalars. |
| `typed_value` | `int \| float \| bool \| date \| str \| None` | The typed value. `None` for a blank cell or a blank percentage. |

### Column Type → emitted scalars

| Column Type | Keys emitted | Scalar type(s) | `typed_value` |
| --- | --- | --- | --- |
| Text | `name` | TEXT | `str` as read |
| Integer | `name` | INT | `int` |
| Decimal | `name` | DECIMAL | `float` |
| True/False | `name` | BOOLEAN | `bool` |
| Date | `name` | DATE | `date` |
| Choice | `name` | CHOICE | the configured choice value |
| Tally | `name`, `name <mark>`…, `name Total`, `name <mark> %`… | TEXT, INT…, INT, PERCENT… | marks `str`; counts `int`; total `int`; fractions `float` (or `None` when total is 0) |

### TallySummary — `interpretation/value_types.py`

| Field | Type |
| --- | --- |
| `marks` | `str`, the configured marks in reading order, e.g. `"YYNP"` |
| `counts` | `dict[str, int]`, one entry per option in option order, including zero counts |
| `total` | `int` |
| `percentages` | `dict[str, float \| None]`, `count / total`, or `None` when `total == 0` |

### Bad values

| Record | Fields |
| --- | --- |
| `ValueProblem` | `section: str` (section title, or a fallback such as `Table`; always shown quoted), `item: str` (column, field, or `""`), `row: str` (`"row 3"`, `"table 2, row 3"`, or `""`), `value: str`, `expected: str` (`"a whole number"`, `"one of +, -, P"`, …) |
| `InvalidValuesError(ValueError)` | `problems: list[ValueProblem]`. `str()` joins every problem with `"; "`. |
| `ValueReadError(ValueError)` | `expected: str`, `found: str = ""` (the offending part of the text, such as the one bad tally mark; empty means the whole text). Raised by a single read, and turned into a `ValueProblem` by the interpreter. |

### OptionDescription — `interpretation/value_types.py`

| Field | Type | Example |
| --- | --- | --- |
| `section` | `str` | `"Words"` |
| `item` | `str` | `"Accuracy"` (`""` for a Running Tally section) |
| `item_type` | `str` | `"Choice"` or `"Tally"` |
| `option` | `str` | `"+"` |
| `description` | `str` | `"correct"` |

## Workbook output

### CellValue (changed) — `storage/session_layout.py`

| Field | Type |
| --- | --- |
| `text` | `str \| None` |
| `number` | `int \| float \| None` |
| `boolean` | `bool \| None` (new) |
| `number_format` | `CellNumberFormat \| None` (new): `DATE` (`m/d/yyyy`) or `PERCENT` (`0%`) |

Exactly one of `text`, `number`, or `boolean` is set, or none of them for an empty cell.

### Workbook Key tab

| Property | Value |
| --- | --- |
| Name | `Workbook Key`, made unique if the SLP already has a tab with that name |
| Found by | sheet-level developer metadata `slpWorkbookKey` |
| Position | last, after every Session Tab |
| Rows | header `Section \| Column or Field \| Type \| Code \| Meaning`, then one row per `OptionDescription` in template order. With no options, one row: `This template has no choice or tally codes to explain.` |
| Lifecycle | Added when a workbook is created. Deleted and re-added in the same batch as every new Session Tab. Untouched when a save finds the session already there. |
| Never | a Session Tab: no Session Moment, never a duplicate, never removed as empty |

### Structure effects (no change to the fingerprint algorithm)

| Change to a template | Keys change? | New workbook? |
| --- | --- | --- |
| A column or field's type between non-Tally types | no | no |
| Choices or any description | no | no |
| A column to or from Tally | yes | yes |
| Adding, removing, or renaming a Tally or Running Tally option | yes | yes |
| An existing Running Tally template, first save after update | yes (`Tally` → expanded) | yes (FR-022) |
| Templates with no tallies, first save after update | no | no (SC-003) |

## State transitions

Sheet outcome: `NOT_IMPORTED → FAILED(INVALID_VALUES)` when any value doesn't fit. From
there it is retried like any other failure (spec Assumptions). Nothing else changes.
