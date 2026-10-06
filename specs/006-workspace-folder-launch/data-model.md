# Data Model: Workspace Folder Launch

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-05

The full signatures are in [contracts/workspace.md](contracts/workspace.md).

## Workspace

A folder the SLP chooses at launch. It holds all of the application's local configuration
for one setup.

| Field | Meaning |
| --- | --- |
| folder | The folder path as given or picked. It is never created by the app. |
| students file | `<folder>/students.json`, the Student Store's file |
| templates file | `<folder>/templates.json`, the Template Store's file |

The file names are fixed and lower case, directly in the folder (FR-003). They are
constants in `workspace/workspace.py`: `STUDENTS_FILE_NAME` and `TEMPLATES_FILE_NAME`.

In code this is `WorkspaceFiles(folder, students_file, templates_file)`, built by
`workspace_files(folder)` without touching the disk.

## Workspace State

Decided by `inspect_workspace` from which Workspace files are present (research R2).

| State | Folder holds | What happens |
| --- | --- | --- |
| `COMPLETE` | both files | Open with no prompt (FR-004). |
| `NOT_SET_UP` | neither file | Ask whether to start a new Workspace (FR-005). |
| `PARTIAL` | exactly one file | Show the missing-file stop with Close only (FR-007, FR-008). |

A path that is not a usable folder is not a state. It raises `WorkspaceFolderError`
(FR-012).

```text
                 ┌──────────────┐ Start New Workspace ┌──────────┐
  launch ──────▶ │  NOT_SET_UP  │ ──────────────────▶ │ COMPLETE │ ──▶ home screen
     │           └──────────────┘  (both files made)  └──────────┘
     │                 │ Close / title bar                   ▲
     │                 ▼                                     │
     │               exit, nothing created                   │
     │                                                       │
     ├──────────────────────────────────────────────────────┘ (already complete)
     │
     │           ┌──────────────┐  Close / title bar
     └─────────▶ │   PARTIAL    │ ──────────────────▶ exit, nothing created
                 └──────────────┘
                       │ SLP restores the missing file outside the app
                       ▼
                 next launch sees COMPLETE
```

There is no transition from `PARTIAL` inside the app. It is left only by the SLP
restoring the file and launching again.

`WorkspaceInspection(files, state, missing_file)` carries the result. `missing_file` is
the path of the missing file when the state is `PARTIAL`, and `None` otherwise.

## Empty Workspace files

Written only by each store's `create_empty_file()` (research R3), in exclusive-create
mode, UTF-8, `indent=2`.

`students.json`:

```json
{
  "format_version": 1,
  "students": []
}
```

`templates.json`:

```json
{
  "format_version": 2,
  "last_template_id": 0,
  "templates": []
}
```

Both are exactly what each store already reads as "no entries", so nothing downstream
changes.

## Errors

| Error | Raised by | When | Shown as |
| --- | --- | --- | --- |
| `WorkspaceFolderError(path, reason)` | `inspect_workspace` | The folder is missing or not a folder, or a Workspace name is a folder. | The Folder error dialog, then exit |
| `WorkspaceCreateError(path, reason)` | `open_workspace` | A new Workspace file could not be created. The other file is already rolled back (research R4). | The Folder error dialog, naming the file, then exit (FR-013) |
| `FileExistsError` | `create_empty_file` | The file appeared after inspection. | Wrapped in `WorkspaceCreateError`. The existing file is untouched (FR-011). |

Every message holds paths and a reason only, never file contents or a Student Key
(FR-016).

## Glossary additions (FR-017)

| Term | Code | Meaning |
| --- | --- | --- |
| **Workspace** | `WorkspaceFiles` | The folder chosen at launch that holds `students.json` (the Student Store's file) and `templates.json` (the Template Store's file). Only a complete Workspace can be opened. |
| **Workspace State** | `WorkspaceState` | Whether a Workspace is complete (both files), partial (one), or not set up (neither). |

The **Student Store** and **Template Store** entries change from "a local JSON file
given at launch" to "`students.json` / `templates.json` in the Workspace".
