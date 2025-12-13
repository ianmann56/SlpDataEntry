from interpretation.student_data_sheet_interpreter import DataSheetInterpretationDto, SessionDataInterpreterBase
from interpretation.student_data_sheet import DataSheetScalarDto, DataSheetScalarType

class TableInterpreter(SessionDataInterpreterBase):
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
  _columns = []

  def __init__(self, columns):
    """
    Initializes the template with expected column names for table processing.

    Purpose: Sets up the template to work with tables that have specific column
    structures, allowing validation and proper data extraction based on column names.

    :param columns: List of expected column names that should be present in data sheet tables
    """
    super().__init__()
    self._columns = columns

  def interpret_student_data_sheet_content(self, data_sheet_content):
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

  def _interpret_single_student_data_sheet_table(self, data_sheet_table):
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
      if expected_col not in columns_in_data_sheet:
        raise Exception(f"Expected to see column {expected_col} in data sheet but could not find it. Got columns: {columns_in_data_sheet}")

    col_index_by_col_name = {
      expected_col: columns_in_data_sheet.index(expected_col)
      for expected_col
      in self._columns
    }

    data = []

    for row_data in data_sheet_table[1:]:
      row_dto = {}
      for column_name, column_index in col_index_by_col_name.items():
        cell_data = row_data[column_index]
        cell_data_dto = DataSheetScalarDto(column_name, cell_data, DataSheetScalarType.TEXT)
        row_dto[column_name] = cell_data_dto

      data.append(row_dto)

    return {
      "columns": self._columns,
      "data": data
    }