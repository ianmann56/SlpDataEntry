import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class ImportWindow:
    """
    Window for the import and interpret path.

    The import and interpret process is not built yet, so for now this window only
    says so and offers a way back. Its content is a placeholder, to be replaced when
    that path is built.
    """

    def __init__(
        self,
        master: tk.Toplevel,
        on_back: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        """
        Initialize the import window.

        Args:
            master: Window the import window is built in
            on_back: Called when Back is pressed
            on_exit: Called when the window is closed from its title bar
        """
        self._window = master
        self._on_back = on_back
        self._on_exit = on_exit

        self._setup_window()
        self._create_widgets()

    def _setup_window(self) -> None:
        """Configure the main window properties."""
        self._window.title("Import & Interpret Student Data Sheets")
        self._window.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _create_widgets(self) -> None:
        """Create and layout the window widgets."""
        main_frame = ttk.Frame(self._window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        message_label = ttk.Label(main_frame,
                                  text="Importing and interpreting Student Data Sheets is not available yet.")
        message_label.pack(pady=(0, 20))

        back_button = ttk.Button(main_frame, text="Back", command=self._on_back)
        back_button.pack()
