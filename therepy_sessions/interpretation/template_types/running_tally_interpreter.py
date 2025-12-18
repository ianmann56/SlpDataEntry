from functools import reduce
from interpretation.student_data_sheet_interpreter import DataSheetInterpretationDto, SessionDataSectionInterpreterBase
from interpretation.student_data_sheet import DataSheetScalarDto, DataSheetScalarType


class RunningTallyInterpreter(SessionDataSectionInterpreterBase):
  """
  Template implementation for data sheets containing a grid of tallys. Each tally could
  be an int, a choice or a boolean.

  This assumes that all tables in the data sheet are running tallys. If you have
  multiple different tables, this will not work for that data sheet.

  Purpose: Handles data sheets where the tabular data is a list of instances that are
  annotated as they happen (like in Yes, No or Prompted).

  Use case: Therapy session data sheets where a tally was tracked keeping track of how many
  times in the session the student did a particular thing (using yes, no or prompted for
  example).
  """

  # The type that each tally can be interpreted as.
  _tally_type = None

  # The options that each tally could be. This is only applicable if the _tally_type is CHOICE.
  _tally_choice_options = None

  def __init__(self, tally_type, tally_choice_options):
    super().__init__()
    self._tally_type = tally_type
    self._tally_choice_options = tally_choice_options

  def interpret_student_data_sheet_content(self, data_sheet_content):
    """
    Processes multiple tables from the data sheet using column-based interpretation.

    This assumes that all tables in the data sheet are running tallys. If you have
    multiple different tables, this will not work for that data sheet.

    Purpose: Implements the abstract method from the base class to handle tables
    as if they were just a single running list of instances with a tally in each box.

    :param data_sheet_content: A dictionary with 2 properties:
      tables: List of 2D arrays representing tables from the data sheet
      form_data: A list of key value pairs where the key is the field name and the
                 value is the value name.
    """
    tables = [
      self._interpret_single_student_data_sheet_table(raw_table)
      for raw_table
      in data_sheet_content.tables
    ]

    return DataSheetInterpretationDto(tables, {})

  def _interpret_single_student_data_sheet_table(self, data_sheet_table):
    print(data_sheet_table)

    tally_string = ''
    for row in data_sheet_table:
      letters_string = reduce(lambda acc, s: acc + s, row, '')
      tally_string = tally_string + letters_string

    tally_column_name = 'Tally'

    tally_as_rows = [
      { tally_column_name: DataSheetScalarDto(tally_column_name, letter, self._tally_type, self._tally_choice_options) }
      for letter
      in tally_string
    ]

    return {
      "columns": [tally_column_name],
      "data": tally_as_rows
    }