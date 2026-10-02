# Feature Specification: View and Edit Data Sheet Templates

**Feature Branch**: `004-view-edit-templates`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "Add the ability to edit and view the details for templates in the template management window."

## Clarifications

### Session 2026-10-01

- Q: When editing a template, should the SLP be able to change an existing interpreter's settings directly, or only add and remove whole interpreters? → A: Change directly. Selecting an interpreter opens its form filled in with the saved values. Saving the form replaces that interpreter, and it keeps its ID and position.
- Q: Before saving changes to a template, should the SLP be told which students use it? → A: Yes, and more. The details view lists the Student Keys of students who use the template. If any students use it, saving asks the SLP to confirm and lists their Student Keys. The template list shows how many students use each template.
- Q: Should viewing and editing be two separate screens, or one screen that opens read-only and switches into editing in place? → A: One screen, the **Template Details** window, with two modes. It opens in *view mode* (read-only) from View or a double-click. Edit, from that window or from the management list, switches it to *edit mode*. Save or Cancel switches it back to view mode.
- Q: Should templates get a saved description that the SLP can see and edit in the Template Details window? → A: Yes. The description typed when creating a template is saved. View mode shows it and edit mode can change it. Templates saved without one show an empty description.
- Q: When the SLP deletes a template that students are using, what should happen? → A: The delete confirmation lists the Student Keys of the students using it and says they will need a new template. If the SLP confirms, those students' Current Template is cleared, so they show as having none, and then the template is deleted. Unused templates keep the plain confirmation.
- Q: Should creating a new template also use the Template Details window, opening empty in edit mode, in place of the separate Create window? → A: No. Keep the separate Create window, which now also saves the description. The Template Details window is only for existing templates. Direction for the plan: wherever possible, share business logic between the two windows, especially validation, instead of writing it twice.
- Q: (Revisited after implementation) Should the Create window reuse the edit view? → A: Yes. One shared template form shows a draft of the template and lets the SLP change it, with no saving of its own. The Create window and the Template Details window are separate parent windows around that form, and each keeps only what is not shared: creating a new template, or view/edit modes, usage, and saving over an existing one.
- Q: In edit mode, when the SLP has changed an interpreter's form but hasn't applied it, and then selects a different interpreter or presses the template's Save, what happens to the unapplied changes? → A: They are applied automatically, using the same checks as applying by hand. The interpreter form also has a Cancel button that discards its unapplied changes and puts back the interpreter's saved values.
- Q: This feature asks before throwing away unsaved template changes, but the Students window does so silently. Should the two behave the same? → A: No, keep the difference. Template edits ask before discarding, because one template can affect several students. The Students window keeps discarding silently, and this feature does not change it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View a template's details (Priority: P1)

The SLP opens **Data Sheet Templates** and picks a template from the list to check what it contains: its name, its description, and every section interpreter in it, in order. For each interpreter they see its type, its title, and its configuration, such as a table's columns, a running tally's tally characters, or a simple form's field names. They also see which students use the template, by Student Key. The template list itself shows how many students use each template. They can do this without any risk of changing the template.

Today, choosing a template only opens a placeholder that says "Implementation coming soon". After saving a template, the SLP has no way to see what is in it.

**Why this priority**: The SLP has to be able to see what a template holds before they can decide whether it fits a sheet layout or needs changes. It is also the base that editing builds on.

**Independent Test**: Save a template with one interpreter of each type. Open its details from the management window and confirm that the name and every interpreter's type, title, and configuration match what was entered when it was created. Then close the details and confirm the saved template is unchanged.

**Acceptance Scenarios**:

1. **Given** a saved template with several interpreters, **When** the SLP selects it and chooses to view it, **Then** the Template Details window opens in view mode, showing the template's name, its description, and lists each interpreter in its saved order with its type, title, and configuration.
2. **Given** the template list is showing, **When** the SLP double-clicks a template, **Then** that template's Template Details window opens in view mode.
3. **Given** the Template Details window is open in view mode, **When** the SLP closes it, **Then** nothing about the template has changed and they are back in the management window.
4. **Given** no template is selected, **When** the SLP chooses to view, **Then** they are told to select a template first.
5. **Given** students `JA` and `MK` have a template as their Current Template, **When** the SLP views its details, **Then** the Template Details window lists `JA` and `MK` as using it.
6. **Given** a template no student uses, **When** the SLP views its details, **Then** the Template Details window says no students use it.
7. **Given** the management window is open, **When** the template list is shown, **Then** each template's row shows how many students have it as their Current Template, including 0.

---

### User Story 2 - Edit a template's name and interpreters (Priority: P2)

From the Template Details window, or straight from the management list, the SLP chooses Edit. The same window switches to edit mode, keeping the same layout, and its fields become editable. They can rename the template, change its description, add new interpreters, remove interpreters, change an existing interpreter's title or configuration, and change the order of the interpreters. When they save, the management list shows the change right away, and the change is still there after a relaunch. Students who use the template keep using it, so their future data sheets are read with the updated template.

**Why this priority**: Sheet layouts change during a school year as goals change. Without editing, the SLP has to delete and re-create a template, and then reassign it to every student who used it.

**Independent Test**: With a saved template assigned to a student, rename it, change one interpreter's configuration, remove one, add one, and save. Confirm that the list shows the new name, that view mode shows the new interpreters, that the student still has this template as their Current Template, and that a relaunch shows the same result.

**Acceptance Scenarios**:

1. **Given** the Template Details window is open in view mode, **When** the SLP chooses Edit, **Then** the same window switches to edit mode with the saved name, description, and interpreters filled in.
2. **Given** a template is selected in the management list, **When** the SLP chooses Edit there, **Then** its Template Details window opens directly in edit mode.
3. **Given** the SLP is editing a template, **When** they change the name and save, **Then** the window returns to view mode showing the saved template, and the management list shows the new name, and it is still the new name after a relaunch.
4. **Given** the SLP is editing a template, **When** they select an existing interpreter, change its title or configuration in its filled-in form, and save the template, **Then** view mode shows the new values, with the interpreter still in the same position.
5. **Given** the SLP has changed an interpreter's form without applying it, **When** they select a different interpreter or press the template's Save, **Then** the form changes are applied first, as if they had applied them by hand.
6. **Given** the SLP has changed an interpreter's form without applying it, **When** they press the form's Cancel, **Then** the form shows that interpreter's values from before the change, and the interpreter is unchanged.
7. **Given** applying an interpreter's form automatically would fail its checks (for example, a duplicate title), **When** the SLP selects another interpreter or presses Save, **Then** nothing is switched or saved, the form stays open, and the SLP is told what to fix.
8. **Given** the SLP is editing a template, **When** they change the description and save, **Then** view mode shows the new description, and it is still there after a relaunch.
9. **Given** the SLP is editing a template, **When** they add an interpreter of any available type and save, **Then** the template includes the new interpreter.
10. **Given** the SLP is editing a template, **When** they remove an interpreter and save, **Then** the template no longer includes it.
11. **Given** the SLP is editing a template, **When** they move an interpreter up or down and save, **Then** the interpreters are kept in the new order.
12. **Given** a student has this template as their Current Template, **When** the SLP saves edits to the template and confirms, **Then** the student still has this template as their Current Template, and their next imported sheets are read with the edited version.
13. **Given** students `JA` and `MK` use the template, **When** the SLP saves edits, **Then** they are asked to confirm, and the prompt says the change applies to `JA` and `MK`. If they decline, nothing is saved and they stay in edit mode with their changes intact.
14. **Given** no student uses the template, **When** the SLP saves valid edits, **Then** the template is saved without a confirmation prompt.
15. **Given** the SLP is editing a template, **When** they clear the name or remove every interpreter and try to save, **Then** nothing is saved and they are told what is missing. These are the same rules that apply when creating a template.
16. **Given** the SLP is editing a template, **When** they give two interpreters the same non-blank title and try to save, **Then** nothing is saved and they are told which title is a duplicate.

---

### User Story 3 - Leave an edit without saving (Priority: P3)

The SLP starts editing a template, then decides not to keep the changes. They cancel, and the window returns to view mode showing the template as it was saved. If they have made changes, they are asked to confirm before those changes are thrown away.

**Why this priority**: A template change affects every student who uses that template. A careless click must not overwrite it.

**Independent Test**: Edit a template's name and interpreters, cancel, confirm the discard, and check that view mode and a relaunch both show the original template.

**Acceptance Scenarios**:

1. **Given** the SLP has changed a template in edit mode, **When** they cancel or close the window, **Then** they are asked to confirm discarding the changes.
2. **Given** the discard confirmation is showing, **When** the SLP declines it, **Then** they stay in edit mode with their changes intact.
3. **Given** the discard confirmation is showing, **When** the SLP accepts it, **Then** the saved template is unchanged. After Cancel, the window returns to view mode showing the saved values. After closing, the window closes.
4. **Given** the SLP is in edit mode but changed nothing, **When** they cancel, **Then** the window returns to view mode without asking for confirmation.

---

### User Story 4 - Delete a template that students use (Priority: P3)

The SLP deletes a template from the management list. If students use it, the confirmation names them by Student Key and warns that they will need a new template. Once the SLP confirms, the template is gone and those students show as having no Current Template, so the SLP can see in the Students window who needs a new one.

**Why this priority**: The usage counts make it possible to tell when a delete affects students. Without this, a delete leaves students pointing at a template that no longer exists, and their next sheets fail to import with no warning beforehand.

**Independent Test**: Assign a template to students `JA` and `MK`, delete it from the management window, and check that the confirmation names both. After confirming, check that the template is gone and that the Students window shows both students with no Current Template.

**Acceptance Scenarios**:

1. **Given** students `JA` and `MK` use a template, **When** the SLP chooses to delete it, **Then** the confirmation names `JA` and `MK` and says they will need a new template.
2. **Given** that confirmation is showing, **When** the SLP confirms, **Then** the template is deleted, `JA` and `MK` have no Current Template, and both changes are still there after a relaunch.
3. **Given** that confirmation is showing, **When** the SLP declines, **Then** neither the template nor any student is changed.
4. **Given** no student uses a template, **When** the SLP chooses to delete it, **Then** the plain delete confirmation is shown, and no student is changed.

---

### Edge Cases

- **Template deleted or missing when opened**: If the selected template can no longer be found when its Template Details window is opened (for example, the templates file was changed outside the application), the SLP is told it no longer exists and the management list is refreshed.
- **Saving a template that has disappeared**: If the template no longer exists when the SLP saves an edit, nothing is written. The SLP is told the template was not found, and the list is refreshed.
- **Templates file cannot be written**: If saving fails, the SLP sees an error that says the change was not saved. The window stays in edit mode so they can try again or cancel.
- **Saved interpreter whose type has no configuration form**: If a template holds an interpreter whose type the application can load but edit mode offers no form for, view mode still shows its type, title, and saved configuration. Edit mode keeps that interpreter unchanged unless the SLP removes it.
- **Renaming to an existing template name**: This is allowed, because template names are not required to be unique today. The SLP tells same-named templates apart by their ID in the list.
- **Student list cannot be read**: If the saved students cannot be loaded, the template list shows the usage count as unknown, not 0. The Template Details window says which students use the template could not be determined. Saving an edit still asks for confirmation and says it could not be checked which students use the template.
- **Student assigned during edit mode**: The usage check before saving uses the students as saved at the moment the SLP presses save, not as they were when edit mode began.
- **Deleting when the students cannot be read**: The delete confirmation says it could not be checked which students use the template. If the SLP confirms, the template is deleted, and no student record is changed.
- **Clearing students fails**: If a student's Current Template cannot be cleared, the template is not deleted. The SLP is told the delete did not happen and why.
- **Template deletion fails after students were cleared**: The students stay cleared, the SLP is told the template could not be deleted, and the list is refreshed. The students then need a template anyway, which is safe.
- **Long configurations**: A template with many interpreters, or an interpreter with many columns or fields, stays readable. The Template Details window scrolls instead of cutting content off.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The template management window MUST let the SLP open the selected template's Template Details window in view mode, both by a View button and by double-clicking the template in the list.
- **FR-002**: In view mode, the Template Details window MUST show the template's name, its ID, its description (shown as empty if it has none), and every interpreter in saved order with its type, title, and full configuration.
- **FR-003**: View mode MUST NOT allow changes to the template. It MUST offer an Edit action that switches the same window to edit mode, without opening another window.
- **FR-004**: The management window's Edit button MUST open the selected template's Template Details window directly in edit mode.
- **FR-004a**: Edit mode MUST use the same layout as view mode, with the fields made editable and Save and Cancel offered. A successful Save, or a Cancel, MUST return the window to view mode showing the saved template.
- **FR-005**: Edit mode MUST start with the template's current saved name, description, and interpreters already filled in.
- **FR-005a**: Creating a template MUST stay in the separate Create window. The Template Details window opens only for templates that have already been saved.
- **FR-006**: Edit mode MUST let the SLP rename the template, change its description, add an interpreter of any available type, remove an interpreter, change an existing interpreter's title and configuration, and reorder interpreters.
- **FR-006a**: To change an existing interpreter, the SLP selects it in edit mode. Its type's configuration form then opens filled in with its saved title and configuration. Applying the form replaces that interpreter in place: it keeps its ID and its position in the list. The SLP cannot change an existing interpreter's type. To use a different type, they remove the interpreter and add a new one.
- **FR-006b**: Every interpreter type offered in edit mode MUST be able to show its configuration form filled in with an existing interpreter's saved values.
- **FR-006c**: Creating a template MUST save the description entered in the Create window. The description is optional free text and may be empty.
- **FR-006d**: Templates saved before descriptions existed MUST still load. They show an empty description until the SLP adds one.
- **FR-006e**: Unapplied changes in an interpreter's form MUST be applied automatically when the SLP selects a different interpreter or saves the template. They MUST go through the same checks as applying by hand. If those checks fail, the selection MUST NOT change, nothing MUST be saved, and the SLP MUST be told what to fix.
- **FR-006f**: The interpreter form MUST offer a Cancel that discards its unapplied changes. The form then goes back to the interpreter's values from before the change, or is emptied when adding a new interpreter. This Cancel MUST NOT discard other edits to the template.
- **FR-007**: Saving an edit MUST keep the template's ID, so every student whose Current Template is this template keeps referring to it.
- **FR-008**: Saving an edit MUST keep each interpreter's ID, both for interpreters that were changed and for those left alone. New interpreters MUST get new IDs that do not match any existing interpreter in the template.
- **FR-009**: Edit mode MUST apply the same validation as the Create window, and both MUST always enforce the same rules: a name is required, at least one interpreter is required, and no two interpreters in the template may share a non-blank title. Titles are compared after trimming leading and trailing spaces, with exact letter case. Any number of interpreters may have a blank title. When validation fails, the window MUST name the problem and save nothing.
- **FR-010**: After a successful save, the management list MUST show the change without the SLP needing to reopen the window, and the change MUST still be there after a relaunch.
- **FR-010a**: The template list MUST show, for each template, how many students have it as their Current Template. The count MUST be correct when the window opens and after any template is created, edited, or deleted from it.
- **FR-010b**: The Template Details window MUST list, in both modes, the Student Key of every student whose Current Template is the template shown, or say that no students use it. It MUST NOT show any other student information.
- **FR-010c**: When the SLP saves a valid edit to a template that one or more students use, the window MUST first ask the SLP to confirm, naming those students by Student Key. Declining MUST save nothing and keep the window in edit mode with the changes intact. If no students use the template, the save MUST go ahead without this prompt.
- **FR-010d**: If the students cannot be read, the template list MUST show the usage count as unknown, not 0, and the Template Details window MUST say that usage could not be determined. Saving MUST still ask for confirmation and say that usage could not be checked.
- **FR-010e**: When the SLP deletes a template that one or more students use, the delete confirmation MUST name those students by Student Key and say they will need a new template. If no students use it, the plain confirmation is shown.
- **FR-010f**: When the SLP confirms deleting a template in use, every student whose Current Template is that template MUST have their Current Template cleared first, and then the template MUST be deleted. If clearing fails, the template MUST NOT be deleted. Declining MUST change nothing.
- **FR-010g**: Clearing a student's Current Template MUST NOT change any other part of the student record.
- **FR-011**: Cancelling edit mode, or closing the window while in edit mode, after making changes MUST ask the SLP to confirm before discarding them. Unapplied interpreter form changes count as changes. Cancelling with no changes MUST return to view mode without asking. Closing in view mode MUST NOT ask.
- **FR-012**: An edited template MUST stay loadable by every part of the application that loads templates today, including the Students window and the Import window.
- **FR-013**: If the template cannot be found when the Template Details window is opened, or when an edit is saved, the SLP MUST be told it was not found, nothing MUST be written, and the management list MUST be refreshed.
- **FR-014**: If a save fails, the SLP MUST be told the change was not saved, and the window MUST stay in edit mode with their changes intact.
- **FR-015**: An interpreter whose type the application can load but that has no configuration form in edit mode MUST still be shown in view mode, and MUST be kept unchanged on save unless the SLP removes it.

### Key Entities

- **Data Sheet Template**: A named, saved set of section interpreters that describes one sheet layout. It has an ID that never changes, a name, an optional free-text description, and an ordered list of interpreters. Students refer to it by ID as their Current Template. Its **usage** is the set of Students whose Current Template is this template, shown as a count in the list, as Student Keys in the Template Details window, and as Student Keys in the delete confirmation. Deleting a template clears the Current Template of every student in its usage.
- **Section Interpreter (as configured in a template)**: One part of a template. It has an ID that is stable within the template, a type (Table, Running Tally, or Simple Form today), a title, which may be blank (non-blank titles are unique within the template), and type-specific configuration such as columns, tally characters, or field names.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The SLP can see the full contents of any saved template, including every interpreter's type, title, and configuration, within 2 interactions from the management window.
- **SC-002**: The SLP can rename a template or change one interpreter's configuration and save it in under 1 minute, without deleting and re-creating the template.
- **SC-002a**: The SLP can tell which students an edit will affect before it is saved, every time a template in use is edited.
- **SC-002b**: After a template is deleted from the management window while the student records can be read, 0 students have a Current Template that points to it. When the records cannot be read, the delete confirmation says that no student records will be changed.
- **SC-003**: After a template is edited, 100% of students who had it as their Current Template still have it, with no reassignment needed.
- **SC-004**: 100% of edited templates load and interpret sheets in the application after a relaunch.
- **SC-005**: No change to a template is saved unless the SLP explicitly saves. Cancelling, closing, or a failed validation leaves the saved template exactly as it was.

## Assumptions

- Only the SLP uses the application, so there are no permissions and no concurrent editors to consider.
- An edit takes effect for sheets imported after it is saved. Sheets that were already imported and interpreted are not re-interpreted.
- Edit mode offers the same interpreter types, with the same configuration forms, as the Create window does. The Create window and the Template Details window stay separate windows, but both are built around the same template form, and the rules they share, starting with validation, are defined once. The two cannot drift apart.
- Template names stay non-unique, matching current creation behavior. Adding a uniqueness rule is out of scope.
- A description is optional and needs no validation. Both the Create window and edit mode show a hint next to the Description field: "Describe the sheet layout. Don't include student names." Like everything else stored about templates, it should describe a sheet layout, not identify a student. Student Keys are fine; full names are not.
- The discard confirmation is specific to templates. The Students window's silent discard of unsaved changes, decided in feature 002, is intentionally left as it is.
- A template holding an interpreter type the application cannot load at all (for example, from a newer version of the app) still fails to load, as it does today. Handling such templates is out of scope.
- Duplicating a template, version history, and undoing a saved edit are out of scope.
- Students are identified in usage displays only by Student Key, in line with the student data privacy rule.
- A student whose Current Template refers to a template that no longer exists, for example because the templates file was changed outside the application, is not counted toward any template. This feature does not clean up those older references.
- Templates saved before this feature continue to load unchanged in the Template Details window, in line with the existing rule that serialized templates must stay loadable.
