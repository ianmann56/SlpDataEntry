# Feature 007 sample Imports

Synthetic `StudentDataSheetImport`s for checking Table Column Types offline (quickstart
V2, V3, V9). Every value is made up, and the only Student Key is `ZZ`. Never add a real
student's sheet here (Principle I).

Each file holds an Import's `form_data`, `tables`, and `table_titles`. Load one with:

```python
import json
from collection.collection_headers import StudentDataSheetImport

with open("sample_data/007/valid_all_types.json", encoding="utf-8") as f:
    data = json.load(f)
sheet_import = StudentDataSheetImport(data["form_data"], data["tables"], data["table_titles"])
```

They are written for a template with three sections:

- a table section titled `Words`: Word (Text), Trials (Integer), Score (Decimal), Done
  (True/False), When (Date), Accuracy (Choice `+`, `-`, `P`), and Attempts (Tally `Y`,
  `N`, `P`)
- a Simple Form section with the field `Prompts given` (Integer)
- a Running Tally section titled `Tally Grid`, with the options `Y`, `N`, `P`

| File | Checks |
| --- | --- |
| `valid_all_types.json` | Every column type reads as a typed value, including `p` matching the choice `P`, `✓` as true, and a blank row (empty cells, Attempts counts of 0, blank percentages). The grid reads as `YYNPY`. |
| `running_tally.json` | The Running Tally grid `Y Y N / P Y` saves one row: `YYNPY`, Y=3 N=1 P=1, total 5, 60% / 20% / 20%. |
| `simple_form.json` | `Prompts given` saves as the number 12. |
| `bad_values.json` | The sheet fails with `INVALID_VALUES`, naming every bad value: `l` in Trials, `X` in Done, `2/30/2026` in When, `X` in Accuracy, `YQN` in Attempts (naming the bad mark `Q`), `Z` in the Running Tally, and `abc` in Prompts given. |
