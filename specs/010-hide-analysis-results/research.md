# Research: Hide Analysis Results

No item in the Technical Context needed clarification. Each decision below follows from the
code 009 left in `therepy_sessions/interpretation/analysis/` and
`therepy_sessions/interpretation/template_manager/analysis_editor.py`.

## R1. Where the setting lives in the model

- **Decision**: Add a field `show_in_imported_sheets: bool = True` as the last field of the
  frozen `Calculation` dataclass in `interpretation/analysis/model.py`.
- **Rationale**: The setting belongs to one calculation (spec Assumptions: per calculation,
  not per layer). As the last field with a default, every existing positional call
  `Calculation(name, description, definition)` keeps working and means "shown" (FR-002,
  FR-006). `apply_renames` rebuilds calculations with `dataclasses.replace`, which carries
  every field over, so a rename keeps the setting (FR-011). Moves and edits replace the whole
  `Calculation` value, so they keep it too.
- **Alternatives considered**:
  - A set of hidden names on `DataSheetAnalysis`. Rejected: it would need its own rename
    handling, and it would split one calculation's settings across two places.
  - A `hidden: bool = False` field. Rejected: the spec and the UI talk about *showing*, and
    a positive name avoids double negatives such as `not hidden`.

## R2. How the setting is saved

- **Decision**: `_calculation_to_json` writes `"show_in_imported_sheets": false` only for a
  hidden calculation and leaves the key out for a shown one. `_calculation_from_json` reads a
  missing key as `True`, and anything other than the JSON value `false` as `True` too.
- **Rationale**: Templates where every calculation is shown are written byte-for-byte as
  before. That includes every template saved before this feature (SC-002), so saving and
  reloading them changes nothing. `FORMAT_VERSION` stays 2, as in 009 R8. Reading only the
  exact value `false` as hidden means a damaged file can never hide a result by accident
  (the spec's "nothing disappears without the SLP choosing it").
- **Alternatives considered**:
  - Always writing the key. Rejected: it rewrites every saved template on its next save,
    with no benefit.
  - Bumping `FORMAT_VERSION`. Rejected: the change only adds an optional key, which older
    loaders don't need.

## R3. What the setting does not touch

- **Decision**: `scope.py`, `rules.py`, `formula.py`, `renames.py`, `formula_legend.py`,
  and storage stay unchanged.
- **Rationale**: FR-007 and FR-008 say hiding changes neither what higher layers may use nor
  how results are worked out. The scope and the checks never read the new field, so a
  hidden result is offered, accepted, and checked like any other (SC-003). Storage never
  reads `analysis`, so the Template Structure and its Student Session Workbooks can't change
  (FR-010, 009 FR-020).
- **Alternatives considered**: Leaving hidden results out of the Formula Legend. Rejected:
  the main use of a hidden result is to feed a higher layer (spec Assumptions).

## R4. The control in the editor panel

- **Decision**: Add a `ttk.Checkbutton` labeled **Show in imported sheets**, bound to a
  `tk.BooleanVar`, on its own row below the description hint in `_create_panel`. The
  "Build with" row, the panel message, the menu/formula frame, and the buttons each move
  down one grid row (3→4, 4→5, 5→6, 6→7). `_fill_from` sets the variable from the
  calculation, and `_panel_calculation` passes it to `Calculation`.
- **Rationale**: Because `_panel_calculation` includes the setting, the existing
  `has_unapplied_changes`, `_apply`, and `_on_panel_cancel` already treat it like any other
  field. It applies on Apply and is discarded on Cancel (FR-003) with no new logic. New
  calculations go through `_open_new` → `_fill_from(Calculation("", "", ...))`, which
  defaults to shown (FR-002). `_set_panel_enabled` disables it with the other panel
  widgets.
- **Alternatives considered**: A right-click toggle in the list, or a toggle button above
  it. Rejected: it would change the analysis outside Apply/Cancel, unlike every other
  calculation change (FR-003).

## R5. Marking hidden calculations in the list

- **Decision**: In `AnalysisEditor._render`, a hidden calculation's row shows its name
  followed by ` (hidden)`, and gets a `hidden` tree tag drawn in a muted foreground color.
  Shown calculations are drawn as today. The same tree is used in view mode and edit mode,
  so one change covers both (FR-004, User Story 2).
- **Rationale**: A text suffix stays readable in both the light and dark `sv-ttk` themes
  and doesn't depend on color alone. The suffix is only display text: rows are found by
  their `iid` (`C{layer}.{index}`), never by their text, so selection and moving still
  work.
- **Alternatives considered**: A new "Shown" column. Rejected: on nearly every row it would
  just say "Yes", and it would take width from the "Works out" summary.

## R6. How the later results feature honors the setting

- **Decision**: No result code is written now. The rule from FR-009 is recorded in two
  places: the `Calculation` docstring and the "Work out calculation results for each
  imported sheet" entry in `FEATURE_IDEAS.md`. The rule is: work out every calculation that
  a shown calculation depends on, and show only the shown ones.
- **Rationale**: Results are not worked out yet (spec Assumptions). A helper with no caller
  would be dead code, and the results feature will decide where results go.
- **Alternatives considered**: Adding `DataSheetAnalysis.shown_calculations()` now.
  Rejected for the reason above. It is a one-line filter the results feature can add.

## R7. Glossary and constitution

- **Decision**: Add **Show in imported sheets** (`Calculation.show_in_imported_sheets`) and
  **Hidden Calculation** to `docs/domain/glossary.md`, and update the **Calculation** row to
  say it may be hidden. Bump the constitution 1.10.0 → 1.11.0 (MINOR, glossary additions),
  with a Sync Impact Report, as 1.8.0–1.10.0 did.
- **Rationale**: Principle II and FR-012.

## R8. Verification

- **Decision**: Offline scratch-script checks of the model, serialization, and renames
  (quickstart V1–V3), and manual window checks (V4–V6). Add a synthetic
  `therepy_sessions/sample_data/010/analysis_templates.json`, a templates file with an
  analysis saved in the 009 format (no `show_in_imported_sheets` keys), for the round-trip
  and old-template checks.
- **Rationale**: The project has no test framework (007 R11, 009 R11). 009's
  `pre_analysis_templates.json` has no analysis at all, so it can't show that a saved
  analysis stays unchanged.
