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
  """How a Row Aggregate combines its rows. EACH_ROW keeps every row's value, giving a Row List."""
  SUM = "Sum"
  AVERAGE = "Average"
  EACH_ROW = "Each row"


class ArithmeticOperation(Enum):
  """How an Arithmetic calculation combines its two inputs."""
  ADD = "add"
  SUBTRACT = "subtract"
  MULTIPLY = "multiply"
  DIVIDE = "divide"
  PERCENTAGE = "percentage"  # left ÷ right × 100


class ComparisonOperator(Enum):
  """How a comparison compares two values. A comparison gives 1 when it holds, and 0 when it doesn't."""
  EQUAL = "="
  NOT_EQUAL = "≠"
  LESS = "<"
  AT_MOST = "≤"
  GREATER = ">"
  AT_LEAST = "≥"


@dataclass(frozen=True)
class ResultOperand:
  """An Arithmetic or comparison input: the single-number result of a calculation in a lower layer."""
  calculation: str


@dataclass(frozen=True)
class SheetValueOperand:
  """An Arithmetic or comparison input: a Numeric Sheet Value of one section."""
  section: str
  value: str


@dataclass(frozen=True)
class NumberOperand:
  """An Arithmetic or comparison input: a fixed number the SLP typed."""
  number: Decimal


Operand = ResultOperand | SheetValueOperand | NumberOperand


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
  """A Row Measure: how many of the chosen Choice or True/False columns hold the choice."""
  choice: str
  columns: tuple[str, ...]


@dataclass(frozen=True)
class RowResultMeasure:
  """A Row Measure: the row's value in a lower-layer Row List of the same table."""
  calculation: str


# One side of a Comparison Measure: a value from each row (the first three), or one value for the whole sheet
ComparisonSide = NumberColumnMeasure | TallyCountMeasure | RowResultMeasure | ResultOperand | SheetValueOperand | NumberOperand

# The sides that have a value for each row
ROW_SIDES: tuple[type, ...] = (NumberColumnMeasure, TallyCountMeasure, RowResultMeasure)


@dataclass(frozen=True)
class ComparisonMeasure:
  """
  A Row Measure: 1 for a row where the comparison holds, 0 where it doesn't. At least one
  side has a value for each row; the other may be one value for the whole sheet.
  """
  left: ComparisonSide
  operator: ComparisonOperator
  right: ComparisonSide


RowMeasure = NumberColumnMeasure | TallyCountMeasure | ChoiceCountMeasure | RowResultMeasure | ComparisonMeasure


@dataclass(frozen=True)
class RowAggregate:
  """
  A menu calculation: a Row Measure taken from every row of one table section, combined
  by Sum or Average into one number, or kept for each row (a Row List).
  """
  section: str
  measure: RowMeasure
  combination: Combination


@dataclass(frozen=True)
class Arithmetic:
  """A menu calculation combining two inputs: by arithmetic, or by a comparison giving 1 or 0."""
  left: Operand
  operation: ArithmeticOperation | ComparisonOperator
  right: Operand


@dataclass(frozen=True)
class Formula:
  """A calculation the SLP typed, kept exactly as typed."""
  text: str


CalculationDefinition = RowAggregate | Arithmetic | Formula


class ShowAs(Enum):
  """How a calculation's result is displayed with imported sheets. Display only: it never changes a result."""
  NUMBER = "Number"
  PERCENT = "Percent"


def default_show_as(definition: CalculationDefinition) -> ShowAs:
  """
  The Show as a calculation gets when it is new, or saved before Show as existed: Percent
  for an Arithmetic percentage, and Number for everything else.
  """
  if isinstance(definition, Arithmetic) and definition.operation is ArithmeticOperation.PERCENTAGE:
    return ShowAs.PERCENT
  return ShowAs.NUMBER


@dataclass(frozen=True)
class Calculation:
  """
  One named result a template defines for each imported sheet: a number, or a Row List
  (one value per row of a table) when it is a Row Aggregate combined by Each row.

  Properties:
    name: Not blank, and unique in the template ignoring letter case and surrounding spaces.
    description: The optional Calculation Description, "" when none.
    definition: A menu calculation (RowAggregate or Arithmetic) or a Formula.
    show_in_imported_sheets: Whether its result appears with each sheet imported with the
      template. False makes it a Hidden Calculation. Hiding never changes what may use its
      result or how any result is worked out. When results are worked out, every
      calculation a shown one depends on is still worked out, but only shown results are
      shown.
    show_as: How its result is displayed with imported sheets: as a number, or as a
      percentage (a result of 72 shows as 72%). Display only: it never changes a result's
      value, how any calculation uses it, or the Template Structure.
  """
  name: str
  description: str
  definition: CalculationDefinition
  show_in_imported_sheets: bool = True
  show_as: ShowAs = ShowAs.NUMBER

  @property
  def is_menu(self) -> bool:
    """Whether it was built from the menu rather than typed as a formula."""
    return not isinstance(self.definition, Formula)

  @property
  def row_list_section(self) -> str | None:
    """The table whose rows its Row List follows, or None when its result is one number."""
    definition = self.definition
    if isinstance(definition, RowAggregate) and definition.combination is Combination.EACH_ROW:
      return definition.section
    return None

  def result_references(self) -> list[str]:
    """The names of the calculations whose results this one uses, as written."""
    definition = self.definition
    if isinstance(definition, Arithmetic):
      return [operand.calculation for operand in (definition.left, definition.right)
              if isinstance(operand, ResultOperand)]
    if isinstance(definition, Formula):
      parse = parse_formula(definition.text)
      return [reference.parts[0] for reference in parse.references if reference.kind is ReferenceKind.RESULT]
    measure = definition.measure
    if isinstance(measure, RowResultMeasure):
      return [measure.calculation]
    if isinstance(measure, ComparisonMeasure):
      return [side.calculation for side in (measure.left, measure.right)
              if isinstance(side, (ResultOperand, RowResultMeasure))]
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
