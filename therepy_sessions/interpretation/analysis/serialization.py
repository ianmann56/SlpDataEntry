"""
The saved form of a Data Sheet Analysis, as kept under a template's "analysis" key in
templates.json. Enums are saved by member name, fixed numbers as strings (so 0.1 stays
exactly 0.1), and formulas exactly as typed.
"""

from decimal import Decimal, InvalidOperation
from typing import Any

from interpretation.analysis.model import (
  AnalysisLayer,
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
  RowMeasure,
  SheetValueOperand,
  TallyCountMeasure,
)


def analysis_to_json(analysis: DataSheetAnalysis) -> dict[str, Any]:
  """The analysis in its saved form."""
  return {
    "layers": [
      {"calculations": [_calculation_to_json(calculation) for calculation in layer.calculations]}
      for layer in analysis.layers
    ]
  }


def analysis_from_json(data: dict[str, Any] | None) -> DataSheetAnalysis:
  """
  Load a saved analysis. None or a missing "layers" key gives an empty analysis, as for
  templates saved before Data Sheet Analysis existed.

  Raises:
    ValueError: If a calculation, measure, or input has a kind that isn't known
  """
  if not data:
    return DataSheetAnalysis.empty()
  return DataSheetAnalysis(tuple(
    AnalysisLayer(tuple(_calculation_from_json(calculation) for calculation in layer.get("calculations") or []))
    for layer in data.get("layers") or []
  ))


# ----- Saving -----

def _calculation_to_json(calculation: Calculation) -> dict[str, Any]:
  data: dict[str, Any] = {"name": calculation.name, "description": calculation.description}
  definition = calculation.definition
  if isinstance(definition, RowAggregate):
    data.update({
      "kind": "row_aggregate",
      "section": definition.section,
      "combination": definition.combination.name,
      "measure": _measure_to_json(definition.measure),
    })
  elif isinstance(definition, Arithmetic):
    data.update({
      "kind": "arithmetic",
      "left": _operand_to_json(definition.left),
      "operation": definition.operation.name,
      "right": _operand_to_json(definition.right),
    })
  else:
    data.update({"kind": "formula", "formula": definition.text})
  return data


def _measure_to_json(measure: RowMeasure) -> dict[str, Any]:
  if isinstance(measure, NumberColumnMeasure):
    return {"kind": "number_column", "column": measure.column}
  if isinstance(measure, TallyCountMeasure):
    return {"kind": "tally_count", "column": measure.column, "mark": measure.mark}
  return {"kind": "choice_count", "choice": measure.choice, "columns": list(measure.columns)}


def _operand_to_json(operand: Operand) -> dict[str, Any]:
  if isinstance(operand, ResultOperand):
    return {"kind": "result", "calculation": operand.calculation}
  if isinstance(operand, SheetValueOperand):
    return {"kind": "sheet_value", "section": operand.section, "value": operand.value}
  return {"kind": "number", "number": str(operand.number)}


# ----- Loading -----

def _calculation_from_json(data: dict[str, Any]) -> Calculation:
  kind = data.get("kind")
  definition: CalculationDefinition
  if kind == "row_aggregate":
    definition = RowAggregate(
      str(data.get("section", "")),
      _measure_from_json(data.get("measure") or {}),
      _member(Combination, data.get("combination"), "combination"),
    )
  elif kind == "arithmetic":
    definition = Arithmetic(
      _operand_from_json(data.get("left") or {}),
      _member(ArithmeticOperation, data.get("operation"), "operation"),
      _operand_from_json(data.get("right") or {}),
    )
  elif kind == "formula":
    definition = Formula(str(data.get("formula", "")))
  else:
    raise ValueError(f'Unknown calculation kind "{kind}".')
  return Calculation(str(data.get("name", "")), str(data.get("description", "")), definition)


def _measure_from_json(data: dict[str, Any]) -> RowMeasure:
  kind = data.get("kind")
  if kind == "number_column":
    return NumberColumnMeasure(str(data.get("column", "")))
  if kind == "tally_count":
    mark = data.get("mark")
    return TallyCountMeasure(str(data.get("column", "")), None if mark is None else str(mark))
  if kind == "choice_count":
    return ChoiceCountMeasure(str(data.get("choice", "")), tuple(str(column) for column in data.get("columns") or []))
  raise ValueError(f'Unknown row measure kind "{kind}".')


def _operand_from_json(data: dict[str, Any]) -> Operand:
  kind = data.get("kind")
  if kind == "result":
    return ResultOperand(str(data.get("calculation", "")))
  if kind == "sheet_value":
    return SheetValueOperand(str(data.get("section", "")), str(data.get("value", "")))
  if kind == "number":
    try:
      return NumberOperand(Decimal(str(data.get("number", ""))))
    except InvalidOperation:
      raise ValueError(f'"{data.get("number")}" is not a number.') from None
  raise ValueError(f'Unknown input kind "{kind}".')


def _member[E](enum_type: type[E], name: Any, what: str) -> E:
  if isinstance(name, str) and name in enum_type.__members__:
    return enum_type[name]
  raise ValueError(f'Unknown {what} "{name}".')
