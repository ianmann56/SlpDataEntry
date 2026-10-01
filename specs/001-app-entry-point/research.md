# Research: Application Entry Point

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-09-27

Technical Context had no open unknowns. The project stack is fixed by the constitution
(Python 3.12, Tkinter, `sv-ttk`, `darkdetect`). The items below are the design decisions
the spec left open, resolved against the existing code.

## R1. Window arrangement: one root, one window per path

- **Decision**: The `tk.Tk` root *is* the home screen. Each path opens in its own
  `tk.Toplevel`. When a path opens, the root is hidden with `withdraw()`. On Back, the path's
  Toplevel is destroyed and the root is restored with `deiconify()`.
- **Rationale**: This satisfies FR-012 (home hidden while a path is open) with no extra
  state. A single Tk interpreter also keeps `sv_ttk.set_theme(...)` applied to every window
  (FR-011). Destroying and re-creating the path window on each visit means template
  management re-reads the Template Store every time (User Story 2, scenario 4), and two
  copies can never exist (SC-004).
- **Alternatives considered**:
  - *Swap frames inside a single window.* Rejected: `DataSheetTemplateManagementWindow`
    takes over its `master` (it sets the title and the `WM_DELETE_WINDOW` protocol, and
    packs into it). Reusing the root would need that window reworked, and the spec wants it
    reused as is apart from Back.
  - *Keep the root visible and disable its buttons.* Rejected in clarification (Q2).

## R2. Where the home screen and import window code lives

- **Decision**: A new package `therepy_sessions/app_shell/` with `home_window.py`, and a
  new package `therepy_sessions/interpretation/importing/` with `import_window.py`. These
  windows know nothing about templates, stores, or clients. They take plain callbacks (`on_manage`, `on_import`, `on_back`, `on_exit`).
  `program.py` wires those callbacks to the real windows.
  The import window is named for its role (`import_window.py` / `ImportWindow`), not
  for its current placeholder content, so the import and interpret feature can fill it in
  without renaming it or changing the wiring in `program.py`.
- **Rationale**: Principle III says UI is a shell and `program.py` is the only
  composition root. Callback injection keeps `app_shell` free of imports from the pipeline
  layers, and keeps "which window opens for which path" in the composition root.
  `interpretation/template_manager/` is the wrong home for the home screen, because the
  home screen is not part of interpretation. `tk_utils/` is for shared helpers, not screens.
  The import window is different: it is the entry to the import and interpret path, so it
  sits in `interpretation/importing/`, beside the template management windows (the same
  pattern as `template_manager/*_window.py`, `layers.md` rule 5). When the real flow is
  built, the window takes its collection and interpretation work through callbacks or
  constructor arguments wired in `program.py`. It does not build clients itself.
- **Alternatives considered**:
  - *Put the window classes in `program.py`.* Rejected: it mixes wiring with widget code and
    keeps growing as real paths arrive.
  - *Keep `import_window.py` in `app_shell/`.* Rejected: the window belongs to the import
    and interpret path, not to navigation, and the later feature fills it with
    interpretation UI.
  - *Have `HomeWindow` import `DataSheetTemplateManagementWindow` directly.* Rejected: it
    couples the shell to interpretation and hides wiring outside the composition root.
- **Constitution impact**: `docs/conventions/architecture/layers.md` lists the packages
  and the rules on who may import whom. Adding `app_shell/` to that list, with its import
  rule, adds guidance. Under Governance, that is a **MINOR** amendment (1.1.0 → 1.2.0),
  made in the same change. See the plan's Constitution Check.

## R3. Back button on the template management window

- **Decision**: Add an optional keyword parameter
  `back_callback: Callable[[], None] | None = None` to
  `DataSheetTemplateManagementWindow.__init__`. When it is given, a **Back** button is added
  to the button row, to the left of **Close**, and clicking it calls `back_callback`. Close
  and the window's title-bar close button keep calling `close_callback`, which
  `program.py` sets to exit the application (FR-005a).
- **Rationale**: This is the smallest change that meets FR-005. Making the parameter
  optional with a default leaves existing callers (`program_interpret.py` does not use this
  window; nothing else does) unaffected. Principle VI requires the modified `__init__` to be
  fully annotated in this change.
- **Alternatives considered**:
  - *Rename Close to Exit.* Deferred: it is a wording change the spec did not ask for.
  - *Make Close behave as Back.* Rejected: clarification Q1 made closing exit the app.

## R4. Closing the placeholder window from its title bar

- **Decision**: The title-bar close button on the import and interpret placeholder exits
  the application, the same as template management.
- **Rationale**: The spec only defines Back for the placeholder. Giving both path windows
  the same close rule (FR-005a) is the least surprising choice. A hidden root with no
  visible window would otherwise leave an invisible, still-running process.
- **Alternatives considered**: *Title-bar close acts as Back.* Rejected for consistency
  with template management.

## R5. Exiting the application

- **Decision**: `program.py` passes `root.destroy` as the exit callback everywhere (home
  close, path-window close, the management Close button).
- **Rationale**: `destroy()` tears down the root and every Toplevel, including any open
  template creator or editor window, and then `mainloop()` returns. `quit()`, which the
  current `program_manage.py` uses, only stops the loop and leaves the windows alive until
  the process exits. `destroy()` is the clean choice once there is more than one window.
  This also covers the edge case of closing template management while an editor window is
  open.

## R6. No external services at startup

- **Decision**: `program.py` MUST NOT import `clients/` or call `create_google_service()` or
  `construct_textract_client()`. It builds only the Tk root, the theme, the `TemplateStore`,
  and the windows.
- **Rationale**: Today `program_manage.py` calls `create_google_service()` at startup,
  which can start a Google OAuth browser flow just to manage templates. FR-009 and SC-005
  forbid that. No path in this feature needs a client. The import and interpret feature will
  add lazy `inject_*` providers (Principle IV) when it needs them.

## R7. Launch contract and the leftover scripts

- **Decision**: The new `therepy_sessions/program.py` keeps the current
  `<template_storage_file_path>` argument, `.json` validation, and usage message (the
  existing `validate_storage_file_path` and `parse_command_line_args` logic moves over from
  `program_manage.py`). `program_manage.py` is deleted (FR-013). `program_interpret.py`
  stays as a developer-only script. It gets a module docstring saying so, its usage text
  is corrected to name itself and its three arguments instead of `program.py`, and its
  argument-count check is corrected to require all three, so a missing argument prints
  usage instead of raising `IndexError` (FR-014).
- **Rationale**: The launch command stays unchanged for the SLP (per the spec's
  Assumptions). The interpretation script is kept on purpose, as decided in clarification
  Q3.

## R8. Verification approach

- **Decision**: Verification is manual, following [quickstart.md](quickstart.md). No
  automated test framework is added.
- **Rationale**: The repository has no test suite or test dependency today, and this
  feature adds no business logic, only navigation between windows. Adding `pytest` plus a
  headless display setup would be a new dependency the constitution requires justifying,
  for little gain. The navigation state machine in [data-model.md](data-model.md) is small
  enough to walk through by hand.
- **Alternatives considered**: *A scripted Tk smoke test using `root.after(...)` to click
  through the paths.* Worth adding with the first feature that brings a test framework.
