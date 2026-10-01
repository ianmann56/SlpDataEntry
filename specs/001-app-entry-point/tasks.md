---

description: "Task list for the Application Entry Point feature"
---

# Tasks: Application Entry Point

**Input**: Design documents from `/specs/001-app-entry-point/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/ui-windows.md](contracts/ui-windows.md),
[contracts/cli.md](contracts/cli.md), [quickstart.md](quickstart.md)

**Tests**: No automated tests. The spec does not ask for them, and research R8 makes
verification manual through [quickstart.md](quickstart.md). Each story phase ends with
the quickstart section that checks it.

**Organization**: Tasks are grouped by user story so each story can be built and checked
on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

- All application code lives under `therepy_sessions/` (single desktop project, see
  [plan.md](plan.md) Project Structure). Modules import each other by package path from
  that directory (e.g. `from interpretation.template_store import TemplateStore`), and
  scripts run from `therepy_sessions/` with the shebang `#!../.venv/bin/python3`.
- Every public function, method, and `__init__` added or changed here MUST be fully
  annotated per [docs/conventions/architecture/type-declarations.md](../../docs/conventions/architecture/type-declarations.md)
  (built-in generics, `X | None`, `collections.abc.Callable`, explicit `-> None`).
- Theme: `sv_ttk.set_theme(darkdetect.theme())` is called once on the root in
  `program.py`. New windows use `ttk` widgets so they inherit it (FR-011). They do not set
  the theme themselves.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new package that the home screen lives in.

- [X] T001 Create the `app_shell` package by adding an empty `therepy_sessions/app_shell/__init__.py` (plan.md Project Structure, research R2).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The new composition root that every story is wired into.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Create `therepy_sessions/program.py` as the single entry point and composition root, following [contracts/cli.md](contracts/cli.md) and research R5–R7:
  - Shebang `#!../.venv/bin/python3`. Make the file executable (`chmod +x therepy_sessions/program.py`).
  - Move `validate_storage_file_path(file_path: str) -> None` and `parse_command_line_args() -> list[str]` over from `therepy_sessions/program_manage.py`. Keep the exact messages: `Usage: python program.py <template_storage_file_path>`, `Example: python program.py templates.json`, `Error: Storage file must be a JSON file (got: <path>)`, `Please provide a file path with .json extension`, each followed by `sys.exit(1)`. Add full type annotations and keep the docstrings.
  - `main() -> None`: parse the args, create `root = tk.Tk()`, call `sv_ttk.set_theme(darkdetect.theme())`, build one `TemplateStore(storage_file_path)` (from `interpretation.template_store`), then call `root.mainloop()`. Leave a clearly marked spot after the store is built where US1 attaches the home screen.
  - Keep the `if __name__ == '__main__':` block with the `try` / `except Exception` and `traceback.print_exc()`, and fix the "unahandled" typo to "unhandled".
  - MUST NOT import anything from `clients/`, `collection/`, or `storage/`, or import `ipdb` or `os`. MUST NOT call `create_google_service()` or `construct_textract_client()` (FR-009, research R6).

**Checkpoint**: `../.venv/bin/python3 program.py` and `../.venv/bin/python3 program.py foo.txt` (run from `therepy_sessions/`) print the usage and JSON errors and exit 1 (quickstart V1, first two rows). A valid `.json` path opens an empty root window.

---

## Phase 3: User Story 1 - Choose a path from one home screen (Priority: P1) 🎯 MVP

**Goal**: Launching `program.py` shows one home screen with exactly two labeled choices. Closing it exits the app.

**Independent Test**: Launch `program.py sample_data/templates.json`, see the home screen titled `SLP Data Entry` with the two buttons, then close it with the title-bar ✕ and confirm the process exits (quickstart V1 row 3, V2, V7).

### Implementation for User Story 1

- [X] T003 [P] [US1] Create `HomeWindow` in `therepy_sessions/app_shell/home_window.py` per [contracts/ui-windows.md](contracts/ui-windows.md) `app_shell.home_window.HomeWindow`:
  - `__init__(self, master: tk.Tk, on_import: Callable[[], None], on_manage: Callable[[], None], on_exit: Callable[[], None]) -> None`.
  - Set `master.title("SLP Data Entry")`, and register `master.protocol("WM_DELETE_WINDOW", on_exit)`.
  - Inside a padded `ttk.Frame` packed into `master` with `pack(fill=tk.BOTH, expand=True)` (so the themed frame covers the whole window, FR-011), show exactly two `ttk.Button`s stacked vertically: **Import & Interpret Student Data Sheets** → `on_import`, then **Manage Setup & Data Sheet Templates** → `on_manage` (FR-002, FR-003).
  - It MUST NOT withdraw or deiconify itself (`program.py` does that).
  - Store any callbacks as `_`-prefixed attributes (e.g. `self._on_exit`), and add no public attributes.
  - Imports are limited to `tkinter`, `tkinter.ttk`, and `collections.abc.Callable`. Nothing from `clients/`, `collection/`, `interpretation/`, or `storage/`.
  - Add a class docstring saying it is the navigation home screen and holds no business logic.
- [X] T004 [US1] Attach the home screen in `therepy_sessions/program.py` (depends on T002, T003): import `HomeWindow` from `app_shell.home_window`, and construct `HomeWindow(root, on_import=..., on_manage=..., on_exit=root.destroy)` before `root.mainloop()`. Until US2 and US3 land, `on_import` and `on_manage` are private no-op functions in `program.py` (`def _open_import_path() -> None: pass` and `def _open_management_path() -> None: pass`, or closures inside `main`) so the buttons can be clicked without error.

**Checkpoint**: Quickstart V1 (all rows), V2, and V7 pass. Both buttons are present and do nothing yet.

---

## Phase 4: User Story 2 - Open template management from the home screen (Priority: P2)

**Goal**: **Manage Setup & Data Sheet Templates** hides home and opens the existing template management window, which gains a Back button. Back returns home, and Close or ✕ exits.

**Independent Test**: Quickstart V3 steps 1–6, plus V5 for the management path.

### Implementation for User Story 2

- [X] T005 [P] [US2] Add the Back button to `DataSheetTemplateManagementWindow` in `therepy_sessions/interpretation/template_manager/template_management_window.py` per [contracts/ui-windows.md](contracts/ui-windows.md) and research R3:
  - Change the signature to `__init__(self, template_store: TemplateStore, master: tk.Misc, close_callback: Callable[[], None] | None = None, interpreter_configs: list[InterpreterConfig] | None = None, back_callback: Callable[[], None] | None = None) -> None`, and store it as the private attribute `self._back_callback = back_callback` (no new public attribute).
  - Import `Callable` from `collections.abc`. Import `TemplateStore` (from `interpretation.template_store`) and `InterpreterConfig` (from `interpretation.template_manager.interpreter_configs`) under `if TYPE_CHECKING:` with `from __future__ import annotations`, so no new runtime import cycle appears.
  - In `_create_widgets`, when `self._back_callback is not None`, add `ttk.Button(button_frame, text="Back", command=self._on_back)` packed `side=tk.RIGHT, padx=(0, 10)`, created *after* the Close button so it sits to the left of Close. Add `_on_back(self) -> None`, which calls `self._back_callback()`.
  - When `back_callback` is `None`, the window MUST look and behave exactly as before. Do not change the list, create, edit, delete, or Close behavior.
  - Update the `__init__` docstring's Args to list `back_callback`.
- [X] T006 [US2] Wire the management path in `therepy_sessions/program.py` (depends on T004, T005), replacing the `on_manage` no-op per the composition-root table in [contracts/ui-windows.md](contracts/ui-windows.md) and [data-model.md](data-model.md) (`HOME` → `MANAGING_TEMPLATES`):
  - On pick: `root.withdraw()`, then `top = tk.Toplevel(root)`, then `DataSheetTemplateManagementWindow(template_store, top, close_callback=root.destroy, interpreter_configs=STUB_INTERPRETER_CONFIGS, back_callback=<back>)`, then `.show()`.
  - `<back>` destroys `top` and calls `root.deiconify()`.
  - Import `DataSheetTemplateManagementWindow` and `STUB_INTERPRETER_CONFIGS` from `interpretation.template_manager.*`.
  - Put the "withdraw root, make Toplevel" and "destroy Toplevel, deiconify root" steps in small private helpers so US3 reuses them. Each visit makes a fresh Toplevel, so the store is re-read and no second copy can exist (research R1, SC-004).
- [X] T007 [US2] Delete `therepy_sessions/program_manage.py` (FR-013, contracts/cli.md). Run `grep -rn "program_manage" --exclude-dir=.git --exclude-dir=specs .` from the repo root and remove any remaining references outside `specs/`.

**Checkpoint**: Quickstart V3 and V5 (management path) pass. V8's first bullet (`ls program_manage.py` → "No such file") passes.

---

## Phase 5: User Story 3 - Placeholder for import and interpret, with a way back (Priority: P3)

**Goal**: **Import & Interpret Student Data Sheets** hides home and opens `ImportWindow`. For now it only says the feature is not available yet and offers Back. ✕ exits.

**Independent Test**: Quickstart V4 steps 1–3, plus V5 for the import path.

### Implementation for User Story 3

- [X] T008 [P] [US3] Create `ImportWindow` in `therepy_sessions/interpretation/importing/import_window.py` (new directory `interpretation/importing/`, with no `__init__.py`, matching `template_manager/`), per [contracts/ui-windows.md](contracts/ui-windows.md) `interpretation.importing.import_window.ImportWindow` and research R2 and R4:
  - `__init__(self, master: tk.Toplevel, on_back: Callable[[], None], on_exit: Callable[[], None]) -> None`.
  - Set `master.title("Import & Interpret Student Data Sheets")`, and register `master.protocol("WM_DELETE_WINDOW", on_exit)`.
  - Inside a padded `ttk.Frame` packed into `master` with `pack(fill=tk.BOTH, expand=True)` (so the themed frame covers the whole window, FR-011), show a `ttk.Label` saying the import and interpret process is not available yet (FR-006), and a single **Back** `ttk.Button` → `on_back` (FR-007). There are no other controls, and nothing starts import, OCR, interpretation, or output (FR-008).
  - Imports are limited to `tkinter`, `tkinter.ttk`, and `collections.abc.Callable`. Nothing from `storage/` or `clients/`, as required for the `interpretation` layer.
  - Store any callbacks as `_`-prefixed attributes (e.g. `self._on_back`), and add no public attributes.
  - The class docstring describes it as the window for the import and interpret path, and notes that its current content is a placeholder to be replaced when that path is built. The module and class names MUST NOT mention "placeholder".
- [X] T009 [US3] Wire the import path in `therepy_sessions/program.py` (depends on T004, T008, and T006's helpers if present), replacing the `on_import` no-op per [contracts/ui-windows.md](contracts/ui-windows.md) and [data-model.md](data-model.md) (`HOME` → `IMPORTING`):
  - On pick: `root.withdraw()`, then `top = tk.Toplevel(root)`, then `ImportWindow(top, on_back=<destroy top + root.deiconify()>, on_exit=root.destroy)`.
  - Import `ImportWindow` from `interpretation.importing.import_window`.
  - If US2 has not landed, add the same withdraw/Toplevel and destroy/deiconify private helpers described in T006.

**Checkpoint**: Quickstart V4 and V5 (import path) pass. All three stories work.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Developer script cleanup, constitution amendment, and full validation.

- [X] T010 [P] Mark `therepy_sessions/program_interpret.py` as developer-only (FR-014, research R7, contracts/cli.md):
  - Add a module docstring right after the shebang. It says this is a temporary developer-only script for checking interpreters against sample sheets, that it is not reachable from `program.py`, that it is a recorded Principle III deviation (see `specs/001-app-entry-point/plan.md` Complexity Tracking), and that it is to be deleted when the import and interpret path is built.
  - Change its usage lines to `Usage: python program_interpret.py <template_storage_file_path> <template_id> <image_path>` and `Example: python program_interpret.py templates.json 3 sample_data/simple_3_way_tally.png`, and change the `len(sys.argv) < 2` check to `< 4` to match the three required arguments.
  - Apart from the argument-count check, do not change its runtime flow.
- [X] T011 [P] Amend `docs/conventions/architecture/layers.md` (research R2, plan Constitution Check III):
  - Add an `app_shell/` line to the package layout block: `app_shell/       navigation shell windows (home screen); Tkinter only`.
  - Add a rule saying `app_shell/` MUST NOT import from `clients/`, `collection/`, `interpretation/`, or `storage/`, and gets everything it opens through callbacks wired in `program.py`.
  - Update rule 5's example of UI windows to cover both `interpretation/template_manager/*_window.py` and `interpretation/importing/*_window.py`.
- [X] T012 Amend `.specify/memory/constitution.md` per its Governance procedure (depends on T011):
  - Prepend a new Sync Impact Report: version 1.1.0 → 1.2.0 (MINOR: new layer rule in a referenced doc). Modified principles: none. Supporting docs: updated `docs/conventions/architecture/layers.md` (adds `app_shell/` and its import rule, and adds `interpretation/importing/` to the UI-window example). Prior history keeps the 1.1.0 and 1.0.0 entries.
  - Set the footer to `**Version**: 1.2.0`, with `**Last Amended**:` set to the date of the change (YYYY-MM-DD).
- [X] T013 Verify the import boundaries from the repo root:
  - `grep -nE "^(from|import) (clients|collection|storage)([. ]|$)" therepy_sessions/program.py` → no matches.
  - `grep -nE "create_google_service|construct_textract_client" therepy_sessions/program.py` → no matches.
  - `grep -nE "^(from|import) " therepy_sessions/app_shell/home_window.py therepy_sessions/interpretation/importing/import_window.py` → only `tkinter`, `collections.abc`, and `__future__` imports.
  - Check the type annotations on every public signature and public attribute added or changed in T002–T009 against [type-declarations.md](../../docs/conventions/architecture/type-declarations.md).
- [ ] T014 Run the full manual validation in [quickstart.md](quickstart.md) V1–V9 from `therepy_sessions/` using only `sample_data/templates.json` (Principle I), and fix any failure in the file responsible.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: T002 has no hard dependency on T001, but it does the same groundwork, so do T001 first.
- **US1 (Phase 3)**: T003 depends on T001. T004 depends on T002 and T003.
- **US2 (Phase 4)** and **US3 (Phase 5)**: both depend on US1 (T004), because they replace its no-op callbacks. Neither depends on the other.
- **Polish (Phase 6)**: T010 and T011 can start any time after Phase 2. T012 depends on T011. T013 and T014 depend on every story you plan to ship.

### User Story Dependencies

- **US1 (P1)**: The foundation. Both other paths hang off the home screen.
- **US2 (P2)**: Needs US1. Independent of US3.
- **US3 (P3)**: Needs US1. Independent of US2. If both are built at once, whichever lands second reuses the navigation helpers the first added to `program.py`.

### Same-file sequencing

`therepy_sessions/program.py` is touched by T002, T004, T006, and T009. Do these one at a time, in that order (or T009 before T006). They are never `[P]` with each other.

### Parallel Opportunities

- T003 (`app_shell/home_window.py`), T005 (`template_management_window.py`), T008 (`interpretation/importing/import_window.py`), T010 (`program_interpret.py`), and T011 (`layers.md`) are all different files with no shared dependencies beyond T001, so they can be written in parallel.
- After T004, US2 (T005 → T006 → T007) and US3 (T008 → T009) can proceed in parallel, up to the point where both edit `program.py`.

---

## Parallel Example: after Phase 2

```bash
# Window classes and docs, all different files:
Task: "T003 Create HomeWindow in therepy_sessions/app_shell/home_window.py"
Task: "T005 Add Back button to DataSheetTemplateManagementWindow in therepy_sessions/interpretation/template_manager/template_management_window.py"
Task: "T008 Create ImportWindow in therepy_sessions/interpretation/importing/import_window.py"
Task: "T010 Mark therepy_sessions/program_interpret.py as developer-only"
Task: "T011 Amend docs/conventions/architecture/layers.md"

# Then sequentially in program.py: T004 → T006 → T009
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (T001) and Phase 2 (T002).
2. Phase 3 (T003, T004).
3. **Stop and validate**: quickstart V1, V2, and V7. The app launches offline to a home screen with two choices, and closing it exits.

### Incremental Delivery

1. Setup + Foundational + US1 → the MVP home screen.
2. Add US2 (T005–T007) → template management reachable, with Back. `program_manage.py` gone. Validate with V3 and V5.
3. Add US3 (T008, T009) → import path reachable, with Back. Validate with V4 and V5.
4. Polish (T010–T014) → dev script marked, constitution amended to 1.2.0, full quickstart pass.

---

## Notes

- `[P]` tasks touch different files and have no dependencies on incomplete tasks.
- Use only synthetic data (`sample_data/templates.json`) for every manual check (Principle I).
- Commit after each task or logical group, and stop at any checkpoint to validate a story on its own.
