import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class HomeWindow:
    """
    Navigation home screen for the application.

    Offers the two paths into the application and holds no business logic. What each
    choice opens, and hiding or showing this window, is wired in by `program.py`.
    """

    def __init__(
        self,
        master: tk.Tk,
        on_import: Callable[[], None],
        on_manage: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        """
        Initialize the home screen.

        Args:
            master: Root window the home screen is built in
            on_import: Called when the import and interpret choice is picked
            on_manage: Called when the setup and template management choice is picked
            on_exit: Called when the window is closed from its title bar
        """
        self._window = master
        self._on_import = on_import
        self._on_manage = on_manage
        self._on_exit = on_exit

        self._setup_window()
        self._create_widgets()

    def _setup_window(self) -> None:
        """Configure the main window properties."""
        self._window.title("SLP Data Entry")
        self._window.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _create_widgets(self) -> None:
        """Create and layout the two path choices."""
        main_frame = ttk.Frame(self._window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        import_button = ttk.Button(main_frame, text="Import & Interpret Student Data Sheets",
                                   command=self._on_import)
        import_button.pack(fill=tk.X, pady=(0, 10))

        manage_button = ttk.Button(main_frame, text="Manage Setup & Data Sheet Templates",
                                   command=self._on_manage)
        manage_button.pack(fill=tk.X)
