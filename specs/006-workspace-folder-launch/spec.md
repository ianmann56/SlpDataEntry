# Feature Specification: Workspace Folder Launch

**Feature Branch**: `006-workspace-folder-launch`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "As a user I want to run the program with a workspace (a folder) instead of the students and templates file separately so that I can run the program eaiser. If the folder: contains a studens.json and templates.json file => then those are the students and templates files for the program. contains only a templates or students file => then tell the user that the other configurations could not be retrieved. Ask them if they'd like to start fresh with those configurations or cancel to go find the file and put it in the directory. contains neither of the templates or students file => then tell the user that it appears that this workspace has not yet been initialized and ask if they would like to start a new workspace here. This program should no longer have the ability to specify the students and templates file explicitly. Only the directory should be specified now."

## Clarifications

### Session 2026-10-05

- Q: How should the SLP give the program its Workspace folder at launch? → A: The folder path is a command-line argument. With no argument, the program opens a folder picker.
- Q: Should the Google sign-in files (the client secret and the cached sign-in token) also move into the Workspace? → A: No. Both stay as they are and are out of scope for this feature.
- Q: When only one of the two files is found, should the SLP be able to start fresh for the missing one? → A: No. Starting fresh would restart Template numbering, so a new Template could take the number of a lost one that Students still point to. The application names the missing file, tells the SLP to restore it next to the other file in the same folder, and offers only a Close button that exits. A folder holding exactly one of the two files can never be opened.
- Q: If the folder holds neither `students.json` nor `templates.json`, should the program still offer to set up a new Workspace there? → A: Yes. The program says the Workspace is not set up yet and asks whether to start one. Yes creates both files empty, and No closes the program without creating anything.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Launch with an existing Workspace (Priority: P1)

The SLP launches the application and gives it one folder, the Workspace, instead of two separate file paths. The Workspace already holds the student records file (`students.json`) and the templates file (`templates.json`). The application uses both and opens the home screen with no extra questions.

**Why this priority**: This is the everyday launch. It replaces the two-path launch, so it must work before anything else in this feature matters.

**Independent Test**: Put a `students.json` and a `templates.json` in a folder, launch with that folder, and confirm the home screen opens and the Students and Templates shown are the ones in those files.

**Acceptance Scenarios**:

1. **Given** a folder holding both `students.json` and `templates.json`, **When** the SLP launches the application with that folder, **Then** the home screen opens with no prompt, and template management and student setup show the Templates and Students from those files.
2. **Given** the application was launched with a Workspace, **When** the SLP saves a Template or a Student, **Then** the change is written to the matching file in that Workspace.
3. **Given** the SLP launches with two file paths the old way, **When** the application starts, **Then** it shows a usage message that asks for one Workspace folder and does not open.

---

### User Story 2 - Start a new Workspace in an empty folder (Priority: P2)

The SLP launches the application with a folder that holds neither file. The application says the Workspace does not appear to be set up yet and asks whether to start a new Workspace there. If the SLP agrees, the application creates an empty student records file and an empty templates file in the folder and opens the home screen. If the SLP declines, the application closes and leaves the folder untouched.

**Why this priority**: The SLP needs this to set up the tool for the first time, or a new school year. It is used less often than an everyday launch.

**Independent Test**: Launch with an empty folder, accept the prompt, and confirm both files now exist with no Students and no Templates, and the home screen opens. Repeat with a fresh empty folder, decline, and confirm the folder is still empty and the application closed.

**Acceptance Scenarios**:

1. **Given** a folder holding neither `students.json` nor `templates.json`, **When** the SLP launches with it, **Then** the application says the Workspace does not appear to be set up yet and asks whether to start a new Workspace in that folder.
2. **Given** that prompt is showing, **When** the SLP chooses to start a new Workspace, **Then** an empty `students.json` and an empty `templates.json` are created in the folder and the home screen opens.
3. **Given** that prompt is showing, **When** the SLP declines, **Then** the application closes and no file is created in the folder.
4. **Given** the SLP started a new Workspace in a folder, **When** they launch again with the same folder, **Then** the application opens without asking anything (User Story 1).

---

### User Story 3 - Stop at a Workspace that is missing one file (Priority: P3)

The SLP launches with a folder that holds only one of the two files, for example after copying only part of a Workspace to a new computer. The application names the missing file and tells the SLP to restore it next to the other file in the same folder, then launch again. The only choice is Close, which exits the application. The application never opens a Workspace that is missing one file, so Students are never left pointing at Templates that were lost.

**Why this priority**: This is an error path. It protects the SLP from losing Students or Templates without noticing, but it only comes up when a Workspace is incomplete.

**Independent Test**: Launch with a folder holding only `templates.json`. Confirm the message names the missing `students.json`, offers only Close, and that Close exits without creating or changing any file. Repeat with only `students.json` present.

**Acceptance Scenarios**:

1. **Given** a folder holding `templates.json` but not `students.json`, **When** the SLP launches with it, **Then** the application says `students.json` (the student records) is missing from the Workspace and tells the SLP to restore it next to `templates.json` in the same folder.
2. **Given** a folder holding `students.json` but not `templates.json`, **When** the SLP launches with it, **Then** the application says `templates.json` (the Templates) is missing from the Workspace and tells the SLP to restore it next to `students.json` in the same folder.
3. **Given** either of those messages is showing, **When** the SLP looks at it, **Then** the only choice offered is Close. No choice to start fresh or continue is offered.
4. **Given** either of those messages is showing, **When** the SLP presses Close or closes the message, **Then** the application exits, no file is created, changed, or deleted, and the home screen never opens.
5. **Given** the SLP restored the missing file into the folder, **When** they launch again with the same folder, **Then** the application opens without asking anything (User Story 1).

---

### Edge Cases

- No folder is given at launch: the application opens a folder picker. The chosen folder is then opened as a Workspace the same way as a folder given at launch. If the SLP cancels the picker, the application closes without creating anything.
- The path given does not exist, or is a file rather than a folder: the application shows a clear error naming the path, and does not open or create anything.
- The folder exists but the application cannot create files in it (for example, it is read-only) when the SLP accepts starting a new Workspace: the application shows a clear error naming the file it could not create, and closes without opening the home screen.
- The folder holds other files besides the two Workspace files: they are ignored and left untouched.
- A file in the folder has a near-miss name (for example `Students.json` on a case-sensitive system, or `students.json.bak`): it does not count as the Workspace file, and the folder is treated as missing that file.
- `students.json` or `templates.json` exists but cannot be read (for example, it is not valid JSON): the application handles it the same way it does today for that file. This feature does not overwrite or replace a file that already exists.
- A path in the Workspace named `students.json` or `templates.json` is a folder, not a file: it is treated as an error naming that path, not as a missing file, so the SLP is never told to restore a file that is actually there in the wrong form.
- The folder path contains spaces or non-ASCII characters: the launch works the same as any other path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST take at most one launch argument: the path to a Workspace folder. When no argument is given, the application MUST open a folder picker for the SLP to choose the Workspace folder. Cancelling the picker MUST close the application without creating anything.
- **FR-002**: The application MUST NOT accept separate student records or templates file paths at launch. Launching the old way MUST show the usage message and not open.
- **FR-003**: The student records file MUST be the file named `students.json` directly inside the Workspace folder, and the templates file MUST be the file named `templates.json` directly inside it.
- **FR-004**: When both files are present, the application MUST open the home screen without any prompt and use those files for all Student and Template reads and writes for the whole session.
- **FR-005**: When neither file is present, the application MUST say that the Workspace does not appear to be set up yet and ask whether to start a new Workspace in that folder, before showing the home screen.
- **FR-006**: If the SLP accepts starting a new Workspace, the application MUST create both files with no Students and no Templates, then open the home screen.
- **FR-007**: When exactly one file is present, the application MUST show a message that names the missing file and what it holds (student records or Templates), and tells the SLP to restore it next to the other file in the same folder and launch again.
- **FR-008**: That message MUST offer only a Close choice. Pressing Close, or closing the message, MUST exit the application without opening the home screen. The application MUST NOT offer any way to start fresh, create the missing file, or continue with only one file.
- **FR-009**: If the SLP declines to start a new Workspace, or the application stops at a missing file, it MUST close without creating, changing, or deleting any file.
- **FR-010**: Closing the new-Workspace prompt without choosing MUST count as declining.
- **FR-011**: The application MUST NOT overwrite or replace an existing `students.json` or `templates.json` as part of opening a Workspace.
- **FR-012**: If the launch path does not exist, or is not a folder, the application MUST show a clear message naming the problem and the path, and MUST NOT open or create anything.
- **FR-013**: If a file for a new Workspace cannot be created, the application MUST show a clear error naming that file and close without opening the home screen.
- **FR-014**: Workspace prompts MUST follow the system light/dark theme, matching the existing windows.
- **FR-015**: Opening a Workspace, including every prompt, MUST NOT contact any external service or read any external-service credentials.
- **FR-016**: Workspace prompts and messages MUST identify files and folders by path only and MUST NOT show any Student Key or other student information.
- **FR-017**: "Workspace" MUST be added to the domain glossary in the same change, and the glossary entries for the Student Store and Template Store MUST say their files come from the Workspace rather than from separate launch arguments.

### Key Entities

- **Workspace**: A folder the SLP chooses at launch that holds all of the application's local configuration for one setup. It currently holds the student records file and the templates file under fixed names. A Workspace is complete when both files are present, partial when only one is, and not set up when neither is. Only a complete Workspace can be opened. A not-set-up folder can become one by starting a new Workspace. A partial Workspace can only be fixed by restoring the missing file.
- **Student records file** (`students.json`): The Student Store's file inside the Workspace. Holds Students, identified by Student Key.
- **Templates file** (`templates.json`): The Template Store's file inside the Workspace. Holds Data Sheet Templates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The SLP launches the application by naming 1 folder instead of 2 files, or by picking 1 folder when no argument is given.
- **SC-002**: From a complete Workspace, the home screen opens with 0 prompts.
- **SC-003**: From an empty folder, the SLP reaches the home screen with a working new Workspace in 1 confirmation.
- **SC-004**: In 100% of launches with a partial or empty folder, the SLP is told what is missing before any file is created. In 100% of launches with a partial Workspace, the folder is left exactly as it was and the home screen never opens.
- **SC-005**: No launch ever replaces or empties an existing `students.json` or `templates.json`.
- **SC-006**: An SLP launching with a partial Workspace for the first time can say, from the message alone, which file is missing and that it goes next to the other file in the same folder.

## Assumptions

- The Workspace folder is given as a command-line argument, as the two file paths were. When it is left out, a folder picker opens instead. The application does not remember the last Workspace between launches.
- The file names are exactly `students.json` and `templates.json`, in lower case, directly in the Workspace folder (not in subfolders). The description's "studens.json" is read as a typo for `students.json`.
- Accepting a new Workspace creates both files immediately, before the home screen opens, so the next launch sees a complete Workspace.
- The application does not create the Workspace folder itself. The SLP chooses or makes the folder first.
- Prompts appear as dialogs in the desktop application, before the home screen, rather than as terminal questions.
- How each store reads, writes, backs up, and reports an unreadable file stays the same. Only where its file comes from changes.
- The Google client secret (still found through its environment variable), the cached Google sign-in token, and the Therapy Data Folder in Google Drive stay where they are today. Moving them into the Workspace is out of scope for this feature and may be its own feature later.
- Existing users move to a Workspace by putting their current two files in one folder under the fixed names. No automatic migration is provided.
- The Workspace holds student records, so it falls under Principle I (Student Data Privacy). Real Workspaces MUST NOT be committed to the repository.
