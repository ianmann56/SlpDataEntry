from __future__ import annotations

from abc import ABC, abstractmethod
from collections import namedtuple
from typing import TYPE_CHECKING

import ipdb
from interpretation.student_data_sheet import StudentDataSheet
from collection.collection_headers import StudentDataSheetImport

if TYPE_CHECKING:
  # Imported for type checking only: the template module imports this module
  from interpretation.template_manager.student_data_sheet_template import StudentDataSheetTemplate
  
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


def _normalize_title(title: str) -> str:
  """A section or table title as compared: no trailing ':', single spaces, ignoring letter case."""
  return " ".join(title.strip().removesuffix(":").split()).casefold()
  
class SessionDataSectionInterpreterBase(ABC):

  def __init__(self, id: str, title: str) -> None:
    """
    :param id: The unique id identifying this specific interpreter instance within a template.
    :param title: The user-facing title identifying this interpreter within a template.
    """
    self._id = id
    self._title = title

  @property
  def id(self) -> str:
    """
    The unique id identifying this specific interpreter instance within a template.
    """
    return self._id

  @property
  def title(self) -> str:
    """
    The user-facing title identifying this interpreter within a template.
    """
    return self._title

  @property
  def section_kind(self) -> str:
    """
    The kind of section this interpreter reads. Part of the Template Structure, so
    renaming an interpreter class changes which workbook its templates' sessions go to.
    """
    return type(self).__name__

  @property
  def consumes_tables(self) -> bool:
    """
    Whether this section reads tables from the sheet. When a template has several such
    sections, each table goes to the one whose title matches the table's title.
    """
    return False

  @abstractmethod
  def section_keys(self) -> list[str]:
    """
    The field / column / tally keys this section produces, in template order.

    These feed the Template Structure: changing them changes which Student Session
    Workbook a template's sessions are saved to.
    """
    pass

  @abstractmethod
  def interpret_student_data_sheet_content(self, data_sheet_content: StudentDataSheetImport) -> DataSheetInterpretationDto:
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

  def __init__(
    self,
    session_data_templates: list[SessionDataSectionInterpreterBase],
    template: StudentDataSheetTemplate,
  ) -> None:
    """
    :param session_data_templates: The template's section interpreters, in template order.
    :param template: The template these interpreters come from. Every sheet this
      interpreter builds carries it.
    """
    super().__init__()
    self.session_data_templates: list[SessionDataSectionInterpreterBase] = session_data_templates
    self._template = template

  def interpret_student_data_sheet(self, data_sheet_content: StudentDataSheetImport) -> StudentDataSheet:
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

    :return: The interpreted sheet. It carries the template it was interpreted with, and
      each of its tables is tagged with the id of the interpreter that produced it.
    """
    student_key = data_sheet_content.form_data['Student Key']
    date = data_sheet_content.form_data['Date']
    time_in = data_sheet_content.form_data['Time IN']
    time_out = data_sheet_content.form_data['Time OUT']
    student_goal = data_sheet_content.form_data['Goal']
    measure = data_sheet_content.form_data['Measure']

    data_sheet = StudentDataSheet(student_key, student_goal, date, time_in, time_out, measure, template=self._template)

    # Each table section sees only the tables assigned to it, so no table is read twice
    tables_by_section = self._assign_tables(data_sheet_content)

    # Each interpretation is paired with the interpreter that produced it, so tables can be tagged
    data_sheet_interpretations = [
      (interpreter, interpreter.interpret_student_data_sheet_content(
        tables_by_section.get(interpreter.id, data_sheet_content)
      ))
      for interpreter
      in self.session_data_templates
    ]

    for interpreter, interpretation in data_sheet_interpretations:
      for table in interpretation.tables:
        data_sheet.register_table(table, interpreter.id)

      for scalar_name, scalar_dto in interpretation.scalars.items():
        data_sheet.register_scalar(scalar_name, scalar_dto)

    return data_sheet
  
  def _assign_tables(self, data_sheet_content: StudentDataSheetImport) -> dict[str, StudentDataSheetImport]:
    """
    Decide which tables on the sheet each table section reads.

    A template with one table section gives it every table, whatever their titles. A
    template with several gives each table to the section whose title matches the
    table's title, ignoring letter case, spacing, and a trailing ':'. A table that
    matches no section, a section with no table, or a table with no title fails the
    sheet loudly.

    :return: For each table section's id, an Import holding only its tables. Sections
      that read no tables are left out and see the whole Import.
    :raises ValueError: If the tables can't be matched to the template's table sections
    """
    table_sections = [interpreter for interpreter in self.session_data_templates if interpreter.consumes_tables]
    if len(table_sections) <= 1:
      return {section.id: data_sheet_content for section in table_sections}

    section_by_title: dict[str, SessionDataSectionInterpreterBase] = {}
    for section in table_sections:
      key = _normalize_title(section.title)
      if not key:
        raise ValueError(
          "the template has more than one table section, so each needs a title matching the title above its table on the sheet"
        )
      if key in section_by_title:
        raise ValueError(f'the template has more than one table section titled "{section.title}", so their tables can\'t be told apart')
      section_by_title[key] = section

    section_titles = ", ".join(f'"{section.title}"' for section in table_sections)
    indexes_by_section: dict[str, list[int]] = {section.id: [] for section in table_sections}
    for index, title in enumerate(data_sheet_content.table_titles):
      if not _normalize_title(title):
        raise ValueError(f"table {index + 1} on the sheet has no title, so it can't be matched to one of {section_titles}")
      section = section_by_title.get(_normalize_title(title))
      if section is None:
        raise ValueError(f'the sheet has a table titled "{title}", but the template has no table section with that title (expected {section_titles})')
      indexes_by_section[section.id].append(index)

    for section in table_sections:
      if not indexes_by_section[section.id]:
        raise ValueError(f'no table titled "{section.title}" was found on the sheet')

    return {
      section_id: StudentDataSheetImport(
        data_sheet_content.form_data,
        [data_sheet_content.tables[index] for index in indexes],
        [data_sheet_content.table_titles[index] for index in indexes],
      )
      for section_id, indexes in indexes_by_section.items()
    }

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