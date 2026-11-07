# Research: Show Analysis Results

Every decision below is grounded in the current code (features 005–010 and the two
analysis commits after 010). No NEEDS CLARIFICATION remains.

## R1. Results are worked out in Interpretation and carried on the sheet

- **Decision**: `StudentDataSheetInterpreter.interpret_student_data_sheet` works out the
  results as its last step, after every section has registered its tables and scalars. It
  stores them on the `StudentDataSheet` as `analysis_results`, with any broken-calculation
  warnings as `analysis_warnings`. Storage only reads them.
- **Rationale**: Interpretation is pure (layers.md rule 3), and only `StudentDataSheet`
  crosses into Storage (rule 1). The sheet already carries its template, so the results
  describe the template exactly as it was at import (spec: "Each Session Tab shows the
  results of the template as it was when the sheet was imported"). A duplicate sheet still
  gets results worked out, but `save()` writes nothing for it, as today.
- **Alternatives**: Working results out in `GoogleDriveDataSheetStore`, which would put
  business rules in Storage and repeat them in any other store. Working them out in
  `SheetImportBatch`, which would put them in the importing workflow rather than in
  interpretation, and leave sample-based offline checks needing the batch.

## R2. One evaluator, over the formula structure

- **Decision**: A new pure module, `interpretation/analysis/results.py`, evaluates
  `FormulaNode` trees (the `structure` that `parse_formula` already builds). Every
  calculation is turned into a tree first:
  - A Formula: `parse_formula(text).structure`.
  - A menu Sum, Average, or Arithmetic calculation: `parse_formula(menu_formula(definition)).structure`.
  - A menu Each row Row Aggregate: the `measure` node of
    `parse_formula("SUM(" + menu_row_measure(aggregate) + ")")`, evaluated once per row.
    This needs a new public `menu_row_measure(aggregate) -> str` in `menu_formula.py`,
    returning the per-row expression that `menu_formula` already writes inside SUM or AVERAGE.
- **Rationale**: 009 SC-006 says every menu calculation can be written as a formula, and
  the committed `menu_formula` does exactly that. Evaluating one representation means a
  menu calculation and the same calculation typed as a formula can never give different
  results. The parser was just shown to be unchanged by building the tree (31 cases).
- **Alternatives**: Two evaluators, one over the menu model and one over formulas, which
  doubles the meaning rules and lets them drift. Evaluating formula text directly, which
  would repeat the parser.

## R3. Numbers, empty values, and the meaning rules

- **Decision**: Values are `Decimal`, or `None` for an empty value. A typed value enters
  as `Decimal(str(value))`, and a fixed number from its digits. Results leave as `float`
  only when written to a cell (R10). The rules are those 009 fixed, plus what they imply:

  | Case | Result |
  | --- | --- |
  | Blank cell, Unreadable Value, or blank percentage | empty |
  | Rounded Value | the whole number it was saved as (its Typed Value) |
  | `+ - *`, negate, or a comparison, with an empty side | empty |
  | `/` (and the menu's percentage) by 0 | empty |
  | Comparison that holds or doesn't | 1 or 0 |
  | `SUM` | the sum of the rows' non-empty values; 0 when there are none |
  | `AVERAGE` | the mean of the rows' non-empty values; empty when there are none |
  | `COUNT(conditions…)` | how many hold; empty if any condition is empty |
  | `COUNT("choice", columns…)` | per row, how many columns hold the choice; a blank or unreadable cell holds none |
  | `[Table/Column] = "c"` / `<> "c"` | 1 or 0, ignoring letter case and surrounding spaces; a blank or unreadable cell holds no choice, so `=` gives 0 and `<>` gives 1 |
  | Tally count or total in a row | the Tally Summary's count; unknown marks are already left out |
  | True/False column against `"True"`/`"False"` | the cell's `bool`, compared by name |

- **Rationale**: Decimal keeps `0.1 + 0.2 = 0.3` true in comparisons, and keeps fixed
  numbers exact, as 009 saves them as strings. A blank holding no choice comes from 009
  (a blank cell "holds neither" `True` nor `False`, and adds 0 to a choice count).
- **Alternatives**: `float` throughout. It is simpler, but makes `=` comparisons
  unreliable.

## R4. Sections hand their values to analysis (interpreter contract)

- **Decision**: Two optional methods join `SessionDataSectionInterpreterBase`, beside
  `analysis_parts()`. Each returns nothing by default:
  - `analysis_sheet_value(value: str, tables: list[DataSheetTable], scalars: dict[str, DataSheetScalarDto]) -> TypedValue`.
    It gives one Numeric Sheet Value of this section on this sheet.
    - `SimpleFormInterpreter` returns the field's Typed Value.
    - `RunningTallyInterpreter` adds each option's count, and the total, across every
      tally table of the section. An option's percentage is that count ÷ total × 100,
      or `None` when the total is 0.
  - `analysis_row_value(row: dict[str, DataSheetScalarDto], column: str, part: str | None) -> TypedValue`.
    It gives one cell of a table row: a number column's value, a Choice cell's value, a
    True/False cell's `bool`, or a Tally column's count (`part` = a mark) or total
    (`part` = `Total`). `TableInterpreter` implements it with `tally_keys`.
  - Results reach a section's tables through the sheet's `section_id` tags, and its
    scalars through `sheet.scalars`.
- **Rationale**: Principle V. The results code never checks interpreter types, just as the
  scope code reads `analysis_parts()`. Each type keeps its own key conventions (`Attempts Y`,
  `Tally Total`) to itself. A Running Tally percentage on the 0–100 scale matches the menu's
  percentage and the Show as Percent display (R9). Adding a section's several tally tables
  gives one value per sheet, which a Numeric Sheet Value must be.
- **Alternatives**: Reading scalar keys directly in `results.py`, which would tie it to
  each interpreter type's key format. Keeping a Running Tally percentage as a 0–1 fraction,
  which would make `[Results/Y %] >= 70` wrong against a goal written as "70%".
- **Amendment**: This adds rule 12 to `interpreters.md` (a new optional contract), so it
  is a constitution MINOR bump (R13).

## R5. A table section's rows

- **Decision**: A table section's rows are every row of every table tagged with that
  section's id, in sheet order. A Row List has one value per such row, and Row List row
  numbers count from 1 across all of them. An aggregate's table is the section of its
  column references or its Row Lists. 009's checks already guarantee there is exactly one.
- **Rationale**: Spec edge case: "rows are measured across every table of that section,
  in sheet order". `_assign_tables` already gives every table to exactly one section.

## R6. Broken calculations

- **Decision**: Before evaluating, `results.py` runs the existing
  `rules.calculation_problems(...)` for each calculation, in layer order, against the
  sheet's template. A calculation with a problem is **broken**. A broken calculation, and
  every calculation that uses it directly or indirectly (through `result_references()`),
  gives an empty result. Every other calculation is worked out. Each broken calculation
  that is shown, or that a shown calculation depends on, becomes one `AnalysisProblem`:
  its name and the problem text the editor would show, for example
  `Calculation "Accuracy" can't be worked out: "Trials" has no column "Trial 4".`
- **Rationale**: FR-006a. Reusing the editor's checks means the warning names exactly what
  the template editor would have refused, in the same words.
- **Alternatives**: Catching evaluation errors, which would give vaguer messages and could
  hide real bugs. Failing the sheet, which the SLP rejected in clarification.

## R7. Hidden calculations are worked out too

- **Decision**: Every calculation is worked out. Results keep `shown`, so Storage writes
  only the shown ones.
- **Rationale**: FR-005 allows skipping unneeded hidden calculations, but skipping saves
  almost nothing on a sheet's worth of rows, and complicates dependency tracking.

## R8. Warnings in the Sheet Outcome

- **Decision**: `SheetImportBatch` adds `problem.message()` for each of
  `data_sheet.analysis_warnings` to the outcome's `warnings`, after the value warnings. It
  appends its own sentence to the message, e.g. `. 1 calculation can't be worked out: …`.
  An empty result from the sheet's values adds nothing (FR-010).
- **Rationale**: "Succeeded with warnings" already means `SUCCEEDED` with `warnings`
  (glossary), so the Import window needs no change.

## R9. Show as: model, default, and saving

- **Decision**:
  - A new `ShowAs` enum (`NUMBER`, `PERCENT`) in `model.py`. `Calculation` gains
    `show_as: ShowAs = ShowAs.NUMBER` as its last field, so existing constructor calls and
    `dataclasses.replace` keep working.
  - `default_show_as(definition)` returns `PERCENT` for an Arithmetic with
    `ArithmeticOperation.PERCENTAGE`, and `NUMBER` otherwise.
  - **Saving**: `"show_as": "PERCENT"` or `"NUMBER"` is written only when the value differs
    from `default_show_as` of the saved definition.
  - **Loading**: a missing key gives `default_show_as`. So a template saved before this
    feature loads with its menu percentages as Percent (FR-014b), and its saved bytes don't
    change while the SLP keeps the defaults.
  - **Editor**: a new calculation's Show as follows `default_show_as` of the panel's
    current choices until the SLP changes it. An existing calculation keeps its value when
    its operation changes (FR-014b).
- **Rationale**: Mirrors how `show_in_imported_sheets` is saved (010 R2). A value is
  written exactly when it would load differently without it, so the round trip is exact.
- **Alternatives**: Always writing `"show_as"`. That changes every saved template the
  first time it is saved, for no gain.

## R10. The Analysis Results block and its cells

- **Decision**: `session_rows` appends the block after the existing rows. They already
  end with a blank row, after the form fields or the last table, so FR-007's blank row is
  the existing one:

  ```text
  Analysis Results
  <name>            <value>          one row per shown single-number result, in order
  ...
  (blank)
  <Row List name>                     per shown Row List, in order
  Row               Value
  1                 <value>
  ...
  (blank)
  ```

  Cells:
  - Names, the title, and `Row`/`Value` are text cells. `_cell_payload` writes them as
    `stringValue`, which Sheets never parses (FR-013).
  - Row numbers are whole numbers.
  - An empty result is `EMPTY_CELL`.
  - A **Number** result that is whole is an `int` with no format. Otherwise it is a
    `float` with the new `CellNumberFormat.DECIMAL`, pattern `0.0#`.
  - A **Percent** result is written as its fraction (result ÷ 100), with
    `CellNumberFormat.PERCENT` (`0%`) when the result is whole, or the new
    `CellNumberFormat.PERCENT_DECIMAL` (`0.0#%`) otherwise. So `72` shows `72%`,
    `66.667` shows `66.67%`, and the cell holds `0.72`, Sheets' native percentage value.
  - `0.0#` shows up to 2 decimal places and keeps the full value in the cell (FR-014).
- **Rationale**: Existing tally percentages are already fractions with `0%`
  (`CELL_KIND_BY_TYPE`), so the SLP's own formulas treat both alike.
- **Alternatives**: Writing `72` with a literal `"%"` suffix pattern. The cell would then
  hold 72, unlike every other percentage in the workbook.

## R11. Show as in the template window

- **Decision**: The calculation editor panel gains a **Show as** combobox
  (`Number`, `Percent`) beside the existing Show in imported sheets check box. It takes
  part in Apply/Cancel through `_panel_calculation()`, like that box (010 R4). The
  calculation list marks a Percent calculation in its Kind column, e.g.
  `Arithmetic · %`, in view and edit mode alike. A Number one carries no mark (FR-014a).
- **Rationale**: Same placement and flow as the 010 setting, so there is one pattern for
  per-calculation settings.

## R12. Nothing else in the workbook changes

- **Decision**: No change to `WorkbookLayout`, `TemplateShape` / the Template Structure,
  the Workbook Key, tab naming, or duplicate detection. `moment_from_rows` reads only the
  header rows at the top, so rows added at the bottom can't affect it.
- **Rationale**: FR-012 and FR-017. Show as and the analysis are not part of the Template
  Structure (glossary).

## R13. Docs and the constitution

- **Decision**:
  - **Glossary**: add Calculation Result, Analysis Results (block), Show as, and Broken
    Calculation. Change Data Sheet Analysis to drop "Working out results is a later
    feature". Calculation gains Show as.
  - **`interpreters.md`**: new rule 12 for the R4 methods.
  - **Constitution**: 1.11.0 → 1.12.0 (MINOR: a new rule in a referenced doc, and glossary
    additions), with the Sync Impact Report.
  - **`FEATURE_IDEAS.md`**: remove "Work out calculation results for each imported
    sheet", which is now built.

## R14. Verification without a test framework

- **Decision**: Follow 007–010: scratch-script checks against a new synthetic sample,
  `therepy_sessions/sample_data/011/`. It holds a template file and Import JSON files with
  values worked out by hand in its README. The scripts check results, cells, and Sheet
  Outcome messages offline, including the "no shown calculations → identical rows" check.
  One manual Drive import confirms the block and number formats in a real Session Tab.
- **Rationale**: The project has no test framework (007 R11). Everything except the Sheets
  formatting itself can be checked offline, because Storage's rows are built by the pure
  `session_rows`.
