# Feature Specification: Nullable Field Values

**Feature Branch**: `008-nullable-field-values`

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "Make the values imported for all Field types nullable. We can't require non-null because we can't control what the SLP writes down on the sheet."

## Clarifications

### Session 2026-10-11

- Q: Blank cells already import as empty. What should happen when the SLP writes something that doesn't fit the type, like "N/A" in an Integer column or "?" in a Date field? Today the whole sheet's import fails. → A: The typed value is saved empty and the import succeeds. The text as written is kept in the workbook so nothing is lost, and the Sheet Outcome lists each such value as a warning.
- Q: Which kinds of values should this cover? → A: Every typed value: Simple Form fields, table columns of every type, and tally marks in Tally columns and Running Tally sections. A mark that isn't an option is left out of the counts instead of failing the sheet.
- Q: When a value doesn't fit its type, where should the workbook keep the text the SLP wrote? → A: In the cell itself, as plain text. The cell has no typed value, but it shows what was written. No note and no extra column.
- Q: Should every template always accept values that don't fit, or should the SLP be able to keep some columns or fields strict? → A: Always on, for every template, column, and field. There is no strictness setting.
- Q: When something written in an Integer column is a valid decimal number, like `7.5`, should the workbook keep it as the number 7.5, or as the text "7.5"? → A: Round it to the nearest whole number (8), with a warning.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A value that doesn't fit its type no longer blocks the sheet (Priority: P1)

The SLP fills in data sheets by hand during sessions. Sometimes what they write doesn't fit the column's or field's type: "N/A" or "absent" in an Integer column, "—" in a Date field, "maybe" in a True/False column, a choice code that isn't configured, or a stray mark in a tally. Today any one of these fails the whole sheet's import (feature 007, FR-012), and none of that session's data is saved until the SLP edits the photo or the template.

With this feature, a value that doesn't fit its type is saved as an empty typed value, and the rest of the sheet imports normally. Every typed value can now be empty, whether the SLP left it blank or wrote something that can't be read as its type.

**Why this priority**: The app cannot control what the SLP writes on paper. One unexpected note shouldn't throw away a whole session's data. This is the core of the request.

**Independent Test**: Import a synthetic sheet using a template whose table has Integer, Decimal, True/False, Date, and Choice columns, where one row holds `N/A`, `about 3`, `maybe`, `13/45/2026`, and an unconfigured choice code. Confirm the import succeeds, those five workbook cells hold no typed value, and every other cell on the sheet is saved as it would be today.

**Acceptance Scenarios**:

1. **Given** a column typed Integer, **When** a sheet with `N/A` in that column is imported, **Then** the import succeeds and that cell holds no number.
2. **Given** a Simple Form field typed Date, **When** a sheet with `?` in that field is imported, **Then** the import succeeds and that field holds no date.
3. **Given** a column typed True/False, **When** a sheet with `X` in that column is imported, **Then** the import succeeds and that cell holds neither true nor false.
4. **Given** a Choice column with choices `+` and `-`, **When** a sheet with `~` in that column is imported, **Then** the import succeeds and that cell holds no choice.
5. **Given** a sheet with values that don't fit in several sections, **When** it is imported, **Then** every value that does fit, in every section, is saved exactly as it would be if the sheet had no such values.
6. **Given** a sheet with no values that don't fit, **When** it is imported, **Then** the workbook result is identical to the result before this feature.
7. **Given** a column or field typed Integer, **When** a sheet with `7.5` in it is imported, **Then** the import succeeds, the cell holds the whole number 8, and the Sheet Outcome warns that `7.5` was rounded to 8.

---

### User Story 2 - Nothing the SLP wrote is lost (Priority: P1)

When a value is saved empty because it doesn't fit its type, the text as read from the sheet is saved in that cell as plain text instead of a typed value, so the SLP can see what was written and decide what it means later. For example, they can tell an "absent" from a "N/A".

**Why this priority**: Saving an empty value without the original text would silently lose information the SLP wrote on purpose. Together with Story 1, this makes leniency safe.

**Independent Test**: Import the sheet from Story 1. Open the workbook and confirm each of the five cells shows, as plain text, the text that was read (`N/A`, `about 3`, and so on), not a number, date, true/false, or choice.

**Acceptance Scenarios**:

1. **Given** `N/A` was read from an Integer cell, **When** the SLP views that cell in the workbook, **Then** the cell shows `N/A` as plain text, not as a number.
2. **Given** an Integer column where one cell was saved as the text `N/A`, **When** the SLP totals or averages that column in the workbook, **Then** the text cell is skipped and the result uses only the numbers.
3. **Given** a value was left blank on the sheet, **When** it is imported, **Then** the cell is empty. An empty cell means "left blank", and a text cell in a typed column means "written but unreadable".

---

### User Story 3 - The SLP is told which values didn't fit (Priority: P2)

After an Import Run, a sheet that imported with values that didn't fit, or with Integer values that were rounded, shows as succeeded with warnings. The warning lists each such value with its section, its column or field, its row (for tables), the value read, and what was expected. The message has the same detail as today's failure reason. The SLP can then check the photo or the workbook if they want to.

**Why this priority**: Without a warning, the SLP would only discover these values by inspecting the workbook. The data is safe without this story, so it ranks below the first two.

**Independent Test**: Import the Story 1 sheet together with a sheet that has no such values. Confirm the first shows as succeeded with a warning listing all five values (section, column, row, value, expected type), and the second shows as succeeded with no warning.

**Acceptance Scenarios**:

1. **Given** a sheet with three values that don't fit, **When** it is imported, **Then** its Sheet Outcome is succeeded with a warning naming all three.
2. **Given** a sheet with no values that don't fit, **When** it is imported, **Then** its Sheet Outcome is succeeded with no warning.
3. **Given** a sheet succeeded with warnings, **When** the SLP presses Import again in the same Import Run, **Then** that sheet is not imported a second time, the same as any succeeded sheet.

---

### User Story 4 - Stray tally marks are skipped, not fatal (Priority: P2)

In a Tally column or a Running Tally section, the SLP sometimes writes a mark that isn't one of the configured options, or OCR reads a smudge as an extra character. Instead of failing the sheet, the unknown mark is left out of the counts, total, and percentages, which are computed from the recognised marks only. The tally's marks cell holds the full text as read, unknown characters included, and the Sheet Outcome warns about the unknown marks.

**Why this priority**: Tallies are the most error-prone values to read, since every character counts. They follow the same principle as Story 1 but need their own rule, because a tally is never "empty". It just has fewer marks.

**Independent Test**: With a Tally column whose options are `Y`, `N`, and `P`, import a synthetic row reading `YQN`. Confirm Y=1, N=1, P=0, total 2, Y=50%, N=50%, P=0%. Confirm the marks cell holds `YQN`, and the outcome warns that `Q` is not one of the marks.

**Acceptance Scenarios**:

1. **Given** Tally options `Y`, `N`, `P`, **When** a cell reads `YQN`, **Then** the counts, total, and percentages include only `Y` and `N`, the marks cell holds `YQN`, and the warning names `Q`.
2. **Given** a Running Tally section with options `+` and `-`, **When** its grid contains `+`, `?`, and `-`, **Then** the summary counts one `+` and one `-`, and the warning names `?`.
3. **Given** a Tally cell whose every character is unknown, **When** it is imported, **Then** its counts and total are 0 and its percentages are blank, as for a blank tally. The marks cell holds the text as read, and a warning is shown.

---

### Edge Cases

- A value is empty or only whitespace: it is blank, as today. It is saved empty with no warning.
- A Text value never fails to fit, since any text is valid Text. Text values are unaffected.
- An Integer value is a whole decimal such as `7.0`: it is read as 7 with no warning, as today.
- An Integer value is a non-whole decimal: it is rounded to the nearest whole number, with halves rounded away from zero (`7.5` → 8, `2.5` → 3, `-2.5` → -3, `7.4` → 7), and the outcome warns about it. It is not an Unreadable Value.
- An Integer value is not a number at all (`about 3`, `7½`): it is an Unreadable Value, saved as text.
- A sheet has an unreadable value in every typed cell: it still imports, with every typed cell holding its text as read and no typed value, and one warning listing them all.
- A sheet is missing an expected table column: it still fails as today (007 FR-013). Leniency covers values only, not the sheet's layout.
- A configured Simple Form field is not found on the sheet at all: it is saved empty with no warning, as today.
- A sheet's template does not match it in other ways (no matching table, wrong number of tables): it fails as today (Principle V, "fail loudly").
- A Tally cell has both known and unknown marks: the known ones are counted, and only the unknown ones are named in the warning.
- The same unreadable text appears in many rows: each cell holds its own text, and the warning lists each one (section, column, row), so the SLP can find every one.
- A sheet that failed before this feature only because of values that don't fit, when imported again, now succeeds with warnings.

## Requirements *(mandatory)*

### Functional Requirements

**Every typed value may be empty**

- **FR-001**: Every typed value read from a sheet MUST be allowed to be empty. This covers every Simple Form field and table column of every Column Type, and every Tally Summary value except the counts and total, which are 0 when there are no marks. The import MUST NOT fail because a value is empty.
- **FR-002**: A value's typed value MUST be empty when it is blank (as today) or when it is an **Unreadable Value**: non-blank text that cannot be read as its Column Type or Field Type by the existing reading rules (007 FR-008 to FR-011).
- **FR-003**: An Unreadable Value MUST NOT fail the sheet's import. This replaces 007 FR-012 and the value-failure parts of FR-021 and FR-028. All other values on the sheet MUST be saved exactly as they would be if the Unreadable Value had been blank.
- **FR-004**: The reading rules for each type MUST NOT change, except for Integer (FR-004a). Whatever is readable today is read to the same value, and whatever is not readable today becomes an Unreadable Value.
- **FR-004a**: An Integer column or field value that is a valid Decimal (by 007's Decimal reading rule) but not a whole number MUST be rounded to the nearest whole number, with halves rounded away from zero, and saved as that whole number. It is a **Rounded Value**, not an Unreadable Value.

**Keeping what was written**

- **FR-005**: For every Unreadable Value, the Student Session Workbook cell MUST hold the text as read, as plain text, in place of a typed value. It MUST NOT be converted to a number, date, true/false, or choice.
- **FR-006**: A blank value MUST be saved as an empty cell. An empty cell always means "not recorded", and a text cell in a non-Text column always means "written but unreadable".
- **FR-007**: Keeping the text MUST NOT add, remove, or rename any workbook column, and MUST NOT change the Template Structure. Sessions MUST keep going to the same Student Session Workbook as before this feature.

**Tallies**

- **FR-008**: In a Tally column or Running Tally section, a character that is not one of the tally options MUST be skipped. The counts, total, and percentages MUST be computed from the recognised marks only, by the existing tally rules (007 FR-016).
- **FR-009**: When a tally skips one or more characters, its marks cell MUST hold the full text as read, unknown characters included (FR-005). When no character is skipped, the marks cell holds the marks as today.
- **FR-010**: A tally whose characters are all unknown MUST have every count and the total at 0 and every percentage blank, as for a blank tally. Its marks cell holds the text as read.

**Telling the SLP**

- **FR-011**: A sheet saved with one or more Unreadable Values, Rounded Values, or skipped tally marks MUST get the Sheet Outcome **succeeded with warnings**. It counts as succeeded for every purpose, including the Import Run's totals and not being imported again.
- **FR-012**: The warning MUST list every Unreadable Value, Rounded Value, and skipped tally mark on the sheet, each naming the section, the column or field, the row (for tables), the value read, and what was expected. This uses the same wording as today's failure reasons (for example, `"Words", column "Trials", row 3: "N/A" is not a whole number`). A Rounded Value also names the number saved (for example, `"Words", column "Trials", row 3: "7.5" is not a whole number; saved as 8`).
- **FR-013**: A sheet with no Unreadable Values, no Rounded Values, and no skipped marks MUST show as succeeded with no warning, as today.

**Unchanged behaviour**

- **FR-014**: A sheet missing an expected table column, or otherwise not matching its template's layout, MUST still fail its import as today.
- **FR-015**: Templates saved before this feature MUST load and import unchanged. No template, column, or field setting is added, and leniency applies to every template. The template editor MUST NOT offer a strictness option.
- **FR-016**: The domain glossary MUST define Unreadable Value, Rounded Value, and the "succeeded with warnings" Sheet Outcome. It MUST also update Typed Value to say it may be empty for a blank or Unreadable Value (Principle II).

### Key Entities

- **Typed Value** *(updated)*: The value read from one cell or field, following its type, or empty. It is empty when the value was blank or was an Unreadable Value.
- **Unreadable Value** *(new)*: Non-blank text on a sheet that cannot be read as its column's or field's type, such as `N/A` in an Integer column. It has an empty Typed Value, and its workbook cell holds the text as read, as plain text. For a tally, it is a character that is not one of the tally options.
- **Rounded Value** *(new)*: A non-whole decimal number written in an Integer column or field, such as `7.5`. It is saved as the nearest whole number (halves away from zero) and reported in the warning.
- **Sheet Outcome** *(updated)*: Gains *succeeded with warnings*, which is a success that also lists each Unreadable Value, Rounded Value, and skipped tally mark.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of sheets whose only problems are values that don't fit their types import successfully. No sheet fails because of what the SLP wrote in a typed cell or field.
- **SC-002**: For 100% of Unreadable Values, the SLP can read the text that was written in the corresponding workbook cell, with no need to find the original photo.
- **SC-003**: For 100% of sheets with Unreadable Values, Rounded Values, or skipped tally marks, the Sheet Outcome names every one by section, column or field, row, and value, so the SLP can find each in under 30 seconds.
- **SC-004**: Totals and averages in the workbook work on every number column with no manual cleanup, even when some of its cells hold unreadable text, because text cells are skipped.
- **SC-005**: Sheets with no Unreadable Values or Rounded Values produce identical workbook results before and after this feature.

## Assumptions

- "Field types" in the request is read as every typed value the app imports: Simple Form fields, table columns of all seven Column Types, and tally marks. This was confirmed in clarification.
- The written text goes in the cell itself, chosen over a hover note or an extra column. A typed column can therefore mix values with occasional text cells. Spreadsheet totals and averages skip those text cells, and sorting puts them apart from the values.
- The kept text contains only what was written on the sheet, which is already stored in the same workbook. Privacy rules are unchanged (Principle I).
- The session Date and Time IN that name a Session Tab keep their current handling. An unreadable date or time already sorts last and does not fail the import.
- Leniency is not configurable per template, column, or field. Every typed value is lenient. A stricter mode can be added later if the SLP asks for it.
- Layout mismatches (missing columns, unmatched tables) remain fatal. This feature is about what the SLP writes, not the shape of the printed sheet.
- The existing synthetic sample `therepy_sessions/sample_data/007/bad_values.json` now imports with warnings instead of failing, and can serve as a test input.
