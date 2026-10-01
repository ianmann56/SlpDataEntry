# Research: Import Data Sheets

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-01

Each decision records what was chosen, why, and what else was considered. The Technical
Context in [plan.md](plan.md) had no open NEEDS CLARIFICATION items; these decisions
settle the design questions the spec left to planning.

## R1. Where the import logic lives

**Decision**: Split the feature into two modules under `interpretation/importing/`:

- `sheet_import_batch.py`: no Tkinter. It holds the list of Selected Files and the
  rules for adding, removing, choosing which files to process, and processing one file
  (read → find student → load template → interpret → classify failure).
- `import_window.py`: the Tkinter window. It shows the list, runs the batch on a worker
  thread (R3), and displays outcomes. It holds no import rules.

**Rationale**: Layers rule 5 says business rules must not live in widget callbacks.
Keeping the batch free of Tkinter means it can be checked offline with fakes (R11).

**Alternatives considered**: putting everything in the window. This was rejected
because it breaks layers rule 5 and can only be tested by clicking. A new top-level
`importing/` package was also rejected: `layers.md` already names
`interpretation/importing/*_window.py` as the home of the import UI.

## R2. How the batch reaches collection, students, and templates

**Decision**: Everything the batch needs is injected through its constructor and wired
in `program.py`:

| Need | Injected as | Wired to |
| --- | --- | --- |
| Read a sheet | `read_sheet: Callable[[str], StudentDataSheetImport]` | `lambda path: image_to_text(path, inject_textract_client)` |
| Find a student | `student_store: StudentStore` | the one `JsonStudentStore` |
| Load a template | `get_template: Callable[[str], StudentDataSheetTemplate \| None]` | `template_store.get_template_by_id` |
| Use a result | `on_sheet_interpreted: Callable[[StudentDataSheet], None]` | `lambda sheet: sheet.debug()` |

**Rationale**: Layers rule 1 allows only `StudentDataSheetImport` to cross from
collection to interpretation, so the batch must not import `image_to_text` itself.
Injecting the result sink keeps printing (a temporary stand-in for Storage) out of
interpretation, and the later Storage feature can replace it in `program.py` alone.
Dependency-injection rule 6 already has windows receive `StudentStore`.

**Amendment**: `layers.md` gains rule 9: `interpretation/importing/` may use
`students/` only through the injected `StudentStore` and the `Student` record. It must
not import student windows. The rule is one-way, so rule 8 (students imports no
pipeline package) still holds. Constitution 1.3.0 → 1.4.0 (MINOR).

**Alternatives considered**: injecting a `find_current_template_id(key)` function
instead of the store. This was rejected because it hides the "student not found" vs
"no Current Template" distinction the spec requires (FR-013) inside wiring code in
`program.py`.

## R3. Keeping the window responsive (FR-016, SC-005)

**Decision**: Press Import → the window runs a quick check on the main thread (R7),
then starts one daemon `threading.Thread`. The thread processes files one at a time and
posts events (`started(path)`, `finished(path, outcome)`, `done(cancelled)`) to a
`queue.Queue`. The window polls the queue with `after(100, ...)` and applies events on
the Tk thread. Cancel sets a `threading.Event`, which the worker checks before each
file. A file already being processed finishes (FR-016a).

The successful `StudentDataSheet` travels inside the `finished` event, and
`on_sheet_interpreted` is called on the Tk thread when the event is applied. Console
output therefore always follows list order and never interleaves.

**Rationale**: Each Textract call takes seconds, so running it on the Tk thread freezes
the window. Tkinter is not thread-safe, so only the main thread touches widgets. A daemon
thread lets the title-bar close exit at once (spec edge case). A sheet whose processing
had not finished produces no event, so nothing partial is printed.

**Alternatives considered**: `after()`-chained processing on the main thread, where
each Textract call still blocks repaint for its duration. `concurrent.futures` was
also rejected: parallel reads are out of scope, and a single thread is simpler.

## R4. Reusing readings and spotting changed files (FR-008a)

**Decision**: Each Selected File keeps its `StudentDataSheetImport` and the file's
`st_mtime_ns` taken just before reading. On each Import press, every file that has not
succeeded is processed:

1. `stat` the file. If that fails → `FILE_UNREADABLE`.
2. If the file has no saved Import, or its `st_mtime_ns` differs from the saved one →
   read it again with `read_sheet`. Otherwise, reuse the saved Import.
3. If the read fails, discard any saved Import so the next press tries again.

A succeeded file is skipped even if it has since changed. Removing a file discards its
Import. The stat function is injectable (it defaults to `os.stat`) so offline checks
can simulate a changed file.

**Rationale**: The modified time is a cheap and reliable signal that a retake was saved
over the old photo, and it costs no extra Textract calls. Nanosecond resolution avoids
missing a quick overwrite.

**Alternatives considered**: hashing the file contents. This is more exact, but it
reads every image on each press, and the modified time is enough to tell when a retake
was saved over the old photo.

## R5. Failure reasons and messages (FR-013, SC-004)

**Decision**: A `FailureReason` enum. Each reason has a fixed message pattern that names
the fix. The Student Key is the only student detail shown (FR-019).

| Reason | Detected when | Message (and the fix it points to) |
| --- | --- | --- |
| `FILE_UNREADABLE` | `stat` fails, or `read_sheet` raises `FileNotFoundError`/`OSError` | "The file could not be opened. Check it still exists, or add it again." |
| `READING_FAILED` | `read_sheet` raises anything else (Textract, credentials, network) | "The sheet could not be read: {error}. Check the connection, or retake the photo." |
| `NO_STUDENT_KEY` | `form_data.get("Student Key", "")` is blank after trimming | "No Student Key was found on the sheet. Retake the photo so the key is clear." |
| `UNKNOWN_STUDENT` | `student_store.get_student(key)` returns `None` | "No student has the Student Key \"{key}\". Add the student in Setup, or retake the photo." |
| `NO_CURRENT_TEMPLATE` | the student's `current_template_id` is `None` | "Student {key} has no Current Template. Choose one in Setup → Students." |
| `TEMPLATE_MISSING` | `get_template(id)` returns `None` or raises | "Student {key}'s Current Template no longer exists or could not be loaded. Choose another in Setup → Students." |
| `TEMPLATE_MISMATCH` | interpretation raises (`KeyError` for a missing header field, or an interpreter's mismatch exception) | "The sheet does not match template \"{name}\": {detail}. Fix the template, or retake the photo." |
| `STUDENT_RECORDS_UNREADABLE` | `UnreadableStudentRecordsError` during the run (the file broke after the R7 check) | "The student records could not be read. Fix them in Setup → Students." |

`KeyError` from the header fields is turned into the detail "the sheet has no 'Date'
field". Each underlying exception is also printed to the console with its traceback, as
`tk_utils.error_handling.throw` does for other errors.

**Rationale**: SC-004 requires the SLP to pick the fix from the window alone. A fixed
set of reasons also makes the offline checks exact.

**Alternatives considered**: showing raw exception text only. This was rejected because
messages like "KeyError: 'Date'" don't tell the SLP what to do.

## R6. Shared state in `StudentDataSheet`

**Decision**: Move `StudentDataSheet._tables` and `._scalars` from class attributes to
attributes created in `__init__`.

**Rationale**: They are class-level `[]` and `{}`, and `register_table` and
`register_scalar` mutate them. Every sheet in a batch would therefore print the tables
of all earlier sheets. Interpreters rule 3 already requires the fix when the class is
touched. `TableInterpreter._columns` and `SimpleFormInterpreter._fields` are reassigned
in `__init__`, so they don't share state and are left as they are.

**Alternatives considered**: none. Without this fix, SC-002 cannot pass.

## R7. Checking the records files before an import starts

**Decision**: When Import is pressed, before the worker starts, the window calls
`student_store.list_students()` and a new `TemplateStore.check_readable()`. If either
raises, the window shows the error with `error_handling.throw` and no import starts.
`check_readable()` raises a new `UnreadableTemplatesError` when the templates file
exists but is not valid JSON.

**Rationale**: This is the spec edge case "records or templates file cannot be read →
import does not start". `TemplateStore._load_templates_from_file` currently turns a
corrupt file into `[]`, which would show every sheet as "template missing". That points
the SLP at the wrong fix. A separate check method leaves the template windows' current
behavior unchanged.

**Alternatives considered**: making `_load_templates_from_file` raise. That is the
right long-term fix, but it changes behavior in the template management windows, which
are outside this feature.

## R8. Building the Textract client

**Decision**: `program.py` defines `inject_textract_client()`. It calls
`construct_textract_client()` the first time it is used, under a `threading.Lock`, and
reuses that client afterward. Nothing AWS-related is built at launch, so the Setup path
still works without credentials.

**Rationale**: Dependency-injection rules 1–3. boto3 clients are safe to share once
built. Missing credentials surface as `READING_FAILED` on each sheet, with boto's
message.

**Alternatives considered**: building the client at launch. This was rejected because
the app would then need AWS credentials even when only Setup is used.

## R9. Retiring `program_interpret.py`

**Decision**: Delete `therepy_sessions/program_interpret.py` in this feature.

**Rationale**: Its docstring says to delete it once the import path exists. Deleting
it also removes feature 001's recorded Principle III deviation (a second composition
root). The Import window does everything it did, for any number of files.

**Alternatives considered**: keeping it for single-template debugging. This was
rejected because it is the only remaining deviation from Principle III, and a sheet
can be checked against a template by setting that template as the student's Current
Template.

## R10. The file picker (FR-001, FR-002)

**Decision**: Use `tkinter.filedialog.askopenfilenames` with one file type, `("Images",
"*.png *.PNG *.jpg *.JPG *.jpeg *.JPEG *.tif *.TIF *.tiff *.TIFF")`, and no "All files"
entry. The batch also rejects any path without one of those extensions, comparing case
by case-folding. List identity is `os.path.normcase(os.path.realpath(path))`, the same
rule `program.py` uses to compare storage paths.

**Rationale**: Tk's patterns are case-sensitive on Linux, so upper-case variants are
listed. Checking the extension in the batch too keeps FR-002 true however a path gets
in. These are the image types Textract's `AnalyzeDocument` accepts.

## R11. Verification approach

**Decision**: Same approach as feature 002: a manual [quickstart.md](quickstart.md)
plus `python -c` checks of `sheet_import_batch` that use a fake `read_sheet`, an
in-memory `StudentStore` fake, and inline synthetic `StudentDataSheetImport`s. These
checks make no Textract calls and need no credentials. The quickstart has one optional
live step that uses the synthetic images in `sample_data/`.

**Rationale**: The project has no test framework, and adding one is a separate
decision. Principle IV is what makes offline checks possible.

## R12. Window layout

**Decision**: A `ttk.Treeview` (multi-select) with columns **File**, **Status**,
**Student Key**, **Template**, **Details**. Below it: **Add Files…**, **Remove
Selected**, **Import**, **Cancel**, **Back**, a determinate `ttk.Progressbar` with
"Importing 3 of 10…", and a summary line such as "This run: 2 succeeded, 1 failed · Whole
list: 9 succeeded, 1 failed, 0 not imported". The file name is shown, and the full path
appears in **Details** until the file is processed.

**Rationale**: This covers FR-006, FR-015, FR-016, FR-016a, and FR-016b with stock ttk
widgets that the `sv-ttk` theme already styles.
