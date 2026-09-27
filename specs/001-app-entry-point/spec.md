# Feature Specification: Application Entry Point

**Feature Branch**: `001-app-entry-point`

**Created**: 2026-09-27

**Status**: Draft

**Input**: User description: "Make a single entry point to the application with 2 paths: 1 to start the process of interpreting and importing session data and another to start the process of managing the setup and configuration of the application. Don't implement the actual features of the paths. Just get it so we can pick the paths. For the import/interpret path, just dead end here and add a back button to go back to the root. For the management path, just have it pull up the template management window."

## Clarifications

### Session 2026-09-27

- Q: When the SLP closes the template management window, should the app go back to the home screen or exit? → A: Closing the window exits the application. The window also gets a Back button that returns to the home screen.
- Q: While the SLP is in one of the paths, should the home screen stay visible? → A: No. The home screen is hidden while a path is open and shown again on Back.
- Q: What should happen to the existing `program_manage.py` and `program_interpret.py` launch scripts? → A: Delete `program_manage.py`. Keep `program_interpret.py` as a temporary developer-only script, recorded as a constitution deviation in the plan.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choose a path from one home screen (Priority: P1)

The SLP launches the application once and lands on a single home screen. The screen offers two clearly labeled choices: one to import and interpret Student Data Sheets from therapy sessions, and one to manage the application's setup and configuration. The SLP no longer needs to know which of several separate programs to start.

**Why this priority**: The home screen is the foundation both paths hang from. Without it, neither of the other stories can be reached.

**Independent Test**: Launch the application and confirm the home screen appears with exactly two choices, each with a label that says what it leads to.

**Acceptance Scenarios**:

1. **Given** the application is not running, **When** the SLP launches it, **Then** the home screen appears showing an "import and interpret session data" choice and a "manage setup and configuration" choice.
2. **Given** the home screen is showing, **When** the SLP closes it, **Then** the application exits.

---

### User Story 2 - Open template management from the home screen (Priority: P2)

From the home screen, the SLP picks the management path and the existing Data Sheet Template management window opens. There the SLP can create, edit, and remove Data Sheet Templates exactly as they can today. A Back button takes them to the home screen. Closing the window exits the application, as it does today.

**Why this priority**: Template management already works. Routing to it gives the SLP a real, usable path from the new entry point straight away.

**Independent Test**: From the home screen, pick the management choice and confirm the template management window opens, lists the templates in the Template Store, and behaves as it does today.

**Acceptance Scenarios**:

1. **Given** the home screen is showing, **When** the SLP picks the management choice, **Then** the home screen is hidden and the Data Sheet Template management window opens, showing the templates from the Template Store.
2. **Given** the template management window was opened from the home screen, **When** the SLP presses its Back button, **Then** the template management window closes and the home screen is shown again.
3. **Given** the template management window was opened from the home screen, **When** the SLP closes the window, **Then** the application exits.
4. **Given** the SLP returned to the home screen from template management with Back, **When** they pick the management choice again, **Then** the template management window opens again and reflects any templates saved earlier.

---

### User Story 3 - Placeholder for import and interpret, with a way back (Priority: P3)

From the home screen, the SLP picks the import and interpret path. Because this path is not built yet, they see a placeholder screen that says so and offers a Back button. Back returns them to the home screen.

**Why this priority**: The path must be selectable so the navigation structure is complete. Its real content comes in a later feature.

**Independent Test**: From the home screen, pick the import and interpret choice, confirm the placeholder screen appears, then press Back and confirm the home screen returns.

**Acceptance Scenarios**:

1. **Given** the home screen is showing, **When** the SLP picks the import and interpret choice, **Then** the home screen is hidden and a placeholder screen appears stating the import and interpret process is not yet available, with a Back button.
2. **Given** the placeholder screen is showing, **When** the SLP presses Back, **Then** the home screen is shown again with both choices available.
3. **Given** the placeholder screen is showing, **When** the SLP looks at it, **Then** no import, OCR, or interpretation action is offered or started.

---

### Edge Cases

- The Template Store file does not exist yet: picking the management path opens the template management window with an empty template list, as it does today.
- The SLP picks the same path repeatedly (go, back, go again): each round trip works the same way, and the application never shows more than one home screen or more than one template management window at a time.
- The Template Store file path is missing or is not a JSON file at launch: the application stops with the same clear usage message it gives today, before showing the home screen.
- The SLP closes the template management window while unsaved template edits are open in a child window: the application exits the same way it does today when that window is closed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST have a single launch point that opens a home screen.
- **FR-002**: The home screen MUST offer exactly two choices: import and interpret session data, and manage setup and configuration.
- **FR-003**: Each choice MUST carry a label that uses the project's domain terms (e.g. Data Sheet, Template) so the SLP can tell what it leads to without prior instruction.
- **FR-004**: Picking the management choice MUST open the existing Data Sheet Template management window, using the Template Store given at launch.
- **FR-005**: The template management window MUST have a Back button that closes it and returns the SLP to the home screen.
- **FR-005a**: Closing the template management window (rather than pressing Back) MUST exit the application.
- **FR-006**: Picking the import and interpret choice MUST show a placeholder screen that states the feature is not yet available.
- **FR-007**: The placeholder screen MUST have a Back button that returns the SLP to the home screen.
- **FR-008**: The placeholder screen MUST NOT start any import, OCR, interpretation, or output action.
- **FR-009**: Reaching the home screen, the placeholder screen, and template management MUST NOT require contacting any external service or reading any external-service credentials.
- **FR-010**: Closing the home screen MUST exit the application.
- **FR-012**: While a path (template management or the import and interpret placeholder) is open, the home screen MUST be hidden. It MUST be shown again only when the SLP presses that path's Back button, so only one of these screens is on display at a time.
- **FR-013**: The new entry point MUST replace the separate template management launch script, which MUST be removed.
- **FR-014**: The existing developer-only interpretation script MAY remain temporarily. It MUST NOT be reachable from the new entry point, and the plan MUST record it as a justified deviation from the single composition root rule (Principle III), to be removed when the import and interpret path is built.
- **FR-011**: The home screen and placeholder screen MUST follow the system light/dark theme, matching the existing windows.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The SLP reaches template management from a fresh launch in 1 choice.
- **SC-002**: The SLP returns to the home screen from the import and interpret placeholder in 1 action.
- **SC-003**: An SLP seeing the home screen for the first time correctly says which choice leads to template management, without help, on the first try.
- **SC-004**: The SLP can repeat 10 round trips between the home screen and each path in one session with no duplicate windows, errors, or restart.
- **SC-005**: The application launches to the home screen with no network connection and no external-service credentials present.

## Assumptions

- The launch command still takes the Template Store file path as its argument, and its validation and usage message stay the same.
- The single entry point replaces the separate template management launch script and becomes the application's composition root. The ad-hoc interpretation script stays for now as a developer-only tool. It is not part of the SLP-facing application, and it will be removed once the import and interpret path is built in a later feature.
- "Manage setup and configuration" means template management only for now. Other configuration areas may be added behind this path later.
- No student data is shown or handled on the home screen or placeholder screen, so Principle I (Student Data Privacy) is not affected.
- The existing template management window is reused as is, apart from the added Back button.
