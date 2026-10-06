# Research: Workspace Folder Launch

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-05

Each decision records what was chosen, why, and what else was considered. The Technical
Context in [plan.md](plan.md) has no open NEEDS CLARIFICATION items. These decisions
settle the design questions the spec left to planning.

## R1. A `workspace/` package that stands apart from the pipeline

**Decision**: Add a package `therepy_sessions/workspace/` with two modules:

- `workspace.py` holds the rules and does no Tkinter work: the fixed file names,
  `workspace_files(folder)`, `inspect_workspace(folder)`, and the
  `open_workspace(...)` flow, which decides what happens for each Workspace State.
- `workspace_dialogs.py` holds the Tkinter prompts: the new-Workspace question, the
  missing-file stop, and the folder error.

`workspace/` imports nothing from `clients/`, `collection/`, `interpretation/`,
`storage/`, or `students/`. It never builds a store. It creates the empty files only
through two callables that `program.py` wires from the stores it builds (R3). The
dialogs reach `open_workspace` as injected callables too, so the flow can be checked
with plain fakes and no display.

**Rationale**:

- The Workspace is about where the app's configuration lives, not about Students,
  Templates, or the pipeline. Putting it in `students/` or `interpretation/` would make
  one of them own the other's file.
- `app_shell/` is limited to Tkinter by layers rule 7, so it can't hold the file rules.
- Splitting rules from dialogs follows layers rule 5 (no business rules in widget
  callbacks) and matches `template_rules.py` beside `template_management_window.py`.

**Alternatives considered**:

- **All of it in `program.py`.** That is the composition root, but the flow has real
  rules (three states, rollback, error cases). Keeping them in `program.py` makes them
  hard to check without starting the app.
- **A `Workspace` class that builds both stores.** That would make `workspace/` import
  `students/` and `interpretation/`, so it could no longer stand apart. It would also
  move store construction out of `program.py` (layers rule 6).

## R2. How the Workspace State is decided

**Decision**: `inspect_workspace(folder)` looks for exactly `students.json` and
`templates.json` directly in the folder, with `os.path.lexists` and `os.path.isdir`:

| Folder holds | Result |
| --- | --- |
| both, each a file | `COMPLETE` |
| exactly one, a file | `PARTIAL`, naming the missing file |
| neither | `NOT_SET_UP` |

It raises `WorkspaceFolderError` when:

- the folder does not exist
- the path is not a folder
- either Workspace name is a folder rather than a file
- either Workspace name is a link to a file that doesn't exist (a broken symlink)

Names are compared as the operating system compares them. On a case-sensitive file
system, `Students.json` is a different name. On a case-insensitive one, it is the same
file, which is what the SLP would expect there. Nothing else in the folder is read or
listed.

**Rationale**: The spec's edge cases treat a folder at a Workspace name as an error, not
as missing (so the SLP is never told to restore a file that is actually there in the
wrong form). A broken link is an error for a similar reason. `os.path.lexists` sees it,
so it can't count as missing. But the stores use `os.path.exists`, which doesn't see it,
so as complete the app would open with no Students or no Templates and give no warning. Asking the OS about the two exact paths, rather than listing the folder,
avoids reading anything unrelated in it.

**Alternatives considered**:

- **List the folder and match names case-insensitively everywhere.** That would make a
  Linux folder holding `Students.json` count as complete, and the stores would then open
  a path that does not exist. Rejected.
- **Check readability during inspection.** The spec says an unreadable file is handled
  as it is today, by each store, when it is used. Inspection only decides presence.

## R3. Creating the empty files: each store writes its own format

**Decision**: Each JSON store gains a public `create_empty_file() -> None`:

- `JsonStudentStore.create_empty_file()` writes `{"format_version": 1, "students": []}`.
- `TemplateStore.create_empty_file()` writes
  `{"format_version": 2, "last_template_id": 0, "templates": []}`.

Both open the file in exclusive-create mode (`open(path, "x")`), so they raise
`FileExistsError` instead of writing over a file that already exists (FR-011). If
writing fails after the file was created, they remove the partial file before
re-raising. They write UTF-8 with `indent=2`, as every other save does.

`program.py` passes `student_store.create_empty_file` and
`template_store.create_empty_file` to `open_workspace` as `create_students_file` and
`create_templates_file`.

**Rationale**:

- Only the store knows its file format and its format version. A Workspace module that
  wrote `{"students": []}` itself would duplicate that knowledge and drift on the next
  format change.
- Exclusive create is the one check that can't race. A file that appears between
  inspection and creation is never replaced.
- An empty templates file written in format 2 records `last_template_id: 0` from the
  start. A file holding 0 is only ever created for a brand new Workspace, where no
  Student can point at an old Template (the reason for the clarification that removed
  "start fresh").

**Alternatives considered**:

- **Write through the stores' existing `_save`.** `_save` uses a temporary file and
  `os.replace`, which replaces an existing file, the opposite of what FR-011 needs.
- **Temporary file plus `os.link` for an atomic, no-replace create.** Hard links fail
  on FAT and exFAT, which is what a USB stick holding a Workspace is likely to use.
  The files here are a few dozen bytes, so exclusive create plus cleanup is enough.
- **Leave the files missing and let the stores treat a missing file as empty.** The
  next launch would then see `NOT_SET_UP` again and ask again. The spec requires both
  files to exist as soon as the SLP accepts.

## R4. Creating a new Workspace is all or nothing

**Decision**: `open_workspace` creates `students.json`, then `templates.json`. If the
second fails, it deletes the first, which it just created, and raises
`WorkspaceCreateError` naming the file that could not be created. If deleting the first
also fails, the error says so and names both files.

**Rationale**: Leaving only `students.json` would turn the folder into a partial
Workspace, which the clarified spec can never open, and the SLP would be stuck at a
Close-only message for a problem the app caused. Rolling back returns the folder to
not set up, so fixing the folder and launching again simply asks again.

**Alternatives considered**: Leaving the first file in place and telling the SLP. This
was rejected for the reason above.

## R5. The launch command and the folder picker

**Decision**: `parse_command_line_args() -> str | None`:

| Arguments | Result |
| --- | --- |
| none | `None`: the app opens a folder picker |
| one | that path, used as the Workspace folder |
| more than one | the usage message on the console, exit code 1, no window |

The usage message names the single folder argument and says that leaving it out opens
a picker. Because the old two-file launch passes two arguments, it always gets the usage
message (FR-002).

The picker is `tkinter.filedialog.askdirectory(parent=root, title="Choose Workspace
Folder", mustexist=True)`, opened from the current working directory. Cancelling it
(an empty result) destroys the root window and the app exits with nothing created.

A single argument that is a `.json` file is not special-cased: it is not a folder, so
it gets the folder error from R2 (FR-012).

**Rationale**:

- Wrong argument counts are a developer or shortcut mistake, caught before any window
  exists, so a console message and exit code fit, as they do today.
- `askdirectory` is the standard Tk folder picker. `mustexist=True` means the picker
  never returns a folder that does not exist.
- The current directory is a sensible start, since a desktop shortcut sets it. The
  spec says the app does not remember the last Workspace.

**Alternatives considered**:

- **`argparse`.** One optional positional argument doesn't need it, and the current
  code reads `sys.argv` directly. It could come later if more options are added.
- **A dialog for the usage message.** The usage message is about how the command was
  typed, which belongs on the console where it was typed.

## R6. When and how the prompts appear

**Decision**: `main()` creates the Tk root, sets the theme, and withdraws the root
before the Workspace is opened. Every Workspace dialog is a small ttk `Toplevel` built
in `workspace_dialogs.py`. It is themed by `sv-ttk` like the other windows (FR-014),
modal (`grab_set` and `wait_window`), and centered on the screen, because its parent is
hidden. It is not marked `transient()` to its parent: a window transient to a withdrawn
window is never shown by some Linux window managers. It calls `lift()` and
`focus_force()` instead, so it comes to the front. Its ttk frame fills the whole
`Toplevel`, so no unthemed Tk background shows (FR-014). Only after `open_workspace` returns the files does `main()` build the stores'
consumers, show the root, and build `HomeWindow`.

| Dialog | Text names | Buttons | Closing it from the title bar |
| --- | --- | --- | --- |
| New Workspace | the folder path | **Start New Workspace**, **Close** | Close (FR-010) |
| Missing file | the missing file, what it holds, and the file it goes next to | **Close** only (FR-008) | Close |
| Folder error | the problem and the path | **Close** only | Close |

Messages show paths only and never read a file's contents, so no Student Key can appear
(FR-016).

**Rationale**:

- `tkinter.messagebox` can't offer a lone **Close** button with that label, and on Linux
  it is not themed by `sv-ttk`. A ttk `Toplevel` meets FR-008 and FR-014 exactly.
- Withdrawing the root means no empty main window flashes behind the prompts, and a
  declined prompt leaves nothing on screen.

**Alternatives considered**: `messagebox.askyesno` and `showerror`, as
`ask_to_start_fresh` uses. These were rejected because of the button labels and theming
described above.

## R7. What changes in the stores and in `program.py`

**Decision**:

- `program.py` builds `JsonStudentStore` and `TemplateStore` from
  `workspace_files(folder)`, then calls `open_workspace`, and continues only on success.
- `validate_storage_file_path` and `validate_distinct_storage_files` are removed. The
  fixed names in one folder always make two distinct `.json` paths.
- How each store reads, writes, backs up, and reports an unreadable file is unchanged
  (spec Assumptions). The only store change is `create_empty_file` (R3).

**Rationale**: The rest of the app already receives the stores by injection, so nothing
past `main()` needs to know the paths came from a Workspace.

## R8. Docs, glossary, and keeping Workspaces out of git

**Decision**:

- `docs/domain/glossary.md` gains **Workspace** and **Workspace State**. The **Student
  Store** and **Template Store** entries say their files are `students.json` and
  `templates.json` in the Workspace (FR-017).
- `docs/conventions/architecture/layers.md` adds `workspace/` to the package layout and
  a new rule 11 (R1).
- `docs/conventions/architecture/dependency-injection.md` rule 6 says `open_workspace`
  receives its dialogs and the stores' `create_empty_file` callables from `program.py`.
- The constitution's Sync Impact Report is updated and the version goes to 1.7.0
  (MINOR: new rules in referenced docs).
- `.gitignore` gains `students.json` and `templates.json`, so a Workspace made inside
  the repo is never committed (Principle I).
- `therepy_sessions/README.md` "How to Run" gains the launch command.

**Rationale**: Principle II requires the glossary entry in the same change. The new
package is a new layer boundary, which the layers doc must name. The `.gitignore` lines
cost nothing and protect real student records.

## R9. How the feature is checked

**Decision**: No test framework is added, as in features 003–005.

- `workspace.py` is checked with a scratch script against temporary folders and fake
  dialogs and creators: every state, both error kinds, decline, rollback, and
  no-overwrite.
- `create_empty_file` is checked against temporary folders, including that it refuses
  to replace an existing file.
- The dialogs, the picker, and the launch are checked by hand with
  [quickstart.md](quickstart.md), on synthetic data only.

**Rationale**: This matches how the project checks its pure logic today, and the flow
was designed (R1) so the scratch checks need no display.
