# Implementation Plan: Import Data Sheets

**Branch**: `003-import-data-sheets` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-import-data-sheets/spec.md`

## Summary

Replace the placeholder Import window with a working one. The SLP builds a list of
sheet images (several rounds, de-duplicated, removable) and presses **Import**. Each
file is read with the existing `image_to_text`. The Student Key on the sheet selects the
student, and that student's Current Template interprets the sheet. Each success is
printed with `StudentDataSheet.debug()`.

The import rules live in a new Tkinter-free `SheetImportBatch`
(`interpretation/importing/sheet_import_batch.py`). Reading, students, templates, and
the result sink are all injected from `program.py` (research R1, R2). The window runs
the batch on one worker thread, with a queue polled by `after()`, so it stays
responsive and can Cancel between sheets (R3).

Readings are kept per file and reused on retry unless the file changed on disk (R4).
Each failure maps to a fixed reason whose message names the fix (R5). Two existing bugs
and gaps are fixed along the way: `StudentDataSheet` shares tables across instances
(R6), and a corrupt templates file looks empty (R7). `program_interpret.py` is retired
(R9).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Tkinter (stdlib, including `filedialog`, `threading`, `queue`), `sv-ttk`, `darkdetect`, `boto3` (existing, through `image_to_text`). No new dependencies.

**Storage**: None new. It reads the existing student records JSON and templates JSON. Nothing from an import is saved (the spec puts storage out of scope).

**Testing**: Offline `python -c`/scratch-script checks of `SheetImportBatch` with fakes, plus a manual [quickstart.md](quickstart.md). One step uses live Textract on synthetic samples. No test framework (R11).

**Target Platform**: Desktop (Linux primary; any Tkinter-capable OS with a display)

**Project Type**: Desktop app (single project under `therepy_sessions/`)

**Performance Goals**: The window repaints during a 10-sheet import (SC-005). Sheets are processed one at a time. Each Textract call takes a few seconds.

**Constraints**: Student data goes only to AWS Textract (FR-018). Output goes to the console only. Each successful reading is paid for once per window session (FR-008a). Tk widgets are touched only from the main thread.

**Scale/Scope**: 1 user, batches of about 10 to a few dozen sheets. 1 new module, 1 rewritten window, 2 small fixes in existing modules, `program.py` wiring, 1 deleted script, and 3 doc amendments.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Status |
| --- | --- | --- |
| I. Student Data Privacy | Images go only to Textract, through the existing `image_to_text`. Debug output goes to the console only, with no log file (FR-018). Window messages name students only by Student Key (FR-019, R5). Validation uses synthetic samples and placeholder keys. Scratch scripts are not committed. | ✅ Pass |
| II. Domain Language Fidelity | Code and UI use **Import**, **Student Key**, **Current Template**, **Data Sheet Template**, and **Interpretation**. New concepts **Selected File**, **Import Batch**, and **Sheet Outcome** are added to `docs/domain/glossary.md` in this change. | ✅ Pass (glossary update in scope) |
| III. Layered Pipeline | `SheetImportBatch` gets its Import through an injected `read_sheet`. It never imports `image_to_text` or `clients/`, so only `StudentDataSheetImport` crosses collection → interpretation (R2). Rules are in the batch, not widget callbacks (R1). Printing is an injected sink. `program.py` stays the only composition root, and deleting `program_interpret.py` removes feature 001's recorded deviation (R9). **Amendment**: `layers.md` rule 9 lets `interpretation/importing/` use `students/` only through the injected `StudentStore` and `Student`. MINOR, 1.3.0 → 1.4.0. | ✅ Pass + amendment |
| IV. Injected External Services | The Textract client is built lazily in `program.py` through `construct_textract_client()`, behind `inject_textract_client` (R8). No module-level clients. `image_to_text` already translates `ClientError`, and the batch turns every read error into `READING_FAILED`. **Amendment**: `dependency-injection.md` rule 6 adds that `ImportWindow`/`SheetImportBatch` receive `StudentStore`, a template lookup, a sheet reader, and a result sink. | ✅ Pass + amendment |
| V. Pluggable Interpreters & Templates | No interpreter or serializer changes. Templates are loaded per sheet through `to_data_sheet_interpreter()`. A mismatched sheet fails loudly as `TEMPLATE_MISMATCH`, and nothing partial is printed (FR-014). R6 fixes per-instance state in `StudentDataSheet` (interpreters rule 3). | ✅ Pass |
| VI. Typed Public Interfaces | All new types are `Enum`/`NamedTuple`/`@dataclass` and fully annotated ([contracts/import-batch.md](contracts/import-batch.md)). Touched public members of `StudentDataSheet` and `TemplateStore` gain annotations. | ✅ Pass |
| Tech constraints | Tkinter + `sv-ttk`. Textract `FORMS`+`TABLES` through the existing collector. Dependency files are unchanged (`ipdb` stays because `student_data_sheet_interpreter.py` still imports it). | ✅ Pass |

**Post-design re-check (after Phase 1)**: No change. The contracts add no dependency,
no external service, and no cross-layer import beyond the `students/` use covered by
the amendment.

## Project Structure

### Documentation (this feature)

```text
specs/003-import-data-sheets/
├── plan.md                  # This file
├── research.md              # Phase 0: decisions R1–R12
├── data-model.md            # SelectedFile, SheetOutcome, states, processing steps
├── quickstart.md            # Validation V1–V8
├── contracts/
│   ├── import-batch.md      # SheetImportBatch API + supporting changes
│   └── ui-windows.md        # ImportWindow, threading, program.py wiring
├── checklists/
│   └── requirements.md      # Spec quality checklist
└── tasks.md                 # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
therepy_sessions/
├── program.py                              # CHANGE: inject_textract_client, check_records_readable, ImportWindow wiring
├── program_interpret.py                    # DELETE (R9)
└── interpretation/
    ├── student_data_sheet.py               # CHANGE: per-instance _tables/_scalars (R6)
    ├── template_store.py                   # CHANGE: check_readable() + UnreadableTemplatesError (R7)
    └── importing/
        ├── sheet_import_batch.py           # NEW: SelectedFile, outcomes, SheetImportBatch
        └── import_window.py                # REWRITE: list, Import/Cancel, worker thread, summary

docs/
├── conventions/architecture/
│   ├── layers.md                           # AMEND: rule 9 (importing → students via StudentStore)
│   └── dependency-injection.md             # AMEND: rule 6 lists import injections
└── domain/
    └── glossary.md                         # AMEND: Selected File, Import Batch, Sheet Outcome

.specify/memory/
└── constitution.md                         # AMEND: Sync Impact Report, version 1.4.0
```

**Structure Decision**: This is a single desktop project under `therepy_sessions/`. The
import path stays in `interpretation/importing/`, where `layers.md` already places the
import UI. The new logic module sits beside the window, so the window remains a shell
(R1).

## Complexity Tracking

No violations. This feature removes the one previously recorded deviation
(`program_interpret.py`, from feature 001).
