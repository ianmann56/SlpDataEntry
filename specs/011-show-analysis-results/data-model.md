# Data Model: Show Analysis Results

Names follow the glossary (Principle II). Every new public member is typed (Principle VI).

## Changed: `Calculation` (`interpretation/analysis/model.py`)

| Field | Type | Notes |
| --- | --- | --- |
| `show_as` | `ShowAs` | New, last field, default `ShowAs.NUMBER`. Display only: never changes a result's value or how any calculation uses it, and is not part of the Template Structure (FR-014c). |

Renames, edits, and reordering keep it, because they use `dataclasses.replace`.

## New: `ShowAs` (`model.py`)

```text
class ShowAs(Enum):
  NUMBER = "Number"
  PERCENT = "Percent"

def default_show_as(definition: CalculationDefinition) -> ShowAs
  # PERCENT for an Arithmetic whose operation is ArithmeticOperation.PERCENTAGE, else NUMBER
```

## New: `CalculationResult` (`interpretation/analysis/results.py`)

One calculation's result for one imported sheet (the glossary's **Calculation Result**).

| Field | Type | Notes |
| --- | --- | --- |
| `name` | `str` | The calculation's name, as configured. |
| `layer` | `int` | Its Analysis Layer number. |
| `shown` | `bool` | `Calculation.show_in_imported_sheets`. |
| `show_as` | `ShowAs` | `Calculation.show_as`. |
| `value` | `Decimal \| None` | A single-number result, or `None` when it is empty. Always `None` for a Row List. |
| `rows` | `tuple[Decimal \| None, ...] \| None` | A Row List: one value per row of its table section (R5), `None` for an empty row. `None` when the result is a single number. A broken Row List has `()`. |
| `broken` | `bool` | Whether it couldn't be worked out because it, or a calculation it depends on, is broken (R6). |

Derived: `is_row_list: bool` (`rows is not None`).

## New: `AnalysisResults` (`results.py`)

| Field | Type | Notes |
| --- | --- | --- |
| `results` | `tuple[CalculationResult, ...]` | Every calculation, in layer order and then template order (`DataSheetAnalysis.all_calculations()`). |

Derived:
- `shown_values: list[CalculationResult]`: the shown single-number results, in order.
- `shown_row_lists: list[CalculationResult]`: the shown Row Lists, in order.
- `has_shown: bool`: whether either list is non-empty. When it is false, no block is written (FR-011).

`AnalysisResults.none()` is the empty value, for a template with no analysis.

## New: `AnalysisProblem` (`results.py`)

One broken calculation the SLP is warned about (FR-006a).

| Field | Type | Notes |
| --- | --- | --- |
| `calculation` | `str` | The broken calculation's name. |
| `problem` | `str` | What it refers to that is missing or mistyped: a message from `rules.calculation_problems`. |

`message() -> str` returns `Calculation "<name>" can't be worked out: <problem>`.

It is listed only when the calculation is shown, or when a shown calculation depends on it.

## Changed: `StudentDataSheet` (`interpretation/student_data_sheet.py`)

| Member | Type | Notes |
| --- | --- | --- |
| `analysis_results` | property → `AnalysisResults` | `AnalysisResults.none()` until set. |
| `analysis_warnings` | property → `list[AnalysisProblem]` | Empty unless a calculation is broken. |
| `set_analysis_results(results, warnings)` | method → `None` | Called once, by `StudentDataSheetInterpreter` only, after every section is read. |

## Changed: `SessionDataSectionInterpreterBase` (contract, R4)

| Member | Default | Overridden by |
| --- | --- | --- |
| `analysis_sheet_value(value, tables, scalars) -> TypedValue` | `None` | `SimpleFormInterpreter` (a field's Typed Value); `RunningTallyInterpreter` (summed counts or total over its tables; a percentage = count ÷ total × 100, `None` when the total is 0) |
| `analysis_row_value(row, column, part) -> TypedValue` | `None` | `TableInterpreter` (a number, choice, or True/False cell's Typed Value; a Tally column's count for `part` = a mark, or its total for `part` = `Total`) |

## Changed: `CellNumberFormat` (`storage/session_layout.py`)

| Member | Sheets pattern | Used for |
| --- | --- | --- |
| `DECIMAL` (new) | `NUMBER`, `0.0#` | A Number result that isn't whole |
| `PERCENT_DECIMAL` (new) | `PERCENT`, `0.0#%` | A Percent result that isn't whole |
| `PERCENT` (existing) | `PERCENT`, `0%` | A whole Percent result, and tally percentages as today |

## Saved form (`templates.json`)

The only change is one optional key per calculation:

```json
{"name": "Accuracy", "kind": "formula", "formula": "{Correct} / {Total} * 100", "show_as": "PERCENT", ...}
```

- `"show_as"` is written only when it differs from `default_show_as` (R9). A missing key
  loads as `default_show_as`.
- `FORMAT_VERSION` doesn't change.

## Session Tab (Student Session Workbook)

The rows above the block don't change (FR-012). The block's layout is in
[contracts/analysis-results.md](contracts/analysis-results.md).

## Lifecycle

```text
template saved (with analysis) ──sheet imported──▶ sections read (pure)
  ──▶ results worked out (pure, R1–R6) ──▶ StudentDataSheet.analysis_results / analysis_warnings
  ──▶ DataSheetStore.save: session_rows + Analysis Results block (skipped for a duplicate)
  ──▶ SheetOutcome: succeeded, with value warnings + broken-calculation warnings
```

Results are never stored anywhere else, and never recalculated later (FR-016).
