from interpretation.student_data_sheet_interpreter import DataSheetInterpretationDto, SessionDataSectionInterpreterBase


class FieldConfiguration:
  # The name of the field
  name = ""

  # The DataSheetScalarType representing the type of value in this field.
  fieldType = None

  def __init__(self, name, fieldType):
    self.name = name
    self.fieldType = fieldType

class SimpleFormInterpreter(SessionDataSectionInterpreterBase):
  """
  Template implementation for data sheets containing form fields with specific names.

  Purpose: Handles data sheets where the form data follows a predictable key-value
  format.

  Use case: Therapy session data sheets with consistent form feilds like 'Total Repetitions',
  'Times w/Prompting', 'Times w/o Prompting', etc.
  """

  # A dictionary of fields and their field configurations.
  # Key: The field name
  # Values: The FieldConfiguration that describes the field.
  _fields = {}

  def __init__(self, fields):
    """
    Initializes the template with expected field configurations for form processing.

    Purpose: Sets up the template to work with forms that have specific fields, allowing
    validation and proper data extraction based on the field configurations.

    :param fields: Dictionary of expected fields and their configurations. The keys are the field
      names, the values are the configurations as FieldConfiguration objects.
    """
    super().__init__()
    self._fields = fields

  def interpret_student_data_sheet_content(self, data_sheet_content):
    """
    Processes multiple form fields from the data sheet.

    Purpose: Implements the abstract method from the base class to handle forms.

    :param data_sheet_content: A dictionary with 2 properties:
      tables: List of 2D arrays representing tables from the data sheet
      form_data: A list of key value pairs where the key is the field name and the
                 value is the value name.
    :return: a DataSheetInterpretationDto representing the interpreted data
    """
    scalars = {
      kv.key: kv.value
      for kv
      in data_sheet_content.form_data
      if kv.key in self._fields.keys()
    }

    return DataSheetInterpretationDto([], scalars)