# Quickstart & Validation: Import Data Sheets

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-01

This is a manual validation guide (research R11). The behavior it checks is defined in
[contracts/](contracts/) and [data-model.md](data-model.md).

## Prerequisites

- `.venv` set up per the project README, and a desktop session.
- **Synthetic data only** (Principle I): placeholder keys such as `JA`, `BK`, `ZZ`, and
  the images in `therepy_sessions/sample_data/`.
- Work from `therepy_sessions/` on scratch copies:

```sh
cd therepy_sessions
SCRATCH=$(mktemp -d)
cp sample_data/templates.json "$SCRATCH/templates.json"
cp sample_data/students.json  "$SCRATCH/students.json"
```

- V1–V3 need no network or credentials. V4 and later call AWS Textract and need
  credentials loaded as described in `therepy_sessions/README.md`.

## V1. Batch rules offline (FR-002–FR-005, FR-008a, FR-009–FR-014)

Write a scratch script, not committed, that builds a `SheetImportBatch` with:

- a fake `read_sheet` that counts calls per path and returns inline synthetic
  `StudentDataSheetImport`s;
- an in-memory `StudentStore` fake with `JA` → a valid template id, `BK` → `None`, and
  `ZZ` → a deleted id;
- `get_template` backed by a scratch `TemplateStore`;
- a fake `stat_mtime_ns` whose value the script can change.

**Expect**:

| Check | Expected |
| --- | --- |
| `add_files` with `a.png`, `a.png`, `./a.png`, `b.PDF` | One file added. `b.PDF` is skipped. |
| Sheet keyed ` ja ` | `SUCCEEDED`, `student_key == "ja"`, template name set |
| Sheet with no `Student Key` | `FAILED` / `NO_STUDENT_KEY` |
| Sheet keyed `QQ` | `FAILED` / `UNKNOWN_STUDENT`, and the message names `QQ` |
| Sheet keyed `BK` | `FAILED` / `NO_CURRENT_TEMPLATE` |
| Sheet keyed `ZZ` | `FAILED` / `TEMPLATE_MISSING` |
| `JA` sheet missing the `Date` field | `FAILED` / `TEMPLATE_MISMATCH`, and the detail names `Date`; no `data_sheet` returned |
| `read_sheet` raises | `FAILED` / `READING_FAILED`; the next `process_file` reads again |
| Second pass over `files_to_process()` | Succeeded files are absent. Failed files reuse their Import (`read_sheet` call count unchanged). |
| Change the fake mtime of one failed file, then process again | Only that file is read again |
| Two `JA` sheets interpreted in a row | Each `StudentDataSheet.tables` has only its own tables (R6) |

## V2. Records-file check (edge case, R7)

1. Write `{` into `"$SCRATCH/templates.json"` and call `TemplateStore(...).check_readable()`.
   **Expect**: `UnreadableTemplatesError`.
2. Restore the file. **Expect**: no error.

## V3. Window without imports (US2, FR-007, FR-017)

Launch with `../.venv/bin/python3 program.py "$SCRATCH/templates.json" "$SCRATCH/students.json"`.

1. Home → **Import & Interpret Student Data Sheets**. **Expect**: an empty list, and
   Import and Remove are off (US1 scenario 1).
2. **Add Files…**. **Expect**: the picker offers only the image type and allows
   multi-select. Pick two files from `sample_data/`.
3. **Add Files…** again with one more file and one already listed. **Expect**: three
   rows with no duplicate.
4. Cancel the picker. **Expect**: no change.
5. Select one row and choose **Remove Selected**. **Expect**: two rows. Remove both.
   **Expect**: Import is off.
6. **Back** → home. Reopen Import. **Expect**: the list is empty again.
7. ✕ in the title bar. **Expect**: the app exits.

## V4. Mixed batch (US1, SC-002, FR-011, FR-015)

Set up students in **Setup → Students** so that each sample image's Student Key belongs
to a student whose Current Template matches its layout.

1. Add those images and press **Import**. **Expect**: progress "Importing n of m…", and
   the window stays responsive. Drag it around to check (SC-005).
2. **Expect**: each row shows **Succeeded**, its Student Key, and its own template name.
   The console shows one `Data Sheet` block per file, in list order, and each block
   shows only that sheet's tables.
3. **Expect**: a summary such as "This run: 3 succeeded, 0 failed · Whole list: 3
   succeeded, 0 failed, 0 not imported".

## V5. Failures and retry (US3, SC-003, SC-004, FR-008a)

1. In Setup, clear the Current Template of one student. Also delete the student whose
   key appears on another image. Import those images plus one valid image.
   **Expect**: the valid image succeeds. The other two fail with the
   `NO_CURRENT_TEMPLATE` and `UNKNOWN_STUDENT` messages, and each message names the fix.
2. Go **Back**, fix the setup in Setup, and return. The list resets, so add the images
   again and press Import. **Expect**: all three succeed.
3. Without leaving the window: add a fourth image whose student has no Current Template,
   and Import. Then set that student's `current_template_id` by editing
   `"$SCRATCH/students.json"` in a text editor, and press Import again. **Expect**: succeeded rows are not re-run (no new console block for
   them), and the fixed row succeeds.
4. Copy an image to `"$SCRATCH/x.png"`, add it, then delete the file and press Import.
   **Expect**: **Failed**, with "The file could not be opened…".

## V6. Cancel (FR-016a, FR-016b)

1. Add at least four images and press Import. Press **Cancel** during the first file.
   **Expect**: **Cancelling…**, then the current file finishes. The remaining rows stay
   **Not imported**, and the summary includes "Cancelled.".
2. While the import was running, **Expect**: Add, Remove, Back, and Import were off.
3. Press Import again. **Expect**: only the rows not yet succeeded run.

## V7. Unreadable records (edge case)

With the window open, write `{` into `"$SCRATCH/students.json"` and press Import.
**Expect**: an error box, and nothing runs. Restore the file.

## V8. Privacy (FR-018, FR-019, Principle I)

- **Expect**: no new files under the repo or `$SCRATCH` after V4–V6, and console output
  only.
- **Expect**: window text names students only by Student Key.
- `git status` shows no images, Imports, or scratch scripts staged.
