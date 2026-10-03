# Quickstart & Validation: Save Imported Sessions to Google Drive

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-02

This is a validation guide (research R12). The behavior it checks is defined in
[contracts/](contracts/) and [data-model.md](data-model.md).

## Prerequisites

- `.venv` set up per the project README, and a desktop session.
- **Synthetic data only** (Principle I): placeholder keys (`AG`, `JA`, `BK`), the
  synthetic images and Imports in `therepy_sessions/sample_data/`, and scratch copies of
  `templates.json` and `students.json`:

  ```sh
  cd therepy_sessions
  SCRATCH=$(mktemp -d)
  cp sample_data/templates.json "$SCRATCH/templates.json"
  cp sample_data/students.json  "$SCRATCH/students.json"
  ```

- **V1–V3** run offline, with no credentials.
- **V4 and later** need:
  - AWS credentials for Textract (as in feature 003)
  - a Google OAuth client secret outside the repo, pointed to by
    `SLP_GOOGLE_CLIENT_SECRET_FILE`
  - ideally a **test Google account**, so the Drive holds nothing but synthetic
    workbooks
- Scratch scripts are not committed.

## V1. Template Structure offline (FR-008, FR-009, SC-004)

In a scratch script, load templates from the scratch `templates.json` and call
`storage.template_structure.shape_of(template)` and `.structure_fingerprint()`.

| Check | Expected |
| --- | --- |
| The same template twice | Equal fingerprints, starting with `s1-` |
| A copy with the sections, fields, and columns reordered | Equal fingerprint |
| A copy that renames the template and changes its description | Equal fingerprint |
| A copy with different choice options or tally type | Equal fingerprint |
| A copy with one column renamed, added, or removed | Different fingerprint |
| A copy with a section title renamed | Different fingerprint |
| Interpreting a sample Import | `sheet.template` is the template used, and every table has a `section_id` |

## V2. Layout functions offline (FR-015–FR-025a)

Call the `storage/session_layout.py` functions directly.

| Check | Expected |
| --- | --- |
| `cell_for` on an `INT` `"7"` / an `INT` `"7a"` / a `TEXT` `"007"` / a raw str `"9/14"` / `""` | number 7 / text `"7a"` / text `"007"` / text `"9/14"` / empty |
| `tab_base_name` with `9/14/2026` and `11:00 AM` / with a blank time | `9/14/2026 11:00 AM` / `9/14/2026` |
| `tab_base_name` of a 150-character date containing a newline | 100 characters or fewer, with no control characters |
| `unique_tab_name("9/14/2026", {"9/14/2026", "9/14/2026 2"})` | `9/14/2026 3` |
| `matches`: same date and time with different case or spaces / either time blank | `True` / `False` |
| `insert_index` of 9/14 11:00 AM into [9/16 11:00, 9/10 11:00] | `1` |
| `insert_index` of 9/14 1:30 PM into [9/14 11:00 AM] | `0` |
| `insert_index` of a blank-time 9/14 into [9/14 11:00 AM, 9/14 (blank)] | `1` (after the timed tab, before the older blank one) |
| `insert_index` with an unreadable date | Placed after every dated tab |
| `session_rows` for a sheet with a form section and a table | The 6 header rows, then the form fields, a blank row, then a title row, a column row, and data rows. No choice lists, types, or ids appear. |
| `session_rows` with a layout whose columns are in a different order than the sheet's template | Values follow the layout's column order |

## V3. Batch and store with fakes offline (FR-002–FR-004, FR-016a, FR-017)

- Build a `SheetImportBatch` with the feature 003 fakes plus an in-memory fake
  `DataSheetStore` that records the sheets it receives.
- Build a `GoogleDriveDataSheetStore` with fake Drive and Sheets services. The fakes are
  in-memory dicts that record each request and can be told to raise `HttpError`.

| Check | Expected |
| --- | --- |
| A sheet with a blank Date | `FAILED` / `MISSING_DATE`; the store's `save` is not called |
| The fake store's `save` raises `DataSheetStoreError` | `FAILED` / `SAVE_FAILED`, and the message starts "Could not save to Google Drive". The next pass reuses the Import, with no new read. |
| The fake store returns `already_saved=True` | `SUCCEEDED`; the message starts "Already saved", and `outcome.saved` is set |
| Sheet keyed ` ag ` is saved | The fake store receives `sheet.student_key == "AG"` (the stored key) and `sheet.template` set |
| Store: the first save for `AG` | A file is created in the folder with `appProperties` (key and fingerprint only), one `batchUpdate` (`addSheet` + `updateCells` + `deleteSheet` + `createDeveloperMetadata`) |
| Store: a second `AG` sheet, with the fake search returning nothing (search lag) | Reuses the cached workbook. No second file is created. |
| Store: the same date and Time IN again with different values | No `batchUpdate`; `already_saved=True` |
| Store: two blank-time sheets with the same date | Tabs `9/14/2026` and `9/14/2026 2` |
| Store: `batchUpdate` fails while creating a workbook | `files.delete` is called on the new file, and `DataSheetStoreError` is raised |
| Store: two workbooks match | The one listed first (newest `modifiedTime`) is used |
| Inspect every recorded `appProperties` and developer-metadata body | Holds no Goal, Measure, or table value (FR-028) |

## V4. First save end to end (US1, US2)

```sh
cd therepy_sessions
../.venv/bin/python3 program.py "$SCRATCH/templates.json" "$SCRATCH/students.json"
```

1. Go to Home → **Import**, add one synthetic sheet for `AG`, and press **Import**.
2. If no token is cached, a browser sign-in opens while the window shows "Connecting to
   Google Drive…". Complete it.

**Expect**:

- The row shows **✓ Succeeded**, with "Saved to AG - <template> › <date> <time>".
- In Drive, `SLP Therepy Data/Current Year/AG - <template>` exists, with exactly one tab
  named by the sheet's Date and Time IN.
- The tab holds the values only, in the layout from V2.
- **Open** (and double-clicking the row) opens that tab in the browser.

## V5. Workbook selection (US3)

1. Import an `AG` sheet with a different date. **Expect** a second tab in the same
   workbook, in newest-first position.
2. In the scratch `templates.json`, copy `AG`'s template under a new name with its
   columns reordered, and assign it to `AG`. Import again. **Expect** the same workbook,
   with columns written in the original order.
3. Assign `AG` a template with the same name but one column renamed. Import. **Expect** a
   new workbook.
4. Rename the first workbook in Drive, assign `AG` the original template, and import.
   **Expect** a tab added to the renamed workbook.
5. Trash that workbook and import. **Expect** a new workbook.

## V6. Duplicates and blank times (US4)

1. Re-import the V4 photo in a new Import window visit. **Expect** "Already saved in …",
   and no new tab.
2. Import a sheet with the same date and a blank Time IN, twice. **Expect** the tabs
   `<date>` and `<date> 2`, after the timed tab for that date.

## V7. Failures (FR-006a, edge cases)

1. Turn off networking and press **Import**. **Expect** "Cannot start the import", with
   no row processed and no Textract call.
2. Turn networking back on, start an import of three sheets, and turn networking off
   after the first sheet saves. **Expect** the remaining rows to show **✗ Failed** with
   "Could not save to Google Drive: no connection…". Turn networking back on and press
   Import. **Expect** them to save, with no duplicate tab for the first sheet.

## V8. Privacy check (Principle I)

- `git status` shows no token, client secret, sample output, or workbook export staged.
- No log file was written under `therepy_sessions/`.
