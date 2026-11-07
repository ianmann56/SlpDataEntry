---

description: "Task list for the Show Analysis Results feature"
---

# Tasks: Show Analysis Results

**Input**: Design documents from `/specs/011-show-analysis-results/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/analysis-results.md](contracts/analysis-results.md),
[quickstart.md](quickstart.md)

**Tests**: No automated tests. The spec doesn't ask for them, and research R14 makes
verification:

- offline scratch-script checks against `therepy_sessions/sample_data/011/`
  (quickstart V1–V7)
- a manual window check (V8)
- one real Drive import (V9)

Scratch scripts are not committed.

**Organization**: Tasks are grouped by user story.

- **US1 (P1)**: work out results on import, and write the single-number results to the
  Session Tab.
- **US2 (P1)**: sheets with no shown results are unchanged.
- **US3 (P2)**: results in a useful form: Show as, number formats, and Row Lists.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US3 from spec.md

## Path Conventions

- All code paths are relative to the repository root.
- Python modules live under `therepy_sessions/` and import from it (for example
  `from interpretation.analysis.model import Calculation`). Run scripts from
  `therepy_sessions/` with `PYTHONPATH=. ../.venv/bin/python`.
- Indentation: two spaces in `interpretation/analysis/`, `interpretation/interpreter_types/`,
  `interpretation/templates/`, and `interpretation/student_data_sheet.py`; four spaces in
  `interpretation/template_manager/`, `interpretation/importing/`, and `storage/`. Keep
  each file's style.
- Every new public member gets full type annotations (Principle VI).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: The synthetic sample every offline check reads.

- [X] T001 Create `therepy_sessions/sample_data/011/analysis_templates.json`: a templates
  file (same shape as `therepy_sessions/sample_data/templates.json`: `format_version`,
  `last_template_id`, `templates`) holding one synthetic template, "Trial results":
  - **Sections**:
    - a Simple Form section `Session` with `Target` (Integer)
    - a Running Tally section `Warm-up` with tally options `Y`, `N`
    - a Table section `Trials` with columns: `Word` (Text), `Trial 1`, `Trial 2`,
      `Trial 3` (Choice `+`, `-`), `Attempts` (Tally `Y`, `N`, `P`), `Score` (Integer),
      and `Done` (True/False)
  - **Analysis layer 1**:
    - `Correct trials`: Sum of the choice count of `+` over `Trial 1`–`Trial 3`
    - `Total trials`: Sum of the `Attempts` total, hidden
    - `Average score`: Average of `Score`
    - `Prompted per row`: Each row of the `Attempts` `P` count, a shown Row List
    - `Rows done`: Sum of the choice count of `True` over `Done`
    - `Rows at target`: Sum of the Comparison `Score` at least `[Session/Target]`
  - **Analysis layer 2**:
    - `Accuracy`: Arithmetic percentage of `Correct trials` over `Total trials`
    - `Accuracy (formula)`: Formula `{Correct trials} / {Total trials} * 100`, saved with
      `"show_as": "PERCENT"`
    - `Prompted total`: Sum of the Row result `Prompted per row`
    - `Warm-up share`: Formula `[Warm-up/Y %]`
  - Write it by building the objects and saving with `TemplateStore`, or by hand
    following `specs/009-data-sheet-analysis/data-model.md`. All names are made up
    (Principle I).
- [X] T002 [P] Create Import JSON files in `therepy_sessions/sample_data/011/imports/`, in
  the shape described in `therepy_sessions/sample_data/imports/README.md`. Header
  `form_data` uses Student Key `ZQ`. The `Trials` table's title is `Trials`, and the
  running tally table's title is `Warm-up`.
  - `normal.json`: 4 rows, every cell filled.
  - `blank_and_unreadable.json`: one blank `Score`, `N/A` in `Score`, `7.5` in `Score`,
    a blank `Trial 2`, and an unknown mark `X` in one `Attempts` cell.
  - `zero_trials.json`: no `Attempts` marks and no `Score` values, so the Averages and
    both accuracies are empty.
  - `two_tables.json`: the `Trials` rows split over two tables both titled `Trials`. If
    `_assign_tables` refuses two tables with one title, use a template variant with one
    table section, and note that in the README.
- [X] T003 Create `therepy_sessions/sample_data/011/README.md`:
  - what the files are, and that they are synthetic
  - a table of the template's calculations
  - for each Import, every calculation's expected result worked out by hand: single
    numbers, or Row List values row by row, and empty where 009's rules say so
  - the expected Session Tab cells for `normal.json` (quickstart V3)

  Depends on T001 and T002.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The model and interpreter contract every story builds on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 In `therepy_sessions/interpretation/analysis/model.py`:
  - Add `class ShowAs(Enum)` with `NUMBER = "Number"` and `PERCENT = "Percent"`.
  - Add `def default_show_as(definition: CalculationDefinition) -> ShowAs`. It returns
    `PERCENT` for an `Arithmetic` whose `operation is ArithmeticOperation.PERCENTAGE`, and
    `NUMBER` otherwise.
  - Add the field `show_as: ShowAs = ShowAs.NUMBER` as the last field of `Calculation`,
    and document it in the docstring: display only, never changes any result
    (data-model.md).
- [X] T005 [P] In `therepy_sessions/interpretation/templates/student_data_sheet_interpreter.py`,
  add two optional methods to `SessionDataSectionInterpreterBase` after `analysis_parts()`.
  Both return `None` by default.
  - `analysis_sheet_value(self, value: str, tables: list[DataSheetTable], scalars: dict[str, DataSheetScalarDto]) -> TypedValue`
  - `analysis_row_value(self, row: dict[str, DataSheetScalarDto], column: str, part: str | None) -> TypedValue`

  Write the docstrings from contracts/analysis-results.md §2. Names match ignoring letter
  case and surrounding spaces (use the `fold` rule from `interpretation/analysis/scope.py`,
  without creating an import cycle). Import `TypedValue` and `DataSheetTable` from
  `interpretation.student_data_sheet` the way the module already imports from it.
- [X] T006 [P] In `therepy_sessions/interpretation/interpreter_types/simple_form_interpreter.py`,
  override `analysis_sheet_value`. Find the field whose name matches `value`, ignoring
  case and spaces, among the Integer and Decimal fields. Return
  `scalars[field_key].typed_value` when present, else `None`. Depends on T005.
- [X] T007 [P] In `therepy_sessions/interpretation/interpreter_types/running_tally_interpreter.py`,
  override `analysis_sheet_value` (research R4):
  - For a mark `m`, add up each table's single row's `f"{TALLY_COLUMN_NAME} {m}"` typed
    value across `tables`.
  - For `Total`, add up `f"{TALLY_COLUMN_NAME} Total"`.
  - For `f"{m} %"`, return the summed count of `m` ÷ the summed total × 100 as a float, or
    `None` when the total is 0.
  - Return `None` for an unknown name, or when `tables` is empty.

  Match names ignoring case and spaces. Depends on T005.
- [X] T008 [P] In `therepy_sessions/interpretation/interpreter_types/table_interpreter.py`,
  override `analysis_row_value`. Find the configured column matching `column`, ignoring
  case and spaces.
  - **Tally column**: when `part` is a mark, return `row[f"{name} {mark}"].typed_value`.
    When `part` is `Total`, return `row[f"{name} Total"].typed_value`. Use the configured
    mark spelling, and the `tally_keys` naming in `interpretation/value_types.py`.
  - **Any other column**, with `part is None`: return `row[name].typed_value`.
  - Return `None` when the key is missing.

  Depends on T005.
- [X] T009 [P] In `therepy_sessions/interpretation/analysis/menu_formula.py`, add a public
  `menu_row_measure(aggregate: RowAggregate) -> str`. It returns
  `_measure(aggregate.measure, aggregate.section)`, the per-row expression `menu_formula`
  writes inside SUM or AVERAGE. Make `menu_formula` call it for Sum and Average, so the
  two can't diverge.

**Checkpoint**: Model, contract, and helper are ready. Existing behavior is unchanged
(nothing calls the new methods yet).

---

## Phase 3: User Story 1 - Read a session's results in its Session Tab (Priority: P1) 🎯 MVP

**Goal**: Every imported sheet's Session Tab ends with an Analysis Results block listing
each shown single-number calculation and its result. Broken calculations warn without
failing the sheet.

**Independent Test**: quickstart V1, V2, V3 (single-number rows), and V5.

- [X] T010 [US1] Create `therepy_sessions/interpretation/analysis/results.py` (pure, no
  I/O), with the NamedTuples from data-model.md:
  - `CalculationResult(name, layer, shown, show_as, value, rows, broken)`, with an
    `is_row_list` property
  - `AnalysisResults(results)`, with `shown_values`, `shown_row_lists`, `has_shown`, and a
    `none()` classmethod
  - `AnalysisProblem(calculation, problem)`, with `message()` returning
    `Calculation "<name>" can't be worked out: <problem>`
- [X] T011 [US1] In `therepy_sessions/interpretation/analysis/results.py`, implement the
  evaluator over `FormulaNode` trees (the node kinds are listed in `parse_formula`'s
  docstring in `interpretation/analysis/formula.py`), with the R3 rules. Use `Decimal` for
  values and `None` for empty.
  - **Sheet context**: build it once per sheet.
    - Map each Section Name, folded, to its interpreter, using `find_section` from
      `scope.py`.
    - Map each table section to its rows: every row of every `sheet.tables` entry whose
      `section_id` is that interpreter's `id`, in sheet order (R5).
    - Look up lower-layer results by folded name.
  - **Node rules**:
    - `number`: `Decimal(digits)`.
    - `result`: a single-number result's value. Inside an aggregate, a Row List's value
      for the current row.
    - `sheet_value`: `interpreter.analysis_sheet_value(value, that section's tables, sheet.scalars)`.
    - `column` inside an aggregate: when the section has `analysis_parts().table_columns`,
      use the current row's `analysis_row_value(row, column, part)`. Otherwise treat it
      as a `sheet_value`.
    - `arithmetic`, `negate`, `comparison`: as R3. A `/` by 0 gives `None`. A comparison
      with a `choice` side compares the cell's value, folded (a `bool` as `True`/`False`),
      with the choice. A blank or `None` cell holds no choice.
    - `aggregate`: find its table, the section of the first `column` node of a table
      section or of a Row List `result` inside it, and evaluate `measure` per row.
      - `SUM` adds the non-empty values (0 when none).
      - `AVERAGE` gives their mean, or `None` when none.
    - `choice_count`: per row, how many column cells hold the choice.
    - `count`: how many conditions are 1, or `None` if any is `None`.
  - **Converting typed values**: a `bool` is never a number; a `float`/`int` becomes
    `Decimal(str(v))`.
- [X] T012 [US1] In `therepy_sessions/interpretation/analysis/results.py`, implement
  `work_out_results(sheet: StudentDataSheet) -> tuple[AnalysisResults, list[AnalysisProblem]]`
  (contracts §1):
  - **Tree per calculation**:
    - `Formula`: `parse_formula(text).structure`.
    - Menu Sum, Average, or `Arithmetic`: `parse_formula(menu_formula(d)).structure`.
    - Each row: the `measure` node of `parse_formula(f"SUM({menu_row_measure(d)})").structure`,
      evaluated per row of `d.section` into `rows`.
  - **Broken calculations** (R6): run `rules.calculation_problems(calculation, interpreters, analysis, layer, index)`
    with the template's interpreters. Treat the name and duplicate checks as non-breaking:
    only reference problems break a calculation.
    - A calculation with problems, or whose `result_references()` name a broken
      calculation, is broken. Its value is `None`, or `rows=()` for a Row List.
    - Emit one `AnalysisProblem` per root broken calculation that is shown, or that a
      shown calculation depends on directly or through others. Use its first problem text.
  - **Order**: work out every calculation, hidden ones included (R7), in
    `analysis.all_calculations()` order.
  - Return `(AnalysisResults.none(), [])` for an empty analysis.

  Depends on T009–T011.
- [X] T013 [P] [US1] In `therepy_sessions/interpretation/student_data_sheet.py`, add:
  - an `analysis_results` property (default `AnalysisResults.none()`)
  - an `analysis_warnings` property (a copy of a list, default empty)
  - `set_analysis_results(self, results: AnalysisResults, warnings: Sequence[AnalysisProblem]) -> None`,
    documented as called by `StudentDataSheetInterpreter` only

  Import the result types under `TYPE_CHECKING` if needed to avoid a cycle, and create
  the default lazily.
- [X] T014 [US1] In `therepy_sessions/interpretation/templates/student_data_sheet_interpreter.py`,
  at the end of `interpret_student_data_sheet`, after the section loop, call
  `work_out_results(data_sheet)` and `data_sheet.set_analysis_results(...)`. Update the
  docstring's `:return:`. Import `work_out_results` inside the method if a module-level
  import would cycle. Depends on T012 and T013.
- [X] T015 [US1] In `therepy_sessions/interpretation/importing/sheet_import_batch.py`
  (around line 337), append `problem.message()` for each of
  `data_sheet.analysis_warnings` to `warnings`, after the value warnings. Append to
  `message`: `. N calculation(s) can't be worked out: <messages joined by "; ">`. Keep the
  existing value-warning sentence, and the `SheetOutcome` docstring, accurate. Depends on
  T013.
- [X] T016 [US1] In `therepy_sessions/storage/session_layout.py`:
  - Add the `ANALYSIS_RESULTS_TITLE: str = "Analysis Results"` constant.
  - Add a helper `result_cell(value: Decimal | None, show_as: ShowAs) -> CellValue`.
    For now, Number results only: `EMPTY_CELL` for `None`, `int` when whole, else `float`.
  - Extend `session_rows`: when `sheet.analysis_results.has_shown`, after the existing
    rows (which already end with a blank row), append the title row, then one
    `[CellValue(name, None), result_cell(...)]` row per `shown_values`.
  - Document the block in the docstring (research R10).

  Depends on T014.
- [X] T017 [US1] Run quickstart V1, V2, V3 (single-number rows), and V5 with scratch
  scripts against `therepy_sessions/sample_data/011/`. Fix any mismatch with the README's
  hand-worked values, in the code or in the README if the README is wrong.

**Checkpoint**: Importing a sheet writes shown single-number results below its data, and
broken calculations warn.

---

## Phase 4: User Story 2 - Sheets without shown results are unchanged (Priority: P1)

**Goal**: A template with no analysis, or with every calculation hidden, saves exactly the
tab it saved before. Sheet Outcomes are unchanged when nothing is broken.

**Independent Test**: quickstart V4 and V6.

- [X] T018 [US2] In `therepy_sessions/storage/session_layout.py`, confirm `session_rows`
  adds nothing at all, no title and no extra blank row, when `has_shown` is false. That
  covers no analysis, an empty analysis, and every calculation hidden. Note FR-011 in the
  docstring. Depends on T016.
- [X] T019 [US2] Run quickstart V4 and V6. Compare `session_rows` and the Sheet Outcomes
  for every Import in `therepy_sessions/sample_data/imports/` and
  `therepy_sessions/sample_data/011/imports/` with the pre-feature results. For the
  pre-feature results, use `git stash` or a worktree of commit `3b60a2d`. Any difference
  beyond the block must be fixed.

**Checkpoint**: US1 + US2 are the shippable MVP.

---

## Phase 5: User Story 3 - Read results in a useful form (Priority: P2)

**Goal**: Show as (Number or Percent) per calculation; percentages, whole numbers, and
2-decimal display; shown Row Lists as small tables.

**Independent Test**: quickstart V3 (formats and Row Lists), V7, and V8.

- [X] T020 [P] [US3] In `therepy_sessions/interpretation/analysis/serialization.py`, save
  `"show_as": calculation.show_as.name` only when
  `calculation.show_as is not default_show_as(definition)`. When loading, read
  `"show_as"` with `_member(ShowAs, ...)`, or `default_show_as(definition)` when it is
  missing. Update the module docstring (R9).
- [X] T021 [P] [US3] In `therepy_sessions/storage/session_layout.py`:
  - Add `CellNumberFormat.DECIMAL` and `CellNumberFormat.PERCENT_DECIMAL`.
  - Finish `result_cell` per contracts §3:
    - Number: an `int` when whole; else a `float` with `DECIMAL`.
    - Percent: `value / 100` as a `float`, with `PERCENT` when `value` is whole, else
      `PERCENT_DECIMAL`.
- [X] T022 [US3] In `therepy_sessions/storage/google_drive_data_sheet_store.py`, add the
  `_NUMBER_FORMATS` entries:
  - `DECIMAL`: `{"type": "NUMBER", "pattern": "0.0#"}`
  - `PERCENT_DECIMAL`: `{"type": "PERCENT", "pattern": "0.0#%"}`

  Depends on T021.
- [X] T023 [US3] In `therepy_sessions/storage/session_layout.py`, extend the block: after
  the single-number rows, for each of `shown_row_lists`, write:
  - a blank row
  - a row with the name
  - a `Row` / `Value` header row (text)
  - one row per value: the row number from 1 as an `int`, and
    `result_cell(value, show_as)`

  A broken Row List (`rows == ()`) writes only its name and header rows. Depends on T021.
- [X] T024 [US3] In `therepy_sessions/interpretation/template_manager/analysis_editor.py`,
  add the **Show as** combobox (`Number`, `Percent`) to the calculation panel next to
  `self._show_check` (around line 539). Wire it:
  - **`_panel_calculation()`** includes `show_as`, so Apply/Cancel and
    `has_unapplied_changes` work (010 R4).
  - **Filling the panel** sets it from the calculation.
  - **Enabling**: `_set_panel_enabled` enables and disables it with the check box.
  - **New calculation**: it follows `default_show_as` of the panel's current choices
    whenever the kind or operation changes, until the SLP picks a value. Track a
    `_show_as_touched` flag, reset on `_open_new` and `_load_panel`.
  - **Existing calculation**: its value never changes with the operation (FR-014b).
- [X] T025 [US3] In `therepy_sessions/interpretation/template_manager/analysis_editor.py`,
  mark Percent calculations in the list's Kind column in `_render` (around line 392), for
  example `f"{_kind_label(calculation)} · %"`, in view and edit mode alike. Number
  calculations are unmarked (FR-014a). Depends on T024.
- [X] T026 [US3] Run quickstart V3 (Percent and DECIMAL cells, Row List tables), V7, and
  V8 (window check in a scratch Workspace). V8 was run as a script driving the `AnalysisEditor` widget;
  looking at the real window is still to do.

**Checkpoint**: All user stories work on their own.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T027 [P] Update `docs/domain/glossary.md`:
  - Add **Calculation Result** (`CalculationResult`), **Analysis Results** (the Session
    Tab block), **Show as** (`Calculation.show_as`, `ShowAs`), and **Broken Calculation**
    (FR-019).
  - Calculation: it has a Show as setting.
  - Data Sheet Analysis: drop "Working out results is a later feature; today it is only
    configured."
  - Numeric Sheet Value: a Running Tally percentage is on the 0–100 scale.
- [X] T028 [P] Add rule 12 to `docs/conventions/architecture/interpreters.md`. Sections
  hand values to Data Sheet Analysis through the optional `analysis_sheet_value` and
  `analysis_row_value`: the results code never checks types, and an interpreter type that
  offers parts through `analysis_parts()` must also give their values. Update the
  "Adding a new interpreter type" section to match.
- [X] T029 Update `.specify/memory/constitution.md`: version 1.11.0 → 1.12.0, Last Amended
  2026-11-06, and a Sync Impact Report covering T027 and T028. Move the 1.11.0 report
  under "Prior history". Depends on T027 and T028.
- [X] T030 [P] In `FEATURE_IDEAS.md`, remove "Work out calculation results for each
  imported sheet" (now built), keeping Historical Analysis. Point to
  `specs/011-show-analysis-results/spec.md` where useful.
- [X] T031 Check every new or changed public member has type annotations (Principle VI),
  and that `interpretation/` imports nothing from `storage/` (layers.md rule 1).
- [ ] T032 Run quickstart V9: one real import to a synthetic test student in Drive.
  Confirm the block, the `72%`, `66.67%`, `7`, and `2.33` displays, and that earlier tabs
  and the Workbook Key are untouched. Confirm no real student data or token files are
  staged.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none. T003 needs T001 and T002.
- **Foundational (Phase 2)**: T005 blocks T006, T007, and T008. T004 and T009 are
  independent.
- **US1 (Phase 3)**: needs Phase 2. Order: T010 → T011 → T012 → (T013 ∥) → T014 → T015 and T016 → T017.
- **US2 (Phase 4)**: needs T016.
- **US3 (Phase 5)**: needs Phase 2 and T016. T020, T021, and T024 can start together.
- **Polish (Phase 6)**: after the stories it documents. T029 after T027 and T028.

### User Story Dependencies

- **US1**: the MVP core.
- **US2**: a guard and checks on US1's block.
- **US3**: builds on US1's block. The Show as UI and saving (T020, T024, T025) need only
  T004, and could ship before US1.

### Parallel Opportunities

- Phase 1: T001 ∥ T002.
- Phase 2: T004 ∥ T005 ∥ T009, then T006 ∥ T007 ∥ T008.
- US1: T013 ∥ T010–T012.
- US3: T020 ∥ T021 ∥ T024.
- Polish: T027 ∥ T028 ∥ T030.

## Parallel Example: Foundational

```text
Task: "T006 SimpleFormInterpreter.analysis_sheet_value in interpreter_types/simple_form_interpreter.py"
Task: "T007 RunningTallyInterpreter.analysis_sheet_value in interpreter_types/running_tally_interpreter.py"
Task: "T008 TableInterpreter.analysis_row_value in interpreter_types/table_interpreter.py"
```

## Parallel Example: User Story 3

```text
Task: "T020 show_as saving in interpretation/analysis/serialization.py"
Task: "T021 number formats and result_cell in storage/session_layout.py"
Task: "T024 Show as combobox in interpretation/template_manager/analysis_editor.py"
```

## Implementation Strategy

### MVP (US1 + US2)

1. Phase 1 (sample) and Phase 2 (model, contract, helper).
2. US1: the results engine, wiring, warnings, and block.
3. US2: the no-change guard and regression checks.
4. **Stop and validate**: V1–V6. Shown results now appear as plain numbers in every new
   Session Tab.

### Incremental Delivery

1. MVP → commit.
2. US3 → Show as, formats, and Row Lists → commit.
3. Polish → docs, the constitution, and the real Drive check → commit.
