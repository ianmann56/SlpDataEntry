# Contract: Session Storage (Google Drive / Sheets)

Storage implements the `DataSheetStore` abstraction
([interpretation-and-import.md](interpretation-and-import.md)) and receives only
`StudentDataSheet` (layers rule 1). It reads the template the sheet was interpreted with
from `sheet.template` (R2), and the canonical Student Key from `sheet.student_key`. Every Sheets and Drive request body lives here
(layers rule 4). Research references (R#) are to [../research.md](../research.md).

## `storage/template_structure.py` (new, pure)

```python
class SectionShape(NamedTuple):
    section_id: str          # interpreter id; matches tables on a sheet, never part of the structure
    kind: str                # interpreter.section_kind
    title: str
    keys: tuple[str, ...]    # interpreter.section_keys(), in template order

class TemplateShape(NamedTuple):
    template_name: str
    sections: tuple[SectionShape, ...]
    def structure_identity(self) -> list[tuple[str, str, list[str]]]: ...
    def structure_fingerprint(self) -> str: ...      # "s1-" + 32 hex characters (R3)

def shape_of(template: StudentDataSheetTemplate) -> TemplateShape: ...
```

This module uses only the interpreters' public `id`, `title`, `section_kind`, and
`section_keys()`. It never `isinstance`-checks interpreter types (Principle V).

## `storage/session_layout.py` (new, pure)

This module has no Google imports and does no I/O, so all of it can be checked offline.

```python
TAB_NAME_MAX: int = 100
LAYOUT_VERSION: int = 1

class CellKind(Enum):
    NUMBER = "number"
    TEXT = "text"

CELL_KIND_BY_TYPE: dict[DataSheetScalarType, CellKind]   # INT → NUMBER, every other type → TEXT (R7)

class CellValue(NamedTuple):
    text: str | None          # None for an empty cell
    number: int | None        # set only when the value is written as a number

class SessionMoment(NamedTuple):
    date_text: str
    time_text: str
    @property
    def sort_key(self) -> tuple[bool, date, bool, time]: ...
    def matches(self, other: "SessionMoment") -> bool: ...

class LayoutSection(NamedTuple):
    kind: str
    title: str
    keys: tuple[str, ...]

class WorkbookLayout(NamedTuple):
    sections: tuple[LayoutSection, ...]
    def to_json(self) -> str: ...
    @staticmethod
    def from_json(text: str) -> "WorkbookLayout": ...
    @staticmethod
    def from_shape(shape: TemplateShape) -> "WorkbookLayout": ...

def cell_for(value: DataSheetScalarDto | str | None) -> CellValue: ...
def moment_of(sheet: StudentDataSheet) -> SessionMoment: ...
def moment_from_rows(rows: list[list[str]]) -> SessionMoment | None: ...   # from a tab's A1:B6
def tab_base_name(moment: SessionMoment) -> str: ...                      # "{date} {time}" or "{date}", cleaned, ≤100
def unique_tab_name(base: str, taken: Collection[str]) -> str: ...        # base, then base + " 2", " 3", …
def insert_index(new: SessionMoment, existing: Sequence[SessionMoment | None]) -> int: ...
def session_rows(sheet: StudentDataSheet, layout: WorkbookLayout) -> list[list[CellValue]]: ...   # R9
def workbook_name(student_key: str, template_name: str) -> str: ...      # "AG - Emotion Causes"
```

| Function | Guarantees | Spec |
| --- | --- | --- |
| `cell_for` | Only `INT` values that parse as integers become numbers. A blank value becomes `CellValue(None, None)`. | FR-024, FR-024a, FR-024b |
| `SessionMoment.matches` | `False` if either time is blank. Otherwise compares the dates and times with `casefold().strip()`. | FR-016, FR-017a |
| `tab_base_name` | Removes control characters, collapses whitespace, and trims to `TAB_NAME_MAX` while leaving room for a ` N` suffix. | FR-015, FR-017a, FR-018 |
| `insert_index` | Newest first by `sort_key`. A tie puts the new tab first. `None` (a tab whose values can't be read) sorts as the oldest. | FR-018a |
| `session_rows` | Puts the 6 header rows first, then the form fields in layout order, a blank row, then the table blocks in layout order. Columns are placed by key. Writes no metadata. | FR-020–FR-025a |

## `storage/google_drive_data_sheet_store.py` (new)

```python
DATA_FOLDER_PATH: tuple[str, str] = ("SLP Therepy Data", "Current Year")

class GoogleDriveDataSheetStore(DataSheetStore):
    def __init__(
        self,
        inject_drive_service: Callable[[], Any],    # googleapiclient Resource, drive v3
        inject_sheets_service: Callable[[], Any],   # googleapiclient Resource, sheets v4
    ) -> None: ...

    def prepare(self) -> None:
        """Connect (signing in if needed) and find or create the Therapy Data Folder. Raises DataSheetStoreError."""

    def save(self, sheet: StudentDataSheet) -> SavedDataSheet:
        """Save one session to its Student Session Workbook, or find it already saved. Raises DataSheetStoreError."""
```

`save` returns `SavedDataSheet` with these fields:

- `location_url`: `https://docs.google.com/spreadsheets/d/{id}/edit#gid={sheetId}`
- `location_name`: `"{workbook name} › {tab name}"`
- `already_saved`

### `prepare()`

1. Call both injectors. This is where OAuth runs, if needed.
2. Find `SLP Therepy Data`: a folder with `'root' in parents` and `trashed=false`; the
   oldest by `createdTime` wins. Create it if there is none.
3. Do the same for `Current Year` inside it.
4. Cache the folder id.

It is idempotent within one store.

### `save(sheet)`

1. `prepare()` if it hasn't run yet.
2. `shape = shape_of(sheet.template)`, `fingerprint = shape.structure_fingerprint()`, and
   `student_key = sheet.student_key` (already the stored key, R2).
3. **Find the workbook**:
   - Check the cached id for `(student_key, fingerprint)` with `files.get`; it must not
     be trashed, and the folder must be in its parents.
   - Otherwise search with `files.list` on the appProperties, `orderBy=modifiedTime desc`,
     and take the first result (R4, R5).
4. **No workbook found**: create it as in research R6.
   - The first tab is `tab_base_name(moment)`.
   - The layout is `WorkbookLayout.from_shape(shape)`.
   - The name is `workbook_name(student_key, shape.template_name)`.
   - Cache the new id and return `already_saved=False`.
5. **Workbook found**:
   1. One `spreadsheets.get` with
      `fields=properties.title,sheets.properties(sheetId,title,index),developerMetadata`
      returns the workbook name, the tabs, and the layout. A missing layout falls back
      to `from_shape(shape)`.
      - **Repair** (spec edge case, FR-019): a missing layout means an earlier create
        failed and its cleanup also failed. In that case the `batchUpdate` in step 4
        also carries `createDeveloperMetadata` with the fallback layout, and a
        `deleteSheet` (after the `addSheet`) for every tab whose `A1:B6` (step 2) is
        empty. Those empty tabs are left out of the duplicate check, `titles`, and
        `tab_moments_in_index_order`. A workbook that has its layout is never repaired,
        so an empty tab the SLP added is not removed.
   2. One `values.batchGet` reads `'<tab>'!A1:B6` for every tab, giving
      `moment_from_rows` for each.
   3. **Duplicate**: if `moment_of(sheet)` matches any tab's moment, return that tab with
      `already_saved=True` and write nothing.
   4. **Otherwise**, compute:
      - `name = unique_tab_name(tab_base_name(moment), titles)`
      - `index = insert_index(moment, tab_moments_in_index_order)`
      - a new `sheetId` (random 31-bit, not in use)

      Then send one `batchUpdate` with `addSheet` and `updateCells` from
      `session_rows(sheet, layout)`, plus the repair requests from step 1 when they
      apply. Return `already_saved=False`.
6. Every `execute(num_retries=3)`. `HttpError`, `RefreshError`, `TransportError`, and
   `OSError` become `DataSheetStoreError`, with messages such as:
   - "not signed in to Google; press Import to sign in"
   - "no connection to Google Drive"
   - "Google Drive refused the request ({status})"

   The original error is chained with `raise … from e` for the console traceback.

**Privacy**: request bodies carry session values only in `updateCells`. The
`appProperties` and developer metadata carry the stored Student Key and template keys
only (FR-028). Nothing is logged to a file (FR-026).

## `clients/google_service.py` (changed)

```python
DEFAULT_CLIENT_SECRET_FILE: str   # today's default path, outside the repo
CLIENT_SECRET_FILE_ENV: str = "SLP_GOOGLE_CLIENT_SECRET_FILE"   # read inside load_google_credentials(), never at import time
SCOPES: list[str] = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def load_google_credentials() -> Any: ...                  # google.oauth2.credentials.Credentials; the pickle cache, refresh, and browser login as today; resolves the secret path from CLIENT_SECRET_FILE_ENV, else DEFAULT_CLIENT_SECRET_FILE
def create_sheets_service(credentials: Any) -> Any: ...    # build('sheets', 'v4')
def create_drive_service(credentials: Any) -> Any: ...     # build('drive', 'v3')
```

- `create_google_service()` is removed; its only caller was the prototype.
- `convert_to_RFC_datetime` is removed (unused).
- Nothing runs at import time (DI rule 3).

## Removed

- `storage/file_creator.py` (the prototype `create_therapy_session_sheet`, R13).
