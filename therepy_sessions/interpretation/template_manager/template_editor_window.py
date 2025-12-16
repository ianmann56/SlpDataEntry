import tkinter as tk
from tkinter import ttk


class TemplateEditorWindow:
    """
    Stub for the template editor window.
    This will be implemented in future iterations.
    """

    def __init__(self, parent, template, title, template_store, save_callback):
        """
        Initialize the template editor window.

        Args:
            parent: Parent tkinter window
            template: StudentDataSheetTemplate to edit, or None for new template
            title: Window title
            template_store: TemplateStore for persistence operations
            save_callback: Callback function to call when template is saved
        """
        self.parent = parent
        self.template = template
        self.template_store = template_store
        self.save_callback = save_callback
        self.window = tk.Toplevel(parent)

        self._setup_window(title)
        self._create_stub_content()

    def _setup_window(self, title):
        """Configure the editor window properties."""
        self.window.title(title)
        self.window.geometry("400x300")
        self.window.resizable(True, True)

        # Center relative to parent
        self.window.transient(self.parent)
        self.window.grab_set()

        # Center the window
        self.window.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (400 // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (300 // 2)
        self.window.geometry(f"400x300+{x}+{y}")

    def _create_stub_content(self):
        """Create stub content for the editor window."""
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Stub message
        if self.template:
            message = f"Template Editor\n\nEditing: {self.template.name}\nID: {self.template.id}\n\n(Implementation coming soon)"
        else:
            message = "Template Creator\n\nCreate New Template\n\n(Implementation coming soon)"

        label = ttk.Label(main_frame, text=message, justify=tk.CENTER,
                         font=("Arial", 12))
        label.pack(expand=True)

        # Close button
        close_button = ttk.Button(main_frame, text="Close",
                                 command=self.window.destroy)
        close_button.pack(pady=10)