# Feature 010 sample templates

`analysis_templates.json` is a templates file saved by the app before hidden calculations
existed, written with that version's `TemplateStore`. Its analysis has no
`show_in_imported_sheets` keys. Every name in it is made up. Never add a real student's
name here (Principle I).

It is used by quickstart V1, V2, and V4–V6 to check that an analysis saved before this
feature loads with every calculation shown, and is saved unchanged while none is hidden.
Never regenerate it with newer code: its whole point is that it was saved by the old code.

| Template | Section | Columns |
| --- | --- | --- |
| Accuracy trials | `Trials` table | `Word` (Text); `Trial 1`–`Trial 3` (Choice: `+`, `-`) |

| Layer | Calculation | Works out |
| --- | --- | --- |
| 1 | Correct trials | Sum over rows of how many of `Trial 1`–`Trial 3` are `+` |
| 1 | Incorrect trials | Sum over rows of how many of `Trial 1`–`Trial 3` are `-` |
| 2 | Accuracy | `{Correct trials} / ({Correct trials} + {Incorrect trials}) * 100` |
