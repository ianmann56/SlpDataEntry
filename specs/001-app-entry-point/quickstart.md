# Quickstart & Validation: Application Entry Point

**Feature**: [spec.md](spec.md) | **Date**: 2026-09-27

This is a manual validation guide; see research R8 for why there are no automated tests.
The navigation it exercises is defined in [data-model.md](data-model.md), and the window
behavior in [contracts/ui-windows.md](contracts/ui-windows.md).

## Prerequisites

- `.venv` created and populated per the project README (`pip install -r pip_requirements.txt`).
- A desktop session (Tkinter needs a display).
- **Only synthetic data** (Principle I). Use `therepy_sessions/sample_data/templates.json`
  or a throwaway path.

```sh
cd therepy_sessions
```

## V1. Launch contract (FR-001, Assumptions)

| Command | Expected |
| --- | --- |
| `../.venv/bin/python3 program.py` | Usage message, exit status 1, no window |
| `../.venv/bin/python3 program.py foo.txt` | "must be a JSON file" error, exit status 1, no window |
| `../.venv/bin/python3 program.py sample_data/templates.json` | Home screen opens |

## V2. Offline, no credentials (FR-009, SC-005)

1. Turn off networking, or run with `AWS_ACCESS_KEY_ID=` and
   `AWS_SECRET_ACCESS_KEY=` unset, and with no Google token file available.
2. Launch with `sample_data/templates.json`.
3. **Expect**: the home screen appears, with no OAuth browser prompt and no credential
   error. Both paths from V3 and V4 work.
4. `grep -nE "clients|create_google_service|construct_textract_client" program.py`
   → **Expect** no matches.

## V3. Management path (User Story 2)

1. From home, click **Manage Setup & Data Sheet Templates**.
   **Expect**: home disappears, and the template management window shows the templates
   from the store.
2. Create a template named `QS Test`, then click **Back**.
   **Expect**: the management window closes and home reappears.
3. Click **Manage Setup & Data Sheet Templates** again.
   **Expect**: `QS Test` is listed. Delete it.
4. Click **Close**. **Expect**: the application exits (exit status 0).
5. Relaunch, open management, and click the title-bar ✕. **Expect**: the application exits.
6. Relaunch, open management, open **Create New Template**, then close the management
   window from its title bar if the window manager allows it. **Expect**: every window
   closes and the process exits.

## V4. Import and interpret placeholder (User Story 3)

1. From home, click **Import & Interpret Student Data Sheets**.
   **Expect**: home disappears, and the placeholder says the feature is not yet available
   and has only a **Back** button.
2. Click **Back**. **Expect**: home reappears with both choices.
3. Open the placeholder again and click the title-bar ✕. **Expect**: the application exits.

## V5. Round trips (SC-004)

Do 10 go-and-Back round trips on each path in a single session.
**Expect**: exactly one visible window at a time, no errors in the terminal, and no
restart needed.

## V6. Theme (FR-011)

Switch the OS between light and dark, then relaunch. **Expect**: home, the placeholder,
and template management all use the matching `sv-ttk` theme.

## V7. Home close (FR-010)

On the home screen, click the title-bar ✕. **Expect**: the application exits.

## V8. Scripts (FR-013, FR-014)

- `ls program_manage.py` → **Expect** "No such file".
- `program_interpret.py` still runs its developer flow when given the three arguments,
  and its usage text names `program_interpret.py`.
