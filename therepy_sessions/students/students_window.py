import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from students.student import Student, TemplateChoice, UnreadableStudentRecordsError
from students.student_editor_window import StudentEditorWindow
from students.student_store import StudentStore
from tk_utils import error_handling


class StudentsWindow:
    """
    Window for listing and managing Students.

    It receives its student store and template provider by injection, and never builds
    them. Rules about Student Keys live in `students.student` and the store, not here.
    """

    def __init__(
        self,
        master: tk.Toplevel,
        student_store: StudentStore,
        list_template_choices: Callable[[], list[TemplateChoice]],
        on_back: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        """
        Initialize the Students window.

        Args:
            master: Window the Students window is built in
            student_store: Where students are saved and loaded
            list_template_choices: Returns the Data Sheet Templates a student can use
            on_back: Called when Back is pressed
            on_exit: Called when the window is closed from its title bar
        """
        self._window = master
        self._student_store = student_store
        self._list_template_choices = list_template_choices
        self._on_back = on_back
        self._on_exit = on_exit

        self._setup_window()
        self._create_widgets()
        self.refresh()

    def _setup_window(self) -> None:
        """Configure the main window properties."""
        self._window.title("Students")
        self._window.resizable(True, True)
        self._window.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _create_widgets(self) -> None:
        """Create and layout the student list and buttons."""
        main_frame = ttk.Frame(self._window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self._students_treeview = ttk.Treeview(list_frame, columns=("key", "template"),
                                               show="headings", height=10)
        self._students_treeview.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self._students_treeview.heading("key", text="Student Key")
        self._students_treeview.heading("template", text="Current Template")
        self._students_treeview.column("key", width=120, minwidth=80)
        self._students_treeview.column("template", width=250, minwidth=150)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._students_treeview.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self._students_treeview.configure(yscrollcommand=scrollbar.set)
        self._students_treeview.bind("<Double-Button-1>", lambda event: self._on_edit())

        self._button_frame = ttk.Frame(main_frame)
        self._button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))

        add_button = ttk.Button(self._button_frame, text="Add Student", command=self._on_add)
        add_button.pack(side=tk.LEFT, padx=(0, 10))

        edit_button = ttk.Button(self._button_frame, text="Edit Selected", command=self._on_edit)
        edit_button.pack(side=tk.LEFT, padx=(0, 10))

        remove_button = ttk.Button(self._button_frame, text="Remove Selected", command=self._on_remove)
        remove_button.pack(side=tk.LEFT, padx=(0, 10))

        back_button = ttk.Button(self._button_frame, text="Back", command=self._on_back)
        back_button.pack(side=tk.RIGHT)

    def refresh(self) -> None:
        """Reload the student list from the student store."""
        for item in self._students_treeview.get_children():
            self._students_treeview.delete(item)

        try:
            choices = self._list_template_choices()
            for student in self._student_store.list_students():
                self._students_treeview.insert("", tk.END, iid=student.student_key,
                                               values=(student.student_key, _template_label(student, choices)))
        except UnreadableStudentRecordsError as e:
            error_handling.throw(e, "Could not load students")

    def _selected_key(self) -> str | None:
        """Return the Student Key of the selected row, or None."""
        selection = self._students_treeview.selection()
        return selection[0] if selection else None

    def _on_edit(self) -> None:
        """Open the editor for the selected student."""
        key = self._selected_key()
        if key is None:
            messagebox.showwarning("No Selection", "Please select a student to edit.", parent=self._window)
            return
        try:
            student = self._student_store.get_student(key)
        except Exception as e:
            error_handling.throw(e, "Could not open the student")
            return
        if student is None:
            self.refresh()
            return
        StudentEditorWindow(self._window, self._student_store, self._list_template_choices(), student,
                            on_saved=self.refresh)

    def _on_remove(self) -> None:
        """Remove the selected student after the SLP confirms."""
        key = self._selected_key()
        if key is None:
            messagebox.showwarning("No Selection", "Please select a student to remove.", parent=self._window)
            return
        if not messagebox.askyesno("Confirm Remove", f'Remove the student "{key}"?', parent=self._window):
            return
        try:
            self._student_store.delete_student(key)
        except Exception as e:
            error_handling.throw(e, "Could not remove the student")
        self.refresh()

    def _on_add(self) -> None:
        """Open the editor to add a new student."""
        StudentEditorWindow(self._window, self._student_store, self._list_template_choices(), None,
                            on_saved=self.refresh)


def ask_to_start_fresh(parent: tk.Misc, error: UnreadableStudentRecordsError) -> bool:
    """
    Ask whether to start with an empty student list when the saved records can't be read.

    Returns:
        True if the SLP chose to start fresh, keeping the unreadable file as a backup
    """
    return messagebox.askyesno(
        "Student Records Could Not Be Loaded",
        f"The student records in {error.file_path} could not be loaded.\n\n"
        "Start with an empty student list? The unreadable file will be kept as a backup.",
        parent=parent,
    )


def _template_label(student: Student, choices: list[TemplateChoice]) -> str:
    """Return how a student's Current Template is shown in the list."""
    if student.current_template_id is None:
        return "None selected"
    for choice in choices:
        if choice.template_id == student.current_template_id:
            return choice.name
    return "Missing template"
