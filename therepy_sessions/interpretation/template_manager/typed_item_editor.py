"""
The Typed Item Editor: the list of a section's columns or fields, each with a type, and
the selected one's name, type, and options.

It holds no rules of its own: the interpreter built from it reports problems through
`config_problems()`, which the template form shows when it is applied (layers rule 5).
"""

import tkinter as tk
from collections.abc import Sequence
from tkinter import messagebox, ttk
from typing import NamedTuple

from interpretation.template_manager.option_list_editor import OptionListEditor
from interpretation.value_types import COLUMN_TYPE_LABELS, ColumnType, has_options


class TypedItem(NamedTuple):
    """
    One column or field as the editor holds it.

    Properties:
      name: The column or field name.
      item_type: Its type.
      options: Its choices or tally marks as (value, meaning). Empty unless the type has options.
    """
    name: str
    item_type: ColumnType
    options: list[tuple[str, str]]


class TypedItemEditor:
    """A Name | Type list with Add, Remove, Up, and Down, and the selected item's details below."""

    def __init__(self, parent: tk.Misc, item_label: str, allowed_types: Sequence[ColumnType]) -> None:
        """
        Build the editor inside `parent`. The caller places `frame`.

        Args:
            parent: Widget the editor is built in
            item_label: What an item is called, e.g. "Column" or "Field"
            allowed_types: The types an item may have, in picker order. Text should come first.
        """
        self._item_label = item_label
        self._allowed_types: list[ColumnType] = list(allowed_types)
        self._items: list[TypedItem] = []
        self._selected: int | None = None
        # Set while the detail widgets are filled from code, so their callbacks don't edit items
        self._filling = False

        self.frame: ttk.Frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)

        self._tree = ttk.Treeview(self.frame, columns=("name", "type"), show="headings", height=5,
                                  selectmode=tk.BROWSE)
        self._tree.heading("name", text="Name")
        self._tree.heading("type", text="Type")
        self._tree.column("name", width=200, minwidth=100)
        self._tree.column("type", width=100, minwidth=80, stretch=False)
        self._tree.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        list_buttons = ttk.Frame(self.frame)
        list_buttons.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Button(list_buttons, text=f"Add {item_label}", command=self._on_add).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(list_buttons, text="Remove", command=self._on_remove).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(list_buttons, text="Up", command=lambda: self._on_move(-1)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(list_buttons, text="Down", command=lambda: self._on_move(1)).pack(side=tk.LEFT)

        self._detail = ttk.LabelFrame(self.frame, text=f"Selected {item_label}", padding="5")
        self._detail.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        self._detail.columnconfigure(1, weight=1)

        ttk.Label(self._detail, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self._name_var = tk.StringVar()
        self._name_entry = ttk.Entry(self._detail, textvariable=self._name_var)
        self._name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self._name_var.trace_add("write", self._on_name_changed)

        ttk.Label(self._detail, text="Type:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self._type_var = tk.StringVar()
        self._type_picker = ttk.Combobox(self._detail, textvariable=self._type_var, state="readonly", width=14)
        self._type_picker.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        self._type_picker.bind("<<ComboboxSelected>>", self._on_type_changed)

        self._options_label = ttk.Label(self._detail, text="Options:")
        self._options_editor = OptionListEditor(self._detail, ColumnType.CHOICE, on_change=self._on_options_changed)

        self.set_allowed_types(self._allowed_types)
        self._show_detail()

    # ----- Public operations -----

    def get(self) -> list[TypedItem]:
        """Every item, in order."""
        return [TypedItem(item.name, item.item_type, list(item.options)) for item in self._items]

    def set(self, items: Sequence[TypedItem]) -> None:
        """Show these items, with none selected."""
        self._items = [TypedItem(item.name, item.item_type, list(item.options)) for item in items]
        self._selected = None
        self._render()
        self._show_detail()

    def reset(self) -> None:
        """Remove every item."""
        self.set([])

    def set_allowed_types(self, types: Sequence[ColumnType]) -> None:
        """Limit the type picker to these types, in this order."""
        self._allowed_types = list(types)
        self._type_picker.configure(values=[COLUMN_TYPE_LABELS[t] for t in self._allowed_types])

    # ----- List events -----

    def _on_select(self, event: tk.Event | None = None) -> None:
        selection = self._tree.selection()
        index = int(selection[0]) if selection else None
        if index == self._selected:
            return
        self._selected = index
        self._show_detail()

    def _on_add(self) -> None:
        default_type = self._allowed_types[0] if self._allowed_types else ColumnType.TEXT
        self._items.append(TypedItem(self._new_name(), default_type, []))
        self._selected = len(self._items) - 1
        self._render()
        self._show_detail()
        self._name_entry.focus_set()
        self._name_entry.select_range(0, tk.END)

    def _on_remove(self) -> None:
        if self._selected is None:
            messagebox.showwarning("No Selection", f"Select a {self._item_label.lower()} to remove first.",
                                   parent=self.frame.winfo_toplevel())
            return
        del self._items[self._selected]
        self._selected = None
        self._render()
        self._show_detail()

    def _on_move(self, offset: int) -> None:
        if self._selected is None:
            return
        target = self._selected + offset
        if target < 0 or target >= len(self._items):
            return
        self._items[self._selected], self._items[target] = self._items[target], self._items[self._selected]
        self._selected = target
        self._render()

    # ----- Detail events -----

    def _on_name_changed(self, *args: object) -> None:
        if self._filling or self._selected is None:
            return
        self._items[self._selected] = self._items[self._selected]._replace(name=self._name_var.get())
        self._render()

    def _on_type_changed(self, event: tk.Event | None = None) -> None:
        if self._filling or self._selected is None:
            return
        item = self._items[self._selected]
        new_type = next((t for t in self._allowed_types if COLUMN_TYPE_LABELS[t] == self._type_var.get()), item.item_type)
        if new_type is item.item_type:
            return
        options = item.options
        if not has_options(new_type) and options:
            discard = messagebox.askyesno(
                "Discard Options",
                f'Changing "{item.name}" to {COLUMN_TYPE_LABELS[new_type]} discards its {len(options)} '
                f'option{"s" if len(options) != 1 else ""}. Change it anyway?',
                parent=self.frame.winfo_toplevel(),
            )
            if not discard:
                self._type_var.set(COLUMN_TYPE_LABELS[item.item_type])
                return
            options = []
        self._items[self._selected] = item._replace(item_type=new_type, options=options)
        self._render()
        self._show_detail()

    def _on_options_changed(self) -> None:
        if self._filling or self._selected is None:
            return
        self._items[self._selected] = self._items[self._selected]._replace(options=self._options_editor.get())

    # ----- Helpers -----

    def _new_name(self) -> str:
        """A name no item uses yet, e.g. "Column 3", so a new item is never blank."""
        used = {item.name.strip().casefold() for item in self._items}
        n = len(self._items) + 1
        while f"{self._item_label} {n}".casefold() in used:
            n += 1
        return f"{self._item_label} {n}"

    def _render(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for index, item in enumerate(self._items):
            self._tree.insert("", tk.END, iid=str(index), values=(item.name, COLUMN_TYPE_LABELS[item.item_type]))
        if self._selected is not None and self._tree.exists(str(self._selected)):
            self._tree.selection_set(str(self._selected))
            self._tree.see(str(self._selected))
        else:
            self._tree.selection_set(())

    def _show_detail(self) -> None:
        """Fill the detail widgets from the selected item, or empty and disable them."""
        self._filling = True
        try:
            if self._selected is None:
                self._name_var.set("")
                self._type_var.set("")
                self._name_entry.state(["disabled"])
                self._type_picker.state(["disabled"])
                self._options_label.grid_remove()
                self._options_editor.frame.grid_remove()
                return

            item = self._items[self._selected]
            self._name_entry.state(["!disabled"])
            self._type_picker.state(["!disabled", "readonly"])
            self._name_var.set(item.name)
            self._type_var.set(COLUMN_TYPE_LABELS[item.item_type])
            if has_options(item.item_type):
                self._options_editor.set_mode(item.item_type)
                self._options_editor.set(item.options)
                self._options_label.grid(row=2, column=0, sticky=(tk.W, tk.N), padx=(0, 5), pady=(5, 0))
                self._options_editor.frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(5, 0))
            else:
                self._options_label.grid_remove()
                self._options_editor.frame.grid_remove()
        finally:
            self._filling = False
