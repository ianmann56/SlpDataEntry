# Data Model: Application Entry Point

**Feature**: [spec.md](spec.md) | **Date**: 2026-09-27

This feature adds no persisted data and no new domain entities. The Template Store and
its JSON file are used as is. What this feature does add is a small **navigation state**
held by the composition root (`program.py`), described here as a state machine.

## Navigation State

| State | Visible window | Root (home) | Notes |
| --- | --- | --- | --- |
| `HOME` | Home screen | shown | Start state after launch validation succeeds |
| `MANAGING_TEMPLATES` | Data Sheet Template management (Toplevel) | withdrawn | Creator and editor windows may open modally on top |
| `IMPORTING` | Import and interpret window (Toplevel, placeholder content for now) | withdrawn | Starts no import, OCR, or interpretation action (FR-008) |
| `EXITED` | none | destroyed | Terminal state; `mainloop()` returns |

At most one path window exists at any time. It is created on entry and destroyed on
exit from its state.

## Transitions

| From | Trigger | To | Effect |
| --- | --- | --- | --- |
| *(launch)* | valid `.json` path argument | `HOME` | Build root, apply theme, build `TemplateStore`, show home |
| *(launch)* | missing / non-`.json` argument | *(process exits)* | Print existing usage message; no window shown |
| `HOME` | pick "manage" choice | `MANAGING_TEMPLATES` | Withdraw root; create Toplevel + `DataSheetTemplateManagementWindow` |
| `HOME` | pick "import and interpret" choice | `IMPORTING` | Withdraw root; create Toplevel + `ImportWindow` |
| `HOME` | close home window | `EXITED` | `root.destroy()` |
| `MANAGING_TEMPLATES` | Back | `HOME` | Destroy Toplevel; `root.deiconify()` |
| `MANAGING_TEMPLATES` | Close button or title-bar close | `EXITED` | `root.destroy()` (also closes any open creator/editor) |
| `IMPORTING` | Back | `HOME` | Destroy Toplevel; `root.deiconify()` |
| `IMPORTING` | title-bar close | `EXITED` | `root.destroy()` |

## Existing entities touched

- **Template Store** (`TemplateStore`): one instance, built once at launch from the path
  argument and shared across every visit to template management. It is not changed.
- **Data Sheet Template management window** (`DataSheetTemplateManagementWindow`): gains
  the optional `back_callback`. See [contracts/ui-windows.md](contracts/ui-windows.md).
