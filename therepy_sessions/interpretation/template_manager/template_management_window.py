from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING
from interpretation.template_manager.template_creator_window import TemplateCreatorWindow
from interpretation.template_manager.template_details_window import DetailsMode, TemplateDetailsWindow
from interpretation.template_manager.template_rules import (
    DeleteResult,
    TemplateUsage,
    delete_confirmation,
    delete_template_and_clear_students,
)
from interpretation.template_store import UnreadableTemplatesError

if TYPE_CHECKING:
    from interpretation.template_manager.student_data_sheet_template import StudentDataSheetTemplate
    from interpretation.template_store import TemplateStore
    from interpretation.template_manager.interpreter_configs import InterpreterConfig


class DataSheetTemplateManagementWindow:
    """
    TKinter window for managing Student Data Sheet Templates.

    Provides functionality to:
    - Display a list of existing templates, with how many students use each
    - Create new templates
    - View and edit existing templates (opens the Template Details window)
    - Delete templates, clearing them from the students who use them

    It learns which students use each template only through the injected
    `load_template_usage` and `clear_template_from_students`, never from a student store.
    """

    def __init__(
        self,
        template_store: TemplateStore,
        master: tk.Misc,
        load_template_usage: Callable[[], TemplateUsage | None],
        clear_template_from_students: Callable[[str], list[str]],
        close_callback: Callable[[], None] | None = None,
        interpreter_configs: list[InterpreterConfig] | None = None,
        back_callback: Callable[[], None] | None = None,
    ) -> None:
        """
        Initialize the template management window.

        Args:
            template_store: Repository for template persistence operations
            master: Parent tkinter window
            load_template_usage: Returns which students use each template, or None if the
                student records cannot be read
            clear_template_from_students: Clears a template from every student using it,
                in one save, and returns their Student Keys
            close_callback: Optional callback function to call when window is closed
            interpreter_configs: List of InterpreterConfig objects (defaults to DEFAULT_INTERPRETER_CONFIGS)
            back_callback: Optional callback function to call when Back is pressed. When given,
                a Back button is shown to the left of Close.
        """
        self.window: tk.Misc = master

        self.template_store: TemplateStore = template_store
        self.close_callback: Callable[[], None] | None = close_callback
        self.interpreter_configs: list[InterpreterConfig] | None = interpreter_configs
        self._load_template_usage = load_template_usage
        self._clear_template_from_students = clear_template_from_students
        self._back_callback = back_callback

        self._setup_window()
        self._create_widgets()

    def _setup_window(self) -> None:
        """Configure the main window properties."""
        self.window.title("Data Sheet Template Management")
        self.window.resizable(True, True)

        # Handle window close event
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self) -> None:
        """Create and layout all the window widgets."""
        # Main container
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Configure grid weights for main_frame
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Title label
        title_label = ttk.Label(main_frame, text="Student Data Sheet Templates",
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)

        # Templates list frame
        list_frame = ttk.LabelFrame(main_frame, text="Available Templates", padding="5")
        list_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Treeview with scrollbar for template list
        treeview_frame = ttk.Frame(list_frame)
        treeview_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        treeview_frame.columnconfigure(0, weight=1)
        treeview_frame.rowconfigure(0, weight=1)

        # Create treeview for template list
        columns = ("id", "students")
        self.templates_treeview = ttk.Treeview(treeview_frame, columns=columns, show="tree headings", height=10)
        self.templates_treeview.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure column headers
        self.templates_treeview.heading("#0", text="Template")
        self.templates_treeview.heading("id", text="ID")
        self.templates_treeview.heading("students", text="Students")

        # Configure column widths
        self.templates_treeview.column("#0", width=260, minwidth=150)
        self.templates_treeview.column("id", width=80, minwidth=50)
        self.templates_treeview.column("students", width=90, minwidth=70)

        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(treeview_frame, orient=tk.VERTICAL, command=self.templates_treeview.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.templates_treeview.configure(yscrollcommand=scrollbar.set)

        # Bind double-click event
        self.templates_treeview.bind("<Double-Button-1>", self._on_template_double_click)

        # Populate treeview
        self._populate_templates_list()

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))

        # Create button
        create_button = ttk.Button(button_frame, text="Create New Template",
                                  command=self._on_create_template)
        create_button.pack(side=tk.LEFT, padx=(0, 10))

        # View button
        view_button = ttk.Button(button_frame, text="View",
                                command=lambda: self._open_details(DetailsMode.VIEW))
        view_button.pack(side=tk.LEFT, padx=(0, 10))

        # Edit button
        edit_button = ttk.Button(button_frame, text="Edit",
                                command=lambda: self._open_details(DetailsMode.EDIT))
        edit_button.pack(side=tk.LEFT, padx=(0, 10))

        # Delete button
        delete_button = ttk.Button(button_frame, text="Delete",
                                  command=self._on_delete_template)
        delete_button.pack(side=tk.LEFT, padx=(0, 10))

        # Close button
        close_button = ttk.Button(button_frame, text="Close",
                                 command=self._on_close)
        close_button.pack(side=tk.RIGHT)

        # Back button (only when the window was opened from somewhere to go back to)
        if self._back_callback is not None:
            back_button = ttk.Button(button_frame, text="Back",
                                    command=self._on_back)
            back_button.pack(side=tk.RIGHT, padx=(0, 10))

    def _populate_templates_list(self) -> None:
        """Populate the treeview with available templates and how many students use each."""
        # Clear existing items
        for item in self.templates_treeview.get_children():
            self.templates_treeview.delete(item)

        # An unreadable file would otherwise look like an empty list
        try:
            self.template_store.check_readable()
        except UnreadableTemplatesError as e:
            messagebox.showerror("Error", f"Could not read the templates file: {e}", parent=self.window)
            return

        usage = self._load_template_usage()
        templates = self.template_store.get_all_templates()
        for template in templates:
            students = str(usage.count_for(template.id)) if usage is not None else "Unknown"
            self.templates_treeview.insert("", tk.END,
                                         text=template.name,
                                         values=(template.id, students))

    def _get_selected_template_id(self) -> str | None:
        """Get the ID of the currently selected template."""
        selection = self.templates_treeview.selection()
        if not selection:
            return None
        values = self.templates_treeview.item(selection[0], "values")
        if not values:
            return None
        return str(values[0])  # ID is the first value

    def _get_selected_template(self) -> StudentDataSheetTemplate | None:
        """
        Reload the selected template from the store. Tells the SLP when nothing is selected,
        or when the template no longer exists (and refreshes the list).
        """
        template_id = self._get_selected_template_id()
        if template_id is None:
            messagebox.showwarning("No Selection", "Please select a template first.", parent=self.window)
            return None
        template = self.template_store.get_template_by_id(template_id)
        if template is None:
            messagebox.showerror("Not Found", "This template no longer exists.", parent=self.window)
            self._populate_templates_list()
        return template

    def _on_template_double_click(self, event: tk.Event) -> None:
        """Handle double-click on template list item."""
        if self.templates_treeview.identify_row(event.y):
            self._open_details(DetailsMode.VIEW)

    def _on_create_template(self) -> None:
        """Handle create new template button click."""
        # Open template creation window
        TemplateCreatorWindow(self.window, self.template_store, self._on_template_created, self.interpreter_configs or [])

    def _open_details(self, mode: DetailsMode) -> None:
        """Open the selected template's Template Details window in view or edit mode."""
        template = self._get_selected_template()
        if template is None:
            return
        TemplateDetailsWindow(
            self.window,
            template,
            self.template_store,
            self.interpreter_configs or [],
            self._load_template_usage,
            on_saved=self._populate_templates_list,
            start_mode=mode,
        )

    def _on_delete_template(self) -> None:
        """Delete the selected template after confirming, clearing it from the students who use it first."""
        template = self._get_selected_template()
        if template is None:
            return

        # Read usage now, not from the list, so the confirmation names the current students
        usage = self._load_template_usage()
        if not messagebox.askyesno("Confirm Delete", delete_confirmation(template.name, template.id, usage),
                                   parent=self.window):
            return

        try:
            outcome = delete_template_and_clear_students(
                template.id,
                usage,
                self._clear_template_from_students,
                self.template_store.delete_template,
            )
        except Exception as e:
            messagebox.showerror("Error", f"The template was not deleted: {e}", parent=self.window)
            self._populate_templates_list()
            return

        if outcome.result is DeleteResult.DELETED:
            messagebox.showinfo("Deleted", f"Template '{template.name}' has been deleted.", parent=self.window)
        elif outcome.result is DeleteResult.NOT_FOUND:
            messagebox.showerror("Not Found", "This template no longer exists.", parent=self.window)
        else:
            messagebox.showerror(
                "Error",
                f"Students {', '.join(outcome.cleared_student_keys)} no longer have a Current Template, "
                f"but the template could not be deleted: {outcome.detail}",
                parent=self.window,
            )
        self._populate_templates_list()

    def show(self) -> None:
        """Display the window and focus it."""
        self.window.focus_set()

    def _on_template_created(self) -> None:
        """Callback method called when a template is created from the editor."""
        # Refresh the template list to show any changes
        self._populate_templates_list()

    def _on_close(self) -> None:
        """Handle window close button click."""
        self.close_callback()

    def _on_back(self) -> None:
        """Handle back button click."""
        self._back_callback()
