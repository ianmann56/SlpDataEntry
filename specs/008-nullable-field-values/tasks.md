---

description: "Task list for the Nullable Field Values feature"
---

# Tasks: Nullable Field Values

**Input**: Design documents from `/specs/008-nullable-field-values/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md),
[contracts/lenient-values-and-outcomes.md](contracts/lenient-values-and-outcomes.md),
[quickstart.md](quickstart.md)

**Tests**: No automated tests. The spec doesn't ask for them. Research R9 makes
verification:

- offline scratch-script checks of `value_types`, the interpreters, and the sheet
  interpreter
- `SheetImportBatch` with a fake `DataSheetStore`
- `session_layout.cell_for` and `GoogleDriveDataSheetStore` with a fake Sheets service
- one live import from [quickstart.md](quickstart.md) on synthetic sheets and a test
  Google account

Scratch scripts are not committed.

**Organization**: Tasks are grouped by user story, in spec priority order.

- **US1 (P1)**: a value that doesn't fit its type no longer blocks the sheet, and a
  non-whole Integer is rounded.
- **US2 (P1)**: the text as read is kept in the workbook cell.
- **US3 (P2)**: the Sheet Outcome is *succeeded with warnings*, listing every value.
- **US4 (P2)**: stray tally marks are skipped, not fatal.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US4 from spec.md

## Path Conventions

- All code is under `therepy_sessions/`. Modules import each other by package path from
  that directory (e.g. `from interpretation.value_types import ValueReading`).
- **Types**: every public member added or changed is fully annotated per
  [type-declarations.md](../../docs/conventions/architecture/type-declarations.md).
- **One-way imports**: `interpretation/value_types.py` imports from
  `interpretation/student_data_sheet.py`, never the reverse. `student_data_sheet.py`
  imports `ValueProblem` only under `TYPE_CHECKING` (research R4).
- **Unchanged**: `storage/`, `collection/`, `students/`, `workspace/`, `program.py`, and
  template serialization (plan, contracts "Unchanged").
- **Privacy**: offline and live checks use only synthetic data and the made-up Student
  Key `ZZ`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Record the "before" state, so SC-005 (identical results for clean sheets)
can be proven later.

- [X] T001 With the code unchanged, run a scratch script from `therepy_sessions/` that interprets `sample_data/007/valid_all_types.json`, `sample_data/007/simple_form.json`, and `sample_data/007/running_tally.json` with the 007 three-section template (as described in `sample_data/007/README.md`), and writes every table row's and scalar's `(key, value, type, typed_value)` to `/tmp/interpretations-before-008.txt`. Also record `session_layout.cell_for` for each scalar of `valid_all_types`, for T026

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Lenient reading, the problem record, and the route problems take from an
interpreter to the `StudentDataSheet`. Every story builds on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 In `therepy_sessions/interpretation/value_types.py`:
  - add `saved_as: str = ""` as the last field of `ValueProblem`, document it, and make `message()` append `; saved as {saved_as}` when it is set (research R6)
  - add the `NamedTuple` `ValueReading(typed_value: TypedValue, expected: str = "", saved_as: str = "")` with a docstring giving the four states of data-model.md
  - add `read_value_leniently(column_type, text, choices=()) -> ValueReading`: call `read_value`. On `ValueReadError` for `ColumnType.INT`, if the trimmed text matches `_DECIMAL_PATTERN`, return `ValueReading(int(Decimal(trimmed).quantize(Decimal(1), rounding=ROUND_HALF_UP)), "a whole number", str(rounded))`; otherwise return `ValueReading(None, e.expected)`. Let the `ValueError` for TALLY propagate (research R1, R2, contracts)
  - import `Decimal` and `ROUND_HALF_UP` from `decimal`
  - leave `read_value` itself unchanged (FR-004)
- [X] T003 [P] In `therepy_sessions/interpretation/student_data_sheet.py`: add `self._value_warnings: list[ValueProblem] = []` in `__init__`, a `value_warnings` property returning a copy, and `add_value_warnings(problems: Sequence[ValueProblem]) -> None` (docstring: called by `StudentDataSheetInterpreter` only). Import `ValueProblem` under the existing `TYPE_CHECKING` block. Update the `TypedValue` comment and `DataSheetScalarDto.typed_value` docstring to say None also for an Unreadable Value. Make `debug()` print the warnings' messages (data-model.md)
- [X] T004 In `therepy_sessions/interpretation/templates/student_data_sheet_interpreter.py`: give `DataSheetInterpretationDto` a third field `value_problems` with `defaults=[()]`, and document it in the docstring above it (data-model.md)

**Checkpoint**: Lenient reading exists and the sheet can carry warnings. Nothing calls them yet.

---

## Phase 3: User Story 1 - A value that doesn't fit its type no longer blocks the sheet (Priority: P1) 🎯 MVP

**Goal**: Simple Form fields and non-tally table cells are read leniently. Unreadable
Values have no typed value, Rounded Values are whole numbers, and the sheet imports.

**Independent Test**: Interpret `sample_data/007/bad_values.json` (quickstart V3). The
table and form sections do not raise. Their bad cells have `typed_value=None`, and every
other value matches T001's record.

- [X] T005 [P] [US1] In `therepy_sessions/interpretation/interpreter_types/table_interpreter.py` `_interpret_single_student_data_sheet_table`: read every non-Tally cell with `read_value_leniently`. Always add the scalar, with `value=cell_text` and `typed_value=reading.typed_value`. When `reading.expected` is set, append `ValueProblem(section, column_name, row, cell_text, reading.expected, saved_as=reading.saved_as)`. Leave the Tally branch for T021. Drop `read_value` from the imports if it is no longer used
- [X] T006 [US1] In `therepy_sessions/interpretation/interpreter_types/table_interpreter.py` `interpret_student_data_sheet_content`: return `DataSheetInterpretationDto(tables, {}, problems)` instead of raising, and update the docstring (`:raises InvalidValuesError:` becomes a note that problems are returned; the missing-column `Exception` is unchanged, FR-014)
- [X] T007 [P] [US1] In `therepy_sessions/interpretation/interpreter_types/simple_form_interpreter.py` `interpret_student_data_sheet_content`: read each found field with `read_value_leniently`, always add its scalar (`value=text`, typed value from the reading), append `ValueProblem(section, field.name, "", text, reading.expected, item_kind="field", saved_as=reading.saved_as)` when `reading.expected` is set, and return the problems as the DTO's third field instead of raising. Remove the unused `InvalidValuesError`, `ValueReadError`, and `read_value` imports, and update the docstring. A field not on the sheet is still skipped with no problem
- [X] T008 [US1] In `therepy_sessions/interpretation/templates/student_data_sheet_interpreter.py` `interpret_student_data_sheet`: for each interpreter in template order, register its tables and scalars and call `data_sheet.add_value_warnings(interpretation.value_problems)`. Keep catching `InvalidValuesError` only from a section that still raises it (the Running Tally, until T022), re-raising after every section is read, so the sheet still fails rather than silently losing marks. Update the docstring and the comment about collecting bad values (contracts, research R4)
- [X] T009 [US1] Run quickstart V1 as a scratch script against `interpretation/value_types.py`: every `read_value_leniently` row of the table, including `7.5`→8, `2.5`→3, `-2.5`→-3, `7.4`→7, `7.0`→7 with no warning, and `read_value("7.5")` as Integer still raising `ValueReadError`
- [X] T010 [US1] Run quickstart V3's table and form checks with a scratch script: in `bad_values.json` row 2, `Trials` is `("l", None)`, `Done` `("X", None)`, `When` `("2/30/2026", None)`, `Accuracy` `("X", None)`; row 1 matches T001; `Prompts given` is `("abc", None)`. Then run V6: removing the `Accuracy` header from a copy of `valid_all_types.json` still raises from the interpreter (FR-014)

**Checkpoint**: Table and form sections never fail on a value. Running Tally marks still fail the sheet until US4.

---

## Phase 4: User Story 2 - Nothing the SLP wrote is lost (Priority: P1)

**Goal**: Every Unreadable Value's workbook cell holds the text as read, as plain text,
and a blank stays an empty cell. Research R7 shows storage already does this, so this
story is verification plus making that guarantee explicit.

**Independent Test**: Quickstart V5's cell checks: `cell_for` gives the text `N/A` for an
Unreadable Integer, and a fake Sheets service sees it written as `stringValue`.

- [X] T011 [US2] Read `therepy_sessions/storage/session_layout.py` `cell_for` and `therepy_sessions/storage/google_drive_data_sheet_store.py` `_cell_payload`, and confirm research R7: a scalar with `typed_value is None` and non-blank `value` becomes a text cell written as `userEnteredValue.stringValue`, and a blank one an empty cell. If either does not hold, fix it there and record the change in plan.md's Structure section; otherwise make no change to `storage/`
- [X] T012 [US2] Run quickstart V5's cell checks with a scratch script: `cell_for` on the `bad_values.json` row 2 scalars gives text cells `l`, `X`, `2/30/2026`, `X`; a blank cell gives an empty cell; and `GoogleDriveDataSheetStore` with a fake Sheets service writes `l` as `stringValue`. The Template Structure fingerprint for the 007 template is unchanged (FR-007)

**Checkpoint**: US1 + US2 together make leniency safe: no sheet fails on a value, and nothing written is lost.

---

## Phase 5: User Story 3 - The SLP is told which values didn't fit (Priority: P2)

**Goal**: A sheet saved with problems shows as *succeeded with warnings*, listing each
one, and counts as succeeded everywhere.

**Independent Test**: Quickstart V5's batch checks: `bad_values` is SUCCEEDED with its
warnings, `valid_all_types` is SUCCEEDED with none, and `totals()` counts one with
warnings.

- [X] T013 [US3] In `therepy_sessions/interpretation/importing/sheet_import_batch.py`: add `warnings: tuple[str, ...] = ()` as the last field of `SheetOutcome` (docstring: set only when SUCCEEDED; *succeeded with warnings* is SUCCEEDED with warnings), and `with_warnings: int` as the last field of `ListTotals` (also counted in `succeeded`) (data-model.md)
- [X] T014 [US3] In `therepy_sessions/interpretation/importing/sheet_import_batch.py` `_interpret`: after saving, build `warnings = tuple(problem.message() for problem in data_sheet.value_warnings)`. When there are any, append to the save message `. {N} value(s) didn't fit their type: {w1}; {w2}; …` (singular "value" for one), and set `warnings` on the outcome. Do this for `already_saved` too (contracts, research R5)
- [X] T015 [US3] In `therepy_sessions/interpretation/importing/sheet_import_batch.py` `totals()`: return `with_warnings` as the count of SUCCEEDED files whose outcome has warnings
- [X] T016 [P] [US3] In `therepy_sessions/interpretation/importing/import_window.py`: add a `"⚠ Succeeded with warnings"` status label and a `"warned"` row tag with an amber colour in `_TAG_COLORS` readable on light and dark sv-ttk (e.g. `#c98a00`). Choose the label and tag from the outcome (SUCCEEDED with warnings → warned) wherever a row's status text and tag are set. Leave the double-click and progress logic, which check `SheetStatus.SUCCEEDED`, unchanged
- [X] T017 [US3] In `therepy_sessions/interpretation/importing/import_window.py`: count this run's warned rows alongside `_run_succeeded` (reset with it), and make the summary read `This run: S succeeded (W with warnings), F failed · Whole list: …`, showing each `(W with warnings)` part only when W > 0, using `totals.with_warnings` for the whole list (contracts)
- [X] T018 [US3] Run quickstart V5's batch checks with a scratch script: `SheetImportBatch` with a fake student store (`ZZ`), the 007 template, a fake `DataSheetStore`, and `read_sheet` returning `bad_values` and `valid_all_types`. `bad_values` is SUCCEEDED, its `message` starts with the save message and lists every warning, `valid_all_types` has `warnings == ()` and its message is unchanged, `files_to_process()` is empty, and `totals()` gives `succeeded=2, with_warnings=1`

**Checkpoint**: Warnings reach the SLP. Running Tally marks are the last thing that can fail a sheet on a value.

---

## Phase 6: User Story 4 - Stray tally marks are skipped, not fatal (Priority: P2)

**Goal**: Unknown tally marks are left out of the counts and reported. The marks cell
keeps the text as read.

**Independent Test**: Quickstart V2, and V3's tally checks: `YQN` counts Y=1, N=1, total
2, marks cell `YQN`, with a warning naming `Q`; the Running Tally counts `Y` and skips `Z`.

- [X] T019 [US4] In `therepy_sessions/interpretation/value_types.py`: add `text_as_read: str = ""` and `unknown_marks: str = ""` to `TallySummary` and document them. Make `read_tally` never raise: collect each non-space character that is not an option into `unknown_marks` (as read, in order), count only recognised marks, and set `text_as_read=text`. Update its docstring (research R3)
- [X] T020 [US4] In `therepy_sessions/interpretation/value_types.py` `tally_scalars`: when `summary.unknown_marks` is set, the `base` scalar's `value` and `typed_value` are both `summary.text_as_read` (still TEXT). Otherwise unchanged. Update the docstring (FR-009, FR-010)
- [X] T021 [P] [US4] In `therepy_sessions/interpretation/interpreter_types/table_interpreter.py`, Tally branch: drop the `try`/`except`, always add `tally_scalars(...)`, and when `summary.unknown_marks` is set append `ValueProblem(section, column_name, row, cell_text, expected)` with `expected = f'made of only the marks {marks} ({named} is not one; left out of the counts)'`, where `named` quotes each distinct unknown mark (e.g. `"Q"`, or `"Q", "Z"` with "are not ones" wording kept grammatical) (research R6). Remove the now-unused `InvalidValuesError` and `ValueReadError` imports
- [X] T022 [P] [US4] In `therepy_sessions/interpretation/interpreter_types/running_tally_interpreter.py`: read each table without raising, and for each table append one `ValueProblem(section, "", where, mark, _marks_phrase-style expected)` per unknown mark (contracts: one per unknown mark, `row` = `"table N"` when there are several tables); return them as the DTO's third field. Remove the `InvalidValuesError` and `ValueReadError` imports and update the docstrings
- [X] T023 [US4] Run quickstart V2 and V3's tally checks with a scratch script: `read_tally("YQN")`, `"QZ"`, `"YyN P"` with options `Y N P` give the data-model.md results; `tally_scalars("Attempts", <YQN>)` has `"Attempts"` = `"YQN"` and `"Attempts Total"` = 2; `bad_values.json` row 2 `Attempts` is `"YQN"` with `Attempts Y`=1, `Attempts N`=1; the Running Tally total is 1; and `data_sheet.value_warnings` holds 7 problems in template order with R6's wording

**Checkpoint**: No value on a sheet can fail its import. Only layout mismatches still do (FR-014).

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Remove the dead failure path, add samples, amend the docs, and validate end to end.

- [X] T024 Remove `InvalidValuesError` from `therepy_sessions/interpretation/value_types.py`, its `try`/`except` from `therepy_sessions/interpretation/templates/student_data_sheet_interpreter.py` (and the `InvalidValuesError` import), and `FailureReason.INVALID_VALUES`, its `_FAILURE_MESSAGES` entry, its `except` branch, and its import from `therepy_sessions/interpretation/importing/sheet_import_batch.py`. Confirm with `grep -rn "InvalidValuesError\|INVALID_VALUES" therepy_sessions docs` that nothing else refers to them (data-model.md "Removed")
- [X] T025 [P] Create `therepy_sessions/sample_data/008/lenient_values.json` (same Import shape and Student Key `ZZ` as `sample_data/007/valid_all_types.json`, for the 007 template) with `7.5` and `N/A` in Trials, `QZ` in Attempts, and `-2.5` in Prompts given, and `therepy_sessions/sample_data/008/README.md` describing it and its expected outcome (quickstart V4). Update `therepy_sessions/sample_data/007/README.md` so `bad_values.json` succeeds with warnings naming the same seven values
- [X] T026 Run quickstart V4 with a scratch script, then re-run T001's script and diff it against `/tmp/interpretations-before-008.txt`: clean samples must be identical (SC-005)
- [X] T027 [P] Rewrite rule 10 of `docs/conventions/architecture/interpreters.md`: values are read through `read_value_leniently` / `read_tally`, every value that doesn't fit is kept (text as read, no typed value), and every Unreadable Value, Rounded Value, and unknown tally mark in a section is returned in `DataSheetInterpretationDto.value_problems` and shown as a warning, never failing the sheet and never silently dropped. Layout mismatches still raise (research R8)
- [X] T028 [P] Update `docs/domain/glossary.md`: add Unreadable Value and Rounded Value (spec Key Entities); Scalar / Typed Value is None for a blank or Unreadable Value; Sheet Outcome adds *succeeded with warnings*; Tally Summary leaves unknown marks out of the counts and its marks value is then the text as read (FR-016)
- [X] T029 Amend `.specify/memory/constitution.md` from 1.8.0 to 1.9.0: a new Sync Impact Report at the top for T027 and T028 (keeping 1.8.0's as "Previous report"), and Last Amended set to the change date (research R8)
- [ ] T030 Run quickstart V7 live with a test Google account and synthetic `ZZ` images: the warned row shows `⚠ Succeeded with warnings` in amber, the clean row `✓ Succeeded`, the summary reads `2 succeeded (1 with warnings), 0 failed`, the workbook holds the text cells, `=SUM()` skips them, and Import again re-imports neither row. **Needs the SLP/developer**: requires real credentials and the GUI
- [X] T031 Run the quickstart Docs check, and confirm no secrets, token files, or real student artifacts are staged (`git status`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none. Must run before any code change.
- **Foundational (Phase 2)**: after Setup. Blocks every story.
- **US1 (Phase 3)**: after Foundational.
- **US2 (Phase 4)**: after US1 (it checks the scalars US1 produces).
- **US3 (Phase 5)**: after Foundational; its checks (T018) need US1's warnings to be meaningful.
- **US4 (Phase 6)**: after Foundational. T021 edits the same file as T005/T006, so it follows US1.
- **Polish (Phase 7)**: T024 needs US1 and US4 (nothing may raise `InvalidValuesError`). T026 needs T025. T029 needs T027 and T028.

### User Story Dependencies

- **US1**: the MVP. Independent after Foundational.
- **US2**: verification of US1's scalars against unchanged storage.
- **US3**: independent of US2 and US4.
- **US4**: independent of US2 and US3; shares `table_interpreter.py` with US1.

### Within Each User Story

- `value_types.py` before the interpreters, interpreters before the sheet interpreter,
  the batch before the window, code before its scratch check.

### Parallel Opportunities

- T003 runs beside T002 (different files); T004 after T002 only for the import of `ValueProblem` names.
- US1: T005 and T007 (different interpreter files).
- US3: T016 (window) beside T013–T015 (batch), once the `SheetOutcome.warnings` shape is fixed.
- US4: T021 and T022, after T019–T020.
- Polish: T025, T027, and T028.

---

## Parallel Example: User Story 1

```text
Task: "T005 [US1] Lenient non-tally cells in interpretation/interpreter_types/table_interpreter.py"
Task: "T007 [US1] Lenient fields in interpretation/interpreter_types/simple_form_interpreter.py"
```

## Parallel Example: User Story 4

```text
Task: "T021 [US4] Tally cells report unknown marks in interpretation/interpreter_types/table_interpreter.py"
Task: "T022 [US4] Running Tally reports unknown marks in interpretation/interpreter_types/running_tally_interpreter.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 and 2)

1. Phase 1 (baseline) and Phase 2 (foundational).
2. US1: table and form values never fail the sheet.
3. US2: confirm the text as read reaches the workbook.
4. **Stop and validate**: quickstart V1, V3 (table and form), V5 (cells), V6.

### Incremental Delivery

1. MVP as above: the most common bad values (N/A, ?, unconfigured choices) import.
2. US3: the SLP sees *succeeded with warnings* and every value listed.
3. US4: tally marks join in; then Polish removes `InvalidValuesError` entirely.
4. Docs, constitution 1.9.0, and the live V7 check.

---

## Notes

- [P] tasks touch different files and have no dependency on incomplete tasks.
- Commit after each phase or logical group.
- Scratch scripts and `/tmp` baselines are never committed.
- Avoid: changing `storage/`, template serialization, or `section_keys()`; any of these
  would break FR-007, FR-015, or SC-005.
