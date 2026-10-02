import tkinter as tk
import uuid
from tkinter import messagebox, ttk
from typing import Any

from interpretation.template_manager.interpreter_configs import ConfigForm, InterpreterConfig, find_config
from interpretation.template_manager.storage.serialization import serialize
from interpretation.template_manager.template_rules import DESCRIPTION_HINT, TemplateDraft, TitleConflictError
from interpretation.templates.student_data_sheet_interpreter import SessionDataSectionInterpreterBase

# Width of the field labels, so windows that add their own rows can line them up with the form's
LABEL_WIDTH: int = 13


class TemplateForm:
    """
    The fields of one Data Sheet Template, shared by the Create and Template Details windows.

    It shows a TemplateDraft and lets the SLP change it: the name, the description, and
    the interpreters (each changed in its type's configuration form). It never saves
    anything, and knows nothing about students. The window that holds it decides when
    and how the draft is saved.

    Call `commit()` before reading the draft, so the name, the description, and any
    unapplied interpreter form changes are in it.
    """

    def __init__(
        self,
        parent: tk.Misc,
        draft: TemplateDraft,
        interpreter_configs: list[InterpreterConfig],
        read_only: bool = False,
    ) -> None:
        """
        Build the form inside `parent`. The caller places `frame`.

        Args:
            parent: Widget the form is built in
            draft: The template values to show and change
            interpreter_configs: The interpreter types the SLP can add
            read_only: Whether the form only shows the draft
        """
        self._configs = interpreter_configs
        self._draft = draft
        self._read_only = read_only
        self._selected_index: int | None = None
        # The config whose form is open, and the interpreter it edits (None when adding one)
        self._form: tuple[InterpreterConfig, int | None] | None = None
        self._form_baseline: dict[str, Any] | None = None

        self.frame: ttk.Frame = ttk.Frame(parent)
        self._name_var = tk.StringVar()
        self._create_widgets()
        self.set_draft(draft)
        self.set_read_only(read_only)

    @property
    def draft(self) -> TemplateDraft:
        """The draft the form shows and changes."""
        return self._draft

    # ----- Public operations -----

    def set_draft(self, draft: TemplateDraft) -> None:
        """Show a different draft, discarding anything unapplied in the interpreter form."""
        self._draft = draft
        self._selected_index = None
        self._close_form()
        self._name_var.set(draft.name)
        state = str(self._description_text.cget("state"))
        self._description_text.configure(state=tk.NORMAL)
        self._description_text.delete("1.0", tk.END)
        self._description_text.insert("1.0", draft.description)
        self._description_text.configure(state=state)
        self._render_tree()

    def set_read_only(self, read_only: bool) -> None:
        """Switch between only showing the draft and letting the SLP change it."""
        self._read_only = read_only
        if read_only:
            self._close_form()
            self._selected_index = None
            self._render_tree()
            self._name_entry.configure(state="readonly")
            self._description_text.configure(state=tk.DISABLED)
            self._description_hint.grid_remove()
            self._edit_controls.grid_remove()
            self._form_panel.grid_remove()
        else:
            self._name_entry.configure(state=tk.NORMAL)
            self._description_text.configure(state=tk.NORMAL)
            self._description_hint.grid()
            self._edit_controls.grid()
            self._form_panel.grid()

    def focus(self) -> None:
        """Put the keyboard focus on the name field."""
        self._name_entry.focus_set()

    def commit(self) -> bool:
        """
        Copy the name and description into the draft, and apply any unapplied interpreter
        form changes.

        Returns:
            False if the interpreter form could not be applied, after telling the SLP why
        """
        if not self._read_only:
            self._draft.name = self._name_var.get()
            self._draft.description = self._description_text.get("1.0", tk.END).strip()
        return self._apply_pending_changes()

    def has_unapplied_changes(self) -> bool:
        """Return whether the interpreter form differs from what was loaded or emptied into it."""
        return self._form is not None and self._form_snapshot() != self._form_baseline

    # ----- Layout -----

    def _create_widgets(self) -> None:
        """Create the name, description, interpreter list, and interpreter form."""
        content = self.frame
        content.columnconfigure(1, weight=1)

        ttk.Label(content, text="Name:", width=LABEL_WIDTH).grid(row=0, column=0, sticky=tk.W, pady=5)
        self._name_entry = ttk.Entry(content, textvariable=self._name_var)
        self._name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(content, text="Description:", width=LABEL_WIDTH).grid(row=1, column=0, sticky=(tk.W, tk.N), pady=5)
        self._description_text = tk.Text(content, height=4, wrap=tk.WORD)
        self._description_text.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        self._description_hint = ttk.Label(content, text=DESCRIPTION_HINT)
        self._description_hint.grid(row=2, column=1, sticky=tk.W)

        ttk.Label(content, text="Interpreters:", width=LABEL_WIDTH).grid(row=3, column=0, sticky=(tk.W, tk.N), pady=5)
        tree_frame = ttk.Frame(content)
        tree_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
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
        self._edit_controls.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        ttk.Button(self._edit_controls, text="Up", command=lambda: self._on_move(-1)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self._edit_controls, text="Down", command=lambda: self._on_move(1)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self._edit_controls, text="Remove", command=self._on_remove).pack(side=tk.LEFT, padx=(0, 15))
        config_names = [config.name for config in self._configs]
        self._add_type_var = tk.StringVar(value=config_names[0] if config_names else "")
        ttk.Combobox(self._edit_controls, textvariable=self._add_type_var, values=config_names,
                     state="readonly", width=24).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self._edit_controls, text="Add", command=self._on_add).pack(side=tk.LEFT)

        self._form_panel = ttk.LabelFrame(content, text="Interpreter", padding="5")
        self._form_panel.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5)
        self._form_panel.columnconfigure(0, weight=1)
        self._forms: dict[str, ConfigForm] = {}
        for config in self._configs:
            self._forms[config.name] = config.create_config_form(self._form_panel)
        self._form_message = ttk.Label(self._form_panel, text="")
        form_buttons = ttk.Frame(self._form_panel)
        form_buttons.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self._apply_button = ttk.Button(form_buttons, text="Apply", command=self._apply_form)
        self._apply_button.pack(side=tk.LEFT, padx=(0, 5))
        self._form_cancel_button = ttk.Button(form_buttons, text="Cancel", command=self._on_form_cancel)
        self._form_cancel_button.pack(side=tk.LEFT)

    # ----- Interpreter list -----

    def _render_tree(self) -> None:
        """Show every interpreter, with its configuration lines as expanded child rows."""
        self._tree.delete(*self._tree.get_children())
        for index, interpreter in enumerate(self._draft.interpreters):
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

    def _on_tree_select(self, event: tk.Event | None = None) -> None:
        """Open the selected interpreter's form, applying the current form first."""
        if self._read_only:
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
        interpreter = self._draft.interpreters[new_index]
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
            messagebox.showwarning("No Selection", "Please select an interpreter first.",
                                   parent=self.frame.winfo_toplevel())
        return self._selected_index

    def _on_move(self, offset: int) -> None:
        """Move the selected interpreter up or down."""
        index = self._require_selection()
        if index is None or not self._apply_pending_changes():
            return
        new_index = self._draft.move(index, offset)
        self._selected_index = new_index
        if self._form is not None and self._form[1] == index:
            self._form = (self._form[0], new_index)
        self._render_tree()

    def _on_remove(self) -> None:
        """Remove the selected interpreter."""
        index = self._require_selection()
        if index is None:
            return
        self._draft.remove(index)
        self._selected_index = None
        self._close_form()
        self._render_tree()

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
            form["load"](self._draft.interpreters[index])
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
        interpreter_id = self._draft.interpreters[index].id if index is not None else ""
        return serialize(config.construct_interpreter(interpreter_id, self._forms[config.name]["get_config"]()))

    def _apply_form(self) -> bool:
        """
        Put the open form's values into the draft.

        Returns:
            False if the values could not be applied, after telling the SLP why
        """
        if self._form is None:
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
            messagebox.showerror("Duplicate Title", str(e), parent=self.frame.winfo_toplevel())
            return False

        self._selected_index = index
        self._form = (config, index)
        self._form_panel.configure(text="Interpreter")
        self._render_tree()
        self._form_baseline = self._form_snapshot()
        return True

    def _apply_pending_changes(self) -> bool:
        """Apply the open form if it has unapplied changes. Returns False if they could not be applied."""
        if not self.has_unapplied_changes():
            return True
        return self._apply_form()

    def _on_form_cancel(self) -> None:
        """Discard the open form's unapplied changes and put back the values from before them."""
        if self._form is None:
            return
        config, index = self._form
        self._open_form(config, index)
