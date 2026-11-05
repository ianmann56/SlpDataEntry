"""
The rules of Data Sheet Analysis: what stops a calculation or a template from being
saved, which calculations use a result, and how each calculation reads in plain language.

The editor widgets and the template's Save call these functions instead of deciding
anything themselves (layers rule 5).
"""

from interpretation.analysis.formula import FormulaProblem, FormulaReference, ReferenceKind, parse_formula
from interpretation.analysis.model import (
  Arithmetic,
  ArithmeticOperation,
  Calculation,
  ChoiceCountMeasure,
  Combination,
  DataSheetAnalysis,
  Formula,
  NumberColumnMeasure,
  Operand,
  ResultOperand,
  RowAggregate,
  RowResultMeasure,
  SheetValueOperand,
  TallyCountMeasure,
)
from interpretation.analysis.parts import TableColumnPart
from interpretation.analysis.scope import (
  NUMBER_COLUMN_TYPES,
  TALLY_TOTAL_PART,
  countable_choices,
  find_column,
  find_section,
  find_sheet_value,
  fold,
  is_ambiguous,
  lower_layer_calculation,
)
from interpretation.templates.student_data_sheet_interpreter import SessionDataSectionInterpreterBase
from interpretation.value_types import COLUMN_TYPE_LABELS, ColumnType

BLANK_NAME_PROBLEM: str = "Calculation names must not be blank."


class _Problem(Exception):
  """A reference problem, raised to stop checking one reference."""


# ----- Shared reference checks -----

def _section(interpreters: list[SessionDataSectionInterpreterBase], name: str) -> SessionDataSectionInterpreterBase:
  """The section with this name, or raise the problem with it."""
  if not name.strip():
    raise _Problem("choose a section")
  section = find_section(interpreters, name)
  if section is not None:
    return section
  if is_ambiguous(interpreters, name):
    raise _Problem(f'give one of the sections named "{name.strip()}" a title, so it can be told apart')
  raise _Problem(f'there is no section named "{name.strip()}"')


def _table_columns(interpreters: list[SessionDataSectionInterpreterBase], name: str) -> list[TableColumnPart]:
  """The columns of the table section with this name, or raise the problem with it."""
  columns = _section(interpreters, name).analysis_parts().table_columns
  if not columns:
    raise _Problem(f'"{name.strip()}" is not a table')
  return columns


def _column(columns: list[TableColumnPart], section: str, name: str) -> TableColumnPart:
  if not name.strip():
    raise _Problem("choose a column")
  column = find_column(columns, name)
  if column is None:
    raise _Problem(f'the table "{section.strip()}" has no column "{name.strip()}"')
  return column


def _type_label(column: TableColumnPart) -> str:
  label = COLUMN_TYPE_LABELS[column.column_type]
  article = "an" if label[0] in "AEIOU" else "a"
  return f"{article} {label}"


def _number_column(column: TableColumnPart) -> None:
  if column.column_type is ColumnType.TALLY:
    raise _Problem(f'"{column.name}" is a Tally column: measure one of its marks, or its total')
  if column.column_type is ColumnType.BOOLEAN:
    raise _Problem(f'"{column.name}" is a True/False column: count "True" or "False" with a choice count')
  if column.column_type not in NUMBER_COLUMN_TYPES:
    raise _Problem(f'"{column.name}" is {_type_label(column)} column, so it can\'t be summed or averaged')


def _tally_part(column: TableColumnPart, mark: str | None) -> None:
  if column.column_type is not ColumnType.TALLY:
    raise _Problem(f'"{column.name}" is not a Tally column')
  if mark is not None and not any(fold(mark) == fold(existing) for existing in column.tally_marks):
    raise _Problem(f'"{column.name}" has no tally mark "{mark.strip()}"')


def _choice_column(column: TableColumnPart, choice: str) -> None:
  choices = countable_choices(column)
  if choices is None:
    raise _Problem(f'"{column.name}" is not a Choice or True/False column')
  if not any(fold(choice) == fold(existing) for existing in choices):
    raise _Problem(f'"{column.name}" has no choice "{choice.strip()}"')


def _sheet_value(interpreters: list[SessionDataSectionInterpreterBase], section_name: str, value: str) -> None:
  parts = _section(interpreters, section_name).analysis_parts()
  if not value.strip():
    raise _Problem("choose a value")
  if find_sheet_value(parts.sheet_values, value) is not None:
    return
  if find_column(parts.table_columns, value) is not None:
    raise _Problem(f'"{value.strip()}" is a table column, so it is measured over the rows of its table')
  raise _Problem(f'"{section_name.strip()}" has no number "{value.strip()}"')


def _result(analysis: DataSheetAnalysis, layer_number: int, name: str, row_list_of: str | None = None) -> None:
  """
  Check a lower-layer result is used as what it is: a number, or (when row_list_of names
  a table) a Row List over that table.
  """
  if not name.strip():
    raise _Problem("choose a calculation")
  calculation = lower_layer_calculation(analysis, layer_number, name)
  if calculation is None:
    if any(fold(name) == fold(other.name) for _, _, other in analysis.all_calculations()):
      raise _Problem(f'"{name.strip()}" is not a calculation in a lower layer')
    raise _Problem(f'there is no calculation "{name.strip()}"')
  section = calculation.row_list_section
  if row_list_of is None and section is not None:
    raise _Problem(f'"{name.strip()}" has a value for each row of "{section.strip()}", '
                   "so it can only be summed or averaged over those rows")
  if row_list_of is not None and section is None:
    raise _Problem(f'"{name.strip()}" is a single number, not a value for each row')
  if row_list_of is not None and section is not None and fold(section) != fold(row_list_of):
    raise _Problem(f'"{name.strip()}" has a value for each row of "{section.strip()}", '
                   f'not of "{row_list_of.strip()}"')


def _capitalized(message: str) -> str:
  return message[:1].upper() + message[1:]


# ----- Menu calculations -----

def _aggregate_problems(
  aggregate: RowAggregate,
  interpreters: list[SessionDataSectionInterpreterBase],
  analysis: DataSheetAnalysis,
  layer_number: int,
) -> list[str]:
  try:
    if not aggregate.section.strip():
      raise _Problem("choose a table")
    columns = _table_columns(interpreters, aggregate.section)
  except _Problem as e:
    return [str(e)]

  problems: list[str] = []
  measure = aggregate.measure
  try:
    if isinstance(measure, NumberColumnMeasure):
      _number_column(_column(columns, aggregate.section, measure.column))
    elif isinstance(measure, TallyCountMeasure):
      _tally_part(_column(columns, aggregate.section, measure.column), measure.mark)
    elif isinstance(measure, RowResultMeasure):
      _result(analysis, layer_number, measure.calculation, row_list_of=aggregate.section)
    else:
      if not measure.choice.strip():
        raise _Problem("choose the choice to count")
      if not measure.columns:
        raise _Problem("choose at least one Choice column")
  except _Problem as e:
    return [str(e)]

  if isinstance(measure, ChoiceCountMeasure):
    seen: set[str] = set()
    for name in measure.columns:
      if fold(name) in seen:
        problems.append(f'the column "{name.strip()}" is chosen more than once')
        continue
      seen.add(fold(name))
      try:
        _choice_column(_column(columns, aggregate.section, name), measure.choice)
      except _Problem as e:
        problems.append(str(e))
  return problems


def _operand_problems(
  operand: Operand,
  interpreters: list[SessionDataSectionInterpreterBase],
  analysis: DataSheetAnalysis,
  layer_number: int,
) -> list[str]:
  try:
    if isinstance(operand, ResultOperand):
      _result(analysis, layer_number, operand.calculation)
    elif isinstance(operand, SheetValueOperand):
      _sheet_value(interpreters, operand.section, operand.value)
    elif not operand.number.is_finite():
      raise _Problem("type a number, such as 100 or 2.5")
  except _Problem as e:
    return [str(e)]
  return []


# ----- Formulas -----

def formula_problems(
  text: str,
  interpreters: list[SessionDataSectionInterpreterBase],
  analysis: DataSheetAnalysis,
  layer_number: int,
) -> list[FormulaProblem]:
  """
  Every problem with a formula for a calculation in this layer: its syntax problem, if
  any, or else every reference problem in text order (an unknown, ambiguous, or
  out-of-layer name, the wrong type, columns from two tables in one aggregation, or a
  choice a column doesn't offer). [] when the formula can be used.
  """
  parse = parse_formula(text)
  if parse.problem is not None:
    return [parse.problem]

  problems: list[FormulaProblem] = []
  table_by_aggregate: dict[int, str] = {}
  for reference in parse.references:
    try:
      _check_reference(reference, interpreters, analysis, layer_number, table_by_aggregate)
    except _Problem as e:
      problems.append(FormulaProblem(_capitalized(str(e)), reference.start, reference.end))
  return problems


def _check_reference(
  reference: FormulaReference,
  interpreters: list[SessionDataSectionInterpreterBase],
  analysis: DataSheetAnalysis,
  layer_number: int,
  table_by_aggregate: dict[int, str],
) -> None:
  if reference.kind is ReferenceKind.RESULT:
    if reference.aggregate_start < 0:
      _result(analysis, layer_number, reference.parts[0])
      return
    # A Row List measured by SUM or AVERAGE: over the table its own calculation measured
    calculation = lower_layer_calculation(analysis, layer_number, reference.parts[0])
    table = calculation.row_list_section if calculation is not None else None
    _result(analysis, layer_number, reference.parts[0], row_list_of=table or "")
    return
  section = reference.parts[0]
  if reference.kind is ReferenceKind.SHEET_VALUE:
    _sheet_value(interpreters, section, reference.parts[1])
    return

  columns = _table_columns(interpreters, section)
  first_table = table_by_aggregate.setdefault(reference.aggregate_start, fold(section))
  if first_table != fold(section):
    raise _Problem("every column in one SUM or AVERAGE must come from the same table")
  column = _column(columns, section, reference.parts[1])
  if reference.choice is not None:
    _choice_column(column, reference.choice)
  elif len(reference.parts) == 3:
    part = reference.parts[2]
    _tally_part(column, None if fold(part) == fold(TALLY_TOTAL_PART) else part)
  else:
    _number_column(column)


# ----- Calculations and the whole analysis -----

def _reference_problems(
  calculation: Calculation,
  interpreters: list[SessionDataSectionInterpreterBase],
  analysis: DataSheetAnalysis,
  layer_number: int,
) -> list[str]:
  """Problems with what a calculation refers to, each starting with its name."""
  definition = calculation.definition
  if isinstance(definition, RowAggregate):
    problems = _aggregate_problems(definition, interpreters, analysis, layer_number)
  elif isinstance(definition, Arithmetic):
    problems = (_operand_problems(definition.left, interpreters, analysis, layer_number)
                + _operand_problems(definition.right, interpreters, analysis, layer_number))
  else:
    problems = [
      f"{problem.message} (at character {problem.start + 1})"
      for problem in formula_problems(definition.text, interpreters, analysis, layer_number)
    ]
  return [f'Calculation "{calculation.name.strip()}": {problem}' for problem in problems]


def calculation_problems(
  calculation: Calculation,
  interpreters: list[SessionDataSectionInterpreterBase],
  analysis: DataSheetAnalysis,
  layer_number: int,
  index: int | None,
) -> list[str]:
  """
  Every problem with one calculation as it would be applied in this layer, at this index
  (None when it is being added). [] when it can be applied.
  """
  problems: list[str] = []
  if not calculation.name.strip():
    problems.append(BLANK_NAME_PROBLEM)
  elif any(
    fold(other.name) == fold(calculation.name) and (number, other_index) != (layer_number, index)
    for number, other_index, other in analysis.all_calculations()
  ):
    problems.append(f'Two calculations are named "{calculation.name.strip()}".')
  return problems + _reference_problems(calculation, interpreters, analysis, layer_number)


def analysis_problems(
  interpreters: list[SessionDataSectionInterpreterBase],
  analysis: DataSheetAnalysis,
) -> list[str]:
  """Every problem that stops the template from being saved, in layer then calculation order."""
  problems: list[str] = []
  seen: set[str] = set()
  reported: set[str] = set()
  for layer_number, _, calculation in analysis.all_calculations():
    name = fold(calculation.name)
    if not name:
      if BLANK_NAME_PROBLEM not in problems:
        problems.append(BLANK_NAME_PROBLEM)
    elif name in seen and name not in reported:
      problems.append(f'Two calculations are named "{calculation.name.strip()}".')
      reported.add(name)
    seen.add(name)
    problems.extend(_reference_problems(calculation, interpreters, analysis, layer_number))
  return problems


def calculations_using(analysis: DataSheetAnalysis, calculation_name: str) -> list[str]:
  """The names of the calculations whose definitions use this calculation's result."""
  return [
    calculation.name
    for _, _, calculation in analysis.all_calculations()
    if any(fold(name) == fold(calculation_name) for name in calculation.result_references())
  ]


# ----- Plain language -----

_OPERATION_WORDS: dict[ArithmeticOperation, str] = {
  ArithmeticOperation.ADD: "plus",
  ArithmeticOperation.SUBTRACT: "minus",
  ArithmeticOperation.MULTIPLY: "times",
  ArithmeticOperation.DIVIDE: "divided by",
}


def describe_operand(operand: Operand) -> str:
  """An Arithmetic input in plain language."""
  if isinstance(operand, ResultOperand):
    return operand.calculation
  if isinstance(operand, SheetValueOperand):
    return f"{operand.section} › {operand.value}"
  return str(operand.number)


def describe_calculation(calculation: Calculation) -> str:
  """What a calculation works out, in plain language for view mode. A formula is shown as typed."""
  definition = calculation.definition
  if isinstance(definition, Formula):
    return definition.text
  if isinstance(definition, Arithmetic):
    left, right = describe_operand(definition.left), describe_operand(definition.right)
    if definition.operation is ArithmeticOperation.PERCENTAGE:
      return f"{left} as a percentage of {right}"
    return f"{left} {_OPERATION_WORDS[definition.operation]} {right}"

  measure = definition.measure
  if (isinstance(measure, ChoiceCountMeasure) and len(measure.columns) == 1
      and definition.combination is Combination.SUM):
    return f'Number of rows of {definition.section} where {measure.columns[0]} is "{measure.choice}"'
  if isinstance(measure, NumberColumnMeasure):
    what = measure.column
  elif isinstance(measure, TallyCountMeasure):
    what = f"{measure.column} total" if measure.mark is None else f"{measure.column} {measure.mark} count"
  elif isinstance(measure, RowResultMeasure):
    what = measure.calculation
  else:
    what = f'count of "{measure.choice}" in {", ".join(measure.columns)}'
  if definition.combination is Combination.EACH_ROW:
    return f"For each row of {definition.section}: {what}"
  return f"{definition.combination.value} over rows of {definition.section}: {what}"
