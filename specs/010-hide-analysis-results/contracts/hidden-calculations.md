# Contract: Hidden Calculations

Changes to the interfaces in
[009 analysis-model-and-formulas.md](../../009-data-sheet-analysis/contracts/analysis-model-and-formulas.md)
and [009 analysis-ui.md](../../009-data-sheet-analysis/contracts/analysis-ui.md). Anything
not listed here is unchanged.

## Model: `interpretation/analysis/model.py`

```python
@dataclass(frozen=True)
class Calculation:
  name: str
  description: str
  definition: CalculationDefinition
  show_in_imported_sheets: bool = True
```

- `Calculation(name, description, definition)` still builds a shown calculation.
- `is_menu`, `row_list_section`, and `result_references()` don't depend on the new field.
- `DataSheetAnalysis` and its `with_*` methods are unchanged. They store whole `Calculation`
  values, so the field travels with each one.

## Serialization: `interpretation/analysis/serialization.py`

| Function | Change |
| --- | --- |
| `analysis_to_json` | A hidden calculation's object gets `"show_in_imported_sheets": false`. A shown one gets no new key. |
| `analysis_from_json` | A calculation object whose `show_in_imported_sheets` is exactly `false` loads hidden. A missing key, or any other value, loads shown. No new error is raised. |

Round trip: `analysis_from_json(analysis_to_json(a)) == a` for every analysis `a`. For an
analysis saved before this feature, `analysis_to_json(analysis_from_json(d)) == d`.

## Unchanged by contract

`analysis_scope`, `calculation_problems`, `analysis_problems`, `calculations_using`,
`apply_renames`, `parse_formula`, and `FormulaLegend` ignore `show_in_imported_sheets`.
Their output for an analysis doesn't change when calculations in it are hidden or shown.

## UI: `AnalysisEditor` (`interpretation/template_manager/analysis_editor.py`)

### Editor panel (edit mode and Create Template)

| Row | Contents |
| --- | --- |
| 0 | Name |
| 1 | Description |
| 2 | Description hint |
| 3 | **New:** ☑ Show in imported sheets |
| 4 | Build with: Menu / Formula |
| 5 | Panel message (when no calculation is open) |
| 6 | Menu fields or formula entry with its Formula Legend |
| 7 | Apply / Cancel |

- The check box is ticked for a new calculation, and shows the setting of a selected one.
- Changing it counts as an unapplied change. Apply puts it into the Template Draft, and
  Cancel restores the applied setting.
- It is disabled whenever the rest of the panel is.

### Calculation list (view mode, edit mode, Create Template)

- A hidden calculation's row reads `<name> (hidden)` and is drawn in a muted color.
- A shown calculation's row reads `<name>`, as before.
- In view mode the list stays read-only, and the panel isn't shown.

## Later contract: working out results (not built here)

The feature that works out results for imported sheets must:

1. Work out every calculation that some shown calculation depends on, directly or through
   lower layers, whether or not it is hidden.
2. Show, with each imported sheet, the results of shown calculations only.
