"""
The Analysis section of the Template Form: the template's Data Sheet Analysis as a list
of layers and their calculations, with an editor panel below it.

A calculation is built from the menu (a Row Aggregate or an Arithmetic calculation) or
typed as a formula, with the Formula Legend beside it. Every choice the panel offers
comes from the Analysis Scope, and every check from `analysis.rules`, so the widgets
decide nothing themselves (layers rule 5). The panel's changes reach the analysis only
when the SLP presses Apply, as in the interpreter panel.
"""

import tkinter as tk
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

from interpretation.analysis.model import (
    Arithmetic,
    ArithmeticOperation,
    Calculation,
    CalculationDefinition,
    ChoiceCountMeasure,
    Combination,
    DataSheetAnalysis,
    Formula,
    NumberColumnMeasure,
    NumberOperand,
    Operand,
    ResultOperand,
    RowAggregate,
    SheetValueOperand,
    TallyCountMeasure,
)
from interpretation.analysis.renames import PartKind, PartRename, apply_renames
from interpretation.analysis.rules import (
    calculation_problems,
    calculations_using,
    describe_calculation,
    describe_operand,
    formula_problems,
)
from interpretation.analysis.scope import TALLY_TOTAL_PART, AnalysisScope, ScopeTable, analysis_scope, fold
from interpretation.template_manager.formula_legend import FormulaLegend
from interpretation.template_manager.template_rules import DESCRIPTION_HINT
from interpretation.templates.student_data_sheet_interpreter import SessionDataSectionInterpreterBase

HISTORICAL_NOTE: str = "Historical analysis (across a student's sessions) is not available yet."

_ROW_AGGREGATE = "Row Aggregate"
_ARITHMETIC = "Arithmetic"
_NUMBER_COLUMN = "Number column"
_TALLY_COUNT = "Tally count"
_CHOICE_COUNT = "Choice count"
_RESULT = "Result"
_SHEET_VALUE = "Sheet value"
_NUMBER = "Number"
_MENU = "menu"
_FORMULA = "formula"

_OPERATION_LABELS: dict[ArithmeticOperation, str] = {
    ArithmeticOperation.ADD: "add (+)",
    ArithmeticOperation.SUBTRACT: "subtract (−)",
    ArithmeticOperation.MULTIPLY: "multiply (×)",
    ArithmeticOperation.DIVIDE: "divide (÷)",
    ArithmeticOperation.PERCENTAGE: "percentage (left ÷ right × 100)",
}
_COMBINATION_LABELS: dict[Combination, str] = {Combination.SUM: "Sum", Combination.AVERAGE: "Average"}


def _kind_label(calculation: Calculation) -> str:
    if isinstance(calculation.definition, RowAggregate):
        return _ROW_AGGREGATE
    if isinstance(calculation.definition, Arithmetic):
        return _ARITHMETIC
    return "Formula"


class _OperandRow:
    """One Arithmetic input: its kind (a result, a sheet value, or a number) and its value."""

    def __init__(self, parent: tk.Misc, label: str, on_change: Callable[[], None]) -> None:
        self._on_change = on_change
        # The operand behind each label in the value picker
        self._operands: dict[str, Operand] = {}
        self.frame: ttk.Frame = ttk.Frame(parent)
        ttk.Label(self.frame, text=label, width=8).pack(side=tk.LEFT)
        self.kind_var = tk.StringVar(value=_RESULT)
        self._kind_picker = ttk.Combobox(self.frame, textvariable=self.kind_var, state="readonly", width=12,
                                         values=[_RESULT, _SHEET_VALUE, _NUMBER])
        self._kind_picker.pack(side=tk.LEFT, padx=(0, 5))
        self._kind_picker.bind("<<ComboboxSelected>>", lambda e: self._kind_changed())
        self.value_var = tk.StringVar()
        self._value_picker = ttk.Combobox(self.frame, textvariable=self.value_var, state="readonly", width=34)
        self._value_picker.bind("<<ComboboxSelected>>", lambda e: on_change())
        self.number_var = tk.StringVar()
        self._number_entry = ttk.Entry(self.frame, textvariable=self.number_var, width=12)
        self.number_var.trace_add("write", lambda *a: on_change())
        self._scope: AnalysisScope | None = None

    def fill(self, scope: AnalysisScope) -> None:
        """Offer the results and sheet values in scope, keeping the current choice."""
        self._scope = scope
        current = self.operand()
        self._show_kind(current)

    def _kind_changed(self) -> None:
        self.value_var.set("")
        self._show_kind(None)
        self._on_change()

    def _show_kind(self, keep: Operand | None) -> None:
        scope = self._scope
        self._operands = {}
        if scope is not None and self.kind_var.get() == _RESULT:
            self._operands = {entry.label: ResultOperand(entry.label) for entry in scope.results}
        elif scope is not None and self.kind_var.get() == _SHEET_VALUE:
            for entry in scope.sheet_values:
                section, value = entry.label.split(" › ", 1)
                self._operands[entry.label] = SheetValueOperand(section, value)
        # A saved input that is no longer in scope stays listed, so Apply can say why
        if keep is not None and not isinstance(keep, NumberOperand):
            label = describe_operand(keep)
            if label.strip() and label.strip() != "›":
                self._operands.setdefault(label, keep)
        self._value_picker.configure(values=list(self._operands))
        if self.kind_var.get() == _NUMBER:
            self._value_picker.pack_forget()
            self._number_entry.pack(side=tk.LEFT)
        else:
            self._number_entry.pack_forget()
            self._value_picker.pack(side=tk.LEFT)

    def load(self, operand: Operand) -> None:
        """Show a saved input."""
        if isinstance(operand, NumberOperand):
            self.kind_var.set(_NUMBER)
            self.number_var.set(str(operand.number))
            self.value_var.set("")
        else:
            self.kind_var.set(_RESULT if isinstance(operand, ResultOperand) else _SHEET_VALUE)
            self.value_var.set(describe_operand(operand))
            self.number_var.set("")
        self._show_kind(operand)

    def operand(self) -> Operand:
        """The input as chosen. An incomplete choice gives an input the rules report."""
        kind = self.kind_var.get()
        if kind == _NUMBER:
            try:
                return NumberOperand(Decimal(self.number_var.get().strip()))
            except InvalidOperation:
                return NumberOperand(Decimal("NaN"))
        label = self.value_var.get()
        if label in self._operands:
            return self._operands[label]
        return ResultOperand("") if kind == _RESULT else SheetValueOperand(label, "")


class AnalysisEditor:
    """The template's layers and calculations, the buttons that change them, and the calculation panel."""

    def __init__(
        self,
        parent: tk.Misc,
        get_interpreters: Callable[[], list[SessionDataSectionInterpreterBase]],
        on_change: Callable[[DataSheetAnalysis], None],
    ) -> None:
        """
        Build the editor inside `parent`. The caller places `frame`.

        Args:
            parent: Widget the editor is built in
            get_interpreters: Returns the template's current sections, for the Analysis Scope
            on_change: Called with the analysis after every change the SLP makes to it
        """
        self._get_interpreters = get_interpreters
        self._on_change = on_change
        self._analysis = DataSheetAnalysis.empty()
        self._read_only = False
        # The selected row as (layer number, calculation index or None for the layer row)
        self._selected: tuple[int, int | None] | None = None
        # What the panel edits as (layer number, calculation index or None for a new one)
        self._open: tuple[int, int | None] | None = None
        self._baseline: Calculation | None = None
        # Set while the panel is filled from code, so its callbacks don't react
        self._filling = False
        # The Choice columns of a loaded choice count, until the column list is first filled
        self._loaded_choice_columns: list[str] | None = None

        self.frame: ttk.Frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        ttk.Label(self.frame, text="Analysis", font=("Arial", 13, "bold")).grid(row=0, column=0, sticky=tk.W)
        area = ttk.LabelFrame(self.frame, text="Data Sheet Analysis", padding="5")
        area.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        area.columnconfigure(0, weight=1)
        ttk.Label(area, text=HISTORICAL_NOTE).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        self._tree = ttk.Treeview(area, columns=("kind", "summary"), show="tree headings", height=8,
                                  selectmode=tk.BROWSE)
        self._tree.heading("#0", text="Calculation")
        self._tree.heading("kind", text="Kind")
        self._tree.heading("summary", text="Works out")
        self._tree.column("#0", width=220, minwidth=140)
        self._tree.column("kind", width=110, minwidth=90, stretch=False)
        self._tree.column("summary", width=520, minwidth=200)
        self._tree.grid(row=1, column=0, sticky=(tk.W, tk.E))
        tree_scrollbar = ttk.Scrollbar(area, orient=tk.VERTICAL, command=self._tree.yview)
        tree_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self._tree.configure(yscrollcommand=tree_scrollbar.set)
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        self._buttons = ttk.Frame(area)
        self._buttons.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        for text, command in (
            ("Add Layer", self._on_add_layer),
            ("Delete Layer", self._on_delete_layer),
            ("Add Calculation", self._on_add_calculation),
            ("Remove", self._on_remove),
            ("Up", lambda: self._on_move(-1)),
            ("Down", lambda: self._on_move(1)),
        ):
            ttk.Button(self._buttons, text=text, command=command).pack(side=tk.LEFT, padx=(0, 5))

        self._panel_row = ttk.Frame(area)
        self._panel_row.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), pady=(5, 0))
        self._panel_row.columnconfigure(0, weight=1)
        self._panel_row.columnconfigure(1, weight=1)
        self._create_panel()
        self._legend = FormulaLegend(self._panel_row, self._insert_into_formula)

        self._render()
        self._close_panel()

    # ----- Public operations -----

    @property
    def analysis(self) -> DataSheetAnalysis:
        """The analysis as the SLP has applied it."""
        return self._analysis

    def show(self, analysis: DataSheetAnalysis) -> None:
        """Show a different template's analysis, with nothing selected and the panel closed."""
        self._selected = None
        self._close_panel()
        self.set_analysis(analysis)

    def set_analysis(self, analysis: DataSheetAnalysis) -> None:
        """Show a different analysis, keeping the selection and the open panel when they still exist."""
        self._analysis = analysis
        if self._selected is not None and not self._exists(self._selected):
            self._selected = None
        if self._open is not None and not self._exists(self._open):
            self._close_panel()
        elif self._open is not None and self._open[1] is not None and not self.has_unapplied_changes():
            self._load_panel(*self._open)
        self._render()
        self.refresh()

    def set_read_only(self, read_only: bool) -> None:
        """Switch between only showing the analysis and letting the SLP change it."""
        self._read_only = read_only
        if read_only:
            self._close_panel()
            self._buttons.grid_remove()
            self._panel_row.grid_remove()
        else:
            self._buttons.grid()
            self._panel_row.grid()
        self._render()

    def has_unapplied_changes(self) -> bool:
        """Whether the panel holds changes not yet applied to the analysis."""
        return self._open is not None and self._panel_calculation() != self._baseline

    def apply_pending(self) -> bool:
        """Apply the panel if it has unapplied changes. Returns False if they could not be applied."""
        if not self.has_unapplied_changes():
            return True
        return self._apply()

    def refresh(self) -> None:
        """Re-read the template's sections, after they change, and redraw."""
        self._render()
        if self._open is not None:
            self._fill_pickers()
            self._update_formula_state()

    # ----- Layers and calculations list -----

    def _exists(self, position: tuple[int, int | None]) -> bool:
        layer, index = position
        if layer < 1 or layer > len(self._analysis.layers):
            return False
        return index is None or index < len(self._analysis.layer(layer).calculations)

    def _render(self) -> None:
        self._tree.delete(*self._tree.get_children())
        if not self._analysis.layers:
            self._tree.insert("", tk.END, iid="none", text="No calculations.")
        for layer_number, layer in enumerate(self._analysis.layers, start=1):
            layer_row = self._tree.insert("", tk.END, iid=f"L{layer_number}", text=f"Layer {layer_number}",
                                          open=True, values=("", "" if layer.calculations else "(no calculations)"))
            for index, calculation in enumerate(layer.calculations):
                row = self._tree.insert(layer_row, tk.END, iid=f"C{layer_number}.{index}", open=True,
                                        text=calculation.name,
                                        values=(_kind_label(calculation), describe_calculation(calculation)))
                if calculation.description.strip():
                    self._tree.insert(row, tk.END, iid=f"D{layer_number}.{index}", text="",
                                      values=("", calculation.description))
        row_id = self._row_id(self._selected)
        if row_id is not None and self._tree.exists(row_id):
            self._tree.selection_set(row_id)
            self._tree.see(row_id)
        else:
            self._tree.selection_set(())

    @staticmethod
    def _row_id(position: tuple[int, int | None] | None) -> str | None:
        if position is None:
            return None
        layer, index = position
        return f"L{layer}" if index is None else f"C{layer}.{index}"

    @staticmethod
    def _position(row_id: str) -> tuple[int, int | None] | None:
        if row_id.startswith("L"):
            return int(row_id[1:]), None
        if row_id[:1] in ("C", "D"):
            layer, index = row_id[1:].split(".")
            return int(layer), int(index)
        return None

    def _on_tree_select(self, event: tk.Event | None = None) -> None:
        selection = self._tree.selection()
        position = self._position(selection[0]) if selection else None
        # Redrawing the tree re-selects the current row; Tk delivers that selection event later
        if position == self._selected or self._read_only:
            self._selected = position
            return
        if not self.apply_pending():
            self._render()
            return
        self._selected = position
        if position is not None and position[1] is not None:
            self._load_panel(position[0], position[1])
        else:
            self._close_panel()
        self._render()

    def _selected_layer(self) -> int | None:
        if self._selected is not None:
            return self._selected[0]
        return len(self._analysis.layers) or None

    def _warn(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message, parent=self.frame.winfo_toplevel())

    def _changed(self, analysis: DataSheetAnalysis) -> None:
        self._analysis = analysis
        self._on_change(analysis)
        self._render()

    def _on_add_layer(self) -> None:
        if not self.apply_pending():
            return
        analysis = self._analysis.with_layer_added()
        self._selected = (len(analysis.layers), None)
        self._close_panel()
        self._changed(analysis)

    def _on_delete_layer(self) -> None:
        highest = len(self._analysis.layers)
        if highest == 0:
            return
        if self._selected is None or self._selected[0] != highest:
            self._warn("Delete Layer", f"Only the highest layer, Layer {highest}, can be deleted. Select it first.")
            return
        count = len(self._analysis.layer(highest).calculations)
        if count and not messagebox.askyesno(
            "Delete Layer",
            f"Delete Layer {highest} and its {count} calculation{'s' if count != 1 else ''}?",
            parent=self.frame.winfo_toplevel(),
        ):
            return
        if self._open is not None and self._open[0] == highest:
            self._close_panel()
        self._selected = None
        self._changed(self._analysis.with_highest_layer_removed())

    def _on_add_calculation(self) -> None:
        layer = self._selected_layer()
        if layer is None:
            self._warn("Add Calculation", "Add a layer first.")
            return
        if not self.apply_pending():
            return
        self._selected = (layer, None)
        self._render()
        self._open_new(layer)

    def _on_remove(self) -> None:
        if self._selected is None or self._selected[1] is None:
            self._warn("No Selection", "Select a calculation to remove first.")
            return
        layer, index = self._selected
        calculation = self._analysis.layer(layer).calculations[index]
        users = [name for name in calculations_using(self._analysis, calculation.name)
                 if fold(name) != fold(calculation.name)]
        if users:
            self._warn("Calculation In Use", f'"{calculation.name}" is used by: {", ".join(users)}.')
            return
        if self._open is not None and self._open[0] == layer:
            self._close_panel()
        self._selected = (layer, None)
        self._changed(self._analysis.with_calculation_removed(layer, index))

    def _on_move(self, offset: int) -> None:
        if self._selected is None or self._selected[1] is None or not self.apply_pending():
            return
        layer, index = self._selected
        analysis, target = self._analysis.with_calculation_moved(layer, index, offset)
        if target == index:
            return
        if self._open == (layer, index):
            self._open = (layer, target)
        elif self._open == (layer, target):
            self._open = (layer, index)
        self._selected = (layer, target)
        self._changed(analysis)

    # ----- Calculation panel -----

    def _create_panel(self) -> None:
        panel = ttk.LabelFrame(self._panel_row, text="Calculation", padding="5")
        panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N))
        panel.columnconfigure(1, weight=1)
        self._panel = panel

        self._name_var = tk.StringVar()
        self._description_var = tk.StringVar()
        self._build_var = tk.StringVar(value=_MENU)
        ttk.Label(panel, text="Name:").grid(row=0, column=0, sticky=tk.W)
        self._name_entry = ttk.Entry(panel, textvariable=self._name_var)
        self._name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        ttk.Label(panel, text="Description:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Entry(panel, textvariable=self._description_var).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(5, 0))
        ttk.Label(panel, text=DESCRIPTION_HINT).grid(row=2, column=1, sticky=tk.W)

        build = ttk.Frame(panel)
        build.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        ttk.Label(build, text="Build with:").pack(side=tk.LEFT, padx=(0, 5))
        for label, value in (("Menu", _MENU), ("Formula", _FORMULA)):
            ttk.Radiobutton(build, text=label, value=value, variable=self._build_var,
                            command=self._on_build_changed).pack(side=tk.LEFT, padx=(0, 10))

        self._menu_frame = ttk.Frame(panel)
        self._menu_frame.columnconfigure(1, weight=1)
        self._create_menu_widgets(self._menu_frame)

        self._formula_frame = ttk.Frame(panel)
        self._formula_frame.columnconfigure(0, weight=1)
        self._formula_text = tk.Text(self._formula_frame, height=4, wrap=tk.WORD, undo=True)
        self._formula_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self._formula_text.tag_configure("problem", underline=True, foreground="#d9534f")
        self._formula_text.bind("<<Modified>>", self._on_formula_modified)
        self._formula_message = ttk.Label(self._formula_frame, text="", wraplength=520, justify=tk.LEFT)
        self._formula_message.grid(row=1, column=0, sticky=tk.W, pady=(3, 0))

        self._panel_message = ttk.Label(panel, text="Select a calculation, or press Add Calculation.")
        buttons = ttk.Frame(panel)
        buttons.grid(row=6, column=0, columnspan=2, sticky=tk.E, pady=(5, 0))
        self._apply_button = ttk.Button(buttons, text="Apply", command=self._apply)
        self._apply_button.pack(side=tk.LEFT, padx=(0, 5))
        self._cancel_button = ttk.Button(buttons, text="Cancel", command=self._on_panel_cancel)
        self._cancel_button.pack(side=tk.LEFT)

    def _create_menu_widgets(self, frame: ttk.Frame) -> None:
        def row(label: str, widget: tk.Widget, number: int) -> ttk.Label:
            text = ttk.Label(frame, text=label)
            text.grid(row=number, column=0, sticky=(tk.W, tk.N), padx=(0, 5), pady=(5, 0))
            widget.grid(row=number, column=1, sticky=tk.W, pady=(5, 0))
            return text

        self._kind_var = tk.StringVar(value=_ROW_AGGREGATE)
        kind_picker = ttk.Combobox(frame, textvariable=self._kind_var, state="readonly", width=16,
                                   values=[_ROW_AGGREGATE, _ARITHMETIC])
        kind_picker.bind("<<ComboboxSelected>>", lambda e: self._on_menu_kind_changed())
        row("Kind:", kind_picker, 0)

        # Row Aggregate
        self._aggregate_frame = ttk.Frame(frame)
        self._aggregate_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        aggregate = self._aggregate_frame

        def aggregate_row(label: str, widget: tk.Widget, number: int) -> tuple[ttk.Label, tk.Widget]:
            text = ttk.Label(aggregate, text=label, width=10)
            text.grid(row=number, column=0, sticky=(tk.W, tk.N), padx=(0, 5), pady=(5, 0))
            widget.grid(row=number, column=1, sticky=tk.W, pady=(5, 0))
            return text, widget

        self._table_var = tk.StringVar()
        self._measure_var = tk.StringVar()
        self._column_var = tk.StringVar()
        self._mark_var = tk.StringVar()
        self._choice_var = tk.StringVar()
        self._combination_var = tk.StringVar(value=_COMBINATION_LABELS[Combination.SUM])
        self._table_picker = ttk.Combobox(aggregate, textvariable=self._table_var, state="readonly", width=30)
        self._measure_picker = ttk.Combobox(aggregate, textvariable=self._measure_var, state="readonly", width=16)
        self._column_picker = ttk.Combobox(aggregate, textvariable=self._column_var, state="readonly", width=30)
        self._mark_picker = ttk.Combobox(aggregate, textvariable=self._mark_var, state="readonly", width=10)
        self._choice_picker = ttk.Combobox(aggregate, textvariable=self._choice_var, state="readonly", width=10)
        self._choice_columns = tk.Listbox(aggregate, selectmode=tk.MULTIPLE, height=4, exportselection=False,
                                          width=30)
        self._combination_picker = ttk.Combobox(aggregate, textvariable=self._combination_var, state="readonly",
                                                width=10, values=list(_COMBINATION_LABELS.values()))
        aggregate_row("Table:", self._table_picker, 0)
        aggregate_row("Measure:", self._measure_picker, 1)
        self._column_row = aggregate_row("Column:", self._column_picker, 2)
        self._mark_row = aggregate_row("Mark:", self._mark_picker, 3)
        self._choice_row = aggregate_row("Choice:", self._choice_picker, 4)
        self._choice_columns_row = aggregate_row("Columns:", self._choice_columns, 5)
        aggregate_row("Combine:", self._combination_picker, 6)
        for picker in (self._table_picker, self._measure_picker, self._column_picker, self._choice_picker):
            picker.bind("<<ComboboxSelected>>", lambda e: self._fill_pickers())

        # Arithmetic
        self._arithmetic_frame = ttk.Frame(frame)
        self._arithmetic_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        self._left = _OperandRow(self._arithmetic_frame, "Left:", lambda: None)
        self._left.frame.grid(row=0, column=0, sticky=tk.W, pady=(5, 0))
        operation_row = ttk.Frame(self._arithmetic_frame)
        operation_row.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Label(operation_row, text="Operation:", width=10).pack(side=tk.LEFT)
        self._operation_var = tk.StringVar(value=_OPERATION_LABELS[ArithmeticOperation.PERCENTAGE])
        ttk.Combobox(operation_row, textvariable=self._operation_var, state="readonly", width=32,
                     values=list(_OPERATION_LABELS.values())).pack(side=tk.LEFT)
        self._right = _OperandRow(self._arithmetic_frame, "Right:", lambda: None)
        self._right.frame.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))

    # ----- Panel state -----

    def _scope(self) -> AnalysisScope | None:
        if self._open is None:
            return None
        return analysis_scope(self._get_interpreters(), self._analysis, self._open[0])

    def _set_panel_enabled(self, enabled: bool) -> None:
        if enabled:
            self._panel_message.grid_remove()
            self._apply_button.state(["!disabled"])
            self._cancel_button.state(["!disabled"])
        else:
            self._menu_frame.grid_remove()
            self._formula_frame.grid_remove()
            self._legend.frame.grid_remove()
            self._panel_message.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
            self._apply_button.state(["disabled"])
            self._cancel_button.state(["disabled"])

    def _close_panel(self) -> None:
        self._open = None
        self._baseline = None
        self._panel.configure(text="Calculation")
        self._fill_from(Calculation("", "", RowAggregate("", NumberColumnMeasure(""), Combination.SUM)))
        self._set_panel_enabled(False)

    def _open_new(self, layer: int) -> None:
        self._open = (layer, None)
        self._panel.configure(text=f"New calculation in Layer {layer}")
        scope = self._scope()
        section = scope.tables[0].section if scope is not None and scope.tables else ""
        self._fill_from(Calculation("", "", RowAggregate(section, NumberColumnMeasure(""), Combination.SUM)))
        self._set_panel_enabled(True)
        self._baseline = self._panel_calculation()
        self._name_entry.focus_set()

    def _load_panel(self, layer: int, index: int) -> None:
        self._open = (layer, index)
        self._panel.configure(text=f"Calculation in Layer {layer}")
        self._fill_from(self._analysis.layer(layer).calculations[index])
        self._set_panel_enabled(True)
        self._baseline = self._panel_calculation()

    def _fill_from(self, calculation: Calculation) -> None:
        """Show a calculation in the panel."""
        self._filling = True
        try:
            self._name_var.set(calculation.name)
            self._description_var.set(calculation.description)
            definition = calculation.definition
            self._formula_text.delete("1.0", tk.END)
            if isinstance(definition, Formula):
                self._build_var.set(_FORMULA)
                self._formula_text.insert("1.0", definition.text)
            else:
                self._build_var.set(_MENU)
            if isinstance(definition, Arithmetic):
                self._kind_var.set(_ARITHMETIC)
                self._operation_var.set(_OPERATION_LABELS[definition.operation])
                self._left.load(definition.left)
                self._right.load(definition.right)
            elif isinstance(definition, RowAggregate):
                self._kind_var.set(_ROW_AGGREGATE)
                self._load_aggregate(definition)
            self._formula_text.edit_modified(False)
            self._formula_text.edit_reset()
        finally:
            self._filling = False
        self._fill_pickers()
        self._show_build()

    def _load_aggregate(self, aggregate: RowAggregate) -> None:
        self._table_var.set(aggregate.section)
        self._combination_var.set(_COMBINATION_LABELS[aggregate.combination])
        measure = aggregate.measure
        self._choice_columns.delete(0, tk.END)
        if isinstance(measure, NumberColumnMeasure):
            self._measure_var.set(_NUMBER_COLUMN)
            self._column_var.set(measure.column)
        elif isinstance(measure, TallyCountMeasure):
            self._measure_var.set(_TALLY_COUNT)
            self._column_var.set(measure.column)
            self._mark_var.set(TALLY_TOTAL_PART if measure.mark is None else measure.mark)
        else:
            self._measure_var.set(_CHOICE_COUNT)
            self._choice_var.set(measure.choice)
            self._loaded_choice_columns = list(measure.columns)

    def _show_build(self) -> None:
        """Show the menu or the formula entry, and the legend beside a formula."""
        if self._open is None:
            return
        if self._build_var.get() == _FORMULA:
            self._menu_frame.grid_remove()
            self._formula_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
            self._legend.frame.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.W, tk.E), padx=(10, 0))
        else:
            self._formula_frame.grid_remove()
            self._legend.frame.grid_remove()
            self._menu_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
            if self._kind_var.get() == _ARITHMETIC:
                self._aggregate_frame.grid_remove()
                self._arithmetic_frame.grid()
            else:
                self._arithmetic_frame.grid_remove()
                self._aggregate_frame.grid()
        self._update_formula_state()

    def _on_build_changed(self) -> None:
        self._show_build()

    def _on_menu_kind_changed(self) -> None:
        self._fill_pickers()
        self._show_build()

    # ----- Menu pickers -----

    def _table(self, scope: AnalysisScope) -> ScopeTable | None:
        return next((table for table in scope.tables if fold(table.section) == fold(self._table_var.get())), None)

    def _fill_pickers(self) -> None:
        """Offer only what the Analysis Scope holds, keeping each current choice when it still fits."""
        scope = self._scope()
        if scope is None or self._filling:
            return
        self._filling = True
        try:
            self._left.fill(scope)
            self._right.fill(scope)
            self._table_picker.configure(values=[table.section for table in scope.tables])
            table = self._table(scope)
            measures: list[str] = []
            if table is not None:
                if table.number_columns:
                    measures.append(_NUMBER_COLUMN)
                if table.tally_columns:
                    measures.append(_TALLY_COUNT)
                if table.choice_columns:
                    measures.append(_CHOICE_COUNT)
            self._measure_picker.configure(values=measures)
            if measures and self._measure_var.get() not in measures and table is not None:
                self._measure_var.set(measures[0])
            measure = self._measure_var.get()

            for widget_row in (self._column_row, self._mark_row, self._choice_row, self._choice_columns_row):
                for widget in widget_row:
                    widget.grid_remove()
            if measure in (_NUMBER_COLUMN, _TALLY_COUNT):
                for widget in self._column_row:
                    widget.grid()
            if measure == _NUMBER_COLUMN:
                columns = [entry.label for entry in table.number_columns] if table is not None else []
                self._column_picker.configure(values=columns)
            elif measure == _TALLY_COUNT:
                columns = [name for name, _ in table.tally_columns] if table is not None else []
                self._column_picker.configure(values=columns)
                entries = next((e for name, e in table.tally_columns if fold(name) == fold(self._column_var.get())),
                               []) if table is not None else []
                self._mark_picker.configure(values=[entry.label.split(" › ")[-1] for entry in entries])
                for widget in self._mark_row:
                    widget.grid()
            elif measure == _CHOICE_COUNT:
                self._fill_choice_count(table)
            if measure != _CHOICE_COUNT:
                self._choice_columns.delete(0, tk.END)
        finally:
            self._filling = False

    def _fill_choice_count(self, table: ScopeTable | None) -> None:
        choice_columns = table.choice_columns if table is not None else []
        choices: list[str] = []
        for _, column_choices, _ in choice_columns:
            for choice in column_choices:
                if all(fold(choice) != fold(existing) for existing in choices):
                    choices.append(choice)
        self._choice_picker.configure(values=choices)
        if self._choice_var.get() == "" and choices:
            self._choice_var.set(choices[0])
        selected = self._loaded_choice_columns
        if selected is None:
            selected = [self._choice_columns.get(i) for i in self._choice_columns.curselection()]
        self._loaded_choice_columns = None
        offering = [name for name, column_choices, _ in choice_columns
                    if any(fold(choice) == fold(self._choice_var.get()) for choice in column_choices)]
        # A saved column that no longer offers the choice stays listed, so Apply can say why
        names = offering + [name for name in selected if all(fold(name) != fold(o) for o in offering)]
        self._choice_columns.delete(0, tk.END)
        for index, name in enumerate(names):
            self._choice_columns.insert(tk.END, name)
            if any(fold(name) == fold(s) for s in selected):
                self._choice_columns.selection_set(index)
        for widget_row in (self._choice_row, self._choice_columns_row):
            for widget in widget_row:
                widget.grid()

    # ----- Building and applying -----

    def _menu_definition(self) -> CalculationDefinition:
        if self._kind_var.get() == _ARITHMETIC:
            operation = next((o for o, label in _OPERATION_LABELS.items() if label == self._operation_var.get()),
                             ArithmeticOperation.ADD)
            return Arithmetic(self._left.operand(), operation, self._right.operand())
        combination = next((c for c, label in _COMBINATION_LABELS.items() if label == self._combination_var.get()),
                           Combination.SUM)
        measure_kind = self._measure_var.get()
        if measure_kind == _TALLY_COUNT:
            mark = self._mark_var.get()
            measure = TallyCountMeasure(self._column_var.get(),
                                        None if fold(mark) == fold(TALLY_TOTAL_PART) else mark)
        elif measure_kind == _CHOICE_COUNT:
            columns = tuple(self._choice_columns.get(i) for i in self._choice_columns.curselection())
            measure = ChoiceCountMeasure(self._choice_var.get(), columns)
        else:
            measure = NumberColumnMeasure(self._column_var.get())
        return RowAggregate(self._table_var.get(), measure, combination)

    def _formula_text_value(self) -> str:
        return self._formula_text.get("1.0", "end-1c")

    def _panel_calculation(self) -> Calculation:
        """The calculation the panel would apply."""
        if self._build_var.get() == _FORMULA:
            definition: CalculationDefinition = Formula(self._formula_text_value())
        else:
            definition = self._menu_definition()
        return Calculation(self._name_var.get().strip(), self._description_var.get().strip(), definition)

    def _apply(self) -> bool:
        """
        Put the panel's calculation into the analysis.

        Returns:
            False if it could not be applied, after telling the SLP why
        """
        if self._open is None:
            return True
        layer, index = self._open
        calculation = self._panel_calculation()
        problems = calculation_problems(calculation, self._get_interpreters(), self._analysis, layer, index)
        if problems:
            self._update_formula_state()
            messagebox.showerror("Fix the Calculation", "\n".join(problems), parent=self.frame.winfo_toplevel())
            return False

        old_name = None if index is None else self._analysis.layer(layer).calculations[index].name
        analysis = self._analysis.with_calculation(layer, index, calculation)
        if index is None:
            index = len(analysis.layer(layer).calculations) - 1
        if old_name is not None and old_name.strip() != calculation.name.strip():
            analysis = apply_renames(analysis, [PartRename(PartKind.CALCULATION, "", "", old_name, calculation.name)])
        self._open = (layer, index)
        self._selected = (layer, index)
        self._panel.configure(text=f"Calculation in Layer {layer}")
        self._baseline = calculation
        self._changed(analysis)
        return True

    def _on_panel_cancel(self) -> None:
        if self._open is None:
            return
        layer, index = self._open
        if index is None:
            self._open_new(layer)
        else:
            self._load_panel(layer, index)

    # ----- Formula entry -----

    def _on_formula_modified(self, event: tk.Event | None = None) -> None:
        if not self._formula_text.edit_modified():
            return
        self._formula_text.edit_modified(False)
        self._update_formula_state()

    def _update_formula_state(self) -> None:
        """Check the formula and show the result under it, highlighting the first problem."""
        self._formula_text.tag_remove("problem", "1.0", tk.END)
        if self._open is None or self._build_var.get() != _FORMULA:
            return
        scope = self._scope()
        if scope is not None:
            self._legend.show(scope, self._open[0])
        text = self._formula_text_value()
        problems = formula_problems(text, self._get_interpreters(), self._analysis, self._open[0])
        if not problems:
            self._formula_message.configure(text="✓ Formula is OK.")
            return
        problem = problems[0]
        self._formula_message.configure(text=f"✗ {problem.message} (at character {problem.start + 1})")
        end = max(problem.end, problem.start + 1)
        self._formula_text.tag_add("problem", f"1.0+{problem.start}c", f"1.0+{end}c")

    def _insert_into_formula(self, text: str, placeholder_spans: list[tuple[int, int]]) -> None:
        """Insert a legend entry at the cursor, replacing a selection the cursor is in, and select its first placeholder."""
        entry = self._formula_text
        if entry.tag_ranges(tk.SEL):
            entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
        start = entry.index(tk.INSERT)
        entry.insert(tk.INSERT, text)
        if placeholder_spans:
            first_start, first_end = placeholder_spans[0]
            entry.tag_add(tk.SEL, f"{start}+{first_start}c", f"{start}+{first_end}c")
            entry.mark_set(tk.INSERT, f"{start}+{first_start}c")
        entry.focus_set()
        self._update_formula_state()
