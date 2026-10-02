# Quickstart & Validation: View and Edit Data Sheet Templates

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-01

This is a manual validation guide (research R12). The behavior it checks is defined in
[contracts/](contracts/) and [data-model.md](data-model.md). It does not repeat them.

## Prerequisites

- `.venv` set up as the project README describes, and a desktop session.
- **Synthetic data only** (Principle I). Use the placeholder keys `AG`, `KT`, `JA`, and
  `MK`. No AWS or Google credentials are needed.
- Work from `therepy_sessions/` on scratch copies:

```sh
cd therepy_sessions
# V1–V2 (offline scripts) use their own folder
SCRATCH_OFFLINE=$(mktemp -d)
fresh_offline() {
  cp sample_data/templates.json "$SCRATCH_OFFLINE/templates.json"   # format 1 (bare list)
  cp sample_data/students.json  "$SCRATCH_OFFLINE/students.json"    # AG -> "4", KT -> "2"
}

# V3–V7 (in the app) use a separate folder that V1–V2 never touch
SCRATCH=$(mktemp -d)
cp sample_data/templates.json "$SCRATCH/templates.json"
cp sample_data/students.json  "$SCRATCH/students.json"
../.venv/bin/python3 program.py "$SCRATCH/templates.json" "$SCRATCH/students.json"
```

Run `fresh_offline` before V1, and again before **every** V2 row (or have the scratch
script copy the samples itself at the start of each row). Several V2 rows create,
change, or break the files, and each row's expected result assumes the untouched
samples.

## V1. Rules offline (FR-006a–f, FR-008, FR-009, FR-010c–f; R1, R2, R4, R9)

Write a scratch script, which is not committed, that imports `template_rules` and loads
templates from a `TemplateStore` on `$SCRATCH_OFFLINE/templates.json`.

| Check | Expected |
| --- | --- |
| `validate_template("  ", [])` | Both "name is required" and "at least one interpreter" are returned |
| `validate_template("X", [a titled "T", b titled "T"])` | One duplicate-title problem naming `T` |
| `validate_template("X", [a titled "", b titled ""])` (as in template "Test3") | `[]` |
| `TemplateDraft.from_template(t)`, change nothing | `has_changes_from(t)` is `False` |
| Draft `move(0, +1)`, then `move(1, -1)` | Same order as before. `has_changes_from` is `False`. |
| Draft `replace(0, x)` where `x` has another interpreter's title | `TitleConflictError`, and the draft is unchanged |
| Draft `replace(0, x)` | `interpreters[0].id` is the old id, and the position is unchanged |
| `group_usage([("AG","4"),("KT","2"),("JA","4"),("BK",None)])` | `keys_for("4") == ["AG","JA"]`, `count_for("3") == 0` |
| `save_confirmation(..., "3", usage)` | `None` |
| `save_confirmation(..., "4", usage)` | The text names `AG, JA` |
| `save_confirmation(..., "4", None)` / `delete_confirmation(..., None)` | The "could not be checked" texts |
| `delete_template_and_clear_students` where clearing raises | The exception propagates, and the delete callable is never called |
| The same, where the delete raises after a clear | `FAILED_AFTER_CLEARING`, with the cleared keys |
| The same, where the delete returns `False` and usage is empty | `NOT_FOUND`, and clearing is never called |

## V2. Stores offline (FR-006c, FR-006d, FR-010f; R6, R9, R10)

Every row starts from fresh copies in `$SCRATCH_OFFLINE` (see Prerequisites).

| Check | Expected |
| --- | --- |
| `TemplateStore` on the format 1 copy: `get_all_templates()` | Every template loads, each with `description == ""` |
| `check_readable()` on format 1, then on the file after a save | No error both times. After the save, the file is an object with `format_version: 2`. |
| `create_template` (gets id `6`), `delete_template("6")`, then `create_template` again | The second template gets id `7`, never `6` |
| `edit_template("4", dto with a description)`, then reload | The description is kept, the id is still `4`, and the list position is unchanged |
| Write `{"format_version": 3, "templates": []}`, then `check_readable()` | `UnreadableTemplatesError` |
| Write `{` into the file, then `create_template(...)`, `edit_template(...)`, and `delete_template(...)` | Each raises `UnreadableTemplatesError`. The file still contains exactly `{`. |
| Edit template `4` (any change to its name or description), reload it, then call `to_data_sheet_interpreter()` on `sample_data/imports/ag_second_sheet.json` (loaded as `StudentDataSheetImport(d["form_data"], d["tables"])`) | It interprets without error, as it did before the edit (FR-012, SC-004) |
| `JsonStudentStore.clear_current_template("4")` on the students copy | Returns `["AG"]`. `AG` now has `None`, and `KT` is unchanged. |
| `clear_current_template("99")` | Returns `[]`, and the file's modification time is unchanged |

## V3. View mode (User Story 1)

1. Go to Setup → Data Sheet Templates. **Expect**: a Students column with `1` for
   "Blah" (id `4`), `1` for "Test2", and `0` for "Test3" and "Testing back".
2. Double-click "Test3". **Expect**: the window opens in view mode, showing the name,
   the ID `3`, an empty description, and two interpreters. Their child rows read
   `Fields: Define tone` and `Columns: Sentence, Pitch, Speed, Body`. Used by: "No
   students use this template."
3. Try typing in the Name field. **Expect**: it is read-only. Close the window.
   **Expect**: no prompt, and nothing changed.
4. Select nothing and press View. **Expect**: "Please select a template first."

## V4. Edit and save (User Story 2)

1. Select "Blah" and press **Edit**. **Expect**: the window opens directly in edit mode.
2. Rename it to "Blah 2", add a description, select the first interpreter, add a field
   to its form, then select a different interpreter without pressing Apply.
   **Expect**: the change is applied (the tree shows the new field).
3. Add a Running Tally interpreter, move it up, and press Save. **Expect**: a
   confirmation that names `AG`. Choose No. **Expect**: still in edit mode, with
   nothing lost.
4. Save again and choose Yes. **Expect**: the window returns to view mode with the new
   values. The list shows "Blah 2" with Students `1`.
5. Relaunch, then open Setup → Students. **Expect**: `AG` still has "Blah 2". The
   template's details match step 4.
6. Edit "Test3" (no students) and give both interpreters the title `X`. **Expect**: the
   second Apply is refused with a duplicate-title message. Save is never reached.

## V5. Leave without saving (User Story 3)

1. Edit "Test2", change its name, and press Cancel. **Expect**: "Discard your changes?"
   Choose No, and you are still editing. Press Cancel again and choose Yes. **Expect**:
   view mode with the original name.
2. Edit, change nothing, and press Cancel. **Expect**: view mode, with no prompt.
3. Edit, change an interpreter form without applying it, and close the window.
   **Expect**: the discard prompt.
4. In the form, change a value and press the form's **Cancel**. **Expect**: the form
   shows the saved values again, and other edits stay.

## V6. Delete a template in use (User Story 4)

1. Delete "Test2". **Expect**: the confirmation names `KT` and says a new template is
   needed. Choose No. **Expect**: nothing changes.
2. Delete "Test2" again and choose Yes. **Expect**: it is deleted. Setup → Students
   shows `KT` with no Current Template, and it still does after a relaunch.
3. Delete "Test3" (unused). **Expect**: the plain confirmation.
4. Create a new template. **Expect**: its ID is not `2` or `3`, or any other ID used
   before.

## V7. Failures (edge cases, FR-010d, FR-013, FR-014)

1. Write `{` into `"$SCRATCH/templates.json"` (back up the file first) and open Data Sheet
   Templates. **Expect**: "Could not read the templates file: …" and an empty list.
   Press Create New Template and save one. **Expect**: an error, and the file still
   contains exactly `{`. Restore the backup.
2. Back up `"$SCRATCH/students.json"`, write `{` into it, and reopen Data Sheet Templates.
   **Expect**: Students shows `Unknown`, and the details say usage could not be
   determined. Save asks the "could not be checked" question. Delete warns that no
   student records will be changed. Restore the backup.
3. Open the management window. In another shell, remove one template from
   `"$SCRATCH/templates.json"`. Then press View on it. **Expect**: "This template no
   longer exists", and the list refreshes.
4. Open a template in edit mode. Run `chmod a-w "$SCRATCH"` and press Save.
   **Expect**: "The change was not saved", still in edit mode with the changes intact,
   and the file is unchanged. Run `chmod u+w "$SCRATCH"` afterwards.

## V8. Older templates and imports still work (FR-012, SC-004)

Run an import (feature 003's quickstart V4) with `AG`'s edited template on a matching
synthetic sample. **Expect**: it is interpreted with the edited template. This step
needs Textract credentials, so skip it when working offline.
