import tkinter as tk


def maximize(window: tk.Wm) -> None:
    """
    Maximize a window, so it fills the screen but can still be restored to its earlier size.

    Windows and macOS call this state "zoomed". X11 window managers have no such state,
    and Tk raises TclError for it there, so the `-zoomed` attribute is used instead.
    """
    try:
        window.state("zoomed")
    except tk.TclError:
        window.attributes("-zoomed", True)
