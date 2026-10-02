# Data Model: Import Data Sheets

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-01

Nothing in this feature is saved to disk. Every entity below lives only while the
Import window is open. Existing entities (`StudentDataSheetImport`, `Student`,
`StudentDataSheetTemplate`, `StudentDataSheet`) are used unchanged, except for the
shared-state fix in R6.

## SelectedFile

One image the SLP added to the list. Module: `interpretation/importing/sheet_import_batch.py`.

| Field | Type | Meaning |
| --- | --- | --- |
| `path` | `str` | Path as picked. Shown as its file name. |
| `identity` | `str` | `os.path.normcase(os.path.realpath(path))`. Unique within the list (FR-004). |
| `outcome` | `SheetOutcome` | Latest result. Starts as `NOT_IMPORTED`. |
| `sheet_import` | `StudentDataSheetImport \| None` | Saved reading, reused on later presses (FR-008a). |
| `read_mtime_ns` | `int \| None` | The file's `st_mtime_ns` just before `sheet_import` was read. |

**Rules**

- Only `.png`, `.jpg`, `.jpeg`, `.tif`, and `.tiff` (any case) can be added (FR-002).
- Adding a path whose `identity` is already in the list does nothing (FR-004).
- Removing a file drops its `sheet_import`.
- Add and remove are refused while a run is in progress (FR-016b).

## SheetOutcome

Typed record (`NamedTuple`) describing one file's result.

| Field | Type | Meaning |
| --- | --- | --- |
| `status` | `SheetStatus` | `NOT_IMPORTED`, `SUCCEEDED`, or `FAILED` |
| `student_key` | `str \| None` | Key read from the sheet, once known |
| `template_name` | `str \| None` | Template used. Set on success, and on `TEMPLATE_MISMATCH`. |
| `failure_reason` | `FailureReason \| None` | Set only when `FAILED` |
| `message` | `str` | Text for the **Details** column. Uses only the Student Key (FR-019). |

`FailureReason` values and their messages: [research.md R5](research.md#r5-failure-reasons-and-messages-fr-013-sc-004).

## State transitions (per file)

```text
           add
            │
            ▼
      NOT_IMPORTED ──process──► SUCCEEDED   (terminal for the window session;
            ▲   │                            skipped by later presses)
            │   └──process──► FAILED ──process (next press)──► SUCCEEDED | FAILED
            │
   (Cancel before the file is reached: stays NOT_IMPORTED)
```

While a file is being processed, the window shows **Importing…** in its row. This is
display-only and is not a stored status.

**Processing one file** (in order; the first failing step sets the outcome):

1. `stat` → `FILE_UNREADABLE`
2. Reuse `sheet_import` if `read_mtime_ns` matches; otherwise `read_sheet` →
   `FILE_UNREADABLE` / `READING_FAILED` (a failed read clears `sheet_import`)
3. Student Key from `form_data["Student Key"]`, trimmed → `NO_STUDENT_KEY`
4. `student_store.get_student(key)` → `UNKNOWN_STUDENT` / `STUDENT_RECORDS_UNREADABLE`
5. `current_template_id` → `NO_CURRENT_TEMPLATE`
6. `get_template(id)` → `TEMPLATE_MISSING`
7. `template.to_data_sheet_interpreter().interpret_student_data_sheet(import)` →
   `TEMPLATE_MISMATCH`
8. `SUCCEEDED` with key and template name. The `StudentDataSheet` is handed to
   `on_sheet_interpreted`.

The template is loaded fresh for each file (FR-010). Templates are never cached across
files or presses.

## ImportRun (the spec's Import Run)

The files processed by one press of Import. The whole list and its rules are the
**Import Batch** (`SheetImportBatch`).

ImportRun is not a class. The Import window keeps it as state for the duration of a
run: the identities passed to the worker, the counts of `finished` events by status,
and whether Cancel was pressed.

| Field | Type | Meaning |
| --- | --- | --- |
| `files` | `list[SelectedFile]` | Files not `SUCCEEDED` at press time, in list order |
| `succeeded` | `int` | Count this run |
| `failed` | `int` | Count this run |
| `cancelled` | `bool` | Cancel was pressed before the last file |

## ListTotals

Computed from the whole list after every outcome change (FR-015).

| Field | Type |
| --- | --- |
| `succeeded` | `int` |
| `failed` | `int` |
| `not_imported` | `int` |

## Window states

| State | Import | Cancel | Add / Remove / Back | Progress |
| --- | --- | --- | --- | --- |
| Empty list | off | hidden | Add, Back on; Remove off | hidden |
| Idle with files (all succeeded) | off | hidden | on | hidden; summary shown |
| Idle with files (some not succeeded) | on | hidden | on | summary shown after a run |
| Running | off | on | off | "Importing n of m…" |
| Cancelling | off | off ("Cancelling…") | off | current file finishing |

FR-007 says Import needs at least one file. If every file has already succeeded, Import
is also off, because a press would have nothing to do.

The title-bar close exits the application in every state.
