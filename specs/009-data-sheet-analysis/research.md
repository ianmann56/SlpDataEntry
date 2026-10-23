# Research: Data Sheet Analysis

Phase 0 decisions for [spec.md](spec.md). Each entry gives the decision, why, and what
else was considered. The Technical Context in [plan.md](plan.md) had no open
NEEDS CLARIFICATION items. The spec left the formula syntax to planning (R3).

Feature 008 (nullable field values) is planned but not implemented. Nothing here depends
on it: this feature only configures calculations, and never reads a sheet.

## R1. Where Data Sheet Analysis lives

**Decision**: A new pure package, `interpretation/analysis/`, holds the model, formula
parser, scope, rules, renames, and serialization. `StudentDataSheetTemplate` gains an
`analysis: DataSheetAnalysis` property (empty by default). The template's interpreters
are unchanged, apart from one optional read-only method (R5). The editor widgets live
beside the other template widgets in `interpretation/template_manager/`.

**Rationale**: Analysis belongs to the template (FR-018), but it is not a section, so it
is not an interpreter type. Keeping its rules out of Tkinter follows layers rule 5, and
lets every rule be checked offline. The package imports no I/O, so Interpretation stays
pure (layers rule 3), and nothing in `storage/` reads it, so the Template Structure
can't change (FR-020).

**Alternatives considered**:
- *Analysis as a new interpreter type.* Rejected: it reads no part of the sheet, would
  enter the Template Structure through `section_keys()`, and would appear in the
  interpreter list.
- *Rules inside the editor widgets.* Rejected by layers rule 5.

## R2. How calculations refer to template parts

**Decision**: Everything is referenced by name, in menu calculations and formulas alike:

- a section by its **Section Name** (its title, or its type's fallback name, such as
  "Table", when untitled)
- a column or field by its name, and a choice or tally option by its value or mark
- a calculation by its name

Names match ignoring letter case and surrounding spaces, which are already the
uniqueness rules for column, field, and option names (`option_rules.name_problems`).
Calculations get no id.

**Rationale**:
- One rule covers menu and formula calculations, and renames are handled the same way
  for both (R6).
- The spec's edge case "remove a column and add one with the old name" then behaves the
  same everywhere: the new column is checked by name and type.
- Sections already have stable ids. But a formula has to name the section in text, so
  ids would only help menu calculations, and would make the two kinds behave
  differently when a section is removed and re-added.

**Ambiguous sections**: Two sections can end up with the same Section Name, for example
two untitled Simple Form sections, both "Form". Such a section is not offered, and a
reference to that name is a problem: "Give one of the sections named "Form" a title."

**Alternatives considered**:
- *Ids for sections, columns, and options.* Rejected: columns and options have no ids,
  and adding them would change every template's saved shape.
- *Ids only for calculations.* Rejected: formulas still need the name, so the rewrite
  machinery is needed regardless, and two reference styles would mean two code paths.

## R3. Formula syntax

**Decision**: A small spreadsheet-like language.

```text
formula    := expr
expr       := term (("+" | "-") term)*
term       := unary (("*" | "/") unary)*
unary      := "-" unary | primary
primary    := NUMBER | result_ref | value_ref | aggregate | "(" expr ")"
aggregate  := ("SUM" | "AVERAGE") "(" measure ")"
measure    := column_ref | "COUNT" "(" STRING ("," column_ref)+ ")"
result_ref := "{" name "}"                       a lower-layer calculation's result
value_ref  := "[" section "/" item "]"           a Numeric Sheet Value
column_ref := "[" section "/" column ("/" part)? "]"   a table column, in a Row Measure
```

- `NUMBER` is digits with an optional decimal point (`3`, `2.5`, `.5`).
- `STRING` is a double-quoted choice value (`"+"`, `"NR"`).
- Function names ignore letter case.
- Spaces between tokens are ignored.
- Inside `[...]` and `{...}`, a `\` escapes the next character, so a name may hold `/`,
  `]`, `}`, or `\`. The Formula Legend always inserts names with these escapes.
- `part` names a Tally column's measure: a tally mark (`P`) or `Total`. A mark is one
  character, so it can never be confused with `Total`.

How each Row Measure (FR-010) and Numeric Sheet Value is written:

| Meaning | Written as |
| --- | --- |
| Number column (Integer or Decimal) | `[Trials/Words correct]` |
| Tally count of one option | `[Trials/Attempts/P]` |
| Tally total | `[Trials/Attempts/Total]` |
| Choice count | `COUNT("+", [Trials/Trial 1], [Trials/Trial 2])` |
| Simple Form Integer or Decimal field | `[Session Info/Prompts given]` |
| Running Tally option count, total, or percentage | `[Running Tally/Y]`, `[Running Tally/Total]`, `[Running Tally/Y %]` |
| Lower-layer result | `{Correct trials}` |

Examples:

- `SUM([Trials/Attempts/P])`
- `AVERAGE(COUNT("+", [Trials/Trial 1], [Trials/Trial 2], [Trials/Trial 3]))`
- `({Correct trials} + {Partial trials}) / {Total trials} * 100`

`SUM` and `AVERAGE` take exactly one Row Measure. Every column in it must belong to the
same table section, and a Row Measure may appear only inside them. So every formula
aggregation is exactly one menu Row Aggregate, and every menu calculation can be written
as a formula (SC-006). Percentage has no operator of its own: it is written `a / b * 100`.

**Rationale**:
- Square brackets, curly braces, and a function-call style are familiar from
  spreadsheets, which the SLP already uses.
- Separate brackets for sheet data and results make a formula's dependencies visible at a
  glance, and keep the scope checks simple: a `{}` reference must be a lower layer.
- Requiring a single Row Measure inside an aggregation keeps the meaning of an empty cell
  unambiguous. The Average skips empty rows (spec Assumptions), which would be unclear for
  row-level arithmetic such as `SUM([a] - [b])`.

**Alternatives considered**:
- *Bare names (`Correct trials / Total trials`).* Rejected: names hold spaces and
  symbols, which FR-012 requires to be delimited.
- *Row-level arithmetic inside `SUM` and `AVERAGE`.* Rejected for now: blank-cell meaning
  is unclear, and the menu can't express it.
- *A `PERCENT(a, b)` function.* Not needed, since `* 100` is clearer and shorter. It can
  be added later without breaking saved formulas.
- *Evaluating with Python `eval`.* Rejected outright: formulas are parsed, never executed
  as code. This feature doesn't evaluate them at all.

## R4. Parsing and live checking

**Decision**: A hand-written tokenizer and recursive-descent parser in
`interpretation/analysis/formula.py`. It returns a `FormulaParse`: a syntax tree with the
character span of every token and reference, or the first `FormulaProblem` (message,
start, end). Checking against a scope is a separate step (R5), which adds problems for
unknown or out-of-scope references, using each reference's span. The editor re-checks
after every change to the formula entry (its `<<Modified>>` event, which covers typing, pasting, and inserts from the legend), and
shows either the first problem, with its position as "at character N" plus a highlight of
the span, or "Formula is OK." Apply runs the same check and refuses a formula with a
problem (FR-013).

A Formula Legend operation is inserted with placeholders written `<row measure>`,
`<choice>`, `<column>`, and so on. The tokenizer reads `<...>` as a placeholder token, so
the parser can report "Fill in <row measure>" at its position. The inserted placeholder
is selected, so typing replaces it.

**Rationale**:
- The grammar has about ten rules, so a parser library would add a dependency for no
  gain.
- Spans are needed three times: for the problem position, for the highlight, and for
  rewriting references on rename (R6).
- Parsing is microseconds, so re-checking on every key needs no debounce.

**Alternatives considered**:
- *`lark` or `pyparsing`.* Rejected: a new runtime dependency (constitution Technology
  Constraints) for a tiny grammar.
- *Python `ast` with a whitelist.* Rejected: Python's syntax has no `[a/b]` or `{x}`
  forms, and its error positions aren't in the SLP's terms.

## R5. What a calculation may use (Analysis Scope)

**Decision**: One pure function, `analysis_scope(interpreters, analysis, layer_number)`,
returns the **Analysis Scope** of a calculation in a layer:

- its Numeric Sheet Values
- its tables, each with its Number columns, Tally columns (marks and Total), and Choice
  columns (with their choices)
- its lower-layer results, with each calculation's description

Every entry carries the exact text a formula uses for it. The menu's choices, the Formula
Legend, formula checking, and the save-time check all read this one scope, so they can't
disagree (FR-006, FR-014, FR-015).

Sections describe themselves to the scope through a new optional method on
`SessionDataSectionInterpreterBase`, `analysis_parts() -> SectionParts`. Its default is
that the section offers nothing.

- `TableInterpreter` returns its columns with their types, choices, and tally marks.
- `SimpleFormInterpreter` returns its Integer and Decimal fields as sheet values.
- `RunningTallyInterpreter` returns each mark, `Total`, and each `<mark> %` as sheet
  values.

**Rationale**: Principle V keeps the core flow free of type checks; Storage, for example,
never checks interpreter types. A new interpreter type opts in by overriding one method,
and the analysis code never imports interpreter classes.

**Alternatives considered**:
- *`isinstance` checks in the scope code.* Rejected: it breaks pluggability, and every
  new type would need an edit to `analysis/`.
- *Reusing `section_keys()`.* Rejected: those are storage keys (such as
  `Attempts Y %`), and carry no types or table structure.

## R6. Renames

**Decision**: A rename is detected where it happens, in the editor, and applied to the
draft's analysis by a pure function.

1. **Tracking.** `TypedItemEditor` and `OptionListEditor` remember each item's *loaded
   name*: the name it had when the form was loaded, or none for an item added since. An
   item whose current name differs from its loaded name was renamed in place. Removing
   an item and adding a new one is a removal and an addition (spec edge case).
2. **Reporting.** `InterpreterConfig` gains an optional `renames(values)` method,
   returning `list[PartRename]` for the column, field, and option renames in the form's
   values (default `[]`). The Template Form adds a section rename itself when an applied
   interpreter keeps its id but its Section Name changes.
3. **Applying.** `TemplateDraft.rename_parts(renames)` calls
   `analysis.renames.apply_renames(analysis, renames)`. This rewrites menu calculations'
   fields, and formula text by replacing only the spans of matching references (R4). It
   re-escapes the new name, and leaves the rest of the text unchanged (FR-016a).
4. **Calculations.** Renaming a calculation in the editor panel and applying it renames
   every `{old}` reference in higher layers, and every menu calculation input that names
   it.

The renames are applied in the same step that applies the interpreter, so the draft is
never left with references to the old name.

**Rationale**:
- Only the editor knows whether a changed name means "renamed" or "replaced".
- Comparing the old and new column lists can't tell a rename from a remove-and-add once
  the SLP has also reordered or removed columns.
- Rewriting by span, not by text search, can't touch a matching name inside a different
  reference or a choice string.

**Alternatives considered**:
- *Inferring renames by position.* Rejected for the reason above.
- *Stable ids for columns and options.* Rejected in R2.
- *Re-printing a formula from its syntax tree.* Rejected: FR-018 keeps formulas exactly
  as typed, including spacing.

## R7. Checking a draft's analysis

**Decision**: `analysis_problems(interpreters, analysis) -> list[str]` returns every
problem, in layer and calculation order, each naming the calculation:

- a blank name, or a name used more than once ignoring letter case and surrounding spaces
  (FR-007)
- a reference to a section, column, field, option, or calculation that doesn't exist, is
  ambiguous (R2), has the wrong type, or is in the same or a higher layer (FR-006,
  FR-016)
- a formula that does not parse

`TemplateDraft.problems()` appends these after the interpreter problems, so Save shows
them in the existing "Validation Error" dialog (FR-016).

Deleting a calculation calls `calculations_using(analysis, name)` first, and is refused
while the list is not empty (FR-017). Deleting a layer is offered only for the highest
layer (FR-004). Applying a calculation runs the same checks for that one calculation, so
problems show up as early as possible. Problems in calculations that a section change
broke are reported at Save, not when the section is applied, because applying a section
must not be blocked by the analysis.

**Rationale**: This reuses the existing save-time problem flow. It also matches FR-016:
a broken reference blocks saving but never blocks editing, so the SLP can change a
section first and fix its calculations afterwards.

## R8. Saving

**Decision**: Each template entry in `templates.json` gains an optional `"analysis"`
key (see [data-model.md](data-model.md) for the shape). An entry without the key loads
with no layers (FR-019). A template with no layers is saved without the key, so
templates nobody adds analysis to are written exactly as before. `FORMAT_VERSION` stays
2: the change only adds a key, and the file stays readable in format-2 terms.

- Fixed numbers are stored as strings and held as `decimal.Decimal`, so `0.1` stays
  exactly `0.1`.
- Formulas are stored exactly as typed (FR-018).
- `TemplateCreateDto` and `TemplateEditDto` gain `analysis` (default empty), and
  `TemplateDraft` carries it and compares it in `has_changes_from` through its saved
  form (FR-003).

**Rationale**: This is additive and backward compatible (interpreters rule 4), and
leaves untouched templates byte-for-byte the same.

**Alternatives considered**:
- *Bumping to format 3.* Rejected: nothing about format 2 changes, and a bump would make
  every older file look stale.
- *A separate analysis file.* Rejected: analysis is part of the template, and must save
  and load with it atomically.

## R9. The Analysis section's widgets

**Decision**: A new `AnalysisEditor` (`interpretation/template_manager/analysis_editor.py`)
is placed by `TemplateForm` below the interpreter form panel, inside a "Data Sheet
Analysis" frame under an "Analysis" heading, with the historical-analysis note (FR-001).

- **List.** A tree of layers ("Layer 1", "Layer 2", ...), each holding its calculations
  (name, kind, and a one-line summary). Below it are the buttons: Add Layer, Delete Layer
  (highest only), Add Calculation (to the selected layer), Remove, Up, and Down.
- **Editor panel** (FR-001b). It has Name, Description, and a "Build with" choice: Menu
  or Formula.
  - **Menu**: a kind picker (Row Aggregate or Arithmetic) and that kind's pickers. Row
    Aggregate shows table, Row Measure type, column(s), option or choice, and
    Sum/Average. Arithmetic shows two inputs (each a result, a sheet value, or a number)
    and the operation.
  - **Formula**: a multi-line entry, the live-check message under it, and the **Formula
    Legend** to its right. The legend is a Treeview with two groups: Operations (with
    their parameters) and Variables in scope (grouped by section, then lower-layer
    results, each with its description). Clicking an entry inserts it at the cursor (R4).
  - **Apply / Cancel**, working as the interpreter panel's do. The panel remembers a
    saved-form snapshot, so `has_unapplied_changes()` can tell when it has changes, and
    the Template Form's existing `has_unapplied_changes()` and `commit()` include it
    (FR-003).
- **View mode.** The editor panel and buttons are hidden, and the tree shows each
  calculation's plain-language description (`describe_calculation`) or formula, and its
  Calculation Description (FR-002).

All the picker choices come from the Analysis Scope (R5). All the checks come from R7.
The widgets decide nothing themselves (layers rule 5).

**Rationale**: It follows the clarified layout (inline, list then editor panel, like
interpreters) and reuses the interpreter panel's apply and snapshot pattern, which the
SLP already knows.

## R10. Opening the template windows full screen

**Decision**: `TemplateCreatorWindow` and `TemplateDetailsWindow` keep their existing
centred geometry, so restoring the window gives back that size, and then maximize, with
`window.state("zoomed")` on Windows and macOS, and `window.attributes("-zoomed", True)`
on X11 (where `state("zoomed")` raises `TclError`). One shared helper,
`tk_utils.windows.maximize(window)`, does this. The windows are not transient (fixed
earlier, in commit 3edee4a), so the window manager lets the SLP restore them to a
smaller size (FR-001a).

**Rationale**: Each window system names the maximized state differently, and one helper
keeps the platform check in one place.

## R11. Testing

**Decision**: As in 007 and 008, there is no test framework.

- **Offline.** Scratch-script checks in [quickstart.md](quickstart.md) cover the parser,
  scope, problems, renames, serialization round trips, and loading old templates.
- **By hand.** Window checks cover the editor, the legend, live checking, the
  full-screen windows, and view mode.

**Rationale**: This matches the project's established practice, and every rule lives in
pure modules that a script can call directly.

## R12. Documentation and constitution

**Decision**:

- **Glossary.** Add Data Sheet Analysis, Historical Analysis, Analysis Layer,
  Calculation, Calculation Description, Row Aggregate, Row Measure, Arithmetic
  calculation, Formula calculation, Formula Legend, Numeric Sheet Value, Analysis Scope,
  and Section Name.
- **interpreters.md.**
  - Add `analysis_parts()` to the optional overrides of a new interpreter type, and
    `renames()` to the Config UI piece.
  - Add rule 11: Data Sheet Analysis refers to template parts by name. An editor that
    lets the SLP rename a part reports it, so calculations follow the rename.
- **Constitution.** Bump the MINOR version, with a Sync Impact Report entry. That's
  1.8.0 → 1.9.0, or 1.9.0 → 1.10.0 if 008's planned amendment lands first.

**Rationale**: Principle II requires glossary terms in the same change. A new optional
contract method in a referenced doc is a MINOR amendment (Governance).
