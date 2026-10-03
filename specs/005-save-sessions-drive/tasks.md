---

description: "Task list for the Save Imported Sessions to Google Drive feature"
---

# Tasks: Save Imported Sessions to Google Drive

**Input**: Design documents from `/specs/005-save-sessions-drive/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md),
[contracts/interpretation-and-import.md](contracts/interpretation-and-import.md),
[contracts/session-storage.md](contracts/session-storage.md), [quickstart.md](quickstart.md)

**Tests**: No automated tests. The spec doesn't ask for them. Research R12 makes
verification:

- offline scratch-script checks of the pure modules
- `SheetImportBatch` with a fake `DataSheetStore`
- `GoogleDriveDataSheetStore` with fake Drive and Sheets services
- live checks from [quickstart.md](quickstart.md) on synthetic sheets and a test Google
  account

Scratch scripts are not committed.

**Organization**: Tasks are grouped by user story.

- **US1 (P1)** delivers an end-to-end save. One workbook per Student Key and Template
  Structure (reused even before Drive search lists it), one tab per import named by
  Date and Time IN with unique names, plain-text rows, status, and Open. It also
  carries the glossary, architecture-doc, and constitution amendments, so it can be
  merged on its own.
- **US2 (P1)** makes tab contents exact: typed cells, every value, no metadata, the
  clarified layout.
- **US3 (P2)** makes later saves follow the workbook's own layout order. It also
  checks renamed, trashed, and copied workbooks, and repairs a workbook left empty by
  a failed create.
- **US4 (P3)** adds duplicate detection and newest-first ordering.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US4 from spec.md

## Path Conventions

- All code is under `therepy_sessions/`. Modules import each other by package path from
  that directory (e.g. `from interpretation.data_sheet_store import DataSheetStore`).
- **Types**: every public function, method, property, attribute, and `__init__` added or
  changed is fully annotated per
  [type-declarations.md](../../docs/conventions/architecture/type-declarations.md).
  Google `Resource` objects are typed `Any`, with a comment naming the concrete type.
- **Interpretation stays clear of storage and Google**: `interpretation/` (including
  `interpretation/importing/` and `interpretation/data_sheet_store.py`) MUST NOT import
  `storage/`, `clients/`, or any `google*` package.
- **Storage stays clear of the rest**: `storage/` may import `interpretation/` (the port,
  `StudentDataSheet`, the template model, and the interpreter base), but never
  `students/`, `clients/`, or `tkinter`.
- **The store's name is private to `program.py`**: only `program.py` names
  `GoogleDriveDataSheetStore`. Every other module uses `DataSheetStore`.
- **Threads**: all Google calls run on the Import window's single worker thread. Only
  the Tk thread touches widgets.
- **Privacy**: messages, workbook names, tab names, `appProperties`, and developer
  metadata name students only by Student Key, and never contain session values outside
  the tab cells (FR-026–FR-028). Use only synthetic data and placeholder keys
  (`AG`, `JA`, `BK`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the Google client module and remove the prototype output.

- [X] T001 Rewrite `therepy_sessions/clients/google_service.py` per contracts/session-storage.md § `clients/google_service.py` and research R11:
  - `load_google_credentials() -> Any` keeps today's pickle-cache, refresh, `RefreshError` fallback, and `InstalledAppFlow.run_local_server` logic.
  - `create_sheets_service(credentials: Any) -> Any` is `build('sheets', 'v4', credentials=credentials)`.
  - `create_drive_service(credentials: Any) -> Any` is `build('drive', 'v3', credentials=credentials)`.
  - `DEFAULT_CLIENT_SECRET_FILE: str` holds today's default path and `CLIENT_SECRET_FILE_ENV: str = "SLP_GOOGLE_CLIENT_SECRET_FILE"` names the override. `load_google_credentials()` reads the environment variable when called, never at import time (Principle IV). `SCOPES: list[str]` is unchanged.
  - Keep the token pickle file name `.token_sheets_v4.pickle`, so existing sign-ins keep working.
  - Remove `create_google_service`, `convert_to_RFC_datetime`, and the unused imports (`Flow`, `MediaFileUpload`, `MediaIoBaseDownload`, `datetime`).
  - Nothing may run at import time.
- [X] T002 [P] Delete `therepy_sessions/storage/file_creator.py` (research R13), and confirm with `grep -rn "file_creator\|create_therapy_session_sheet" therepy_sessions --include='*.py'` that nothing references it.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add the storage abstraction, attach the template to the sheet, report
section keys, and compute the Template Structure. Every story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 [P] Create `therepy_sessions/interpretation/data_sheet_store.py` per contracts/interpretation-and-import.md § `data_sheet_store.py`:
  - `SavedDataSheet(NamedTuple)` with `location_url: str`, `location_name: str`, and `already_saved: bool`.
  - `DataSheetStoreError(Exception)`.
  - `DataSheetStore(ABC)` with abstract `prepare(self) -> None` and `save(self, sheet: StudentDataSheet) -> SavedDataSheet`.
  - Docstrings state that `prepare` is idempotent, that `save` writes nothing partial and calls `prepare` if needed, and that messages name students only by Student Key.
  - Import nothing but stdlib and `interpretation.student_data_sheet`.
- [X] T004 [P] In `therepy_sessions/interpretation/templates/student_data_sheet_interpreter.py`, add to `SessionDataSectionInterpreterBase` (research R2):
  - a `section_kind` property returning `type(self).__name__`
  - an abstract `section_keys(self) -> list[str]` whose docstring says "field / column / tally keys in template order"
  - type annotations on `__init__(self, id: str, title: str) -> None`, and on the `id` and `title` properties (`-> str`)
- [X] T005 [P] Implement `section_keys` on each interpreter type (depends on T004):
  - `therepy_sessions/interpretation/interpreter_types/table_interpreter.py`: `[column.column_name for column in self._columns]`
  - `therepy_sessions/interpretation/interpreter_types/running_tally_interpreter.py`: `["Tally"]`. Reuse the existing `tally_column_name` value by making it a module constant `TALLY_COLUMN_NAME: str = "Tally"`.
  - `therepy_sessions/interpretation/interpreter_types/simple_form_interpreter.py`: `list(self._fields.keys())`

  Annotate each new method. Move the class-level mutable defaults that these files still declare (`_columns = []`, `_fields = {}`) into `__init__` only (interpreters rule 3).
- [X] T006 Update `therepy_sessions/interpretation/student_data_sheet.py` per contracts/interpretation-and-import.md § `StudentDataSheet`:
  - Add `from __future__ import annotations`, and import `StudentDataSheetTemplate` only under `if TYPE_CHECKING:` (research R2 import cycle).
  - `DataSheetTable` gains `section_id: NotRequired[str]`.
  - `__init__` gains a final `template: StudentDataSheetTemplate` parameter, exposed as a `template` property.
  - `register_table(self, table: DataSheetTable, section_id: str) -> None` stores `{**table, "section_id": section_id}`.
  - Add `use_student_key(self, student_key: str) -> None`, which replaces `_student_key`.
  - `debug()` also prints `Template: {self.template.name}`.
- [X] T007 Update `therepy_sessions/interpretation/templates/student_data_sheet_interpreter.py` and `therepy_sessions/interpretation/template_manager/student_data_sheet_template.py` (depends on T006):
  - `StudentDataSheetInterpreter.__init__(self, session_data_templates: list[SessionDataSectionInterpreterBase], template: StudentDataSheetTemplate) -> None` stores the template. Import it under `TYPE_CHECKING` to avoid the cycle.
  - `interpret_student_data_sheet` builds `StudentDataSheet(..., template=self._template)`, and registers each table with `data_sheet.register_table(table, interpreter.id)`. Pair each interpretation with the interpreter that produced it.
  - `StudentDataSheetTemplate.to_data_sheet_interpreter()` returns `StudentDataSheetInterpreter(self.interpreters, self)`.
  - Annotate `interpret_student_data_sheet` to return `StudentDataSheet`.
- [X] T008 [P] Create `therepy_sessions/storage/template_structure.py` per contracts/session-storage.md § `template_structure.py` and research R3 (depends on T004, T005):
  - `SectionShape(NamedTuple)` (`section_id`, `kind`, `title`, `keys: tuple[str, ...]`) and `TemplateShape(NamedTuple)` (`template_name`, `sections`).
  - `shape_of(template: StudentDataSheetTemplate) -> TemplateShape` reads each interpreter's `id`, `section_kind`, `title`, and `section_keys()`, with no `isinstance` checks.
  - `TemplateShape.structure_identity()` returns `sorted((kind, title, sorted(keys)) for each section)`.
  - `TemplateShape.structure_fingerprint()` returns `"s1-" + hashlib.sha256(json.dumps(identity, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()[:32]`.
  - Stdlib only, no I/O.
- [X] T009 Offline check of the foundation (quickstart V1). In a scratch script run from `therepy_sessions/`:
  - Load the scratch `templates.json` through `TemplateStore` and interpret an Import from `sample_data/imports/`.
  - Confirm `sheet.template` is the template used, and that every table has a `section_id`.
  - Confirm every V1 fingerprint expectation: reordered, renamed, and type- or choice-changed copies are equal; a renamed column or section title differs.
  - Confirm the program still launches (`../.venv/bin/python3 program.py <templates> <students>`) and that Setup → Templates still loads every saved template.

**Checkpoint**: The sheet carries its template, the structure is computable, and the
storage port exists.

---

## Phase 3: User Story 1 - Save each imported session to the student's Google Sheet (Priority: P1) 🎯 MVP

**Goal**: Pressing Import saves each interpreted sheet as a new tab in its student's
workbook in `SLP Therepy Data/Current Year`.

- The workbook is created on the first save, and found by Student Key and Template
  Structure on later saves, including a workbook created moments earlier in the same
  window, which Drive search may not list yet.
- Tab names are unique, so a second blank-Time-IN sheet for a date gets `<date> 2`.
- A row shows ✓ Succeeded only after its save, with an Open action.
- Failures to save, or a missing Date, show ✗ Failed.
- The glossary, architecture docs, and constitution describe the new code, so this
  phase can be merged on its own.

**Independent Test**: spec US1. Import one synthetic `AG` sheet: one workbook is created
in the folder, with a tab named `<Date> <Time IN>`. Import a second `AG` sheet with
another date: a second tab appears in the same workbook. Open shows the tab. See
quickstart V4.

### Implementation for User Story 1

- [X] T010 [P] [US1] Create `therepy_sessions/storage/session_layout.py` with the US1 subset of contracts/session-storage.md § `session_layout.py`. Pure, with no Google imports:
  - `TAB_NAME_MAX: int = 100`
  - `SessionMoment(NamedTuple)` (`date_text`, `time_text`) and `moment_of(sheet) -> SessionMoment`
  - `tab_base_name(moment) -> str`: `"{date} {time}"`, or `"{date}"` when the time is blank. Remove control characters, collapse whitespace, and trim so a `" N"` suffix still fits in 100 characters (FR-015, FR-018).
  - `unique_tab_name(base, taken) -> str`: `base`, else the lowest `f"{base} {n}"` for `n ≥ 2` not in `taken` (FR-016b, FR-017a). Google Sheets refuses two tabs with the same name, so every save needs this.
  - `workbook_name(student_key, template_name) -> str`, returning `"{key} - {name}"`.
  - `CellValue(NamedTuple)` (`text: str | None`, `number: int | None`).
  - A first `session_rows(sheet, layout) -> list[list[CellValue]]` that writes every value as text, in this order:
    1. the 6 header rows (`Student Key`, `Date`, `Time IN`, `Time OUT`, `Goal`, `Measure` in column A; values in B)
    2. one row per form field
    3. a blank row
    4. for each table: a title row with its section title, a column-header row, and the data rows, then a blank row
  - `LayoutSection`, plus `WorkbookLayout` with `from_shape(shape)`, `to_json()` (`{"version": 1, "sections": [...]}`), and `from_json(text)`.
- [X] T011 [US1] Create `therepy_sessions/storage/google_drive_data_sheet_store.py` with `GoogleDriveDataSheetStore(DataSheetStore)` per contracts/session-storage.md (depends on T003, T008, T010).

  **Constructor**: `__init__(inject_drive_service: Callable[[], Any], inject_sheets_service: Callable[[], Any])`.

  **`prepare()`** (research R10), idempotent:
  - Call both injectors.
  - Find or create the folder `SLP Therepy Data` (`'root' in parents`, `mimeType='application/vnd.google-apps.folder'`, `trashed=false`, the oldest `createdTime` wins), then `Current Year` inside it.
  - Cache the folder id.

  **Workbook cache** (research R5, FR-007):
  - `self._workbook_ids: dict[tuple[str, str], str]`, keyed by `(student_key, fingerprint)`, is filled on create and on search hits.
  - Before using a cached id, call `files().get(fileId=..., fields="trashed,parents")`. Drop the entry and search again if the file is trashed, not in the folder, or 404.
  - The class docstring says the cache only speeds things up, and Drive is the source of truth.

  **`save(sheet)`**, calling `prepare()` first if needed:
  - `shape = shape_of(sheet.template)`, then the fingerprint, then `key = sheet.student_key`.
  - Use the cached id when it is still valid. Otherwise search with `files.list(q=<folder, not trashed, spreadsheet mimeType, appProperties slpWorkbook=1 / slpStudentKey=key / slpStructure=fp>, orderBy="modifiedTime desc", fields="files(id,name)")` and take the first match (research R4, FR-013b).
  - **None found**: create the workbook per research R6.
    - `drive.files().create(body={name: workbook_name(...), mimeType: spreadsheet, parents: [folder], appProperties: {...}}, fields="id")`.
    - Then one `spreadsheets().batchUpdate` with `addSheet` (a new random `sheetId`, `title=tab_base_name`, `index=0`), `updateCells` (rows from `session_rows`, start at row 0 col 0, `fields="userEnteredValue"`), `deleteSheet` of the default tab (its id comes from a `spreadsheets().get(fields="sheets.properties.sheetId")`), and `createDeveloperMetadata` (key `slpWorkbookLayout`, `DOCUMENT` location, `DOCUMENT` visibility, value `WorkbookLayout.from_shape(shape).to_json()`).
    - If the batch fails, call `files().delete` on the new file (best effort; print a delete failure to the console, naming students only by Student Key) and raise. T025 repairs a file left behind this way.
  - **Found**: `spreadsheets().get(fields="properties.title,sheets.properties(sheetId,title,index)")`, then one `batchUpdate` with `addSheet` (a unique random `sheetId`, the title `unique_tab_name(tab_base_name(moment), existing titles)`, and the index set to the current tab count) plus `updateCells`.
  - **Result**: `SavedDataSheet(location_url=f"https://docs.google.com/spreadsheets/d/{id}/edit#gid={sheet_id}", location_name=f"{workbook title} › {tab title}", already_saved=False)`.
  - **Calls and errors**:
    - Every `.execute(num_retries=3)`.
    - Wrap all calls so `googleapiclient.errors.HttpError`, `google.auth.exceptions.RefreshError` / `TransportError`, and `OSError` raise `DataSheetStoreError` with SLP-readable text ("no connection to Google Drive", "not signed in to Google; press Import to sign in", "Google Drive refused the request (<status>)"), chained with `from e` (DI rule 5).
    - The cell payload maps `CellValue.text` → `{"userEnteredValue": {"stringValue": text}}`, `number` → `{"numberValue": number}`, and empty → `{}`.
- [X] T012 [US1] Update `therepy_sessions/interpretation/importing/sheet_import_batch.py` per contracts/interpretation-and-import.md § `sheet_import_batch.py` (depends on T003, T007):
  - Add the constructor parameter `data_sheet_store: DataSheetStore` (before `stat_mtime_ns`).
  - `FailureReason` gains `MISSING_DATE` and `SAVE_FAILED`, with the messages from the contract's table added to `_FAILURE_MESSAGES`.
  - `SheetOutcome` gains `saved: SavedDataSheet | None = None`.
  - In `_interpret`, after interpretation:
    1. Call `data_sheet.use_student_key(student.student_key)`.
    2. Raise `_SheetFailed(MISSING_DATE, ...)` if `not data_sheet.date.strip()`.
    3. Call `saved = self._data_sheet_store.save(data_sheet)`. Any exception raises `_SheetFailed(SAVE_FAILED, student_key=..., template_name=..., detail=str(e)) from e`.
  - The success outcome carries `saved=saved`, with `message` set to `f"Saved to {saved.location_name}"` or `f"Already saved in {saved.location_name}"`.
  - Update the module docstring: the batch now saves through the injected store.
- [X] T013 [US1] Update `therepy_sessions/interpretation/importing/import_window.py` per contracts/interpretation-and-import.md § `ImportWindow` (depends on T012). The new signature is `(master, batch, data_sheet_store: DataSheetStore, check_records_readable, open_url: Callable[[str], None], on_back, on_exit)`.
  - Remove `on_sheet_interpreted` and its call in `_poll`.
  - **Worker**: in `_work`, first post `("preparing",)` and call `self._data_sheet_store.prepare()`. On an exception, post `("prepare_failed", e)` followed by `("done", False)` and return.
  - **`_poll`**: `"preparing"` sets the progress label to "Connecting to Google Drive…". `"prepare_failed"` calls `error_handling.throw(error, "Cannot start the import")`.
  - **Status indicator (FR-003a)**:
    - `_STATUS_LABELS` becomes `✓ Succeeded` / `✗ Failed` / `○ Not imported`, and "Importing…" becomes `… Importing`.
    - Add Treeview tags `succeeded`, `failed`, `not_imported`, and `importing`, each with a foreground color readable in sv-ttk light and dark (e.g. green `#2e9d4f`, red `#d64545`, and the default for the rest).
    - Set the row's tag in `_show_outcome` and `_show_started`.
  - **Open (FR-003b)**:
    - Add an **Open** button beside Remove Selected. `_refresh_controls` enables it only when exactly one selected row's outcome is `SUCCEEDED` with `saved` set, and no run is active.
    - Bind `<Double-1>` on the tree to the same action.
    - The action calls `self._open_url(outcome.saved.location_url)`. Look up the outcome from `self._batch.files`.
- [X] T014 [US1] Wire the store in `therepy_sessions/program.py` per contracts/interpretation-and-import.md § `program.py` (depends on T001, T011, T013):
  - Add lazy `inject_sheets_service` / `inject_drive_service`, sharing one `load_google_credentials()` result under a `threading.Lock`, mirroring `inject_textract_client`.
  - In `open_import_path`, build `data_sheet_store: DataSheetStore = GoogleDriveDataSheetStore(inject_drive_service, inject_sheets_service)` per visit, and pass it to `SheetImportBatch(..., data_sheet_store=data_sheet_store)` and to `ImportWindow(..., data_sheet_store, check_records_readable, open_url=webbrowser.open, ...)`.
  - Remove the "Printing stands in for the Storage step" lambda.
- [X] T015 [P] [US1] Amend `docs/domain/glossary.md` (Principle II: in the same change as the code that introduces the terms):
  - Add **Data Sheet Store** (`DataSheetStore`), **Template Structure**, **Student Session Workbook** (`GoogleDriveDataSheetStore` writes it; replace the **Session Sheet** row), **Session Tab**, **Session Moment** (`SessionMoment`), **Workbook Layout Order** (`WorkbookLayout`), and **Therapy Data Folder**.
  - Update the "Pipeline in one line" Storage step to "save to the student's Student Session Workbook through the Data Sheet Store".
- [X] T016 [P] [US1] Amend `docs/conventions/architecture/layers.md`:
  - Rule 1 says `StudentDataSheet` carries the template it was interpreted with, and that Storage reads the template only through the sheet.
  - Rule 9 (or a new rule 10) says `interpretation/importing/` reaches storage only through the injected `DataSheetStore` port in `interpretation/data_sheet_store.py`, and that implementations live in `storage/`.
  - Update the `storage/` line in the package diagram.
- [X] T017 [P] [US1] Amend `docs/conventions/architecture/dependency-injection.md`:
  - Rule 1 names `create_sheets_service` / `create_drive_service` / `load_google_credentials`.
  - Rule 2's example becomes the store's providers instead of `create_therapy_session_sheet`.
  - Rule 4 mentions `SLP_GOOGLE_CLIENT_SECRET_FILE`, read inside `load_google_credentials()`.
  - Rule 6 says `ImportWindow` and `SheetImportBatch` receive the same `DataSheetStore` (one per Import visit, built in `program.py`), the window also receives `open_url`, and the Google services are built lazily on the first Import press.
- [X] T018 [P] [US1] Amend `docs/conventions/architecture/interpreters.md`:
  - The Interpreter row of "Adding a new interpreter type" requires `section_keys()` (and `section_kind` if the class is renamed).
  - The diagram shows the sheet carrying its template.
  - Note that `section_keys` feeds the Template Structure, so changing it changes which workbook a template's sessions go to.
- [X] T019 [US1] Update `.specify/memory/constitution.md` (depends on T015–T018):
  - Add a Sync Impact Report at the top (1.5.0 → 1.6.0, MINOR) listing T015–T018. Move the 1.5.0 report under "Previous report".
  - Set **Version** 1.6.0 and **Last Amended** to the date of the change.
- [X] T020 [US1] Offline check (quickstart V3, US1 rows). In a scratch script:
  - Run `SheetImportBatch` with an in-memory fake `DataSheetStore`. Confirm:
    - a blank Date → `MISSING_DATE`, and `save` is not called
    - `save` raises → `SAVE_FAILED`, the message starts "Could not save to Google Drive", and the next pass reuses the Import
    - a ` ag ` sheet reaches the store with `student_key == "AG"` and `template` set
  - Run `GoogleDriveDataSheetStore` with fake Drive and Sheets services that record requests. Confirm:
    - the first save creates one labeled file plus one `batchUpdate`
    - a failing batch deletes the new file and raises `DataSheetStoreError`
    - with a fake search that returns nothing right after a create, a second `AG` save reuses the cached workbook, and no second file is created
    - when two files match, the first-listed one is used
    - two blank-time sheets with the same date make `9/14/2026` and `9/14/2026 2`
- [ ] T021 [US1] Live check (quickstart V4) on a test Google account with synthetic `AG` sheets:
  - Sign-in opens while "Connecting to Google Drive…" shows.
  - The workbook `AG - <template>` and its tab appear in `SLP Therepy Data/Current Year`.
  - The row shows ✓ Succeeded with "Saved to …".
  - Open and double-click open the tab.
  - Two `AG` sheets with different dates, imported in the same batch, add two tabs to one workbook.

**Checkpoint**: Importing saves to Drive end to end, and the docs and constitution match
the code. The MVP is shippable.

---

## Phase 4: User Story 2 - Every imported value is in the tab, and nothing else (Priority: P1)

**Goal**: Tabs hold exactly the interpreted values in the clarified layout:

- numbers saved as numbers only when typed `INT`
- blanks kept in place
- table blocks labeled by section title
- no choices, types, ids, or template details

**Independent Test**: spec US2. Import a sheet whose template has a form section, a
table with choice columns, and an `INT` running tally. Every value is present, tally
counts are numeric, and no choice lists or type names appear. See quickstart V2 and V4.

### Implementation for User Story 2

- [X] T022 [US2] Add typed cells to `therepy_sessions/storage/session_layout.py` per research R7:
  - `CellKind(Enum)` (`NUMBER`, `TEXT`).
  - `CELL_KIND_BY_TYPE: dict[DataSheetScalarType, CellKind]`, with `INT` → `NUMBER` and every other member → `TEXT`.
  - `cell_for(value: DataSheetScalarDto | str | None) -> CellValue`:
    - `None` or blank → empty
    - a raw `str` → text
    - a DTO whose kind is `NUMBER` and whose `value.strip()` matches `^[+-]?\d+$` → `number=int(...)`
    - anything else → `text=str(value.value)`
  - Docstring: this is the single place a later per-field configuration plugs in (FR-024b).
- [X] T023 [US2] Refine `session_rows` in `therepy_sessions/storage/session_layout.py` per research R9 and FR-020–FR-025 (depends on T022):
  - Build every cell through `cell_for`. Header values are text.
  - Form rows come from the layout's `SimpleFormInterpreter`-kind sections in layout order. A key missing from `sheet.scalars` gives an empty B cell.
  - Table blocks come from the layout's table-producing sections in order. For each `sheet.tables` entry whose `section_id` maps to that section, write: a title row (the section title, when non-empty), a header row of the layout section's keys, data rows with each cell taken by key from the row dict (a missing key → empty), then one blank row between blocks.
  - Never emit `choice_options`, scalar types, `section_id`, the template name, or the description (FR-023).
  - To map a sheet section to a layout section, match `(kind, title, tuple(sorted(keys)))`, the same key form `TemplateShape.structure_identity()` uses (T008), against the next unused layout section. Match the sheet's tables to sheet sections through `shape_of(sheet.template)` section ids.
- [ ] T024 [US2] Offline check (quickstart V2 `cell_for` and `session_rows` rows). On a sheet interpreted from a synthetic Import with a form section, a table, and an `INT` tally:
  - `INT "7"` → number; `INT "7a"` → text; `TEXT "007"` → text; raw str `"9/14"` → text; `""` → empty
  - rows match the layout, and no choice or type strings appear in any cell

  Then re-run T021's live import and inspect the tab.

**Checkpoint**: Tab contents meet FR-020–FR-025.

---

## Phase 5: User Story 3 - The workbook follows the template's structure, not its name (Priority: P2)

**Goal**: Same-structure templates (renamed, copied, or reordered) keep saving to the
original workbook, in its original layout order and under its original name.

- A different structure starts a new workbook.
- Renamed workbooks are still found. Trashed or moved ones are not.
- A copy with the newest modification wins.
- A workbook left empty by a failed create is completed by the next save.

**Independent Test**: spec US3 and quickstart V5 steps 1–5.

### Implementation for User Story 3

- [X] T025 [US3] In `therepy_sessions/storage/google_drive_data_sheet_store.py`, read the workbook's own layout on every save to an existing workbook (FR-025a), and repair a workbook left by a failed create (spec edge case, FR-019):
  - Request `developerMetadata` in the `spreadsheets().get` fields.
  - Take the `slpWorkbookLayout` entry through `WorkbookLayout.from_json`. Fall back to `WorkbookLayout.from_shape(shape)` when it is missing or unreadable, and print the reason to the console.
  - Pass that layout to `session_rows`.
  - Run one `values().batchGet(ranges=[f"'{title}'!A1:B6" for each tab], valueRenderOption="FORMATTED_VALUE")`, escaping `'` in titles as `''`. T029 reuses this result.
  - **Repair**, only when the `slpWorkbookLayout` entry is missing: add `createDeveloperMetadata` with the fallback layout to the save's `batchUpdate`, plus a `deleteSheet` (after the `addSheet`) for every tab whose `A1:B6` is empty. Leave those tabs out of the existing titles. A workbook that has its layout is never repaired, so an empty tab the SLP added stays.
  - Never rename the workbook (FR-011).
- [X] T026 [US3] Offline check (quickstart V3 store rows):
  - A fake template with reordered columns writes the layout's original column order.
  - A workbook with no layout metadata and an empty default tab gets `createDeveloperMetadata` and a `deleteSheet` of that tab in the save's `batchUpdate`.
  - A workbook with its layout metadata and an empty tab gets neither.
- [ ] T027 [US3] Live check (quickstart V5, steps 1–5): a reordered copy reuses the workbook, a renamed column creates a new workbook, a renamed workbook is still found, and a trashed workbook leads to a new one.

**Checkpoint**: Workbook selection meets FR-007–FR-013b and FR-025a.

---

## Phase 6: User Story 4 - Several sessions in a day, and re-imports (Priority: P3)

**Goal**:

- Sessions with the same Date and Time IN are recognized as already saved, and nothing
  is written.
- Every new tab lands in newest-first order.

**Depends on US3**: T029 reuses the per-tab `batchGet` that T025 adds, so US4 is built
and tested after US3. This is intended: both stories read the same tab headers, and one
read per save keeps the Google calls per sheet low (SC-006).

**Independent Test**: spec US4 and quickstart V6. Two times on one date make two tabs.
A re-import shows "Already saved". Two blank-time sheets make `<date>` and `<date> 2`.
Tabs are newest first.

### Implementation for User Story 4

- [X] T028 [P] [US4] Add moment matching and ordering to `therepy_sessions/storage/session_layout.py` per research R8:
  - `SessionMoment.matches(other)`: `False` if either `time_text.strip()` is blank. Otherwise compare dates and times with `casefold().strip()`.
  - `SessionMoment.sort_key -> tuple[bool, date, bool, time]`.
    - The date is parsed with `%m/%d/%Y`, `%m/%d/%y`, `%m-%d-%Y`, or `%m-%d-%y`.
    - The time is parsed after upper-casing and removing dots, with `%I:%M %p`, `%I:%M%p`, `%I %p`, or `%H:%M`.
    - Use `date.min` / `time.min` with a `False` flag when a value can't be parsed.
  - `moment_from_rows(rows: list[list[str]]) -> SessionMoment | None`: find the `Date` and `Time IN` labels in column A of the first 6 rows. Return `None` if `Date` is absent.
  - `insert_index(new, existing)`: the index of the first existing tab whose key ≤ the new key, treating `None` as the oldest. Return `len(existing)` if there is none (FR-018a).
- [X] T029 [US4] Use them in `GoogleDriveDataSheetStore.save` for existing workbooks (depends on T025, T028):
  1. Get each tab's `moment_from_rows` from T025's `batchGet` result.
  2. If `moment_of(sheet)` matches any tab, return `SavedDataSheet(..., already_saved=True)` for that tab's `sheetId` and title, and write nothing (FR-016a).
  3. Otherwise the title is `unique_tab_name(tab_base_name(moment), existing titles)` as before, and the `index` is `insert_index(moment, moments in tab index order)` instead of the tab count.

  For new workbooks the first tab keeps `index=0`.
- [X] T030 [US4] Offline check (quickstart V2 ordering rows, V3 duplicate rows):
  - the `insert_index` cases from V2
  - the same date and time with different values → `already_saved` with no `batchUpdate`
  - a renamed tab with matching values is still detected as a duplicate
- [ ] T031 [US4] Live check (quickstart V6): re-importing the V4 photo shows "Already saved in …" with no new tab, and two blank-time sheets create `<date>` and `<date> 2` after the timed tab for that date.

**Checkpoint**: All four user stories work independently.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across the feature.

- [ ] T032 Run the remaining quickstart checks:
  - V7: Drive offline at Import press → "Cannot start the import" with no Textract call. Network lost mid-batch → ✗ Failed rows that save on retry without a duplicate tab.
  - V8: with a cached sign-in, `prepare()` and the 10 `save` calls take 60 seconds or less in total on a typical school network (SC-006).
  - V9: privacy — `git status` shows no token, secret, or synthetic output staged, and no log file exists.
  - Confirm `grep -rn "storage\|google" therepy_sessions/interpretation --include='*.py'` shows no imports of `storage/` or Google packages.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (T001–T002)**: no dependencies. T001 is needed only by T014.
- **Foundational (T003–T009)**: T004 → T005 → T008. T006 → T007. T003 is independent.
  T009 needs all of them. It blocks every story.
- **US1 (T010–T021)**: needs Foundational. T010 → T011. T012 → T013. T011 + T013 + T001 →
  T014. The doc tasks T015–T018 can start any time after Foundational; T019 follows
  them. T014 + T019 → T020 → T021.
- **US2 (T022–T024)**: needs US1's `session_layout.py` and the store (T010, T011).
- **US3 (T025–T027)**: needs US1's store (T011). It can run alongside US2, except that
  T025 and T023 both touch how `session_rows` is called; do T023 first if both are in
  flight.
- **US4 (T028–T031)**: needs US1 (T010, T011) and T025, whose `batchGet` it reuses.
  T028 edits `session_layout.py`, so sequence it after T022/T023 if US2 is in flight.
- **Polish (T032)**: runs last.

### User story dependencies

- US1 is the MVP and the base for the others: it creates `session_layout.py`,
  `GoogleDriveDataSheetStore`, and the doc amendments.
- US2 and US3 each extend US1 and are independent of each other in behavior. US4 builds
  on T025 from US3. They share two files (`session_layout.py`,
  `google_drive_data_sheet_store.py`), so run them one after another unless separate
  people coordinate those edits.

### Parallel opportunities

- T001 ∥ T002.
- T003 ∥ T004 ∥ T006 (different files). Then T005 ∥ T007, then T008.
- In US1: T010 ∥ T012 (different files), then T011 ∥ T013. T015 ∥ T016 ∥ T017 ∥ T018
  alongside the code tasks.
- T028 (pure functions) can be written while T025 is in progress.

## Parallel Example: User Story 1

```text
# After Foundational is complete:
Task: "T010 [US1] Create storage/session_layout.py (US1 subset)"
Task: "T012 [US1] Add data_sheet_store, MISSING_DATE, SAVE_FAILED to sheet_import_batch.py"
Task: "T015–T018 [US1] Amend glossary.md, layers.md, dependency-injection.md, interpreters.md"

# Then:
Task: "T011 [US1] Create storage/google_drive_data_sheet_store.py"
Task: "T013 [US1] Update import_window.py (prepare on worker, status, Open)"
```

## Implementation Strategy

### MVP first (User Story 1)

1. Phase 1 Setup → Phase 2 Foundational (T009 confirms nothing regressed).
2. Phase 3 (US1), including the doc amendments and the constitution bump → T020
   offline, then T021 live.
3. Stop and validate: imports now land in Drive. This alone replaces the debug print,
   and it can be merged.

### Incremental delivery

1. **+US2**: exact contents and types. Re-run the V2 and V4 checks.
2. **+US3**: layout order and workbook repair. Run V5.
3. **+US4**: duplicates and ordering. Run V6.
4. **Polish**: V7, V8, and V9.

Each step leaves the app working, with two known gaps until later stories close them:

- Before US3, a workbook left empty by a failed create whose cleanup also failed gets
  session tabs added, but keeps its empty default tab (FR-019). T025 repairs it.
- Before US4, re-importing a sheet with a Time IN adds a second tab named
  `<Date> <Time IN> 2` at the end of the workbook. US4 recognizes it as already saved
  instead and places new tabs newest first.

---

## Phase 8: Convergence

- [ ] T033 CRITICAL: Fully annotate the public members this feature changed (`image_to_text(image_path: str, inject_textract_client: Callable[[], Any]) -> StudentDataSheetImport` in `therepy_sessions/collection/images/aws_image_collection.py`, `SimpleFormInterpreter.__init__(self, id: str, title: str, fields: dict[str, FieldConfiguration]) -> None` in `therepy_sessions/interpretation/interpreter_types/simple_form_interpreter.py`, and `-> None` on `TableInterpreter.__init__` in `therepy_sessions/interpretation/interpreter_types/table_interpreter.py`) per Constitution VI (contradicts)
- [ ] T034 Give the Google sign-in a timeout in `therepy_sessions/clients/google_service.py` (`run_local_server(timeout_seconds=...)`) so a closed or abandoned sign-in tab ends `prepare()` with an error, and translate it in `GoogleDriveDataSheetStore._translate_errors` to "Google sign-in was cancelled or timed out; press Import to try again", so the import does not start and the SLP is told why per FR-006a (partial)
- [ ] T035 Record matching tables to template sections by title (Import `table_titles` from Textract `TABLE_TITLE`, `consumes_tables`, `StudentDataSheetInterpreter._assign_tables`, interpreters rule 9) in this feature's `spec.md` (a functional requirement and edge cases) and `plan.md` (a research decision), or move it to its own feature, per spec/plan scope (unrequested)
