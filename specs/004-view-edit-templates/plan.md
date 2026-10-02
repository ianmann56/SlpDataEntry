# Implementation Plan: View and Edit Data Sheet Templates

**Branch**: `004-view-edit-templates` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-view-edit-templates/spec.md`

## Summary

This feature replaces the "Implementation coming soon" stub with a **Template Details**
window. The window opens read-only in view mode and switches to edit mode in place
(R7). In view mode, a tree shows every interpreter and its configuration through a new
`InterpreterConfig.describe` (R5). In edit mode, each interpreter's form opens with its
saved values, through a new `load` in each config form (R3). Unapplied form changes are
applied automatically, and a form-level Cancel discards them (R4).

All rules shared by the Create window and the Template Details window live in a new
module, `interpretation/template_manager/template_rules.py`, which does not import
Tkinter (R1). It holds:

- validation, with blank titles exempt from the duplicate check (R2)
- `TemplateDraft`, the working copy of a template in edit mode
- `TemplateUsage`
- the save and delete confirmation texts
- the clear-then-delete flow (R9)

Template management finds out which students use each template through two callables
injected from `program.py` (R8), so it imports nothing from `students/`. The student
store gains one atomic `clear_current_template` (R9).

Templates gain a saved `description` (R6). The templates file moves to a versioned
format with `last_template_id`, so template IDs are never reused (R10, interpreters
rule 6). Files saved before this feature still load, and saves become atomic.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Tkinter (stdlib: `ttk.Treeview`, `messagebox`), `sv-ttk`, `darkdetect`. There are no new dependencies.

**Storage**: Two existing local JSON files. The templates file gains `format_version: 2`, `last_template_id`, and an optional `description` for each template. Format 1 files are still read (R10). The student records file is unchanged in shape. One new store operation writes to it (R9).

**Testing**: No test framework, as in feature 003. Offline scratch-script checks of `template_rules.py`, `TemplateStore`, and `JsonStudentStore.clear_current_template` on copies of `sample_data/`, plus the manual [quickstart.md](quickstart.md) (R12).

**Target Platform**: Desktop (Linux primary; any OS that can run Tkinter with a display)

**Project Type**: Desktop app (a single project under `therepy_sessions/`)

**Performance Goals**: Windows feel instant. The files hold a few dozen templates and students, and every action reads them synchronously on the main thread. No background thread is needed.

**Constraints**: There is no network access, and no student data leaves the machine. Students appear only by Student Key (Principle I). Every templates file saved before this feature must keep loading, and the app never writes over a templates file it could not read (Principle V). A failed save never leaves a half-written file.

**Scale/Scope**: 1 user, about 1–50 templates, and about 1–100 students. This feature adds 2 new modules (`template_rules.py`, `template_details_window.py`) and deletes 1 stub. It changes 7 modules (management window, creator window, interpreter configs, template model, template store, both student stores) and `program.py`, and amends 4 docs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Status |
| --- | --- | --- |
| I. Student Data Privacy | Usage displays and confirmations name students only by Student Key (FR-010b, contracts/template-rules.md). No data leaves the machine, and no external service is involved. Validation uses synthetic keys and `sample_data/` copies. The description is free text about a sheet layout, and the spec's Assumptions say it must not identify a student. Both windows show a hint next to the field saying not to include student names. | ✅ Pass |
| II. Domain Language Fidelity | Code and UI use **Data Sheet Template**, **Current Template**, **Student Key**, **Section Interpreter**, and **Template Store**. The new terms **Template Details** (window), **view mode / edit mode**, **Template Description**, **Template Usage**, and **Template Draft** are added to `docs/domain/glossary.md` in this change. | ✅ Pass (glossary update in scope) |
| III. Layered Pipeline | Rules sit in a Tkinter-free `template_rules.py`, not in widget callbacks (rule 5, R1). Template management gets student information only through two injected callables wired in `program.py` (R8). It imports nothing from `students/`, so no new layer rule is needed. `students/` still imports nothing from the pipeline (rule 8). `program.py` stays the only composition root (rule 6). | ✅ Pass |
| IV. Injected External Services | No AWS or Google clients are involved. The stores and providers are injected through constructors. **Amendment**: `dependency-injection.md` rule 6 lists the new injections for the management and details windows (`load_template_usage` and `clear_template_from_students`). | ✅ Pass + amendment |
| V. Pluggable Interpreters & Templates | The core flow is not edited for any one type. **Amendment**: the "Config UI" piece in `interpreters.md` now requires `interpreter_type`, `describe`, and a `load` in the form, so every type can be shown and edited (FR-006b, R3, R5). All three existing configs implement them. Saved templates stay loadable: `description` is optional, and format 1 files are read (R6, R10). Interpreters the SLP doesn't change are saved exactly as loaded (R4). **Amendment**: `interpreters.md` rule 6 says the highest ID ever given out is kept, so an ID is never reused (R10). | ✅ Pass + amendment |
| VI. Typed Public Interfaces | Every new public member is annotated (contracts/). The DTOs become `@dataclass`, the config form becomes the `ConfigForm` `TypedDict`, and the usage and outcome types are a `NamedTuple` and an `Enum`. Touched public members of `TemplateStore`, `StudentDataSheetTemplate`, `InterpreterConfig`, the two windows, and the creator window gain annotations in this change. | ✅ Pass |
| Tech constraints | Tkinter + `sv-ttk`, and JSON written as UTF-8 with `indent=2`. No new dependency or service. | ✅ Pass |
| Development Workflow | No debug scaffolding. The verification approach is the same as feature 003. | ✅ Pass |

**Amendment size**: three referenced docs gain or change rules (dependency-injection rule
6, and interpreters "Config UI" and rule 6), plus glossary terms. That is MINOR:
constitution 1.4.0 → 1.5.0, with the Sync Impact Report updated.

**Post-design re-check (after Phase 1)**: No change. The contracts add no dependency, no
external service, and no import from `interpretation/` into `students/` or the other
way. The only cross-area link is the two callables wired in `program.py`.

## Project Structure

### Documentation (this feature)

```text
specs/004-view-edit-templates/
├── plan.md                  # This file
├── research.md              # Phase 0: decisions R1–R12
├── data-model.md            # Template, file format, usage, draft, window modes, delete outcome
├── quickstart.md            # Validation V1–V8
├── contracts/
│   ├── template-rules.md    # template_rules API, store and config contract changes
│   └── ui-windows.md        # Management, Template Details, and Create windows; program.py wiring
├── checklists/
│   └── requirements.md      # Spec quality checklist
└── tasks.md                 # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
therepy_sessions/
├── program.py                                      # CHANGE: load_template_usage, clear_template_from_students wiring
├── interpretation/
│   ├── template_store.py                           # CHANGE: typed DTOs + description, format 2 + last_template_id, atomic save (R6, R10)
│   └── template_manager/
│       ├── template_rules.py                       # NEW: validation, TemplateDraft, TemplateUsage, confirmations, delete flow (R1, R2, R8, R9)
│       ├── template_details_window.py              # NEW: view/edit window (R7)
│       ├── template_editor_window.py               # DELETE: stub replaced by template_details_window.py
│       ├── template_management_window.py           # CHANGE: Students column, View/Edit/Delete flows
│       ├── template_creator_window.py              # CHANGE: saves description, uses template_rules
│       ├── interpreter_configs.py                  # CHANGE: ConfigForm, interpreter_type, load, describe, find_config (R3, R5)
│       └── student_data_sheet_template.py          # CHANGE: description, annotations
└── students/
    ├── student_store.py                            # CHANGE: clear_current_template (abstract)
    └── json_student_store.py                       # CHANGE: clear_current_template (one atomic save)

docs/
├── conventions/architecture/
│   ├── dependency-injection.md                     # AMEND: rule 6 lists the template-usage injections
│   └── interpreters.md                             # AMEND: Config UI piece (interpreter_type, load, describe); rule 6 (no id reuse)
└── domain/
    └── glossary.md                                 # AMEND: Template Details, view/edit mode, Template Description, Template Usage, Template Draft

.specify/memory/
└── constitution.md                                 # AMEND: Sync Impact Report, version 1.5.0
```

**Structure Decision**: This is a single desktop project under `therepy_sessions/`. The
new window and its rules module sit beside the other template management modules in
`interpretation/template_manager/`, where `layers.md` already places the template UI.
The rules module sits next to the windows that use it, so both windows stay thin, as
`SheetImportBatch` did in feature 003.

## Complexity Tracking

No violations.
