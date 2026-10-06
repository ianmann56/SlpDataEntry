# Quickstart & Validation: Workspace Folder Launch

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-05

This is a validation guide (research R9). The behavior it checks is defined in
[contracts/](contracts/) and [data-model.md](data-model.md).

## Prerequisites

- `.venv` set up per the project README, and a desktop session.
- **Synthetic data only** (Principle I): placeholder Student Keys (`AG`, `JA`), and
  scratch folders under a temporary directory, never a real Workspace.
- No AWS or Google credentials are needed. Every check here runs offline (FR-015).

```sh
cd therepy_sessions
SCRATCH=$(mktemp -d)
mkdir "$SCRATCH/complete" "$SCRATCH/empty" "$SCRATCH/only-templates" "$SCRATCH/only-students"
```

Seed the complete and partial folders by starting a new Workspace in each (V3), adding
a Template and a Student `AG` through Setup, and then deleting one file from each
partial folder:

```sh
rm "$SCRATCH/only-templates/students.json"
rm "$SCRATCH/only-students/templates.json"
```

## V1. Offline checks of the Workspace rules

Run a scratch script (not committed) against temporary folders, with fake dialogs and
creators, and confirm:

- `inspect_workspace` returns `COMPLETE`, `PARTIAL` (with the right `missing_file`), and
  `NOT_SET_UP`, and raises `WorkspaceFolderError` for a missing path, a file path, and a
  folder named `students.json`.
- `open_workspace`:
  - returns files without calling any fake for `COMPLETE`
  - calls only `show_missing_workspace_file` for `PARTIAL` and creates nothing
  - creates nothing when declined
  - creates both files when accepted
- When `create_templates_file` raises, `students.json` is removed again and
  `WorkspaceCreateError` names `templates.json`.
- `create_empty_file` on each store writes the formats in
  [data-model.md](data-model.md). A second call raises `FileExistsError` and leaves the
  file byte-for-byte unchanged.
- The stores read the new empty files as no Students and no Templates. A Template
  created after that gets id `1`.

## V2. Everyday launch (User Story 1)

```sh
../.venv/bin/python program.py "$SCRATCH/complete"
```

- The home screen opens with no prompt.
- Setup → Templates and Setup → Students show the seeded Template and `AG`.
- Add a Student `JA`, close the app, and check that
  `$SCRATCH/complete/students.json` now holds `JA`.

## V3. New Workspace (User Story 2)

```sh
../.venv/bin/python program.py "$SCRATCH/empty"
```

- **Start a New Workspace?** names the folder. Press **Close**. The app exits, and
  `ls -A "$SCRATCH/empty"` is empty.
- Launch again and press the title-bar close. The result is the same (FR-010).
- Launch again and press **Start New Workspace**. Both files now exist in the formats in
  [data-model.md](data-model.md), and the home screen opens with no Templates and no
  Students.
- Launch again. The home screen opens with no prompt.

## V4. Missing file (User Story 3)

```sh
../.venv/bin/python program.py "$SCRATCH/only-templates"
../.venv/bin/python program.py "$SCRATCH/only-students"
```

For each folder, check that:

- **Workspace File Missing** names the missing file, what it holds, and the file it goes
  next to, with **Close** as the only button.
- **Close** and the title-bar close both exit without opening the home screen.
- `ls -A` shows the folder unchanged. Record a checksum of the remaining file before
  and after.
- After copying the missing file back from `$SCRATCH/complete`, the next launch opens
  with no prompt.

## V5. Folder picker

```sh
../.venv/bin/python program.py
```

- **Choose Workspace Folder** opens. Cancel it, and the app exits with nothing created.
- Launch again and pick `$SCRATCH/complete`. The home screen opens as in V2.
- Launch again and pick a fresh empty folder. The flow is the same as V3.

## V6. Bad launches and folder errors

| Command | Expected |
| --- | --- |
| `program.py a.json b.json` | The usage message on the console, exit code 1, and no window |
| `program.py "$SCRATCH/nope"` | **Can't Open Workspace**: the folder doesn't exist |
| `program.py "$SCRATCH/complete/students.json"` | **Can't Open Workspace**: not a folder |
| `mkdir "$SCRATCH/dirname"; mkdir "$SCRATCH/dirname/students.json"`, then launch with `"$SCRATCH/dirname"` | **Can't Open Workspace**: `students.json` is a folder |
| `mkdir "$SCRATCH/ro"; chmod a-w "$SCRATCH/ro"`, then launch with it and accept | **Can't Open Workspace**: couldn't create `students.json`; the folder is still empty |
| `mkdir "$SCRATCH/My Wörkspace"`, then launch with it and accept | It works like V3. |

Run `chmod u+w "$SCRATCH/ro"` before cleaning up.

## V7. Theme, privacy, and no network

- With the system in dark mode and then light mode, every Workspace dialog matches the
  home screen's theme (FR-014).
- No dialog text contains a Student Key, only paths (FR-016).
- With networking off, V2 through V6 behave the same (FR-015, SC-005 of feature 001).

## V8. Docs and git

- `docs/domain/glossary.md` defines **Workspace** and **Workspace State**, and the
  Student Store and Template Store entries mention the Workspace.
- `layers.md` lists `workspace/` and rule 11. The constitution is version 1.7.0.
- A `students.json` and a `templates.json` made in the repo root show as ignored in
  `git status --ignored`.

Clean up with `rm -rf "$SCRATCH"`.
