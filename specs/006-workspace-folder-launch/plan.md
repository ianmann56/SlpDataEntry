# Implementation Plan: Workspace Folder Launch

**Branch**: `006-workspace-folder-launch` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-workspace-folder-launch/spec.md`

## Summary

Replace the two file-path launch arguments with one **Workspace** folder that holds
`students.json` and `templates.json`. When the folder is left out, a folder picker
opens instead.

**A new `workspace/` package** stands apart from the pipeline (R1):

- `workspace.py` holds the rules and does no UI work:
  - fixed file names
  - `inspect_workspace` decides the **Workspace State**: complete, partial, or not set
    up (R2)
  - `open_workspace` runs the launch flow with injected dialogs and file creators
- `workspace_dialogs.py` holds three small themed ttk dialogs (R6):
  - **Start a New Workspace?** with Start New Workspace and Close
  - **Workspace File Missing** with Close only
  - **Can't Open Workspace** with Close only

**Each store creates its own empty file.** `JsonStudentStore` and `TemplateStore` each
gain `create_empty_file()`. It writes the store's own empty format in exclusive-create
mode, so it never replaces an existing file (R3). A new Workspace is all or nothing: if
the second file fails, the first is removed again (R4).

**`program.py`** takes 0 or 1 arguments (R5). It withdraws the root window while the
Workspace opens, builds both stores from the Workspace paths, and shows the home screen
only once `open_workspace` returns. The old path validators are removed (R7).

**Docs**:

- glossary: **Workspace**, **Workspace State**, and the store entries
- `layers.md`: rule 11
- `dependency-injection.md`: rule 6
- constitution: 1.7.0
- `.gitignore`: the two Workspace file names
- the run instructions (R8)

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**:

- Tkinter (`ttk`, `filedialog`), `sv-ttk`, `darkdetect` (existing)
- stdlib `os`, `json`, `enum`, `typing`

No new dependencies.

**Storage**:

- Local JSON files only: `students.json` and `templates.json` in the Workspace folder.
- File formats are unchanged. The empty files are each store's existing "no entries"
  format (data-model).

**Testing**:

- Offline scratch-script checks of `workspace.py` and `create_empty_file`, with
  temporary folders and fake dialogs and creators.
- Manual validation per [quickstart.md](quickstart.md).
- No test framework (R9).

**Target Platform**: Desktop (Linux primary; any OS that runs Tkinter). Workspaces may
sit on FAT or exFAT USB drives (R3).

**Project Type**: Desktop app (single project under `therepy_sessions/`).

**Performance Goals**: Opening a complete Workspace adds two file-existence checks
before the home screen. That is imperceptible, and SC-002 asks for 0 prompts.

**Constraints**:

- No network and no credentials at launch (FR-015).
- Never replace or empty an existing Workspace file (FR-011, SC-005).
- Declining or stopping leaves the folder exactly as it was (FR-009, SC-004).
- Dialogs show paths only (FR-016).

**Scale/Scope**:

- 1 SLP, 1 Workspace per launch.
- Code: 3 new modules (`workspace/__init__.py`, `workspace.py`,
  `workspace_dialogs.py`), 3 changed modules (`program.py`, `json_student_store.py`,
  `template_store.py`), and 6 doc/config amendments.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Status |
| --- | --- | --- |
| I. Student Data Privacy | No new external service, and no data leaves the machine. Dialogs show paths and fixed text only, and never read file contents, so no Student Key appears (FR-016, R6). A Workspace holds real student records, so `.gitignore` gains `students.json` and `templates.json` (R8). Validation uses synthetic keys in scratch folders. | ✅ Pass |
| II. Domain Language Fidelity | **Workspace** and **Workspace State** are added to `docs/domain/glossary.md` in this change. The Student Store and Template Store entries are updated (FR-017). Code names match: `WorkspaceFiles`, `WorkspaceState`, `inspect_workspace`, `open_workspace`. | ✅ Pass (glossary update in scope) |
| III. Layered Pipeline | `workspace/` imports no pipeline package and not `students/`. It reaches the stores only through `create_*_file` callables wired in `program.py` (R1). Rules live in `workspace.py`, not in widget callbacks (layers rule 5). `program.py` stays the only composition root and the only place stores are built (rule 6). **Amendment**: `layers.md` adds `workspace/` to the package layout and rule 11. | ✅ Pass + amendment |
| IV. Injected External Services | No clients are touched. Launch still builds no AWS or Google client and reads no credentials (FR-015). The dialogs and file creators are injected into `open_workspace`. **Amendment**: DI rule 6 names what `open_workspace` receives. | ✅ Pass + amendment |
| V. Pluggable Interpreters & Templates | The template file format is unchanged, and every saved templates file still loads. The new empty file is standard format 2 with `last_template_id: 0`, written only for a brand new Workspace, so ids are never reused against existing Students (R3). | ✅ Pass |
| VI. Typed Public Interfaces | Every new public member is annotated: `WorkspaceState` (`Enum`), `WorkspaceFiles` and `WorkspaceInspection` (`NamedTuple`), the errors, the functions, the dialogs, and `create_empty_file` ([contracts/workspace.md](contracts/workspace.md)). `parse_command_line_args` changes to `-> str \| None`. | ✅ Pass |
| Tech constraints | Tkinter with `sv-ttk` for the dialogs. Local persistence stays JSON, UTF-8, `indent=2`. No new dependency, so `pip_requirements.txt` and `ALL_DEPENDENCIES.md` are unchanged. | ✅ Pass |
| Development Workflow | Offline checks use synthetic data in temporary folders (R9). No debug scaffolding is added. | ✅ Pass |

**Post-design re-check (after Phase 1)**: Still passing.

- The contracts add no dependency and no upstream import. `workspace_dialogs.py`
  imports only Tkinter and `workspace.workspace`.
- `program.py` remains the only module importing both `workspace/` and the stores.
- The amendments are MINOR, so the constitution goes 1.6.0 → 1.7.0.

## Project Structure

### Documentation (this feature)

```text
specs/006-workspace-folder-launch/
├── plan.md                  # This file
├── research.md              # Phase 0: decisions R1–R9
├── data-model.md            # Workspace, Workspace State, empty file formats, errors
├── quickstart.md            # Validation V1–V8
├── contracts/
│   ├── workspace.md         # workspace.py, workspace_dialogs.py, create_empty_file, program.py wiring
│   └── launch.md            # Command line, usage message, picker, dialog text
├── checklists/
│   └── requirements.md      # Spec quality checklist
└── tasks.md                 # Phase 2 (/speckit-tasks; not created here)
```

### Source Code (repository root)

```text
therepy_sessions/
├── program.py                              # CHANGE: 0/1 argument; picker; withdraw root; stores from workspace_files; open_workspace; remove path validators
├── workspace/
│   ├── __init__.py                         # NEW
│   ├── workspace.py                        # NEW: file names, WorkspaceState/Files/Inspection, errors, workspace_files, inspect_workspace, open_workspace
│   └── workspace_dialogs.py                # NEW: ask_to_start_new_workspace, show_missing_workspace_file, show_workspace_error (themed ttk Toplevels)
├── students/
│   └── json_student_store.py               # CHANGE: create_empty_file()
├── interpretation/
│   └── template_store.py                   # CHANGE: create_empty_file()
└── README.md                               # CHANGE: How to Run gives the Workspace launch command

docs/
├── conventions/architecture/
│   ├── layers.md                           # AMEND: workspace/ in package layout; rule 11
│   └── dependency-injection.md             # AMEND: rule 6 (open_workspace receives dialogs and create_empty_file callables)
└── domain/
    └── glossary.md                         # AMEND: Workspace, Workspace State; Student Store and Template Store entries

.specify/memory/
└── constitution.md                         # AMEND: Sync Impact Report, version 1.7.0

.gitignore                                  # CHANGE: students.json, templates.json
```

**Structure Decision**: This is a single desktop project under `therepy_sessions/`.

- The Workspace gets its own top-level package, beside `students/` and `app_shell/`,
  because it owns neither Students nor Templates. It only locates their files.
- Its rules (`workspace.py`) are separate from its Tkinter dialogs
  (`workspace_dialogs.py`), so the flow can be checked offline with fakes.
- File creation stays inside each store, which owns its format.

## Complexity Tracking

No violations.
