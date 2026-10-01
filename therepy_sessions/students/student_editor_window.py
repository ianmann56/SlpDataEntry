import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from students.student import (
    DuplicateStudentKeyError,
    Student,
    StudentKeyError,
    TemplateChoice,
    student_keys_match,
)
from students.student_field_editors import CurrentTemplateFieldEditor, StudentFieldEditor, StudentKeyFieldEditor
from students.student_store import StudentStore
from tk_utils import error_handling


class StudentEditorWindow:
    """
    Modal dialog for adding a student, or viewing and editing one.

    The form is built from field editors, so later settings are added without changing
    this window. Changes are kept only on Save; Cancel or closing discards them.
    """

    def __init__(
        self,
        parent: tk.Misc,
        student_store: StudentStore,
        template_choices: list[TemplateChoice],
        student: Student | None,
        on_saved: Callable[[], None],
    ) -> None:
        """
        Initialize the student editor.

        Args:
            parent: Window the dialog belongs to
            student_store: Where the student is saved
            template_choices: The Data Sheet Templates the student can use
            student: The student to edit, or None to add a new one
            on_saved: Called after the student is saved
        """
        self._parent = parent
        self._student_store = student_store
        self._original: Student | None = student
        self._on_saved = on_saved
        self._key_editor = StudentKeyFieldEditor()
        self._field_editors: list[StudentFieldEditor] = [
            self._key_editor,
            CurrentTemplateFieldEditor(template_choices),
        ]
        self._window = tk.Toplevel(parent)

        self._setup_window()
        self._create_widgets()

    def _setup_window(self) -> None:
        """Configure the dialog and make it modal."""
        if self._original is None:
            self._window.title("Add Student")
        else:
            self._window.title(f"Edit Student: {self._original.student_key}")
        self._window.resizable(True, False)
        self._window.protocol("WM_DELETE_WINDOW", self._window.destroy)
        self._window.transient(self._parent)
        self._window.wait_visibility()
        self._window.grab_set()

    def _create_widgets(self) -> None:
        """Create the form from the field editors, and the buttons."""
        main_frame = ttk.Frame(self._window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X)
        form_frame.columnconfigure(1, weight=1)

        student = self._original or Student(student_key="")
        for row, editor in enumerate(self._field_editors):
            editor.build(form_frame, row)
            editor.load(student)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        ttk.Button(button_frame, text="Cancel", command=self._window.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Save", command=self._on_save).pack(side=tk.RIGHT, padx=(0, 10))

        self._key_editor.focus()

    def _on_save(self) -> None:
        """Build the student from the form, then save it."""
        draft = self._original or Student(student_key="")
        try:
            for editor in self._field_editors:
                draft = editor.apply(draft)
        except StudentKeyError as e:
            messagebox.showerror("Invalid Student Key", str(e), parent=self._window)
            return

        if self._original is not None and not student_keys_match(self._original.student_key, draft.student_key):
            # Report a key that's already in use before asking the SLP to confirm changing to it
            try:
                if self._student_store.get_student(draft.student_key) is not None:
                    raise DuplicateStudentKeyError(draft.student_key)
            except DuplicateStudentKeyError as e:
                messagebox.showerror("Invalid Student Key", str(e), parent=self._window)
                return
            except Exception as e:
                error_handling.throw(e, "Could not save the student")
                return
            if not self._confirm_key_change(self._original.student_key, draft.student_key):
                return

        try:
            if self._original is None:
                self._student_store.add_student(draft)
            else:
                self._student_store.update_student(self._original.student_key, draft)
        except DuplicateStudentKeyError as e:
            messagebox.showerror("Invalid Student Key", str(e), parent=self._window)
            return
        except Exception as e:
            error_handling.throw(e, "Could not save the student")
            return

        self._on_saved()
        self._window.destroy()

    def _confirm_key_change(self, old_key: str, new_key: str) -> bool:
        """Warn that the student's identifying key is changing, and return whether to go ahead."""
        return messagebox.askyesno(
            "Change Student Key",
            f'The Student Key is the student\'s identifying key in the system. '
            f'Change it from "{old_key}" to "{new_key}"?\n\n'
            f'New data sheets for this student must use the new key "{new_key}".',
            parent=self._window,
        )
