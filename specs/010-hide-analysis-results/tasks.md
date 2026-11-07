---

description: "Task list for the Hide Analysis Results feature"
---

# Tasks: Hide Analysis Results

**Input**: Design documents from `/specs/010-hide-analysis-results/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/hidden-calculations.md](contracts/hidden-calculations.md),
[quickstart.md](quickstart.md)

**Tests**: No automated tests. The spec doesn't ask for them, and research R8 makes
verification:

- offline scratch-script checks of the pure `interpretation/analysis/` modules
  (quickstart V1–V3)
- manual window checks (quickstart V4–V6) in a scratch Workspace

Scratch scripts are not committed.

**Organization**: Tasks are grouped by user story.

- **US1 (P1)**: hide a stepping-stone calculation: the model field, saving, and the editor
  panel check box.
- **US2 (P2)**: see at a glance which calculations are hidden, in view and edit mode.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US2 from spec.md

## Path Conventions

All code paths are relative to the repository root. Python modules live under
`therepy_sessions/` and import from it (for example `from interpretation.analysis.model
import Calculation`). The code uses two-space indents in `interpretation/analysis/` and
four-space indents in `interpretation/template_manager/`. Keep each file's style.

---

## Phase 1: Setup

**Purpose**: Capture a templates file saved by the code **before** this feature, so later
checks can prove old templates load and save unchanged (SC-002).

- [X] T001 Before changing any code, create `therepy_sessions/sample_data/010/analysis_templates.json` by saving it with the current, unchanged `TemplateStore` (`therepy_sessions/interpretation/template_store.py`) from a scratch script run in `therepy_sessions/` with `PYTHONPATH=.`. It holds one template, "Accuracy trials", with a `Trials` Table section: `Word` (Text), `Trial 1`–`Trial 3` (Choice: `+`, `-`). Its analysis has Layer 1: "Correct trials" = `RowAggregate("Trials", ChoiceCountMeasure("+", ("Trial 1", "Trial 2", "Trial 3")), Combination.SUM)` and "Incorrect trials" = the same with choice `-`. Layer 2: "Accuracy" = `Formula` of `{Correct trials} / ({Correct trials} + {Incorrect trials}) * 100`. Before saving, check that `analysis_problems` is empty for it, and that the formula's reference syntax matches `interpretation/analysis/formula.py`; adjust the text if the parser expects a different form. Use only made-up names (Principle I).
- [X] T002 [P] Create `therepy_sessions/sample_data/010/README.md` in the style of `therepy_sessions/sample_data/009/README.md`: say that `analysis_templates.json` was saved by the code before hidden calculations existed, has no `show_in_imported_sheets` keys, holds only made-up names, is used by quickstart V1, V2, V4–V6, and must never be regenerated with newer code. Include a table of its template, section, columns, and calculations.

**Checkpoint**: The sample file exists and was written by pre-feature code.

---

## Phase 2: Foundational

**Purpose**: The model field and its saved form. Both stories need these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Add `show_in_imported_sheets: bool = True` as the **last** field of the frozen `Calculation` dataclass in `therepy_sessions/interpretation/analysis/model.py` (research R1). Extend the class docstring's Properties with: whether its result appears with each sheet imported with the template; `False` makes it a Hidden Calculation; hiding never changes what may use it or how it is worked out; and, for the later results feature, every calculation a shown one depends on is still worked out, but only shown results are shown (R6). Don't change `is_menu`, `row_list_section`, `result_references`, or `DataSheetAnalysis`.
- [X] T004 Update `therepy_sessions/interpretation/analysis/serialization.py` (research R2, contract "Serialization"): in `_calculation_to_json`, add `data["show_in_imported_sheets"] = False` after the definition keys **only** when `calculation.show_in_imported_sheets` is `False`; never write the key for a shown calculation. In `_calculation_from_json`, pass `show_in_imported_sheets=data.get("show_in_imported_sheets") is not False` to `Calculation`, so a missing key or any value other than JSON `false` loads as shown. Mention the optional key in the module docstring. Don't change `FORMAT_VERSION`.
- [X] T005 Run quickstart V1–V3 (`specs/010-hide-analysis-results/quickstart.md`) as a scratch script against `therepy_sessions/sample_data/010/analysis_templates.json`: old analysis loads all shown and `analysis_to_json` gives back the exact saved value; hiding round-trips and leaves `analysis_problems` and `analysis_scope` unchanged; `"no"` and `null` load as shown; `apply_renames` of "Correct trials" → "Correct" keeps it hidden and rewrites the formula. Fix `model.py` or `serialization.py` until all pass. Don't commit the script.

**Checkpoint**: The setting exists, saves, loads, and survives renames.

---

## Phase 3: User Story 1 - Hide a stepping-stone calculation (Priority: P1) 🎯 MVP

**Goal**: The SLP hides or shows any calculation from the editor panel, with Apply and
Cancel, and the setting is saved with the template.

**Independent Test**: Quickstart V4 steps 1–4 and 6: a new calculation starts ticked;
Cancel restores the setting; Apply hides it; the Formula Legend and "Accuracy" are
unaffected; the setting survives save and reopen.

### Implementation for User Story 1

- [X] T006 [US1] In `AnalysisEditor._create_panel` in `therepy_sessions/interpretation/template_manager/analysis_editor.py` (research R4, contract "Editor panel"): create `self._show_var = tk.BooleanVar(value=True)` and a `ttk.Checkbutton(panel, text="Show in imported sheets", variable=self._show_var)` stored as `self._show_check`, gridded at `row=3, column=0, columnspan=2, sticky=tk.W, pady=(5, 0)`. Move the "Build with" frame from row 3 to row 4 and the Apply/Cancel buttons from row 6 to row 7. In the same file, change the `_panel_message.grid(row=4, ...)` call in `_set_panel_enabled` to row 5, and both `_formula_frame.grid(row=5, ...)` and `_menu_frame.grid(row=5, ...)` calls in `_show_build` to row 6.
- [X] T007 [US1] In `therepy_sessions/interpretation/template_manager/analysis_editor.py`: in `_fill_from`, set `self._show_var.set(calculation.show_in_imported_sheets)` inside the `self._filling` block next to the description; in `_panel_calculation`, pass `show_in_imported_sheets=self._show_var.get()` to `Calculation`. Check that `_open_new` (which builds `Calculation("", "", ...)`) therefore opens ticked, that `has_unapplied_changes` sees a changed box, and that `_on_panel_cancel` restores it, with no other change to `_apply`.
- [X] T008 [US1] In `_set_panel_enabled` in `therepy_sessions/interpretation/template_manager/analysis_editor.py`, disable and enable `self._show_check` together with the other panel widgets, matching how that method already handles them (`state(["disabled"])` / `state(["!disabled"])`).
- [X] T009 [US1] Run quickstart V4 steps 1–4 and 6 by hand in a scratch Workspace holding a copy of `therepy_sessions/sample_data/010/analysis_templates.json` as `templates.json` (run the app from `therepy_sessions/` with `../.venv/bin/python program.py`). Then open the saved `templates.json` and confirm only the two hidden calculations carry `"show_in_imported_sheets": false`.

**Checkpoint**: User Story 1 works on its own. The list doesn't mark hidden calculations
yet; the setting is visible by selecting a calculation in edit mode.

---

## Phase 4: User Story 2 - See at a glance which results will show (Priority: P2)

**Goal**: Hidden calculations are marked in the calculation list, in view mode and edit
mode alike.

**Independent Test**: Quickstart V4 step 5 and V5: a hidden calculation reads
`<name> (hidden)` in a muted color, a renamed one keeps the mark, and view mode shows the
mark with no way to change it.

### Implementation for User Story 2

- [X] T010 [US2] In `AnalysisEditor._render` in `therepy_sessions/interpretation/template_manager/analysis_editor.py` (research R5, contract "Calculation list"): for a calculation with `show_in_imported_sheets` False, insert its row with `text=f"{calculation.name} (hidden)"` and `tags=("hidden",)`; shown calculations keep `text=calculation.name` and no tag. Keep the `iid` as `C{layer}.{index}` so selection and moving still work. Where `self._tree` is created in `__init__`, add `self._tree.tag_configure("hidden", foreground=...)` with a muted gray that reads in both the light and dark `sv-ttk` themes (follow any muted-text color already used in `therepy_sessions/interpretation/template_manager/` if one exists).
- [X] T011 [US2] Run quickstart V4 step 5 and V5 by hand: rename a hidden calculation and confirm it keeps "(hidden)"; open the template in view mode and confirm the two Layer 1 calculations read "(hidden)", "Accuracy" doesn't, and no editor panel is shown.

**Checkpoint**: Both stories work.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T012 [P] Update `docs/domain/glossary.md` (research R7, FR-012): add rows after **Calculation Description** for **Show in imported sheets** (`Calculation.show_in_imported_sheets`: whether a calculation's result appears with each sheet imported with the template; on by default and for templates saved before it existed; set in the editor panel) and **Hidden Calculation** (a calculation with Show in imported sheets off: still worked out and usable by higher layers, but its result doesn't appear with imported sheets; marked "(hidden)" in the Analysis section). Update the **Calculation** row to say it may be hidden.
- [X] T013 [P] Update the "Work out calculation results for each imported sheet" entry in `FEATURE_IDEAS.md` (research R6): add to the list of what is already fixed that every calculation a shown calculation depends on must be worked out, but only shown calculations' results are shown (feature 010, FR-009), linking `specs/010-hide-analysis-results/spec.md`.
- [X] T014 Amend `.specify/memory/constitution.md` after T012 (research R7): bump **Version** 1.10.0 → 1.11.0 and **Last Amended** to the change date. Add a new Sync Impact Report at the top for 1.11.0 (MINOR: glossary additions; no principles, sections, or rules changed; supporting doc `docs/domain/glossary.md` adds Show in imported sheets and Hidden Calculation, and Calculation may be hidden; templates requiring updates: none; deferred TODOs: none). Move the 1.10.0 report below it as "Previous report (1.10.0)", following the existing pattern.
- [X] T015 Run quickstart V6: confirm that only the `analysis` value of the template differs in `templates.json` after V4, so its Student Session Workbook still matches. Then confirm no secrets, token files, or real student data are staged (`git status`).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 must run before any code change (it needs the old code). T002
  can run alongside T001.
- **Foundational (Phase 2)**: After T001. T003 → T004 → T005.
- **US1 (Phase 3)**: After Phase 2. T006 → T007 → T008 → T009 (same file).
- **US2 (Phase 4)**: After Phase 2. T010 edits the same file as US1, so do it after T008
  unless working on a separate branch. T011 needs T007 to hide calculations in the app.
- **Polish (Phase 5)**: T012 and T013 can run any time after Phase 2. T014 after T012.
  T015 last.

### User Story Dependencies

- **US1 (P1)**: Needs only Phase 2.
- **US2 (P2)**: Needs only Phase 2 for the mark itself. Checking it by hand (T011) is
  easiest with US1's check box. Without it, hide calculations by editing the scratch
  `templates.json`.

### Parallel Opportunities

- T001 and T002 (different files).
- T012 and T013 (different files), alongside any phase after Phase 2.
- US1 and US2 code all lives in `analysis_editor.py`, so they aren't parallel in one
  working tree.

## Parallel Example: Polish

```text
Task: "T012 [P] Add Show in imported sheets and Hidden Calculation to docs/domain/glossary.md"
Task: "T013 [P] Record the results-feature rule in FEATURE_IDEAS.md"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: capture the sample with the old code.
2. Phase 2: the field and its saved form, checked offline (V1–V3).
3. Phase 3: the check box. **Stop and validate** with V4.

### Incremental Delivery

1. Setup + Foundational → the setting is saved and loaded safely.
2. US1 → the SLP can hide calculations (MVP).
3. US2 → hidden calculations are visible at a glance.
4. Polish → glossary, constitution, and feature-ideas updates.
