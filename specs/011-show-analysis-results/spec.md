# Feature Specification: Show Analysis Results

**Feature Branch**: `011-show-analysis-results`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "As an SLP, I want to see the results of the analysis calculations on data sheets that I import so that I can infer patterns based on the data. Design: The results will be inserted into the saved data sheet located below the actual data imported in the data sheet."

## Clarifications

### Session 2026-11-06

- Q: How should a shown Row List appear in the Analysis Results block? → A: As its own small table below the single-number results, with one row per table row holding the row number and value.
- Q: When the SLP corrects a misread value in a Session Tab after import, should the results update? → A: No. Results are fixed values worked out at import; editing a cell does not change them.
- Q: How should a typed formula's result be displayed when it works out a percentage? → A: Each calculation gets a **Show as** setting (Number or Percent) in its editor. Menu percentage calculations default to Percent; every other calculation defaults to Number.
- Q: When a shown result comes out empty (e.g. Accuracy with 0 total trials), should the import warn? → A: No. The result cell is left empty and the Sheet Outcome is unchanged.
- Q: If a calculation can't be worked out at import (e.g. templates.json was edited by hand and it refers to a missing column), is the sheet still saved? → A: Yes. The broken calculation and every calculation that uses it, directly or indirectly, give empty results; the rest are worked out; the sheet succeeds with a warning naming each broken calculation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read a session's results in its Session Tab (Priority: P1)

The SLP's template has a Data Sheet Analysis: layer 1 holds "Correct trials" and "Total trials" (both hidden), and layer 2 holds "Accuracy", the percentage of one over the other. They import a photographed data sheet with that template. When they open the student's Student Session Workbook, the new Session Tab shows the sheet's header, form fields, and tables exactly as before, and below the last table an **Analysis Results** block lists "Accuracy" with its value, for example `72%`.

Today the SLP works this number out by hand, or with their own spreadsheet formulas, in every Session Tab. With this feature, every sheet they import carries its results, so they can compare sessions side by side and see patterns without doing the arithmetic.

**Why this priority**: This is the whole request. The calculations configured in features 009 and 010 do nothing for the SLP until their results appear with each imported sheet.

**Independent Test**: Build a template with one table section (a Tally column with options `Y`, `N`, `P`, and two Choice columns with `+` and `-`), two layer 1 Row Aggregates, and one layer 2 percentage. Import a synthetic sheet whose values are known, and confirm the Session Tab ends with an Analysis Results block holding each shown calculation's name and the value worked out by hand, below all the imported data, with the data above it unchanged.

**Acceptance Scenarios**:

1. **Given** a template with shown calculations, **When** a sheet is imported with it and saved, **Then** its Session Tab holds an Analysis Results block below all of the sheet's imported data, separated from it by a blank row.
2. **Given** the Analysis Results block, **When** the SLP reads it, **Then** it lists each shown calculation once, in layer order and, within a layer, in the template's order, with its name beside its result.
3. **Given** a hidden calculation that a shown calculation uses, **When** the sheet is imported, **Then** the hidden calculation's result is worked out and used, but does not appear in the block.
4. **Given** a Row Aggregate, Arithmetic, or Formula calculation, **When** its result is worked out, **Then** it follows the meaning fixed by feature 009: an Average skips rows with no value, a Sum over no values is 0, and an Average over no values, a division or percentage by 0, or any use of an empty result gives an empty result.
5. **Given** a calculation whose result is empty, **When** the block is written, **Then** the calculation's name is listed and its result cell is left empty.
6. **Given** a sheet with Unreadable Values or unknown tally marks, **When** its results are worked out, **Then** those values count as empty, and the sheet still imports (it already succeeds with warnings).

---

### User Story 2 - Sheets without shown results are unchanged (Priority: P1)

The SLP imports sheets with a template that has no analysis, or whose calculations are all hidden. Their Session Tabs look exactly as they did before this feature: no empty Analysis Results block, no extra rows.

**Why this priority**: The constitution requires saved templates to keep working (Principle V), and the SLP should never see clutter they didn't configure.

**Independent Test**: Import the same synthetic sheet with a template that has no analysis, and with a template whose calculations are all hidden. Confirm both Session Tabs match, cell for cell, a tab saved before this feature.

**Acceptance Scenarios**:

1. **Given** a template with no Analysis Layers, **When** a sheet is imported with it, **Then** its Session Tab holds no Analysis Results block and is otherwise unchanged.
2. **Given** a template whose every calculation is hidden, **When** a sheet is imported with it, **Then** its Session Tab holds no Analysis Results block.
3. **Given** an existing Student Session Workbook, **When** a new sheet with results is saved to it, **Then** the workbook is still found and used, and its earlier Session Tabs are not changed.

---

### User Story 3 - Read results in a useful form (Priority: P2)

The SLP reads each result the way they would write it: a percentage as a percentage, a count as a whole number, and an average with a sensible number of decimal places. A Row List (one value per row) is shown so the SLP can tell which row each value belongs to.

**Why this priority**: Story 1 already puts the right numbers in front of the SLP. Formatting makes them quicker to read and compare across sessions, but is not needed for them to be correct.

**Independent Test**: Import a sheet with a template holding a percentage, a Sum of a tally count, an Average, and a Row List. Confirm the percentage shows with a `%` sign, the Sum shows as a whole number, the Average shows rounded to at most 2 decimal places, and each Row List value can be matched to its table row.

**Acceptance Scenarios**:

1. **Given** a calculation whose Show as setting is Percent, **When** its result is written, **Then** its value is shown followed by `%` (a result of `72` shows as `72%`, and `66.667` as `66.67%`), and the cell still holds a number the SLP can use in their own spreadsheet formulas.
2. **Given** a Formula calculation such as `{Correct} / {Total} * 100`, **When** the SLP sets its Show as setting to Percent in the editor panel and presses Apply, **Then** sheets imported afterward show its result as a percentage.
3. **Given** a new Arithmetic calculation using percentage, **When** the SLP adds it, **Then** its Show as setting starts as Percent; **Given** any other new calculation, **Then** it starts as Number.
4. **Given** a Number result that is a whole number, **When** it is written, **Then** it is shown without decimals.
5. **Given** a Number result that is not a whole number, **When** it is written, **Then** it is shown rounded to at most 2 decimal places, while the cell keeps the full value.
6. **Given** a shown calculation whose result is a Row List, **When** the block is written, **Then** it appears as its own small table below the single-number results: a row with the calculation's name, a header row (`Row`, `Value`), and one row per row of its table, in sheet order, holding the row number (from 1) and that row's value, with an empty cell for an empty value.

---

### Edge Cases

- A template's analysis was changed after earlier sessions were saved: each Session Tab shows the results of the calculations the template had when that sheet was imported. Earlier tabs are not recalculated or rewritten.
- Sessions saved before this feature: they keep no Analysis Results block. Results are not added to them.
- The SLP edits a value in a Session Tab after import: the results in that tab do not change. They are the results of the sheet as read at import.
- A table section that produced no rows on this sheet: a Sum over it is 0 and an Average over it is empty, per feature 009.
- A table section that produced more than one table on this sheet: rows are measured across every table of that section, in sheet order.
- The template's analysis was edited outside the app and a calculation refers to a missing column: that calculation and every calculation using it are empty, the rest are worked out, and the sheet succeeds with a warning naming the broken calculation (FR-006a).
- A sheet that fails to import (Sheet Outcome *failed*): nothing is saved, so no results are worked out or written.
- A result so large or with so many decimals that it does not fit the cell: the cell keeps the full value; only its display is rounded.
- A calculation name that looks like a number or formula (e.g. `=Total` or `100`): it is written as plain text, never read as a number or a spreadsheet formula.
- A duplicate sheet (same Session Moment) that the existing duplicate rules skip: nothing is written for it, results included.
- A Row List calculation set to Percent: each of its row values is shown as a percentage.
- The SLP changes a calculation's Show as setting after sessions were saved: only sheets imported afterward follow the new setting.
- Two calculations in the same layer, one using the other: not possible; feature 009 lets a calculation use only lower layers.

## Requirements *(mandatory)*

### Functional Requirements

**Working out results**

- **FR-001**: When a sheet is imported and saved with a template that has a Data Sheet Analysis, the system MUST work out each calculation's result from that sheet's interpreted values (Typed Values and Tally Summaries), layer by layer, from layer 1 upward.
- **FR-002**: Results MUST follow the calculation meaning fixed by feature 009: an Average covers only rows whose measured value is not empty; a Sum over no values is 0 and empty values add nothing; an Average over no values, a division or percentage by 0, and any calculation using an empty result give an empty result; a Comparison gives 1 when it holds and 0 when it doesn't; `COUNT` gives how many of its conditions hold.
- **FR-003**: A blank value, an Unreadable Value, and an unknown tally mark MUST count as empty in every calculation. A Rounded Value MUST count as the whole number it was saved as.
- **FR-004**: A Formula calculation MUST be worked out according to its meaning, and MUST NEVER be run as code.
- **FR-005**: A Hidden Calculation MUST still be worked out whenever a shown calculation depends on it, directly or through other calculations. A hidden calculation that no shown calculation depends on MAY be skipped.
- **FR-006**: Working out results MUST NOT change whether a sheet imports successfully. A sheet that imports today MUST still import, with the same Sheet Outcome and warnings, except for the warning in FR-006a.
- **FR-006a**: A **broken calculation** is one that cannot be worked out because it refers to a section, column, field, choice, tally option, or calculation that the template no longer holds or no longer has the needed type (possible only when the template was changed outside the app). A broken calculation, and every calculation that uses it directly or indirectly, MUST give an empty result; every other calculation MUST be worked out as usual. The sheet MUST still be saved, and MUST succeed with a warning naming each broken calculation and what it refers to. A broken calculation that is hidden MUST be named too when a shown calculation uses it.

**Writing results**

- **FR-007**: When a template has at least one shown calculation, the sheet's Session Tab MUST end with an **Analysis Results** block, placed below all of the sheet's imported data (header, form fields, and every table) and separated from it by one blank row.
- **FR-008**: The Analysis Results block MUST begin with a title row reading "Analysis Results", followed by one row per shown single-number calculation: its name in the first column and its result in the second.
- **FR-009**: Calculations MUST be listed in layer order and, within each layer, in the order the template lists them. Hidden calculations MUST NOT be listed.
- **FR-010**: An empty result MUST be written as an empty cell beside the calculation's name. An empty result that comes from the sheet's values MUST NOT add a warning to the Sheet Outcome; only a broken calculation does (FR-006a).
- **FR-011**: When a template has no shown calculations (no analysis, or every calculation hidden), the Session Tab MUST NOT hold an Analysis Results block, and MUST be identical to what it would have been before this feature.
- **FR-012**: The rows above the Analysis Results block MUST be exactly what they would have been before this feature.
- **FR-013**: A calculation's name MUST be written as plain text, never read as a number, date, or spreadsheet formula.
- **FR-013a**: Results MUST be written as fixed values worked out at import, never as spreadsheet formulas. Editing a cell of the Session Tab afterward MUST NOT change any result.
- **FR-014**: Results MUST be written as numbers, so the SLP can use them in their own spreadsheet formulas. A result whose calculation's Show as setting is Percent MUST be shown as its value followed by `%`, without scaling it (a result of `72` is `72%`). A whole-number result MUST be shown without decimals, and any other result rounded to at most 2 decimal places, while the cell keeps its full value.
- **FR-014a**: Every calculation, menu or formula, MUST have a **Show as** setting, Number or Percent. In edit mode and when creating a template, the editor panel MUST let the SLP change it, taking effect on Apply and discarded on the editor's Cancel. View mode MUST show it read-only, and only when it is Percent. It MUST be saved with the template and restored when the template is opened again.
- **FR-014b**: A new Arithmetic calculation using percentage MUST start with Show as set to Percent; every other new calculation MUST start as Number. A calculation saved before this feature MUST be treated as Percent when it is an Arithmetic percentage, and as Number otherwise. Changing the operation of an existing calculation MUST NOT change its Show as setting.
- **FR-014c**: The Show as setting MUST change only how a result is displayed, never its value or how any calculation uses it, and MUST NOT change the template's Template Structure.
- **FR-015**: Each shown Row List MUST be written after every single-number result, in the same calculation order, as its own small table: a row holding the calculation's name, a header row (`Row`, `Value`), and one row per row of its table in sheet order, holding the row number (counted from 1 across every table of that section) and that row's value. An empty value MUST be an empty cell. Row Lists are separated from the single-number results and from each other by one blank row. Values follow the display rules of FR-014.

**Scope and compatibility**

- **FR-016**: Results MUST be worked out and written only when a sheet is saved. Session Tabs saved earlier MUST NOT be recalculated, rewritten, or given an Analysis Results block.
- **FR-017**: Adding results MUST NOT change how a Student Session Workbook is found or chosen, its Workbook Layout Order, its Session Tab names, or its Workbook Key.
- **FR-018**: Results and calculation names MUST be saved only to the student's Student Session Workbook through the Data Sheet Store, the same place as the sheet's other values. They MUST NOT be sent to any other service.
- **FR-019**: The new terms (**Calculation Result**, **Analysis Results** block, **Show as**, and **Broken Calculation**) MUST be added to the domain glossary, and the glossary's note that working out results is a later feature MUST be updated, as part of this feature.

### Key Entities

- **Calculation Result**: The value one calculation gives for one imported sheet: a number, an empty result, or (for a Row List) one value or empty per row of its table. Worked out at import from the sheet's interpreted values and the template's Data Sheet Analysis.
- **Calculation** (existing): Gains one setting, **Show as** (Number or Percent), which decides only how its result is displayed.
- **Analysis Results block**: The rows at the bottom of a Session Tab listing each shown calculation's name and result, in layer order. Written only when the template has a shown calculation.
- **Session Tab** (existing): Gains the Analysis Results block below its imported data. Nothing above the block changes.
- **Hidden Calculation** (existing): Worked out when needed, never listed in the block.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For 100% of imported sheets whose template has shown calculations, the SLP can read every shown result in the sheet's Session Tab without doing any arithmetic.
- **SC-002**: For a set of synthetic sheets with hand-worked expected results, 100% of shown results match the expected values, including empty results for averages over no values and divisions by 0.
- **SC-003**: 100% of Session Tabs saved with a template that has no shown calculations are identical, cell for cell, to the tabs saved before this feature.
- **SC-004**: The SLP can compare one result (such as Accuracy) across 5 sessions in under 1 minute, by finding it in the same place at the bottom of each Session Tab.
- **SC-005**: No sheet that imported successfully before this feature fails to import because of its calculations, and its Sheet Outcome changes only to add the broken-calculation warning of FR-006a.

## Assumptions

- "The saved data sheet" means the sheet's Session Tab in its Student Session Workbook, the only place an imported sheet is saved today.
- Results are fixed values (FR-013a), matching feature 009's rule that results come from interpreted values and formulas are never run as code. To get corrected results, the SLP deletes the session's tab and imports the sheet again (feature 005 skips a sheet whose tab still exists as a duplicate).
- Results are shown only in the Session Tab. The Import window and its Sheet Outcomes do not list results (an empty result adds no warning, FR-010; only a broken calculation does, FR-006a).
- Calculation Descriptions are not written to the Session Tab or the Workbook Key; the SLP can read them in the template's view mode. Adding them to the Workbook Key is a possible later change.
- Percent display assumes the result is already on a 0–100 scale, as feature 009's percentage operation and formulas like `{Correct} / {Total} * 100` give. A share from 0 to 1 (such as an Average of a Comparison) set to Percent would show as, for example, `0.72%`; the SLP multiplies by 100 in a formula to show it as a percentage.
- Each Session Tab shows the results of the template as it was when the sheet was imported. Because the Data Sheet Analysis is not part of the Template Structure, different tabs in one workbook may list different calculations.
- Historical Analysis (results across sessions) remains out of scope.
- Calculation names and results are template text and numbers; they never identify a student (feature 009, FR-021), so writing them to the workbook adds no new privacy concern beyond the values already saved there.
- Synthetic sample sheets under `therepy_sessions/sample_data/` are enough to verify results offline.
