---

description: "Task list for the Import Data Sheets feature"
---

# Tasks: Import Data Sheets

**Input**: Design documents from `/specs/003-import-data-sheets/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/import-batch.md](contracts/import-batch.md),
[contracts/ui-windows.md](contracts/ui-windows.md), [quickstart.md](quickstart.md)

**Tests**: No automated tests. The spec doesn't ask for them. Research R11 makes
verification an offline scratch-script check of `SheetImportBatch` plus the manual
[quickstart.md](quickstart.md). Scratch scripts are not committed.

**Organization**: Tasks are grouped by user story. US1 (P1) delivers a working
one-round import with successes printed. US2 (P2) adds list editing. US3 (P3) adds the
exact failure reasons, reuse of readings on retry, and changed-file detection. Cancel
(FR-016a) is in the final phase because it touches the running state that all stories
share.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US3 from spec.md

## Path Conventions

- All code is under `therepy_sessions/`. Modules import each other by package path from
  that directory (e.g. `from interpretation.importing.sheet_import_batch import SheetImportBatch`).
- Every public function, method, attribute, and `__init__` added or changed is fully
  annotated per [type-declarations.md](../../docs/conventions/architecture/type-declarations.md).
  Injected collaborators and callbacks are stored as `_`-prefixed attributes.
- `interpretation/importing/sheet_import_batch.py` MUST NOT import `tkinter`,
  `collection.images`, `clients`, or `storage`. It may import
  `collection.collection_headers.StudentDataSheetImport`, and from `students/` only
  `students.student_store.StudentStore` and `students.student` (research R2).
- Only the Tk thread touches widgets or calls `on_sheet_interpreted`. Only the worker
  thread calls `process_file` (research R3).
- Use only placeholder keys (`AG`, `JA`, `BK`, `ZZ`, `QQ`), the synthetic images in
  `therepy_sessions/sample_data/`, and scratch copies of the JSON files (Principle I).

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Confirm the starting point: `therepy_sessions/interpretation/importing/` contains only the placeholder `import_window.py`. It has no `__init__.py`, like the rest of `interpretation/` (imported as namespace packages), so none is added. `therepy_sessions/program.py` launches with `program.py <templates.json> <students.json>`. No dependency changes are needed (plan Technical Context).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix shared state, add the templates-file check, create the batch's types, and amend the docs and constitution that allow the new imports, so no code lands ahead of the rules it relies on. Every story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 [P] In `therepy_sessions/interpretation/student_data_sheet.py`, delete the class attributes `_student_key`, `_student_goal`, `_date`, `_time_in`, `_time_out`, `_measure`, `_tables`, and `_scalars` from `StudentDataSheet`. Add `class DataSheetTable(TypedDict)` with `columns: list[object]` (comment: a `ColumnDefinition` from `TableInterpreter`, or a `str` from `RunningTallyInterpreter`) and `data: list[dict[str, DataSheetScalarDto]]` (type-declarations rule 4). Create `self._tables: list[DataSheetTable] = []` and `self._scalars: dict[str, DataSheetScalarDto | str] = {}` in `__init__`, beside the existing assignments (research R6, interpreters rule 3). Annotate `__init__` (all parameters `str`, `-> None`), each property's return type (`tables -> list[DataSheetTable]`), `register_table(self, table: DataSheetTable) -> None`, `register_scalar(self, scalar_name: str, scalar_dto: DataSheetScalarDto | str) -> None` (comment: `# SimpleFormInterpreter stores the raw form text`; the `scalars` property returns, and `_scalars` holds, `dict[str, DataSheetScalarDto | str]`), and `debug(self) -> None`. Do not change `debug()`'s output format (FR-011).
- [ ] T003 [P] In `therepy_sessions/interpretation/template_store.py`, add `class UnreadableTemplatesError(Exception)`. Its `__init__(self, file_path: str, reason: str) -> None` builds the message `Could not read templates from <file_path>: <reason>` and stores `self.file_path: str`. Add `TemplateStore.check_readable(self) -> None`: if `self.storage_file_path` exists, open it with UTF-8 and `json.load` it. Raise `UnreadableTemplatesError` on `json.JSONDecodeError`, on `OSError`, or if the top-level value is not a list. Return quietly if the file is missing. Do not change `_load_templates_from_file` or any other method (research R7).
- [ ] T004 [P] Create `therepy_sessions/interpretation/importing/sheet_import_batch.py` with the types from [contracts/import-batch.md](contracts/import-batch.md): the `SheetStatus` and `FailureReason` enums; the `SheetOutcome`, `ProcessedSheet`, and `ListTotals` `NamedTuple`s (with the defaults shown); `SUPPORTED_IMAGE_EXTENSIONS: tuple[str, ...]`; and a `@dataclass class SelectedFile` with `path: str`, `identity: str`, `outcome: SheetOutcome = SheetOutcome(SheetStatus.NOT_IMPORTED)`, `sheet_import: StudentDataSheetImport | None = None`, and `read_mtime_ns: int | None = None` ([data-model.md](data-model.md)). Add a module docstring stating the import rules and that this module has no Tkinter or I/O of its own beyond `stat`. Add the private helpers `_file_identity(path: str) -> str` (`os.path.normcase(os.path.realpath(path))`), `_is_supported_image(path: str) -> bool` (case-folded extension in `SUPPORTED_IMAGE_EXTENSIONS`), and `_os_stat_mtime_ns(path: str) -> int`.
- [ ] T005 [P] In `docs/conventions/architecture/layers.md`, add rule 9: `interpretation/importing/` may use `students/` only through an injected `StudentStore` and the `Student` record and its exceptions. It MUST NOT import student windows, and it receives Imports only through an injected sheet reader, never by importing `collection.images` (research R2).
- [ ] T006 [P] In `docs/conventions/architecture/dependency-injection.md`, extend rule 6 to say that `ImportWindow` and `SheetImportBatch` receive the `StudentStore`, a template lookup, a sheet reader wrapping `image_to_text`, and a result sink through their constructors. Also say that `program.py` builds the Textract client lazily on first use (research R8).
- [ ] T007 [P] In `docs/domain/glossary.md` *Software concepts*, add four rows (Principle II), matching the spec's Key Entities:
  - **Selected File** (`SelectedFile`): an image in the Import window's list, kept with its Import while the window is open.
  - **Import Batch** (`SheetImportBatch`): the list of Selected Files and the rules for importing them.
  - **Import Run**: the Selected Files processed by one press of Import (those not yet succeeded).
  - **Sheet Outcome** (`SheetOutcome`): one file's result, *not imported*, *succeeded*, or *failed* with a reason.
- [ ] T008 Amend `.specify/memory/constitution.md` (after T005–T007). Add a Sync Impact Report for 1.3.0 → 1.4.0 (MINOR: new layer rule 9 and an expanded injection rule 6 in referenced docs, plus glossary additions), and move the 1.3.0 report under "Previous report". Bump **Version** to 1.4.0 and **Last Amended** to the change date. Do not change any principle text.

**Checkpoint**: `cd therepy_sessions && ../.venv/bin/python3 -c "import interpretation.importing.sheet_import_batch, interpretation.template_store, interpretation.student_data_sheet"` succeeds.

---

## Phase 3: User Story 1 - Import a batch of sheets from several students (Priority: P1) 🎯 MVP

**Goal**: The SLP picks several images in one round, presses Import, and each sheet is interpreted with its own student's Current Template. Each success is printed with `debug()`, and every row shows its outcome.

**Independent Test**: Quickstart V4. Set up two students with different Current Templates matching two sample images. Add both in one picker round and press Import. Each row shows **Succeeded** with its own Student Key and template name. The console shows one `Data Sheet` block per file, in list order, and each block has only its own tables. The window repaints throughout.

### Implementation for User Story 1

- [ ] T009 [US1] In `therepy_sessions/interpretation/importing/sheet_import_batch.py`, add `class SheetImportBatch` with the constructor from [contracts/import-batch.md](contracts/import-batch.md) (`read_sheet`, `student_store`, `get_template`, `stat_mtime_ns=_os_stat_mtime_ns`). Store each as a `_`-prefixed attribute. Keep `self._files: list[SelectedFile] = []`. Implement:
  - `files` (returns `list(self._files)`).
  - `add_files(paths: Sequence[str]) -> list[SelectedFile]`: appends supported paths whose identity is not yet listed, in order, and returns the ones added.
  - `files_to_process() -> list[SelectedFile]`: files whose status is not `SUCCEEDED`, in list order.
  - `totals() -> ListTotals`.
  - A private `_find(identity: str) -> SelectedFile` that raises `KeyError` for an unknown identity.
- [ ] T010 [US1] In the same file, implement `SheetImportBatch.process_file(self, identity: str) -> ProcessedSheet`, following the data-model "Processing one file" steps. For now, read every time: call `self._stat_mtime_ns(path)`, then `self._read_sheet(path)`, and save `sheet_import` and `read_mtime_ns`. Then:
  - Take the key as `form_data.get("Student Key", "").strip()`.
  - Look it up with `self._student_store.get_student(key)`.
  - Take `current_template_id`, call `self._get_template(id)` (fresh on every call; never cached, FR-010), and run `template.to_data_sheet_interpreter().interpret_student_data_sheet(sheet_import)`.

  On success, set the outcome `SheetOutcome(SUCCEEDED, student_key=key, template_name=template.name)` and return it together with the data sheet. Wrap the steps so that **no exception escapes**: any exception prints its traceback with `traceback.print_exc()` and becomes a `FAILED` outcome with `message=str(e)`, `failure_reason=None` for now (US3 refines this), and `data_sheet=None` (FR-012, FR-014). Store the outcome on the `SelectedFile`.
- [ ] T011 [US1] Rewrite `therepy_sessions/interpretation/importing/import_window.py` per [contracts/ui-windows.md](contracts/ui-windows.md):
  - Constructor `(master, batch, check_records_readable, on_sheet_interpreted, on_back, on_exit)`. Keep the title "Import & Interpret Student Data Sheets" and `WM_DELETE_WINDOW → on_exit` (FR-017).
  - Layout per research R12: a padded `ttk.Frame` holding a `ttk.Treeview` (`show="headings"`, `selectmode="extended"`, columns File/Status/Student Key/Template/Details) with a vertical scrollbar, a button row (**Add Files…**, **Remove Selected**, **Import**, **Cancel**, **Back**), a determinate `ttk.Progressbar`, a progress label, and a summary label.
  - **Add Files…** calls `filedialog.askopenfilenames(parent=self._window, title="Add data sheet images", filetypes=[("Images", "*.png *.PNG *.jpg *.JPG *.jpeg *.JPEG *.tif *.TIF *.tiff *.TIFF")])`, with no "All files" entry (R10). It passes the result to `batch.add_files` and inserts one row per added file, using `iid=identity`, File = `os.path.basename(path)`, Status **Not imported**, and Details = the full path. An empty result does nothing.
  - Build **Remove Selected** and **Cancel**, but leave Remove always disabled and Cancel hidden (`pack_forget`/`grid_remove`). US2 and the final phase wire them.
  - Add a `_refresh_controls()` method that applies the data-model *Window states* table: Import on only when not running and `batch.files_to_process()` is non-empty (FR-007); Add and Back off while running (FR-016b).
- [ ] T012 [US1] In `therepy_sessions/interpretation/importing/import_window.py`, implement the run (research R3):
  1. **Import** first calls `self._check_records_readable()`. On any exception, call `error_handling.throw(e, "Cannot start the import")` and return.
  2. Otherwise take `ids = [f.identity for f in batch.files_to_process()]`, create `self._events: queue.Queue` and `self._stop = threading.Event()`, reset the run counters `self._run_succeeded = 0` and `self._run_failed = 0`, set running, and call `_refresh_controls()`.
  3. Start `threading.Thread(target=self._work, args=(ids,), daemon=True)`. The thread posts `("started", id)` and then `("finished", id, processed)` for each file, checks `self._stop.is_set()` before each file, and finally posts `("done", cancelled)`.
  4. Poll with `self._window.after(100, self._poll)`. Stop polling once `done` is handled, or if `self._window.winfo_exists()` is false.
  5. On `started`: set that row's Status to **Importing…** and update the progress bar and "Importing n of m…".
  6. On `finished`: add 1 to `_run_succeeded` or `_run_failed` according to `processed.outcome.status`, then update that row (Status **Succeeded**/**Failed**, Student Key, Template, Details = `outcome.message`), and if `processed.data_sheet` is set, call `self._on_sheet_interpreted(processed.data_sheet)` (FR-011, so printing happens on the Tk thread and in order).
  7. On `done`: clear running, hide the progress bar, set the summary to `This run: {s} succeeded, {f} failed · Whole list: {S} succeeded, {F} failed, {N} not imported`, with `{s}`/`{f}` from the run counters and `{S}`/`{F}`/`{N}` from `batch.totals()` (FR-015), and call `_refresh_controls()`.
- [ ] T013 [US1] In `therepy_sessions/program.py`, implement the wiring from [contracts/ui-windows.md](contracts/ui-windows.md):
  - Import `threading`, `Any`, `construct_textract_client` from `clients.aws_clients`, `image_to_text` from `collection.images.aws_image_collection`, and `SheetImportBatch`.
  - Inside `main()`, add a lazily built, lock-guarded `inject_textract_client() -> Any` (boto3 Textract client; built on first call only, R8) and `check_records_readable() -> None` (calls `student_store.list_students()` then `template_store.check_readable()`).
  - Rewrite `open_import_path()` to pass a fresh `SheetImportBatch(read_sheet=lambda path: image_to_text(path, inject_textract_client), student_store=student_store, get_template=template_store.get_template_by_id)`, `check_records_readable`, and `on_sheet_interpreted=lambda sheet: sheet.debug()`, keeping the existing `on_back`/`on_exit`.
  - Nothing AWS-related may run at launch.
- [ ] T014 [US1] Run quickstart V3 steps 1–2, 6–7 (window opens empty with Import off, picker offers only images, Back resets the list, ✕ exits), then V4 (mixed batch, console blocks in order, each with only its own tables, window stays draggable). Fix any problems found in `therepy_sessions/interpretation/importing/import_window.py` or `therepy_sessions/program.py`.

**Checkpoint**: User Story 1 works end to end. This is the MVP.

---

## Phase 4: User Story 2 - Build and adjust the file list before importing (Priority: P2)

**Goal**: The SLP adds files over several rounds without duplicates, and removes any of them before importing.

**Independent Test**: Quickstart V3 steps 3–5. Add two files, then add a third plus one already listed: three rows. Cancel the picker: no change. Remove one: two rows remain, and only those two are processed on Import. Remove all: Import is off.

### Implementation for User Story 2

- [ ] T015 [US2] In `therepy_sessions/interpretation/importing/sheet_import_batch.py`, implement `SheetImportBatch.remove_files(self, identities: Collection[str]) -> None`. It removes the matching `SelectedFile`s, which drops their saved Imports with them, and ignores unknown identities ([contracts/import-batch.md](contracts/import-batch.md)).
- [ ] T016 [US2] In `therepy_sessions/interpretation/importing/import_window.py`, wire **Remove Selected**: call `batch.remove_files(self._tree.selection())`, delete those rows, and call `_refresh_controls()`. Bind `<<TreeviewSelect>>` to `_refresh_controls()`. Extend `_refresh_controls()` so Remove is on only when not running and at least one row is selected (FR-005, FR-016b). Clear the summary label when the list changes, so it never describes files that are gone.
- [ ] T017 [US2] In a scratch script (not committed), check `add_files` with `a.png`, `a.png`, `./a.png`, `b.PDF`, and `c.JPG`: two files are added (`a.png` once, `c.JPG`), and `b.PDF` is skipped (FR-002, FR-004). Check that `remove_files` with one known id and one unknown id removes only the known file. Then run quickstart V3 steps 3–5 in the app.

**Checkpoint**: User Stories 1 and 2 both work.

---

## Phase 5: User Story 3 - One bad sheet does not stop the batch (Priority: P3)

**Goal**: Each failing sheet shows a specific reason that names the fix. The other sheets still succeed. A retry reuses earlier readings, except for files that changed on disk.

**Independent Test**: Quickstart V1 and V5. In a batch with one valid sheet, one whose key matches no student, and one whose student has no Current Template, the valid sheet succeeds and prints. The other two fail with the `UNKNOWN_STUDENT` and `NO_CURRENT_TEMPLATE` messages. After the setup is fixed, pressing Import again re-runs only the failed rows and does not call Textract again for them.

### Implementation for User Story 3

- [ ] T018 [US3] In `therepy_sessions/interpretation/importing/sheet_import_batch.py`, replace T010's catch-all with the exact classification and messages in [research.md R5](research.md#r5-failure-reasons-and-messages-fr-013-sc-004):
  - `stat` failure, or `FileNotFoundError`/`OSError` from `read_sheet` → `FILE_UNREADABLE`. Any other `read_sheet` exception → `READING_FAILED`.
  - A blank key → `NO_STUDENT_KEY`.
  - `get_student` returning `None` → `UNKNOWN_STUDENT`. `UnreadableStudentRecordsError` → `STUDENT_RECORDS_UNREADABLE`.
  - `current_template_id is None` → `NO_CURRENT_TEMPLATE`.
  - `get_template` returning `None` or raising → `TEMPLATE_MISSING`.
  - An exception from interpretation → `TEMPLATE_MISMATCH`, with `template_name` set. A `KeyError` whose key is a header label (`Date`, `Time IN`, `Time OUT`, `Goal`, `Measure`) becomes the detail `the sheet has no '<label>' field`; any other exception, including other `KeyError`s, uses `str(e)`.

  Put each message pattern in one private function or dict so the wording lives in a single place. Set `student_key` on the outcome as soon as it is known. Messages name students only by Student Key (FR-019). Keep printing the traceback to stderr for each failure. No partial `data_sheet` is ever returned (FR-014).
- [ ] T019 [US3] In the same file, add reuse of readings to `process_file` (research R4, FR-008a):
  1. Always call `self._stat_mtime_ns(path)` first; if it fails → `FILE_UNREADABLE`.
  2. If `sheet_import` is set and `read_mtime_ns` equals the new value, reuse it and skip `read_sheet`.
  3. Otherwise call `read_sheet`, then store the Import and the mtime taken before the read.
  4. If the read fails, set `sheet_import = None` and `read_mtime_ns = None`.

  Succeeded files are never re-processed, because the window only passes in `files_to_process()`.
- [ ] T020 [P] [US3] Add synthetic Import fixtures under `therepy_sessions/sample_data/imports/`, copied from the synthetic sheet `therepy_sessions/sample_data/multiple_tables_named.png` and built for template id `4` ("Blah") in `therepy_sessions/sample_data/templates.json`. That template has a `SimpleFormInterpreter` for the field `Define tone`, and two `TableInterpreter`s with the columns `Sentence`, `Pitch`, `Speed`, `Body`.
  - **Base fixture** `ag_multiple_tables_named.json`: `form_data` has the labels `Student Key` (`AG`), `Date`, `Time IN`, `Time OUT`, `Goal`, `Measure` and `Define tone`, with the values printed on the sheet. `tables` holds the sheet's tables (*Differentiate Tone* and *Use Tone Accurately*), each with the header row `["Sentence", "Pitch", "Speed", "Body"]`, then `["I'm so excited!", "Y", "N", "N"]` and `["This is boring.", "N", "Y", "Y"]`. If one live `image_to_text` run of the image is available, use its `form_data` and `tables` as the base fixture, so the fixture matches what Textract really returns.
  - **Variants** of the base fixture, with one change each: a second `AG` sheet with different Y/N cells; key ` ag `; key `QQ`; key `BK`; key `ZZ`; no `Student Key`; `AG` with no `Date`; `AG` with the `Body` column removed from one table (a `TEMPLATE_MISMATCH` raised by the interpreter itself).

  Add `therepy_sessions/sample_data/imports/README.md` saying the files are synthetic copies of `multiple_tables_named.png` and how V1 loads them. In the V1 fake `StudentStore`, `AG` → `"4"`, `BK` → `None`, and `ZZ` → a deleted id.
- [ ] T021 [US3] Run quickstart V1 as a scratch script (not committed). It uses fakes for `read_sheet` (counting calls and returning the T020 fixtures), `StudentStore`, and `stat_mtime_ns`, and a scratch `TemplateStore` for `get_template`. Every row of the V1 table must hold, including:
  - a second pass that makes no new `read_sheet` calls for unchanged failed files;
  - a changed mtime that triggers exactly one new read;
  - two `AG` sheets interpreted one after the other: each data sheet has the same number of tables as when that sheet is interpreted alone, and neither includes the other's rows.

  Fix any failures in `therepy_sessions/interpretation/importing/sheet_import_batch.py`.
- [ ] T022 [US3] Run quickstart V2 (corrupt templates file → `UnreadableTemplatesError`), V5 (failures with fixes named, retry runs only non-succeeded rows, deleted file → "could not be opened"), and V7 (corrupt students file → error box, nothing runs).

**Checkpoint**: All three user stories work.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cancel, retiring the developer script, and final validation.

- [ ] T023 In `therepy_sessions/interpretation/importing/import_window.py`, wire **Cancel** (FR-016a):
  - Show it only while running.
  - On press, call `self._stop.set()`, change its text to **Cancelling…**, and disable it.
  - Pass the cancelled flag from `done` into the summary, adding ` Cancelled.`. Rows not reached keep **Not imported** and count as not imported in the whole-list totals.
  - Reset the button text when the run ends.

  Then run quickstart V6.
- [ ] T024 [P] Delete `therepy_sessions/program_interpret.py` (research R9). Search the repository (`grep -rn program_interpret --exclude-dir=.git`) and update every live reference outside `specs/001-*`/`specs/002-*`, which are historical records. Check `README.md` and `therepy_sessions/README.md` in particular.
- [ ] T025 Check Principle VI and the layer rules:
  - Every public member added or changed in `sheet_import_batch.py`, `import_window.py`, `student_data_sheet.py`, `template_store.py`, and `program.py` is annotated.
  - `grep -n "^import\|^from" therepy_sessions/interpretation/importing/sheet_import_batch.py` shows no `tkinter`, `clients`, `collection.images`, or `storage` import.
- [ ] T026 Run the full quickstart (V1–V8) once more, timing how long it takes to add 10 sheets from 3 students and start the import (SC-001: under 1 minute). Then confirm with `git status` that no real sheet images or Imports, credentials, or scratch scripts are staged (Principle I, FR-018). The only Imports staged should be the synthetic fixtures in `therepy_sessions/sample_data/imports/`, which use placeholder keys only.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: after Setup. Blocks all stories. T002–T007 touch different files and can run in parallel. T008 comes after T005–T007.
- **US1 (Phase 3)**: after Foundational. T009 → T010 (same file). T011 → T012 (same file). T013 needs T009 and T011. T014 needs all of them.
- **US2 (Phase 4)**: after US1, because it extends the same two files. T015 → T016 → T017.
- **US3 (Phase 5)**: after US1, and independent of US2 except for both editing `sheet_import_batch.py`. If doing both, finish US2's T015 first. T018 → T019 → T020 → T021 → T022.
- **Polish (Phase 6)**: T023 after US1. T024 can start any time after Foundational. T025 and T026 last.

### User Story Dependencies

- **US1 (P1)**: depends only on Foundational.
- **US2 (P2)**: builds on US1's window and batch, and can be tested on its own with quickstart V3.
- **US3 (P3)**: builds on US1's `process_file`, and can be tested on its own with quickstart V1/V5.

### Parallel Opportunities

- T002 ∥ T003 ∥ T004 ∥ T005 ∥ T006 ∥ T007 (six different files).
- Within US1: T009–T010 (batch) ∥ T011–T012 (window), since they are different files written against the contract.
- T020 (fixtures) ∥ T018–T019 (batch), since they are different files.
- T024 can run alongside any story phase.

---

## Parallel Example: User Story 1

```bash
# After Phase 2, two tracks against contracts/import-batch.md and contracts/ui-windows.md:
Task: "T009–T010 SheetImportBatch core and process_file in therepy_sessions/interpretation/importing/sheet_import_batch.py"
Task: "T011–T012 ImportWindow layout and worker-thread run in therepy_sessions/interpretation/importing/import_window.py"
# Then T013 wires both in therepy_sessions/program.py.
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 and Phase 2 (T001–T008).
2. Phase 3 (T009–T014).
3. **STOP and VALIDATE** with quickstart V4. A mixed-student batch imports, and each sheet prints with its own template. Failures already show up as **Failed** with raw text.

### Incremental Delivery

1. MVP (US1).
2. Add US2: list editing and duplicate protection.
3. Add US3: precise reasons, retry without new Textract calls, changed-file detection.
4. Polish: Cancel, retire `program_interpret.py`, full quickstart.

---

## Notes

- [P] tasks touch different files and have no dependencies on incomplete tasks.
- Commit after each phase checkpoint.
- Scratch scripts for V1/T017/T021 live outside the repository or under a git-ignored path.
