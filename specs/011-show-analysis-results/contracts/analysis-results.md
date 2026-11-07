# Contract: Analysis Results

This contract covers four interfaces:

1. The pure results API
2. The interpreter methods it reads through
3. The Session Tab block
4. The Show as setting in the template window

## 1. Results API (`interpretation/analysis/results.py`, pure)

```text
work_out_results(sheet: StudentDataSheet) -> tuple[AnalysisResults, list[AnalysisProblem]]
```

`work_out_results` returns every calculation of `sheet.template.analysis`, worked out from
the sheet's tables and scalars, plus one problem per broken calculation that is shown or
that a shown calculation depends on.

- **Inputs**: only the sheet and its template. No I/O. The same sheet always gives the
  same results.
- **Calls**: `StudentDataSheetInterpreter.interpret_student_data_sheet` calls it last,
  and passes its output to `set_analysis_results`.
- **Never raises** for a well-formed sheet. A calculation that can't be worked out is
  broken (research R6), and never stops the sheet.
- **Each calculation's tree**, from which its result is evaluated (research R2):

  | Calculation | Tree |
  | --- | --- |
  | Formula | `parse_formula(text).structure` |
  | Menu Sum, Average, or Arithmetic | `parse_formula(menu_formula(d)).structure` |
  | Menu Each row | the `measure` of `parse_formula(f"SUM({menu_row_measure(d)})").structure`, once per row |

- **Meaning rules**: research R3.

```text
menu_row_measure(aggregate: RowAggregate) -> str      # interpretation/analysis/menu_formula.py
```

`menu_row_measure` returns the per-row expression that `menu_formula` writes inside SUM
or AVERAGE. For example, `COUNT("+", [Trials/Trial 1], [Trials/Trial 2])`.

## 2. Interpreter methods (optional; `interpreters.md` rule 12)

```text
analysis_sheet_value(value: str, tables: list[DataSheetTable], scalars: dict[str, DataSheetScalarDto]) -> TypedValue
analysis_row_value(row: dict[str, DataSheetScalarDto], column: str, part: str | None) -> TypedValue
```

- The base class returns `None` from both, so a type that doesn't opt in offers nothing.
- `value`, `column`, and `part` are matched ignoring letter case and surrounding spaces,
  the same way analysis names are matched everywhere else.
- `tables` are only the tables tagged with this section's id.
- The return is the Typed Value, or `None` for blank, unreadable, or missing.
- A Running Tally percentage is on the 0–100 scale.

## 3. Session Tab block (`storage/session_layout.session_rows`)

The block is written only when `sheet.analysis_results.has_shown`. Otherwise
`session_rows` returns exactly what it returns today.

| Row | Column A | Column B |
| --- | --- | --- |
| (existing rows, unchanged, ending with a blank row) | | |
| title | `Analysis Results` (text) | |
| one per shown single-number result | name (text) | value, or empty |
| blank, before each shown Row List | | |
| Row List name | name (text) | |
| Row List header | `Row` (text) | `Value` (text) |
| one per row of its table | row number, from 1 (whole number) | value, or empty |

The value cells, by the result's Show as (research R10):

| Show as | Whole result | Not whole |
| --- | --- | --- |
| Number | `int`, no format (`7`) | `float`, `DECIMAL` `0.0#` (`2.33`) |
| Percent | `result / 100`, `PERCENT` `0%` (`72%`) | `result / 100`, `PERCENT_DECIMAL` `0.0#%` (`66.67%`) |

## 4. Template window (Show as)

- **Editor panel** (edit mode and Create): a **Show as** combobox with `Number` and
  `Percent`.
  - Changes take effect on Apply, and are discarded on the editor's Cancel.
  - A new calculation's value follows `default_show_as` of the panel's choices until the
    SLP changes it.
  - An existing calculation keeps its value when its operation changes.
- **Calculation list** (view and edit mode): a Percent calculation's Kind reads, for
  example, `Arithmetic · %` or `Formula · %`. A Number calculation is unmarked. View mode
  is read-only.
- **Saved form**: `"show_as"` is written only when it differs from the default (research R9).

## Sheet Outcome

A broken calculation adds `AnalysisProblem.message()` to `SheetOutcome.warnings`, after
the value warnings. The status stays `SUCCEEDED`. A sheet with no broken calculation gets
exactly the outcome and message it gets today (SC-005).
