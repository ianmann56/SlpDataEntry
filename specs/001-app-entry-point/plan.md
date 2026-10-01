# Implementation Plan: Application Entry Point

**Branch**: `001-app-entry-point` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-app-entry-point/spec.md`

## Summary

Replace the separate template management launch script with one entry point,
`therepy_sessions/program.py`. It opens a home screen with two choices. **Manage Setup &
Data Sheet Templates** hides the home screen and opens the existing template management
window, which gains a Back button. **Import & Interpret Student Data Sheets** hides the home
screen and shows a placeholder with Back. The Tk root is the home screen, and each path is
a `Toplevel` that is created on entry and destroyed on Back. The new shell windows take
plain callbacks, and `program.py` wires them (research R1, R2). Nothing contacts AWS or
Google at launch (R6).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Tkinter (stdlib), `sv-ttk`, `darkdetect`. All are existing, and no new dependencies are added.

**Storage**: Existing `TemplateStore` JSON file (path from CLI arg), unchanged

**Testing**: Manual validation via [quickstart.md](quickstart.md); no automated suite exists yet (research R8)

**Target Platform**: Desktop (Linux primary; Tkinter-capable OS with a display)

**Project Type**: Desktop app (single project under `therepy_sessions/`)

**Performance Goals**: Screen switches feel instant (well under 1 s); no measurable target beyond that

**Constraints**: Offline-capable launch; no credentials read at startup (FR-009); one visible top-level screen at a time (FR-012)

**Scale/Scope**: 1 user (the SLP); 2 new small windows, 1 changed window, 1 new composition root, 1 deleted script

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Status |
| --- | --- | --- |
| I. Student Data Privacy | No student data is shown on the new screens. Validation uses only the synthetic `sample_data/templates.json`. No new external service. | ✅ Pass |
| II. Domain Language Fidelity | Labels use glossary terms: "Student Data Sheets", "Data Sheet Templates", "Import", "Interpret". No new domain concept is introduced. "Home screen" is a UI term, not a domain term. | ✅ Pass |
| III. Layered Pipeline | `program.py` becomes the composition root again. The new `app_shell/` imports nothing from the pipeline layers. The new `interpretation/importing/` package follows the `interpretation` import rules (nothing from `storage/` or `clients/`) and, for now, imports only Tkinter. Wiring stays in `program.py`. **Deviation**: `program_interpret.py` stays as a second, developer-only root (spec FR-014). This is recorded in Complexity Tracking. **Amendment**: `layers.md` gains an `app_shell/` entry and its import rule, and rule 5's UI-window example adds `interpretation/importing/*_window.py`. This is a MINOR bump, 1.1.0 → 1.2.0, done in the same change. | ⚠️ Pass with justified deviation + amendment |
| IV. Injected External Services | `program.py` no longer builds Google or Textract clients at startup (R6). The windows receive `TemplateStore` and the config list through their constructors. | ✅ Pass (improves on current `program_manage.py`) |
| V. Pluggable Interpreters & Templates | No interpreter or serialization change. Saved templates load as before. | ✅ Pass |
| VI. Typed Public Interfaces | The new classes and the modified `DataSheetTemplateManagementWindow.__init__` are fully annotated ([contracts/ui-windows.md](contracts/ui-windows.md)). The public helpers moved into `program.py` (`main`, `validate_storage_file_path`, `parse_command_line_args`) get annotated too. | ✅ Pass |
| Tech constraints | Tkinter + `sv-ttk` + `darkdetect` only. `pip_requirements.txt` and `ALL_DEPENDENCIES.md` are unchanged. | ✅ Pass |

**Post-design re-check (after Phase 1)**: No change. The contracts and state machine add
no dependencies, I/O, or pipeline imports beyond what is listed above.

## Project Structure

### Documentation (this feature)

```text
specs/001-app-entry-point/
├── plan.md              # This file
├── research.md          # Phase 0: design decisions R1–R8
├── data-model.md        # Phase 1: navigation state machine
├── quickstart.md        # Phase 1: manual validation guide
├── contracts/
│   ├── ui-windows.md    # Window constructor + behavior contracts
│   └── cli.md           # Launch command contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
therepy_sessions/
├── program.py                         # NEW: single entry point / composition root
├── program_manage.py                  # DELETE (FR-013)
├── program_interpret.py               # KEEP: add dev-only docstring, fix usage text (FR-014)
├── app_shell/                         # NEW package: navigation shell windows
│   ├── __init__.py
│   └── home_window.py                 # HomeWindow
└── interpretation/
    ├── importing/                     # NEW package: import and interpret path windows
    │   └── import_window.py           # ImportWindow (placeholder content for now)
    └── template_manager/
        └── template_management_window.py  # CHANGE: optional back_callback + Back button

docs/conventions/architecture/
└── layers.md                          # AMEND: add app_shell/ + import rule; rule 5 example

.specify/memory/
└── constitution.md                    # AMEND: Sync Impact Report, version 1.2.0
```

**Structure Decision**: This is a single desktop project under `therepy_sessions/`,
following the layout in `layers.md`. The home screen goes in a new `app_shell/`
package beside the pipeline packages. The import window goes in a new
`interpretation/importing/` package, beside `template_manager/`, because it belongs to the
import and interpret path (research R2). Both depend only on Tkinter for now, and
`program.py` connects them to the rest of the app.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| Second composition root: `program_interpret.py` (Principle III, "`program.py` is the only composition root") | It is the only working photo → OCR → interpretation flow. The developer needs it to check interpreters against real sample sheets until the import and interpret path is built (clarification Q3). | *Delete it now*: the developer loses the only end-to-end check until the next feature. *Route to it from the placeholder*: this would expose unfinished, credential-dependent behavior to the SLP (FR-008, FR-009). **Removal trigger**: delete it in the feature that implements the import and interpret path. |
