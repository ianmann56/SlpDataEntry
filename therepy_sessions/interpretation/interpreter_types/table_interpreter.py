import ipdb

from interpretation.templates.student_data_sheet_interpreter import DataSheetInterpretationDto, SessionDataSectionInterpreterBase
from interpretation.student_data_sheet import DataSheetScalarDto, DataSheetScalarType
from collection.collection_headers import StudentDataSheetImport

class ColumnDefinition:
  column_name: str
  column_choices: list[str]

  def __init__(self, column_name: str, column_choices: list[str]):
    self.column_name = column_name
    self.column_choices = column_choices

  def to_json(self):
    return {
      "column_name": self.column_name,
      "column_choices": self.column_choices
    }

class TableInterpreter(SessionDataSectionInterpreterBase):
  """
  Template implementation for data sheets containing tables with specific column structures.

  This assumes that all tables in the data sheet have the same structure. If you have
  multiple different tables, this will not work for that data sheet.

  Purpose: Handles data sheets where the tabular data follows a predictable column-based
  format. Validates that tables contain expected columns and structures the data as
  dictionaries keyed by column names.

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
    Get the list of expected column names.
    
    Returns:
        list: List of column names
    """
    return self._columns

  @property
  def consumes_tables(self) -> bool:
    """
    A table section reads the tables on the sheet.
    """
    return True

  def section_keys(self) -> list[str]:
    """
    The column names, in template order.
    """
    return [column.column_name for column in self._columns]

  def interpret_student_data_sheet_content(self, data_sheet_content: StudentDataSheetImport):
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
    :return: a DataSheetInterpretationDto representing the interpreted data
    """
    tables = [
      self._interpret_single_student_data_sheet_table(raw_table)
      for raw_table
      in data_sheet_content.tables
    ]

    return DataSheetInterpretationDto(tables, {})

  def _interpret_single_student_data_sheet_table(self, data_sheet_table: list[list[str]]):
    """
    Processes a single table by mapping data rows to expected column structure.

    Purpose: Validates that the table contains all expected columns, then transforms
    raw table data into structured objects where each row becomes a dictionary
    mapping column names to cell values.

    :param data_sheet_table: 2D array where first row contains headers and subsequent rows contain data
    :return: Dictionary with 'columns' (expected column list) and 'data' (list of row dictionaries)
    :raises Exception: If any expected column is missing from the table headers
    """    
    columns_in_data_sheet = data_sheet_table[0]

    for expected_col in self._columns:
      if expected_col.column_name not in columns_in_data_sheet:
        raise Exception(f"Expected to see column {expected_col.column_name} in data sheet but could not find it. Got columns: {columns_in_data_sheet}")

    col_index_by_col_name = {
      expected_col.column_name: (columns_in_data_sheet.index(expected_col.column_name), expected_col)
      for expected_col
      in self._columns
    }

    data = []

    for row_data in data_sheet_table[1:]:
      row_dto = {}
      for column_name, (column_index, column_def) in col_index_by_col_name.items():
        column_choices = column_def.column_choices
        cell_data = row_data[column_index]
        cell_data_dto = DataSheetScalarDto(column_name, cell_data, DataSheetScalarType.TEXT, column_choices)
        row_dto[column_name] = cell_data_dto

      data.append(row_dto)

    return {
      "columns": self._columns,
      "data": data
    }