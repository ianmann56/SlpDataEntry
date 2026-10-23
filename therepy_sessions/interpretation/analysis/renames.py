"""
Renames: when the SLP renames a template part in place, every calculation that uses it
follows the new name.

Menu calculations have their fields changed. Formulas have only the spans of matching
references rewritten (re-escaped), so everything else stays exactly as typed (FR-016a).
A formula that doesn't parse is left unchanged: it is already a problem, reported at Save.
"""

from dataclasses import replace
from enum import Enum
from typing import NamedTuple

from interpretation.analysis.formula import FormulaReference, ReferenceKind, escape_name, parse_formula, quote_choice
from interpretation.analysis.model import (
  AnalysisLayer,
  Arithmetic,
  Calculation,
  CalculationDefinition,
  ChoiceCountMeasure,
  DataSheetAnalysis,
  Formula,
  NumberColumnMeasure,
  Operand,
  ResultOperand,
  RowAggregate,
  SheetValueOperand,
  TallyCountMeasure,
)
from interpretation.analysis.scope import fold

# How a Running Tally names an option's percentage among its Numeric Sheet Values
_PERCENT_SUFFIX: str = " %"


class PartKind(Enum):
  """What kind of template part was renamed."""
  SECTION = "section"
  ITEM = "item"                # a column or a field
  OPTION = "option"            # a choice or a tally mark
  CALCULATION = "calculation"


class PartRename(NamedTuple):
  """
  One part renamed in place.

  Properties:
    kind: What was renamed.
    section: The Section Name the part belongs to, after any section rename. "" for a calculation.
    item: The column or field an option belongs to. "" otherwise, including for a Running Tally mark.
    old: The name before.
    new: The name after.
  """
  kind: PartKind
  section: str
  item: str
  old: str
  new: str


def apply_renames(analysis: DataSheetAnalysis, renames: list[PartRename]) -> DataSheetAnalysis:
  """Rewrite every calculation that uses a renamed part, applying the renames in order."""
  for rename in renames:
    if rename.old.strip() == rename.new.strip():
      continue
    analysis = DataSheetAnalysis(tuple(
      AnalysisLayer(tuple(_renamed_calculation(calculation, rename) for calculation in layer.calculations))
      for layer in analysis.layers
    ))
  return analysis


def _renamed_calculation(calculation: Calculation, rename: PartRename) -> Calculation:
  definition: CalculationDefinition = calculation.definition
  if isinstance(definition, RowAggregate):
    definition = _renamed_aggregate(definition, rename)
  elif isinstance(definition, Arithmetic):
    definition = replace(
      definition,
      left=_renamed_operand(definition.left, rename),
      right=_renamed_operand(definition.right, rename),
    )
  else:
    definition = Formula(_renamed_formula(definition.text, rename))
  return replace(calculation, definition=definition)


def _same(a: str, b: str) -> bool:
  return fold(a) == fold(b)


# ----- Menu calculations -----

def _renamed_aggregate(aggregate: RowAggregate, rename: PartRename) -> RowAggregate:
  if rename.kind is PartKind.SECTION:
    return replace(aggregate, section=rename.new) if _same(aggregate.section, rename.old) else aggregate
  if rename.kind is PartKind.CALCULATION or not _same(aggregate.section, rename.section):
    return aggregate

  measure = aggregate.measure
  if rename.kind is PartKind.ITEM:
    if isinstance(measure, (NumberColumnMeasure, TallyCountMeasure)) and _same(measure.column, rename.old):
      measure = replace(measure, column=rename.new)
    elif isinstance(measure, ChoiceCountMeasure):
      measure = replace(measure, columns=tuple(
        rename.new if _same(column, rename.old) else column for column in measure.columns
      ))
  elif rename.kind is PartKind.OPTION and rename.item:
    if (isinstance(measure, TallyCountMeasure) and measure.mark is not None
        and _same(measure.column, rename.item) and _same(measure.mark, rename.old)):
      measure = replace(measure, mark=rename.new)
    elif (isinstance(measure, ChoiceCountMeasure) and _same(measure.choice, rename.old)
          and any(_same(column, rename.item) for column in measure.columns)):
      measure = replace(measure, choice=rename.new)
  return replace(aggregate, measure=measure)


def _renamed_operand(operand: Operand, rename: PartRename) -> Operand:
  if isinstance(operand, ResultOperand):
    if rename.kind is PartKind.CALCULATION and _same(operand.calculation, rename.old):
      return ResultOperand(rename.new)
    return operand
  if isinstance(operand, SheetValueOperand):
    if rename.kind is PartKind.SECTION:
      return replace(operand, section=rename.new) if _same(operand.section, rename.old) else operand
    if rename.kind is PartKind.CALCULATION or not _same(operand.section, rename.section):
      return operand
    value = _renamed_value(operand.value, rename)
    return replace(operand, value=value) if value is not None else operand
  return operand


def _renamed_value(value: str, rename: PartRename) -> str | None:
  """A Numeric Sheet Value's new name after an item or Running Tally mark rename, or None if it is untouched."""
  if rename.kind is PartKind.ITEM and _same(value, rename.old):
    return rename.new
  if rename.kind is PartKind.OPTION and not rename.item:
    if _same(value, rename.old):
      return rename.new
    if _same(value, rename.old + _PERCENT_SUFFIX):
      return rename.new + _PERCENT_SUFFIX
  return None


# ----- Formulas -----

def _renamed_parts(reference: FormulaReference, rename: PartRename) -> tuple[str, ...] | None:
  """A sheet or column reference's parts after the rename, or None if it is untouched."""
  parts = list(reference.parts)
  if rename.kind is PartKind.SECTION:
    if not _same(parts[0], rename.old):
      return None
    parts[0] = rename.new
    return tuple(parts)
  if rename.kind is PartKind.CALCULATION or not _same(parts[0], rename.section):
    return None
  if reference.kind is ReferenceKind.SHEET_VALUE:
    value = _renamed_value(parts[1], rename)
    if value is None:
      return None
    parts[1] = value
    return tuple(parts)
  if rename.kind is PartKind.ITEM and _same(parts[1], rename.old):
    parts[1] = rename.new
    return tuple(parts)
  if (rename.kind is PartKind.OPTION and rename.item and len(parts) == 3
      and _same(parts[1], rename.item) and _same(parts[2], rename.old)):
    parts[2] = rename.new
    return tuple(parts)
  return None


def _renamed_formula(text: str, rename: PartRename) -> str:
  parse = parse_formula(text)
  if parse.problem is not None:
    return text

  edits: dict[tuple[int, int], str] = {}
  for reference in parse.references:
    if reference.kind is ReferenceKind.RESULT:
      if rename.kind is PartKind.CALCULATION and _same(reference.parts[0], rename.old):
        edits[(reference.start, reference.end)] = f"{{{escape_name(rename.new)}}}"
      continue
    parts = _renamed_parts(reference, rename)
    if parts is not None:
      edits[(reference.start, reference.end)] = "[" + "/".join(escape_name(part) for part in parts) + "]"
    # A COUNT's choice follows a rename of that choice in one of the columns it counts
    if (reference.choice is not None and rename.kind is PartKind.OPTION and rename.item
        and _same(reference.parts[0], rename.section) and _same(reference.parts[1], rename.item)
        and _same(reference.choice, rename.old)):
      edits[(reference.choice_start, reference.choice_end)] = quote_choice(rename.new)

  # Replace from the end backwards, so earlier offsets stay valid
  for (start, end), new_text in sorted(edits.items(), reverse=True):
    text = text[:start] + new_text + text[end:]
  return text
