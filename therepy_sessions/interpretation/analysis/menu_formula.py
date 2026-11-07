"""
The formula a menu calculation is equivalent to, written in the Formula calculation
language (see formula.py), so a saved menu calculation can be read the same way as a typed one.

The menu choices stay the source of a menu calculation: this text is only derived from
them, and is never read back.
"""

from decimal import Decimal

from interpretation.analysis.formula import quote_choice
from interpretation.analysis.model import (
  Arithmetic,
  ArithmeticOperation,
  ChoiceCountMeasure,
  Combination,
  ComparisonMeasure,
  ComparisonOperator,
  ComparisonSide,
  NumberColumnMeasure,
  NumberOperand,
  ResultOperand,
  RowAggregate,
  RowMeasure,
  RowResultMeasure,
  SheetValueOperand,
  TallyCountMeasure,
)
from interpretation.analysis.scope import TALLY_TOTAL_PART, result_reference, sheet_reference

_ARITHMETIC_SYMBOLS: dict[ArithmeticOperation, str] = {
  ArithmeticOperation.ADD: "+",
  ArithmeticOperation.SUBTRACT: "-",
  ArithmeticOperation.MULTIPLY: "*",
  ArithmeticOperation.DIVIDE: "/",
}

_COMPARISON_SYMBOLS: dict[ComparisonOperator, str] = {
  ComparisonOperator.EQUAL: "=",
  ComparisonOperator.NOT_EQUAL: "<>",
  ComparisonOperator.LESS: "<",
  ComparisonOperator.AT_MOST: "<=",
  ComparisonOperator.GREATER: ">",
  ComparisonOperator.AT_LEAST: ">=",
}

_AGGREGATE_FUNCTIONS: dict[Combination, str] = {
  Combination.SUM: "SUM",
  Combination.AVERAGE: "AVERAGE",
}


def menu_formula(definition: RowAggregate | Arithmetic) -> str | None:
  """
  The formula equivalent to a menu calculation, or None for a Row Aggregate combined by
  Each row: its result is a Row List, and a formula's result is always one number.
  """
  if isinstance(definition, Arithmetic):
    left = _side(definition.left, None)
    right = _side(definition.right, None)
    if definition.operation is ArithmeticOperation.PERCENTAGE:
      return f"{left} / {right} * 100"
    if isinstance(definition.operation, ComparisonOperator):
      return f"{left} {_COMPARISON_SYMBOLS[definition.operation]} {right}"
    return f"{left} {_ARITHMETIC_SYMBOLS[definition.operation]} {right}"
  function = _AGGREGATE_FUNCTIONS.get(definition.combination)
  if function is None:
    return None
  return f"{function}({_measure(definition.measure, definition.section)})"


def _measure(measure: RowMeasure, section: str) -> str:
  """A Row Measure as the per-row expression inside SUM or AVERAGE."""
  if isinstance(measure, ChoiceCountMeasure):
    columns = ", ".join(sheet_reference(section, column) for column in measure.columns)
    return f"COUNT({quote_choice(measure.choice)}, {columns})"
  if isinstance(measure, ComparisonMeasure):
    left = _side(measure.left, section)
    right = _side(measure.right, section)
    return f"{left} {_COMPARISON_SYMBOLS[measure.operator]} {right}"
  return _side(measure, section)


def _side(side: ComparisonSide, table: str | None) -> str:
  """One value: a row's column, tally part, or Row List value (in its table), or a value for the sheet."""
  if isinstance(side, NumberColumnMeasure):
    return sheet_reference(table or "", side.column)
  if isinstance(side, TallyCountMeasure):
    part = TALLY_TOTAL_PART if side.mark is None else side.mark
    return sheet_reference(table or "", side.column, part)
  if isinstance(side, (RowResultMeasure, ResultOperand)):
    return result_reference(side.calculation)
  if isinstance(side, SheetValueOperand):
    return sheet_reference(side.section, side.value)
  assert isinstance(side, NumberOperand)
  return _number(side.number)


def _number(number: Decimal) -> str:
  """A fixed number as the formula language writes it: plain digits, a negative one in parentheses."""
  text = format(number, "f")
  if "." in text:
    text = text.rstrip("0").rstrip(".")
  if text in ("", "-0"):
    text = "0"
  return f"({text})" if text.startswith("-") else text
