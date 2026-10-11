"""
The Option List Editor: a list of choices or tally marks, each with what it means.

It is used for Choice columns and fields, Tally columns, and Running Tally sections. It
holds no rules of its own: adding or changing an option asks `option_rules`, and only
shows its message (layers rule 5).
"""

import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import messagebox, ttk

from interpretation.template_manager.option_rules import check_new_option
from interpretation.value_types import ColumnType


class OptionListEditor:
    """A Code | Meaning list, with entries and Add, Update, Remove, Up, and Down buttons."""

    def __init__(
        self,
        parent: tk.Misc,
        mode: ColumnType,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        """
        Build the editor inside `parent`. The caller places `frame`.

        Args:
            parent: Widget the editor is built in
            mode: CHOICE or TALLY, which decides the rules and the code column's heading
            on_change: Called after the SLP changes the list
        """
        self._mode = mode
        self._on_change = on_change
        self._options: list[tuple[str, str]] = []

        self.frame: ttk.Frame = ttk.Frame(parent)
        self.frame.columnconfigure(1, weight=1)

        self._tree = ttk.Treeview(self.frame, columns=("code", "meaning"), show="headings", height=4,
                                  selectmode=tk.BROWSE)
        self._tree.column("code", width=70, minwidth=50, stretch=False)
        self._tree.column("meaning", width=220, minwidth=100)
        self._tree.heading("meaning", text="Meaning")
        self._tree.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        self._code_var = tk.StringVar()
        self._meaning_var = tk.StringVar()
        self._code_entry = ttk.Entry(self.frame, textvariable=self._code_var, width=8)
        self._code_entry.grid(row=1, column=0, sticky=tk.W, pady=(5, 0), padx=(0, 5))
        self._meaning_entry = ttk.Entry(self.frame, textvariable=self._meaning_var)
        self._meaning_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(5, 0))

        buttons = ttk.Frame(self.frame)
        buttons.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        self._buttons: list[ttk.Button] = [
            ttk.Button(buttons, text="Add", command=self._on_add),
            ttk.Button(buttons, text="Update", command=self._on_update),
            ttk.Button(buttons, text="Remove", command=self._on_remove),
            ttk.Button(buttons, text="Up", command=lambda: self._on_move(-1)),
            ttk.Button(buttons, text="Down", command=lambda: self._on_move(1)),
        ]
        for button in self._buttons:
            button.pack(side=tk.LEFT, padx=(0, 5))

        self.set_mode(mode)

    # ----- Public operations -----

    def get(self) -> list[tuple[str, str]]:
        """The options as (choice value or tally mark, meaning), in order."""
        return list(self._options)

    def set(self, options: Sequence[tuple[str, str]]) -> None:
        """Show these options, replacing the list and clearing the entries."""
        self._options = [(code, meaning) for code, meaning in options]
        self._code_var.set("")
        self._meaning_var.set("")
        self._render(None)

    def set_mode(self, mode: ColumnType) -> None:
        """Switch between choices (CHOICE) and tally marks (TALLY)."""
        self._mode = mode
        self._tree.heading("code", text="Mark" if mode is ColumnType.TALLY else "Choice")

    def set_read_only(self, read_only: bool) -> None:
        """Switch between only showing the options and letting the SLP change them."""
        state = "disabled" if read_only else "!disabled"
        for widget in (self._code_entry, self._meaning_entry, *self._buttons):
            widget.state([state])

    # ----- Events -----

    def _selected_index(self) -> int | None:
        selection = self._tree.selection()
        return int(selection[0]) if selection else None

    def _on_select(self, event: tk.Event | None = None) -> None:
        """Fill the entries from the selected option, so it can be changed."""
        index = self._selected_index()
        if index is None:
            return
        code, meaning = self._options[index]
        self._code_var.set(code)
        self._meaning_var.set(meaning)

    def _warn(self, message: str) -> None:
        messagebox.showwarning("Check the Option", message, parent=self.frame.winfo_toplevel())

    def _on_add(self) -> None:
        code = self._code_var.get()
        problem = check_new_option(self._mode, code, [existing for existing, _ in self._options])
        if problem is not None:
            self._warn(problem)
            return
        self._options.append((code.strip(), self._meaning_var.get().strip()))
        self._code_var.set("")
        self._meaning_var.set("")
        self._changed(None)
        self._code_entry.focus_set()

    def _on_update(self) -> None:
        index = self._selected_index()
        if index is None:
            self._warn("Select an option to update first.")
            return
        code = self._code_var.get()
        others = [existing for i, (existing, _) in enumerate(self._options) if i != index]
        problem = check_new_option(self._mode, code, others)
        if problem is not None:
            self._warn(problem)
            return
        self._options[index] = (code.strip(), self._meaning_var.get().strip())
        self._changed(index)

    def _on_remove(self) -> None:
        index = self._selected_index()
        if index is None:
            self._warn("Select an option to remove first.")
            return
        del self._options[index]
        self._code_var.set("")
        self._meaning_var.set("")
        self._changed(None)

    def _on_move(self, offset: int) -> None:
        index = self._selected_index()
        if index is None:
            return
        target = index + offset
        if target < 0 or target >= len(self._options):
            return
        self._options[index], self._options[target] = self._options[target], self._options[index]
        self._changed(target)

    # ----- Helpers -----

    def _changed(self, select_index: int | None) -> None:
        self._render(select_index)
        if self._on_change is not None:
            self._on_change()

    def _render(self, select_index: int | None) -> None:
        self._tree.delete(*self._tree.get_children())
        for index, (code, meaning) in enumerate(self._options):
            self._tree.insert("", tk.END, iid=str(index), values=(code, meaning))
        if select_index is not None and self._tree.exists(str(select_index)):
            self._tree.selection_set(str(select_index))
            self._tree.see(str(select_index))
