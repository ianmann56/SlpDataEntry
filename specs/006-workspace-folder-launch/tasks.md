---

description: "Task list for the Workspace Folder Launch feature"
---

# Tasks: Workspace Folder Launch

**Input**: Design documents from `/specs/006-workspace-folder-launch/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/workspace.md](contracts/workspace.md),
[contracts/launch.md](contracts/launch.md), [quickstart.md](quickstart.md)

**Tests**: No automated tests. The spec doesn't ask for them. Research R9 makes
verification:

- offline scratch-script checks of `workspace/workspace.py` and `create_empty_file`,
  using temporary folders and fake dialogs and creators
- manual checks from [quickstart.md](quickstart.md) on synthetic data

Scratch scripts are not committed.

**Organization**: Tasks are grouped by user story. `open_workspace` grows one state per
story, and each story leaves the app safe to merge:

- **US1 (P1)** launches from a complete Workspace, given on the command line or picked.
  Until US2 and US3 land, a folder that is not complete stops at **Can't Open
  Workspace** and nothing is created. US1 also carries the glossary, architecture-doc,
  constitution, `.gitignore`, and README changes.
- **US2 (P2)** adds starting a new Workspace in a folder holding neither file.
- **US3 (P3)** adds the Close-only stop for a folder missing one file.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US3 from spec.md

## Path Conventions

- All code is under `therepy_sessions/`. Modules import each other by package path from
  that directory (e.g. `from workspace.workspace import open_workspace`).
- **Types**: every public function, method, attribute, constant, and `__init__` added or
  changed is fully annotated per
  [type-declarations.md](../../docs/conventions/architecture/type-declarations.md).
- **`workspace/` stands apart**: `workspace/` MUST NOT import `clients/`, `collection/`,
  `interpretation/`, `storage/`, or `students/`. `workspace/workspace.py` MUST NOT
  import `tkinter`. `workspace/workspace_dialogs.py` imports only `tkinter` and
  `workspace.workspace`.
- **Stores are built only in `program.py`**, which is the only module that imports both
  `workspace/` and the stores.
- **Privacy**: dialog text holds paths and fixed wording only. It never reads or shows
  file contents or a Student Key (FR-016). Use only synthetic data and placeholder keys
  (`AG`, `JA`) in scratch folders.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the package and keep Workspace files out of git.

- [ ] T001 Create the empty package marker `therepy_sessions/workspace/__init__.py`, matching the existing package `__init__.py` files.
- [ ] T002 [P] Add `students.json` and `templates.json` to `.gitignore` under the "Project Specific" section, with a one-line comment saying they are Workspace files holding student records (research R8, Principle I). Confirm with `git ls-files | grep -E "(students|templates)\.json"` that no tracked file is hidden by them.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The Workspace rules and the shared dialog, which every story uses.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 Create `therepy_sessions/workspace/workspace.py` per contracts/workspace.md § `workspace/workspace.py` and research R2. Stdlib only (`os`, `enum`, `typing`), with no Tkinter:
  - Constants `STUDENTS_FILE_NAME: str = "students.json"` and `TEMPLATES_FILE_NAME: str = "templates.json"`.
  - `WorkspaceState(Enum)` with `COMPLETE`, `PARTIAL`, `NOT_SET_UP`.
  - `WorkspaceFiles(NamedTuple)` with `folder`, `students_file`, `templates_file`.
  - `WorkspaceInspection(NamedTuple)` with `files`, `state`, and `missing_file: str | None`.
  - `WorkspaceFolderError(Exception)` and `WorkspaceCreateError(Exception)`, each with `__init__(self, path: str, reason: str) -> None` and public `path: str` and `reason: str` attributes. `reason` is the full sentence shown to the SLP, so the dialog adds nothing but the title (contracts/launch.md § Folder error).
  - `workspace_files(folder: str) -> WorkspaceFiles` joins the fixed names onto `folder` with `os.path.join` and touches nothing on disk.
  - `inspect_workspace(folder: str) -> WorkspaceInspection`:
    - raises `WorkspaceFolderError(folder, "This folder doesn't exist: <folder>")` if `not os.path.exists(folder)`
    - raises `WorkspaceFolderError(folder, "This isn't a folder: <folder>. Choose the folder that holds students.json and templates.json.")` if `not os.path.isdir(folder)`
    - raises `WorkspaceFolderError(path, "<path> is a folder, but it should be a file. Fix this in the Workspace folder, then launch again.")` if either Workspace path `os.path.isdir`
    - otherwise uses `os.path.lexists` on the two exact paths to return `COMPLETE`, `PARTIAL` (with `missing_file` set to the missing path), or `NOT_SET_UP`
    - never lists or reads the folder
  - Module and function docstrings name the Workspace and Workspace State glossary terms.
- [ ] T004 Create `therepy_sessions/workspace/workspace_dialogs.py` per contracts/workspace.md § `workspace/workspace_dialogs.py` and research R6 (depends on T003):
  - A private helper `_show_dialog(parent: tk.Misc, title: str, message: str, buttons: list[str], close_button: str) -> str`. It builds a `tk.Toplevel(parent)` holding a `ttk.Frame` with padding, a wrapped `ttk.Label` for the message, and one `ttk.Button` per label, right-aligned with the last one as default. It makes the window non-resizable, centers it on the screen (the parent is withdrawn), makes it modal with `grab_set()`, and maps the title-bar close (`WM_DELETE_WINDOW`) and Escape to `close_button`. It blocks with `wait_window()` and returns the label pressed.
  - `show_workspace_error(parent: tk.Misc, error: WorkspaceFolderError | WorkspaceCreateError) -> None`: title **Can't Open Workspace**, message `error.reason`, button **Close** only.
  - Import only `tkinter`, `tkinter.ttk`, and `workspace.workspace`. The theme comes from `sv_ttk`, which `program.py` has already set, so don't import `sv_ttk` here.
- [ ] T005 Offline check of the foundation (quickstart V1, first bullet). From `therepy_sessions/`, run a scratch script with `tempfile.TemporaryDirectory()` that confirms `inspect_workspace` returns:
  - `COMPLETE` with both files present
  - `PARTIAL` with `missing_file` correct, in both directions
  - `NOT_SET_UP` for an empty folder, and for a folder holding only an unrelated file and `students.json.bak`
  - `WorkspaceFolderError` for a missing path, a file path, and a folder named `students.json`

  Also confirm with `grep -n "^import\|^from" therepy_sessions/workspace/*.py` that the import rules in Path Conventions hold.

**Checkpoint**: The Workspace State is decided correctly, and the error dialog exists.

---

## Phase 3: User Story 1 - Launch with an existing Workspace (Priority: P1) 🎯 MVP

**Goal**: The SLP launches with one folder, or picks it, and a complete Workspace opens
straight to the home screen, using its two files for every read and write.

**Independent Test**: Launch with a folder holding both files and confirm the home
screen opens with no prompt, showing those Templates and Students. Launch the old
two-file way and confirm the usage message (quickstart V2, V5, V6).

- [ ] T006 [US1] In `therepy_sessions/workspace/workspace.py`, add `open_workspace(folder: str) -> WorkspaceFiles | None` for the US1 stage of contracts/workspace.md § `open_workspace` behavior:
  - It calls `inspect_workspace(folder)`.
  - It returns `inspection.files` for `COMPLETE`.
  - For any other state, it raises `WorkspaceFolderError(folder, "This folder isn't a complete Workspace. It needs both students.json and templates.json: <folder>")`.

  The docstring says that nothing is created, changed, or deleted when it returns `None` or raises. US2 and US3 replace the non-complete branch.
- [ ] T007 [US1] Rewrite argument handling in `therepy_sessions/program.py` per contracts/launch.md § Command line and research R5:
  - `parse_command_line_args() -> str | None` returns `None` for no arguments and `sys.argv[1]` for one.
  - For more than one argument, it prints the four-line usage message from contracts/launch.md exactly and calls `sys.exit(1)` before any window exists.
  - Delete `validate_storage_file_path` and `validate_distinct_storage_files`.
  - Update the docstring.
- [ ] T008 [US1] Rewrite the start of `main()` in `therepy_sessions/program.py` per contracts/workspace.md § `program.py` wiring (depends on T006, T007):
  1. `folder_arg = parse_command_line_args()`.
  2. Create the root, set the theme as today, then call `root.withdraw()`.
  3. If `folder_arg` is `None`, get the folder from `filedialog.askdirectory(parent=root, title="Choose Workspace Folder", mustexist=True)`. On an empty result, `root.destroy()` and return.
  4. `files = workspace_files(folder)`. Build `TemplateStore(files.templates_file)` and `JsonStudentStore(files.students_file)` in place of today's argument paths.
  5. Call `open_workspace(folder)` inside `try`. On `WorkspaceFolderError` or `WorkspaceCreateError`, call `show_workspace_error(root, e)` and treat the result as `None`.
  6. On `None`, `root.destroy()` and return. Otherwise call `root.deiconify()` and continue with the existing, unchanged providers, `open_*` functions, `HomeWindow`, and `mainloop()`.

  Add the `from tkinter import filedialog` and `workspace` imports. Remove imports the deleted validators used, if nothing else uses them (`os`).
- [ ] T009 [P] [US1] Update "How to Run" in `therepy_sessions/README.md`:
  - Give the launch command `../.venv/bin/python program.py [<workspace_folder>]`.
  - Say that the folder holds `students.json` and `templates.json`, and that leaving it out opens a folder picker.
  - Say that existing users move to a Workspace by putting their two current files in one folder under those names (spec Assumptions).
- [ ] T010 [P] [US1] Amend `docs/domain/glossary.md` per data-model.md § Glossary additions (FR-017):
  - Add **Workspace** (`WorkspaceFiles`) and **Workspace State** (`WorkspaceState`) rows to the table that holds Student Store and Template Store.
  - Change the **Student Store** and **Template Store** entries to say their files are `students.json` and `templates.json` in the Workspace, instead of a file given at launch.
- [ ] T011 [P] [US1] Amend `docs/conventions/architecture/layers.md` (research R1, R8):
  - Add `workspace/` to the package layout block: "Workspace folder rules and launch dialogs; no pipeline or students imports".
  - Change the `program.py` line to "parses args, opens the Workspace, builds clients, wires the layers".
  - Add rule 11: **The Workspace stands apart.** `workspace/` MUST NOT import from `clients/`, `collection/`, `interpretation/`, `storage/`, or `students/`, and never builds a store. Its rules (`workspace.py`) import no Tkinter, and its dialogs live in `workspace_dialogs.py`. It creates Workspace files only through callables wired in `program.py` from each store's `create_empty_file`.
- [ ] T012 [P] [US1] Amend rule 6 of `docs/conventions/architecture/dependency-injection.md`: `program.py` builds the `JsonStudentStore` and `TemplateStore` from the Workspace paths (`workspace_files`), and `open_workspace` receives every dialog and file creator it uses as a callable from `program.py`.
- [ ] T013 [US1] Amend `.specify/memory/constitution.md` (depends on T010–T012):
  - Add a 1.7.0 Sync Impact Report at the top that lists the `layers.md`, `dependency-injection.md`, and `glossary.md` changes. Move the 1.6.0 report under "Previous report (1.6.0)", following the file's existing pattern, and add a "1.6.0 (2026-10-03)" line to Prior history.
  - Change the footer to `**Version**: 1.7.0 | ... | **Last Amended**: <today>`.
  - In the Technology Constraints "Local persistence" bullet, say the JSON files live in the Workspace folder.
- [ ] T014 [US1] Validate US1 from `therepy_sessions/`, with synthetic data only. Seed `$SCRATCH/complete` by hand with the empty formats from data-model.md, then add a Template and Student `AG` through Setup.
  - quickstart V2 (everyday launch, and a save written to the Workspace)
  - V5 (the picker opens, cancelling exits with nothing created, and picking `$SCRATCH/complete` opens)
  - V6 rows 1–4 (usage message with exit code 1, missing folder, file path, and a folder named `students.json`)
  - an empty folder shows **Can't Open Workspace** and `ls -A` stays empty

**Checkpoint**: The app launches only from a Workspace. US1 can be merged on its own.

---

## Phase 4: User Story 2 - Start a new Workspace in an empty folder (Priority: P2)

**Goal**: A folder holding neither file offers to start a new Workspace. Yes creates
both empty files and opens; Close leaves the folder untouched.

**Independent Test**: Launch with an empty folder. Close leaves it empty. Start New
Workspace creates both files and opens, and the next launch has no prompt (quickstart
V3).

- [ ] T015 [P] [US2] Add `create_empty_file(self) -> None` to `JsonStudentStore` in `therepy_sessions/students/json_student_store.py` per contracts/workspace.md § Store additions and research R3:
  - Open `self._file_path` with `open(..., "x", encoding="utf-8")`, so it raises `FileExistsError` and leaves an existing file unchanged.
  - Write `{"format_version": FORMAT_VERSION, "students": []}` with `json.dump(..., indent=2, ensure_ascii=False)`.
  - If writing fails after the file was opened, remove the file (ignoring an `OSError` from the removal) and re-raise.
  - Don't create directories.
  - The docstring states the two `Raises` cases.
- [ ] T016 [P] [US2] Add `create_empty_file(self) -> None` to `TemplateStore` in `therepy_sessions/interpretation/template_store.py`. It is the same as T015, writing `{"format_version": FORMAT_VERSION, "last_template_id": 0, "templates": []}` to `self.storage_file_path`. The docstring notes that `last_template_id` starts at 0 only for a brand new file.
- [ ] T017 [P] [US2] Add `ask_to_start_new_workspace(parent: tk.Misc, folder: str) -> bool` to `therepy_sessions/workspace/workspace_dialogs.py` per contracts/launch.md § New Workspace:
  - title **Start a New Workspace?**
  - the message text with the folder path
  - buttons **Start New Workspace** and **Close**, with Close as the `close_button`
  - returns `True` only for **Start New Workspace**
- [ ] T018 [US2] Extend `open_workspace` in `therepy_sessions/workspace/workspace.py` with the parameters `ask_to_start_new_workspace: Callable[[str], bool]`, `create_students_file: Callable[[], None]`, and `create_templates_file: Callable[[], None]`, and the `NOT_SET_UP` branch from contracts/workspace.md § `open_workspace` behavior and research R4:
  - If the SLP declines, return `None` having created nothing.
  - If the SLP accepts, call `create_students_file()`. An `OSError` raises `WorkspaceCreateError(students_file, "Couldn't create <path>: <error>. Nothing was set up in this folder.")`.
  - Then call `create_templates_file()`. On an `OSError`, `os.remove(students_file)` and raise `WorkspaceCreateError` for the templates file. If the removal also fails, the reason instead says the students file could not be removed, naming both paths, and drops "Nothing was set up".
  - Return `files` on success.

  Only `OSError` is wrapped. `PARTIAL` keeps the US1 error until US3.
- [ ] T019 [US2] Wire US2 in `therepy_sessions/program.py` (depends on T015–T018). Pass these to `open_workspace`:
  - `ask_to_start_new_workspace=lambda f: ask_to_start_new_workspace(root, f)`
  - `create_students_file=student_store.create_empty_file`
  - `create_templates_file=template_store.create_empty_file`

  The stores are already built before the call (T008).
- [ ] T020 [US2] Offline check (quickstart V1, US2 bullets) in a scratch script with temporary folders and fake callables:
  - declining creates nothing
  - accepting creates both files in the data-model.md formats
  - a raising `create_templates_file` leaves the folder empty and names `templates.json`
  - a raising `create_students_file` never calls the templates creator
  - a second `create_empty_file` raises `FileExistsError` and leaves the bytes unchanged
  - both stores read the new files as empty, and the first Template created gets id `1`
- [ ] T021 [US2] Validate US2 manually:
  - quickstart V3 (Close, title-bar close, Start New Workspace, relaunch with no prompt)
  - V5 last bullet (picking an empty folder)
  - V6 rows 5–6 (read-only folder shows **Can't Open Workspace** and stays empty; a path with spaces and non-ASCII characters works)

**Checkpoint**: The SLP can set up a Workspace from inside the app.

---

## Phase 5: User Story 3 - Stop at a Workspace that is missing one file (Priority: P3)

**Goal**: A folder holding exactly one file names the missing file and where it goes,
and offers only Close. Nothing is created and the home screen never opens.

**Independent Test**: Launch with a folder holding only `templates.json`, then with one
holding only `students.json`. Each shows the right missing file, offers only Close, and
leaves the folder byte-for-byte unchanged (quickstart V4).

- [ ] T022 [P] [US3] Add `show_missing_workspace_file(parent: tk.Misc, inspection: WorkspaceInspection) -> None` to `therepy_sessions/workspace/workspace_dialogs.py` per contracts/launch.md § Missing file:
  - title **Workspace File Missing**
  - message picked by whether `inspection.missing_file` is `inspection.files.students_file` (the student records file) or the templates file (the Templates file)
  - message text names the missing path, which file to restore, and which file it goes next to
  - button **Close** only
- [ ] T023 [P] [US3] Extend `open_workspace` in `therepy_sessions/workspace/workspace.py` with the parameter `show_missing_workspace_file: Callable[[WorkspaceInspection], None]` and the `PARTIAL` branch: call it with the inspection and return `None`. Remove the US1 "isn't a complete Workspace" error. The function now matches contracts/workspace.md exactly.
- [ ] T024 [US3] Wire US3 in `therepy_sessions/program.py` (depends on T022, T023): pass `show_missing_workspace_file=lambda i: show_missing_workspace_file(root, i)` to `open_workspace`.
- [ ] T025 [US3] Validate US3:
  - Offline (quickstart V1): `PARTIAL` calls only the fake `show_missing_workspace_file`, never the creators or the ask, and returns `None`.
  - Manual (quickstart V4) for both partial folders: the message, Close only, Close and the title-bar close both exit, an unchanged checksum of the remaining file, and opening with no prompt after the file is restored.

**Checkpoint**: All three Workspace States behave as the spec requires.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T026 [P] Run quickstart V7: every Workspace dialog matches the home screen in dark and light mode (FR-014); no dialog text contains a Student Key (FR-016); and V2–V6 behave the same with networking off and no AWS or Google credentials in the environment (FR-015).
- [ ] T027 [P] Run quickstart V8 and a final review:
  - the glossary, `layers.md` rule 11, DI rule 6, and constitution 1.7.0 match the code
  - `git status --ignored` shows Workspace files made in the repo root as ignored
  - `grep -rn "validate_storage_file_path\|validate_distinct_storage_files\|template_storage_file_path" therepy_sessions --include='*.py'` returns nothing
  - every public member in `workspace/` and both `create_empty_file` methods is fully annotated (Principle VI)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: depends on T001. Blocks every story.
- **US1 (Phase 3)**: depends on Foundational. This is the MVP.
- **US2 (Phase 4)**: depends on US1 (it extends `open_workspace` and the `program.py` wiring from T006 and T008).
- **US3 (Phase 5)**: depends on US1. It is independent of US2 in behavior, but both edit `open_workspace` and `program.py`, so run them one after the other.
- **Polish (Phase 6)**: after the stories you intend to ship.

### Within each story

- Dialog and store additions (marked [P]) come first. `open_workspace` changes come next, then `program.py` wiring, then validation.

### Parallel opportunities

- T001 ∥ T002.
- In US1, T009 ∥ T010 ∥ T011 ∥ T012 (docs) can be done alongside T006–T008. T013 waits for T010–T012.
- In US2, T015 ∥ T016 ∥ T017 (three different files), then T018, then T019.
- In US3, T022 ∥ T023, then T024.
- T026 ∥ T027.

## Parallel Example: User Story 2

```text
# After US1 is complete:
Task: "T015 [US2] JsonStudentStore.create_empty_file in students/json_student_store.py"
Task: "T016 [US2] TemplateStore.create_empty_file in interpretation/template_store.py"
Task: "T017 [US2] ask_to_start_new_workspace in workspace/workspace_dialogs.py"

# Then:
Task: "T018 [US2] NOT_SET_UP branch with rollback in workspace/workspace.py"
Task: "T019 [US2] Wire the new-Workspace callables in program.py"
```

## Implementation Strategy

### MVP first (User Story 1)

1. Phase 1 Setup → Phase 2 Foundational (T005 confirms the state rules).
2. Phase 3 (US1), including the doc amendments and the constitution bump → T014.
3. Stop and validate: the app launches from one folder or the picker. This can be
   merged.

### Incremental delivery

1. **+US2**: new Workspaces. Run T020 and T021.
2. **+US3**: the missing-file stop. Run T025.
3. **Polish**: T026 and T027.

Each step leaves the app safe, with one known gap until later stories close it. Before
US2 and US3, a folder that is not complete stops at **Can't Open Workspace** saying it
needs both files. Nothing is ever created or changed in it, so the stop is safe but less
helpful. A first Workspace can be made by hand with the empty formats in data-model.md.
