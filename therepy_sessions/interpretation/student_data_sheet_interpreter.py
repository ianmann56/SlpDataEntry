from abc import ABC, abstractmethod
from collections import namedtuple
from interpretation.student_data_sheet import StudentDataSheet

class StudentDataSheetInterpreter:
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

  session_data_templates = []

  def __init__(self, session_data_templates):
    super().__init__()
    self.session_data_templates = session_data_templates

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
    student_key = data_sheet_content.form_data['Student Key']
    date = data_sheet_content.form_data['Date']
    time_in = data_sheet_content.form_data['Time IN']
    time_out = data_sheet_content.form_data['Time OUT']
    student_goal = data_sheet_content.form_data['Goal']
    measure = data_sheet_content.form_data['Measure']

    data_sheet = StudentDataSheet(student_key, student_goal, date, time_in, time_out, measure)

    data_sheet_interpretations = [
      template.interpret_student_data_sheet_content(data_sheet_content)
      for template
      in self.session_data_templates
    ]

    for interpretation in data_sheet_interpretations:
      for table in interpretation.tables:
        data_sheet.register_table(table)

      for scalar_name, scalar_dto in interpretation.scalars.items():
        data_sheet.register_scalar(scalar_name, scalar_dto)

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
  
"""
Represents the interpreted data from a data sheet.

Properties:
  tables: List of dictionaries representing all of the tables in the data sheet.
    These will contain a list of columns and a list of key value mapping of column
    name to the row value for each row in the table.
  scalars: Dictionary where the key is the scalar field name and the value is a
    DTO with the value and type (with those names as property names).
"""
DataSheetInterpretationDto = namedtuple('DataSheetInterpretationDto', ['tables', 'scalars'])
  
class SessionDataInterpreterBase(ABC):

  @abstractmethod
  def interpret_student_data_sheet_content(self, data_sheet_content):
    """
    Processes and interprets tabular data from the student data sheet.
    
    Purpose: Abstract method that subclasses must implement to define how
    raw data should be structured and interpreted. This allows different
    template types to handle data sheets in their own specific way while maintaining
    a consistent interface.
    
    :param data_sheet_content: A dictionary with 2 properties:
      tables: List of 2D arrays representing tables from the data sheet
      form_data: A list of key value pairs where the key is the field name and the
                 value is the value name.
    :return: a DataSheetInterpretationDto representing the interpreted data
    """
    pass