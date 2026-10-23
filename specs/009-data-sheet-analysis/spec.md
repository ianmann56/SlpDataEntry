# Feature Specification: Data Sheet Analysis

**Feature Branch**: `009-data-sheet-analysis`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Add an analysis feature. This spec will focus on configuring analysis for each template. On the template view/edit window, the user should see a section for analyzing instances of the template. There will be 2 categories of analysis: data sheet level analysis and historical analysis (like calculations on multiple sessions of imports for the same student with the same template). For this spec, we're only going to focus on data sheet level analysis. In this section: the user should be able to define calculations based on the parts of the template; the user should be able to define calculations in layers where a higher layer can reference not only data from the import but results of calculations in a lower layer. Examples of types of calculations are: the sum of tallies in a column across rows of a table; the sum of a particular value selected in one or more choice field columns across rows of a table; the average number of a particular value selected in all rows across one or more choice field columns in a table; the average tally count in a column over all rows in a table."

## Clarifications

### Session 2026-10-22

- Q: Is working out and saving each calculation's result on import part of this spec? → A: No. This spec only configures calculations on the template. Working out results is a later spec.
- Q: When an Average reaches a row whose value is empty, is the row skipped or counted as 0? → A: Skipped. An Average covers only the rows that have a value.
- Q: Are calculations built from a fixed menu, or typed as formulas? → A: Both, in every layer. The SLP chooses, for each calculation, whether to build it from the menu or type a formula.
- Q: What help does the SLP see while typing a formula? → A: A Formula Legend beside the formula, listing every operation available with its parameters, and every variable name in scope for that calculation.
- Q: When the SLP clicks an operation or variable name in the Formula Legend, should it be inserted into the formula at the cursor? → A: Yes. An operation is inserted with placeholders for its parameters, and a variable name is inserted as written.
- Q: When the SLP renames something a calculation uses, should calculations using it update to the new name automatically? → A: Yes. Renames update every calculation, menu and formula text alike. Removing something or changing its type still blocks saving until the calculation is fixed.
- Q: Should a formula be checked continuously as the SLP types it, or only when applied? → A: As they type. A message under the formula shows the current problem, or that the formula is OK, and Apply still refuses a formula with a problem.
- Q: Should each calculation have an optional description of what it measures? → A: Yes, for every calculation, menu or formula. It is shown with the calculation in view mode, and beside lower-layer results in the Formula Legend.
- Q: Where does the SLP build and edit a calculation? → A: Inline. The Analysis section sits below the interpreters in the template window, with an editor panel under the calculation list, like the interpreter editor, and the Formula Legend beside the formula entry. The Create Template and Template Details windows open full screen by default.
- Q: Can the SLP move a calculation to a different layer, or only reorder it within its layer? → A: Only reorder within its layer. To change a calculation's layer, the SLP deletes it and builds it again in the other layer.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define a calculation from the menu (Priority: P1)

The SLP opens a Data Sheet Template and finds an **Analysis** section alongside its name, description, and interpreters. Within it, under **Data Sheet Analysis**, they add a **Calculation** and build it from the menu: they give it a name (for example, "Total prompted attempts"), choose a table section of the template, choose what to measure in each row, and choose how to combine the rows (**Sum** or **Average**). For example: the sum of the `P` count of the "Attempts" Tally column across every row, or the average number of `+` marks per row across the "Trial 1", "Trial 2", and "Trial 3" Choice columns.

Today the SLP totals these by hand or with their own formulas in every Student Session Workbook. Defining a calculation once on the template records how every sheet read with that template should be analyzed.

**Why this priority**: These single-table aggregations are the examples the SLP gave, and the menu is the error-proof way to build them.

**Independent Test**: Create a template with one table section holding a Tally column (options `Y`, `N`, `P`) and two Choice columns (choices `+`, `-`). Build four menu calculations matching the four examples in the request. Save, reopen the template, and confirm each calculation is shown with its name, table, row measure, and combination exactly as defined.

**Acceptance Scenarios**:

1. **Given** the SLP is viewing, editing, or creating a template, **When** the window opens, **Then** it fills the screen, and below the interpreters they see an Analysis section containing a Data Sheet Analysis area, and a note that historical analysis is not yet available.
2. **Given** the template is in edit mode (or being created), **When** the SLP adds a menu calculation, **Then** they must give it a name and choose its kind, a Row Aggregate or an Arithmetic calculation, and may give it a description.
3. **Given** a Row Aggregate, **When** the SLP builds it, **Then** they must choose a table section, a row measure, and Sum or Average.
4. **Given** a Tally column with options `Y`, `N`, `P`, **When** the SLP chooses it as the row measure, **Then** they can measure either the count of one tally option or the tally's total.
5. **Given** a table with Choice columns, **When** the SLP chooses "choice count" as the row measure, **Then** they pick one choice value and one or more Choice columns that offer it, and each row is measured as the number of the chosen columns holding that value.
6. **Given** a table with Integer or Decimal columns, **When** the SLP chooses one as the row measure, **Then** each row is measured as that column's number.
7. **Given** a template in view mode, **When** the SLP looks at the Analysis section, **Then** every menu calculation is shown read-only in plain language (e.g. "Sum over rows of *Attempts* `P` count"), with its description when it has one, and none can be changed until they switch to edit mode.
8. **Given** a calculation has been defined, **When** the SLP saves the template and reopens it, **Then** the calculation is restored exactly.
9. **Given** the template is in edit mode, **When** the SLP selects a calculation in the list, **Then** its details appear in an editor panel below the list, and their changes take effect when they press Apply and are discarded when they press Cancel.

---

### User Story 2 - Build calculations in layers (Priority: P1)

The SLP arranges calculations in numbered **Analysis Layers**. Layer 1 calculations read only the sheet's data. A calculation in a higher layer can also use the results of calculations in any lower layer. For example, with layer 1 holding "Correct trials" (sum of `+` across the Trial columns) and "Total trials" (sum of the Tally total), a layer 2 calculation "Accuracy" is the percentage of "Correct trials" over "Total trials", the number the SLP compares against a Goal's target (such as 70% accuracy).

**Why this priority**: The request names layering as a core requirement, and the numbers the SLP reports (accuracy, prompted rate) are ratios of simpler results.

**Independent Test**: Using the template from User Story 1, add a layer 2 Arithmetic calculation giving the percentage of one layer 1 result over another. Save, reopen, and confirm it still names both layer 1 results. Then confirm a layer 1 calculation is never offered another calculation's result.

**Acceptance Scenarios**:

1. **Given** a template's analysis, **When** the SLP adds a layer, **Then** it is numbered one higher than the current highest layer.
2. **Given** a calculation in layer *N*, **When** the SLP chooses its inputs, **Then** they are offered the template's sheet data and the results of calculations in layers 1 to *N − 1*, and never results from layer *N* or above.
3. **Given** an Arithmetic calculation, **When** the SLP builds it, **Then** they combine two inputs with add, subtract, multiply, divide, or percentage (first ÷ second × 100), where each input is a lower-layer result, a numeric sheet value, or a fixed number they type.
4. **Given** a layer 2 calculation uses a layer 1 result, **When** the SLP tries to delete that layer 1 calculation, **Then** it is not deleted and they are told which calculations use it.
5. **Given** the highest layer holds calculations, **When** the SLP deletes that layer, **Then** it is deleted only after they confirm. Lower layers cannot be deleted while a higher layer exists.
6. **Given** calculations within a layer, **When** the SLP reorders them, **Then** the new order is saved and shown.

---

### User Story 3 - Type a calculation as a formula (Priority: P2)

Instead of building a calculation from the menu, the SLP can type it as a **Formula**, in any layer. A formula can do everything the menu can, and more in one step. For example, a layer 2 formula `(Correct trials + Partial trials) / Total trials * 100` combines three results at once, and a layer 1 formula can sum the `P` count of the "Attempts" Tally column directly. While typing, a **Formula Legend** beside the formula lists every operation available, with its parameters, and every variable name in scope for that calculation, so the SLP doesn't have to remember either. Clicking an entry inserts it into the formula at the cursor.

**Why this priority**: The menu covers the examples in the request; formulas remove the need for extra layers when combining more than two values, and handle cases the menu doesn't anticipate.

**Independent Test**: Add a layer 2 formula combining three layer 1 results, and a layer 1 formula that sums a Tally option count over a table. Save, reopen, and confirm both formulas are restored as typed. Then type a formula naming a column that doesn't exist, and one naming a result from its own layer, and confirm each is refused with a message saying what is wrong.

**Acceptance Scenarios**:

1. **Given** the SLP adds a calculation in any layer, **When** they choose to type a formula, **Then** they can enter it in place of the menu choices.
2. **Given** the SLP is typing a formula, **When** it cannot be understood, refers to something that doesn't exist, or uses a result from its own layer or above, **Then** a message under the formula says what is wrong and where, and it updates as they keep typing; **When** the formula has no problem, **Then** the message says the formula is OK.
3. **Given** the SLP chooses to type a formula, **When** the formula entry is shown, **Then** a Formula Legend appears beside it listing each operation (such as Sum and Average over a table's rows, and the arithmetic operators) with its parameters, and each variable name in scope for that calculation: its numeric sheet values, the tables and row measures it can aggregate, and the results of lower-layer calculations.
4. **Given** a layer 1 formula, **When** the SLP writes it, **Then** it can take the Sum or Average over a table's rows of any row measure the menu offers, and combine those with numbers, numeric sheet values, the four arithmetic operations, and parentheses.
5. **Given** a template in view mode, **When** the SLP looks at a formula calculation, **Then** its name, formula, and description (when it has one) are shown read-only.
6. **Given** a calculation in layer 2, **When** the SLP looks at its Formula Legend, **Then** layer 1 results are listed and no layer 2 or higher result is.
7. **Given** the SLP is typing a formula, **When** they click a variable name in the Formula Legend, **Then** it is inserted at the cursor exactly as the formula expects; **When** they click an operation, **Then** it is inserted at the cursor with a placeholder for each of its parameters.
8. **Given** a formula with a problem, **When** the SLP applies it, **Then** it is refused and the message under the formula still says what is wrong.

---

### User Story 4 - Existing templates keep working (Priority: P1)

Templates saved before this feature load with an empty Analysis section and import exactly as before.

**Why this priority**: The constitution requires saved templates to stay loadable (Principle V).

**Independent Test**: Load a templates file saved by the previous version and confirm each template opens with no calculations and imports with the same workbook results as before.

**Acceptance Scenarios**:

1. **Given** a template saved before this feature, **When** the app loads it, **Then** it has no Analysis Layers and no calculations.
2. **Given** such a template, **When** the SLP adds a calculation and saves, **Then** the template still loads and imports afterwards with the same workbook results as before.

---

### Edge Cases

- A "choice count" over several columns where some cells in a row are empty: those cells do not hold the choice, so they add 0 to that row's count.
- The SLP renames a section, column, field, choice, tally option, or calculation that other calculations use: every menu calculation and formula using it switches to the new name automatically, and the template can be saved without further changes (FR-016a).
- The SLP removes, or changes the type of, a section, column, field, choice, or tally option that a calculation uses (by menu or by formula): the template cannot be saved until the calculation is fixed, and the SLP is told which calculation and which missing part.
- The SLP removes a column and adds a new one with the old name: this is a removal followed by an addition, not a rename, so calculations that used the old column are checked against the new one by name and type.
- Two calculations are given the same name, ignoring letter case and surrounding spaces: the template cannot be saved, and the SLP is told which name is duplicated.
- A calculation name that a formula could not tell apart from an operator or number (for example, a name holding `+` or `(`): formulas still refer to it unambiguously, because references are written in a quoted or bracketed form.
- A template has several table sections: each Row Aggregate names exactly one table section; a higher-layer calculation may combine results from different tables.
- A layer has no calculations: it may be saved empty, and is shown as empty.
- A calculation was added to the wrong layer: it cannot be moved; the SLP deletes it (if nothing uses its result) and builds it again in the right layer.
- The SLP cancels edit mode: changes to the analysis are discarded with every other change.
- A formula that divides by a number that can be 0: it is accepted; how a division by 0 is shown is decided when results are worked out (see Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

**Analysis section**

- **FR-001**: The Template Details window (view and edit mode) and the Create Template window MUST show an **Analysis** section for the template, below its interpreters, containing a **Data Sheet Analysis** area. It MUST say that historical analysis (calculations across a student's sessions) is not yet available.
- **FR-001a**: The Create Template and Template Details windows MUST open full screen (maximized) by default. The SLP MUST still be able to restore them to a smaller size.
- **FR-001b**: In edit mode and when creating a template, the Data Sheet Analysis area MUST show its layers and their calculations as a list, with an **editor panel** below the list, as for interpreters. Selecting a calculation MUST show it in the editor panel; adding one MUST open an empty editor. Changes in the editor panel MUST take effect in the Template Draft only when the SLP presses Apply, and MUST be discarded on the editor's Cancel. For a formula calculation, the Formula Legend MUST be beside the formula entry in the panel.
- **FR-002**: In view mode the Analysis section MUST be read-only and MUST show every calculation, grouped by layer: a menu calculation in plain language naming its inputs and how they are combined, and a formula calculation as its formula. In edit mode and when creating a template the SLP MUST be able to change it.
- **FR-003**: Analysis changes MUST be part of the Template Draft: they are saved only when the template is saved, discarded on Cancel, and count as unsaved changes when the SLP is asked whether to discard their edits.

**Layers**

- **FR-004**: Data Sheet Analysis MUST be organized as an ordered list of **Analysis Layers**, numbered from 1. The SLP MUST be able to add a layer (numbered one above the highest), and delete the highest layer after confirming. Only the highest layer can be deleted, so no remaining calculation can use a deleted layer's results.
- **FR-005**: Each layer MUST hold an ordered list of calculations. The SLP MUST be able to add, edit, remove, and reorder calculations within a layer. A calculation MUST NOT be moved to another layer; it stays in the layer it was added to.
- **FR-006**: A calculation in layer *N* MUST be able to use only the template's sheet data, fixed numbers, and the results of calculations in layers 1 to *N − 1*. Neither the menu nor the formula reference picker MUST offer any other result, and a formula referring to one MUST be refused.

**Calculations**

- **FR-007**: Every calculation MUST have a name that is not blank and is unique within the template, ignoring letter case and surrounding spaces.
- **FR-007a**: Every calculation, menu or formula, MAY have an optional free-text **Calculation Description** saying what it measures. It MUST be shown with the calculation in view mode, and beside that calculation's result wherever the result is listed in a Formula Legend.
- **FR-008**: Every calculation MUST be either a **menu calculation** (a Row Aggregate or an Arithmetic calculation) or a **Formula calculation**, in any layer. The SLP chooses which when adding it.
- **FR-009**: A **Row Aggregate** MUST name one table section, one **Row Measure**, and one combination, **Sum** or **Average**, taken across the rows of that table.
- **FR-010**: A Row Measure MUST be one of:
  - **Number column**: the value of one Integer or Decimal column in the row.
  - **Tally count**: the count of one Tally Option, or the tally's total, in one Tally column in the row.
  - **Choice count**: the number of chosen Choice columns (one or more) whose value in the row is one chosen Choice Option. Only Choice columns offering that option, matched ignoring letter case and surrounding spaces, MUST be offered.
- **FR-011**: An **Arithmetic** calculation MUST combine two inputs with add, subtract, multiply, divide, or percentage (first ÷ second × 100). Each input MUST be a lower-layer calculation result, a **numeric sheet value** (an Integer or Decimal Simple Form field, or a Running Tally section's option count, total, or option percentage), or a fixed number typed by the SLP.
- **FR-012**: A **Formula** MUST be able to use: fixed numbers; numeric sheet values; lower-layer results; the Sum or Average over a table section's rows of any Row Measure from FR-010; addition, subtraction, multiplication, and division; and parentheses, with the usual order of operations. Every reference in a formula MUST be written in a delimited form, so names holding spaces or symbols are unambiguous.
- **FR-013**: A formula MUST be checked as the SLP types it. A message under the formula entry MUST show, after each change, either what is wrong and where in the formula (it cannot be understood, or refers to something it may not use), or that the formula is OK. Apply MUST stay available, but MUST refuse a formula with a problem, leaving the message in place.
- **FR-014**: While the SLP types a formula, a **Formula Legend** MUST be shown beside the formula entry. It MUST list every operation a formula may use, each with its parameters (for example, a table Sum naming its table and Row Measure), and every variable name in scope for that calculation (FR-006), written exactly as the formula expects. It MUST NOT list anything the calculation may not use. Clicking a legend entry MUST insert it into the formula at the cursor: a variable name as written, and an operation with a placeholder for each of its parameters. The legend is not shown for menu calculations.
- **FR-015**: The menu, and the formula reference list, MUST offer only the sections, columns, fields, choices, and tally options the template's current draft holds, by their configured names.

**Validation and persistence**

- **FR-016**: A template MUST NOT be saved while any calculation, menu or formula, refers to a section, column, field, choice option, tally option, or calculation that no longer exists or no longer has the needed type. The SLP MUST be told which calculation is affected and what it refers to.
- **FR-016a**: When the SLP renames a section, column, field, choice option, tally option, or calculation that calculations use, every calculation using it MUST be updated to the new name in the same draft: menu calculations by their choices, and formulas by rewriting each reference to it. Nothing else in a formula MUST change. A rename means changing the name of an existing item in place.
- **FR-017**: A calculation MUST NOT be deleted while another calculation uses its result; the SLP MUST be told which calculations use it.
- **FR-018**: Analysis Layers and calculations, including each formula exactly as typed, MUST be saved with the template and restored exactly when it is loaded.
- **FR-019**: Templates saved before this feature MUST load without changes by the SLP, with no Analysis Layers.
- **FR-020**: Changing a template's analysis MUST NOT change its Template Structure or anything saved when a sheet is imported.
- **FR-021**: Calculation names, Calculation Descriptions, and formulas are template text. They describe the sheet layout and MUST never identify a student.

### Key Entities

- **Data Sheet Analysis**: The calculations a template defines for one imported sheet, as an ordered list of Analysis Layers. Saved with the template.
- **Historical Analysis**: Calculations across many sessions of one student with one template. Named here only to place Data Sheet Analysis beside it; out of scope.
- **Analysis Layer**: A numbered group of calculations. A calculation may use results only from lower layers.
- **Calculation**: One named number the template defines for each imported sheet, with an optional Calculation Description. Either a menu calculation (Row Aggregate or Arithmetic) or a Formula calculation.
- **Row Aggregate**: A menu calculation that measures each row of one table section with a Row Measure and combines the rows by Sum or Average.
- **Row Measure**: What a Row Aggregate reads from each row: a number column, a tally count, or a choice count across one or more Choice columns.
- **Arithmetic calculation**: A menu calculation that combines two inputs (lower-layer results, numeric sheet values, or fixed numbers) with add, subtract, multiply, divide, or percentage.
- **Formula calculation**: A calculation the SLP types as a formula, using the same inputs and table aggregations as the menu, plus arithmetic and parentheses.
- **Formula Legend**: The reference shown beside a formula while it is typed: the operations available with their parameters, and the variable names in scope for that calculation.
- **Numeric Sheet Value**: A single number on the sheet a calculation can use directly: an Integer or Decimal Simple Form field, or a Running Tally section's option count, total, or option percentage.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The SLP can define the four example calculations from the request, plus one layer 2 accuracy percentage, on an existing template in under 10 minutes.
- **SC-002**: 100% of templates saved before this feature load with no analysis and import with the same workbook results as before.
- **SC-003**: Someone who did not build a template can tell what every calculation measures from the template's view mode alone, without asking the SLP.
- **SC-004**: 100% of attempts to save a template whose calculation (menu or formula) refers to a missing, mistyped, or not-yet-available part are refused with a message naming the calculation.
- **SC-005**: 100% of formulas that cannot be understood show, while still being typed, a message saying what and where the problem is, and are refused when applied.
- **SC-006**: Every calculation that can be built from the menu can also be written as a formula, and the SLP can write a three-input formula (such as `(A + B) / C * 100`) in one calculation.

## Assumptions

- Only configuring Data Sheet Analysis is in scope. Working out and saving each calculation's result for an imported sheet, and Historical Analysis, are later specs.
- The Analysis section lives in the shared Template Form, so it appears in both the Create Template and Template Details windows. Opening those windows full screen (FR-001a) gives the Formula Legend room beside the formula.
- The calculation meaning defined here is what the later results spec will follow:
  - An Average covers only the rows whose measured value is not empty; rows with an empty value (blank, or unreadable per feature 008) are skipped.
  - A Sum over no values is 0; empty values add nothing.
  - An Average over no values, and a division or percentage by 0, give an empty result, and a calculation using an empty result is also empty.
  - Results are numbers, worked out from interpreted values (Typed Values, Tally Summaries), never from raw OCR text.
- Row Aggregates cover the four example calculations: "sum of tallies in a column" and "average tally count" are Tally count measures combined by Sum and Average; "sum of a particular value selected in choice columns" and "average number of a particular value" are Choice count measures combined by Sum and Average.
- True/False, Date, and Text columns and fields are not row measures or sheet values in this spec.
- The exact formula syntax (how references, functions, and percentages are written) is decided during planning, within FR-012 to FR-014.
- A menu calculation is not converted to a formula, or back, automatically; the SLP can replace one with the other.
- The new domain terms (Data Sheet Analysis, Historical Analysis, Analysis Layer, Calculation, Row Aggregate, Row Measure, Arithmetic calculation, Formula calculation, Calculation Description, Formula Legend, Numeric Sheet Value) will be added to the glossary as part of this feature, per Principle II.
