# Contract: UI Windows

**Feature**: [../spec.md](../spec.md) | **Date**: 2026-09-27

This page covers the public constructor signatures and visible behavior of the windows this
feature adds or changes. All signatures follow Principle VI: every parameter and the
return type are annotated, using built-in generics, `X | None`, and
`collections.abc.Callable`.

## `app_shell.home_window.HomeWindow` (new)

```python
class HomeWindow:
    def __init__(
        self,
        master: tk.Tk,
        on_import: Callable[[], None],
        on_manage: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None: ...
```

- Builds its widgets inside `master`, the root window, and sets the window title to
  `SLP Data Entry`.
- Shows exactly two buttons (FR-002, FR-003):
  - **Import & Interpret Student Data Sheets** → `on_import()`
  - **Manage Setup & Data Sheet Templates** → `on_manage()`
- The title-bar close button (`WM_DELETE_WINDOW`) → `on_exit()` (FR-010).
- It doesn't hide or show itself. `program.py` does that.
- It imports only `tkinter` / `tkinter.ttk`, and nothing from `clients/`, `collection/`,
  `interpretation/`, or `storage/`.

## `app_shell.import_placeholder_window.ImportPlaceholderWindow` (new)

```python
class ImportPlaceholderWindow:
    def __init__(
        self,
        master: tk.Toplevel,
        on_back: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None: ...
```

- Builds its widgets inside `master` and sets the title to
  `Import & Interpret Student Data Sheets`.
- Shows a message saying the import and interpret process is not available yet
  (FR-006), and a **Back** button → `on_back()` (FR-007).
- The title-bar close button → `on_exit()` (research R4).
- It offers no other controls and starts no import, OCR, interpretation, or output work
  (FR-008).
- It has the same import restriction as `HomeWindow`.

## `interpretation.template_manager.template_management_window.DataSheetTemplateManagementWindow` (changed)

```python
class DataSheetTemplateManagementWindow:
    def __init__(
        self,
        template_store: TemplateStore,
        master: tk.Misc,
        close_callback: Callable[[], None] | None = None,
        interpreter_configs: list[InterpreterConfig] | None = None,
        back_callback: Callable[[], None] | None = None,
    ) -> None: ...
```

- **Unchanged**: the list, create, edit, and delete behavior, and the fact that the window
  takes over `master` (its title and close protocol). Close and the title-bar close still
  call `close_callback`.
- **New**: when `back_callback` is not `None`, a **Back** button appears in the button
  row, to the left of **Close**, and calls `back_callback()` (FR-005). When it is `None`,
  the window looks and behaves exactly as it does today.
- This change must annotate the modified `__init__` fully (Principle VI).

## Composition root wiring (`program.py`)

`program.py` is the only module that connects these windows (Principle III):

| Callback | Wired to |
| --- | --- |
| `HomeWindow.on_manage` | withdraw root → new `tk.Toplevel(root)` → `DataSheetTemplateManagementWindow(store, top, close_callback=root.destroy, interpreter_configs=STUB_INTERPRETER_CONFIGS, back_callback=<destroy top + deiconify root>)` |
| `HomeWindow.on_import` | withdraw root → new `tk.Toplevel(root)` → `ImportPlaceholderWindow(top, on_back=<destroy top + deiconify root>, on_exit=root.destroy)` |
| every `on_exit` / `close_callback` | `root.destroy` |
