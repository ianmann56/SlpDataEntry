# Feature Specification: Students

**Feature Branch**: `002-configure-students`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "Add a new window called "Configure Students". It will let the user create/view/update/remove records for each student which contains the configs for that student for the application. There will be more configurations later so don't narrow design and architecture for this page down to just these fields. A student consists of the following: First Name; Last Name; Initial (this is the key that lets it match student data sheets to the student); Current Template (The template from the template store which will be used to interpret this student's data sheets)"

## Clarifications

### Session 2026-09-30

- Q: The request lists first and last name, but Principle I (Student Data Privacy) forbids storing a student's full name. Which should change? → A: Drop the names. A student is identified only by their Student Key. No constitution change.
- Q: How should the setup path offer both the Students window and template management? → A: The home screen's setup button opens a **Setup** menu with *Data Sheet Templates* and *Students*. Back from either window returns to the Setup menu, and Back from the menu returns home.
- Q: What should the student configuration window be called? → A: **Students**, not "Configure Students", because it sits inside the Setup menu already. The Setup menu choice uses the same label.
- Q: Which characters and how many may a Student Key have? → A: Any text the SLP types, up to 5 characters after leading and trailing spaces are trimmed.
- Q: Where should the student records file live, and how does the application find it at launch? → A: A second, required launch argument gives the student records file path, after the template file path.
- Q: Since the Student Key is what identifies a student, should the SLP be able to change an existing student's key? → A: Yes, but only after confirming a warning. The warning says the student's identifying key in the system is changing, and that new data sheets for the student must use the new key.
- Q: If the saved student list can't be loaded when the SLP opens the Students window, because the file is damaged, what should happen? → A: Offer to start fresh. After the SLP confirms, keep a backup copy of the damaged file and open an empty list.
- Q: If the SLP has typed changes into a student they're adding or editing, then presses Back or closes the window before saving, should the app warn them before throwing those changes away? → A: No. Unsaved changes are discarded silently. Only an explicit Save keeps changes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add a student and see the list (Priority: P1)

The SLP opens the **Students** window and sees a list of the students they have already set up. They add a new student by entering their Student Key (the initials written on the student's data sheets) and choosing the Data Sheet Template used to interpret that student's sheets. The new student appears in the list and is still there the next time the SLP opens the application.

**Why this priority**: Nothing else in this feature works without student records existing.

**Independent Test**: Open the Students window with no students saved, add one student with all fields filled in, confirm they appear in the list, then close and relaunch the application and confirm the student is still listed with the same details.

**Acceptance Scenarios**:

1. **Given** no students are saved, **When** the SLP opens the Students window, **Then** an empty student list is shown with a way to add a student.
2. **Given** the Students window is open, **When** the SLP adds a student with a Student Key and a Current Template, **Then** the student appears in the list showing their Student Key and Current Template.
3. **Given** a student was added, **When** the SLP closes and relaunches the application and opens the Students window, **Then** the student is listed with the same details.
4. **Given** the SLP is adding a student, **When** they try to save without a Student Key, **Then** the student is not saved and the SLP is told the Student Key is required.
5. **Given** a student with Student Key `JA` exists, **When** the SLP tries to add another student with Student Key `JA` (or `ja`), **Then** the student is not saved and the SLP is told that key is already in use.

---

### User Story 2 - View and update a student (Priority: P2)

The SLP picks a student from the list to see their full configuration and changes it, for example to switch them to a different Data Sheet Template when the student's sheet layout changes, or to correct a mistyped Student Key.

**Why this priority**: Templates change over a school year as goals change. Without editing, the SLP would have to delete and re-create a student for every change.

**Independent Test**: With one student saved, open them, change their Current Template and Student Key, save, and confirm the list and a relaunch both show the new values.

**Acceptance Scenarios**:

1. **Given** a student is listed, **When** the SLP opens that student, **Then** all of the student's saved configuration is shown and can be edited.
2. **Given** the SLP is editing a student, **When** they change the Current Template and save, **Then** the list shows the new template, and it is still the new template after a relaunch.
3. **Given** the SLP is editing a student, **When** they change the Student Key to one already used by a different student, **Then** the change is not saved and the SLP is told that key is already in use.
4. **Given** the SLP is editing a student and has changed their Student Key to an unused key, **When** they save, **Then** they are warned that the student's identifying key in the system is changing from the old key to the new one, and that new data sheets for this student must use the new key. The change is saved only if they confirm.
5. **Given** the key-change warning is showing, **When** the SLP declines, **Then** nothing is saved and the student keeps their old Student Key.
6. **Given** the SLP is editing a student, **When** they cancel instead of saving, **Then** the student's saved configuration is unchanged.

---

### User Story 3 - Remove a student (Priority: P3)

The SLP removes a student who no longer receives services, so the list only shows current students.

**Why this priority**: Useful housekeeping, but the list still works if old students stay in it.

**Independent Test**: With two students saved, remove one, confirm after a prompt, and confirm only the other remains, including after a relaunch.

**Acceptance Scenarios**:

1. **Given** a student is listed, **When** the SLP chooses to remove them, **Then** the SLP is asked to confirm before anything is removed.
2. **Given** the SLP is asked to confirm a removal, **When** they confirm, **Then** the student is removed from the list and stays removed after a relaunch.
3. **Given** the SLP is asked to confirm a removal, **When** they decline, **Then** the student remains unchanged.

---

### User Story 4 - Reach the Students window from the Setup menu (Priority: P1)

The SLP picks the setup and configuration choice on the home screen and lands on a **Setup** menu. From there they open either the Students window or Data Sheet Template management, and Back takes them to the Setup menu again.

**Why this priority**: The window is unusable if the SLP cannot get to it. It shares priority with User Story 1 because the two together are the smallest useful slice. The Setup menu also gives later setup areas a place to go without crowding the home screen.

**Independent Test**: From a fresh launch, open the Setup menu, open the Students window, press Back to return to the Setup menu, open Data Sheet Template management, press Back twice, and confirm the home screen is showing.

**Acceptance Scenarios**:

1. **Given** the home screen is showing, **When** the SLP picks **Manage Setup & Configuration**, **Then** the home screen is hidden and the Setup menu appears with exactly two choices: **Data Sheet Templates** and **Students**, plus a Back button.
2. **Given** the Setup menu is showing, **When** the SLP picks **Students**, **Then** the Setup menu is hidden and the Students window opens.
3. **Given** the Students window is open, **When** the SLP presses Back, **Then** the Students window closes and the Setup menu is shown again.
4. **Given** the Setup menu is showing, **When** the SLP picks Data Sheet Templates, **Then** template management opens as it does today, and its Back button returns to the Setup menu.
5. **Given** the Setup menu is showing, **When** the SLP presses Back, **Then** the home screen is shown again.
6. **Given** the Setup menu or the Students window is open, **When** the SLP closes that window from its title bar, **Then** the application exits, as it does for the other path windows.

---

### Edge Cases

- **No templates exist yet**: the SLP can still add a student. Their Current Template is left as "none selected", and the list shows that clearly.
- **A student's Current Template is later deleted** in template management: the student keeps their other configuration, and the Students window shows their template as missing so the SLP can pick a new one. Deleting templates is not blocked.
- **Student Key formatting**: leading and trailing spaces are trimmed, and keys are compared without regard to letter case, so `ja`, `JA`, and ` JA ` are the same key. A key longer than 5 characters after trimming is rejected with a message giving the limit, and a key that is only spaces counts as missing.
- **A Student Key edit that changes only letter case or surrounding spaces** (e.g. `ja` → `JA`): it is still the same key, so it is saved without the key-change warning.
- **Back or close with unsaved changes**: if the SLP presses Back or closes a window while adding or editing a student, the unsaved changes are discarded without a prompt. Saved students are unaffected.
- **The two launch arguments name the same file**: the application refuses to start and says the template file and student records file must be different files.
- **The student records file does not exist yet**: the Students window opens with an empty list, and the file is created on the first save.
- **The student records file cannot be read** (for example, it is damaged): see FR-020. The SLP is offered a fresh start that keeps a backup of the damaged file, or can decline and stay on the Setup menu with the file untouched.
- **Records saved before a new configuration field is added**: they still load, and the new field shows its default for those students.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST provide a window titled **Students** (formerly referred to as "Configure Students"). It is opened from the Setup menu, so its name does not repeat "configure" or "setup".
- **FR-002**: The Students window MUST list every saved student, showing at least their Student Key and Current Template.
- **FR-003**: The SLP MUST be able to add a student by entering a Student Key and choosing a Current Template. A student record MUST NOT hold the student's name or any other direct identifier beyond the Student Key (Principle I).
- **FR-004**: The SLP MUST be able to open any listed student to view and edit all of their configuration, including their Student Key.
- **FR-004a**: Saving a changed Student Key MUST first show a warning that the student's identifying key in the system is changing from the old key to the new one, and that new data sheets for the student must use the new key. The change MUST be saved only if the SLP confirms. Declining MUST save nothing. Saving without changing the Student Key MUST NOT show this warning.
- **FR-004b**: Student changes MUST be kept only when the SLP explicitly saves. Pressing Back, cancelling, or closing a window before saving MUST discard the unsaved changes without a prompt.
- **FR-005**: The SLP MUST be able to remove a student, and MUST be asked to confirm before the student is removed.
- **FR-006**: The Student Key MUST be required. Leading and trailing spaces MUST be trimmed, and the trimmed key MUST be 1 to 5 characters long. Any characters are allowed. It MUST be unique among all students, ignoring letter case.
- **FR-007**: The Current Template MUST be chosen from the Data Sheet Templates in the Template Store, or left as "none selected". The SLP MUST NOT be able to type in a template that does not exist.
- **FR-008**: When a student's Current Template no longer exists in the Template Store, the Students window MUST show it as missing rather than hiding the student or failing to open.
- **FR-009**: Student records MUST be saved locally on the SLP's computer, and MUST still be there after the application is closed and relaunched.
- **FR-010**: Saved student records MUST stay loadable when new configuration fields are added in later features. A field missing from an older record MUST take that field's default value.
- **FR-011**: The window's layout MUST group a student's configuration so that later features can add configuration fields without changing how the SLP finds, adds, opens, or removes students.
- **FR-012**: The home screen's setup choice MUST be labeled **Manage Setup & Configuration** and MUST open a **Setup** menu instead of opening template management directly.
- **FR-013**: The Setup menu MUST offer exactly two choices, **Data Sheet Templates** (the existing template management window) and **Students**, and a Back button that returns to the home screen.
- **FR-014**: The Students window and template management, when opened from the Setup menu, MUST each have a Back button that returns to the Setup menu.
- **FR-015**: While the Setup menu, the Students window, or template management is open, only that one screen MUST be on display. The home screen and Setup menu are hidden while a screen opened from them is open.
- **FR-016**: Closing the Setup menu or the Students window from its title bar MUST exit the application, matching the other path windows.
- **FR-017**: Opening the Setup menu or the Students window, and managing students, MUST NOT contact any external service or read any external-service credentials.
- **FR-018**: The Setup menu and the Students window MUST follow the system light/dark theme, matching the existing windows.
- **FR-019**: The launch command MUST take the student records file path as a second, required argument after the template file path. It MUST be validated the same way as the template file path. If it is missing or invalid, the application MUST print a usage message naming both arguments and exit before showing any window.
- **FR-020**: If the student records file exists but cannot be read when the Students window is opened, the SLP MUST be told the records could not be loaded and offered to start with an empty student list. If they confirm, the damaged file MUST first be kept as a backup copy beside it, under a name that does not overwrite any earlier backup, and the Students window then opens with an empty list. If they decline, the Students window MUST NOT open, the SLP stays on the Setup menu, and the file MUST be left untouched.

### Key Entities

- **Student**: One child the SLP works with, as configured for this application. It holds the student's Student Key and their Current Template, and never their name. It is designed to hold more configuration fields in later features. Identified by its Student Key, which is unique among all students and can be changed only through the key-change warning (FR-004a).
- **Student Key**: The short identifier (usually initials, e.g. `JA`) written on the student's data sheets. It is what lets a data sheet be matched to its student. The user's description calls it "Initial". This spec uses the glossary term.
- **Current Template**: A reference from a student to one Data Sheet Template in the Template Store. It may be empty, or refer to a template that has since been deleted.
- **Student Store**: The local saved collection of Student records, kept separately from the Template Store.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The SLP can add a new student, with all fields filled in, in under 1 minute from opening the Students window.
- **SC-002**: The SLP can switch a student to a different Data Sheet Template in 3 actions or fewer after opening the Students window.
- **SC-003**: 100% of students saved in one session are listed, with the same details, after the application is relaunched.
- **SC-004**: No two saved students can ever share a Student Key, in any letter case.
- **SC-005**: The SLP reaches the Students window, or template management, from a fresh launch in 2 choices.
- **SC-006**: Student records saved by this feature still load, unchanged, after a later feature adds a new student configuration field.

## Assumptions

- The Setup menu changes feature 001's navigation. Template management now takes 2 choices from home instead of 1, superseding feature 001's SC-001, and the home screen's second label changes from "Manage Setup & Data Sheet Templates" to "Manage Setup & Configuration". The home screen still has exactly two choices.
- The SLP has a small caseload, in the tens of students, so a single scrollable list without search or filtering is enough.
- The request's First Name and Last Name fields are left out, per the first clarification. Future configuration fields MUST also not add direct identifiers without a constitution amendment.
- "Initial" in the request is the glossary's **Student Key**, so this feature uses that term in the UI and specs (Principle II).
- A student has at most one Current Template at a time. This feature keeps no history of past templates.
- The Current Template is optional, so the SLP can add a student before any template exists.
- Student records are stored in their own file, separate from Data Sheet Templates. The SLP gives its path as the second launch argument (see Clarifications). This changes feature 001's launch contract, which took only the template file path.
- Only the template management window's existing behavior is kept as is. Deleting a template is not blocked by students that use it (see Edge Cases).
- No real student data goes into the repository. Validation uses placeholder Student Keys (e.g. `JA`) only.
