# Data Model: Hide Analysis Results

Only one record changes. The full Data Sheet Analysis model is in
[009 data-model.md](../009-data-sheet-analysis/data-model.md).

## Calculation (changed)

`interpretation/analysis/model.py`, a frozen dataclass.

| Field | Type | Meaning |
| --- | --- | --- |
| `name` | `str` | Unchanged. |
| `description` | `str` | Unchanged. |
| `definition` | `CalculationDefinition` | Unchanged. |
| `show_in_imported_sheets` | `bool`, default `True` | **New.** Whether this calculation's result appears with each sheet imported with the template. `False` makes it a **Hidden Calculation**. |

### Rules

- A new calculation is shown (FR-002). The field's default covers every existing
  constructor call.
- The field never changes what a calculation may use or how it is worked out. Scope,
  problem checks, the Formula Legend, and renames ignore it (FR-007, FR-008).
- Renaming, editing, or moving a calculation keeps the field. Renames use
  `dataclasses.replace`, and edits apply the whole panel calculation, setting included
  (FR-011).
- When results are worked out (a later feature), every calculation that a shown
  calculation depends on is worked out, and only shown calculations' results are shown
  (FR-009).

### States

A calculation is either **shown** or **hidden**. The SLP switches it in the editor panel,
and the switch takes effect on Apply. There are no other states.

## Saved form (changed)

One optional key on each calculation object under a template's `"analysis"` key in
`templates.json`:

| Key | Present when | Value |
| --- | --- | --- |
| `show_in_imported_sheets` | The calculation is hidden | `false` |

- A missing key loads as shown (FR-006).
- Only the JSON value `false` loads as hidden. Any other value loads as shown.
- A shown calculation is written without the key, so a template whose calculations are all
  shown is saved exactly as before this feature.
- `FORMAT_VERSION` stays 2.

Example of a hidden calculation:

```json
{
  "name": "Correct trials",
  "description": "",
  "kind": "row_aggregate",
  "section": "Trials",
  "combination": "SUM",
  "measure": {"kind": "choice_count", "choice": "+", "columns": ["Trial 1", "Trial 2"]},
  "show_in_imported_sheets": false
}
```

## Unchanged

`DataSheetAnalysis`, `AnalysisLayer`, every definition, measure and operand record, the
Template Structure, Student Session Workbooks, and `students.json`.
