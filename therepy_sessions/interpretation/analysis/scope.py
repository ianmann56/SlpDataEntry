"""
The Analysis Scope: what one calculation in one layer may use.

The menu's choices, the Formula Legend, and every check read this one module, so they
can't disagree. Sections describe themselves through `analysis_parts()`; nothing here
checks interpreter types.
"""

from typing import NamedTuple

from interpretation.analysis.formula import escape_name
from interpretation.analysis.model import DataSheetAnalysis
from interpretation.analysis.parts import TableColumnPart
from interpretation.templates.student_data_sheet_interpreter import SessionDataSectionInterpreterBase
from interpretation.value_types import ColumnType

# The column types whose value is a number a Row Measure can read
NUMBER_COLUMN_TYPES: tuple[ColumnType, ...] = (ColumnType.INT, ColumnType.DECIMAL)

# How a formula names a tally's total, after its section and column
TALLY_TOTAL_PART: str = "Total"


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
    choice_columns: Each Choice column with its choices and its entry.
  """
  section: str
  number_columns: list[ScopeEntry]
  tally_columns: list[tuple[str, list[ScopeEntry]]]
  choice_columns: list[tuple[str, list[str], ScopeEntry]]


class AnalysisScope(NamedTuple):
  """
  What one calculation may use.

  Properties:
    sheet_values: The Numeric Sheet Values of every section that can be told apart.
    tables: The table sections that have a column a Row Measure can read.
    results: The results of every calculation in a lower layer, in order.
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


def result_reference(name: str) -> str:
  """How a formula writes a calculation's result."""
  return f"{{{escape_name(name)}}}"


def sheet_reference(*parts: str) -> str:
  """How a formula writes a sheet value or a table column."""
  return "[" + "/".join(escape_name(part) for part in parts) + "]"


def _scope_table(section: str, columns: list[TableColumnPart]) -> ScopeTable | None:
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
    elif column.column_type is ColumnType.CHOICE:
      entry = ScopeEntry(column.name, sheet_reference(section, column.name), "")
      choice_columns.append((column.name, list(column.choices), entry))
  if not (number_columns or tally_columns or choice_columns):
    return None
  return ScopeTable(section, number_columns, tally_columns, choice_columns)


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
      table = _scope_table(section, parts.table_columns)
      if table is not None:
        tables.append(table)

  results = [
    ScopeEntry(calculation.name, result_reference(calculation.name), calculation.description)
    for number, _, calculation in analysis.all_calculations()
    if number < layer_number
  ]
  return AnalysisScope(sheet_values, tables, results)
