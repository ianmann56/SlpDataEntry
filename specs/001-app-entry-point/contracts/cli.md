# Contract: Launch Command

**Feature**: [../spec.md](../spec.md) | **Date**: 2026-09-27

## `program.py` (new single entry point)

Run from `therepy_sessions/`, since the shebang is `#!../.venv/bin/python3`:

```sh
./program.py <template_storage_file_path>
# or
../.venv/bin/python3 program.py <template_storage_file_path>
```

| Input | Behavior |
| --- | --- |
| No argument | Prints `Usage: python program.py <template_storage_file_path>` and `Example: python program.py templates.json`, then exits with status 1. No window opens. |
| Argument not ending in `.json` (case-insensitive) | Prints `Error: Storage file must be a JSON file (got: <path>)` and the `.json` hint, then exits with status 1. No window opens. |
| Valid `.json` path, whether the file exists or not | Opens the home screen. A missing file gives an empty template list, as `TemplateStore` does today. |

- No network access, OAuth prompt, or credential read happens at launch (FR-009, SC-005).
- Exit status is 0 after any normal exit through a window close or Close button.

## `program_manage.py` (removed)

Deleted (FR-013). Its launch behavior is now `program.py` → **Manage Setup & Data Sheet
Templates**.

## `program_interpret.py` (kept, developer-only)

It works the same as today:
`program_interpret.py <template_storage_file_path> <template_id> <image_path>`. Three
things change: a module docstring marks it as a temporary developer-only script, its
usage text names `program_interpret.py` and its three arguments, and the argument-count
check requires all three, so a missing argument prints usage instead of raising
`IndexError`. `program.py` never reaches it (FR-014).
