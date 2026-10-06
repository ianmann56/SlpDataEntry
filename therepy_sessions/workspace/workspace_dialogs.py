"""
Dialogs shown while a Workspace is opened, before the home screen.

Each dialog is a small modal ttk window, themed like the rest of the application. The
root window is withdrawn while they show, so they are centered on the screen. They show
only paths and fixed text, never file contents.
"""

import tkinter as tk
from tkinter import ttk

from workspace.workspace import (
    STUDENTS_FILE_NAME,
    TEMPLATES_FILE_NAME,
    WorkspaceCreateError,
    WorkspaceFolderError,
    WorkspaceInspection,
)

_CLOSE: str = "Close"


def show_workspace_error(parent: tk.Misc, error: WorkspaceFolderError | WorkspaceCreateError) -> None:
    """Show the problem and the path it is about. Offers only Close."""
    _show_dialog(parent, "Can't Open Workspace", error.reason, [_CLOSE], _CLOSE)


def ask_to_start_new_workspace(parent: tk.Misc, folder: str) -> bool:
    """
    Say the folder is not set up as a Workspace yet and ask whether to start one there.

    Returns:
        True only if the SLP pressed Start New Workspace. Close, Escape, and the title
        bar return False.
    """
    message = (
        "This folder doesn't appear to be set up as a Workspace yet:\n\n"
        f"{folder}\n\n"
        f"Start a new Workspace here? This creates an empty {STUDENTS_FILE_NAME} and an "
        f"empty {TEMPLATES_FILE_NAME} in this folder."
    )
    start = "Start New Workspace"
    return _show_dialog(parent, "Start a New Workspace?", message, [start, _CLOSE], _CLOSE) == start


def show_missing_workspace_file(parent: tk.Misc, inspection: WorkspaceInspection) -> None:
    """
    Name the missing Workspace file and what it holds, and tell the SLP to restore it
    next to the other file in the same folder and launch again. Offers only Close.
    """
    if inspection.missing_file == inspection.files.students_file:
        holds, missing_name, other_name = "student records", STUDENTS_FILE_NAME, TEMPLATES_FILE_NAME
    else:
        holds, missing_name, other_name = "Templates", TEMPLATES_FILE_NAME, STUDENTS_FILE_NAME
    message = (
        f"The {holds} file is missing from this Workspace:\n\n"
        f"{inspection.missing_file}\n\n"
        f"Restore {missing_name} next to {other_name} in the same folder, then launch again."
    )
    _show_dialog(parent, "Workspace File Missing", message, [_CLOSE], _CLOSE)


def _show_dialog(parent: tk.Misc, title: str, message: str, buttons: list[str], close_button: str) -> str:
    """
    Show a modal dialog and wait until it is closed.

    Args:
        parent: Window the dialog belongs to; it may be withdrawn
        title: Window title
        message: Text shown in the dialog
        buttons: Button labels, left to right; the last is the default
        close_button: The label the title-bar close and Escape act as

    Returns:
        The label of the button pressed
    """
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.resizable(False, False)
    pressed = close_button

    def press(label: str) -> None:
        nonlocal pressed
        pressed = label
        dialog.destroy()

    # The frame fills the whole window, so no unthemed Tk background shows
    frame = ttk.Frame(dialog, padding=20)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text=message, wraplength=480, justify="left").pack(anchor="w", pady=(0, 20))

    button_row = ttk.Frame(frame)
    button_row.pack(anchor="e")
    for index, label in enumerate(buttons):
        is_default = index == len(buttons) - 1
        button = ttk.Button(button_row, text=label, command=lambda label=label: press(label))
        button.pack(side="left", padx=(10 if index else 0, 0))
        if is_default:
            button.focus_set()
            dialog.bind("<Return>", lambda _event, label=label: press(label))

    dialog.protocol("WM_DELETE_WINDOW", lambda: press(close_button))
    dialog.bind("<Escape>", lambda _event: press(close_button))

    # The parent is withdrawn, so center on the screen. A dialog transient to a withdrawn
    # window is never shown by some window managers, so bring it forward instead.
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - dialog.winfo_reqwidth()) // 2
    y = (dialog.winfo_screenheight() - dialog.winfo_reqheight()) // 3
    dialog.geometry(f"+{x}+{y}")
    dialog.lift()
    dialog.focus_force()
    dialog.wait_visibility()
    dialog.grab_set()
    dialog.wait_window()
    return pressed
