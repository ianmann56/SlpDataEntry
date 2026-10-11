# Contract: Lenient Values and Import Outcomes

Signatures that change in this feature. Record shapes are in [data-model.md](../data-model.md).

## `interpretation/value_types.py`

```python
class ValueReading(NamedTuple):
  typed_value: TypedValue
  expected: str = ""
  saved_as: str = ""

def read_value(column_type: ColumnType, text: str, choices: Sequence[ChoiceOption] = ()) -> TypedValue
  # Unchanged strict rule. Still raises ValueReadError / ValueError (TALLY).

def read_value_leniently(column_type: ColumnType, text: str, choices: Sequence[ChoiceOption] = ()) -> ValueReading
  # Never raises ValueReadError. Raises ValueError for TALLY, as read_value does.
  # INT: a non-whole number that passes the Decimal rule → int rounded half away from zero,
  #      expected="a whole number", saved_as=str(rounded).
  # Any other text that read_value rejects → ValueReading(None, expected=<e.expected>).

def read_tally(text: str, options: Sequence[TallyOption]) -> TallySummary
  # Never raises. Unknown characters go to TallySummary.unknown_marks (R3).

def tally_scalars(base: str, summary: TallySummary, options: Sequence[TallyOption]) -> dict[str, DataSheetScalarDto]
  # Unchanged keys. When summary.unknown_marks is set, the `base` scalar holds
  # summary.text_as_read as both value and typed_value.

class ValueProblem(NamedTuple):
  ...                      # existing fields
  saved_as: str = ""
  def message(self) -> str  # + "; saved as {saved_as}" when set

# Removed: InvalidValuesError
```

## Interpreters (`interpretation/interpreter_types/*.py`)

`interpret_student_data_sheet_content(...) -> DataSheetInterpretationDto` **no longer
raises for values that don't fit**. It returns every value it read, including Unreadable
Values as scalars with `typed_value=None` and `value=<text as read>`, and lists every
problem in `value_problems`.

Layout errors are unchanged and still raise. For example, a missing expected column
still raises `Exception` from `TableInterpreter` (FR-014).

| Interpreter | Problem it reports |
| --- | --- |
| `TableInterpreter` | One `ValueProblem` per Unreadable or Rounded cell (`item_kind="column"`, `row` set). One per Tally cell with unknown marks (`value` = the cell text, with the unknown marks named in `expected`). |
| `SimpleFormInterpreter` | One per Unreadable or Rounded field (`item_kind="field"`, `row=""`) |
| `RunningTallyInterpreter` | One per unknown mark (`item=""`, `value` = the mark, `row` = `"table N"` when there are several tables) |

A future interpreter type follows the same contract (interpreters.md rule 10, as amended).

## `StudentDataSheetInterpreter.interpret_student_data_sheet`

The signature is unchanged. It **no longer raises `InvalidValuesError`**. It registers
every section's tables and scalars and calls `data_sheet.add_value_warnings(...)` with
each section's `value_problems`, in template order.

## `SheetImportBatch.process_file` → `ProcessedSheet`

- No `FailureReason.INVALID_VALUES` outcome.
- On a save, including `already_saved`: `SheetOutcome(SUCCEEDED, ..., warnings=tuple(p.message() for p in data_sheet.value_warnings))`.
- When there are warnings, `message` is `"{save message}. {N} value(s) didn't fit their type: {w1}; {w2}; …"`.
- `totals()` also returns `with_warnings`.

## Import window (`interpretation/importing/import_window.py`)

| Outcome | Status label | Row colour |
| --- | --- | --- |
| SUCCEEDED, no warnings | `✓ Succeeded` | green (as today) |
| SUCCEEDED with warnings | `⚠ Succeeded with warnings` | amber, readable on light and dark sv-ttk |
| FAILED | `✗ Failed` | red (as today) |

The run summary reads
`This run: S succeeded (W with warnings), F failed · Whole list: …`. The
`(W with warnings)` part appears only when W > 0.

Double-click to open, and re-processing, treat a warned row exactly like any succeeded
row.

## Unchanged

- `storage/` (R7)
- template serialization and the template editor (FR-015)
- `section_keys()` and the Template Structure (FR-007)
- `collection/`
- `program.py`
