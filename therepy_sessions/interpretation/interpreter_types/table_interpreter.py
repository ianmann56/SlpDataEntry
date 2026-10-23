from typing import Any

from interpretation.analysis.parts import SectionParts, TableColumnPart
from interpretation.templates.student_data_sheet_interpreter import DataSheetInterpretationDto, SessionDataSectionInterpreterBase
from interpretation.student_data_sheet import DataSheetScalarDto, DataSheetTable
from interpretation.template_manager.option_rules import name_problems, option_problems, tally_key_collisions
from interpretation.value_types import (
  ChoiceOption,
  ColumnType,
  OptionDescription,
  TallyOption,
  ValueProblem,
  read_tally,
  read_value_leniently,
  scalar_type_for,
  tally_keys,
  tally_scalars,
  unknown_marks_phrase,
)
from collection.collection_headers import StudentDataSheetImport

# The section name used in messages and the Workbook Key when a table section has no title
_FALLBACK_SECTION_NAME: str = "Table"

class ColumnDefinition:
  """
  One column of a table section, with its Column Type.

  Properties:
    column_name: The column's header on the sheet.
    column_type: How its cells are read.
    choices: The choices of a Choice column. Empty otherwise.
    tally_options: The tally options of a Tally column. Empty otherwise.
  """

  def __init__(
    self,
    column_name: str,
    column_type: ColumnType = ColumnType.TEXT,
    choices: list[ChoiceOption] | None = None,
    tally_options: list[TallyOption] | None = None,
  ) -> None:
    self._column_name = column_name
    self._column_type = column_type
    # Copied per instance so columns never share option lists
    self._choices: list[ChoiceOption] = list(choices or [])
    self._tally_options: list[TallyOption] = list(tally_options or [])

  @property
  def column_name(self) -> str:
    return self._column_name

  @property
  def column_type(self) -> ColumnType:
    return self._column_type

  @property
  def choices(self) -> list[ChoiceOption]:
    return self._choices

  @property
  def tally_options(self) -> list[TallyOption]:
    return self._tally_options

  @property
  def column_choices(self) -> list[str]:
    """The choice values, in order."""
    return [choice.value for choice in self._choices]

  def to_json(self) -> dict[str, Any]:
    """The column as saved: its name, its type's member name, and its options (choices or tally marks)."""
    if self._column_type is ColumnType.CHOICE:
      options = [{"value": choice.value, "description": choice.description} for choice in self._choices]
    elif self._column_type is ColumnType.TALLY:
      options = [{"value": option.mark, "description": option.description} for option in self._tally_options]
    else:
      options = []
    return {
      "column_name": self._column_name,
      "column_type": self._column_type.name,
      "options": options,
    }

class TableInterpreter(SessionDataSectionInterpreterBase):
  """
  Template implementation for data sheets containing tables with specific column structures.

  This assumes that all tables in the data sheet have the same structure. If you have
  multiple different tables, this will not work for that data sheet.

  Purpose: Handles data sheets where the tabular data follows a predictable column-based
  format. Validates that tables contain expected columns and structures the data as
  dictionaries keyed by column names. Each cell is read as its column's type; a Tally
  column's cell becomes its Tally Summary.

  Use case: Therapy session data sheets with consistent column layouts like 'Word',
  'Times w/Prompting', 'Times w/o Prompting', etc.
  """
  def __init__(self, id: str, title: str, columns: list[ColumnDefinition]) -> None:
    """
    Initializes the template with expected column names for table processing.

    Purpose: Sets up the template to work with tables that have specific column
    structures, allowing validation and proper data extraction based on column names.

    :param id: The unique id identifying this specific interpreter instance within a template.
    :param title: The user-facing title identifying this interpreter within a template.
    :param columns: List of expected column definitons that should be present in data sheet tables
    """
    super().__init__(id, title)
    self._columns: list[ColumnDefinition] = columns

  @property
  def columns(self) -> list[ColumnDefinition]:
    """
    Get the list of expected column definitions.

    Returns:
        list: List of column definitions
    """
    return self._columns

  @property
  def fallback_section_name(self) -> str:
    """The name this section goes by when it has no title."""
    return _FALLBACK_SECTION_NAME

  @property
  def consumes_tables(self) -> bool:
    """
    A table section reads the tables on the sheet.
    """
    return True

  def section_keys(self) -> list[str]:
    """
    The column names, in template order. A Tally column contributes its Tally Summary
    keys (tally_keys) instead, so its tally options are part of the Template Structure.
    """
    keys: list[str] = []
    for column in self._columns:
      if column.column_type is ColumnType.TALLY:
        keys.extend(tally_keys(column.column_name, column.tally_options))
      else:
        keys.append(column.column_name)
    return keys

  def config_problems(self) -> list[str]:
    """
    Blank or repeated column names, Choice and Tally columns with missing, blank,
    repeated, or (for tallies) too-long options, and Tally summary keys that clash with
    another column's name.
    """
    problems = name_problems("column", [column.column_name for column in self._columns])
    for column in self._columns:
      if column.column_type is ColumnType.CHOICE:
        problems.extend(option_problems(column.column_name, ColumnType.CHOICE, column.column_choices))
      elif column.column_type is ColumnType.TALLY:
        problems.extend(option_problems(column.column_name, ColumnType.TALLY, [o.mark for o in column.tally_options]))
    problems.extend(tally_key_collisions(self._columns))
    return problems

  def analysis_parts(self) -> SectionParts:
    """Every column, in order, with its type, choices, and tally marks."""
    return SectionParts(
      [
        TableColumnPart(
          column.column_name,
          column.column_type,
          column.column_choices,
          [option.mark for option in column.tally_options],
        )
        for column in self._columns
      ],
      [],
    )

  def option_descriptions(self) -> list[OptionDescription]:
    """Every Choice and Tally column's options, in column order then option order."""
    section = self.section_name
    descriptions: list[OptionDescription] = []
    for column in self._columns:
      if column.column_type is ColumnType.CHOICE:
        descriptions.extend(
          OptionDescription(section, column.column_name, "Choice", choice.value, choice.description)
          for choice in column.choices
        )
      elif column.column_type is ColumnType.TALLY:
        descriptions.extend(
          OptionDescription(section, column.column_name, "Tally", option.mark, option.description)
          for option in column.tally_options
        )
    return descriptions

  def interpret_student_data_sheet_content(self, data_sheet_content: StudentDataSheetImport) -> DataSheetInterpretationDto:
    """
    Processes multiple tables from the data sheet using column-based interpretation.

    This assumes that all tables in the data sheet have the same structure. If you have
    multiple different tables, this will not work for that data sheet.

    Purpose: Implements the abstract method from the base class to handle tables
    by applying column-based processing to each table individually.

    :param data_sheet_content: A dictionary with 2 properties:
      tables: List of 2D arrays representing tables from the data sheet
      form_data: A list of key value pairs where the key is the field name and the
                 value is the value name.
    :return: a DataSheetInterpretationDto representing the interpreted data. Every cell
      that doesn't fit its column's type is kept as read and listed in its value_problems.
    """
    problems: list[ValueProblem] = []
    several_tables = len(data_sheet_content.tables) > 1
    tables = [
      self._interpret_single_student_data_sheet_table(raw_table, table_number if several_tables else None, problems)
      for table_number, raw_table
      in enumerate(data_sheet_content.tables, start=1)
    ]

    return DataSheetInterpretationDto(tables, {}, problems)

  def _interpret_single_student_data_sheet_table(
    self,
    data_sheet_table: list[list[str]],
    table_number: int | None,
    problems: list[ValueProblem],
  ) -> DataSheetTable:
    """
    Processes a single table by mapping data rows to expected column structure.

    Purpose: Validates that the table contains all expected columns, then transforms
    raw table data into structured objects where each row becomes a dictionary
    mapping column names (and Tally Summary keys) to typed scalars.

    :param data_sheet_table: 2D array where first row contains headers and subsequent rows contain data
    :param table_number: The table's number among this section's tables, or None when it has only one
    :param problems: Collects every cell that doesn't fit its column
    :return: Dictionary with 'columns' (expected column list) and 'data' (list of row dictionaries)
    :raises Exception: If any expected column is missing from the table headers
    """
    columns_in_data_sheet = data_sheet_table[0]

    # Checked by column name: a Tally column is one column on paper (FR-013)
    for expected_col in self._columns:
      if expected_col.column_name not in columns_in_data_sheet:
        raise Exception(f"Expected to see column {expected_col.column_name} in data sheet but could not find it. Got columns: {columns_in_data_sheet}")

    col_index_by_col_name = {
      expected_col.column_name: (columns_in_data_sheet.index(expected_col.column_name), expected_col)
      for expected_col
      in self._columns
    }

    section = self.section_name
    data: list[dict[str, DataSheetScalarDto]] = []

    for row_number, row_data in enumerate(data_sheet_table[1:], start=1):
      row = f"table {table_number}, row {row_number}" if table_number is not None else f"row {row_number}"
      row_dto: dict[str, DataSheetScalarDto] = {}
      for column_name, (column_index, column_def) in col_index_by_col_name.items():
        # OCR can leave out trailing empty cells, so a cell past the end of a short row is blank
        cell_text = row_data[column_index] if column_index < len(row_data) else ""
        if column_def.column_type is ColumnType.TALLY:
          summary = read_tally(cell_text, column_def.tally_options)
          if summary.unknown_marks:
            # The whole cell is named, so the SLP can find it; the unknown marks are named too
            expected = unknown_marks_phrase(column_def.tally_options, summary.unknown_marks)
            problems.append(ValueProblem(section, column_name, row, cell_text, expected))
          row_dto.update(tally_scalars(column_name, summary, column_def.tally_options))
          continue
        # A cell that doesn't fit keeps its text, with no typed value, so nothing written is lost
        reading = read_value_leniently(column_def.column_type, cell_text, column_def.choices)
        if reading.expected:
          problems.append(ValueProblem(section, column_name, row, cell_text, reading.expected, saved_as=reading.saved_as))
        row_dto[column_name] = DataSheetScalarDto(
          column_name,
          cell_text,
          scalar_type_for(column_def.column_type),
          column_def.column_choices or None,
          reading.typed_value,
        )

      data.append(row_dto)

    return {
      "columns": self._columns,
      "data": data
    }
