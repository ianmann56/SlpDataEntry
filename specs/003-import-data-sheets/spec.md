# Feature Specification: Import Data Sheets

**Feature Branch**: `003-import-data-sheets`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "We're gonna implement the import window. The window should let the user select multiple files (image files only). They should be able to add or remove more files before they submit this list. The user will click "Import" after they've selected all the files they want. Once they click "Import", each file will get read, parsed with the image_to_text method. The result of that read will yield an object that contains some parsed fields from the data sheet. One of those fields will be the student's initials (their Student Key). This Student Key will be used to load their current template. Then, the template will be used to interpret the parsed student data sheet. Some assumptions that should be taken into consideration: The list of files selected by the SLP will be from a variety of students, not all from the same student. The list of files selected by the SLP will, therefore, not all have the same applicable template. Load the template for each sheet depending on the student for that sheet. Once the student data sheet is interpreted, for now, just print out the debug method from the sheet (see how program_interpretation.py does it)"

## Clarifications

### Session 2026-10-01

- Q: When the SLP presses Import a second time on the same list, should sheets that already succeeded be read again by the reading service? → A: No. Succeeded sheets are skipped, and failed sheets reuse their earlier reading; only files that could not be read are sent to the reading service again.
- Q: What should happen if the SLP presses Back or closes the window while an import is still running? → A: A Cancel button stops the import after the current sheet; Back is unavailable until the import stops or finishes.
- Q: When a sheet is interpreted successfully, should its row in the Import window show the Student Key that was read from it? → A: Yes. A succeeded row shows the Student Key and the name of the template used.
- Q: If the SLP overwrites a photo with a retake under the same file name, should the next Import press read the new photo or reuse the earlier reading? → A: Re-read the file automatically if it changed on disk since it was read.
- Q: After the SLP presses Import a second time, should the summary count every file in the list, or only the files processed in that run? → A: Both: this run's counts plus totals for the whole list.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import a batch of sheets from several students (Priority: P1)

After a day of sessions, the SLP has photographed the Student Data Sheets of several different students. They open the **Import** window from the home screen, select all of the photos at once, and press **Import**. For each photo, the application reads the sheet, finds the Student Key on it, looks up that student's Current Template, and interprets the sheet with that template. Each sheet is matched to its own student's template, so a single batch can mix students with different sheet layouts. For now, the result of each interpretation is printed to the developer console so the SLP (or developer) can confirm it is correct.

**Why this priority**: This is the core of the import path. Without it, the Import button on the home screen leads nowhere and the templates and students set up in earlier features have no use.

**Independent Test**: Set up two students (e.g. `JA` and `BK`) with different Current Templates. Select one synthetic sample sheet for each student and press Import. Confirm the console shows one interpreted Data Sheet per file, each with the right Student Key and with tables and scalars that match that student's template.

**Acceptance Scenarios**:

1. **Given** the SLP is on the home screen, **When** they choose Import, **Then** the Import window opens with an empty list of selected files and the Import button unavailable.
2. **Given** the Import window is open, **When** the SLP adds files, **Then** the file picker lets them choose several image files at once and offers only image files.
3. **Given** files for students `JA` and `BK` are selected and each student has a Current Template, **When** the SLP presses Import, **Then** each sheet is interpreted with the Current Template of the student whose Student Key is on that sheet.
4. **Given** a sheet has been interpreted, **When** interpretation completes, **Then** the interpreted Data Sheet is printed to the developer console in the same format the existing debug output uses (Student Key, Date, Time In, Time Out, Goal, Measure, other scalars, tables).
5. **Given** the import has finished, **When** the SLP looks at the Import window, **Then** each selected file shows whether it was interpreted successfully (with the Student Key read and the name of the template used) or why it failed.

---

### User Story 2 - Build and adjust the file list before importing (Priority: P2)

Photos may be spread across several folders, or the SLP may pick a wrong photo by mistake. Before pressing Import, the SLP can add more files in further rounds of selection and remove any file from the list.

**Why this priority**: The import works with a single selection round, but without add-more and remove, any mistake means closing the window and starting over.

**Independent Test**: Open the Import window, add two files, add a third from a different folder, remove one, and confirm the list shows exactly the two remaining files. Press Import and confirm only those two are processed.

**Acceptance Scenarios**:

1. **Given** the list has files in it, **When** the SLP adds more files, **Then** the new files are appended to the list and the existing ones stay.
2. **Given** a file is already in the list, **When** the SLP adds the same file again, **Then** it appears in the list only once.
3. **Given** the list has files in it, **When** the SLP selects one or more files and removes them, **Then** those files leave the list and the others stay.
4. **Given** the SLP removes the last file, **When** the list becomes empty, **Then** the Import button becomes unavailable again.
5. **Given** the SLP opens the file picker, **When** they cancel it without choosing anything, **Then** the list is unchanged.

---

### User Story 3 - One bad sheet does not stop the batch (Priority: P3)

Some sheets in a batch will not import cleanly: the photo is blurry, the Student Key is missing or mistyped, the student has not been set up, has no Current Template, or the sheet does not match the template. The SLP needs every other sheet to still be interpreted, and needs to know which sheets failed and why so they can fix the setup or retake the photo.

**Why this priority**: Batches mix students and photo quality varies, so failures will happen. But the happy path (Story 1) delivers value on its own.

**Independent Test**: Select three sheets: one valid, one with a Student Key that matches no student, and one for a student with no Current Template. Press Import. Confirm the valid sheet is interpreted and printed, and the other two are marked failed with distinct reasons.

**Acceptance Scenarios**:

1. **Given** a sheet's Student Key matches no saved student, **When** the batch is imported, **Then** that sheet is marked failed with a message naming the Student Key that was read, and the other sheets are still processed.
2. **Given** a sheet's student has no Current Template, or their Current Template no longer exists, **When** the batch is imported, **Then** that sheet is marked failed with a message saying the student's template is missing, and the other sheets are still processed.
3. **Given** no Student Key can be read from a sheet, **When** the batch is imported, **Then** that sheet is marked failed with a message saying no Student Key was found.
4. **Given** a sheet does not match its student's template, **When** it is interpreted, **Then** that sheet is marked failed with the reason, and no partial result is printed for it.
5. **Given** a sheet cannot be read (e.g. the file is unreadable or the reading service reports an error), **When** the batch is imported, **Then** that sheet is marked failed with the reason, and the other sheets are still processed.

---

### Edge Cases

- The reading service misreads a Student Key as another real student's key (e.g. `JA` read as `JB`): if the sheet fits that student's template, it succeeds. The SLP catches the mismatch from the Student Key shown on the succeeded row (FR-015).
- A Student Key on the sheet differs from the saved key only in letter case or surrounding spaces (e.g. ` ja ` vs `JA`): it matches, using the same rule the Students window uses.
- Several sheets in one batch belong to the same student: each is interpreted with that student's Current Template.
- A selected file is moved or deleted after it was added but before Import: that file is marked failed and the rest continue.
- The SLP wants to leave while an import is running: Back is unavailable, so they press Cancel first. Cancel lets the sheet being processed finish, then stops. Sheets not reached keep the "not yet imported" outcome and are processed on the next Import press. The title-bar close still exits the application; no partial result is printed for a sheet whose interpretation did not complete.
- The SLP presses Import again after a batch finishes: sheets that succeeded are skipped and keep their outcome. Failed sheets are processed again so a sheet that failed because of setup can be retried after fixing that setup. A failed sheet that was already read reuses that reading; only a file whose reading failed is sent to the reading service again. Newly added files are read as usual.
- The SLP saves a retaken photo over a failed file under the same name: on the next Import press the file's change is detected, so it is read again instead of reusing the old reading.
- The student records or templates file cannot be read when Import is pressed: the import does not start and the SLP is told why.

## Requirements *(mandatory)*

### Functional Requirements

**File list**

- **FR-001**: The Import window MUST let the SLP add files through a file picker that allows choosing several files at once.
- **FR-002**: The file picker MUST offer only image file types the reading service supports (PNG, JPEG, and TIFF).
- **FR-003**: The SLP MUST be able to add files in more than one round; each round appends to the list.
- **FR-004**: The list MUST NOT contain the same file twice.
- **FR-005**: The SLP MUST be able to remove one or more selected files from the list.
- **FR-006**: The list MUST show each file so the SLP can tell the files apart (at least the file name).
- **FR-007**: The Import action MUST be available only when the list has at least one file and no import is running.

**Import and interpretation**

- **FR-008**: When the SLP presses Import, the application MUST process every file in the list that has not yet succeeded. A file with no reading yet MUST be read with the existing image reading step, producing one Import per file.
- **FR-008a**: A file MUST be sent to the reading service at most once per successful reading while the Import window is open. A later Import press MUST reuse a file's earlier Import and MUST skip files that already succeeded. Only files whose reading failed, or whose file changed on disk since it was read (its last-modified time differs), are read again.
- **FR-009**: For each Import, the application MUST take the Student Key read from the sheet and find the saved student whose key matches it, ignoring letter case and surrounding spaces.
- **FR-010**: For each matched student, the application MUST load that student's Current Template and interpret the sheet with it. The template MUST be chosen per sheet, never once for the whole batch.
- **FR-011**: For each sheet interpreted successfully, the application MUST print the interpreted Data Sheet's debug output to the developer console, as the existing developer interpretation script does.
- **FR-012**: A failure on one sheet MUST NOT stop the other sheets from being processed.
- **FR-013**: A sheet MUST be marked failed, with a reason the SLP can understand, when: the file cannot be read; no Student Key is found on it; its Student Key matches no saved student; the student has no Current Template; the Current Template no longer exists; or the sheet does not match the template.
- **FR-014**: A sheet that does not match its template MUST fail loudly. No partial interpretation is printed for it.
- **FR-015**: After the import finishes, the Import window MUST show each file's outcome (succeeded or failed with its reason), and a summary with two parts: how many succeeded and failed in this run, and totals for the whole list (succeeded, failed, not yet imported). A succeeded file MUST show the Student Key read from it and the name of the template used, so the SLP can spot a sheet matched to the wrong student.
- **FR-016**: While the import is running, the window MUST show that work is in progress and MUST stay responsive enough to repaint and show progress.
- **FR-016a**: While the import is running, the window MUST offer a Cancel action. Cancel MUST let the sheet currently being processed finish, then stop. The remaining sheets MUST keep the "not yet imported" outcome, and the whole-list totals MUST count them as not imported.
- **FR-016b**: While the import is running, Back and the add/remove file actions MUST be unavailable. They become available again once the import finishes or is cancelled.

**Navigation**

- **FR-017**: The Import window MUST replace the current placeholder reached from the home screen's Import choice, and MUST keep its Back button returning to the home screen (when no import is running, per FR-016b) and its title-bar close exiting the application.

**Privacy**

- **FR-018**: Sheet images and their content MUST be sent only to the existing approved reading service. Debug output MUST go only to the local console and MUST NOT be written to a persistent log.
- **FR-019**: Failure messages and status shown in the window MUST identify students only by Student Key.

### Key Entities *(include if feature involves data)*

- **Selected File**: An image file the SLP has added to the list, identified by its location on disk. Has an outcome after an import: not yet imported, succeeded, or failed with a reason. Once read, it keeps its Import, and the file's last-modified time at reading, for the rest of the window session, so a retry does not read it again unless the file has changed. Removing the file from the list discards its Import.
- **Import** (`StudentDataSheetImport`): Raw reading of one sheet, including the Student Key written on it. Existing concept.
- **Student** and **Current Template**: Existing concepts from the Students feature. The Student Key on the sheet selects the Student; the Student's Current Template selects the Data Sheet Template.
- **Data Sheet Template**: Existing concept. Turned into an interpreter to produce the Data Sheet.
- **Interpretation** (`StudentDataSheet`): The interpreted result for one sheet. In this feature it is only printed; it is not stored or sent onward.
- **Import Batch**: The set of Selected Files processed by one press of Import (all files not yet succeeded), with per-file outcomes and this run's success/failure count. The window also keeps totals across the whole list.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The SLP can select a batch of 10 sheets from at least 3 different students (in any number of selection rounds) and start the import in under 1 minute.
- **SC-002**: In a batch mixing students with different templates, 100% of valid sheets are interpreted with the template of the student named on that sheet.
- **SC-003**: In a batch containing invalid sheets, 100% of the valid sheets are still interpreted, and 100% of the invalid sheets are marked failed with a reason.
- **SC-004**: For each failed sheet, the SLP can tell from the window alone which fix is needed (set up the student, assign a template, fix the template, or retake the photo), without reading the console.
- **SC-005**: The window remains responsive (can repaint and show progress) throughout an import of 10 sheets.

## Assumptions

- The Student Key comes from the Import's parsed form data, as the existing interpreter already reads it. This feature does not change how the Student Key is found on the sheet.
- The batch is processed one sheet at a time. Speeding it up by reading sheets in parallel is out of scope.
- Printing the debug output is a temporary stand-in for the Storage step. Writing a Session Sheet to Google Sheets, and saving interpreted results, are out of scope and come in a later feature.
- Successful sheets stay in the list after the import, with their outcome shown. The SLP can remove them or go Back; the list is not kept after leaving the window.
- PDF and other non-image files are out of scope, even though the reading service could accept some of them.
- The Import window uses the same student records and templates the Setup path manages, and the same approved reading service the developer script uses today.
- Once this path works, the temporary developer-only interpretation script (`program_interpret.py`) is no longer needed. Removing it may be done in this feature or later, as decided in planning.
- Only one SLP uses the application at a time on one computer; there is no concurrent editing of students or templates during an import.
