# Layered Pipeline

All application code lives under `therepy_sessions/`. It is organized as a one-way
pipeline with separate adapter and UI packages beside it.

```
clients/         external SDK construction only (boto3 Textract, Google Sheets)
collection/      source → StudentDataSheetImport         (OCR, image handling)
interpretation/  StudentDataSheetImport → StudentDataSheet (templates, interpreters)
storage/         StudentDataSheet → output destination   (Google Sheets)
tk_utils/        shared Tkinter helpers
program.py       composition root: parses args, builds clients, wires the layers
```

## Rules

1. **Dependencies point downstream only.** `collection` MUST NOT import from
   `interpretation` or `storage`. `interpretation` MUST NOT import from `storage` or
   `clients`. The only thing crossing the collection → interpretation boundary is
   `StudentDataSheetImport`. The only thing crossing interpretation → storage is
   `StudentDataSheet`.
2. **Collection normalizes and nothing else.** A collector turns vendor output (for
   example Textract blocks) into `form_data` (label → text, trailing `:` stripped) and
   `tables` (list of row-major 2D string arrays). It MUST NOT assign domain meaning.
3. **Interpretation is pure.** Interpreters take an Import and return data. They do no
   I/O, make no network calls, and touch no UI. The same input always produces the same
   output, so they can be exercised against saved sample Imports.
4. **Vendor details stay in their layer.** Textract response shapes belong in
   `collection/`. Sheets API request bodies belong in `storage/`. Nothing else references them.
5. **UI is a shell.** Tkinter windows (`template_manager/*_window.py`) collect input and
   call into stores and interpreters. Business rules MUST NOT live in widget callbacks.
6. **Wiring happens in `program.py`.** Only the composition root decides which concrete
   clients, stores, and templates run together.

## Adding a new source or destination

- New input source (PDF, scanner, another OCR vendor): add a module under
  `collection/<kind>/` that returns `StudentDataSheetImport`.
- New output (CSV, a different spreadsheet layout): add a module under `storage/` that
  accepts `StudentDataSheet` plus injected clients.

Any external service that receives student data is also subject to
[../../domain/student-data-privacy.md](../../domain/student-data-privacy.md).
