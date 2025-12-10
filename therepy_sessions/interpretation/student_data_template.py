from abc import ABC, abstractmethod
from collections import namedtuple
from interpretation.student_data_sheet import StudentDataSheet

class BaseStudentDataSheetTemplate(ABC):
  """
  Abstract base class for interpreting student data sheets from various sources.
  
  Purpose: Provides a common framework for processing therapy session data sheets
  that have been imported from images or other external systems. Handles the parsing
  of labeled text sections (Date, Goal, Measure, etc.) and delegates table interpretation
  to concrete subclasses.
  
  The class follows the Template Method pattern, where the main workflow is defined
  in interpret_student_data_sheet() but specific table processing logic is left
  to subclasses to implement based on their specific data structure needs.
  
  Expected input format:
  - Student identifier appears before the first labeled section (top left of the sheet).
  - Text with labeled sections like "Date: 2/7/2025", "Goal: Use variety of complex words"
  - Tables as array of 2D arrays with headers in the first row

  Example input image:

  -----------------------------------------------------------------------------------------------
  | JA                                                                         Date: 10/3/2025  |
  | Time IN: 11:00 AM                                                       Time OUT: 11:25 AM  |
  | Goal: By October, {JA} will identify a possible cause of a given emotion from an array of   |
  | 5-6 picture choices, given a verbal or visual cue. 70% accuracy. By April 2025, {JA} will   |
  | identify a possible cause of a given emotion from a situational picture and state emotional |
  | regulation or problem solving strategy from an array of 5-6 picture choices, given a verbal |
  | or visual cue 70% accuracy.                                                                 |
  | Measure: Identify the cause of emotion from a picture. Then state emotional regulation or   |
  | problem solving strategy from picture choices.                                              |
  | Data:                                                                                       |
  | TABULAR DATA HERE - PROCESSED BY SUBCLASSES                                                 |
  -----------------------------------------------------------------------------------------------

  Example input content:

  ```
  JA
  Date: 10/3/2025
  Time IN: 11:00 AM
  Time OUT: 11:25 AM
  Goal: By October 2024, {JA} will identify a possible cause of a given emotion
  from an array of 5-6 picture choices, given a verbal or visual cue. 70% accuracy
  By April 2025, {JA} will identify a possible cause of a given emotion from a
  situational picture and state emotional regulation or problem solving strategy from
  an array of 5-6 picture choices, given a verbal or visual cue 70% accuracy
  Measure: Identify the cause of emotion from a picture. Then
  state emotional regulation or problem solving strategy from
  picture choices.
  Data:
  TABULAR DATA HERE - PROCESSED BY SUBCLASSES
  ```

  Use this as a base for creating specific templates that handle different
  table structures or data sheet layouts in therapy session documentation.
  """

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
    expected_meta_labels = [
      'Date', 'Time IN', 'Time OUT', 'Goal', 'Measure', 'Data'
    ]
    
    labelled_sections = self._split_by_labels(data_sheet_content.text, expected_meta_labels)
    
    student_key = self._get_labelled_content(labelled_sections, 'student_key')
    date = self._get_labelled_content(labelled_sections, 'Date')
    time_in = self._get_labelled_content(labelled_sections, 'Time IN')
    time_out = self._get_labelled_content(labelled_sections, 'Time OuT')
    student_goal = self._get_labelled_content(labelled_sections, 'Goal')
    measure = self._get_labelled_content(labelled_sections, 'Measure')

    data_sheet = StudentDataSheet(student_key, student_goal, date, time_in, time_out, measure)

    tables = self._interpret_student_data_sheet_tables(data_sheet_content.tables)

    for table in tables:
      data_sheet.register_table(table)

    return data_sheet
  
  def _split_by_labels(self, text, labels):
    """
    Parses text content by identifying sections marked with specific labels.
    
    Purpose: Splits the raw text into labeled sections to extract structured data
    like Date, Time IN, Goal, etc. Also extracts the unlabeled student key that
    appears before the first label.
    
    :param text: Raw text content from the data sheet
    :param labels: List of expected labels to search for in the text
    :return: Dictionary mapping lowercase labels to content dictionaries with
             'label', 'content_with_label', and 'content_without_label' keys
    """
    LabelWPosition = namedtuple('LabelWPosition', ['label', 'pos'])

    labels_with_positions = [
      LabelWPosition(label, text.find(label))
      for label
      in labels
    ]

    labels_with_positions = sorted(labels_with_positions, key=lambda lwp: lwp.pos)

    text_by_label = {}
    for i, (label, pos) in enumerate(labels_with_positions):
      if i + 1 >= len(labels_with_positions):
        # Then this is the last label. so there's no next label.
        next_label_position = len(text)
      else:
        next_label_position = labels_with_positions[i+1].pos

      content_with_label = text[pos:next_label_position].strip()
      content_without_label = content_with_label.split(':', maxsplit=1)[1].strip()

      content_dto = {
        'label': label,
        'content_with_label': content_with_label,
        'content_without_label': content_without_label
      }
      text_by_label[label.lower()] = content_dto

    # student key is unlabelled but is expected before the first label which makes this
    # easy... just take all the text before the first label and that's the student key.
    student_key_end_pos = labels_with_positions[0].pos
    student_key_content = text[0:student_key_end_pos].strip()

    text_by_label['student_key'] = {
      'label': 'Student Key',
      'content_with_label': student_key_content,
      'content_without_label': student_key_content
    }

    return text_by_label

  def _get_labelled_content(self, text_by_label, label):
    """
    Extracts the content associated with a specific label from parsed sections.
    
    Purpose: Helper method to retrieve clean content (without the label prefix)
    from the structured text sections created by _split_by_labels.
    
    :param text_by_label: Dictionary of labeled sections from _split_by_labels
    :param label: The label whose content should be retrieved
    :return: String content without the label prefix
    """
    content_dto = text_by_label[label.lower()]
    return content_dto['content_without_label']

  @abstractmethod
  def _interpret_student_data_sheet_tables(self, data_sheet_tables):
    """
    Processes and interprets tabular data from the student data sheet.
    
    Purpose: Abstract method that subclasses must implement to define how
    raw table data should be structured and interpreted. This allows different
    template types to handle tables in their own specific way while maintaining
    a consistent interface.
    
    :param data_sheet_tables: List of 2D arrays representing tables from the data sheet
    :return: Processed table data in a format specific to the template implementation
    """
    pass

class ColumnTableStudentDataSheetTemplate(BaseStudentDataSheetTemplate):
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

  def _interpret_student_data_sheet_tables(self, data_sheet_tables):
    """
    Processes multiple tables from the data sheet using column-based interpretation.
    
    This assumes that all tables in the data sheet have the same structure. If you have
    multiple different tables, this will not work for that data sheet.

    Purpose: Implements the abstract method from the base class to handle tables
    by applying column-based processing to each table individually.
    
    :param data_sheet_tables: List of 2D arrays representing tables from the data sheet
    :return: List of interpreted table objects with structured column data
    """
    return [
      self._interpret_single_student_data_sheet_table(raw_table)
      for raw_table
      in data_sheet_tables
    ]

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
        row_dto[column_name] = row_data[column_index]

      data.append(row_dto)
    
    return {
      "columns": self._columns,
      "data": data
    }