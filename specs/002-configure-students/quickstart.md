# Quickstart & Validation: Students

**Feature**: [spec.md](spec.md) | **Date**: 2026-09-30

This is a manual validation guide (research R11). The behavior it checks is defined in
[contracts/](contracts/) and [data-model.md](data-model.md).

## Prerequisites

- `.venv` set up per the project README, and a desktop session.
- **Synthetic data only** (Principle I): placeholder keys such as `JA`, `BK`, `ZZ`.
- Work from `therepy_sessions/`, with scratch copies so the real files are never touched:

```sh
cd therepy_sessions
SCRATCH=$(mktemp -d)
cp sample_data/templates.json "$SCRATCH/templates.json"
```

## V1. Launch contract (FR-019)

| Command | Expected |
| --- | --- |
| `../.venv/bin/python3 program.py "$SCRATCH/templates.json"` | Two-argument usage message, exit status 1, no window |
| `../.venv/bin/python3 program.py "$SCRATCH/templates.json" students.txt` | "must be a JSON file" error, exit status 1 |
| `../.venv/bin/python3 program.py "$SCRATCH/templates.json" "$SCRATCH/templates.json"` | "must be different files" error, exit status 1 |
| `../.venv/bin/python3 program.py "$SCRATCH/templates.json" "$SCRATCH/students.json"` | Home screen opens. `students.json` does not exist yet. |

## V2. Navigation (User Story 4)

1. Home shows **Manage Setup & Configuration**. Click it.
   **Expect**: home hides, and **Setup** shows *Data Sheet Templates*, *Students*, and
   *Back*.
2. **Students** → the Students window. **Back** → Setup.
3. **Data Sheet Templates** → template management. **Back** → Setup.
4. **Back** → home.
5. Repeat 1–4 five times. **Expect**: only one window is visible at a time, with no
   errors in the terminal.
6. Title-bar ✕ on Setup, on Students, and on template management each exit the app.

## V3. Add and list (User Story 1)

1. Open Students. **Expect**: an empty list (FR-002, US1 scenario 1).
2. **Add Student**: key ` JA ` (with spaces), Current Template = any template. Save.
   **Expect**: the row shows `JA` and the template's name.
3. Add `BK` with **None selected**. **Expect**: `None selected` in the list.
4. Try to add a student with an empty key, a key of only spaces, and `ABCDEF`.
   **Expect**: each one is refused with the matching message, and the dialog stays open.
5. Try to add `ja`. **Expect**: "already in use" (SC-004).
6. Quit, relaunch with the same two paths, and open Students. **Expect**: `BK` and `JA`
   are listed (sorted) with the same details (SC-003).
7. `cat "$SCRATCH/students.json"`. **Expect**: the `format_version`/`students` shape in
   [data-model.md](data-model.md), with no names.

## V4. Edit (User Story 2)

1. Open `JA`, change only the template, and Save. **Expect**: no key warning, and the
   list updates.
2. Open `JA`, change the key to `ja`, and Save. **Expect**: no warning (letter case only).
3. Open `JA`, change the key to `BK`, and Save. **Expect**: "already in use".
4. Open `JA`, change the key to `JM`, and Save. **Expect**: the identifying-key warning
   naming `JA` and `JM`. Choose **No** → nothing saved, and the dialog stays open. Save
   again and choose **Yes** → the list shows `JM`.
5. Open `JM`, change the template, and press **Cancel**. **Expect**: unchanged, with no
   prompt. Repeat, but close the dialog's title bar instead, and then press the
   Students window's **Back**. **Expect**: unchanged (FR-004b).

## V5. Remove (User Story 3)

1. Select `BK` → **Remove Selected** → **No**. **Expect**: still listed.
2. **Remove Selected** → **Yes**. **Expect**: gone, including after a relaunch.

## V6. Missing template (FR-008)

1. Give `JM` a template, then delete that template in template management.
2. Open Students. **Expect**: `JM` shows `Missing template`.
3. Open `JM` and Save without touching the template. **Expect**: still `Missing template`.
   Pick a real template and Save. **Expect**: its name shows.

## V7. Damaged records file (FR-020)

1. Quit, then run `echo 'not json' > "$SCRATCH/students.json"` and relaunch.
2. Setup → **Students**. **Expect**: the start-fresh prompt naming the file. Choose
   **No**. **Expect**: Setup is still showing, and the file still contains `not json`.
3. **Students** again → **Yes**. **Expect**: an empty Students window, and
   `ls "$SCRATCH"` shows `students.unreadable-<timestamp>.json` with the old content.
4. Repeat steps 1–3. **Expect**: a second backup, and the first one is not overwritten.

## V8. Forward compatibility (FR-010, SC-006)

Write `{"format_version": 1, "students": [{"student_key": "ZZ", "future_setting": 7}]}`
to the records file and relaunch. **Expect**: `ZZ` is listed with `None selected`. After
editing `ZZ`'s template and saving, the file holds only the known fields for `ZZ`.

## V9. Boundaries and theme

- `grep -rnE "^(from|import) (interpretation|clients|collection|storage)" students/` →
  **Expect** no matches (research R1, R6).
- `grep -rn "JsonStudentStore(" --include=*.py .` → **Expect** only `program.py`
  (research R2).
- Switch the OS between light and dark and relaunch. **Expect**: Setup, Students, and
  the editor match the theme (FR-018).
