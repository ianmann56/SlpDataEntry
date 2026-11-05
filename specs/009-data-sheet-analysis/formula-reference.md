# Formula Reference: How Template Parts Are Written

How a Formula calculation refers to each part of a template, and where in a formula
each may go. This is the target for task T044. The entries marked *(new)* are added by
that task; everything else already works.

The rule underneath: anything with one value per **row** goes inside `SUM` or
`AVERAGE`. Anything with one value per **sheet** goes outside them.

| Meaning | Written as | Where it can go |
|---|---|---|
| Number column (Integer or Decimal) | `[Trials/Words correct]` | Only inside `SUM` or `AVERAGE` |
| Tally count of one option in a Tally column | `[Trials/Attempts/P]` (still valid) or `COUNT("P", [Trials/Attempts])` *(new)* | Only inside `SUM` or `AVERAGE` |
| Tally column total | `[Trials/Attempts/Total]` | Only inside `SUM` or `AVERAGE` |
| Choice count | `COUNT("+", [Trials/Trial 1], [Trials/Trial 2])`; a True/False column counts `"True"` or `"False"` | Only inside `SUM` or `AVERAGE` |
| Lower-layer Row List | `{Correct per row}` | Only inside `SUM` or `AVERAGE`, alone, e.g. `AVERAGE({Correct per row})` |
| Running Tally option count | `COUNT("Y", [Running Tally])` *(new)* or `[Running Tally/Y]` (still valid) | Anywhere a value can go, but not inside `SUM` or `AVERAGE` |
| Running Tally total or option percentage | `[Running Tally/Total]`, `[Running Tally/Y %]` | Anywhere a value can go, but not inside `SUM` or `AVERAGE` |
| Simple Form Integer or Decimal field | `[Session Info/Prompts given]` | Anywhere a value can go, but not inside `SUM` or `AVERAGE` |
| Lower-layer single-number result | `{Correct trials}` | Anywhere a value can go, but not inside `SUM` or `AVERAGE` |

## Comparisons and COUNT

A comparison `=`, `<>` (or `!=`), `<`, `<=`, `>`, `>=` gives 1 when it holds and 0 when it
doesn't. Either side can be any value, or arithmetic on values. Compare two values at a time.

| Meaning | Written as |
|---|---|
| Did a result meet its target? | `{Accuracy} >= 70` |
| Rows where a column passes a sheet value | `SUM([Trials/Words correct] >= [Session Info/Prompts given])` |
| Rows where a Row List is at least 2 | `SUM({Plus per row} >= 2)` |
| Share of rows (0 to 1) | `AVERAGE([Trials/Attempts/P] > 0)` |
| A choice or True/False column holds a choice | `[Trials/Trial 1] = "+"`, `[Tone/Pitch] <> "True"` (only `=` or `<>`, only inside `SUM`, `AVERAGE`, or `COUNT`) |
| How many conditions hold, per row | `SUM(COUNT([Tone/Pitch] = "True", [Tone/Speed] = "True", [Tone/Body] = "True") >= 2)` |
| How many conditions hold, for the sheet | `COUNT({Accuracy} >= 70, {Prompted rate} < 20)` |

Inside `SUM` or `AVERAGE`, the row measure can be any expression (e.g.
`SUM([T/A] + [T/B])`) that uses at least one value from the rows of one table. Single
values there (numbers, sheet values, single-number results) are the same for every row.
`SUM` and `AVERAGE` can't be nested.

See also: the grammar in [research.md](research.md) R3 and
[contracts/analysis-model-and-formulas.md](contracts/analysis-model-and-formulas.md),
which T044 updates to match this table.
