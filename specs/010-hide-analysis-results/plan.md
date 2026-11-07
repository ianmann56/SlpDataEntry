# Implementation Plan: Hide Analysis Results

**Branch**: `010-hide-analysis-results` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/010-hide-analysis-results/spec.md`

## Summary

Every Data Sheet Analysis calculation gets a **Show in imported sheets** setting. It is on
by default, and the SLP turns it off to hide a step that only feeds a higher-layer
calculation. Calculation results aren't worked out on import yet, so this feature adds the
setting, saves it, and shows it. The later results feature must follow it (R6).

- **Model.** `Calculation` gains `show_in_imported_sheets: bool = True` as its last field
  (R1). Existing constructor calls, renames (`dataclasses.replace`), edits, and moves all
  carry it with no other change.
- **Saving.** A hidden calculation is saved with `"show_in_imported_sheets": false`. A
  shown one is saved without the key, so templates saved before this feature load as all
  shown and save byte-for-byte unchanged (R2). `FORMAT_VERSION` stays 2.
- **Unchanged.** Scope, problem checks, the Formula Legend, renames, and storage ignore the
  setting. A hidden result can still be used by higher layers, and the Template Structure
  can't change (R3).
- **UI.** The `AnalysisEditor` panel gains a check box below the description. It follows
  the existing Apply/Cancel flow because `_panel_calculation` includes it (R4). The list
  marks hidden calculations as `<name> (hidden)` in a muted color, in view and edit mode
  alike (R5).
- **Docs.** Two glossary terms, constitution 1.10.0 → 1.11.0 (R7), and the later results
  rule in `FEATURE_IDEAS.md` (R6).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Tkinter + `sv-ttk`, the existing stack. No new dependency.

**Storage**:

- `templates.json` gets one optional key per hidden calculation under a template's
  `"analysis"` key. `FORMAT_VERSION` stays 2.
- No change to Student Session Workbooks, the Template Structure, or `students.json`.

**Testing**:

- Offline scratch-script checks of the model, serialization, and renames (quickstart
  V1–V3).
- Manual window checks (V4–V6).
- A new synthetic sample, `therepy_sessions/sample_data/010/analysis_templates.json`
  (R8).
- No test framework (007 R11, 009 R11).

**Target Platform**: Desktop (Linux primary; any OS that runs Tkinter).

**Project Type**: Desktop app (single project under `therepy_sessions/`).

**Performance Goals**: No measurable change. One more field per calculation, and one more
widget in the panel.

**Constraints**:

- Interpretation stays pure.
- Hiding never changes what a calculation may use or how it is worked out (FR-007,
  FR-008).
- Old templates load as shown and save unchanged (FR-006, SC-002).
- The Template Structure never changes (FR-010).

**Scale/Scope**:

- Code: 3 changed modules: `analysis/model.py`, `analysis/serialization.py`, and
  `template_manager/analysis_editor.py`.
- Docs: the glossary, the constitution version, and `FEATURE_IDEAS.md`.
- Data: one new sample file.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies | Result |
| --- | --- | --- |
| I. Student Data Privacy | No new service, and no student data is read or written. The setting is a flag on template text. Checks use a synthetic template in a scratch Workspace. | ✅ Pass |
| II. Domain Language Fidelity | The field is named for the UI label, `show_in_imported_sheets`. **Show in imported sheets** and **Hidden Calculation** are added to the glossary, and **Calculation** is updated, in this change (R7, FR-012). | ✅ Pass (glossary update in scope) |
| III. Layered Pipeline | The model and saved-form changes stay in pure `interpretation/analysis/`. The widget in `interpretation/template_manager/` only reads and sets the field. `storage/`, `collection/`, and `program.py` are untouched. | ✅ Pass |
| IV. Injected External Services | No client is used or changed. | ✅ Pass |
| V. Pluggable Interpreters & Templates | No interpreter changes. Serialized templates stay loadable: a missing key loads as shown, and all-shown templates save unchanged (R2). Analysis is still never part of the Template Structure (interpreters.md rule 11). | ✅ Pass |
| VI. Typed Public Interfaces | The new public field is annotated `bool`. No other public member changes signature. | ✅ Pass |

**Post-design re-check**: The data model, contract, and quickstart add nothing beyond the
table above. All gates pass, and there is no Complexity Tracking entry.

## Project Structure

### Documentation (this feature)

```text
specs/010-hide-analysis-results/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R8
├── data-model.md        # Phase 1: Calculation and its saved form
├── quickstart.md        # Phase 1: checks V1–V6
├── contracts/
│   └── hidden-calculations.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
therepy_sessions/
├── interpretation/
│   ├── analysis/
│   │   ├── model.py              # Calculation.show_in_imported_sheets (R1)
│   │   └── serialization.py      # optional "show_in_imported_sheets": false (R2)
│   └── template_manager/
│       └── analysis_editor.py    # panel check box (R4), "(hidden)" in the list (R5)
└── sample_data/
    └── 010/
        ├── README.md
        └── analysis_templates.json   # analysis saved in the 009 format (R8)

docs/domain/glossary.md                # two new terms, Calculation updated (R7)
.specify/memory/constitution.md        # 1.10.0 → 1.11.0 (R7)
FEATURE_IDEAS.md                       # results feature must honor the setting (R6)
```

**Structure Decision**: The existing single project under `therepy_sessions/`. This feature
changes three modules from 009 and adds no new module.

## Complexity Tracking

No violations.
