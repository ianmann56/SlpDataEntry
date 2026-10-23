# Implementation Plan: Data Sheet Analysis

**Branch**: `009-data-sheet-analysis` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-data-sheet-analysis/spec.md`

## Summary

Each Data Sheet Template gains a **Data Sheet Analysis**: numbered Analysis Layers of
named Calculations, configured in a new Analysis section of the Create Template and
Template Details windows. This feature only configures calculations. Working out
results is a later spec.

**Model.** A new pure package, `interpretation/analysis/`, holds the model (R1).

- A calculation is a menu **Row Aggregate** (Sum or Average over a table's rows of a
  Number column, Tally count, or Choice count), a menu **Arithmetic** calculation (two
  inputs and an operation), or a typed **Formula**.
- Everything is referenced by name: sections by their Section Name, then columns,
  fields, options, and calculations (R2).

**Formulas.** A small spreadsheet-like grammar (R3), for example
`AVERAGE(COUNT("+", [Trials/Trial 1], [Trials/Trial 2]))` and
`{Correct} / {Total} * 100`.

- A hand-written parser records the character span of every token and reference (R4).
- The editor re-checks the formula after every change, and shows the problem and its
  position, or "Formula is OK."
- A **Formula Legend** beside the entry lists the operations and the variables in scope.
  Clicking an entry inserts it, with an operation's placeholders selected.

**Scope and checks.**

- A single `analysis_scope` feeds the menu, the legend, and every check (R5).
- Sections describe themselves through a new optional `analysis_parts()` method, so the
  analysis code never checks interpreter types (Principle V).
- Save is refused while any calculation refers to something missing, mistyped,
  ambiguous, or out of layer (R7).

**Renames.** The column, field, and option editors remember each item's loaded name.
Configs report renames, and a pure `apply_renames` rewrites menu fields and only the
matching reference spans in formula text (R6).

**Saving.** The template entry in `templates.json` gains an optional `"analysis"` key.
Templates without analysis are written byte-for-byte as before, and `FORMAT_VERSION`
stays 2 (R8). Storage never reads analysis, so the Template Structure can't change
(FR-020).

**UI.**

- An `AnalysisEditor` in the Template Form shows a list of layers and calculations, with
  an editor panel below it (Apply/Cancel, the same pattern as interpreters) (R9).
- Both template windows open maximized through a new `tk_utils/windows.maximize` helper
  (R10).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Tkinter + `sv-ttk`, the existing stack. No new dependency. The
parser is hand-written, and `decimal` is in the standard library.

**Storage**:

- `templates.json` gets an optional `"analysis"` key per template entry, and
  `FORMAT_VERSION` stays 2.
- No change to Student Session Workbooks, the Template Structure, or `students.json`.

**Testing**:

- Offline scratch-script checks of the parser, scope, problems, renames, and
  serialization (quickstart V1–V5).
- Manual window checks (V6–V10).
- No test framework (007 R11, 009 R11).

**Target Platform**: Desktop (Linux primary; any OS that runs Tkinter, through the
maximize helper).

**Project Type**: Desktop app (single project under `therepy_sessions/`).

**Performance Goals**:

- Re-checking a formula on each key press is imperceptible: microseconds for formulas of
  a few hundred characters.
- Opening a template with dozens of calculations adds no visible delay.

**Constraints**:

- Interpretation stays pure.
- Analysis never changes import results or the Template Structure (FR-020).
- Old templates load unchanged (FR-019).
- Formulas are never executed as code (R3).
- Calculation names, descriptions, and formulas never identify a student (FR-021).

**Scale/Scope**:

- Code: a new package of 7 small modules, about 9 changed modules, and 2 new UI modules.
- Docs: the glossary, `interpreters.md`, and the constitution version.
- Templates: tens per Workspace, each with perhaps 1–4 layers of a few calculations.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies | Result |
| --- | --- | --- |
| I. Student Data Privacy | No new service, and no student data is read or written. Calculation names, descriptions, and formulas are template text, and the Description field shows the same "don't include student names" hint as the Template Description (FR-021). Checks use synthetic templates in a scratch Workspace. | ✅ Pass |
| II. Domain Language Fidelity | Code names match the spec's terms: `DataSheetAnalysis`, `AnalysisLayer`, `Calculation`, `RowAggregate`, `RowMeasure`, `Arithmetic`, `Formula`, `FormulaLegend` (widget), `AnalysisScope`, and `section_name`. Thirteen terms are added to the glossary in this change (R12). | ✅ Pass (glossary update in scope) |
| III. Layered Pipeline | All rules live in pure `interpretation/analysis/`. Widgets in `interpretation/template_manager/` only show scope entries and call rules (layers rule 5). Nothing new crosses a layer boundary: `storage/` and `collection/` are untouched, and `program.py` is unchanged. | ✅ Pass |
| IV. Injected External Services | No client is used or changed. | ✅ Pass |
| V. Pluggable Interpreters & Templates | Interpreter types opt in through the optional `analysis_parts()`, and configs through the optional `renames()`. The core never checks types. Saved templates stay loadable: the `"analysis"` key is optional and additive, and untouched entries are re-saved identically (rule 4). Interpreters the SLP didn't change are still saved as loaded (rule 7). | ✅ Pass (`interpreters.md` amended, R12) |
| VI. Typed Public Interfaces | Every new public member is annotated. The model uses frozen dataclasses, and the parser, scope, and rename records are `NamedTuple`s, all listed in the contract. Changed members (`StudentDataSheetTemplate.__init__`, DTOs, `TemplateDraft`, `InterpreterConfig.renames`, `TypedItem`) are annotated in the same change. | ✅ Pass |
| Tech constraints | No new dependency, so `pip_requirements.txt` and `ALL_DEPENDENCIES.md` are unchanged. JSON is still UTF-8, `indent=2`. | ✅ Pass |
| Development Workflow | Offline checks use synthetic inputs. The constitution amendment follows Governance (MINOR bump and Sync Impact Report). | ✅ Pass |

**Post-design re-check (after Phase 1)**: Still passing. The contracts add two optional
hooks, `analysis_parts()` and `renames()`, rather than type checks, and keep every rule
out of widget callbacks. No Complexity Tracking entry is needed.

## Project Structure

### Documentation (this feature)

```text
specs/009-data-sheet-analysis/
├── plan.md              # This file
├── research.md          # Phase 0: R1–R12
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1: V1–V10
├── contracts/
│   ├── analysis-model-and-formulas.md
│   └── analysis-ui.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
therepy_sessions/
├── interpretation/
│   ├── analysis/                              # NEW, pure (no Tkinter, no I/O)
│   │   ├── __init__.py
│   │   ├── parts.py                           # TableColumnPart, SectionParts
│   │   ├── model.py                           # DataSheetAnalysis, AnalysisLayer, Calculation, definitions
│   │   ├── formula.py                         # tokenizer, parser, spans, escape_name, OPERATIONS
│   │   ├── scope.py                           # analysis_scope, Section Name ambiguity
│   │   ├── rules.py                           # problems, calculations_using, describe_calculation
│   │   ├── renames.py                         # PartRename, apply_renames (span rewriting)
│   │   └── serialization.py                   # analysis_to_json / analysis_from_json
│   ├── templates/
│   │   └── student_data_sheet_interpreter.py  # base: section_name, analysis_parts() default
│   ├── interpreter_types/
│   │   ├── table_interpreter.py               # analysis_parts(); use section_name
│   │   ├── simple_form_interpreter.py         # analysis_parts(); use section_name
│   │   └── running_tally_interpreter.py       # analysis_parts(); use section_name
│   ├── template_store.py                      # DTOs gain analysis; read/write optional "analysis" key
│   └── template_manager/
│       ├── student_data_sheet_template.py     # analysis property
│       ├── template_rules.py                  # TemplateDraft.analysis, rename_parts, problems, has_changes_from
│       ├── interpreter_configs.py             # InterpreterConfig.renames(), overrides for the three configs
│       ├── typed_item_editor.py               # TypedItem.loaded_name; per-option loaded values
│       ├── option_list_editor.py              # loaded value per option
│       ├── template_form.py                   # hosts AnalysisEditor; renames on apply; commit/unapplied include analysis
│       ├── analysis_editor.py                 # NEW: layers list, buttons, calculation panel (menu + formula)
│       ├── formula_legend.py                  # NEW: legend Treeview, click-to-insert
│       ├── template_creator_window.py         # maximize
│       └── template_details_window.py         # maximize
├── sample_data/
│   └── 009/                                   # NEW: README.md + pre_analysis_templates.json
└── tk_utils/
    └── windows.py                             # NEW: maximize(window)
docs/
├── conventions/architecture/interpreters.md   # analysis_parts(), renames(), rule 11
└── domain/glossary.md                         # 13 new terms
.specify/memory/constitution.md                # MINOR bump, Sync Impact Report
```

**Structure Decision**: This is the existing single desktop project.

- The new rules get their own package, `interpretation/analysis/`, beside `templates/`
  and `interpreter_types/`.
- The new widgets join the other template widgets in `interpretation/template_manager/`.
- `storage/`, `collection/`, `clients/`, `students/`, `workspace/`, `app_shell/`, and
  `program.py` are untouched.

## Complexity Tracking

No constitution violations to justify.
