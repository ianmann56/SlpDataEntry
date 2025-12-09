from abc import ABC, abstractmethod

from interpretation.student_data_sheet import StudentDataSheet

class BaseStudentDataSheetTemplate(ABC):

  def interpret_student_data_sheet(self, data_sheet_content):
    """
    Takes the given imported student's data sheet from an image or some other external system
    and interprets the content based on the template configured for that student.

    The data being passed in is expected to be normalized in the sense that tables are parsed
    and the text is split into the appropriate lines.

    This method will give meaning to the content and return an object that represents that meaning.
    
    :param data_sheet_content: The data from a student's data sheet that is parsed into distinct
      parts and ready for meaning to be attached to each part.

      This is expected to contain the following properties:
        text: The raw text separated by lines
        tables: a list of 2D arrays, each 2D array representing a table. Each array at the lowest
                level represents a row of data. The column headers are expected to be the first row.

    :return: A DTO with the name and goal of the student and the date on which the sample was taken.
    """
    meta_text_lines = data_sheet_content.text.splitlines()[0:3]
    
    student_key = self._strip_label(meta_text_lines[0])
    date = self._strip_label(meta_text_lines[1])
    student_goal = self._strip_label(meta_text_lines[2])

    data_sheet = StudentDataSheet(student_key, student_goal, date)

    tables = self._interpret_student_data_sheet_tables(data_sheet_content.tables)

    for table in tables:
      data_sheet.register_table(table)

    return data_sheet

  def _strip_label(self, text):
    label_and_content = text.split(':', maxsplit=1)
    content = label_and_content[1].strip()
    return content

  @abstractmethod
  def _interpret_student_data_sheet_tables(self, data_sheet_tables):
    """
    Applies meaning to the list of tables and returns an object to represent it.
    """
    pass

class ColumnTableStudentDataSheetTemplate(BaseStudentDataSheetTemplate):
  _columns = []

  def __init__(self, columns):
    super().__init__()
    self._columns = columns

  def _interpret_student_data_sheet_tables(self, data_sheet_tables):
    return [
      self._interpret_single_student_data_sheet_table(raw_table)
      for raw_table
      in data_sheet_tables
    ]

  def _interpret_single_student_data_sheet_table(self, data_sheet_table):
    return {
      "columns": self._columns,
      "data": data_sheet_table[1:]
    }