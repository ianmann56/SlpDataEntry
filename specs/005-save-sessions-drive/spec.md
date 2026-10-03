# Feature Specification: Save Imported Sessions to Google Drive

**Feature Branch**: `005-save-sessions-drive`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "Replace the faked out debug call in the import window to save the sheet data (which is now parsed and interpreted) to a spread sheet on google drive. Each student + template combo gets its own sheet file. Each import for that student with that template represents a day's session and is saved as an individual tab in that sheet. If the user switches templates for a student, new imports under the new template start a new sheet. Use the student's initials and the actual structure of the template (not its name, matched on key so order does not matter) to identify the sheet to save to. The sheet is named from the student's initials and the name of the template that started it. Tabs are named with the session date from the sheet content; duplicates get a number appended. Each tab contains only the imported values, not template or interpretation metadata such as field options. All imported data must be present. All sheets are saved together in a Google Drive folder titled "SLP Therepy Data/Current Year"."

## Clarifications

### Session 2026-10-02

- Q: Should a change that keeps every key but changes a field's value type or its allowed choices count as a different template structure? → A: No. Only sections and their keys count; value types and choice options are metadata and do not start a new workbook.
- Q: Where is the link between "student + template structure" and its workbook kept? → A: As a hidden label on each workbook in Drive (Student Key plus a structure fingerprint); the app finds workbooks by searching the folder for it. Nothing is kept locally.
- Q: Should saved values be real numbers or plain text? → A: Values whose interpreted type is a number are saved as numbers; all others are saved as plain text exactly as read, with no automatic conversion. The plan must keep this decision derived from the template's value types so a later feature can let the SLP configure it per field on the template (that configuration is out of scope here).
- Q: Where does a new session tab go among existing tabs? → A: Ordered by session date, newest first (later refined to date then Time IN; see below).
- Q: How are header and form values laid out at the top of a tab? → A: A vertical list (field name in column A, value in column B, one field per row), then a blank row, then each table or tally block.
- Q: When templates with the same keys in a different order share a workbook, which order do tabs use? → A: The order of the template that started the workbook, stored with the workbook's hidden label and used for every later tab.
- Q: When does the app make sure the SLP is signed in to Google? → A: When Import is pressed, before any sheet is read: sign in if needed and confirm the folder exists. If that fails, the import does not start and the SLP is told why.
- Q: If several workbooks in the folder carry the same student and template structure (e.g. a copy made in Drive), which one is used? → A: The most recently changed one.
- Q: After a sheet is saved, what should its row in the Import window show? → A: A status indicator showing whether the sheet's import (including its save) succeeded or failed, plus an Open action on succeeded rows that opens the saved tab in the browser.
- Q: If a sheet whose session was already saved is imported again, is it saved again? → A: No; nothing new is written, the row shows succeeded with "already saved", and Open goes to the existing tab. (How a duplicate is recognized was later changed from "same date and identical values" to "same Date and Time IN"; see below.)
- Q: Each sheet has a Time IN and a Time OUT; which time identifies a tab together with the date? → A: Time IN. Tabs are named and identified by session Date plus Time IN (e.g. `9/14/2026 11:00 AM`).
- Q: If an imported sheet has the same Date and Time IN as a saved tab but some values differ, what happens? → A: It is a duplicate: already saved. Nothing is written, the existing tab is kept unchanged, and the row shows succeeded with "already saved". Sheets and tabs are duplicates only when Date and Time IN both match; values are not compared.
- Q: If a sheet's Time IN is blank, does it fail or get saved? → A: It is saved with a date-only tab name (e.g. `9/14/2026`). Such sheets are never treated as duplicates: each gets its own tab, with a number appended when the name is taken (`9/14/2026 2`). Sheets that have a Time IN follow the Date + Time IN duplicate rule.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Save each imported session to the student's Google Sheet (Priority: P1)

After a day of sessions, the SLP imports a batch of photographed Student Data Sheets. Instead of only being printed to the developer console, each successfully interpreted sheet is saved to Google Drive. Every student has one Google Sheet per template structure (the **Student Session Workbook**), stored in the `SLP Therepy Data/Current Year` folder. Each imported session becomes a new tab in that workbook, named with the session Date and Time IN written on the sheet. The first import for a student and template creates the workbook; later imports add tabs to it.

**Why this priority**: This is the Storage step of the pipeline. Without it, the import produces nothing the SLP can keep, review, or analyze.

**Independent Test**: With student `JA` assigned a template, import one synthetic sample sheet dated `9/14/2026` with Time IN `11:00 AM`. Confirm a workbook named from `JA` and the template name now exists in `SLP Therepy Data/Current Year` with a tab named `9/14/2026 11:00 AM` holding the sheet's values. Import a second sheet for `JA` dated `9/16/2026` and confirm it appears as a second tab in the same workbook, with no new workbook created.

**Acceptance Scenarios**:

1. **Given** student `JA` has a Current Template and no workbook exists for `JA` with that template's structure, **When** a sheet for `JA` is imported, **Then** a new workbook is created in `SLP Therepy Data/Current Year`, named from `JA` and the template's name, with one tab named with the session Date and Time IN on the sheet.
2. **Given** a workbook already exists for `JA` with that template's structure, **When** another sheet for `JA` is imported, **Then** a new tab is added to that existing workbook and no new workbook is created.
3. **Given** a batch mixes sheets for `JA` and `BK`, **When** the batch is imported, **Then** each sheet is saved to the workbook of its own student, never to another student's workbook.
4. **Given** the folder `SLP Therepy Data/Current Year` does not exist in the SLP's Google Drive, **When** the first sheet is saved, **Then** the folder (and its parent) is created and the workbook is placed inside it.
5. **Given** a sheet has been saved, **When** the SLP looks at the Import window, **Then** that sheet's row shows it succeeded only after the save completed.
6. **Given** a sheet has been saved, **When** the SLP chooses Open on its row, **Then** the saved tab opens in their web browser.

---

### User Story 2 - Every imported value is in the tab, and nothing else (Priority: P1)

The SLP opens a session tab and sees exactly what was written on the paper sheet: the header values (Student Key, Date, Time IN, Time OUT, Goal, Measure), every form value, and every table and running tally with its column names and cell values. The tab does not show template or interpretation details such as the list of allowed choices for a field, value types, section ids, or the template's name or description.

**Why this priority**: A session tab that drops values loses therapy data; a tab cluttered with configuration is hard to read and analyze. Both are as essential as saving at all.

**Independent Test**: Import a synthetic sample sheet whose template uses a form section, a table with choice columns, and a running tally. Compare the tab against the interpreted Data Sheet: every header value, form value, table cell, and tally mark is present, and no choice option lists, type names, or template metadata appear.

**Acceptance Scenarios**:

1. **Given** an interpreted Data Sheet with header values, form values, tables, and running tallies, **When** it is saved, **Then** the tab contains every one of those values.
2. **Given** a table column offers choices (e.g. `Y`, `N`, `P`), **When** the sheet is saved, **Then** the tab shows only the value recorded in each cell, not the list of choices.
3. **Given** a table or tally, **When** it is saved, **Then** its column names appear as headers above its values so each value can be read in context.
4. **Given** a form value or cell was left blank on the paper sheet, **When** it is saved, **Then** it appears as an empty cell in its place, so the layout of the remaining values is not shifted.

---

### User Story 3 - The workbook follows the template's structure, not its name (Priority: P2)

Over a school year the SLP adjusts templates. When a student's sheet layout really changes, the SLP wants the new sessions in a fresh workbook so each workbook has one consistent layout across all its tabs. When the SLP only renames a template, copies it under a new name, or reorders its sections or fields, the sessions should keep going to the existing workbook because the layout did not really change.

**Why this priority**: It keeps each workbook consistent and analyzable across sessions. The basic save (Stories 1–2) works without it for a student who never changes templates.

**Independent Test**: Import a sheet for `JA` under template A. Assign `JA` a different template B with the same name as A but a different field; import again and confirm a second workbook is created. Assign `JA` template C, which has a different name but the same sections and fields as A in a different order; import again and confirm the tab is added to the first workbook.

**Acceptance Scenarios**:

1. **Given** `JA` has a workbook started with template A, **When** `JA`'s Current Template is changed to a template with a different structure and a sheet is imported, **Then** a new workbook is created for `JA` named from the new template's name, and the old workbook is unchanged.
2. **Given** `JA` has a workbook started with template A, **When** `JA`'s Current Template is changed to another template with the same name as A but a different structure, **Then** new imports go to a new workbook, even though the names match.
3. **Given** `JA` has a workbook started with template A, **When** `JA`'s Current Template is changed to a template with a different name but the same structure as A, **Then** new imports go to the existing workbook, and the workbook keeps its original name.
4. **Given** two templates have the same sections, fields, and columns listed in a different order, **When** their structures are compared, **Then** they are treated as the same structure.
5. **Given** `JA` switched from template A to template B and later back to template A (or a template with A's structure), **When** a sheet is imported, **Then** it is saved to the original workbook started with A.
6. **Given** `JA` and `BK` use the same template, **When** sheets for each are imported, **Then** each student has their own workbook.

---

### User Story 4 - Several sessions in a day, and re-imports (Priority: P3)

Sometimes a student has more than one session on the same day; each has its own Time IN, so each gets its own tab. Sometimes the SLP imports a sheet that is already saved (the same photo again, or a retake). A sheet whose Date and Time IN match a saved tab is the same session, so nothing new is written and the saved tab is kept as it is.

**Why this priority**: It happens rarely, but without it a second session on one day could be lost, or a re-import could double-count a session.

**Independent Test**: Import two sheets for `JA` dated `9/14/2026`, one with Time IN `11:00 AM` and one with `1:30 PM`. Confirm the workbook has two tabs, `9/14/2026 1:30 PM` and `9/14/2026 11:00 AM`. Import the `11:00 AM` sheet again, or a retake that reads one tally differently, and confirm no new tab is created, the existing tab is unchanged, and the row shows "already saved".

**Acceptance Scenarios**:

1. **Given** `JA`'s workbook has a tab for `9/14/2026 11:00 AM`, **When** a sheet for `JA` dated `9/14/2026` with Time IN `1:30 PM` is saved, **Then** a new tab `9/14/2026 1:30 PM` is created and the existing tab is not changed.
2. **Given** `JA`'s workbook has a tab for `9/14/2026 11:00 AM`, **When** a sheet with the same Date and Time IN is imported again, whether its other values match or not, **Then** no new tab is created, the existing tab is not changed, the row shows succeeded with "already saved", and Open goes to the existing tab.
3. **Given** two sheets for `JA` with the same Date and Time IN are in the same batch, **When** the batch is imported, **Then** the first is saved and the second shows succeeded with "already saved".
4. **Given** `JA`'s workbook has a tab `9/14/2026` from a sheet with a blank Time IN, **When** another sheet for `JA` dated `9/14/2026` with a blank Time IN is imported, **Then** it is saved to a new tab `9/14/2026 2`, and the first tab is not changed.

**Tab order** (applies to every save): **Given** `JA`'s workbook has tabs `9/16/2026 11:00 AM` and `9/10/2026 11:00 AM`, **When** a sheet dated `9/14/2026` with Time IN `11:00 AM` is saved, **Then** the tabs read `9/16/2026 11:00 AM`, `9/14/2026 11:00 AM`, `9/10/2026 11:00 AM` (newest first).

---

### Edge Cases

- The sheet's Time IN is blank: the sheet is saved to a tab named with the date alone, plus a number if that name is taken (FR-017a). It is never treated as a duplicate, so importing the same blank-time photo twice creates two tabs.
- The sheet's Date is blank or could not be read: the sheet is marked failed with a reason saying the date is missing, and nothing is saved for it. The SLP fixes the photo or sheet and retries.
- The Session Moment contains characters a tab name cannot hold, or is longer than a tab name allows: the tab name is adjusted to a valid name that still shows the date and time as written as closely as possible.
- Google Drive cannot be reached or sign-in fails when Import is pressed: the import does not start and the SLP is told why (FR-006a).
- Google Drive becomes unreachable, or a save is refused, partway through a batch: that sheet is marked failed with a reason naming the problem (e.g. "Could not save to Google Drive: no connection"), and the other sheets in the batch are still processed.
- A save fails partway (e.g. the tab was created but its values were not written): the sheet is marked failed, and retrying it does not leave a duplicate or half-filled tab behind.
- A failed save is retried with a later Import press in the same window: the sheet is saved once; it is not read again by the reading service if its earlier reading is still valid (existing import retry rules).
- The SLP renames a workbook in Google Drive: later imports still find and add to it.
- The SLP deletes a workbook, or moves it to the trash or out of the `SLP Therepy Data/Current Year` folder: the next import for that student and structure starts a new workbook in the folder.
- The SLP renames a tab: it still counts as that session, because duplicates are found from the Date and Time IN in the tab, not its name. The SLP deletes a tab: that session can be imported again and gets a new tab. New tab names are unique among the tabs that exist at the time of saving.
- The student's Student Key is later changed in the Students window: the existing workbook keeps its name; new imports under the new key start a new workbook named with the new key.
- The SLP copies a workbook in Drive and the copy carries the same hidden label: new sessions go to whichever of them was changed most recently (FR-013b). Since each save changes that workbook, later saves keep going to it until the SLP edits the other one.
- A new workbook would have the same name as an existing file in the folder (e.g. two structures started by templates with the same name for the same student): both files are kept; each is identified by its structure, not its name.

## Requirements *(mandatory)*

### Functional Requirements

**Replacing the debug output**

- **FR-001**: When a sheet is interpreted successfully during an import, the application MUST save it to Google Drive as described below, instead of printing its debug output as the only result.
- **FR-002**: A sheet MUST be shown as succeeded in the Import window only after its save has completed. If the save fails, the sheet MUST be shown as failed with a reason the SLP can understand, and nothing partial MUST remain from that attempt.
- **FR-003**: A failure to save one sheet MUST NOT stop the other sheets in the batch from being processed and saved.
- **FR-003a**: Each row in the Import window MUST show a status indicator that tells at a glance whether the sheet's import succeeded (interpreted and saved) or failed. A row not yet imported MUST look different from both.
- **FR-003b**: Each succeeded row MUST offer an Open action that opens that sheet's saved tab in the SLP's web browser. Failed and not-yet-imported rows MUST NOT offer it.
- **FR-004**: A sheet whose save failed MUST be retried on the next Import press, following the existing retry rules (it is not shown as succeeded, and its earlier reading is reused when still valid).

**Folder**

- **FR-005**: All workbooks MUST be saved in the Google Drive folder `SLP Therepy Data/Current Year` (a folder named `Current Year` inside a folder named `SLP Therepy Data`) in the signed-in SLP's Drive.
- **FR-006**: If either folder does not exist, the application MUST create it. If it exists, the application MUST reuse it and MUST NOT create a duplicate.
- **FR-006a**: When the SLP presses Import, and before any sheet is read, the application MUST confirm it can reach the SLP's Google Drive, asking the SLP to sign in if needed, and MUST find or create the folder (FR-005, FR-006). If this fails (sign-in cancelled or refused, no connection), the import MUST NOT start, no sheet is read, and the window MUST tell the SLP why, the same way it reports unreadable student or template records.

**Workbook per student and template structure**

- **FR-007**: Each combination of Student Key and Template Structure MUST have exactly one Student Session Workbook.
- **FR-008**: To decide which workbook a sheet is saved to, the application MUST use the sheet's student (by Student Key) and the Template Structure of the template used to interpret it. The template's name, description, and id MUST NOT affect which workbook is chosen.
- **FR-009**: Two templates MUST be treated as having the same Template Structure when they have the same set of sections and, within each section, the same set of keys (field names, column names, and tally columns), regardless of the order in which sections, fields, or columns are listed. Value types and lists of allowed choices MUST NOT be part of the Template Structure: a change that keeps every key but changes a field's type or choices (e.g. adding `P` to a `Y`/`N` column) keeps saving to the same workbook.
- **FR-010**: When no workbook exists yet for a sheet's Student Key and Template Structure, the application MUST create one in the folder and save the sheet to it.
- **FR-011**: A new workbook MUST be named from the Student Key and the name of the template used to start it (e.g. `JA - Emotion Causes`). The workbook's name MUST NOT change when later imports use a template with the same structure but a different name.
- **FR-012**: When a workbook already exists for a sheet's Student Key and Template Structure, the application MUST add the sheet to it and MUST NOT create another workbook.
- **FR-013**: The application MUST find an existing workbook by its Student Key and Template Structure, even if the SLP has renamed it in Drive, as long as it is still in the folder and not in the trash. A workbook that is deleted, trashed, or moved out of the folder MUST be treated as missing, so the next import starts a new one.
- **FR-013a**: Each workbook MUST carry a hidden label in Drive (not shown in its name or tabs) holding its Student Key, a fingerprint of its Template Structure, and its Workbook Layout Order (FR-025a). The application MUST find workbooks by searching the folder for this label, and MUST NOT depend on any local record, so the same workbooks are found from any computer or after a reinstall.
- **FR-013b**: When more than one workbook in the folder carries the same Student Key and Template Structure (for example, the SLP copied a workbook in Drive), the application MUST save to the one most recently changed in Drive, and MUST NOT change, merge, or remove the others.

**Session tabs**

- **FR-014**: Each successfully imported sheet MUST be saved as its own new tab in its workbook, unless it is already saved (FR-016a). Saving MUST NOT change or remove any existing tab.
- **FR-015**: The tab MUST be named with the session Date followed by a space and the Time IN, both as read from the sheet's content (e.g. `9/14/2026 11:00 AM`), never the date or time of the import. Together, Date and Time IN form the sheet's **Session Moment**, which identifies the session within its workbook.
- **FR-016**: A sheet and a saved tab are duplicates only when both have a Time IN and their Session Moments match, that is, the same Date and the same Time IN (compared ignoring letter case and surrounding spaces). A sheet with a blank Time IN is never a duplicate, and is never matched by a later sheet. Other values MUST NOT be compared. A tab's Session Moment MUST be taken from the Date and Time IN values held in the tab, not from its name, so renaming a tab does not hide it.
- **FR-016a**: Before saving, the application MUST check the workbook for a duplicate tab (FR-016). If one exists, the application MUST NOT write or change any tab; the sheet MUST be shown as succeeded with an "already saved" note, and its Open action MUST open the existing tab.
- **FR-016b**: When a new tab's name is already used by a tab that is not a duplicate (for example, an earlier blank-Time-IN sheet with the same date, a tab the SLP renamed, or two different Session Moments that became the same name after adjustment per FR-018), the application MUST append a space and the lowest number, starting at 2, that gives a unique name.
- **FR-017**: A sheet with no readable session Date MUST be marked failed with a reason saying the date is missing, and MUST NOT be saved.
- **FR-017a**: A sheet with a blank Time IN MUST still be saved. Its tab MUST be named with the Date alone (e.g. `9/14/2026`), made unique per FR-016b (`9/14/2026 2`, `9/14/2026 3`, ...). Its Time IN appears as an empty cell in the tab.
- **FR-018**: When the Session Moment contains characters not allowed in a tab name, or is too long, the application MUST adjust it to a valid tab name and still keep the name unique per FR-016b.
- **FR-018a**: Session tabs MUST be ordered by Session Moment (date, then Time IN), newest first, whatever order the sheets are imported in. A new tab MUST be placed among the existing tabs at its Session Moment's position. A tab whose date cannot be read as a calendar date MUST be placed after all dated tabs; among tabs with the same date, one whose Time IN is blank or cannot be read as a clock time MUST be placed after those whose time can, and blank-Time-IN tabs for the same date MUST keep their save order, newest first. Placing a new tab MUST NOT change the contents of any existing tab.
- **FR-019**: A newly created workbook MUST contain only session tabs; it MUST NOT keep an empty default tab.

**Tab contents**

- **FR-020**: A session tab MUST contain every value from the interpreted Data Sheet: Student Key, Date, Time IN, Time OUT, Goal, Measure, every form value, and every cell of every table and running tally.
- **FR-021**: Header and form values MUST be listed first, starting at the top of the tab, one field per row: the field name in the first column and its value in the second. The header fields (Student Key, Date, Time IN, Time OUT, Goal, Measure) come first in that order, followed by the form values.
- **FR-022**: After the header and form list, and one blank row, each table and running tally MUST appear as a block of rows under a header row of its column names, with blocks separated by one blank row, with one row per row of the paper sheet, in the order the rows appear on the sheet. Each block MUST be labeled with its section title when it has one.
- **FR-023**: A session tab MUST NOT contain template or interpretation metadata: no lists of allowed choices, no value types, no section or template ids, and no template name or description.
- **FR-024**: Values MUST be saved as they were interpreted. Blank values MUST be saved as empty cells in their place.
- **FR-024a**: A value whose interpreted type is a number MUST be saved as a number the spreadsheet can calculate with. Every other value (text, choice, date, yes/no, and raw form text) MUST be saved as plain text exactly as read, and the spreadsheet MUST NOT auto-convert it (e.g. `9/14` stays text, `007` keeps its zeros). If a number-typed value cannot be read as a number, it MUST be saved as plain text rather than dropped.
- **FR-024b**: How each value is saved MUST be decided from that value's type in the interpretation (which comes from the template), not from guessing at its content, so a later feature can let the SLP choose it per field on the template without changing the save rules.
- **FR-025**: Every tab in a workbook MUST lay out its values in the same positions, so the tabs of one workbook can be compared or combined.
- **FR-025a**: The order of form fields, of table and tally blocks, and of columns within each block MUST follow the Workbook Layout Order: the order in the template that started the workbook. Later imports with a same-structure template listed in a different order MUST still use the Workbook Layout Order. The Workbook Layout Order MUST be stored with the workbook's hidden label (FR-013a), so it survives reinstalls and other computers.

**Privacy**

- **FR-026**: Session data MUST be sent only to the SLP's Google Drive and Google Sheets (an approved service) and MUST NOT be written to any local persistent log.
- **FR-027**: Workbook names, tab names, and messages shown in the Import window MUST identify students only by Student Key.
- **FR-028**: The hidden workbook label MUST identify the student only by Student Key and MUST NOT contain session values; the structure fingerprint and the Workbook Layout Order MUST be derived only from template keys.

### Key Entities *(include if feature involves data)*

- **Interpretation** (`StudentDataSheet`): Existing concept. The interpreted result for one sheet; the source of every value saved.
- **Template Structure**: The shape of a Data Sheet Template that decides where its sessions are saved: its sections and, within each, the set of field, column, and tally keys, compared without regard to order. It ignores the template's name, description, id, value types, and choice options. New glossary term.
- **Student Session Workbook**: The Google Sheet holding every saved session for one Student Key and one Template Structure. Named from the Student Key and the name of the template that started it. Lives in `SLP Therepy Data/Current Year`. Carries a hidden label (Student Key, structure fingerprint, and Workbook Layout Order) used to find it and lay out its tabs. Replaces the glossary's **Session Sheet** entry as the tool's output.
- **Workbook Layout Order**: The order of sections, form fields, and columns taken from the template that started a workbook. Every tab in that workbook uses it. New glossary term.
- **Session Moment**: A sheet's session Date plus its Time IN, as read from the sheet. It names a Session Tab and identifies the session within a workbook. A sheet with a blank Time IN has a date-only Session Moment, which never identifies a duplicate. New glossary term.
- **Session Tab**: One tab in a Student Session Workbook holding the values of one imported sheet, named with that sheet's Session Moment.
- **Therapy Data Folder**: The Drive folder `SLP Therepy Data/Current Year` holding every Student Session Workbook.
- **Student** and **Current Template**: Existing concepts. The sheet's Student Key and the Current Template used to interpret it select the workbook.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After importing a batch, 100% of sheets shown as succeeded have a matching tab in the right student's workbook, and 0 sheets shown as failed have one.
- **SC-002**: For every saved tab, 100% of the values in the interpreted Data Sheet are present in the tab, and 0 choice lists, value types, or template details appear.
- **SC-003**: Across a school year of imports for one student and one template structure, all sessions are in a single workbook, with exactly one tab per Session Moment (and one per blank-Time-IN sheet), no duplicate tab names, and no tab added or changed by re-importing an already-saved session.
- **SC-004**: Renaming a template, reordering its fields, or changing a field's type or choices never creates a new workbook; adding, removing, or renaming a section, field, or column always does, in 100% of tested cases.
- **SC-005**: The SLP can open a student's workbook in Google Drive and find a given session by its date in under 30 seconds, without opening other files.
- **SC-006**: Importing and saving a batch of 10 sheets takes no more than 1 minute longer than importing the same batch without saving, on a typical school network connection.

## Assumptions

- The SLP signs in to Google with the existing sign-in flow the application already uses for Google Sheets and Drive. This feature does not change how sign-in works, though it may need Drive access to folders and files it creates.
- `SLP Therepy Data/Current Year` is a literal folder path. Rolling over to a new school year (e.g. renaming `Current Year` to an archive name) is done by the SLP by hand in Drive and is out of scope; after a rollover, new imports start new workbooks in a fresh `Current Year` folder.
- The folder name keeps the spelling `Therepy` as given, matching the project's existing naming.
- The session Date is saved, and used as the tab name, exactly as interpreted from the sheet. It is read as a calendar date (month/day/year, as US school sheets are written), and Time IN as a clock time, only to order tabs (FR-018a). Time IN is saved and used in the tab name exactly as read. Reformatting dates into one standard format is out of scope.
- A retake whose reading differs from the saved tab is still a duplicate when its Date and Time IN match (FR-016), so it never replaces the saved tab. To replace a saved session, the SLP deletes its tab in Drive and imports again.
- The summaries, charts, and progress text from the existing prototype output (`create_therapy_session_sheet`) are out of scope. Session tabs hold only the imported values; analysis comes in a later feature.
- Letting the SLP choose on a template how each field is saved (number, text, date, etc.) is a planned later feature and out of scope. This feature uses the value types templates already have.
- The prototype output code with hard-coded sample data is replaced or removed by this feature.
- The debug print may still be shown on the developer console as a local aid, but it is no longer the result of an import.
- Only one SLP uses the application at a time on one computer, with one Google account; no one else edits the workbooks' tab lists during an import.
- Sheets are saved one at a time as each is interpreted, in the order the import processes them.
