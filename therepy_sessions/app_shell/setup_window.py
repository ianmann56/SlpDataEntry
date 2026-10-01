import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class SetupWindow:
    """
    Setup menu for the application's setup and configuration areas.

    A navigation menu that holds no business logic. What each choice opens, and hiding
    or showing this window, is wired in by `program.py`.
    """

    def __init__(
        self,
        master: tk.Toplevel,
        on_templates: Callable[[], None],
        on_students: Callable[[], None],
        on_back: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        """
        Initialize the Setup menu.

        Args:
            master: Window the Setup menu is built in
            on_templates: Called when the Data Sheet Templates choice is picked
            on_students: Called when the Students choice is picked
            on_back: Called when Back is pressed
            on_exit: Called when the window is closed from its title bar
        """
        self._window = master
        self._on_templates = on_templates
        self._on_students = on_students
        self._on_back = on_back
        self._on_exit = on_exit

        self._setup_window()
        self._create_widgets()

    def _setup_window(self) -> None:
        """Configure the main window properties."""
        self._window.title("Setup")
        self._window.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _create_widgets(self) -> None:
        """Create and layout the setup choices and Back."""
        main_frame = ttk.Frame(self._window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        templates_button = ttk.Button(main_frame, text="Data Sheet Templates",
                                      command=self._on_templates)
        templates_button.pack(fill=tk.X, pady=(0, 10))

        students_button = ttk.Button(main_frame, text="Students",
                                     command=self._on_students)
        students_button.pack(fill=tk.X)

        back_button = ttk.Button(main_frame, text="Back", command=self._on_back)
        back_button.pack(fill=tk.X, pady=(20, 0))
