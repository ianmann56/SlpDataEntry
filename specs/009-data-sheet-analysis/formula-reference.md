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
| Choice count | `COUNT("+", [Trials/Trial 1], [Trials/Trial 2])` | Only inside `SUM` or `AVERAGE` |
| Running Tally option count | `COUNT("Y", [Running Tally])` *(new)* or `[Running Tally/Y]` (still valid) | Anywhere a value can go, but not inside `SUM` or `AVERAGE` |
| Running Tally total or option percentage | `[Running Tally/Total]`, `[Running Tally/Y %]` | Anywhere a value can go, but not inside `SUM` or `AVERAGE` |
| Simple Form Integer or Decimal field | `[Session Info/Prompts given]` | Anywhere a value can go, but not inside `SUM` or `AVERAGE` |
| Lower-layer result | `{Correct trials}` | Anywhere a value can go, but not inside `SUM` or `AVERAGE` |

See also: the grammar in [research.md](research.md) R3 and
[contracts/analysis-model-and-formulas.md](contracts/analysis-model-and-formulas.md),
which T044 updates to match this table.
