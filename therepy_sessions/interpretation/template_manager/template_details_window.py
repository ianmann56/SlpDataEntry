import tkinter as tk
from collections.abc import Callable
from enum import Enum
from tkinter import messagebox, ttk

from interpretation.template_manager.interpreter_configs import InterpreterConfig
from interpretation.template_manager.student_data_sheet_template import StudentDataSheetTemplate
from interpretation.template_manager.template_form import LABEL_WIDTH, TemplateForm
from interpretation.template_manager.template_rules import TemplateDraft, TemplateUsage, save_confirmation
from interpretation.template_store import TemplateStore, UnreadableTemplatesError
from tk_utils import error_handling
from tk_utils.scrollable import create_scrollable_frame


class DetailsMode(Enum):
    """Whether the Template Details window is showing a template or editing it."""

    VIEW = "view"
    EDIT = "edit"


class TemplateDetailsWindow:
    """
    Window showing one saved Data Sheet Template, in view mode (read-only) or edit mode.

    The template's fields are a TemplateForm, shared with the Create window. This window
    adds what only an existing template has: its ID, which students use it, switching
    between modes, and saving changes over the saved template.
    """

    def __init__(
        self,
        parent: tk.Misc,
        template: StudentDataSheetTemplate,
        template_store: TemplateStore,
        interpreter_configs: list[InterpreterConfig],
        load_template_usage: Callable[[], TemplateUsage | None],
        on_saved: Callable[[], None],
        start_mode: DetailsMode = DetailsMode.VIEW,
    ) -> None:
        """
        Initialize the Template Details window.

        Args:
            parent: Window the details window is opened over
            template: The saved template to show
            template_store: Where the template is saved
            interpreter_configs: The interpreter types edit mode offers
            load_template_usage: Returns which students use each template, or None if unknown
            on_saved: Called after the template is saved, so the list can refresh
            start_mode: The mode the window opens in
        """
        self._parent = parent
        self._saved = template
        self._template_store = template_store
        self._configs = interpreter_configs
        self._load_template_usage = load_template_usage
        self._on_saved = on_saved
        self._mode = DetailsMode.VIEW

        self.window: tk.Toplevel = tk.Toplevel(parent)
        self._setup_window()
        self._create_widgets()
        self._set_mode(start_mode)

    def _setup_window(self) -> None:
        """Make the window modal over its parent, and centre it."""
        width, height = 640, 680
        self.window.geometry(f"{width}x{height}")
        self.window.resizable(True, True)
        self.window.transient(self._parent)
        self.window.wait_visibility()
        self.window.grab_set()
        self.window.update_idletasks()
        x = self._parent.winfo_x() + (self._parent.winfo_width() // 2) - (width // 2)
        y = self._parent.winfo_y() + (self._parent.winfo_height() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self) -> None:
        """Create the ID row, the shared template form, the usage row, and the buttons."""
        top_frame = ttk.Frame(self.window)
        top_frame.pack(fill=tk.BOTH, expand=True)

        self._button_frame = ttk.Frame(top_frame, padding=(20, 10))
        self._button_frame.pack(side=tk.BOTTOM, fill=tk.X)

        content = create_scrollable_frame(top_frame)
        content.columnconfigure(0, weight=1)

        id_row = ttk.Frame(content)
        id_row.grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Label(id_row, text="ID:", width=LABEL_WIDTH).pack(side=tk.LEFT, pady=5)
        self._id_label = ttk.Label(id_row, text=self._saved.id)
        self._id_label.pack(side=tk.LEFT, pady=5)

        self._form = TemplateForm(content, TemplateDraft.from_template(self._saved), self._configs, read_only=True)
        self._form.frame.grid(row=1, column=0, sticky=(tk.W, tk.E))

        usage_row = ttk.Frame(content)
        usage_row.grid(row=2, column=0, sticky=(tk.W, tk.E))
        ttk.Label(usage_row, text="Used by:", width=LABEL_WIDTH).pack(side=tk.LEFT, anchor=tk.N, pady=5)
        self._usage_label = ttk.Label(usage_row, text="", wraplength=440, justify=tk.LEFT)
        self._usage_label.pack(side=tk.LEFT, anchor=tk.N, pady=5)

    # ----- Modes -----

    def _set_mode(self, mode: DetailsMode) -> None:
        """Show the saved template in view mode, or start editing a fresh draft of it."""
        self._mode = mode
        self._form.set_draft(TemplateDraft.from_template(self._saved))
        self._form.set_read_only(mode is DetailsMode.VIEW)
        self.window.title(f"{'Edit Template' if mode is DetailsMode.EDIT else 'Template'}: {self._saved.name}")
        self._render_usage()
        self._render_buttons()
        if mode is DetailsMode.EDIT:
            self._form.focus()

    def _render_usage(self) -> None:
        """Show which students use the template, by Student Key."""
        usage = self._load_template_usage()
        if usage is None:
            text = "Could not determine which students use this template."
        else:
            student_keys = usage.keys_for(self._saved.id)
            text = ", ".join(student_keys) if student_keys else "No students use this template."
        self._usage_label.configure(text=text)

    def _render_buttons(self) -> None:
        """Show Edit and Close in view mode, and Save and Cancel in edit mode."""
        for child in self._button_frame.winfo_children():
            child.destroy()
        if self._mode is DetailsMode.EDIT:
            ttk.Button(self._button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT, padx=(10, 0))
            ttk.Button(self._button_frame, text="Save", command=self._on_save).pack(side=tk.RIGHT)
        else:
            ttk.Button(self._button_frame, text="Close", command=self._on_close).pack(side=tk.RIGHT, padx=(10, 0))
            ttk.Button(self._button_frame, text="Edit", command=lambda: self._set_mode(DetailsMode.EDIT)).pack(side=tk.RIGHT)

    # ----- Save, cancel, close -----

    def _has_unsaved_changes(self) -> bool:
        """Return whether edit mode holds changes that Save has not written."""
        if self._mode is not DetailsMode.EDIT:
            return False
        if self._form.has_unapplied_changes():
            return True
        self._form.commit()
        return self._form.draft.has_changes_from(self._saved)

    def _on_save(self) -> None:
        """Save the draft over the saved template, confirming first when students use it."""
        if not self._form.commit():
            return
        draft = self._form.draft

        problems = draft.problems()
        if problems:
            messagebox.showerror("Validation Error", "\n".join(problems), parent=self.window)
            return

        confirmation = save_confirmation(draft.name.strip(), self._saved.id, self._load_template_usage())
        if confirmation is not None and not messagebox.askyesno("Confirm Save", confirmation, parent=self.window):
            return

        try:
            updated = self._template_store.edit_template(self._saved.id, draft.to_edit_dto())
        except (OSError, UnreadableTemplatesError) as e:
            error_handling.throw(e, "The change was not saved")
            return

        if updated is None:
            messagebox.showerror("Not Found", "This template no longer exists.", parent=self.window)
            self._on_saved()
            self.window.destroy()
            return

        self._saved = updated
        self._on_saved()
        self._set_mode(DetailsMode.VIEW)

    def _confirm_discard(self) -> bool:
        """Return whether edit mode may be left, asking first when it holds unsaved changes."""
        if not self._has_unsaved_changes():
            return True
        return messagebox.askyesno("Discard Changes", "Discard your changes to this template?", parent=self.window)

    def _on_cancel(self) -> None:
        """Leave edit mode, discarding the draft after confirming any changes."""
        if self._confirm_discard():
            self._set_mode(DetailsMode.VIEW)

    def _on_close(self) -> None:
        """Close the window, confirming first if edit mode holds changes."""
        if self._mode is DetailsMode.EDIT and not self._confirm_discard():
            return
        self.window.destroy()
