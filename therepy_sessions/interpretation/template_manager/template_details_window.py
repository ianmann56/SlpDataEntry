import tkinter as tk
import uuid
from collections.abc import Callable
from enum import Enum
from tkinter import messagebox, ttk
from typing import Any

from interpretation.template_manager.interpreter_configs import ConfigForm, InterpreterConfig, find_config
from interpretation.template_manager.storage.serialization import serialize
from interpretation.template_manager.student_data_sheet_template import StudentDataSheetTemplate
from interpretation.template_manager.template_rules import (
    DESCRIPTION_HINT,
    TemplateDraft,
    TemplateUsage,
    TitleConflictError,
    save_confirmation,
)
from interpretation.template_store import TemplateStore, UnreadableTemplatesError
from interpretation.templates.student_data_sheet_interpreter import SessionDataSectionInterpreterBase
from tk_utils import error_handling

class DetailsMode(Enum):
    """Whether the Template Details window is showing a template or editing it."""

    VIEW = "view"
    EDIT = "edit"


class TemplateDetailsWindow:
    """
    Window showing one saved Data Sheet Template, in view mode (read-only) or edit mode.

    Both modes share one layout. Edit mode changes a TemplateDraft, and only Save writes
    it. Every rule it applies comes from `template_rules`, not from widget callbacks.
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
        self._draft: TemplateDraft | None = None
        self._selected_index: int | None = None
        # The config whose form is open, and the interpreter it edits (None when adding one)
        self._form: tuple[InterpreterConfig, int | None] | None = None
        self._form_baseline: dict[str, Any] | None = None

        self.window = tk.Toplevel(parent)
        self._name_var = tk.StringVar()
        self._setup_window()
        self._create_widgets()
        self._set_mode(start_mode)

    # ----- Layout -----

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
        """Create the scrolling content and the action buttons."""
        top_frame = ttk.Frame(self.window)
        top_frame.pack(fill=tk.BOTH, expand=True)

        self._button_frame = ttk.Frame(top_frame, padding=(20, 10))
        self._button_frame.pack(side=tk.BOTTOM, fill=tk.X)

        canvas = tk.Canvas(top_frame, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(top_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        content = ttk.Frame(canvas, padding="20")
        content_id = canvas.create_window((0, 0), window=content, anchor=tk.NW)
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(content_id, width=e.width))
        content.columnconfigure(1, weight=1)

        ttk.Label(content, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self._name_entry = ttk.Entry(content, textvariable=self._name_var)
        self._name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(content, text="ID:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self._id_label = ttk.Label(content, text=self._saved.id)
        self._id_label.grid(row=1, column=1, sticky=tk.W, pady=5)

        ttk.Label(content, text="Description:").grid(row=2, column=0, sticky=(tk.W, tk.N), pady=5, padx=(0, 10))
        self._description_text = tk.Text(content, height=4, wrap=tk.WORD)
        self._description_text.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        self._description_hint = ttk.Label(content, text=DESCRIPTION_HINT)
        self._description_hint.grid(row=3, column=1, sticky=tk.W)

        ttk.Label(content, text="Interpreters:").grid(row=4, column=0, sticky=(tk.W, tk.N), pady=5, padx=(0, 10))
        tree_frame = ttk.Frame(content)
        tree_frame.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)
        tree_frame.columnconfigure(0, weight=1)
        self._tree = ttk.Treeview(tree_frame, columns=("type",), show="tree headings", height=8,
                                  selectmode=tk.BROWSE)
        self._tree.heading("#0", text="Interpreter")
        self._tree.heading("type", text="Type")
        self._tree.column("#0", width=280, minwidth=150)
        self._tree.column("type", width=180, minwidth=120)
        self._tree.grid(row=0, column=0, sticky=(tk.W, tk.E))
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview)
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self._tree.configure(yscrollcommand=tree_scrollbar.set)
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        self._edit_controls = ttk.Frame(content)
        self._edit_controls.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        ttk.Button(self._edit_controls, text="Up", command=lambda: self._on_move(-1)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self._edit_controls, text="Down", command=lambda: self._on_move(1)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self._edit_controls, text="Remove", command=self._on_remove).pack(side=tk.LEFT, padx=(0, 15))
        config_names = [config.name for config in self._configs]
        self._add_type_var = tk.StringVar(value=config_names[0] if config_names else "")
        ttk.Combobox(self._edit_controls, textvariable=self._add_type_var, values=config_names,
                     state="readonly", width=24).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self._edit_controls, text="Add", command=self._on_add).pack(side=tk.LEFT)

        self._form_panel = ttk.LabelFrame(content, text="Interpreter", padding="5")
        self._form_panel.grid(row=6, column=1, sticky=(tk.W, tk.E), pady=5)
        self._form_panel.columnconfigure(0, weight=1)
        self._forms: dict[str, ConfigForm] = {}
        for config in self._configs:
            self._forms[config.name] = config.create_config_form(self._form_panel)
        self._form_message = ttk.Label(self._form_panel, text="")
        form_buttons = ttk.Frame(self._form_panel)
        form_buttons.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self._apply_button = ttk.Button(form_buttons, text="Apply", command=self._on_apply)
        self._apply_button.pack(side=tk.LEFT, padx=(0, 5))
        self._form_cancel_button = ttk.Button(form_buttons, text="Cancel", command=self._on_form_cancel)
        self._form_cancel_button.pack(side=tk.LEFT)

        ttk.Label(content, text="Used by:").grid(row=7, column=0, sticky=(tk.W, tk.N), pady=5, padx=(0, 10))
        self._usage_label = ttk.Label(content, text="", wraplength=440, justify=tk.LEFT)
        self._usage_label.grid(row=7, column=1, sticky=tk.W, pady=5)

    # ----- Rendering -----

    def _set_mode(self, mode: DetailsMode) -> None:
        """Switch between view and edit mode, keeping the same layout."""
        self._mode = mode
        self._form = None
        self._form_baseline = None
        self._selected_index = None

        if mode is DetailsMode.EDIT:
            self._draft = TemplateDraft.from_template(self._saved)
            self._name_entry.configure(state=tk.NORMAL)
            self._description_hint.grid()
            self._edit_controls.grid()
            self._form_panel.grid()
        else:
            self._draft = None
            self._name_entry.configure(state="readonly")
            self._description_hint.grid_remove()
            self._edit_controls.grid_remove()
            self._form_panel.grid_remove()

        self.window.title(f"{'Edit Template' if mode is DetailsMode.EDIT else 'Template'}: {self._saved.name}")
        self._render_fields()
        self._render_tree()
        self._show_form(None)
        self._render_usage()
        self._render_buttons()

    def _render_fields(self) -> None:
        """Fill the name and description from the saved template."""
        self._name_var.set(self._saved.name)
        self._description_text.configure(state=tk.NORMAL)
        self._description_text.delete("1.0", tk.END)
        self._description_text.insert("1.0", self._saved.description)
        if self._mode is DetailsMode.VIEW:
            self._description_text.configure(state=tk.DISABLED)

    def _current_interpreters(self) -> list[SessionDataSectionInterpreterBase]:
        """Return the interpreters being shown: the draft's in edit mode, the saved ones otherwise."""
        return self._draft.interpreters if self._draft is not None else self._saved.interpreters

    def _render_tree(self) -> None:
        """Show every interpreter, with its configuration lines as expanded child rows."""
        self._tree.delete(*self._tree.get_children())
        for index, interpreter in enumerate(self._current_interpreters()):
            config = find_config(self._configs, interpreter)
            type_name = config.name if config is not None else type(interpreter).__name__
            parent_id = self._tree.insert("", tk.END, iid=str(index), open=True,
                                          text=interpreter.title or "(untitled)", values=(type_name,))
            for line_number, line in enumerate(self._describe(interpreter, config)):
                self._tree.insert(parent_id, tk.END, iid=f"{index}.{line_number}", text=line, values=("",))
        if self._selected_index is not None and self._tree.exists(str(self._selected_index)):
            self._tree.selection_set(str(self._selected_index))
            self._tree.see(str(self._selected_index))
        else:
            self._tree.selection_set(())

    def _describe(self, interpreter: SessionDataSectionInterpreterBase, config: InterpreterConfig | None) -> list[str]:
        """Return an interpreter's configuration lines, falling back to its saved config for types with no form."""
        if config is not None:
            return config.describe(interpreter)
        try:
            saved_config = serialize(interpreter).get("config", {})
        except ValueError:
            return ["(configuration unavailable)"]
        return [f"{key}: {value}" for key, value in saved_config.items()] or ["(none)"]

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

    # ----- Interpreter form -----

    def _show_form(self, config: InterpreterConfig | None, message: str = "") -> None:
        """Show one config's form in the panel, or a message when no form applies."""
        for form in self._forms.values():
            form["frame"].grid_remove()
        self._form_message.grid_remove()
        if config is not None:
            self._forms[config.name]["frame"].grid(row=0, column=0, sticky=(tk.W, tk.E))
        if message:
            self._form_message.configure(text=message)
            self._form_message.grid(row=1, column=0, sticky=tk.W)
        enabled = tk.NORMAL if config is not None else tk.DISABLED
        self._apply_button.configure(state=enabled)
        self._form_cancel_button.configure(state=enabled)

    def _open_form(self, config: InterpreterConfig, index: int | None) -> None:
        """Open a config's form for the interpreter at `index`, or empty for a new one."""
        form = self._forms[config.name]
        if index is None:
            form["reset"]()
            self._form_panel.configure(text=f"New {config.name}")
        else:
            form["load"](self._current_interpreters()[index])
            self._form_panel.configure(text="Interpreter")
        self._form = (config, index)
        self._form_baseline = self._form_snapshot()
        self._show_form(config)

    def _close_form(self, message: str = "") -> None:
        """Close the open form."""
        self._form = None
        self._form_baseline = None
        self._form_panel.configure(text="Interpreter")
        self._show_form(None, message)

    def _form_snapshot(self) -> dict[str, Any] | None:
        """Return the interpreter the open form would build, in saved form, for comparing."""
        if self._form is None:
            return None
        config, index = self._form
        interpreter_id = self._current_interpreters()[index].id if index is not None else ""
        return serialize(config.construct_interpreter(interpreter_id, self._forms[config.name]["get_config"]()))

    def _form_has_changes(self) -> bool:
        """Return whether the open form differs from what was loaded or emptied into it."""
        return self._form is not None and self._form_snapshot() != self._form_baseline

    def _apply_form(self) -> bool:
        """
        Put the open form's values into the draft.

        Returns:
            False if the values could not be applied, after telling the SLP why
        """
        if self._form is None or self._draft is None:
            return True
        config, index = self._form
        values = self._forms[config.name]["get_config"]()
        try:
            if index is None:
                self._draft.add(config.construct_interpreter(str(uuid.uuid4()), values))
                index = len(self._draft.interpreters) - 1
            else:
                self._draft.replace(index, config.construct_interpreter(self._draft.interpreters[index].id, values))
        except TitleConflictError as e:
            messagebox.showerror("Duplicate Title", str(e), parent=self.window)
            return False

        self._selected_index = index
        self._form = (config, index)
        self._form_panel.configure(text="Interpreter")
        self._render_tree()
        self._form_baseline = self._form_snapshot()
        return True

    def _apply_pending_changes(self) -> bool:
        """Apply the open form if it has unapplied changes. Returns False if they could not be applied."""
        if not self._form_has_changes():
            return True
        return self._apply_form()

    def _on_apply(self) -> None:
        """Handle the form's Apply button."""
        self._apply_form()

    def _on_form_cancel(self) -> None:
        """Discard the open form's unapplied changes and put back the values from before them."""
        if self._form is None:
            return
        config, index = self._form
        self._open_form(config, index)

    # ----- Edit controls -----

    def _on_tree_select(self, event: tk.Event | None = None) -> None:
        """Open the selected interpreter's form in edit mode, applying the current form first."""
        if self._mode is not DetailsMode.EDIT:
            return
        selection = self._tree.selection()
        if not selection:
            return
        new_index = int(selection[0].split(".")[0])
        # Redrawing the tree re-selects the current row; Tk delivers that selection event later
        if new_index == self._selected_index:
            return

        if not self._apply_pending_changes():
            # Put the old selection back, so the form still matches what is selected
            self._render_tree()
            return

        self._selected_index = new_index
        self._render_tree()
        interpreter = self._current_interpreters()[new_index]
        config = find_config(self._configs, interpreter)
        if config is None:
            self._close_form("This interpreter's type can't be edited here.")
        else:
            self._open_form(config, new_index)

    def _on_add(self) -> None:
        """Open an empty form for a new interpreter of the chosen type."""
        config = next((c for c in self._configs if c.name == self._add_type_var.get()), None)
        if config is None or not self._apply_pending_changes():
            return
        self._selected_index = None
        self._render_tree()
        self._open_form(config, None)

    def _require_selection(self) -> int | None:
        """Return the selected interpreter's position, or tell the SLP to select one."""
        if self._selected_index is None:
            messagebox.showwarning("No Selection", "Please select an interpreter first.", parent=self.window)
        return self._selected_index

    def _on_move(self, offset: int) -> None:
        """Move the selected interpreter up or down."""
        index = self._require_selection()
        if index is None or self._draft is None or not self._apply_pending_changes():
            return
        new_index = self._draft.move(index, offset)
        self._selected_index = new_index
        if self._form is not None and self._form[1] == index:
            self._form = (self._form[0], new_index)
        self._render_tree()

    def _on_remove(self) -> None:
        """Remove the selected interpreter."""
        index = self._require_selection()
        if index is None or self._draft is None:
            return
        self._draft.remove(index)
        self._selected_index = None
        self._close_form()
        self._render_tree()

    # ----- Save, cancel, close -----

    def _sync_fields_to_draft(self) -> None:
        """Copy the name and description fields into the draft."""
        if self._draft is not None:
            self._draft.name = self._name_var.get()
            self._draft.description = self._description_text.get("1.0", tk.END).strip()

    def _has_unsaved_changes(self) -> bool:
        """Return whether edit mode holds changes that Save has not written."""
        if self._draft is None:
            return False
        self._sync_fields_to_draft()
        return self._draft.has_changes_from(self._saved) or self._form_has_changes()

    def _on_save(self) -> None:
        """Save the draft, after applying the open form and confirming when students use the template."""
        if self._draft is None or not self._apply_pending_changes():
            return
        self._sync_fields_to_draft()

        problems = self._draft.problems()
        if problems:
            messagebox.showerror("Validation Error", "\n".join(problems), parent=self.window)
            return

        confirmation = save_confirmation(self._draft.name.strip(), self._saved.id, self._load_template_usage())
        if confirmation is not None and not messagebox.askyesno("Confirm Save", confirmation, parent=self.window):
            return

        try:
            updated = self._template_store.edit_template(self._saved.id, self._draft.to_edit_dto())
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
