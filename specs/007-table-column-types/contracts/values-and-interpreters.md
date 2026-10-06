# Contract: Value Reading and Interpreters

Pure code in `interpretation/`. No I/O and no UI (layers rule 3). Shapes are in
[../data-model.md](../data-model.md).

## `interpretation/value_types.py` (NEW)

Imports `DataSheetScalarType`, `DataSheetScalarDto`, and `TypedValue` from
`interpretation/student_data_sheet.py`. That module never imports this one, so there
is no import cycle.

```python
class ColumnType(Enum): TEXT, INT, DECIMAL, BOOLEAN, DATE, CHOICE, TALLY
FIELD_TYPES: tuple[ColumnType, ...]
COLUMN_TYPE_LABELS: dict[ColumnType, str]          # "Integer", "True/False", …

class ChoiceOption(NamedTuple): value: str; description: str = ""
class TallyOption(NamedTuple):  mark: str;  description: str = ""

class TallySummary(NamedTuple):
    marks: str; counts: dict[str, int]; total: int; percentages: dict[str, float | None]

class ValueReadError(ValueError):     expected: str; found: str = ""
class ValueProblem(NamedTuple):       section: str; item: str; row: str; value: str; expected: str
class InvalidValuesError(ValueError): problems: list[ValueProblem]
class OptionDescription(NamedTuple):  section: str; item: str; item_type: str; option: str; description: str

def read_value(column_type: ColumnType, text: str, choices: Sequence[ChoiceOption] = ()) -> TypedValue
def read_tally(text: str, options: Sequence[TallyOption]) -> TallySummary
def tally_keys(base: str, options: Sequence[TallyOption]) -> list[str]
def tally_scalars(base: str, summary: TallySummary, options: Sequence[TallyOption]) -> dict[str, DataSheetScalarDto]
def scalar_type_for(column_type: ColumnType) -> DataSheetScalarType   # not defined for TALLY
```

Behavior:

- `read_value`:
  - blank or whitespace text → `None` (FR-010)
  - `TALLY` → `ValueError`, because tallies use `read_tally`
  - text that doesn't fit → `ValueReadError(expected)` (FR-008, FR-009, FR-011)
- `read_tally`:
  - blank text → marks `""`, every count 0, total 0, every percentage `None`
  - spaces are ignored and marks are matched ignoring letter case; the result uses each
    mark as configured
  - a non-option character → `ValueReadError("only the marks Y, N, P", found="X")`, naming the
    first bad mark, so a Running Tally error can name the mark read (FR-021)
- `tally_keys` returns, in order: `base`, then `f"{base} {mark}"` for each option, then
  `f"{base} Total"`, then `f"{base} {mark} %"` for each option (R3).
- `tally_scalars` returns exactly the keys from `tally_keys`, typed TEXT / INT / INT /
  PERCENT.

## `interpretation/student_data_sheet.py` (CHANGE)

- Defines `TypedValue = int | float | bool | date | str | None`. It is defined here, not
  in `value_types.py`, so the dependency runs one way.
- `DataSheetScalarType` gains `DECIMAL` and `PERCENT`.
- `DataSheetScalarDto` becomes a `NamedTuple` with `typed_value: TypedValue = None` (R10).
- `StudentDataSheet.scalars` / `register_scalar` take `DataSheetScalarDto` only.

## `interpretation/templates/student_data_sheet_interpreter.py` (CHANGE)

```python
class SessionDataSectionInterpreterBase(ABC):
    def config_problems(self) -> list[str]: return []                  # NEW, overridable
    def option_descriptions(self) -> list[OptionDescription]: return [] # NEW, overridable
```

`StudentDataSheetInterpreter.interpret_student_data_sheet`:

- runs every section
- catches `InvalidValuesError` from each section and collects its problems
- after the last section, raises one `InvalidValuesError` with every problem, in section
  order, if there are any
- lets any other exception propagate at once, as today

## Interpreters (CHANGE)

| Interpreter | `section_keys()` | Emits | `config_problems()` | `option_descriptions()` |
| --- | --- | --- | --- | --- |
| `TableInterpreter(id, title, columns: list[ColumnDefinition])` | each column's name, or `tally_keys(name, options)` for Tally columns, in column order | one row per data row; a Tally column adds its `tally_scalars` to the row | names blank or duplicated; Choice/Tally with no options; duplicate or blank options; tally mark not 1 character; derived key equal to another column's name | every Choice and Tally column's options |
| `SimpleFormInterpreter(id, title, fields: dict[str, FieldConfiguration])` | field names (unchanged) | one `DataSheetScalarDto` per configured field present on the sheet (no longer raw `str`) | field type not in `FIELD_TYPES`; Choice with no options; duplicate or blank options | every Choice field's choices |
| `RunningTallyInterpreter(id, title, tally_options: list[TallyOption])` | `tally_keys("Tally", options)` | one row per table: `tally_scalars("Tally", read_tally(all marks in reading order))` | no options; duplicate options; mark not 1 character | every option, with item `""` |

All three:

- collect every `ValueReadError` into `ValueProblem`s (R5) and raise one
  `InvalidValuesError`
- still raise the existing exceptions for a missing column (FR-013) or a mismatched
  table (interpreters rule 9)
- create mutable state in `__init__` (interpreters rule 3), fixing the class-level
  attributes in `RunningTallyInterpreter` and `FieldConfiguration`

The column-presence check uses column names, not derived keys. A Tally column is one
column on paper.

## Serializers — `interpretation/template_manager/storage/serialization.py` (CHANGE)

They write the new shapes and read both the new and old shapes, as in R7 and
[../data-model.md](../data-model.md). `serialize(deserialize(old))` gives the new shape
with the same meaning. `deserialize(serialize(x))` equals `x`.

## `interpretation/template_manager/option_rules.py` (NEW, pure)

```python
def option_problems(item: str, column_type: ColumnType, values: Sequence[str]) -> list[str]
def name_problems(kind: str, names: Sequence[str]) -> list[str]          # blank or duplicate names
def tally_key_collisions(columns: Sequence[ColumnDefinition]) -> list[str]
def check_new_option(column_type: ColumnType, value: str, existing: Sequence[str]) -> str | None  # one message or None
```

Each message names the column or field and the rule, e.g.
`Column "Accuracy" needs at least one choice.`

## `interpretation/template_manager/template_rules.py` (CHANGE)

`validate_template(name, interpreters)` also appends each interpreter's
`config_problems()`, in template order (FR-005).

## Collection — `collection/images/aws_image_collection.py` (CHANGE)

In `_get_cell_text`, a `SELECTION_ELEMENT` child with `SelectionStatus == "SELECTED"`
adds `✓`, and `NOT_SELECTED` adds nothing (R9). Nothing else changes.
