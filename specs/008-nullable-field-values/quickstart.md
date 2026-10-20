# Quickstart: Validating Nullable Field Values

This guide shows the feature works end to end. Record shapes are in
[data-model.md](data-model.md), and signatures are in
[contracts/lenient-values-and-outcomes.md](contracts/lenient-values-and-outcomes.md).

**Privacy (Principle I)**: Use only synthetic sheets with the Student Key `ZZ`, a test
Google account, and a copy of the templates file. Never use a real student's sheet or
the SLP's real Drive.

## Prerequisites

```sh
source .venv/bin/activate
cd therepy_sessions
```

The offline checks (V1–V6) are throwaway scripts run from `therepy_sessions/`, as in
007. They are not committed. The sample Imports are loaded as described in
`sample_data/007/README.md`, and use its three-section template (`Words`,
`Prompts given`, `Tally Grid`).

## Offline checks (no network)

### V1. Lenient reading (FR-002, FR-004, FR-004a)

Call `value_types.read_value_leniently`:

| Type | Input → `(typed_value, expected, saved_as)` |
| --- | --- |
| Integer | `"7"` → `(7, "", "")`; `"7.0"` → `(7, "", "")`; `"7.5"` → `(8, "a whole number", "8")`; `"2.5"` → 3; `"-2.5"` → -3; `"7.4"` → 7; `"N/A"` → `(None, "a whole number", "")`; `""` → `(None, "", "")` |
| Decimal | `"2.5"` → `(2.5, "", "")`; `"about 3"` → `(None, "a number", "")` |
| True/False | `"Y"` → True; `"X"` and `"maybe"` → `(None, "yes or no (Y, N, ✓, …)", "")` |
| Date | `"10/3/26"` → 2026-10-03; `"13/45/2026"` → `(None, "a date (month/day/year)", "")` |
| Choice `+ - P` | `"p"` → `"P"`; `"~"` → `(None, "one of +, -, P", "")` |
| Text | `"N/A"` → `("N/A", "", "")` |

Also confirm that `read_value` itself is unchanged: `"7.5"` as Integer still raises
`ValueReadError` (FR-004).

### V2. Tallies (FR-008 to FR-010)

Use `read_tally` with options `Y N P`:

| Input | Expected result |
| --- | --- |
| `"YQN"` | marks `YN`, Y=1 N=1 P=0, total 2, Y=0.5, `unknown_marks="Q"`, `text_as_read="YQN"` |
| `"QZ"` | total 0, percentages None, `unknown_marks="QZ"` |
| `"YyN P"` | as in 007, with `unknown_marks=""` |

`tally_scalars("Attempts", <YQN summary>, ...)` gives `"Attempts"` with value and
typed value `"YQN"`, and `"Attempts Total"` = 2.

### V3. Interpreters return problems instead of raising (FR-003, FR-012)

Interpret `sample_data/007/bad_values.json` with the 007 three-section template. It
must not raise. Check the following:

- **Table row 2**:
  - `Trials` scalar: value `"l"`, typed None
  - `Done`: value `"X"`, typed None
  - `When`: `"2/30/2026"`, None
  - `Accuracy`: `"X"`, None
  - `Attempts`: `"YQN"` (TEXT), and `Attempts Y`=1, `Attempts N`=1, `Attempts Total`=2
- **Row 1**: identical to a clean import.
- **`Prompts given`**: value `"abc"`, typed None.
- **Running Tally**: `Y` counted, `Z` skipped (total 1).
- **`data_sheet.value_warnings`**: 7 problems in template order, and the messages
  match R6's wording:
  - `l`, `X` (Done), `2/30/2026`, `X` (Accuracy), and `YQN` naming `Q`
  - `abc`
  - `Z`

### V4. Rounding and every-unknown tally

Interpret `sample_data/008/lenient_values.json`, which holds:

- `7.5` in Trials
- `N/A` in Trials
- `QZ` in Attempts
- `-2.5` in Prompts given

Check:

- Trials holds 8 and `None` (with value `"N/A"`).
- Attempts has total 0, blank percentages, and value `"QZ"`.
- Prompts given holds -3.
- The warnings include `"7.5" is not a whole number; saved as 8` and `saved as -3`.

### V5. Batch and storage, with fakes (FR-005, FR-011, FR-013)

Run `SheetImportBatch` with a fake student store, the 007 template, a fake
`DataSheetStore`, and `read_sheet` returning the samples.

**Batch outcomes:**

- `bad_values` is SUCCEEDED, with 7 `warnings`. The `message` starts with the save
  message and then lists all 7.
- `valid_all_types` is SUCCEEDED, with `warnings == ()` and its message unchanged
  (SC-005).
- `files_to_process()` excludes both files.
- `totals()` gives `succeeded=2, with_warnings=1`.

**Cells:** `session_layout.cell_for` gives:

- the text cell `N/A` for an Unreadable Integer
- the number 8 for a Rounded one
- the text `YQN` for the Attempts marks

With a fake Sheets service, `GoogleDriveDataSheetStore` writes those three as
`stringValue`, `numberValue`, and `stringValue`. The Template Structure fingerprint
equals the one for `valid_all_types` (FR-007).

### V6. Layout errors still fail (FR-014)

Remove the `Accuracy` header from a copy of `valid_all_types.json`. The sheet fails as
`TEMPLATE_MISMATCH`, as before.

## Live check (test Google account)

### V7. Import window

1. Run `python3 program.py`, open a test Workspace, and give student `ZZ` the 007
   template.
2. Import images of `bad_values` and a clean sheet.
3. Expect the first row to show `⚠ Succeeded with warnings` in amber, listing each
   value in Details. The clean row shows `✓ Succeeded`. The summary reads
   `2 succeeded (1 with warnings), 0 failed`.
4. Double-click the warned row. In the workbook, Trials row 2 holds the text `l`,
   Accuracy holds `X`, Attempts holds `YQN` with Total 2, and the clean row is unchanged.
5. `=SUM()` over Trials skips `l` (SC-004).
6. Press Import again. Neither row is re-imported.

## Docs check

- interpreters.md rule 10 describes warnings, not `InvalidValuesError`.
- The glossary has Unreadable Value, Rounded Value, and *succeeded with warnings*.
- The constitution is at 1.9.0, with a Sync Impact Report.
- `sample_data/007/README.md` gives `bad_values.json`'s new expected outcome.
