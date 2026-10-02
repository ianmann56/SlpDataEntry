import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from interpretation.template_manager.interpreter_configs import InterpreterConfig
from interpretation.template_manager.template_form import TemplateForm
from interpretation.template_manager.template_rules import TemplateDraft
from interpretation.template_store import TemplateStore
from tk_utils import error_handling
from tk_utils.scrollable import create_scrollable_frame


class TemplateCreatorWindow:
    """
    TKinter window for creating new Student Data Sheet Templates.

    The template's fields are a TemplateForm, shared with the Template Details window,
    filled from an empty draft. This window adds what only creating needs: saving the
    draft as a new template, and asking before throwing away what was entered.
    """

    def __init__(
        self,
        parent: tk.Misc,
        template_store: TemplateStore,
        save_callback: Callable[[], None],
        interpreter_configs: list[InterpreterConfig],
    ) -> None:
        """
        Initialize the template creator window.

        Args:
            parent: Parent tkinter window
            template_store: TemplateStore for persistence operations
            save_callback: Called after the template is created, so the parent can refresh
            interpreter_configs: The interpreter types the SLP can add
        """
        self.parent: tk.Misc = parent
        self.template_store: TemplateStore = template_store
        self.save_callback: Callable[[], None] = save_callback
        self.interpreter_configs: list[InterpreterConfig] = interpreter_configs
        self.window: tk.Toplevel = tk.Toplevel(parent)

        self._setup_window()
        self._create_widgets()

    def _setup_window(self) -> None:
        """Make the window modal over its parent, and centre it."""
        width, height = 640, 620
        self.window.title("Create New Template")
        self.window.geometry(f"{width}x{height}")
        self.window.resizable(True, True)
        self.window.transient(self.parent)
        self.window.wait_visibility()
        self.window.grab_set()
        self.window.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (width // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _create_widgets(self) -> None:
        """Create the title, the shared template form, and the buttons."""
        top_frame = ttk.Frame(self.window)
        top_frame.pack(fill=tk.BOTH, expand=True)

        button_frame = ttk.Frame(top_frame, padding=(20, 10))
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Create Template", command=self._on_create).pack(side=tk.RIGHT)

        content = create_scrollable_frame(top_frame)
        content.columnconfigure(0, weight=1)

        title_label = ttk.Label(content, text="Create New Template", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))

        self._form = TemplateForm(content, TemplateDraft.new(), self.interpreter_configs)
        self._form.frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self._form.focus()

    def _on_create(self) -> None:
        """Save the draft as a new template."""
        if not self._form.commit():
            return
        draft = self._form.draft

        problems = draft.problems()
        if problems:
            messagebox.showerror("Validation Error", "\n".join(problems), parent=self.window)
            return

        try:
            new_template = self.template_store.create_template(draft.to_create_dto())
        except Exception as e:
            error_handling.throw(e, "Failed to create template")
            return

        messagebox.showinfo("Success", f"Template '{new_template.name}' created successfully!", parent=self.window)
        self.save_callback()
        self.window.destroy()

    def _on_cancel(self) -> None:
        """Close the window, asking first if anything has been entered."""
        has_changes = self._form.has_unapplied_changes()
        if not has_changes:
            self._form.commit()
            has_changes = self._form.draft.has_changes_from(None)

        if has_changes and not messagebox.askyesno(
            "Confirm Cancel", "You have unsaved changes. Are you sure you want to cancel?", parent=self.window
        ):
            return
        self.window.destroy()
