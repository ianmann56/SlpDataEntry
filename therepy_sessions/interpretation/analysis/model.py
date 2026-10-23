"""
The Data Sheet Analysis model: Analysis Layers of named Calculations.

Every record is frozen, so a template's analysis is only changed by building a new
value. Layer numbers are 1-based everywhere: layer n is `layers[n - 1]`.
"""

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum

from interpretation.analysis.formula import ReferenceKind, parse_formula


class Combination(Enum):
  """How a Row Aggregate combines its rows."""
  SUM = "Sum"
  AVERAGE = "Average"


class ArithmeticOperation(Enum):
  """How an Arithmetic calculation combines its two inputs."""
  ADD = "add"
  SUBTRACT = "subtract"
  MULTIPLY = "multiply"
  DIVIDE = "divide"
  PERCENTAGE = "percentage"  # left ÷ right × 100


@dataclass(frozen=True)
class NumberColumnMeasure:
  """A Row Measure: the number in one Integer or Decimal column."""
  column: str


@dataclass(frozen=True)
class TallyCountMeasure:
  """A Row Measure: the count of one tally mark in a Tally column, or the tally's total when mark is None."""
  column: str
  mark: str | None


@dataclass(frozen=True)
class ChoiceCountMeasure:
  """A Row Measure: how many of the chosen Choice columns hold the choice."""
  choice: str
  columns: tuple[str, ...]


RowMeasure = NumberColumnMeasure | TallyCountMeasure | ChoiceCountMeasure


@dataclass(frozen=True)
class RowAggregate:
  """A menu calculation: a Row Measure taken from every row of one table section, combined by Sum or Average."""
  section: str
  measure: RowMeasure
  combination: Combination


@dataclass(frozen=True)
class ResultOperand:
  """An Arithmetic input: the result of a calculation in a lower layer."""
  calculation: str


@dataclass(frozen=True)
class SheetValueOperand:
  """An Arithmetic input: a Numeric Sheet Value of one section."""
  section: str
  value: str


@dataclass(frozen=True)
class NumberOperand:
  """An Arithmetic input: a fixed number the SLP typed."""
  number: Decimal


Operand = ResultOperand | SheetValueOperand | NumberOperand


@dataclass(frozen=True)
class Arithmetic:
  """A menu calculation combining two inputs."""
  left: Operand
  operation: ArithmeticOperation
  right: Operand


@dataclass(frozen=True)
class Formula:
  """A calculation the SLP typed, kept exactly as typed."""
  text: str


CalculationDefinition = RowAggregate | Arithmetic | Formula


@dataclass(frozen=True)
class Calculation:
  """
  One named number a template defines for each imported sheet.

  Properties:
    name: Not blank, and unique in the template ignoring letter case and surrounding spaces.
    description: The optional Calculation Description, "" when none.
    definition: A menu calculation (RowAggregate or Arithmetic) or a Formula.
  """
  name: str
  description: str
  definition: CalculationDefinition

  @property
  def is_menu(self) -> bool:
    """Whether it was built from the menu rather than typed as a formula."""
    return not isinstance(self.definition, Formula)

  def result_references(self) -> list[str]:
    """The names of the calculations whose results this one uses, as written."""
    definition = self.definition
    if isinstance(definition, Arithmetic):
      return [operand.calculation for operand in (definition.left, definition.right)
              if isinstance(operand, ResultOperand)]
    if isinstance(definition, Formula):
      parse = parse_formula(definition.text)
      return [reference.parts[0] for reference in parse.references if reference.kind is ReferenceKind.RESULT]
    return []


@dataclass(frozen=True)
class AnalysisLayer:
  """A numbered group of calculations. A calculation may use results only from lower layers."""
  calculations: tuple[Calculation, ...] = ()


@dataclass(frozen=True)
class DataSheetAnalysis:
  """The calculations a template defines for one imported sheet, as an ordered list of Analysis Layers."""
  layers: tuple[AnalysisLayer, ...] = ()

  @classmethod
  def empty(cls) -> "DataSheetAnalysis":
    """An analysis with no layers."""
    return cls(())

  @property
  def is_empty(self) -> bool:
    """Whether it has no layers."""
    return not self.layers

  def layer(self, layer_number: int) -> AnalysisLayer:
    """The layer with this 1-based number."""
    return self.layers[layer_number - 1]

  def all_calculations(self) -> list[tuple[int, int, Calculation]]:
    """Every calculation as (layer number, index in its layer, calculation), in order."""
    return [
      (layer_number, index, calculation)
      for layer_number, layer in enumerate(self.layers, start=1)
      for index, calculation in enumerate(layer.calculations)
    ]

  def with_layer_added(self) -> "DataSheetAnalysis":
    """Add an empty layer above the highest one."""
    return replace(self, layers=self.layers + (AnalysisLayer(),))

  def with_highest_layer_removed(self) -> "DataSheetAnalysis":
    """
    Remove the highest layer and its calculations. Only the highest layer can be removed,
    so no remaining calculation can use a removed one's result.

    Raises:
      ValueError: If there are no layers
    """
    if not self.layers:
      raise ValueError("There is no layer to delete.")
    return replace(self, layers=self.layers[:-1])

  def _with_layer(self, layer_number: int, calculations: tuple[Calculation, ...]) -> "DataSheetAnalysis":
    layers = list(self.layers)
    layers[layer_number - 1] = AnalysisLayer(calculations)
    return replace(self, layers=tuple(layers))

  def with_calculation(self, layer_number: int, index: int | None, calculation: Calculation) -> "DataSheetAnalysis":
    """Append a calculation to a layer (index None), or replace the one at index."""
    calculations = list(self.layer(layer_number).calculations)
    if index is None:
      calculations.append(calculation)
    else:
      calculations[index] = calculation
    return self._with_layer(layer_number, tuple(calculations))

  def with_calculation_removed(self, layer_number: int, index: int) -> "DataSheetAnalysis":
    """
    Remove one calculation. No dependency check is made here: callers check
    `rules.calculations_using` first, and refuse while it is not empty.
    """
    calculations = list(self.layer(layer_number).calculations)
    del calculations[index]
    return self._with_layer(layer_number, tuple(calculations))

  def with_calculation_moved(self, layer_number: int, index: int, offset: int) -> tuple["DataSheetAnalysis", int]:
    """
    Move a calculation up (offset -1) or down (offset +1) within its layer. A move past
    either end does nothing.

    Returns:
      The analysis after the move, and the calculation's index after it
    """
    calculations = list(self.layer(layer_number).calculations)
    target = index + offset
    if target < 0 or target >= len(calculations):
      return self, index
    calculations[index], calculations[target] = calculations[target], calculations[index]
    return self._with_layer(layer_number, tuple(calculations)), target
