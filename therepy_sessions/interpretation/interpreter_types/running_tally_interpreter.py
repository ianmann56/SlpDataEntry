from interpretation.templates.student_data_sheet_interpreter import DataSheetInterpretationDto, SessionDataSectionInterpreterBase
from interpretation.student_data_sheet import DataSheetScalarDto, DataSheetTable
from interpretation.template_manager.option_rules import option_problems
from interpretation.value_types import (
  ColumnType,
  OptionDescription,
  TallyOption,
  ValueProblem,
  read_tally,
  tally_keys,
  tally_scalars,
  unknown_mark_phrase,
)
from collection.collection_headers import StudentDataSheetImport

# The base of the Tally Summary keys a running tally emits, e.g. "Tally", "Tally Y", "Tally Total"
TALLY_COLUMN_NAME: str = 'Tally'

# The section name used in messages and the Workbook Key when a running tally has no title
_FALLBACK_SECTION_NAME: str = "Running Tally"

class RunningTallyInterpreter(SessionDataSectionInterpreterBase):
  """
  Template implementation for data sheets containing a grid of tally marks, each one
  character, written as things happen (like Y, N, or P for yes, no, or prompted).

  This assumes that all tables in the data sheet are running tallys. If you have
  multiple different tables, this will not work for that data sheet.

  Purpose: Handles data sheets where the tabular data is a list of instances that are
  annotated as they happen. Each table is read as one tally, in reading order, and
  becomes one row holding its Tally Summary: the marks, a count per option, the total,
  and a percentage per option.

  Use case: Therapy session data sheets where a tally was tracked keeping track of how many
  times in the session the student did a particular thing (using yes, no or prompted for
  example).
  """

  def __init__(self, id: str, title: str, tally_options: list[TallyOption]) -> None:
    """
    :param id: The unique id identifying this specific interpreter instance within a template.
    :param title: The user-facing title identifying this interpreter within a template.
    :param tally_options: The marks that may be written in the grid, with what each means.
    """
    super().__init__(id, title)
    # Copied per instance so interpreters never share option lists
    self._tally_options: list[TallyOption] = list(tally_options)

  @property
  def tally_options(self) -> list[TallyOption]:
    """The marks that may be written in the grid, with what each means, in order."""
    return self._tally_options

  @property
  def tally_choice_options(self) -> list[str]:
    """The marks, in order."""
    return [option.mark for option in self._tally_options]

  @property
  def consumes_tables(self) -> bool:
    """
    A running tally is read from a table on the sheet.
    """
    return True

  def section_keys(self) -> list[str]:
    """
    The Tally Summary keys, so the tally options are part of the Template Structure.
    """
    return tally_keys(TALLY_COLUMN_NAME, self._tally_options)

  def config_problems(self) -> list[str]:
    """No options, or blank, repeated, or too-long marks."""
    return option_problems(self.title, ColumnType.TALLY, self.tally_choice_options, kind="running tally section")

  def option_descriptions(self) -> list[OptionDescription]:
    """Every tally option, in order."""
    section = self.title or _FALLBACK_SECTION_NAME
    return [
      OptionDescription(section, "", "Tally", option.mark, option.description)
      for option in self._tally_options
    ]

  def interpret_student_data_sheet_content(self, data_sheet_content: StudentDataSheetImport) -> DataSheetInterpretationDto:
    """
    Reads each table as one running tally.

    This assumes that all tables in the data sheet are running tallys. If you have
    multiple different tables, this will not work for that data sheet.

    Purpose: Implements the abstract method from the base class to handle tables
    as if they were just a single running list of instances with a tally in each box.

    :param data_sheet_content: A dictionary with 2 properties:
      tables: List of 2D arrays representing tables from the data sheet
      form_data: A list of key value pairs where the key is the field name and the
                 value is the value name.
    :return: a DataSheetInterpretationDto with one table per tally. Each mark that isn't
      an option is left out of the counts and listed in its value_problems.
    """
    section = self.title or _FALLBACK_SECTION_NAME
    problems: list[ValueProblem] = []
    several_tables = len(data_sheet_content.tables) > 1
    tables: list[DataSheetTable] = []
    for table_number, raw_table in enumerate(data_sheet_content.tables, start=1):
      where = f"table {table_number}" if several_tables else ""
      table, unknown_marks = self._interpret_single_student_data_sheet_table(raw_table)
      tables.append(table)
      problems.extend(
        ValueProblem(section, "", where, mark, unknown_mark_phrase(self._tally_options))
        for mark in unknown_marks
      )

    return DataSheetInterpretationDto(tables, {}, problems)

  def _interpret_single_student_data_sheet_table(self, data_sheet_table: list[list[str]]) -> tuple[DataSheetTable, str]:
    """
    Read every cell in reading order (row by row) as one tally.

    :return: The table, and each mark that isn't an option, in reading order
    """
    tally_string = ''.join(''.join(row) for row in data_sheet_table)
    summary = read_tally(tally_string, self._tally_options)
    row: dict[str, DataSheetScalarDto] = tally_scalars(TALLY_COLUMN_NAME, summary, self._tally_options)

    table: DataSheetTable = {
      "columns": list(row.keys()),
      "data": [row]
    }
    return table, summary.unknown_marks
