"""
Field editors that make up the student editor's form.

Each editor owns one Student setting. A later setting is added by giving `Student` a new
field with a default, writing one editor here, and adding it to the editor window's list.
"""

import tkinter as tk
from abc import ABC, abstractmethod
from dataclasses import replace
from tkinter import ttk

from students.student import Student, TemplateChoice, validate_student_key

NONE_SELECTED_LABEL: str = "None selected"
MISSING_TEMPLATE_LABEL: str = "Missing template"


class StudentFieldEditor(ABC):
    """Edits one Student setting in the student editor's form."""

    @abstractmethod
    def build(self, parent: ttk.Frame, row: int) -> None:
        """Create this field's label and widget in `row` of the parent's grid."""

    @abstractmethod
    def load(self, student: Student) -> None:
        """Show the student's current value."""

    @abstractmethod
    def apply(self, student: Student) -> Student:
        """
        Return a copy of `student` with this field set from the widget.

        Raises:
            StudentKeyError: If the value entered is invalid
        """


class StudentKeyFieldEditor(StudentFieldEditor):
    """Edits the Student Key."""

    def __init__(self) -> None:
        self._key_var: tk.StringVar | None = None
        self._entry: ttk.Entry | None = None

    def build(self, parent: ttk.Frame, row: int) -> None:
        self._key_var = tk.StringVar(master=parent)
        ttk.Label(parent, text="Student Key").grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        self._entry = ttk.Entry(parent, textvariable=self._key_var, width=10)
        self._entry.grid(row=row, column=1, sticky="ew", pady=5)

    def load(self, student: Student) -> None:
        self._require_built().set(student.student_key)

    def apply(self, student: Student) -> Student:
        return replace(student, student_key=validate_student_key(self._require_built().get()))

    def focus(self) -> None:
        """Put the keyboard focus in the Student Key entry."""
        if self._entry is not None:
            self._entry.focus_set()

    def _require_built(self) -> tk.StringVar:
        if self._key_var is None:
            raise RuntimeError("build() must be called before load() or apply()")
        return self._key_var


class CurrentTemplateFieldEditor(StudentFieldEditor):
    """
    Chooses the Current Template from the existing Data Sheet Templates, or none.

    Options are mapped by position, not name, so templates with the same name still work.
    A template that no longer exists is offered as "Missing template" and kept unless
    the SLP picks another.
    """

    def __init__(self, template_choices: list[TemplateChoice]) -> None:
        self._template_choices = template_choices
        self._combobox: ttk.Combobox | None = None
        self._missing_template_id: str | None = None

    def build(self, parent: ttk.Frame, row: int) -> None:
        ttk.Label(parent, text="Current Template").grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        self._combobox = ttk.Combobox(parent, state="readonly", width=30)
        self._combobox.grid(row=row, column=1, sticky="ew", pady=5)

    def load(self, student: Student) -> None:
        combobox = self._require_built()
        options = [NONE_SELECTED_LABEL] + [choice.name for choice in self._template_choices]
        selected = 0
        self._missing_template_id = None
        if student.current_template_id is not None:
            for index, choice in enumerate(self._template_choices):
                if choice.template_id == student.current_template_id:
                    selected = index + 1
                    break
            else:
                self._missing_template_id = student.current_template_id
                options.append(MISSING_TEMPLATE_LABEL)
                selected = len(options) - 1
        combobox.configure(values=options)
        combobox.current(selected)

    def apply(self, student: Student) -> Student:
        index = self._require_built().current()
        if index <= 0:
            template_id = None
        elif index <= len(self._template_choices):
            template_id = self._template_choices[index - 1].template_id
        else:
            template_id = self._missing_template_id
        return replace(student, current_template_id=template_id)

    def _require_built(self) -> ttk.Combobox:
        if self._combobox is None:
            raise RuntimeError("build() must be called before load() or apply()")
        return self._combobox
