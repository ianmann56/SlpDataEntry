# Contract: Data Sheet Store, Sheet Changes, Import Batch, Import Window, and Wiring

Every public member listed here is fully annotated (Principle VI). Research references
(R#) are to [../research.md](../research.md).

## `interpretation/data_sheet_store.py` (new): the storage abstraction

```python
class SavedDataSheet(NamedTuple):
    """Where a sheet's session now lives."""
    location_url: str      # opens the saved session (for Google: the tab's URL)
    location_name: str     # SLP-readable, e.g. "AG - Emotion Causes › 9/14/2026 11:00 AM"; Student Key only
    already_saved: bool    # True when the session was already stored and nothing was written (FR-016a)

class DataSheetStoreError(Exception):
    """A store operation failed. str(e) is an SLP-readable reason naming students only by Student Key."""

class DataSheetStore(ABC):
    """The storage mechanism for interpreted data sheets. Business and UI logic use only this."""

    @abstractmethod
    def prepare(self) -> None:
        """Get ready to save: connect, sign in if needed, find or create the destination. Raises DataSheetStoreError."""

    @abstractmethod
    def save(self, sheet: StudentDataSheet) -> SavedDataSheet:
        """Store one interpreted sheet, or report it is already stored. Writes nothing partial. Raises DataSheetStoreError."""
```

- This module is pure: it holds the ABC and records only, with no I/O.
- Implementations live in `storage/`. The only one in this feature is
  `GoogleDriveDataSheetStore` ([session-storage.md](session-storage.md)).
- `prepare` is idempotent, and `save` calls it if it hasn't run.

## `StudentDataSheet` (changed)

```python
from __future__ import annotations
if TYPE_CHECKING:
    from interpretation.template_manager.student_data_sheet_template import StudentDataSheetTemplate

class DataSheetTable(TypedDict):
    columns: list[object]
    data: list[dict[str, DataSheetScalarDto]]
    section_id: NotRequired[str]          # id of the interpreter that produced the table

class StudentDataSheet:
    def __init__(self, student_key: str, student_goal: str, date: str, time_in: str,
                 time_out: str, measure: str, template: StudentDataSheetTemplate) -> None: ...
    @property
    def template(self) -> StudentDataSheetTemplate: ...   # the template the sheet was interpreted with
    def register_table(self, table: DataSheetTable, section_id: str) -> None: ...
    def use_student_key(self, student_key: str) -> None: ...   # set the stored (canonical) key after matching
```

`debug()` is kept as a local developer aid, and also prints `template.name`.

## `SessionDataSectionInterpreterBase` (changed)

```python
@property
def section_kind(self) -> str: ...          # default: type(self).__name__

@abstractmethod
def section_keys(self) -> list[str]: ...    # field / column / tally keys in template order
```

| Interpreter | `section_keys()` |
| --- | --- |
| `TableInterpreter` | `[c.column_name for c in self.columns]` |
| `RunningTallyInterpreter` | `["Tally"]` |
| `SimpleFormInterpreter` | `list(self.fields.keys())` |

`interpreters.md`'s "Adding a new interpreter type" table gains this requirement: the
Interpreter piece implements `section_keys`.

## `StudentDataSheetInterpreter` and `StudentDataSheetTemplate` (changed)

```python
class StudentDataSheetInterpreter:
    def __init__(self, session_data_templates: list[SessionDataSectionInterpreterBase],
                 template: StudentDataSheetTemplate) -> None: ...
    def interpret_student_data_sheet(self, data_sheet_content: StudentDataSheetImport) -> StudentDataSheet: ...

# StudentDataSheetTemplate
def to_data_sheet_interpreter(self) -> StudentDataSheetInterpreter: ...   # passes self.interpreters and self
```

The interpreter attaches `template` to every sheet it returns, and registers each table
with its producing interpreter's id.

## `interpretation/importing/sheet_import_batch.py` (changed)

```python
class FailureReason(Enum):
    ...                                   # existing reasons
    MISSING_DATE = "missing_date"
    SAVE_FAILED = "save_failed"

class SheetOutcome(NamedTuple):
    status: SheetStatus
    student_key: str | None = None
    template_name: str | None = None
    failure_reason: FailureReason | None = None
    message: str = ""
    saved: SavedDataSheet | None = None   # set only on SUCCEEDED

class SheetImportBatch:
    def __init__(
        self,
        read_sheet: Callable[[str], StudentDataSheetImport],
        student_store: StudentStore,
        get_template: Callable[[str], StudentDataSheetTemplate | None],
        data_sheet_store: DataSheetStore,
        stat_mtime_ns: Callable[[str], int] = _os_stat_mtime_ns,
    ) -> None: ...
```

`process_file` steps, in order:

1. read
2. match the student
3. load the template
4. interpret
5. `data_sheet.use_student_key(student.student_key)`
6. **check the date**: a blank date raises `MISSING_DATE`
7. **save**: `data_sheet_store.save(data_sheet)`. Any exception raises `SAVE_FAILED`
   with `detail=str(e)`, and its cause is printed to the console.

On success:

- `message` is `"Saved to {location_name}"`, or `"Already saved in {location_name}"`.
- `saved` holds the `SavedDataSheet`.

| New failure | Message |
| --- | --- |
| `MISSING_DATE` | "No session Date was found on the sheet. Fill in the Date and retake the photo." |
| `SAVE_FAILED` | "Could not save to Google Drive: {detail}. Press Import again to retry." |

## `ImportWindow` (changed)

```python
class ImportWindow:
    def __init__(
        self,
        master: tk.Toplevel,
        batch: SheetImportBatch,
        data_sheet_store: DataSheetStore,
        check_records_readable: Callable[[], None],
        open_url: Callable[[str], None],
        on_back: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None: ...
```

| Change | Behavior | Spec |
| --- | --- | --- |
| `on_sheet_interpreted` removed | Saving happens inside `process_file` through the store. | FR-001 |
| `data_sheet_store.prepare()` | The worker calls it first, while the window shows "Connecting to Google Drive…". If it raises, the worker posts `("prepare_failed", error)`. The Tk thread then shows `error_handling.throw(error, "Cannot start the import")`, and the run ends with no sheet processed and rows unchanged. Cancel pressed during it takes effect afterwards. | FR-006a, R10 |
| Status indicator | The Status column shows `✓ Succeeded`, `✗ Failed`, `○ Not imported`, or `… Importing`. Treeview tags give distinct foreground colors that are readable in the light and dark sv-ttk themes. | FR-003a |
| **Open** button / double-click | Enabled when exactly one selected row is `SUCCEEDED` and no run is active. It calls `open_url(outcome.saved.location_url)`. | FR-003b |
| Details column | Shows the outcome `message`. | FR-002, FR-016a |

The window and the batch receive the same store instance. `open_url` is injected
(`webbrowser.open`), so the window does no I/O itself.

## `program.py` wiring (changed)

```python
google_lock = threading.Lock()
credentials / sheets_service / drive_service: Any = None   # built lazily, once per app run

def inject_sheets_service() -> Any: ...   # googleapiclient Resource (sheets v4)
def inject_drive_service() -> Any: ...    # googleapiclient Resource (drive v3)

def open_import_path() -> None:
    data_sheet_store: DataSheetStore = GoogleDriveDataSheetStore(inject_drive_service, inject_sheets_service)
    ImportWindow(
        path_window,
        SheetImportBatch(read_sheet=..., student_store=..., get_template=..., data_sheet_store=data_sheet_store),
        data_sheet_store,
        check_records_readable,
        open_url=webbrowser.open,
        on_back=..., on_exit=...,
    )
```

`program.py` is the only module that names `GoogleDriveDataSheetStore`. A new store is
built for each Import window visit, so its workbook cache (R5) lasts only as long as the
window.
