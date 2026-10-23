# Quickstart: Validating Data Sheet Analysis

Checks that prove [spec.md](spec.md) works end to end. V1–V5 run offline with scratch
scripts. V6–V10 are by hand in the app. The interfaces are in
[contracts/analysis-model-and-formulas.md](contracts/analysis-model-and-formulas.md)
and [contracts/analysis-ui.md](contracts/analysis-ui.md).

## Prerequisites

- The virtual environment exists: `python3 -m venv .venv`, then
  `.venv/bin/pip install -r pip_requirements.txt`.
- Run scratch scripts from `therepy_sessions/`, so the package imports resolve, and keep
  them out of the repo (for example, in a temp folder):

  ```sh
  cd therepy_sessions && PYTHONPATH=. ../.venv/bin/python /path/to/scratch_check.py
  ```

- For V6–V10, use a scratch Workspace folder with a copy of a `templates.json`, never
  the SLP's real one. No Google or AWS access is needed: nothing here imports a sheet.
- Use only synthetic names in templates (Principle I).
- `therepy_sessions/sample_data/009/pre_analysis_templates.json` is the committed templates file saved before this feature, for V4 and V10.

## The test template

Build it in a script, or in the app for V6. It is a "Trials" Table section with:

| Column | Type | Options |
| --- | --- | --- |
| Word | Text | |
| Trial 1, Trial 2, Trial 3 | Choice | `+` correct, `-` incorrect, `P` prompted |
| Attempts | Tally | `Y`, `N`, `P` |
| Words correct | Integer | |

It also has a "Session Info" Simple Form section with a `Prompts given` Integer field,
and a `Notes` Text field.

## V1. Formula parsing (FR-012, FR-013)

`parse_formula` must give:

| Text | Expect |
| --- | --- |
| `SUM([Trials/Attempts/P])` | no problem; 1 COLUMN reference with parts `("Trials","Attempts","P")` |
| `AVERAGE(COUNT("+", [Trials/Trial 1], [Trials/Trial 2]))` | no problem; 2 COLUMN references with choice `+` |
| `({A} + {B}) / {C} * 100` | no problem; 3 RESULT references |
| `[Odd\/Name/x\]y]` | no problem; parts `("Odd/Name", "x]y")` |
| `SUM([Trials/Attempts/P]` | problem at the end: `)` expected |
| `{A} +` | problem at the end: something expected after `+` |
| `SUM(<row measure>)` | problem spanning `<row measure>`: fill it in |
| `[Trials/Words correct] + 2` | no syntax problem (the reference is a SHEET_VALUE; V2 rejects it) |

`escape_name("a/b]c}d\\")` gives `a\/b\]c\}d\\\\`, and parsing it back gives the
original.

## V2. Scope and problems (FR-006, FR-010, FR-011, FR-015, FR-016)

With the test template and two layers:

- `analysis_scope(..., layer_number=1)`:
  - `tables` has Trials, with Number column `Words correct`, Tally `Attempts`
    (`P`, `N`, `Y`, `Total`), and Choice columns Trial 1–3.
  - `sheet_values` has `[Session Info/Prompts given]`, but not `Notes`.
  - `results` is empty.
- At layer 2, `results` lists the layer 1 calculations with their descriptions.
- `formula_problems` at layer 2 reports each of these, naming the reference:
  - `{Accuracy}`, where Accuracy is in layer 2
  - `[Trials/Words correct] + 2`, a column outside `SUM`/`AVERAGE`
  - `SUM([Trials/Word])`, a Text column
  - `SUM(COUNT("X", [Trials/Trial 1]))`, a choice that isn't offered
  - `SUM([Trials/Nope])`, an unknown column
- `formula_problems("SUM([trials/attempts/p])", ...)` has no problem, because names
  ignore letter case.
- Two calculations named `Total` and ` total ` give one duplicate-name problem
  (FR-007).
- Removing the Attempts column (rebuild the TableInterpreter without it), then calling
  `analysis_problems`, names every calculation that used it.
- Two untitled Simple Form sections: neither is in scope, and `[Form/x]` reports the
  ambiguity (R2).

## V3. Renames (FR-016a)

Start from a layer 1 menu calculation on `Attempts` / `P`, a layer 1 formula
`SUM([Trials/Attempts/P])  +  {X}` (with odd spacing), and a layer 2 formula using
`{Correct trials}`. Then apply:

| Rename | Expect |
| --- | --- |
| `ITEM Trials: Attempts → Tries` | Menu column `Tries`; formula `SUM([Trials/Tries/P])  +  {X}`, with the spacing kept. |
| `OPTION Trials/Tries: P → Q` | Menu mark `Q`; formula `[Trials/Tries/Q]`. |
| `SECTION Trials → Practice` | Every `[Trials/...]` becomes `[Practice/...]`; the menu section is `Practice`. |
| `CALCULATION Correct trials → Correct` | `{Correct trials}` becomes `{Correct}`; any `ResultOperand` too. |
| `ITEM` rename to `A/B` | It is inserted escaped: `[Practice/A\/B/Q]`. |
| `OPTION Trials/Trial 1: + → C` | `COUNT("+", [Trials/Trial 1])` becomes `COUNT("C", [Trials/Trial 1])`. |

`analysis_problems` is `[]` after each rename.

## V4. Saving and loading (FR-018, FR-019, FR-020)

- `analysis_from_json(analysis_to_json(a)) == a` for an analysis holding every
  definition variant, including a `NumberOperand` of `0.1` and a formula with odd
  spacing.
- Load a copy of `therepy_sessions/sample_data/009/pre_analysis_templates.json` (a templates file saved before this feature): every template has
  `analysis.is_empty`. Saving one unchanged writes an entry with no `"analysis"` key,
  byte-identical to before.
- Save a template with analysis, and reload it through `TemplateStore`: the analysis is
  equal.
- The template's Template Structure (`TemplateShape.structure_identity()`) is the same
  with and without analysis.

## V5. Dependencies and layers (FR-004, FR-005, FR-017)

- `with_calculation_removed` raises, naming the users, for a layer 1 calculation used in
  layer 2.
- `with_highest_layer_removed` removes only the last layer.
- `with_calculation_moved` keeps the calculation in its layer, and does nothing past
  either end.
- `describe_calculation` gives the plain-language lines from the contract, for one of
  each kind.
- Every menu calculation can be written as a formula (SC-006). For each menu
  calculation in V7, its equivalent formula has no `formula_problems` at the same layer.

## V6. Full-screen windows (FR-001a)

1. Open Data Sheet Template management, then Create New Template. The window fills the
   screen.
2. Restore it smaller, then maximize it again, with the window buttons. Both work.
3. Open an existing template's details. It also opens full screen, in view mode.

## V7. Menu calculations, layers, and view mode (User Stories 1–2)

1. Create the test template. Under Analysis, check the historical-analysis note, then
   Add Layer.
2. Add the four example calculations from the spec as menu Row Aggregates:
   - Sum of `+` across Trial 1–3
   - Average of `+` across Trial 1–3
   - Sum of the Attempts `P` count
   - Average of the Attempts total
   
   Check that the column choices only offer the right types.
3. Add Layer 2. Add "Accuracy" as Arithmetic: Correct trials, Percentage, Total trials.
   Layer 2's result pickers list only layer 1 calculations.
4. Try Remove on a layer 1 calculation that Accuracy uses. It is refused, naming
   Accuracy.
5. Save, close, and reopen. View mode shows every calculation in plain language, with
   its description, and nothing can be edited.
6. Time this. It should take under 10 minutes (SC-001).

## V8. Formula editing and the legend (User Story 3)

1. Edit the template. Add a layer 2 calculation, and choose Build with: Formula. The
   Formula Legend appears beside it.
2. Click `AVERAGE(row measure)`. `AVERAGE(<row measure>)` is inserted, with the
   placeholder selected. The message says to fill it in.
3. Click `[Trials/Attempts/Total]` in the legend. It replaces the placeholder, and the
   message becomes `✓ Formula is OK.`
4. Type `+ {Accuracy}`. The message names the out-of-scope result while you type.
   Apply is refused, and the message stays.
5. Fix the formula, Apply, and Save. Reopen it: the formula is shown exactly as typed.

## V9. Renames and removals in the window (FR-016, FR-016a)

1. In edit mode, rename the Attempts column to "Tries", and Apply the section. The
   analysis list now shows "Tries" in the menu calculation and the formula. Save works.
2. Remove the Trial 3 column, and Apply. Save is refused with a Validation Error naming
   the calculations that use Trial 3.
3. Cancel. The template is unchanged.

## V10. Old templates (User Story 4)

Use a scratch Workspace whose `templates.json` is a copy of `therepy_sessions/sample_data/009/pre_analysis_templates.json`. Open each template. Each shows "No
calculations." Edit one, add a calculation, and Save. It reloads, and the rest of its
entry is unchanged.
