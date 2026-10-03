# Research: Save Imported Sessions to Google Drive

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-02

Each decision records what was chosen, why, and what else was considered. The Technical
Context in [plan.md](plan.md) has no open NEEDS CLARIFICATION items. These decisions
settle the design questions the spec left to planning.

## R1. The Data Sheet Store abstraction

**Decision**: Business logic (`SheetImportBatch`) and UI logic (`ImportWindow`) talk to
storage only through an abstract **Data Sheet Store**:

```python
class DataSheetStore(ABC):                       # interpretation/data_sheet_store.py
    def prepare(self) -> None: ...                # connect / sign in / find the destination
    def save(self, sheet: StudentDataSheet) -> SavedDataSheet: ...
```

- **Abstraction**: `interpretation/data_sheet_store.py`. It holds the ABC, the
  `SavedDataSheet` result record, and `DataSheetStoreError`. It is the port the
  pipeline's consumers own.
- **Concrete implementation**: `storage/google_drive_data_sheet_store.py`,
  `GoogleDriveDataSheetStore(DataSheetStore)`. It is the only code that knows about
  Drive, Sheets, workbooks, or tabs.
- **Wiring**: `program.py` builds one `GoogleDriveDataSheetStore` per Import window visit
  and injects it, typed as `DataSheetStore`, into both the batch and the window.
- **Saving**: `SheetImportBatch.process_file` calls `store.save(data_sheet)` on the
  worker thread, right after interpretation. A sheet is `SUCCEEDED` only when `save`
  returns. Any exception from it becomes the new `SAVE_FAILED` outcome.
- **Preparing**: `ImportWindow` calls `store.prepare()` on the worker thread before the
  first sheet (R10).
- **Removed**: the `on_sheet_interpreted` sink.

The sheet is the only argument: everything Storage needs is on the `StudentDataSheet`
(R2).

**Rationale**:

- This mirrors the existing `StudentStore` (ABC) / `JsonStudentStore` split, so the
  project has one consistent pattern for "the thing that persists X".
- Callers depend on the abstraction, so another destination (CSV, a different
  spreadsheet layout) is a new subclass wired in `program.py`, with no change to the
  batch or the window.
- Offline checks use an in-memory fake store.
- The ABC sits in `interpretation/` (the consumer side), so layers rule 1 still holds:
  `interpretation/` never imports `storage/`, and `storage/` imports `interpretation/`
  to implement the port.
- Saving inside `process_file` gives FR-002 (succeed only after the save), FR-004 (a
  failed save retries through the existing "not yet succeeded" rule, reusing its
  Import), and Cancel only ever between sheets.

**Alternatives considered**:

- An injected `save_sheet` callable, as in this plan's first draft. Rejected: the SLP
  asked for an explicit storage abstraction, and two loose callables (`save_sheet`,
  `prepare_output`) hide that they belong to one mechanism.
- Putting the ABC in `storage/`. Rejected: `interpretation/` would then import
  `storage/`, which needs an exception to layers rule 1.
- Saving on the Tk thread through the old sink. Rejected: it would freeze the window,
  and a save couldn't fail the sheet.

## R2. The template rides on the StudentDataSheet

**Decision**: `StudentDataSheet` gains a `template: StudentDataSheetTemplate` property:
the template the sheet was interpreted with.

- `StudentDataSheetTemplate.to_data_sheet_interpreter()` passes `self` to
  `StudentDataSheetInterpreter`, which sets it on every sheet it builds. A sheet is
  therefore never without its template.
- Each table registered on the sheet is tagged with the `section_id` (interpreter id)
  that produced it, so Storage can label blocks and order them (FR-022, FR-025a).
- After matching the student, the batch sets the sheet's Student Key to the **stored**
  key with `sheet.use_student_key(student.student_key)`. It differs from the text read
  only in case and surrounding spaces. Storage then labels and names workbooks with
  the canonical key even when OCR read ` ja `.

Storage derives everything template-related from `sheet.template`:

- name
- sections
- keys in template order
- the structure fingerprint (R3)

Its section keys come from the interpreters, through two new members on
`SessionDataSectionInterpreterBase`:

- `section_kind`, which defaults to the class name
- the abstract `section_keys() -> list[str]`, giving keys in template order

So Storage never `isinstance`-checks interpreter types, and new types stay pluggable
(Principle V).

**Import cycle**: `student_data_sheet.py` imports the template type only under
`typing.TYPE_CHECKING`, with `from __future__ import annotations`. The template module
already imports the interpreter module, which imports `student_data_sheet.py`, so a
runtime import would be circular.

**Amendment**: layers rule 1 still allows only `StudentDataSheet` to cross
interpretation → storage. It now states that the sheet carries the template it was
interpreted with, and that Storage may read the template (and its interpreters' public
members) through the sheet. Storage still never loads templates or imports
`TemplateStore`.

**Rationale**: The SLP asked that the template travel with the sheet, so Storage can
drive any template-dependent logic itself. Today that logic is the structure, layout
order, and workbook name; later it will be per-field save types (FR-024b). Keeping the
structure and fingerprint rules in Storage puts them beside the only code that uses
them.

**Alternatives considered**:

- A precomputed `TemplateShape` on the sheet, as in this plan's first draft. Rejected:
  Storage would see only what interpretation chose to expose, and a later feature that
  reads per-field save configuration from the template would have to widen that DTO.
- Passing the template as a second `save` argument. Rejected: the SLP asked for the
  sheet to be the single unit sent to storage.

## R3. What Template Structure means, and its fingerprint

**Decision**: This lives in `storage/template_structure.py`, computed from `sheet.template`
(R2).

- A section's identity is `(section_kind, title, sorted(keys))`. The Template Structure
  is the sorted list of those section identities. Section ids, the template name and
  description, value types, and choice options are excluded (FR-008, FR-009).
- The **structure fingerprint** is the first 32 hex characters of SHA-256 over the
  canonical JSON of that sorted list (`sort_keys=True`, no whitespace), prefixed with a
  version: `s1-<hex>`.
- Header fields (Student Key, Date, Time IN/OUT, Goal, Measure) are on every sheet, so
  they are not part of it.

**Rationale**:

- Sorting at both levels gives order independence (FR-009).
- Using a multiset of sections handles two sections with the same kind and title.
- The version prefix lets a later feature change the definition without silently
  matching old workbooks.
- SHA-256 needs only the stdlib (`hashlib`), and 128 bits rules out collisions at this
  scale.
- Section titles are included, so renaming a section starts a new workbook (SC-004).

**Alternatives considered**:

- Storing the full structure instead of a hash. Rejected: Drive `appProperties` values
  are limited to 124 bytes per key and value together.
- Keying sections by interpreter id. Rejected: ids are internal (FR-008), and a copied
  template would get different ids.

## R4. The hidden workbook label, and how workbooks are found

**Decision**: The label is split across two places, by what each is good at:

| Data | Where | Why |
| --- | --- | --- |
| `slpWorkbook=1`, `slpStudentKey=<key>`, `slpStructure=<fingerprint>` | Drive file `appProperties` | Searchable with `files.list`, invisible to the SLP, private to this OAuth client |
| Workbook Layout Order (JSON) | Spreadsheet `developerMetadata`, key `slpWorkbookLayout`, `DOCUMENT` visibility | Holds structured data up to 30,000 characters per spreadsheet, invisible in the UI |

To find a workbook, the app runs `files.list` with this query:

```text
'<folderId>' in parents and trashed = false and mimeType = 'application/vnd.google-apps.spreadsheet'
and appProperties has { key='slpWorkbook' and value='1' }
and appProperties has { key='slpStudentKey' and value='<key>' }
and appProperties has { key='slpStructure' and value='<fp>' }
```

It sorts by `orderBy='modifiedTime desc'` and takes the first result (FR-013b).

- **Renamed** workbooks still match (FR-013).
- **Trashed or moved** workbooks don't, because of the `in parents` and `trashed` terms.
- **Reinstall or another computer**: nothing is stored locally (FR-013a).

**Rationale**: `appProperties` is the only Drive metadata that is searchable and hidden.
The layout order is too big for it, so it lives in developer metadata. That metadata
travels with the file and is readable with one `spreadsheets.get` call.

**Alternatives considered**:

- A local index file. Rejected in clarification.
- Encoding the label in the file name. Rejected: renaming would break it (FR-013).
- A hidden `_layout` tab. Rejected: FR-019 allows only session tabs, and a hidden tab can
  still be unhidden by the SLP.

**Consequence**: The **copy** case (FR-013b) depends on Drive's copy behavior. Drive
keeps `appProperties` on `files.copy`. A copy made in the Drive UI with "Make a copy" may
drop them, in which case the copy is simply not a match. Either outcome satisfies the
spec.

## R5. Search lag within one Import Run

**Decision**: `GoogleDriveDataSheetStore` keeps an in-memory map
`(student_key, fingerprint) → spreadsheet id` for workbooks it found or created during
the window's life.

Before using a cached id, it checks with `files.get(fields='trashed,parents')` that the
workbook is not trashed and is still in the folder. If the check fails, it drops the
entry and searches again.

**Rationale**: Drive search is eventually consistent. A workbook created for the first
`JA` sheet in a batch may not show up in a search a second later for the second `JA`
sheet, which would create a duplicate workbook and break FR-007. The cache is only an
accelerator: Drive is still the source of truth, and the cache dies with the window.

**Alternatives considered**: sleeping and retrying the search. Rejected: slow, and still
not guaranteed.

## R6. Making each save atomic (FR-002)

**Decision**:

- **Adding a tab to an existing workbook** is one `spreadsheets.batchUpdate` with two
  requests:
  1. `addSheet`, with an explicit `sheetId`, `title`, and `index`
  2. `updateCells`, writing every row, with each value as `userEnteredValue.stringValue`
     or `numberValue`

  `batchUpdate` is all-or-nothing, so a tab is never half-written.
- **Creating a new workbook** takes three steps:
  1. `drive.files.create` with `mimeType` spreadsheet, the workbook name, `parents=[folderId]`,
     and the `appProperties`. This places and labels the file in one call.
  2. One `spreadsheets.batchUpdate`: `addSheet` the session tab, `updateCells` its rows,
     `deleteSheet` the default tab, and `createDeveloperMetadata` with the layout.
  3. If step 2 fails, `drive.files.delete` the new file (best effort) and report the
     failure. A failed delete is printed to the console, and the empty workbook is later
     found and reused. It holds no session tab, so no data is wrong.

**Rationale**: This meets "nothing partial remains" (FR-002) with no compensation logic
for existing workbooks. Writing values with `updateCells`, rather than
`values.update(valueInputOption=USER_ENTERED)`, keeps text as typed: `9/14` stays text,
`007` keeps its zeros, and a leading `=` is not a formula (FR-024a).

**Alternatives considered**:

- `values.update` with `RAW`. Also keeps text, but it is a second call outside the
  `addSheet` batch, so a failure between the two leaves an empty tab.
- `spreadsheets.create` with the data inline, then moving the file into the folder.
  Rejected: the file sits unlabeled in My Drive root between the two calls.

## R7. Saving each value as a number or as text (FR-024a, FR-024b)

**Decision**: Storage has one function, `cell_for(scalar) -> CellValue`, that looks at
the scalar's `DataSheetScalarType`:

- `INT`: `numberValue` if the text parses as an integer (after stripping spaces),
  otherwise `stringValue` of the original text.
- Every other type: `stringValue` of the value as read.
- A raw `str` scalar (what `SimpleFormInterpreter` stores today, with no type):
  `stringValue`.
- Blank or `None`: an empty cell.

The type → cell rule is a module-level mapping, `CELL_KIND_BY_TYPE`. A later feature can
let the SLP choose a type per field on the template, which changes the
`DataSheetScalarType` the interpreter emits. This function, and the save rules, then
need no change.

**Rationale**: FR-024b asks for the decision to come from the interpreted type. Today
`TableInterpreter` emits `TEXT` for every cell and `SimpleFormInterpreter` emits untyped
strings, so in practice only tallies configured as `INT` become numbers. That is correct
until per-field configuration arrives.

**Alternatives considered**: guessing from content (`USER_ENTERED`). Rejected in
clarification.

## R8. Tab names, Session Moment, and ordering

**Decision**: These are pure functions in `storage/session_layout.py`.

- **Tab name**:
  - `"{date} {time_in}"` when Time IN is not blank, otherwise `"{date}"`.
  - Control characters and newlines are removed, whitespace runs are collapsed, and the
    name is trimmed to 100 characters (the Sheets limit) (FR-018).
  - If the name is already used by a tab that isn't a duplicate, the lowest free
    `" 2"`, `" 3"`, … is appended (FR-016b, FR-017a).
- **Session Moment of an existing tab**: read from the tab's values, not its title. One
  `values.batchGet` reads `A1:B6` of every tab. The values in column B next to the `Date`
  and `Time IN` labels in column A are the moment, so renamed tabs still count (FR-016).
- **Duplicate**: the sheet's Time IN is not blank, and some tab's Date and Time IN equal
  the sheet's, compared with `casefold().strip()` (FR-016, FR-017a).
- **Ordering key**: `(has_date, date, has_time, time)`.
  - The date is parsed with `%m/%d/%Y`, `%m/%d/%y`, `%m-%d-%Y`, or `%m-%d-%y`.
  - The time is parsed with `%I:%M %p`, `%I:%M%p`, `%I %p`, or `%H:%M`, after
    upper-casing and removing dots (`a.m.`).
  - A value that can't be parsed sorts after the parsed ones (FR-018a).
- **Insert index**: the new tab goes before the first existing tab whose key is less than
  or equal to its own key. Ties put the new tab first, so blank-time tabs for one date
  are newest first. Tabs whose values can't be read (for example, ones the SLP added)
  count as undated and sort to the end.

**Rationale**: These are plain functions, so they can be checked offline with no Google
access (R12). Python's `strptime` covers the formats US school sheets use without a new
dependency; `python-dateutil` is only a transitive boto dependency, and relying on it
would need justification.

**Alternatives considered**:

- Sorting all tabs with `updateSheetProperties` on every save. Rejected: it rewrites
  tabs the save didn't touch.
- Storing the moment in per-tab developer metadata. Rejected: FR-016 ties identity to
  the values in the tab.

## R9. The tab layout (FR-020–FR-025a)

**Decision**: Rows, top to bottom:

1. Six header rows: `Student Key`, `Date`, `Time IN`, `Time OUT`, `Goal`, `Measure`, with
   the field name in A and the value in B.
2. One row per form field, in Workbook Layout Order across the form sections. A field
   missing on the sheet gets an empty B cell.
3. A blank row.
4. For each table section in layout order, and each table that section produced on this
   sheet:
   - a title row with the section title (FR-022)
   - a header row of column names in layout order
   - one row per data row, in sheet order
   - a blank row before the next block

Each table column is mapped by key, so a template whose columns are listed in a
different order still writes to the original positions (FR-025a).

Choice options, types, ids, and the template name or description are never written
(FR-023).

**Rationale**: This follows the clarified layout exactly. The header rows always come
first and in the same order, which also makes reading the Session Moment (R8) simple.

**Alternatives considered**: none beyond the options settled in clarification.

## R10. Signing in and finding the folder at Import press (FR-006a)

**Decision**: `ImportWindow` calls `data_sheet_store.prepare()` on the worker thread
**first**, before processing any sheet, while the window shows
"Connecting to Google Drive…". If it raises, the run ends with no sheet processed and the
error is shown through `error_handling.throw` ("Cannot start the import").

`GoogleDriveDataSheetStore.prepare()` calls its injected service providers. These build
the Google credentials and services lazily in `program.py`, running OAuth
`run_local_server` if needed. It then finds or creates `SLP Therepy Data` (in My
Drive root) and `Current Year` inside it.

**Rationale**:

- Running it on the worker keeps the window repainting while the browser sign-in is open.
- Running it before any sheet means no Textract call is spent when Drive is unreachable.
- When several folders with the same name exist, the oldest (by `createdTime`) is reused,
  so a duplicate is never created (FR-006).

**Alternatives considered**: running it on the Tk thread like `check_records_readable`.
Rejected: `run_local_server` blocks until the browser flow ends, which would freeze the
window.

## R11. Google clients and credentials

**Decision**: Split `clients/google_service.py` into:

- `load_google_credentials() -> Credentials`: the existing pickle cache, refresh, and
  `InstalledAppFlow` logic.
- `create_sheets_service(credentials)`: `build('sheets', 'v4', ...)`.
- `create_drive_service(credentials)`: `build('drive', 'v3', ...)`.

The scopes stay as they are today (`spreadsheets`, `drive`), so existing tokens keep
working.

The client-secret path keeps today's default, which is outside the repo. It can now be
overridden with the `SLP_GOOGLE_CLIENT_SECRET_FILE` environment variable
(dependency-injection rule 4).

`program.py` builds the credentials and services once, lazily, behind
`inject_drive_service` and `inject_sheets_service`, guarded by a lock like
`inject_textract_client`.

`GoogleDriveDataSheetStore` translates `HttpError`, `RefreshError`, and transport
errors into `DataSheetStoreError` with an SLP-readable message (DI rule 5), e.g. "Could not
save to Google Drive: no connection."

Every `execute()` uses `num_retries=3`, so the client library backs off on 429 and 5xx
responses.

**Rationale**: Drive needs its own discovery service, but both services share one
credential. All Google calls run on the single worker thread, so the non-thread-safe
`httplib2` transport is never shared across threads.

A run of 10 sheets makes about 4–5 Sheets/Drive calls per sheet, which is well under
the per-user quotas (60 Sheets writes per minute). The built-in retries cover a burst.

**Alternatives considered**: narrowing to the `drive.file` scope. It would be more
private, but then the app could not see a `SLP Therepy Data` folder the SLP made by
hand, and would create a second one. It is recorded as a possible later hardening.

## R12. Validation approach

**Decision**: Same as features 003 and 004: no test framework.

- **Offline checks** with scratch `python -c` scripts:
  - `storage/template_structure.py` fingerprints, including order independence and
    type/choice independence
  - the pure functions in `session_layout.py`: tab names, moments, ordering, rows, and
    cell kinds
  - `SheetImportBatch` with an in-memory fake `DataSheetStore`
  - `GoogleDriveDataSheetStore` against in-memory fake Drive and Sheets services that record
    requests
- **Live checks** in [quickstart.md](quickstart.md), on synthetic sheets and a
  test Google account's Drive.

**Rationale**: This matches the constitution's workflow ("verifiable offline with
synthetic sample inputs"), and adds no dependency.

## R13. Retiring the prototype output

**Decision**: Delete `storage/file_creator.py` (`create_therapy_session_sheet`, which
holds hard-coded sample data and charts) and `convert_to_RFC_datetime` (unused). The
glossary's **Session Sheet** entry becomes **Student Session Workbook**.

**Rationale**: The spec puts charts and summaries out of scope and says the prototype is
replaced. Keeping dead code that names "Jimmy" and writes charts would confuse the
Storage layer's contract.
