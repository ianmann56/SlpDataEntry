# Feature 008 sample Imports

Synthetic `StudentDataSheetImport`s for checking Nullable Field Values offline
(quickstart V4). Every value is made up, and the only Student Key is `ZZ`. Never add a
real student's sheet here (Principle I).

They load and use the same three-section template as the
[007 samples](../007/README.md): a `Words` table section, a Simple Form section with the
Integer field `Prompts given`, and a `Tally Grid` Running Tally with the options `Y`, `N`,
`P`.

| File | Checks |
| --- | --- |
| `lenient_values.json` | The sheet succeeds with four warnings. Trials row 1 `7.5` is saved as the number 8 (a Rounded Value). Trials row 2 `N/A` has no typed value and is saved as the text `N/A` (an Unreadable Value). Attempts row 1 `QZ` has every count and the total at 0, blank percentages, and the marks cell `QZ`. `Prompts given` `-2.5` is saved as -3. Every other value reads as it would in `valid_all_types.json`. |
