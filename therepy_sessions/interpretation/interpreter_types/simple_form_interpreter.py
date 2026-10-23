from interpretation.analysis.parts import SectionParts
from interpretation.templates.student_data_sheet_interpreter import DataSheetInterpretationDto, SessionDataSectionInterpreterBase
from interpretation.student_data_sheet import DataSheetScalarDto
from interpretation.template_manager.option_rules import name_problems, option_problems
from interpretation.value_types import (
  COLUMN_TYPE_LABELS,
  FIELD_TYPES,
  ChoiceOption,
  ColumnType,
  OptionDescription,
  ValueProblem,
  read_value_leniently,
  scalar_type_for,
)
from collection.collection_headers import StudentDataSheetImport

# The section name used in messages and the Workbook Key when a form section has no title
_FALLBACK_SECTION_NAME: str = "Form"


class FieldConfiguration:
  """
  One field of a form section, with its Field Type.

  Properties:
    name: The field's label on the sheet.
    field_type: How its value is read. One of FIELD_TYPES.
    choices: The choices of a Choice field. Empty otherwise.
  """

  def __init__(
    self,
    name: str,
    field_type: ColumnType = ColumnType.TEXT,
    choices: list[ChoiceOption] | None = None,
  ) -> None:
    self._name = name
    self._field_type = field_type
    # Copied per instance so fields never share option lists
    self._choices: list[ChoiceOption] = list(choices or [])

  @property
  def name(self) -> str:
    return self._name

  @property
  def field_type(self) -> ColumnType:
    return self._field_type

  @property
  def fieldType(self) -> ColumnType:
    """The field type, by its older name."""
    return self._field_type

  @property
  def choices(self) -> list[ChoiceOption]:
    return self._choices


class SimpleFormInterpreter(SessionDataSectionInterpreterBase):
  """
  Template implementation for data sheets containing form fields with specific names.

  Purpose: Handles data sheets where the form data follows a predictable key-value
  format. Each field's value is read as its Field Type.

  Use case: Therapy session data sheets with consistent form feilds like 'Total Repetitions',
  'Times w/Prompting', 'Times w/o Prompting', etc.
  """

  def __init__(self, id: str, title: str, fields: dict[str, FieldConfiguration]) -> None:
    """
    Initializes the template with expected field configurations for form processing.

    Purpose: Sets up the template to work with forms that have specific fields, allowing
    validation and proper data extraction based on the field configurations.

    :param id: The unique id identifying this specific interpreter instance within a template.
    :param title: The user-facing title identifying this interpreter within a template.
    :param fields: Dictionary of expected fields and their configurations. The keys are the field
      names, the values are the configurations as FieldConfiguration objects.
    """
    super().__init__(id, title)
    # A dictionary of fields and their field configurations.
    # Key: The field name
    # Values: The FieldConfiguration that describes the field.
    self._fields: dict[str, FieldConfiguration] = fields

  @property
  def fields(self) -> dict[str, FieldConfiguration]:
    """
    Get the field configurations for this interpreter.

    Returns:
        dict: Dictionary of field names to FieldConfiguration objects
    """
    return self._fields

  @property
  def fallback_section_name(self) -> str:
    """The name this section goes by when it has no title."""
    return _FALLBACK_SECTION_NAME

  def section_keys(self) -> list[str]:
    """
    The field names, in template order.
    """
    return list(self._fields.keys())

  def config_problems(self) -> list[str]:
    """
    Blank or repeated field names, a type a field can't have, and Choice fields with
    missing, blank, or repeated choices.
    """
    problems = name_problems("field", [field.name for field in self._fields.values()])
    for field in self._fields.values():
      if field.field_type not in FIELD_TYPES:
        problems.append(f'Field "{field.name}" can\'t be a {COLUMN_TYPE_LABELS[field.field_type]} field.')
      elif field.field_type is ColumnType.CHOICE:
        problems.extend(option_problems(field.name, ColumnType.CHOICE, [c.value for c in field.choices], kind="field"))
    return problems

  def analysis_parts(self) -> SectionParts:
    """The Integer and Decimal fields, in field order, as Numeric Sheet Values."""
    return SectionParts(
      [],
      [field.name for field in self._fields.values() if field.field_type in (ColumnType.INT, ColumnType.DECIMAL)],
    )

  def option_descriptions(self) -> list[OptionDescription]:
    """Every Choice field's choices, in field order then choice order."""
    section = self.section_name
    return [
      OptionDescription(section, field.name, "Choice", choice.value, choice.description)
      for field in self._fields.values()
      if field.field_type is ColumnType.CHOICE
      for choice in field.choices
    ]

  def interpret_student_data_sheet_content(self, data_sheet_content: StudentDataSheetImport) -> DataSheetInterpretationDto:
    """
    Processes multiple form fields from the data sheet.

    Purpose: Implements the abstract method from the base class to handle forms. Each
    configured field found on the sheet is read as its Field Type.

    :param data_sheet_content: A dictionary with 2 properties:
      tables: List of 2D arrays representing tables from the data sheet
      form_data: A list of key value pairs where the key is the field name and the
                 value is the value name.
    :return: a DataSheetInterpretationDto representing the interpreted data. Every field
      whose value doesn't fit its type is kept as read and listed in its value_problems.
    """
    section = self.section_name
    problems: list[ValueProblem] = []
    scalars: dict[str, DataSheetScalarDto] = {}
    for field_key, field in self._fields.items():
      if field_key not in data_sheet_content.form_data:
        continue
      text = data_sheet_content.form_data[field_key]
      # A value that doesn't fit keeps its text, with no typed value, so nothing written is lost
      reading = read_value_leniently(field.field_type, text, field.choices)
      if reading.expected:
        problems.append(
          ValueProblem(section, field.name, "", text, reading.expected, item_kind="field", saved_as=reading.saved_as)
        )
      choice_values = [choice.value for choice in field.choices]
      scalars[field_key] = DataSheetScalarDto(
        field_key, text, scalar_type_for(field.field_type), choice_values or None, reading.typed_value,
      )

    return DataSheetInterpretationDto([], scalars, problems)
