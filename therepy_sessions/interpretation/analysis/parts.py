"""
What a section offers to Data Sheet Analysis.

Each interpreter type describes itself with `analysis_parts()`, so the analysis code
never checks interpreter types (Principle V). This module imports only `value_types`,
so the interpreter base class can use it without an import cycle.
"""

from typing import NamedTuple

from interpretation.value_types import ColumnType


class TableColumnPart(NamedTuple):
  """
  One column of a table section, as analysis sees it.

  Properties:
    name: The column's name.
    column_type: Its Column Type, which decides which Row Measures it can give.
    choices: The choice values of a Choice column, in order. Empty otherwise.
    tally_marks: The tally marks of a Tally column, in order. Empty otherwise.
  """
  name: str
  column_type: ColumnType
  choices: list[str]
  tally_marks: list[str]


class SectionParts(NamedTuple):
  """
  What one section offers to analysis.

  Properties:
    table_columns: A table section's columns, in template order. Empty for other sections.
    sheet_values: The names of the section's Numeric Sheet Values (single numbers a
      calculation can use directly), in template order.
  """
  table_columns: list[TableColumnPart]
  sheet_values: list[str]

  @classmethod
  def none(cls) -> "SectionParts":
    """A section that offers nothing to analysis."""
    return cls([], [])
