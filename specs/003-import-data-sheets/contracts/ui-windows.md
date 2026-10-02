# Contract: Import Window and Wiring

## `ImportWindow`

**Module**: `therepy_sessions/interpretation/importing/import_window.py` (replaces the placeholder)

```python
class ImportWindow:
    def __init__(
        self,
        master: tk.Toplevel,
        batch: SheetImportBatch,
        check_records_readable: Callable[[], None],
        on_sheet_interpreted: Callable[[StudentDataSheet], None],
        on_back: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None: ...
```

| Parameter | Meaning |
| --- | --- |
| `batch` | A new, empty `SheetImportBatch` for each visit, so the list is not kept after leaving (spec assumption). |
| `check_records_readable` | Called on the Tk thread when Import is pressed. It raises `UnreadableStudentRecordsError` or `UnreadableTemplatesError` if a file is unreadable (R7). |
| `on_sheet_interpreted` | Called on the Tk thread, once per succeeded sheet, in list order (R3). |
| `on_back` / `on_exit` | Unchanged from the placeholder: Back returns home, and the title-bar close exits. |

### Widgets and behavior

The layout follows research R12, and the enabled/disabled rules follow the data-model
*Window states*.

| Action | Behavior | Spec |
| --- | --- | --- |
| **Add Files…** | `askopenfilenames` with the image file type (R10). Cancel leaves the list unchanged. Added rows show **Not imported**. | FR-001–FR-004, US2 |
| **Remove Selected** | Removes every selected row. Off when nothing is selected. | FR-005 |
| **Import** | Runs `check_records_readable()`. If it raises, shows `error_handling.throw(e, "Cannot start the import")` and starts nothing. Otherwise starts the worker over `batch.files_to_process()`. | FR-007, FR-008, edge case |
| *(running)* | The current row shows **Importing…**. The progress bar and "Importing n of m…" update after each file. Each finished file updates its row right away. | FR-016 |
| **Cancel** | Sets the stop flag. The button shows **Cancelling…** until the current file finishes. Rows not reached stay **Not imported**. | FR-016a |
| *(finished/cancelled)* | Re-enables the controls. Shows "This run: s succeeded, f failed · Whole list: S succeeded, F failed, N not imported" (plus "Cancelled." when relevant). | FR-015, FR-016b |
| Row, succeeded | Status **Succeeded**, Student Key, template name, and an empty Details column. | FR-015 |
| Row, failed | Status **Failed**, the Student Key if read, the template name if one was used, and Details set to the R5 message. | FR-013, SC-004 |
| Title-bar ✕ | `on_exit()` in every state. The daemon worker dies with the process. | FR-017 |

### Threading contract (R3)

- Only the worker thread calls `batch.process_file`. Only the Tk thread touches widgets
  or calls `on_sheet_interpreted`.
- The worker → Tk queue carries events of three kinds: `("started", identity)`,
  `("finished", identity, ProcessedSheet)`, and `("done", cancelled: bool)`.
- The window polls every 100 ms while a run is active, and stops polling after `done`.
  It also stops if the window has been destroyed.

## `program.py` wiring

```python
textract_lock = threading.Lock()
textract_client: Any = None   # boto3 Textract client, built on first use (R8)

def inject_textract_client() -> Any: ...   # lock; construct_textract_client() once

def check_records_readable() -> None:
    student_store.list_students()
    template_store.check_readable()

def open_import_path() -> None:
    path_window = _open_child_window(root, root)
    ImportWindow(
        path_window,
        SheetImportBatch(
            read_sheet=lambda path: image_to_text(path, inject_textract_client),
            student_store=student_store,
            get_template=template_store.get_template_by_id,
        ),
        check_records_readable,
        on_sheet_interpreted=lambda sheet: sheet.debug(),
        on_back=lambda: _return_to(root, path_window),
        on_exit=root.destroy,
    )
```

The launch command is unchanged from feature 002
(`program.py <templates.json> <students.json>`). `program_interpret.py` is deleted (R9).
