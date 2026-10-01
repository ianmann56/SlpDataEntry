# Contract: Launch Command

**Feature**: [../spec.md](../spec.md) | **Date**: 2026-09-30

This replaces feature 001's single-argument contract
([../../001-app-entry-point/contracts/cli.md](../../001-app-entry-point/contracts/cli.md))
(FR-019, research R9). Run from `therepy_sessions/`:

```sh
./program.py <template_storage_file_path> <student_storage_file_path>
```

| Input | Behavior |
| --- | --- |
| Fewer than two arguments | Prints `Usage: python program.py <template_storage_file_path> <student_storage_file_path>` and `Example: python program.py templates.json students.json`, then exits with status 1. No window opens. |
| Either argument not ending in `.json` (case-insensitive) | Prints the existing `Error: Storage file must be a JSON file (got: <path>)` and the `.json` hint for the first bad argument, then exits with status 1. No window opens. |
| Both arguments resolve to the same file | Prints `Error: The template file and student records file must be different files`, then exits with status 1. No window opens. |
| Two valid, different `.json` paths, whether or not the files exist | Opens the home screen. A missing student file gives an empty list, and the file is created on the first save. |

- Constructing the student store does no file I/O, so a damaged student file never blocks
  launch. It is handled when the Students window is opened (FR-020).
- No network access, OAuth prompt, or credential read happens (FR-017).
- `program_interpret.py` is unchanged.
