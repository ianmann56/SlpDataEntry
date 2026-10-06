# Implementation Plan: Save Imported Sessions to Google Drive

**Branch**: `005-save-sessions-drive` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-save-sessions-drive/spec.md`

## Summary

Replace the Import window's debug-print sink with a real Storage step. After a sheet is
interpreted, it is saved as a **Session Tab** in its **Student Session Workbook** in
`SLP Therepy Data/Current Year`. There is one workbook per Student Key and Template
Structure.

**A Data Sheet Store abstraction.** Business logic and UI logic reach storage only
through an abstract **Data Sheet Store** (`DataSheetStore`, R1):

- It has two methods: `prepare()` and `save(sheet: StudentDataSheet) -> SavedDataSheet`.
- The ABC lives in `interpretation/data_sheet_store.py`, on the consumer side, so layers
  rule 1 still holds.
- `GoogleDriveDataSheetStore` in `storage/` implements it, and `program.py` injects it
  into both `SheetImportBatch` and `ImportWindow`.

**The sheet is the only thing sent to the store, and it carries its template.**
`StudentDataSheet` gains `template`, set by the interpreter, and the batch gives it the
stored Student Key (R2). Storage derives the template-dependent rules from
`sheet.template`, using the interpreters' new `section_keys()` / `section_kind`:

- the structure fingerprint, which ignores order, types, and choices (R3)
- the workbook name
- the layout order

**Saving runs in the batch.** It happens inside `SheetImportBatch.process_file` on the
worker thread. A sheet succeeds only after the store saves it, and a failed save is
retried with the existing rules (R1).

**What the Google store does**:

- finds workbooks by hidden Drive `appProperties` (Student Key and fingerprint), with
  the newest modified copy winning (R4)
- keeps the Workbook Layout Order in spreadsheet developer metadata
- caches workbooks found or created in this window, to beat search lag (R5)
- writes each tab with one atomic `batchUpdate`, placing values by key and typing them
  from the interpreted type (R6, R7)
- repairs a workbook left empty by a failed create whose cleanup also failed: the next
  save writes its missing layout and removes its empty default tab (R6)
- detects duplicates from the Date and Time IN in each tab. A blank Time IN gets a
  date-only tab name and is never a duplicate (R8).

**Pure layout logic** lives in `storage/session_layout.py` and
`storage/template_structure.py`, so it can be checked offline (R8, R9, R12).

**Sign-in and the folder** are prepared through `store.prepare()` on the worker thread
when Import is pressed, before any sheet is read (R10).

**Rows** gain a status indicator and an **Open** action.

**The prototype** `storage/file_creator.py` is retired (R13).

**Each table goes to one section**: Collection reads each table's printed title, and
the sheet interpreter gives each table to the section with that title, so a template with
several table sections no longer saves every table twice (R14).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**:

- Tkinter, `sv-ttk`, `darkdetect` (existing)
- `google-api-python-client`, `google-auth`, `google-auth-oauthlib` (already pinned)
  for Sheets v4 and Drive v3
- stdlib `hashlib`, `json`, `datetime`, `webbrowser`

No new dependencies.

**Storage**:

- Google Drive and Sheets: workbooks, tabs, `appProperties`, and developer metadata.
- No new local storage. The OAuth token cache stays as today (`.token_*`, git-ignored).

**Testing**:

- Offline scratch-script checks of the pure functions (`template_structure`,
  `session_layout`).
- `SheetImportBatch` with an in-memory fake `DataSheetStore`.
- `GoogleDriveDataSheetStore` with in-memory fake Drive and Sheets services.
- Live validation on synthetic sheets and a test Google account, per
  [quickstart.md](quickstart.md).
- No test framework (R12).

**Target Platform**: Desktop (Linux primary; any OS that runs Tkinter and a browser for
OAuth).

**Project Type**: Desktop app (single project under `therepy_sessions/`).

**Performance Goals**:

- A 10-sheet batch saves within 1 extra minute (SC-006): about 4–5 Google calls per
  sheet, a few seconds total.
- The window stays responsive during sign-in and saving: everything runs on the worker
  thread (R10).

**Constraints**:

- Student data goes only to Google Drive and Sheets (plus Textract, as before).
- Labels and layout metadata hold only the Student Key and template keys (FR-028).
- No partial tabs (FR-002).
- All Google calls run on the single worker thread, because the `httplib2` transport is
  not thread-safe.

**Scale/Scope**:

- 1 SLP; batches of about 10 to a few dozen sheets.
- A caseload of dozens of workbooks per school year.
- About 180 tabs per workbook per year at most.
- Code: 4 new modules, about 9 changed modules, 1 deleted module, and 5 doc amendments.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Status |
| --- | --- | --- |
| I. Student Data Privacy | Session values go only to the SLP's Google Sheets, an approved service (FR-026). Drive `appProperties` and developer metadata hold the stored Student Key and template keys only, never values (FR-028, R4). Workbook names, tab names, and window messages use the Student Key only (FR-027). No log file. Errors print to the console as today. Validation uses synthetic sheets and a test account. The client secret stays outside the repo, now overridable by an environment variable (R11). | ✅ Pass |
| II. Domain Language Fidelity | New terms are added to `docs/domain/glossary.md` in this change: **Data Sheet Store**, **Template Structure**, **Student Session Workbook** (replacing **Session Sheet**), **Session Tab**, **Session Moment**, **Workbook Layout Order**, and **Therapy Data Folder**. Code identifiers match them: `DataSheetStore`, `SessionMoment`, `WorkbookLayout`, `GoogleDriveDataSheetStore`. | ✅ Pass (glossary update in scope) |
| III. Layered Pipeline | Only `StudentDataSheet` crosses interpretation → storage. The template rides on it as `sheet.template` (R2). The `DataSheetStore` ABC lives in `interpretation/`, so `interpretation/` imports nothing from `storage/` or `clients/`. `storage/` imports `interpretation/` to implement the port (allowed downstream). Interpretation stays pure: attaching the template is not I/O. Sheets and Drive request bodies live only in `storage/` (rule 4). Layout and ordering rules are plain functions, not widget callbacks (rule 5). `program.py` is the only module that names the concrete store (rule 6). **Amendment**: layers rule 1 states that the sheet carries its template, and that Storage reads it only through the sheet. It also names `DataSheetStore` as the port that the importing code and windows use to reach storage. | ✅ Pass + amendment |
| IV. Injected External Services | Google credentials and services are built only in `clients/google_service.py`, lazily, behind `inject_drive_service` and `inject_sheets_service` in `program.py` (R11). No module-level clients and no OAuth at import time. `GoogleDriveDataSheetStore` translates `HttpError`, `RefreshError`, and transport errors into `DataSheetStoreError` (DI rule 5). **Amendment**: DI rule 6 now says `ImportWindow` and `SheetImportBatch` receive a `DataSheetStore` (one instance per Import visit, built in `program.py`) instead of the result sink, and the window also receives `open_url`. | ✅ Pass + amendment |
| V. Pluggable Interpreters & Templates | Storage never `isinstance`-checks interpreter types. Each interpreter reports `section_keys()` and `section_kind` through the base class, and Storage reads them from `sheet.template` (R2). Serialized templates are unchanged, so every saved template still loads. A mismatched sheet still fails loudly. A new destination is a new `DataSheetStore` subclass, with no change to the import flow. A template whose table sections don't match the sheet's table titles fails loudly (R14). **Amendment**: `interpreters.md` makes `section_keys` and `consumes_tables` part of a complete interpreter type, notes that `StudentDataSheet` carries its template, and adds rule 9 (each table is read by one section). | ✅ Pass + amendment |
| VI. Typed Public Interfaces | All new types are `NamedTuple`/`Enum`/`TypedDict` and fully annotated (contracts). Touched members of the interpreter classes, `StudentDataSheet`, `DataSheetTable`, `StudentDataSheetInterpreter`, and `google_service` gain annotations in this change. Google `Resource` objects are typed `Any`, with a comment naming the concrete type (type-declarations rule 6). | ✅ Pass |
| Tech constraints | Output goes through `google-api-python-client` with OAuth, as the constitution specifies. No new runtime dependency, so `pip_requirements.txt` and `ALL_DEPENDENCIES.md` are unchanged. Local persistence is unchanged. | ✅ Pass |
| Development Workflow | The debug-print stand-in from feature 003 is replaced by the shipped Storage path (`debug()` stays as an uncalled developer aid). Offline checks use synthetic inputs (R12). | ✅ Pass |

**Post-design re-check (after Phase 1)**: Still passing.

- The contracts add no dependency and no upstream import. `storage/` imports from
  `interpretation/` (the `DataSheetStore` port, `StudentDataSheet`, and the template
  model), which is allowed downstream.
- Callers see only `DataSheetStore`, `SavedDataSheet`, and `DataSheetStoreError`.
- `StudentDataSheet` imports the template type only for type checking, so there is no
  import cycle (R2).
- The amendments are MINOR, so the constitution goes 1.5.0 → 1.6.0.

## Project Structure

### Documentation (this feature)

```text
specs/005-save-sessions-drive/
├── plan.md                         # This file
├── research.md                     # Phase 0: decisions R1–R14
├── data-model.md                   # Shapes, outcomes, workbook/tab/label model, cell rules
├── quickstart.md                   # Validation V1–V9
├── contracts/
│   ├── interpretation-and-import.md  # DataSheetStore port, sheet/interpreter changes, batch, window, wiring
│   └── session-storage.md            # template_structure, session_layout, GoogleDriveDataSheetStore, google_service
├── checklists/
│   └── requirements.md             # Spec quality checklist
└── tasks.md                        # Phase 2 (/speckit-tasks; not created here)
```

### Source Code (repository root)

```text
therepy_sessions/
├── program.py                                   # CHANGE: lazy Google services, one GoogleDriveDataSheetStore per Import visit injected as DataSheetStore, open_url
├── clients/
│   └── google_service.py                        # CHANGE: load_google_credentials / create_sheets_service / create_drive_service; env override; sign-in timeout; remove unused helpers
├── collection/
│   ├── collection_headers.py                    # CHANGE: StudentDataSheetImport.table_titles (R14)
│   └── images/aws_image_collection.py           # CHANGE: read TABLE_TITLE into table_titles (R14)
├── interpretation/
│   ├── data_sheet_store.py                      # NEW: DataSheetStore ABC, SavedDataSheet, DataSheetStoreError (the storage port)
│   ├── student_data_sheet.py                    # CHANGE: template, use_student_key, register_table(table, section_id), DataSheetTable.section_id
│   ├── templates/
│   │   └── student_data_sheet_interpreter.py    # CHANGE: base section_kind/section_keys/consumes_tables; interpreter takes the template, attaches it, tags tables, assigns tables by title (R14)
│   ├── interpreter_types/
│   │   ├── table_interpreter.py                 # CHANGE: section_keys, consumes_tables
│   │   ├── running_tally_interpreter.py         # CHANGE: section_keys, consumes_tables
│   │   └── simple_form_interpreter.py           # CHANGE: section_keys
│   ├── template_manager/
│   │   └── student_data_sheet_template.py       # CHANGE: to_data_sheet_interpreter passes self
│   └── importing/
│       ├── sheet_import_batch.py                # CHANGE: data_sheet_store, use_student_key, MISSING_DATE, SAVE_FAILED, outcome.saved
│       └── import_window.py                     # CHANGE: data_sheet_store.prepare() on worker, status indicator, Open action, drop on_sheet_interpreted
└── storage/
    ├── file_creator.py                          # DELETE (prototype, R13)
    ├── template_structure.py                    # NEW: pure TemplateShape/shape_of(template), structure fingerprint
    ├── session_layout.py                        # NEW: pure naming, moments, ordering, rows, cell kinds, layout JSON
    └── google_drive_data_sheet_store.py         # NEW: GoogleDriveDataSheetStore(DataSheetStore) (Drive/Sheets requests)

docs/
├── conventions/architecture/
│   ├── layers.md                                # AMEND: rule 1 (sheet carries its template; DataSheetStore port); rule 2 (table_titles)
│   ├── dependency-injection.md                  # AMEND: rule 6 (DataSheetStore injected, open_url, lazy Google services)
│   └── interpreters.md                          # AMEND: section_keys/section_kind/consumes_tables in "Adding a new interpreter type"; the sheet carries its template; rule 9 (each table read by one section)
└── domain/
    └── glossary.md                              # AMEND: new terms; Session Sheet → Student Session Workbook

.specify/memory/
└── constitution.md                              # AMEND: Sync Impact Report, version 1.6.0
```

**Structure Decision**: This is a single desktop project under `therepy_sessions/`.
Output code goes in `storage/`, where `layers.md` places "StudentDataSheet → output
destination".

- The storage port (`DataSheetStore`) sits in `interpretation/`, beside its consumers,
  following the same pattern as `StudentStore` / `JsonStudentStore`.
- The pure rules (`template_structure.py`, `session_layout.py`) are kept apart from the
  Google adapter (`google_drive_data_sheet_store.py`), so they can be checked offline.
- Template-dependent storage logic lives in `storage/`, driven by `sheet.template`.

## Complexity Tracking

No violations.
