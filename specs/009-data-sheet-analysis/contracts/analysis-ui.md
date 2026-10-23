# Contract: Analysis Section UI

What the SLP sees and does in the Create Template and Template Details windows. The
widgets decide nothing themselves: every choice list comes from `analysis_scope`, and
every check comes from `analysis/rules.py` (layers rule 5). See
[analysis-model-and-formulas.md](analysis-model-and-formulas.md).

## Windows (FR-001a)

- `TemplateCreatorWindow` and `TemplateDetailsWindow` open maximized, through
  `tk_utils/windows.maximize(window)`.
- The SLP can restore either window to its earlier centred size (640 pixels wide), and
  maximize it again.
- Both windows stay modal (`grab_set`) as today.

## Layout (FR-001, FR-001b)

```text
┌ Template window (maximized) ───────────────────────────────────────────────────────┐
│ Name / Description / Interpreters list / Interpreter panel      (unchanged)        │
│                                                                                    │
│ Analysis                                                                           │
│ ┌ Data Sheet Analysis ───────────────────────────────────────────────────────────┐ │
│ │ Historical analysis (across a student's sessions) is not available yet.        │ │
│ │ ┌ Layers and calculations ──────────────────────────────────────────────────┐  │ │
│ │ │ ▾ Layer 1                                                                 │  │ │
│ │ │     Correct trials   Menu     Sum over rows of Trials: count of "+" …     │  │ │
│ │ │     Total trials     Menu     Sum over rows of Trials: Attempts total     │  │ │
│ │ │ ▾ Layer 2                                                                 │  │ │
│ │ │     Accuracy         Formula  {Correct trials} / {Total trials} * 100     │  │ │
│ │ └───────────────────────────────────────────────────────────────────────────┘  │ │
│ │ [Add Layer] [Delete Layer] [Add Calculation] [Remove] [Up] [Down]              │ │
│ │ ┌ Calculation ──────────────────────────────────────┐ ┌ Formula Legend ──────┐  │ │
│ │ │ Name: [Accuracy            ]                      │ │ ▾ Operations         │  │ │
│ │ │ Description: [Percent of trials correct    ]      │ │   SUM(row measure)   │  │ │
│ │ │ Build with: (•) Formula ( ) Menu                  │ │   …                  │  │ │
│ │ │ ┌──────────────────────────────────────────────┐  │ │ ▾ Variables in scope │  │ │
│ │ │ │{Correct trials} / {Total trials} * 100       │  │ │   ▾ Trials           │  │ │
│ │ │ └──────────────────────────────────────────────┘  │ │     [Trials/Attempts…│  │ │
│ │ │ ✓ Formula is OK.                                  │ │   ▾ Lower layers     │  │ │
│ │ │                              [Apply] [Cancel]     │ │     {Correct trials} │  │ │
│ │ └───────────────────────────────────────────────────┘ └──────────────────────┘  │ │
│ └────────────────────────────────────────────────────────────────────────────────┘ │
│                                                              [Save] [Cancel]       │
└────────────────────────────────────────────────────────────────────────────────────┘
```

The Formula Legend appears only while "Build with" is Formula (FR-014).

## Editing (edit mode and Create)

| Action | Behaviour |
| --- | --- |
| **Add Layer** | Appends layer *n + 1*, and selects it. |
| **Delete Layer** | Enabled only when the highest layer is selected. It asks "Delete Layer *n* and its *k* calculations?" when *k* > 0. It is refused, naming the users, if any of its calculations are used by a later layer. That can't happen while it is the highest layer, but the check is kept for safety. |
| **Add Calculation** | Applies any pending calculation change first, then opens an empty editor panel for the selected layer (or the layer of the selected calculation). New calculations start as Menu, Row Aggregate. |
| **Select a calculation** | Applies pending changes first. If they can't be applied, the old selection is restored, as with interpreters. Then it loads the calculation into the editor panel. |
| **Remove** | Removes the selected calculation, after `calculations_using` is empty. Otherwise it shows "*name* is used by: *a*, *b*." and nothing is removed (FR-017). |
| **Up / Down** | Moves the selected calculation within its layer only (FR-005). |
| **Apply** | Builds the calculation from the panel. On `calculation_problems` it shows them in a "Fix the Calculation" dialog and changes nothing. Otherwise it puts the calculation in the draft. If the name changed, it applies `PartRename(CALCULATION, "", "", old, new)` to its analysis with `apply_renames` before reporting the change, so every user of the old name follows. |
| **Cancel** (panel) | Reloads the panel from the draft, discarding unapplied changes. |

The Description entry shows the same hint as the Template Description, "Describe the sheet layout. Don't include student names." (FR-021).

Every menu picker lists only Analysis Scope entries, by label:

- **Row Aggregate.** Table, then the Row Measure kind (Number column, Tally count, or
  Choice count), then the column. A tally adds the mark or "Total". A choice count adds
  the choice, then a checklist of the Choice columns that offer it. Then Sum or Average.
- **Arithmetic.** Each input's kind (Result, Sheet value, or Number), then its value,
  then the operation.

## Formula entry (FR-012 to FR-014)

- After every change, the panel calls `formula_problems`. The message under the entry
  shows either `✓ Formula is OK.` or `✗ <message> (at character <start + 1>)`, and the
  problem's span is highlighted with a text tag.
- **Legend.** It has two groups.
  - *Operations*: `OPERATIONS`, each with its description as a second column.
  - *Variables in scope*: one node per scope table with its column references, one node
    for sheet values (grouped by section), and one node for "Lower layers" with each
    result and its Calculation Description. A first-layer calculation shows
    "(none in layer 1)" under "Lower layers".
- **Clicking a legend entry** inserts its text at the entry's cursor. For an operation,
  the first placeholder is selected. Focus returns to the entry, and the check runs
  again.

## View mode (FR-002)

- The editor panel and the analysis buttons are hidden.
- Each calculation row shows its name, its kind, and `describe_calculation(...)`.
- A calculation with a description has a child row showing it.
- An analysis with no layers shows "No calculations."

## Unsaved changes (FR-003)

- `TemplateForm.has_unapplied_changes()` is true when either the interpreter panel or
  the calculation panel differs from its snapshot.
- `TemplateForm.commit()` applies both, and returns `False` if either fails.
- Cancel and Close in the windows use these, unchanged.

## Applying a section (renames, R6)

When the interpreter panel applies an interpreter that already existed, the form:

1. Gets `config.renames(values)`, and adds a `SECTION` rename if the Section Name
   changed.
2. Replaces the interpreter in the draft, as today.
3. Calls `draft.rename_parts(renames)` so calculations follow, then redraws the analysis
   list.

A section change never fails because of analysis. Broken references are reported at
Save (FR-016).
