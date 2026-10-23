# Data Model: Data Sheet Analysis

Entities for [spec.md](spec.md), with the decisions from [research.md](research.md).
Everything here is pure data in `interpretation/analysis/`, with no Tkinter and no I/O.

## Template (changed)

`StudentDataSheetTemplate` gains:

| Field | Type | Notes |
| --- | --- | --- |
| `analysis` | `DataSheetAnalysis` | Empty (no layers) by default and for templates saved before this feature (FR-019). |

`TemplateCreateDto`, `TemplateEditDto`, and `TemplateDraft` gain `analysis` too. The
draft holds its own copy, so edits never touch the saved template until Save (FR-003).

## DataSheetAnalysis

| Field | Type | Notes |
| --- | --- | --- |
| `layers` | `tuple[AnalysisLayer, ...]` | In order. Layer *n* is `layers[n - 1]`. |

Rules:

- Only the highest layer may be removed (FR-004).
- `calculations_using(name)` lists the calculations whose definition references the
  calculation `name`. It is computed in `rules.py` from each calculation's
  `result_references()`. A calculation is never removed while that list is non-empty
  (FR-017).

## AnalysisLayer

| Field | Type | Notes |
| --- | --- | --- |
| `calculations` | `tuple[Calculation, ...]` | In order (FR-005). May be empty. A calculation never moves to another layer. |

## Calculation

| Field | Type | Notes |
| --- | --- | --- |
| `name` | `str` | Not blank, and unique in the template ignoring letter case and surrounding spaces (FR-007). Never identifies a student (FR-021). |
| `description` | `str` | The optional Calculation Description, `""` when none (FR-007a). |
| `definition` | `RowAggregate \| Arithmetic \| Formula` | A menu calculation (the first two) or a Formula calculation (FR-008). |

## RowAggregate (menu)

| Field | Type | Notes |
| --- | --- | --- |
| `section` | `str` | A table section's Section Name. |
| `measure` | `RowMeasure` | What each row gives. |
| `combination` | `Combination` | `SUM` or `AVERAGE`. |

`RowMeasure` is one of:

| Variant | Fields | Valid when |
| --- | --- | --- |
| `NumberColumnMeasure` | `column: str` | The column is Integer or Decimal. |
| `TallyCountMeasure` | `column: str`, `mark: str \| None` | The column is Tally. `mark` is one of its tally options, or `None` for the tally's total. |
| `ChoiceCountMeasure` | `choice: str`, `columns: tuple[str, ...]` (one or more, no repeats) | Every column is Choice and offers `choice`, matched ignoring letter case and surrounding spaces. |

## Arithmetic (menu)

| Field | Type | Notes |
| --- | --- | --- |
| `left`, `right` | `Operand` | Two inputs. |
| `operation` | `ArithmeticOperation` | `ADD`, `SUBTRACT`, `MULTIPLY`, `DIVIDE`, or `PERCENTAGE` (left ÷ right × 100). |

`Operand` is one of:

| Variant | Fields | Valid when |
| --- | --- | --- |
| `ResultOperand` | `calculation: str` | Names a calculation in a lower layer (FR-006). |
| `SheetValueOperand` | `section: str`, `value: str` | Names a Numeric Sheet Value of that section. |
| `NumberOperand` | `number: Decimal` | Always valid. |

## Formula

| Field | Type | Notes |
| --- | --- | --- |
| `text` | `str` | Exactly as typed, and saved as typed (FR-018). The grammar is in [contracts/analysis-model-and-formulas.md](contracts/analysis-model-and-formulas.md). |

## SectionParts (new interpreter output)

What a section offers to analysis, from `SessionDataSectionInterpreterBase.analysis_parts()`.
The default offers nothing.

| Field | Type | Notes |
| --- | --- | --- |
| `table_columns` | `list[TableColumnPart]` | A table section's columns, in template order. |
| `sheet_values` | `list[str]` | Names of the section's Numeric Sheet Values, in template order. |

`TableColumnPart` holds `name: str`, `column_type: ColumnType`, `choices: list[str]`, and
`tally_marks: list[str]`.

Sheet values by section type:

| Section type | `sheet_values` |
| --- | --- |
| Simple Form | Its Integer and Decimal fields' names. |
| Running Tally | Each mark, then `Total`, then each `<mark> %`. |
| Table | None (its columns are offered as `table_columns`). |

## Section Name

A section's title, or, when it is untitled, its type's fallback name (`Table`, `Form`,
`Running Tally`). These are the names its messages already use. It is exposed as
`SessionDataSectionInterpreterBase.section_name`. A Section Name used by more than one
section, ignoring letter case and surrounding spaces, is **ambiguous**. Analysis can't
use it until one of the sections is given a different title (research R2).

## AnalysisScope (derived, never saved)

What one calculation in one layer may use, built by
`analysis_scope(interpreters, analysis, layer_number)`:

| Field | Type | Notes |
| --- | --- | --- |
| `sheet_values` | `list[ScopeEntry]` | Numeric Sheet Values of unambiguous sections. |
| `tables` | `list[ScopeTable]` | Unambiguous table sections that have at least one Integer, Decimal, Tally, or Choice column. |
| `results` | `list[ScopeEntry]` | Calculations in layers 1 to *layer_number − 1*, with descriptions. |

A `ScopeEntry` holds `label` (shown in the menu and the legend), `reference` (the exact
formula text, escaped), and `description`. A `ScopeTable` holds its Section Name, its
Number columns, its Tally columns with their marks, and its Choice columns with their
choices, each with its formula reference.

## PartRename (derived, never saved)

One rename reported by the editor when a section or calculation is applied (research
R6):

| Field | Type | Notes |
| --- | --- | --- |
| `kind` | `PartKind` | `SECTION`, `ITEM` (a column or field), `OPTION` (a choice or tally mark), or `CALCULATION`. |
| `section` | `str` | The Section Name the part belongs to (its new name for `SECTION`). `""` for `CALCULATION`. |
| `item` | `str` | The column or field an `OPTION` belongs to. `""` otherwise. |
| `old`, `new` | `str` | The name before and after. |

## Saved form (`templates.json`)

The `"analysis"` key is added to a template entry only when there is at least one layer
(research R8):

```json
{
  "id": "4",
  "name": "Articulation trials",
  "description": "",
  "interpreters": [ ... ],
  "analysis": {
    "layers": [
      {
        "calculations": [
          {
            "name": "Correct trials",
            "description": "Trials marked + in any Trial column",
            "kind": "row_aggregate",
            "section": "Trials",
            "combination": "SUM",
            "measure": {"kind": "choice_count", "choice": "+", "columns": ["Trial 1", "Trial 2", "Trial 3"]}
          },
          {
            "name": "Total trials",
            "description": "",
            "kind": "row_aggregate",
            "section": "Trials",
            "combination": "SUM",
            "measure": {"kind": "tally_count", "column": "Attempts", "mark": null}
          }
        ]
      },
      {
        "calculations": [
          {
            "name": "Accuracy",
            "description": "Percent of trials correct",
            "kind": "arithmetic",
            "left": {"kind": "result", "calculation": "Correct trials"},
            "operation": "PERCENTAGE",
            "right": {"kind": "result", "calculation": "Total trials"}
          },
          {
            "name": "Accuracy with partial",
            "description": "",
            "kind": "formula",
            "formula": "({Correct trials} + {Partial trials}) / {Total trials} * 100"
          }
        ]
      }
    ]
  }
}
```

Other saved shapes:

- A `number_column` measure saves `{"kind": "number_column", "column": ...}`.
- A sheet value operand saves `{"kind": "sheet_value", "section": ..., "value": ...}`.
- A number operand saves `{"kind": "number", "number": "2.5"}`, as a string.

Enum members are saved by name. A missing `"description"` loads as `""`.

## State transitions

```text
saved template ──Edit──▶ draft (copy of analysis)
draft analysis ──Apply in editor panel──▶ draft analysis changed (+ renames applied, R6)
draft analysis ──Apply section with renames──▶ references rewritten in draft
draft ──Save──▶ problems()? ──none──▶ saved template replaced
                         └─some──▶ Validation Error, draft kept
draft ──Cancel──▶ discarded
```
