# Contract: Sheet Import Batch

**Module**: `therepy_sessions/interpretation/importing/sheet_import_batch.py`

This module has no Tkinter import. Everything external is injected (research R2). It
is fully annotated (Principle VI). Entity fields are in [../data-model.md](../data-model.md).

## Types

```python
class SheetStatus(Enum):
    NOT_IMPORTED = "not_imported"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

class FailureReason(Enum):
    FILE_UNREADABLE = "file_unreadable"
    READING_FAILED = "reading_failed"
    NO_STUDENT_KEY = "no_student_key"
    UNKNOWN_STUDENT = "unknown_student"
    NO_CURRENT_TEMPLATE = "no_current_template"
    TEMPLATE_MISSING = "template_missing"
    TEMPLATE_MISMATCH = "template_mismatch"
    STUDENT_RECORDS_UNREADABLE = "student_records_unreadable"

class SheetOutcome(NamedTuple):
    status: SheetStatus
    student_key: str | None = None
    template_name: str | None = None
    failure_reason: FailureReason | None = None
    message: str = ""

class ProcessedSheet(NamedTuple):
    outcome: SheetOutcome
    data_sheet: StudentDataSheet | None      # set only when status is SUCCEEDED

class ListTotals(NamedTuple):
    succeeded: int
    failed: int
    not_imported: int

SUPPORTED_IMAGE_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".tif", ".tiff")
```

`SelectedFile` is a `@dataclass` with the fields in the data model.

## `SheetImportBatch`

```python
class SheetImportBatch:
    def __init__(
        self,
        read_sheet: Callable[[str], StudentDataSheetImport],
        student_store: StudentStore,
        get_template: Callable[[str], StudentDataSheetTemplate | None],
        stat_mtime_ns: Callable[[str], int] = _os_stat_mtime_ns,
    ) -> None: ...

    @property
    def files(self) -> list[SelectedFile]: ...          # list order; a copy

    def add_files(self, paths: Sequence[str]) -> list[SelectedFile]: ...
    def remove_files(self, identities: Collection[str]) -> None: ...

    def files_to_process(self) -> list[SelectedFile]: ...   # not SUCCEEDED, list order
    def process_file(self, identity: str) -> ProcessedSheet: ...
    def totals(self) -> ListTotals: ...
```

### Behavior

| Call | Guarantees |
| --- | --- |
| `add_files(paths)` | Appends each new, supported path in the given order. Skips paths already in the list (by identity) and unsupported extensions. Returns the files actually added. Never raises for a bad path, because a missing file is caught when it is processed. |
| `remove_files(ids)` | Removes the matching files and drops their saved Imports. Unknown ids are ignored. |
| `files_to_process()` | Every file whose status is not `SUCCEEDED`. |
| `process_file(id)` | Runs steps 1–8 from the data model. It sets the file's `outcome`, its saved Import, and its mtime, and returns them. It **never raises** for any per-sheet failure: each one becomes a `FAILED` outcome, and the cause's traceback is printed to stderr. It calls `get_template` on every call and does not cache templates. |
| `totals()` | Counts for the whole list. |

### Thread use

The window calls `process_file` from one worker thread at a time. Between runs, it
calls `add_files`/`remove_files` from the Tk thread. The window guarantees these never
overlap (FR-016b), so the batch needs no locks.

### Not in this module

Printing, Tk widgets, threads, `image_to_text`, and AWS clients. The pre-run readability
check lives in the window (see [ui-windows.md](ui-windows.md)).

## Supporting changes in other modules

| Module | Change |
| --- | --- |
| `interpretation/student_data_sheet.py` | `_tables`/`_scalars` are created in `__init__` (R6). Changed public members gain annotations. |
| `interpretation/template_store.py` | Adds `check_readable(self) -> None`, which raises `UnreadableTemplatesError(file_path: str, reason: str)` when the file exists and is not valid JSON (R7). |
