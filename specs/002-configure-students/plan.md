# Implementation Plan: Students

**Branch**: `002-configure-students` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-configure-students/spec.md`

## Summary

Add a **Students** window where the SLP adds, views, edits, and removes students. Each
student is identified only by a unique Student Key and has a Current Template. All
student code lives in a new `therepy_sessions/students/` package:
- a frozen `Student` dataclass and pure key rules;
- a `StudentStore` interface, with a `JsonStudentStore` that is injected into
  the windows that need it;
- the Students window and a modal editor whose form is built from pluggable field
  editors, so later settings slot in.

The home screen's setup button opens a new **Setup** menu in `app_shell/` with *Data
Sheet Templates* and *Students*. `program.py` takes the student records file as a
second launch argument, builds the one student store, and wires everything (research R1,
R2, R8, R9).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Tkinter (stdlib), `sv-ttk`, `darkdetect`. No new dependencies.

**Storage**: New local JSON file for student records (path from the second launch argument). It is versioned and written atomically (research R4). The existing Template Store JSON is unchanged.

**Testing**: Manual validation through [quickstart.md](quickstart.md), plus `python -c` checks of the pure rules and the student store. No test framework (research R11).

**Target Platform**: Desktop (Linux primary; any Tkinter-capable OS with a display)

**Project Type**: Desktop app (single project under `therepy_sessions/`)

**Performance Goals**: Lists and saves feel instant for a caseload in the tens. The whole file is read or written per operation.

**Constraints**: Offline; no credentials (FR-017). Only one screen visible at a time (FR-015). No names or other direct identifiers (FR-003, Principle I).

**Scale/Scope**: 1 user, tens of students. 1 new package (6 modules), 1 new Setup window, 1 relabeled button, a new launch argument, and 3 doc amendments.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Status |
| --- | --- | --- |
| I. Student Data Privacy | A record holds only the Student Key and the template id. Names were dropped in clarification. The records file is local, chosen by the SLP, and never sent anywhere. Validation uses placeholder keys in scratch files only. | ✅ Pass |
| II. Domain Language Fidelity | The UI and code use **Student**, **Student Key**, and **Data Sheet Template**. New concepts, **Current Template** and **Student Store**, are added to `docs/domain/glossary.md` in this change. | ✅ Pass (glossary update in scope) |
| III. Layered Pipeline | `students/` is a new setup package beside the pipeline. It imports none of `clients/`, `collection/`, `interpretation/`, or `storage/`, and gets template choices through an injected provider (R6). Rules live in pure functions and the student store, not widget callbacks (R3). `program.py` is still the only composition root. **Amendment**: `layers.md` gains `students/` and its import rule, and `app_shell/` gains the Setup menu. This is a MINOR bump, 1.2.0 → 1.3.0. | ✅ Pass + amendment |
| IV. Injected External Services | No clients. `JsonStudentStore` is built once in `program.py` and injected as the `StudentStore` interface into `StudentsWindow` and `StudentEditorWindow` (R2). **Amendment**: `dependency-injection.md` rule 6 names the student store and the template-choices provider. | ✅ Pass + amendment |
| V. Pluggable Interpreters & Templates | Interpreters are untouched. Templates are referenced only by their stable id. Deleting a template still works, and the student shows `Missing template` (FR-008). | ✅ Pass |
| VI. Typed Public Interfaces | Every new class and function is fully annotated ([contracts/](contracts/)). `Student` is a frozen dataclass, and `TemplateChoice` is a `NamedTuple`. The changed public helpers in `program.py` stay annotated. | ✅ Pass |
| Tech constraints | Tkinter + `sv-ttk` + `darkdetect`. JSON is UTF-8 with `indent=2`. Dependency files are unchanged. | ✅ Pass |

**Post-design re-check (after Phase 1)**: No change. The contracts add no dependency,
external service, or cross-layer import beyond what is listed above.

## Project Structure

### Documentation (this feature)

```text
specs/002-configure-students/
├── plan.md                      # This file
├── research.md                  # Phase 0: decisions R1–R11
├── data-model.md                # Student, rules, file format, navigation states
├── quickstart.md                # Manual validation V1–V9
├── contracts/
│   ├── cli.md                   # Two-argument launch command
│   ├── student-store.md    # StudentStore interface + JSON implementation
│   └── ui-windows.md            # Setup, Students, editor, field editors, wiring
├── checklists/
│   └── requirements.md          # Spec quality checklist
└── tasks.md                     # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
therepy_sessions/
├── program.py                         # CHANGE: second argument, student store, Setup wiring
├── app_shell/
│   ├── home_window.py                 # CHANGE: label "Manage Setup & Configuration"
│   └── setup_window.py                # NEW: SetupWindow
└── students/                          # NEW package: everything about students
    ├── __init__.py
    ├── student.py                     # Student, TemplateChoice, key rules, exceptions
    ├── student_store.py          # StudentStore (ABC)
    ├── json_student_store.py     # JsonStudentStore
    ├── student_field_editors.py       # StudentFieldEditor (ABC) + key and template editors
    ├── students_window.py             # StudentsWindow + ask_to_start_fresh
    └── student_editor_window.py       # StudentEditorWindow (modal)

docs/
├── conventions/architecture/
│   ├── layers.md                      # AMEND: students/ entry + rule; Setup menu in app_shell
│   └── dependency-injection.md        # AMEND: rule 6 covers StudentStore + providers
└── domain/
    └── glossary.md                    # AMEND: Current Template, Student Store

.specify/memory/
└── constitution.md                    # AMEND: Sync Impact Report, version 1.3.0
```

**Structure Decision**: This is a single desktop project under `therepy_sessions/`. As
requested, everything about students goes in the new `students/` package (research R1).
The Setup menu is navigation, so it goes in `app_shell/` beside the home screen. Both
packages depend only on Tkinter and on what `program.py` injects.

## Complexity Tracking

No violations. Feature 001's recorded deviation (`program_interpret.py` as a second,
developer-only composition root) is unchanged and outside this feature.
