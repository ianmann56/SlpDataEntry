"""
The Formula Legend: shown beside a formula while it is typed, listing every operation
with its parameters and every variable name in scope for that calculation.

Clicking an entry inserts it into the formula. The legend decides nothing itself: its
operations come from `formula.OPERATIONS` and its variables from the Analysis Scope.
"""

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from interpretation.analysis.formula import OPERATIONS
from interpretation.analysis.scope import AnalysisScope


class FormulaLegend:
    """A tree of Operations and Variables in scope. Clicking a leaf inserts it into the formula."""

    def __init__(self, parent: tk.Misc, on_insert: Callable[[str, list[tuple[int, int]]], None]) -> None:
        """
        Build the legend inside `parent`. The caller places `frame`.

        Args:
            parent: Widget the legend is built in
            on_insert: Called with the text to insert and the (start, end) of each
                placeholder in it
        """
        self._on_insert = on_insert
        # The text each insertable row inserts, by row id
        self._inserts: dict[str, tuple[str, list[tuple[int, int]]]] = {}

        self.frame: ttk.LabelFrame = ttk.LabelFrame(parent, text="Formula Legend", padding="5")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
        ttk.Label(self.frame, text="Click an entry to insert it at the cursor.").grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        self._tree = ttk.Treeview(self.frame, columns=("meaning",), show="tree headings", height=14,
                                  selectmode=tk.BROWSE)
        self._tree.heading("#0", text="Entry")
        self._tree.heading("meaning", text="Meaning")
        self._tree.column("#0", width=280, minwidth=160)
        self._tree.column("meaning", width=260, minwidth=120)
        self._tree.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self._tree.yview)
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.bind("<ButtonRelease-1>", self._on_click)
        self._tree.bind("<Return>", self._on_return)

    def show(self, scope: AnalysisScope, layer_number: int) -> None:
        """Show the operations, and the variables in scope for a calculation in this layer."""
        self._tree.delete(*self._tree.get_children())
        self._inserts.clear()

        operations = self._tree.insert("", tk.END, text="Operations", open=True)
        for operation in OPERATIONS:
            self._leaf(operations, operation.label, operation.description,
                       operation.insert_text, operation.placeholder_spans)

        variables = self._tree.insert("", tk.END, text="Variables in scope", open=True)
        for table in scope.tables:
            node = self._tree.insert(variables, tk.END, text=f"Table: {table.section}", open=True,
                                     values=("Use inside SUM or AVERAGE",))
            for entry in table.number_columns:
                self._leaf(node, entry.reference, "Number column", entry.reference)
            for column, entries in table.tally_columns:
                tally = self._tree.insert(node, tk.END, text=column, open=True, values=("Tally column",))
                for entry in entries:
                    part = entry.label.split(" › ")[-1]
                    meaning = "Tally total" if entry.reference.endswith("/Total]") else f'Count of "{part}"'
                    self._leaf(tally, entry.reference, meaning, entry.reference)
            for _, choices, entry in table.choice_columns:
                self._leaf(node, entry.reference, "Choice column, for COUNT: " + ", ".join(choices), entry.reference)

        if scope.sheet_values:
            values = self._tree.insert(variables, tk.END, text="Sheet values", open=True,
                                       values=("Single numbers on the sheet",))
            for entry in scope.sheet_values:
                self._leaf(values, entry.reference, entry.label, entry.reference)

        results = self._tree.insert(variables, tk.END, text="Lower layers", open=True,
                                    values=("Results of earlier calculations",))
        if scope.results:
            for entry in scope.results:
                self._leaf(results, entry.reference, entry.description, entry.reference)
        else:
            self._tree.insert(results, tk.END, text=f"(none in layer {layer_number})")

    def _leaf(self, parent: str, text: str, meaning: str, insert_text: str,
              spans: list[tuple[int, int]] | None = None) -> None:
        row = self._tree.insert(parent, tk.END, text=text, values=(meaning,))
        self._inserts[row] = (insert_text, list(spans or []))

    def _insert_row(self, row: str) -> None:
        if row in self._inserts:
            text, spans = self._inserts[row]
            self._on_insert(text, spans)

    def _on_click(self, event: tk.Event) -> None:
        row = self._tree.identify_row(event.y)
        if row:
            self._insert_row(row)

    def _on_return(self, event: tk.Event | None = None) -> None:
        selection = self._tree.selection()
        if selection:
            self._insert_row(selection[0])
