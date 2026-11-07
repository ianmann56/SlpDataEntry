# Quickstart: Validating Hide Analysis Results

Checks that prove [spec.md](spec.md) works. V1–V3 run offline with scratch scripts. V4–V6
are done by hand in the app. The interfaces are in
[contracts/hidden-calculations.md](contracts/hidden-calculations.md), and the saved form is
in [data-model.md](data-model.md).

## Prerequisites

- The virtual environment exists, as in the [README](../../README.md).
- Run scratch scripts from `therepy_sessions/`, and keep them out of the repo:

  ```sh
  cd therepy_sessions && PYTHONPATH=. ../.venv/bin/python /path/to/scratch_check.py
  ```

- For V4–V6, use a scratch Workspace folder holding a copy of
  `therepy_sessions/sample_data/010/analysis_templates.json` as its `templates.json`, never
  the SLP's real one. No Google or AWS access is needed.
- Use only synthetic names (Principle I).

## The test analysis

`sample_data/010/analysis_templates.json` holds one template with a "Trials" table and an
analysis saved in the 009 format, with no `show_in_imported_sheets` keys:

- **Layer 1**: "Correct trials" (Sum of a `+` choice count over the trial columns) and
  "Incorrect trials" (Sum of a `-` choice count over the same columns).
- **Layer 2**: "Accuracy", a formula:
  `{Correct trials} / ({Correct trials} + {Incorrect trials}) * 100`.

## V1. Old analysis loads shown, and saves unchanged (FR-006, SC-002)

Load the template's `"analysis"` value with `analysis_from_json`.

- Every calculation has `show_in_imported_sheets == True`.
- `analysis_to_json` of the loaded analysis equals the original value exactly.

## V2. Hidden setting round-trips, and nothing else changes (FR-005, FR-007, FR-008, SC-003)

Hide both Layer 1 calculations with `dataclasses.replace(..., show_in_imported_sheets=False)`.

- Their saved objects hold `"show_in_imported_sheets": false`. "Accuracy" has no such key.
- `analysis_from_json(analysis_to_json(a)) == a`.
- `analysis_problems` gives the same (empty) list before and after hiding.
- `analysis_scope` for Layer 2 offers the same results before and after hiding.
- A saved value of `"show_in_imported_sheets": "no"` or `null` loads as shown.

## V3. Renames keep the setting (FR-011)

Apply a calculation rename of "Correct trials" → "Correct" with `apply_renames`.

- The renamed calculation is still hidden.
- "Accuracy"'s formula now refers to `{Correct}`.

## V4. Hide and show in the editor (User Story 1, FR-002, FR-003)

Open the template in Template Details and switch to edit mode.

1. Press Add Calculation. **Show in imported sheets** is ticked.
2. Select "Correct trials", clear the box, and press Cancel. The box is ticked again, and
   the list still shows the plain name.
3. Clear the box again and press Apply. The row reads "Correct trials (hidden)" in a muted
   color.
4. Hide "Incorrect trials" too. Select "Accuracy". Its formula is still OK, and the Formula
   Legend still lists both hidden results.
5. Rename "Correct trials" to "Correct" and apply. It still reads "(hidden)".
6. Save, close, and reopen. Both Layer 1 calculations read "(hidden)", and "Accuracy" doesn't.

## V5. See hidden calculations in view mode (User Story 2, FR-004, SC-004)

Open the saved template from V4 in view mode.

- The two Layer 1 calculations read "(hidden)", and "Accuracy" doesn't.
- There is no editor panel, so the setting can't be changed until edit mode.

## V6. Template Structure is unchanged (FR-010)

After V4, the template's Student Session Workbook name and label are the same as before:
the template still matches the workbook it matched before. Compare the template's
structure fields in `templates.json` before and after V4. Only the `analysis` value differs.

## Not checked here

FR-009 and SC-005 (only shown results appear with imported sheets) are checked when the
feature that works out results ships.
