"""
Calculation Results: every Data Sheet Analysis calculation worked out for one imported
sheet. Pure: no I/O, and the same sheet always gives the same results.

Every calculation is evaluated as a formula tree (see parse_formula), so a menu
calculation and the same calculation typed as a formula always agree:

- a Formula: its own tree
- a menu Sum, Average, or Arithmetic calculation: the tree of menu_formula()
- a menu Each row aggregate: the tree of its per-row measure (menu_row_measure()), once
  per row of its table, giving a Row List

Values are Decimal, and None is an empty value. The meaning rules are 009's:

- An Average covers only the rows with a value, and is empty over none.
- A Sum over no values is 0.
- Dividing by 0, or using an empty value in arithmetic, a comparison, or COUNT, gives
  an empty value.
- A blank or unreadable cell holds no choice.

Sections hand their values over through analysis_sheet_value() and analysis_row_value(),
so nothing here checks interpreter types (Principle V).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, NamedTuple

from interpretation.analysis.formula import FormulaNode, parse_formula
from interpretation.analysis.menu_formula import menu_formula, menu_row_measure
from interpretation.analysis.model import Calculation, DataSheetAnalysis, Formula, RowAggregate, ShowAs
from interpretation.analysis.parts import fold
from interpretation.analysis.rules import reference_problems
from interpretation.analysis.scope import find_section

if TYPE_CHECKING:
  # For type checking only: the sheet module creates AnalysisResults lazily
  from interpretation.student_data_sheet import DataSheetScalarDto, StudentDataSheet
  from interpretation.templates.student_data_sheet_interpreter import SessionDataSectionInterpreterBase


class CalculationResult(NamedTuple):
  """
  One calculation's result for one imported sheet.

  Properties:
    name: The calculation's name, as configured.
    layer: Its Analysis Layer number.
    shown: Whether it shows with imported sheets (Show in imported sheets).
    show_as: How its result is displayed.
    value: A single-number result, or None when it is empty. Always None for a Row List.
    rows: A Row List: one value per row of its table section, None for an empty row.
      None when the result is a single number. () for a broken Row List.
    broken: Whether it couldn't be worked out, because it or a calculation it uses is broken.
  """
  name: str
  layer: int
  shown: bool
  show_as: ShowAs
  value: Decimal | None
  rows: tuple[Decimal | None, ...] | None
  broken: bool

  @property
  def is_row_list(self) -> bool:
    """Whether the result is a Row List rather than one number."""
    return self.rows is not None


class AnalysisResults(NamedTuple):
  """
  Every calculation's result for one imported sheet, in layer order and then template order.

  Properties:
    results: One per calculation, hidden ones included.
  """
  results: tuple[CalculationResult, ...]

  @classmethod
  def none(cls) -> AnalysisResults:
    """The results of a template with no calculations."""
    return cls(())

  @property
  def shown_values(self) -> list[CalculationResult]:
    """The shown single-number results, in order."""
    return [result for result in self.results if result.shown and not result.is_row_list]

  @property
  def shown_row_lists(self) -> list[CalculationResult]:
    """The shown Row Lists, in order."""
    return [result for result in self.results if result.shown and result.is_row_list]

  @property
  def has_shown(self) -> bool:
    """Whether any result shows with the sheet. When not, nothing is written for the analysis."""
    return any(result.shown for result in self.results)


class AnalysisProblem(NamedTuple):
  """
  A Broken Calculation the SLP is warned about: one that can't be worked out because it
  refers to something the template no longer has (possible only when the template was
  changed outside the app).

  Properties:
    calculation: Its name.
    problem: What it refers to that is missing or has the wrong type.
  """
  calculation: str
  problem: str

  def message(self) -> str:
    """The warning as the SLP reads it."""
    return f'Calculation "{self.calculation.strip()}" can\'t be worked out: {self.problem}'


class _Broken(Exception):
  """A calculation that can't be worked out on this sheet."""


_ZERO = Decimal(0)
_ONE = Decimal(1)


def _number(value: Any) -> Decimal | None:
  """A Typed Value as a number: ints and floats only (a True/False value is not a number)."""
  if isinstance(value, bool) or not isinstance(value, (int, float)):
    return None
  try:
    return Decimal(str(value))
  except InvalidOperation:
    return None


def _holds(cell: Any, choice: str) -> bool:
  """Whether a cell holds a choice. A True/False cell holds "True" or "False"; a blank cell holds none."""
  if cell is None:
    return False
  text = ("True" if cell else "False") if isinstance(cell, bool) else str(cell)
  return fold(text) == fold(choice)


def _compare(left: Decimal, operator: str, right: Decimal) -> bool:
  return {
    "EQUAL": left == right,
    "NOT_EQUAL": left != right,
    "LESS": left < right,
    "AT_MOST": left <= right,
    "GREATER": left > right,
    "AT_LEAST": left >= right,
  }[operator]


class _Evaluator:
  """Works out formula trees against one sheet and the results worked out so far."""

  def __init__(self, sheet: StudentDataSheet) -> None:
    self._sheet = sheet
    self._interpreters: list[SessionDataSectionInterpreterBase] = sheet.template.interpreters
    # The results so far, by folded name
    self.results: dict[str, CalculationResult] = {}
    # The table section each Row List follows, by folded name
    self.row_list_sections: dict[str, str] = {}

  # ----- Sections -----

  def section(self, name: str) -> SessionDataSectionInterpreterBase:
    found = find_section(self._interpreters, name)
    if found is None:
      raise _Broken(f'There is no one section named "{name}".')
    return found

  @staticmethod
  def is_table(section: SessionDataSectionInterpreterBase) -> bool:
    return bool(section.analysis_parts().table_columns)

  def tables(self, section: SessionDataSectionInterpreterBase) -> list[Any]:
    return [table for table in self._sheet.tables if table.get("section_id") == section.id]

  def rows(self, section_name: str) -> list[dict[str, DataSheetScalarDto]]:
    """Every row of every table of a table section, in sheet order."""
    return [row for table in self.tables(self.section(section_name)) for row in table["data"]]

  def sheet_value(self, section_name: str, value: str) -> Decimal | None:
    section = self.section(section_name)
    return _number(section.analysis_sheet_value(value, self.tables(section), self._sheet.scalars))

  # ----- Results -----

  def result(self, name: str) -> CalculationResult:
    found = self.results.get(fold(name))
    if found is None:
      raise _Broken(f'There is no lower-layer result named "{name}".')
    if found.broken:
      raise _Broken(f'It uses "{found.name}", which can\'t be worked out.')
    return found

  # ----- Evaluation -----

  def value(self, node: FormulaNode, row: tuple[str, int, dict[str, DataSheetScalarDto]] | None = None) -> Decimal | None:
    """
    Work out one node: for the whole sheet when `row` is None, or for one row as
    (table section, row index, row) inside SUM or AVERAGE.
    """
    kind = node["kind"]
    if kind == "number":
      return Decimal(node["number"])
    if kind == "result":
      result = self.result(node["calculation"])
      if result.rows is None:
        return result.value
      if row is None:
        raise _Broken(f'"{result.name}" has a value per row, so it can only be summed or averaged.')
      return result.rows[row[1]] if row[1] < len(result.rows) else None
    if kind == "sheet_value":
      return self.sheet_value(node["section"], node["value"])
    if kind == "column":
      return _number(self.cell(node, row))
    if kind == "negate":
      operand = self.value(node["operand"], row)
      return None if operand is None else -operand
    if kind == "arithmetic":
      return self.arithmetic(node, row)
    if kind == "comparison":
      return self.comparison(node, row)
    if kind == "aggregate":
      return self.aggregate(node)
    if kind == "choice_count":
      return Decimal(sum(1 for column in node["columns"] if _holds(self.cell(column, row), node["choice"])))
    if kind == "count":
      values = [self.value(condition, row) for condition in node["conditions"]]
      if any(value is None for value in values):
        return None
      return Decimal(sum(1 for value in values if value == _ONE))
    raise _Broken(f'A formula part "{kind}" can\'t be worked out.')

  def cell(self, node: FormulaNode, row: tuple[str, int, dict[str, DataSheetScalarDto]] | None) -> Any:
    """
    The Typed Value a column reference names: a cell of the current row for a table
    section, or a Numeric Sheet Value for any other section.
    """
    section = self.section(node["section"])
    if not self.is_table(section):
      return section.analysis_sheet_value(node["column"], self.tables(section), self._sheet.scalars)
    if row is None or fold(row[0]) != fold(section.section_name):
      raise _Broken(f'[{node["section"]}/{node["column"]}] can only be used inside SUM or AVERAGE over its table.')
    return section.analysis_row_value(row[2], node["column"], node.get("part"))

  def arithmetic(self, node: FormulaNode, row: tuple[str, int, dict[str, DataSheetScalarDto]] | None) -> Decimal | None:
    left = self.value(node["left"], row)
    right = self.value(node["right"], row)
    if left is None or right is None:
      return None
    operation = node["operation"]
    if operation == "ADD":
      return left + right
    if operation == "SUBTRACT":
      return left - right
    if operation == "MULTIPLY":
      return left * right
    return None if right == _ZERO else left / right

  def comparison(self, node: FormulaNode, row: tuple[str, int, dict[str, DataSheetScalarDto]] | None) -> Decimal | None:
    left, right, operator = node["left"], node["right"], node["operator"]
    if left["kind"] == "choice" or right["kind"] == "choice":
      choice, column = (left, right) if left["kind"] == "choice" else (right, left)
      holds = _holds(self.cell(column, row), choice["choice"])
      return _ONE if holds == (operator == "EQUAL") else _ZERO
    left_value = self.value(left, row)
    right_value = self.value(right, row)
    if left_value is None or right_value is None:
      return None
    return _ONE if _compare(left_value, operator, right_value) else _ZERO

  def table_of(self, node: FormulaNode) -> str | None:
    """The table section an aggregate's measure reads rows from: of its first column of a table, or Row List."""
    kind = node.get("kind")
    if kind == "column":
      section = self.section(node["section"])
      if self.is_table(section):
        return section.section_name
    if kind == "result":
      section_name = self.row_list_sections.get(fold(node["calculation"]))
      if section_name is not None:
        return section_name
    for child in node.values():
      for item in child if isinstance(child, list) else [child]:
        if isinstance(item, dict) and (found := self.table_of(item)) is not None:
          return found
    return None

  def per_row(self, measure: FormulaNode, section_name: str) -> list[Decimal | None]:
    """A measure worked out for each row of a table section, in sheet order."""
    return [self.value(measure, (section_name, index, row)) for index, row in enumerate(self.rows(section_name))]

  def aggregate(self, node: FormulaNode) -> Decimal | None:
    section_name = self.table_of(node["measure"])
    if section_name is None:
      raise _Broken("A SUM or AVERAGE has nothing to read from a table's rows.")
    values = [value for value in self.per_row(node["measure"], section_name) if value is not None]
    if node["combination"] == "SUM":
      return sum(values, _ZERO)
    return sum(values, _ZERO) / len(values) if values else None


def _tree(text: str) -> FormulaNode:
  structure = parse_formula(text).structure
  if structure is None:
    raise _Broken(f'Its formula can\'t be read: {text}')
  return structure


def _work_out(calculation: Calculation, evaluator: _Evaluator) -> tuple[Decimal | None, tuple[Decimal | None, ...] | None]:
  """One calculation's value, or its Row List."""
  definition = calculation.definition
  if isinstance(definition, Formula):
    return evaluator.value(_tree(definition.text)), None
  if isinstance(definition, RowAggregate) and calculation.row_list_section is not None:
    measure = _tree(f"SUM({menu_row_measure(definition)})")["measure"]
    return None, tuple(evaluator.per_row(measure, definition.section))
  text = menu_formula(definition)
  assert text is not None
  return evaluator.value(_tree(text)), None


def _needed_by_shown(analysis: DataSheetAnalysis) -> set[str]:
  """The folded names of every shown calculation, and of every calculation they use, directly or not."""
  by_name = {fold(calculation.name): calculation for _, _, calculation in analysis.all_calculations()}
  needed: set[str] = set()
  pending = [fold(calculation.name) for calculation in by_name.values() if calculation.show_in_imported_sheets]
  while pending:
    name = pending.pop()
    if name in needed or name not in by_name:
      continue
    needed.add(name)
    pending.extend(fold(reference) for reference in by_name[name].result_references())
  return needed


def work_out_results(sheet: StudentDataSheet) -> tuple[AnalysisResults, list[AnalysisProblem]]:
  """
  Every calculation of the sheet's template worked out from the sheet's values, and one
  problem per Broken Calculation that is shown or that a shown calculation uses.

  A Broken Calculation, and every calculation that uses it directly or not, gives an
  empty result (a Row List gives ()). Every other calculation is worked out. Nothing here
  fails the sheet.
  """
  analysis = sheet.template.analysis
  if analysis.is_empty:
    return AnalysisResults.none(), []
  interpreters = sheet.template.interpreters
  evaluator = _Evaluator(sheet)
  needed = _needed_by_shown(analysis)
  results: list[CalculationResult] = []
  problems: list[AnalysisProblem] = []
  for layer_number, _, calculation in analysis.all_calculations():
    name = fold(calculation.name)
    is_row_list = calculation.row_list_section is not None
    if is_row_list:
      evaluator.row_list_sections[name] = calculation.row_list_section or ""
    own_problems = reference_problems(calculation, interpreters, analysis, layer_number)
    value: Decimal | None = None
    rows: tuple[Decimal | None, ...] | None = () if is_row_list else None
    broken = True
    uses_broken = any(
      (used := evaluator.results.get(fold(reference))) is not None and used.broken
      for reference in calculation.result_references()
    )
    if not own_problems and not uses_broken:
      try:
        value, rows = _work_out(calculation, evaluator)
        broken = False
      except _Broken as e:
        own_problems = [str(e)]
      except (ArithmeticError, KeyError, IndexError, TypeError, ValueError) as e:
        # Never fail the sheet over its analysis: an unexpected error breaks only this calculation
        own_problems = [f"It couldn't be worked out ({type(e).__name__})."]
      if broken:
        value, rows = None, (() if is_row_list else None)
    if own_problems and name in needed:
      problems.append(AnalysisProblem(calculation.name, own_problems[0]))
    result = CalculationResult(
      calculation.name, layer_number, calculation.show_in_imported_sheets, calculation.show_as, value, rows, broken,
    )
    evaluator.results[name] = result
    results.append(result)
  return AnalysisResults(tuple(results)), problems
