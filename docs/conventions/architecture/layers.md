# Layered Pipeline

All application code lives under `therepy_sessions/`. It is organized as a one-way
pipeline with separate adapter and UI packages beside it.

```
clients/         external SDK construction only (boto3 Textract, Google Sheets)
collection/      source → StudentDataSheetImport         (OCR, image handling)
interpretation/  StudentDataSheetImport → StudentDataSheet (templates, interpreters)
storage/         StudentDataSheet → output destination   (DataSheetStore implementations: Google Drive/Sheets)
tk_utils/        shared Tkinter helpers
app_shell/       navigation shell windows (home screen, Setup menu); Tkinter only
students/        student setup records, student store, and windows; no pipeline imports
workspace/       Workspace folder rules and launch dialogs; no pipeline or students imports
program.py       composition root: parses args, opens the Workspace, builds clients, wires the layers
```

## Rules

1. **Dependencies point downstream only.** `collection` MUST NOT import from
   `interpretation` or `storage`. `interpretation` MUST NOT import from `storage` or
   `clients`. The only thing crossing the collection → interpretation boundary is
   `StudentDataSheetImport`. The only thing crossing interpretation → storage is
   `StudentDataSheet`. The sheet carries the template it was interpreted with
   (`StudentDataSheet.template`), and Storage reads the template, and its interpreters'
   public members, only through the sheet. Storage never loads templates itself.
2. **Collection normalizes and nothing else.** A collector turns vendor output (for
   example Textract blocks) into `form_data` (label → text, trailing `:` stripped) and
   `tables` (list of row-major 2D string arrays), with `table_titles` (the title above
   each table, trailing `:` stripped, `""` when none). It MUST NOT assign domain meaning.
3. **Interpretation is pure.** Interpreters take an Import and return data. They do no
   I/O, make no network calls, and touch no UI. The same input always produces the same
   output, so they can be exercised against saved sample Imports.
4. **Vendor details stay in their layer.** Textract response shapes belong in
   `collection/`. Sheets API request bodies belong in `storage/`. Nothing else references them.
5. **UI is a shell.** Tkinter windows (`interpretation/template_manager/*_window.py`,
   `interpretation/importing/*_window.py`, `students/*_window.py`) collect input and
   call into stores and interpreters. Business rules MUST NOT live in widget callbacks.
6. **Wiring happens in `program.py`.** Only the composition root decides which concrete
   clients, stores, and templates run together.
7. **The app shell knows only Tkinter.** `app_shell/` MUST NOT import from `clients/`,
   `collection/`, `interpretation/`, or `storage/`. It gets everything it opens through
   callbacks wired in `program.py`.
8. **Students stand apart from the pipeline.** `students/` MUST NOT import from
   `clients/`, `collection/`, `interpretation/`, or `storage/`. It reaches templates only
   through the `TemplateChoice` provider wired in `program.py`, and its data only through
   the injected `StudentStore`.
9. **Importing reaches students through the store.** `interpretation/importing/` may use
   `students/` only through an injected `StudentStore` and the `Student` record and its
   exceptions. It MUST NOT import student windows. It receives Imports only through an
   injected sheet reader, never by importing `collection.images`, so the only thing
   crossing collection → interpretation is still `StudentDataSheetImport`. This rule is
   one-way: rule 8 still keeps `students/` free of pipeline imports.
10. **Importing reaches storage through the Data Sheet Store.** `interpretation/importing/`
   saves sheets only through an injected `DataSheetStore`, the port defined in
   `interpretation/data_sheet_store.py`. Implementations live in `storage/`, which
   imports the port to implement it, and only `program.py` names one. So
   `interpretation/` still imports nothing from `storage/`.
11. **The Workspace stands apart.** `workspace/` MUST NOT import from `clients/`,
   `collection/`, `interpretation/`, `storage/`, or `students/`, and never builds a
   store. Its rules (`workspace.py`) import no Tkinter, and its dialogs live in
   `workspace_dialogs.py`. It creates Workspace files only through callables wired in
   `program.py` from each store's `create_empty_file`.

## Adding a new source or destination

- New input source (PDF, scanner, another OCR vendor): add a module under
  `collection/<kind>/` that returns `StudentDataSheetImport`.
- New output (CSV, a different spreadsheet layout): add a `DataSheetStore` subclass
  under `storage/` that accepts `StudentDataSheet` plus injected clients, and wire it in
  `program.py`. The import code and window need no change.

Any external service that receives student data is also subject to
[../../domain/student-data-privacy.md](../../domain/student-data-privacy.md).
