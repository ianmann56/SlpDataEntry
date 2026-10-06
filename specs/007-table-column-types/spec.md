# Feature Specification: Table Column Types

**Feature Branch**: `007-table-column-types`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "Add the ability to specify the type of data in table columns. The available types should be: a free form text field; a choice field (each choice should be configurable with a description of the meaning of that particular choice); an integer field; a decimal field; a tally field (includes a sub-configuration for the choices of the tally options, each tally option should allow a description of the meaning of that particular tally choice); True/False (a boolean); a date."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Give each table column a type (Priority: P1)

While creating or editing a Data Sheet Template, the SLP adds a column to a table section. Along with the column's name, they pick what kind of data the column holds: **Text**, **Integer**, **Decimal**, **True/False**, **Date**, **Choice**, or **Tally**. When a data sheet is imported with that template, each cell in the column is read as that type, and it is saved to the Student Session Workbook as that type. For example, a "Times w/Prompting" column marked Integer is saved as a number the SLP can total and chart, not as text.

Today every column is read and saved as text, so the SLP has to retype or convert values in the workbook before they can analyze them.

**Why this priority**: Typed values are what make the saved data analyzable. The simple types (Text, Integer, Decimal, True/False, Date) need no extra setup and deliver most of the value by themselves.

**Independent Test**: Create a template with one table section whose columns are Text, Integer, Decimal, True/False, and Date. Import a synthetic sheet whose table fills those columns with valid values. Confirm the workbook holds text, whole numbers, decimal numbers, true/false values, and dates in the matching columns.

**Acceptance Scenarios**:

1. **Given** the SLP is adding a column to a table section, **When** they enter a name, **Then** they must also pick one of the seven column types, with Text selected by default.
2. **Given** a column is typed Integer, **When** a sheet with `7` in that column is imported, **Then** the workbook cell holds the number 7.
3. **Given** a column is typed Decimal, **When** a sheet with `2.5` in that column is imported, **Then** the workbook cell holds the number 2.5.
4. **Given** a column is typed True/False, **When** a sheet with `Y` in one row and `N` in another is imported, **Then** the workbook cells hold true and false.
5. **Given** a column is typed Date, **When** a sheet with `10/3/2026` in that column is imported, **Then** the workbook cell holds the date October 3, 2026.
6. **Given** a column is typed Text, **When** a sheet with any writing in that column is imported, **Then** the workbook cell holds that writing unchanged.
7. **Given** a cell in a typed column is blank, **When** the sheet is imported, **Then** the workbook cell is left empty and the import still succeeds.
8. **Given** a saved template, **When** the SLP views its details, **Then** each column is shown with its name and its type.
9. **Given** a template is being edited, **When** the SLP changes a column's type and saves, **Then** sheets imported afterwards are read with the new type, and sessions keep going to the same Student Session Workbook.

---

### User Story 2 - Choice columns with described choices (Priority: P2)

The SLP marks a column as **Choice** and lists the values that may appear in it, such as `+`, `-`, and `P`. For each choice they can write a short description of what it means, such as "`P` = correct with a prompt". When a sheet is imported, each cell must be one of the listed choices. The descriptions are saved with the template and shown wherever the template's columns are shown, so the SLP (or anyone they share the template with) can tell what each mark means.

**Why this priority**: Many sheets use short codes in a column. Restricting the column to known codes catches misreads, and the descriptions keep the meaning of each code with the template instead of in the SLP's memory.

**Independent Test**: Create a Choice column with choices `+` ("correct"), `-` ("incorrect"), and `P` ("correct with prompt"). Save, view the template, and confirm each choice and its description is shown. Import a synthetic sheet using those codes and confirm each cell is saved as the matching choice.

**Acceptance Scenarios**:

1. **Given** the SLP picks Choice for a column, **When** they configure it, **Then** they can add, remove, and reorder choices, and give each choice an optional description.
2. **Given** a Choice column with no choices, **When** the SLP tries to apply or save it, **Then** nothing is saved and they are told the column needs at least one choice.
3. **Given** a Choice column with two choices that are the same, ignoring letter case and surrounding spaces, **When** the SLP tries to apply or save it, **Then** nothing is saved and they are told which choice is a duplicate.
4. **Given** a Choice column with choices `+`, `-`, `P`, **When** a sheet with `p` in that column is imported, **Then** the cell is saved as the choice `P`.
5. **Given** a Choice column with choices `+`, `-`, `P`, **When** a sheet with `X` in that column is imported, **Then** the cell is treated as an invalid value (see FR-012).
6. **Given** a saved template with a Choice column, **When** the SLP views its details, **Then** each choice is listed in order with its description.

---

### User Story 3 - Tally columns with described tally options (Priority: P3)

Some tables have a column where the SLP writes a running series of marks in one cell, such as `YYNPY` beside a target word, one mark for each attempt. The SLP marks that column as **Tally** and lists the tally options (the single marks allowed, such as `Y`, `N`, `P`). Each tally option can have a description, such as "`P` = prompted". When a sheet is imported, each cell is read as the sequence of marks it holds, every mark must be one of the tally options, and the result is saved in a form the SLP can count by option.

**Why this priority**: It extends an existing kind of data (the running tally) to the per-row case, which several sheet layouts use. It needs the most configuration and depends on the same option-and-description pattern as Choice, so it comes after Choice.

**Independent Test**: Create a Tally column with options `Y` ("yes"), `N` ("no"), and `P` ("prompted"). Import a synthetic sheet whose rows hold `YYN`, `PNY`, and an empty cell. Confirm each row's saved result reflects the marks read, and that the template's details show every option with its description.

**Acceptance Scenarios**:

1. **Given** the SLP picks Tally for a column, **When** they configure it, **Then** they can add, remove, and reorder tally options, and give each one an optional description.
2. **Given** a Tally column, **When** the SLP adds a tally option longer than one character, or a duplicate of another option ignoring case, **Then** it is refused and they are told why.
3. **Given** a Tally column with no tally options, **When** the SLP tries to apply or save it, **Then** nothing is saved and they are told the column needs at least one tally option.
4. **Given** a Tally column with options `Y`, `N`, `P`, **When** a sheet with `YyN P` in that column is imported, **Then** the cell is read as the marks Y, Y, N, P in that order (letter case and spaces ignored), and saved as described in FR-016.
5. **Given** a Tally column with options `Y`, `N`, `P`, **When** a sheet with `YXN` in that column is imported, **Then** the cell is treated as an invalid value (see FR-012).
6. **Given** a saved template with a Tally column, **When** the SLP views its details, **Then** each tally option is listed in order with its description.

---

### User Story 4 - Existing templates keep working (Priority: P1)

The SLP has templates saved before this feature. After updating, those templates load and import exactly as before, without the SLP having to edit them first.

**Why this priority**: The constitution requires saved templates to stay loadable. Breaking existing templates would stop imports for every student.

**Independent Test**: Load a templates file saved by the previous version with a table section. Confirm it opens, every column shows as Text, and an import produces the same workbook values as before the update.

**Acceptance Scenarios**:

1. **Given** a template saved before this feature, **When** the app loads it, **Then** every column without a recorded type is treated as Text.
2. **Given** a template saved before this feature whose column had a list of choices, **When** the app loads it, **Then** that column is treated as Choice with those choices and no descriptions.
3. **Given** an older template, **When** the SLP saves it again, **Then** each column's type is recorded and the template still loads afterwards.

---

### Edge Cases

- A cell holds surrounding spaces, such as ` 7 `: spaces are ignored before reading the value for every type except Text, which keeps the writing as read.
- An Integer cell holds `7.0` or `3.5`: `7.0` is read as 7; `3.5` is an invalid value for an Integer column.
- A Decimal cell holds `.5` or `3`: both are valid (0.5 and 3).
- A number holds a thousands separator, a percent sign, or a unit (e.g. `70%`, `1,200`): these are invalid values; the SLP should use Text for such columns.
- A Date cell holds a two-digit year, such as `10/3/26`: it is read as 2026.
- A Date cell holds an impossible date, such as `2/30/2026`: it is an invalid value.
- A True/False cell holds a checkmark or an `X`: see FR-009 for the marks accepted.
- A Choice cell holds a value whose letters match a choice except for case (`p` vs `P`): it is saved as the choice as configured.
- A Tally cell is blank: it is read as zero marks, not as an invalid value.
- The SLP changes a column's type from Choice or Tally to another type: the choices or tally options are discarded when the template is saved, after the SLP is warned in the form.
- The SLP changes a column's type after sessions are already saved: earlier Session Tabs keep the values they were saved with; only later imports use the new type.
- OCR misreads a value (e.g. `l` for `1` in an Integer column): it is handled as an invalid value (FR-012); the tool does not guess corrections.

## Requirements *(mandatory)*

### Functional Requirements

**Configuring column types**

- **FR-001**: Every column of a table section MUST have exactly one column type: Text, Integer, Decimal, True/False, Date, Choice, or Tally.
- **FR-002**: The SLP MUST be able to set and change a column's type wherever a table section's columns are configured, both when creating a template and when editing one. New columns MUST default to Text.
- **FR-003**: For a Choice column, the SLP MUST be able to add, remove, and reorder choices, and enter an optional free-text description for each choice.
- **FR-004**: For a Tally column, the SLP MUST be able to add, remove, and reorder tally options, and enter an optional free-text description for each tally option. Each tally option MUST be exactly one character.
- **FR-005**: A Choice column MUST have at least one choice, and a Tally column MUST have at least one tally option. Choices within a column, and tally options within a column, MUST be unique, ignoring letter case and surrounding spaces. A template that breaks these rules MUST NOT be saved, and the SLP MUST be told which column and which rule is broken.
- **FR-006**: Column types, choices, tally options, and their descriptions MUST be saved with the template and restored exactly when it is loaded.
- **FR-007**: Viewing a template's details MUST show each column's name and type, and for Choice and Tally columns, each choice or tally option in order with its description.

**Reading values on import**

- **FR-008**: When a sheet is imported, each cell MUST be read according to its column's type:
  - **Text**: the writing as read, unchanged.
  - **Integer**: a whole number, optionally signed; a decimal whose fractional part is zero (e.g. `7.0`) is accepted as that whole number.
  - **Decimal**: a number with an optional sign and an optional decimal point.
  - **True/False**: see FR-009.
  - **Date**: a calendar date written month/day/year, with `/` or `-` as the separator and a two- or four-digit year.
  - **Choice**: one of the column's choices, matched ignoring letter case and surrounding spaces, and recorded as the choice as configured.
  - **Tally**: an ordered sequence of the column's tally options, matched ignoring letter case, with spaces ignored.
- **FR-009**: A True/False cell MUST be read as true from `Y`, `Yes`, `T`, `True`, `1`, or a checkmark, and as false from `N`, `No`, `F`, `False`, `0`, or `X`, ignoring letter case.
- **FR-010**: A blank cell MUST be recorded as an empty value for every column type and MUST NOT cause the import to fail.
- **FR-011**: For every type except Text, surrounding spaces MUST be ignored before the value is read.
- **FR-012**: When a non-blank cell cannot be read as its column's type, the system MUST [NEEDS CLARIFICATION: fail the whole sheet's import with a reason naming the column, row, and value read, OR save the sheet with that cell kept as the raw text and clearly flagged as not matching its type?].
- **FR-013**: Column types MUST NOT change which columns a table section must contain; a sheet missing an expected column still fails as it does today.

**Saving typed values**

- **FR-014**: Integer and Decimal values MUST be saved to the Student Session Workbook as numbers, Date values as dates, and True/False values as true/false values, so they can be sorted, totaled, and charted without conversion.
- **FR-015**: Text and Choice values MUST be saved as text.
- **FR-016**: A Tally cell MUST be saved as [NEEDS CLARIFICATION: the marks as one text value in the order read (e.g. `YYNP`), OR a count per tally option in separate workbook columns (e.g. Y=2, N=1, P=1), OR both?].
- **FR-017**: Changing column types, choices, tally options, or descriptions MUST NOT change the template's Template Structure, so sessions keep going to the same Student Session Workbook.

**Compatibility**

- **FR-018**: Templates saved before this feature MUST load without changes by the SLP. A column with no recorded type MUST be treated as Text, or as Choice (with no descriptions) when it has saved choices.
- **FR-019**: The Running Tally section and the Simple Form section MUST keep working as they do today; this feature does not change them.

### Key Entities

- **Column Definition**: One expected column in a table section. Has a name (unique within the section) and a column type. A Choice column also has an ordered list of Choice Options; a Tally column also has an ordered list of Tally Options.
- **Column Type**: The kind of value a column holds: Text, Integer, Decimal, True/False, Date, Choice, or Tally.
- **Choice Option**: One allowed value of a Choice column. Has a value (the text expected on the sheet) and an optional description of what it means.
- **Tally Option**: One allowed mark in a Tally column. Has a one-character mark and an optional description of what it means.
- **Typed Cell Value**: The value read from one cell, following its column's type: a text, whole number, decimal number, true/false, date, choice, or sequence of tally marks, or empty.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The SLP can configure a table section with one column of each of the seven types, including descriptions for three choices and three tally options, in under 5 minutes.
- **SC-002**: For a sheet whose cells are all valid for their types, 100% of Integer, Decimal, Date, and True/False values arrive in the workbook as values that can be totaled, averaged, or sorted chronologically with no manual conversion.
- **SC-003**: 100% of templates saved before this feature load and import with the same workbook results as before the update.
- **SC-004**: Every cell that does not match its column's type is reported or flagged with the column and row it came from; none are silently saved as a different value.
- **SC-005**: Someone who did not build a template can tell what every choice and tally mark means from the template's details alone, without asking the SLP.

## Assumptions

- Column types apply only to columns of table sections. The Running Tally section's tally characters and the Simple Form section's fields are not changed by this feature.
- Descriptions are optional, free text, and shown wherever the template is shown. They are not written into the Student Session Workbook.
- Descriptions, like Template Descriptions, describe the sheet layout and MUST never identify a student.
- Dates on sheets are written in US month/day/year order. Two-digit years are in the 2000s.
- Choice values may be more than one character (e.g. `NR` for "no response"); tally options are always single marks, since a tally cell is read one mark at a time.
- Columns are typed per table section; there is no shared library of column types or choice sets across templates.
- The new domain terms (Column Type, Choice Option, Tally Option) will be added to the glossary as part of this feature, per Principle II.
- Values in Session Tabs saved before a type change are not rewritten.
