# Quickstart: Show Analysis Results

These scenarios show the feature works.

- **V1–V7** run offline as scratch scripts against synthetic samples.
- **V8–V9** use the app.

Run scripts from `therepy_sessions/` with `PYTHONPATH=. ../.venv/bin/python <script>`.
Keep scratch scripts out of the repo.

## Prerequisites

`therepy_sessions/sample_data/011/` holds:

- **`analysis_templates.json`**: one synthetic template, "Trial results". It has:
  - a `Trials` table: `Word` (Text), `Trial 1`–`Trial 3` (Choice `+`, `-`), `Attempts`
    (Tally `Y`, `N`, `P`), and `Done` (True/False)
  - a `Session` Simple Form with `Target` (Integer)
  - a `Warm-up` Running Tally (`Y`, `N`)
  - an analysis covering every Row Measure, an Arithmetic percentage, a typed formula
    with Show as Percent, a hidden layer 1 step, and a shown Row List
- **`imports/*.json`**: Import files for that template:
  - `normal.json`
  - `blank_and_unreadable.json`: blank cells, `N/A`, `7.5`, and an unknown tally mark
  - `zero_trials.json`: every Average and division has nothing to work with
  - `two_tables.json`: the `Trials` section split over two tables
- **`README.md`**: every expected result, worked out by hand.

Every name is made up (Principle I).

## V1. Results match the hand-worked values (US1, SC-002)

1. Interpret each sample Import with the template.
2. Read `sheet.analysis_results`.

**Expect**:
- Every calculation's `value` or `rows` equals the README's.
- Sums over no values are 0.
- The Averages and the division in `zero_trials.json` are empty (`None`).
- In `two_tables.json`, the Row List spans both tables, numbered 1…n in sheet order.

## V2. A menu calculation and the same formula agree (R2)

For each menu calculation in the sample, build a Formula calculation from
`menu_formula(...)` and work out both on `normal.json`.

**Expect**: identical results.

## V3. The Session Tab block (FR-007–FR-015)

Call `session_rows(sheet, WorkbookLayout.from_shape(shape_of(template)))` for
`normal.json`.

**Expect**:
- Every row up to the existing trailing blank row equals `session_rows` for the same
  sheet with `AnalysisResults.none()`.
- After it:
  - the `Analysis Results` title
  - one row per shown single-number result in layer order, with no hidden calculation
    listed
  - each shown Row List as a name row, a `Row` / `Value` row, and numbered rows
- Cells:
  - Percent cells hold the fraction, with `PERCENT` or `PERCENT_DECIMAL`.
  - A whole Number result is an `int` with no format, and a non-whole one is a `float`
    with `DECIMAL`.
  - Empty results are `EMPTY_CELL`.
  - Every name is a text cell.

## V4. No shown calculations means no change (US2, FR-011, SC-003)

Build `session_rows` for `normal.json` with three variants of the template:

1. the template with its analysis removed
2. the same template with every calculation hidden
3. the template as it is in the committed 010 sample, `sample_data/010/analysis_templates.json`

**Expect**: the first two give identical rows, with no block. For the third, the rows
before the block match the rows for the same sheet with `AnalysisResults.none()`.

## V5. Broken calculations (FR-006a)

1. Copy the sample template.
2. In the copy's JSON, rename `Trial 3` in the formula of one layer 1 calculation to
   `Trial 4`. This is the hand-edit FR-006a describes.
3. Interpret `normal.json` with the copy.

**Expect**:
- That calculation, and every calculation using it, are empty, and the rest match the
  README.
- `sheet.analysis_warnings` holds one problem naming it and `Trial 4`.
- Run through `SheetImportBatch` with a fake store, the outcome is `SUCCEEDED`, and its
  warnings end with that message.

## V6. Outcomes are unchanged otherwise (FR-006, SC-005)

Run every Import in `sample_data/imports/` through `SheetImportBatch` with a fake store,
before and after the change.

**Expect**: identical statuses, messages, and warnings.

## V7. Show as is saved and loaded (FR-014a–c)

1. Load the sample template.
2. Save it with `analysis_to_json`.
3. Load the result again.

**Expect**:
- `show_as` round-trips.
- `"show_as"` appears only where it differs from `default_show_as`.
- The 010 sample, saved before Show as existed, loads with every calculation as Number
  (its Accuracy is a typed formula), and saves with no `"show_as"` key. A menu
  percentage saved earlier, such as "Test" in `sample_data/templates.json`, loads as
  Percent.

## V8. Template window (US3, FR-014a)

1. Open the sample template in edit mode.
2. Add an Arithmetic percentage.

**Expect**:
- Show as starts as Percent.
- Change the new calculation's operation to divide: Show as follows it to Number.
- Open the saved Accuracy and change its operation to divide: Show as stays Percent.
- Set a formula's Show as to Percent and press Apply: the list marks it `Formula · %`.
- Press Cancel on a changed Show as: the old value stays.
- In view mode, the marks show and nothing can be changed.

## V9. Real workbook (US1, US3)

Import a photographed synthetic sheet for a test student whose Current Template is the
sample template.

**Expect**:
- The new Session Tab shows the existing rows unchanged, a blank row, and the Analysis
  Results block.
- `72%`, `66.67%`, `7`, and `2.33` display as such.
- Clicking a percentage shows the fraction (for example `0.72`) in the formula bar.
- Earlier tabs and the Workbook Key are unchanged.
