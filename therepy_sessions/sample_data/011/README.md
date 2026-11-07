# Feature 011 samples

Synthetic files for checking Calculation Results offline (quickstart V1–V7). Every name,
word, and Student Key here is made up. Never add a real student's data (Principle I).

- `analysis_templates.json`: one template, "Trial results", saved with `TemplateStore`.
- `imports/*.json`: Imports (`StudentDataSheetImport`) for it. Load them as described in
  `../imports/README.md`. Their Student Key is `ZQ`.

## Template

| Section | Kind | Parts |
| --- | --- | --- |
| `Session` | Simple Form | `Target` (Integer) |
| `Warm-up` | Running Tally | `Y`, `N` |
| `Trials` | Table | `Word` (Text); `Trial 1`–`Trial 3` (Choice `+`, `-`); `Attempts` (Tally `Y`, `N`, `P`); `Score` (Integer); `Done` (True/False) |

| Layer | Calculation | Works out | Shown | Show as |
| --- | --- | --- | --- | --- |
| 1 | Correct trials | Sum over rows of how many of `Trial 1`–`Trial 3` are `+` | yes | Number |
| 1 | Total trials | Sum over rows of the `Attempts` total | **hidden** | Number |
| 1 | Average score | Average of `Score` | yes | Number |
| 1 | Prompted per row | Each row: `Attempts` `P` count (a Row List) | yes | Number |
| 1 | Rows done | Sum over rows of how many of `Done` are `True` | yes | Number |
| 1 | Rows at target | Sum over rows of `Score` at least `[Session/Target]` | yes | Number |
| 2 | Accuracy | Percentage of Correct trials over Total trials (menu) | yes | Percent (default) |
| 2 | Accuracy (formula) | `{Correct trials} / {Total trials} * 100` | yes | Percent (saved) |
| 2 | Prompted total | Sum over rows of `Prompted per row` | yes | Number |
| 2 | Warm-up share | `[Warm-up/Y %]` | yes | Number |

## Imports

Each has `Target` 6. All except `zero_trials.json` have the warm-up grid `Y Y N / Y N Y`:
Y = 4, N = 2, total 6, so Y % = 66.67.

`normal.json`:

| Word | Trial 1 | Trial 2 | Trial 3 | Attempts | Score | Done |
| --- | --- | --- | --- | --- | --- | --- |
| cat | + | + | - | YYP | 8 | Yes |
| dog | + | - | - | YNP | 5 | No |
| sun | + | + | + | YY | 9 | Yes |
| hat | - | + | - | NNP | 4 | No |

`blank_and_unreadable.json` has the same rows, except:

- cat's `Score` is blank.
- dog's `Trial 2` is blank, its `Attempts` is `YXP` (unknown mark `X`), and its `Score`
  is `N/A`.
- sun's `Score` is `7.5`, a Rounded Value saved as 8.
- hat's `Done` is blank.

`zero_trials.json` has 2 rows (cat, dog), with every Trial `-`, no `Attempts` marks, no
`Score`, `Done` = No, and an empty warm-up grid.

`two_tables.json` is `normal.json`, with the `Trials` rows split over two tables both
titled `Trials` (cat and dog, then sun and hat).

## Expected results (worked out by hand)

| Calculation | normal / two_tables | blank_and_unreadable | zero_trials |
| --- | --- | --- | --- |
| Correct trials | 2+1+3+1 = **7** | 2+1+3+1 = **7** (a blank holds no choice) | **0** |
| Total trials (hidden) | 3+3+2+3 = **11** | 3+2+2+3 = **10** (`X` left out) | **0** |
| Average score | 26 / 4 = **6.5** | (8 + 4) / 2 = **6** (blank and `N/A` skipped) | **empty** (no values) |
| Prompted per row | **1, 1, 0, 1** | **1, 1, 0, 1** | **0, 0** |
| Rows done | **2** | **2** (a blank holds neither) | **0** |
| Rows at target | 8, 9 ≥ 6: **2** | only 8 ≥ 6 counts, empty rows skipped: **1** | **0** (sum over no values) |
| Accuracy | 7 / 11 × 100 = **63.6363…** | 7 / 10 × 100 = **70** | 0 / 0: **empty** |
| Accuracy (formula) | **63.6363…** | **70** | **empty** |
| Prompted total | **3** | **3** | **0** |
| Warm-up share | 4 / 6 × 100 = **66.6666…** | **66.6666…** | total 0: **empty** |

`blank_and_unreadable.json` also has 3 value warnings: the unknown mark `X`, `N/A`, and
`7.5` saved as 8. No sample has a calculation warning.

The Running Tally hands its percentage over as a float, so Warm-up share equals 200/3 to
about 15 significant digits rather than exactly. That doesn't change its display.

## Expected Session Tab block for `normal.json`

After the existing rows, which end with a blank row:

| A | B | Shown as |
| --- | --- | --- |
| Analysis Results | | |
| Correct trials | 7 | `7` |
| Average score | 6.5 (`0.0#`) | `6.5` |
| Rows done | 2 | `2` |
| Rows at target | 2 | `2` |
| Accuracy | 0.636363… (`0.0#%`) | `63.64%` |
| Accuracy (formula) | 0.636363… (`0.0#%`) | `63.64%` |
| Prompted total | 3 | `3` |
| Warm-up share | 66.666… (`0.0#`) | `66.67` |
| (blank) | | |
| Prompted per row | | |
| Row | Value | |
| 1 | 1 | |
| 2 | 1 | |
| 3 | 0 | |
| 4 | 1 | |

Total trials is hidden, so it isn't listed.
