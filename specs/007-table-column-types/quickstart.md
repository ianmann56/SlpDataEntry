# Quickstart: Validating Table Column Types

This guide shows the feature works end to end. Record shapes are in
[data-model.md](data-model.md), and signatures are in [contracts/](contracts/).

**Privacy (Principle I)**: Use only synthetic sheets with made-up Student Keys (e.g.
`ZZ`), a test Google account, and a copy of the templates file. Never use a real
student's sheet or the SLP's real Drive.

## Prerequisites

```sh
source .venv/bin/activate
cd therepy_sessions
cp <your templates file> /tmp/templates-before-007.json   # an old-format file, for V7
```

Each offline check (V1–V6) is a throwaway script run from `therepy_sessions/` with
`python3 -I -c` or a scratch file in `$TMPDIR`. These scripts aren't committed (R11).

## Offline checks (no network)

### V1. Reading values (FR-008 to FR-011, spec Edge Cases)

Call `value_types.read_value` / `read_tally` with:

| Type | Input → expected |
| --- | --- |
| Integer | `" 7 "` → 7; `"7.0"` → 7; `"3.5"`, `"l"`, `"1,200"` → `ValueReadError` |
| Decimal | `"2.5"` → 2.5; `".5"` → 0.5; `"3"` → 3.0; `"70%"` → error |
| True/False | `"Y"`, `"yes"`, `"✓"`, `"1"` → True; `"n"`, `"0"` → False; `"X"` → error; `""` → None |
| Date | `"10/3/2026"`, `"10-3-26"` → 2026-10-03; `"2/30/2026"` → error |
| Choice `+ - P` | `"p"` → `"P"`; `"X"` → error |
| Text | `" a b "` → `" a b "` (unchanged) |
| Tally `Y N P` | `"YyN P"` → marks `YYNP`, Y=2 N=1 P=1, total 4, Y=0.5; `""` → total 0 and percentages None; `"YXN"` → error |

### V2. Interpreters and every bad cell (FR-012, R5)

Build a `TableInterpreter` with the columns Word (Text), Trials (Integer), Accuracy
(Choice `+ - P`), and Attempts (Tally `Y N P`). Give it a synthetic Import whose rows
include `l` in Trials on row 3 and `X` in Accuracy on row 5.

- Expect one `InvalidValuesError` naming both cells, with column, row, and value.
- Fix both, and expect each row to hold typed scalars plus the 8 Attempts keys
  (`Attempts`, `Attempts Y/N/P`, `Attempts Total`, `Attempts Y/N/P %`).
- `section_keys()` lists them in that order.

### V3. Running Tally summary (FR-021)

A `RunningTallyInterpreter` with options `Y N P`, given the grid `[["Y","Y","N"],["P","Y"]]`,
emits one row: marks `YYNPY`, Y=3 N=1 P=1, total 5, Y=0.6.

### V4. Configuration rules (FR-004, FR-005, R3, R8)

`validate_template` reports each of these, naming the column:

- a Choice column with no choices
- duplicate choices `p` / `P`
- a tally mark `YY`
- a Text column named `Attempts Y` next to the Tally column `Attempts`

`check_new_option(TALLY, "YY", [])` returns a message.

### V5. Serialization (FR-006, FR-018, FR-023, R7)

- Load `/tmp/templates-before-007.json` with the new code:
  - table columns come out as Text, or as Choice when they had `column_choices`
  - form fields come out as Text
  - Running Tally characters become options with blank descriptions
- Serialize, deserialize, and serialize again: the output is identical, and it's in the
  new shape.

### V6. Cells, key rows, and structure (FR-014 to FR-017, FR-022, FR-024, SC-003)

- `cell_for` gives `numberValue` for INT and DECIMAL, `boolValue` for BOOLEAN, the
  serial 46298 with the DATE format for 2026-10-03, 0.5 with the PERCENT format, and
  text for Choice.
- `workbook_key_rows` lists every Choice and Tally option with its description, or the
  "no codes" row.
- `structure_fingerprint`:
  - unchanged after switching Trials from Integer to Decimal, or editing any description
  - changed after adding a tally option
  - unchanged for an old-format template with no tallies, compared with the code before
    this feature

With a fake Sheets service, `GoogleDriveDataSheetStore.save` creates a workbook with the
session tab, then `Workbook Key` last, carrying the `slpWorkbookKey` metadata. A second
save:

- adds the new tab before the key tab
- replaces the key tab in the same batch
- never treats the key tab as a session or as empty

## Live checks (test Google account, synthetic sheets)

### V7. Configure and view (US1–US2, US5–US6, SC-001)

```sh
python3 program.py <args as usual>
```

1. In Setup → Data Sheet Templates, create a template with:
   - a table section: Word (Text), Trials (Integer), Score (Decimal), Done (True/False),
     When (Date), Accuracy (Choice `+` correct, `-` incorrect, `P` with prompt), and
     Attempts (Tally `Y` yes, `N` no, `P` prompted)
   - a Simple Form section: "Prompts given" (Integer)
   - a Running Tally section titled to match a second table, with the same options
2. Time it: it should take under 5 minutes.
3. Check the rules: try adding the tally mark `YY`, and saving a Choice column with no
   choices. Each one is refused with a message.
4. Open the template in view mode. Every column and field shows its type, and every
   option shows its description.

### V8. Import and the workbook (US1–US3, US5–US6, FR-014 to FR-016, FR-024, SC-002, SC-006)

Import a synthetic sheet for `ZZ` that fills every column validly, including one blank
row. In the workbook:

- Trials, Score, and Prompts given are numbers; SUM works.
- Done shows TRUE/FALSE.
- When is a date that sorts.
- Accuracy shows the codes.
- Attempts shows the marks, counts, a total, and percentages; the blank row has 0s and
  blank percentages.
- The Running Tally block is one row with the same summary.
- The last tab is `Workbook Key`, listing every code with its meaning.

### V9. Bad values fail the sheet (FR-012, SC-004)

Import a synthetic sheet with `abc` in Trials and `X` in Done.

- The row fails with "Some values on the sheet don't fit template …", naming both cells.
- No tab is added, and the key tab is unchanged.
- A valid sheet imported in the same run still succeeds.

### V10. Existing templates and workbooks (US4, FR-022, SC-003)

Use the copied old templates file.

- A table-only template imports into its existing workbook, with values as before (text).
- An old Running Tally template starts a new workbook, and the old one is untouched.
- An old workbook gets a `Workbook Key` tab on its next save.

### V11. Structure changes (FR-017)

Edit the V7 template:

- Change Trials to Decimal and edit a description, then import. The sessions still go
  to the same workbook, and the key shows the new description.
- Add tally option `X`, then import. A new workbook is started.
