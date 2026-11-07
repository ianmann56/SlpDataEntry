# Implementation Plan: Show Analysis Results

**Branch**: `011-show-analysis-results` (work happens on `master`) | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/011-show-analysis-results/spec.md`

## Summary

When a sheet is imported, the app works out every Data Sheet Analysis calculation from
the sheet's values. It writes the shown results in an **Analysis Results** block at the
bottom of the sheet's Session Tab.

- **Where.** Results are worked out in Interpretation, as the last step of
  `StudentDataSheetInterpreter`, and carried on the `StudentDataSheet` (R1). Storage only
  lays them out.
- **How.** A new pure module, `interpretation/analysis/results.py`, evaluates the
  `FormulaNode` trees that `parse_formula` already builds (R2):
  - a formula's own tree
  - a menu calculation's tree, through the committed `menu_formula`
  - an Each row aggregate's per-row measure

  One evaluator means a menu calculation and the same formula always agree. Values are
  `Decimal`, `None` is empty, and 009's meaning rules apply (R3).
- **Reading the sheet.** Two optional interpreter methods, `analysis_sheet_value` and
  `analysis_row_value`, hand values to analysis, so the results code never checks
  interpreter types (R4). This is `interpreters.md` rule 12.
- **Broken calculations.** They are found with the editor's own `calculation_problems`.
  They and every calculation that depends on them are empty, the rest are worked out, and
  the Sheet Outcome warns (R6, R8).
- **Show as.** `Calculation.show_as` (`ShowAs.NUMBER` / `PERCENT`) is set in the editor
  panel and marked in the calculation list. It is saved only when it differs from
  `default_show_as` (R9, R11).
- **Session Tab.** `session_rows` appends the block: names as text, numbers as numbers.
  Percentages are written as fractions with a `%` format. Non-whole numbers use a
  2-decimal format. Nothing above the block changes, and nothing is written when no
  calculation is shown (R10, R12).
- **Docs.** Four glossary terms, `interpreters.md` rule 12, constitution 1.11.0 → 1.12.0,
  and `FEATURE_IDEAS.md` (R13).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: The existing stack: Tkinter + `sv-ttk`, and
`google-api-python-client` for Sheets. No new dependency. `decimal` is in the standard
library.

**Storage**:

- **`templates.json`**: one optional `"show_as"` key per calculation whose Show as isn't
  its default. `FORMAT_VERSION` stays 2.
- **Session Tabs**: new rows at the bottom of new tabs only. No change to workbook
  lookup, the Workbook Layout Order, the Template Structure, the Workbook Key, or
  `students.json`.

**Testing**:

- Offline scratch-script checks against a new synthetic sample,
  `therepy_sessions/sample_data/011/` (quickstart V1–V7).
- A manual window check (V8) and one real Drive import (V9).
- No test framework (007 R11).

**Target Platform**: Desktop (Linux primary; any OS that runs Tkinter).

**Project Type**: Desktop app (single project under `therepy_sessions/`).

**Performance Goals**: No noticeable change to an import. A sheet has tens of rows and a
template a handful of calculations, so evaluation is negligible next to OCR and the
Sheets calls. The block adds no API call: its rows go in the existing tab-writing
`batchUpdate`.

**Constraints**:

- Interpretation stays pure.
- Formulas are evaluated as trees, never run as code (FR-004).
- Rows above the block are byte-for-byte unchanged (FR-012).
- Templates saved earlier load and save unchanged while their defaults are kept.

**Scale/Scope**:

- 1 new module (`results.py`).
- 1 new function in `menu_formula.py`.
- Small changes to `model.py`, `serialization.py`, `student_data_sheet.py`, the sheet
  interpreter, 3 interpreter types, `session_layout.py`, the Drive store's format table,
  `sheet_import_batch.py`, and `analysis_editor.py`.
- 1 sample folder, and doc updates.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How this plan complies | Status |
| --- | --- | --- |
| I. Student Data Privacy | Results and calculation names go only to the student's own Student Session Workbook through the Data Sheet Store (FR-018). Names are template text (009 FR-021). No new service. The samples are synthetic. | ✅ Pass |
| II. Domain Language Fidelity | The new terms (Calculation Result, Analysis Results, Show as, Broken Calculation) are added to the glossary in this change. Code uses the same names (`CalculationResult`, `AnalysisResults`, `ShowAs`, broken). | ✅ Pass |
| III. Layered Pipeline | Results are worked out in Interpretation (pure, no I/O) and cross into Storage only on the `StudentDataSheet` (R1). Storage only lays out cells. The editor's Show as control holds no rules: `default_show_as` lives in the model. | ✅ Pass |
| IV. Injected External Services | No new client. The block is part of the existing tab write. | ✅ Pass |
| V. Pluggable Interpreters & Templates | Sections hand values over through two new optional methods, and the core never checks types (R4, `interpreters.md` rule 12, an amendment). Templates saved earlier stay loadable: `"show_as"` is optional and defaulted (R9). A sheet that doesn't match its template still fails as before. A broken calculation warns but never fails the sheet, which is the clarified behavior, not a template mismatch. | ✅ Pass (`interpreters.md` amended, R13) |
| VI. Typed Public Interfaces | Every new public member is annotated: `ShowAs`, `default_show_as`, `CalculationResult`, `AnalysisResults`, `AnalysisProblem`, `work_out_results`, `menu_row_measure`, the interpreter methods, the `StudentDataSheet` members, and the new `CellNumberFormat` members. The DTOs are NamedTuples. | ✅ Pass |

**Post-design re-check**: Unchanged. The design adds no layer crossing, client, or
untyped DTO. The one amendment (`interpreters.md` rule 12, constitution MINOR bump) is
part of this feature (R13).

## Project Structure

### Documentation (this feature)

```text
specs/011-show-analysis-results/
├── plan.md                       # This file
├── research.md                   # Phase 0: decisions R1–R14
├── data-model.md                 # Phase 1: entities and saved form
├── quickstart.md                 # Phase 1: validation scenarios V1–V9
├── contracts/
│   └── analysis-results.md       # Phase 1: results API, interpreter methods, block, Show as UI
├── checklists/requirements.md    # From /speckit-specify
└── tasks.md                      # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
therepy_sessions/
├── interpretation/
│   ├── analysis/
│   │   ├── model.py                    # ShowAs, default_show_as, Calculation.show_as
│   │   ├── serialization.py            # optional "show_as" key (R9)
│   │   ├── menu_formula.py             # + menu_row_measure()
│   │   └── results.py                  # NEW: work_out_results, CalculationResult, AnalysisResults, AnalysisProblem
│   ├── templates/
│   │   └── student_data_sheet_interpreter.py  # base: analysis_sheet_value / analysis_row_value; work out results last
│   ├── interpreter_types/
│   │   ├── simple_form_interpreter.py  # analysis_sheet_value
│   │   ├── running_tally_interpreter.py# analysis_sheet_value (summed, 0–100 percentages)
│   │   └── table_interpreter.py        # analysis_row_value
│   ├── student_data_sheet.py           # analysis_results, analysis_warnings, set_analysis_results
│   ├── importing/sheet_import_batch.py # broken-calculation warnings in the Sheet Outcome
│   └── template_manager/analysis_editor.py   # Show as combobox, "· %" mark
├── storage/
│   ├── session_layout.py               # CellNumberFormat.DECIMAL / PERCENT_DECIMAL; Analysis Results block
│   └── google_drive_data_sheet_store.py# patterns for the two new formats
└── sample_data/011/                    # NEW: synthetic template, Imports, README with hand-worked results

docs/domain/glossary.md                         # 4 terms; Data Sheet Analysis, Calculation updated
docs/conventions/architecture/interpreters.md   # rule 12
.specify/memory/constitution.md                 # 1.11.0 → 1.12.0
FEATURE_IDEAS.md                                # results idea removed (built)
```

**Structure Decision**: Single desktop project. The work is in the existing
`interpretation/analysis/` package, plus small hooks in the interpreter types, the sheet,
the batch, the editor, and `storage/session_layout.py`. Nothing moves between layers.

## Complexity Tracking

No constitution violations to justify.
