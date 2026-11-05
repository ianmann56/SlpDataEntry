"""
The Analysis Scope: what one calculation in one layer may use.

The menu's choices, the Formula Legend, and every check read this one module, so they
can't disagree. Sections describe themselves through `analysis_parts()`; nothing here
checks interpreter types.
"""

from typing import NamedTuple

from interpretation.analysis.formula import escape_name
from interpretation.analysis.model import (
  Calculation,
  DataSheetAnalysis,
  NumberColumnMeasure,
  RowResultMeasure,
  TallyCountMeasure,
)
from interpretation.analysis.parts import TableColumnPart
from interpretation.templates.student_data_sheet_interpreter import SessionDataSectionInterpreterBase
from interpretation.value_types import ColumnType

# The column types whose value is a number a Row Measure can read
NUMBER_COLUMN_TYPES: tuple[ColumnType, ...] = (ColumnType.INT, ColumnType.DECIMAL)

# How a formula names a tally's total, after its section and column
TALLY_TOTAL_PART: str = "Total"

# The choices a True/False column offers to a choice count
BOOLEAN_CHOICES: tuple[str, ...] = ("True", "False")


def fold(name: str) -> str:
  """A name as compared: ignoring letter case and surrounding spaces."""
  return name.strip().casefold()


class ScopeEntry(NamedTuple):
  """
  One thing a calculation may use.

  Properties:
    label: How the menu and the Formula Legend show it.
    reference: Exactly how a formula writes it, escaped.
    description: The Calculation Description of a result, or "" for sheet data.
  """
  label: str
  reference: str
  description: str


class ScopeTable(NamedTuple):
  """
  A table section a Row Aggregate can measure, with the columns it can read.

  Properties:
    section: The table's Section Name.
    number_columns: Its Integer and Decimal columns.
    tally_columns: Each Tally column with its entries: one per mark, then the total.
    choice_columns: Each Choice or True/False column with its choices and its entry.
    row_results: The Row Lists of lower-layer calculations over this table, in order.
  """
  section: str
  number_columns: list[ScopeEntry]
  tally_columns: list[tuple[str, list[ScopeEntry]]]
  choice_columns: list[tuple[str, list[str], ScopeEntry]]
  row_results: list[ScopeEntry]


class AnalysisScope(NamedTuple):
  """
  What one calculation may use.

  Properties:
    sheet_values: The Numeric Sheet Values of every section that can be told apart.
    tables: The table sections that have a column or Row List a Row Measure can read.
    results: The single-number results of every calculation in a lower layer, in order.
      Row Lists are not here: they are listed with their table.
  """
  sheet_values: list[ScopeEntry]
  tables: list[ScopeTable]
  results: list[ScopeEntry]


def section_name_counts(interpreters: list[SessionDataSectionInterpreterBase]) -> dict[str, int]:
  """How many sections use each Section Name, keyed by the folded name."""
  counts: dict[str, int] = {}
  for interpreter in interpreters:
    key = fold(interpreter.section_name)
    counts[key] = counts.get(key, 0) + 1
  return counts


def is_ambiguous(interpreters: list[SessionDataSectionInterpreterBase], name: str) -> bool:
  """Whether more than one section uses this Section Name, so analysis can't tell them apart."""
  return section_name_counts(interpreters).get(fold(name), 0) > 1


def find_section(
  interpreters: list[SessionDataSectionInterpreterBase],
  name: str,
) -> SessionDataSectionInterpreterBase | None:
  """The one section with this Section Name, or None when there is none or more than one."""
  matches = [interpreter for interpreter in interpreters if fold(interpreter.section_name) == fold(name)]
  return matches[0] if len(matches) == 1 else None


def find_column(columns: list[TableColumnPart], name: str) -> TableColumnPart | None:
  """The table column with this name, or None."""
  return next((column for column in columns if fold(column.name) == fold(name)), None)


def countable_choices(column: TableColumnPart) -> list[str] | None:
  """The choices a choice count can count in this column, or None when it is not a Choice or True/False column."""
  if column.column_type is ColumnType.CHOICE:
    return list(column.choices)
  if column.column_type is ColumnType.BOOLEAN:
    return list(BOOLEAN_CHOICES)
  return None


def find_sheet_value(sheet_values: list[str], name: str) -> str | None:
  """The Numeric Sheet Value with this name, as configured, or None."""
  return next((value for value in sheet_values if fold(value) == fold(name)), None)


def lower_layer_names(analysis: DataSheetAnalysis, layer_number: int) -> list[str]:
  """The names of every calculation in layers 1 to layer_number - 1, in order."""
  return [
    calculation.name
    for number, _, calculation in analysis.all_calculations()
    if number < layer_number
  ]


def lower_layer_calculation(analysis: DataSheetAnalysis, layer_number: int, name: str) -> Calculation | None:
  """The calculation in layers 1 to layer_number - 1 with this name, or None."""
  return next(
    (calculation for number, _, calculation in analysis.all_calculations()
     if number < layer_number and fold(calculation.name) == fold(name)),
    None,
  )


def result_reference(name: str) -> str:
  """How a formula writes a calculation's result."""
  return f"{{{escape_name(name)}}}"


def sheet_reference(*parts: str) -> str:
  """How a formula writes a sheet value or a table column."""
  return "[" + "/".join(escape_name(part) for part in parts) + "]"


def _scope_table(section: str, columns: list[TableColumnPart], row_results: list[ScopeEntry]) -> ScopeTable | None:
  number_columns: list[ScopeEntry] = []
  tally_columns: list[tuple[str, list[ScopeEntry]]] = []
  choice_columns: list[tuple[str, list[str], ScopeEntry]] = []
  for column in columns:
    if column.column_type in NUMBER_COLUMN_TYPES:
      number_columns.append(ScopeEntry(column.name, sheet_reference(section, column.name), ""))
    elif column.column_type is ColumnType.TALLY:
      entries = [
        ScopeEntry(f"{column.name} › {part}", sheet_reference(section, column.name, part), "")
        for part in [*column.tally_marks, TALLY_TOTAL_PART]
      ]
      tally_columns.append((column.name, entries))
    elif (choices := countable_choices(column)) is not None:
      entry = ScopeEntry(column.name, sheet_reference(section, column.name), "")
      choice_columns.append((column.name, choices, entry))
  if not (number_columns or tally_columns or choice_columns or row_results):
    return None
  return ScopeTable(section, number_columns, tally_columns, choice_columns, row_results)


def analysis_scope(
  interpreters: list[SessionDataSectionInterpreterBase],
  analysis: DataSheetAnalysis,
  layer_number: int,
) -> AnalysisScope:
  """
  What a calculation in this layer may use. Sections whose Section Name another section
  shares are left out, because a name can't tell them apart.
  """
  counts = section_name_counts(interpreters)
  lower = [calculation for number, _, calculation in analysis.all_calculations() if number < layer_number]
  results = [
    ScopeEntry(calculation.name, result_reference(calculation.name), calculation.description)
    for calculation in lower
    if calculation.row_list_section is None
  ]
  sheet_values: list[ScopeEntry] = []
  tables: list[ScopeTable] = []
  for interpreter in interpreters:
    section = interpreter.section_name
    if counts[fold(section)] > 1:
      continue
    parts = interpreter.analysis_parts()
    sheet_values.extend(
      ScopeEntry(f"{section} › {value}", sheet_reference(section, value), "")
      for value in parts.sheet_values
    )
    if parts.table_columns:
      row_results = [
        ScopeEntry(calculation.name, result_reference(calculation.name), calculation.description)
        for calculation in lower
        if calculation.row_list_section is not None and fold(calculation.row_list_section) == fold(section)
      ]
      table = _scope_table(section, parts.table_columns, row_results)
      if table is not None:
        tables.append(table)
  return AnalysisScope(sheet_values, tables, results)


def row_value_sides(table: ScopeTable) -> list[NumberColumnMeasure | TallyCountMeasure | RowResultMeasure]:
  """Every value a row of this table has that a comparison can compare: its number columns, tally parts, and Row Lists."""
  sides: list[NumberColumnMeasure | TallyCountMeasure | RowResultMeasure] = [
    NumberColumnMeasure(entry.label) for entry in table.number_columns
  ]
  for column, entries in table.tally_columns:
    for entry in entries:
      part = entry.label.split(" › ")[-1]
      sides.append(TallyCountMeasure(column, None if fold(part) == fold(TALLY_TOTAL_PART) else part))
  sides.extend(RowResultMeasure(entry.label) for entry in table.row_results)
  return sides
