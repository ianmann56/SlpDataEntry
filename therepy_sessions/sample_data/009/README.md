# Feature 009 sample templates

`pre_analysis_templates.json` is a templates file saved by the app before Data Sheet
Analysis existed, written with that version's `TemplateStore`. It has no `"analysis"`
keys. Every name in it is made up. Never add a real student's name here (Principle I).

It is used by quickstart V4 and V10 to check that templates saved before this feature
load with no calculations, and are saved unchanged when no calculation is added. Never
regenerate it with newer code: its whole point is that it was saved by the old code.

| Template | Sections |
| --- | --- |
| Articulation trials | `Trials` table: `Word` (Text); `Trial 1`–`Trial 3` (Choice: `+`, `-`, `P`); `Attempts` (Tally: `Y`, `N`, `P`); `Words correct` (Integer) |
| Session form | `Session Info` Simple Form: `Prompts given` (Integer), `Notes` (Text) |
| Tally grid | An untitled Running Tally (`Y`, `N`, `P`), so its Section Name is `Running Tally` |
