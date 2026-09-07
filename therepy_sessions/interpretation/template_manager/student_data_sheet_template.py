from interpretation.templates.student_data_sheet_interpreter import StudentDataSheetInterpreter


class StudentDataSheetTemplate:
  _id = ""
  _name = ""
  _configured_interpreters = None

  def __init__(self, id, name, configured_interpreters=None):
    self._id = id
    self._name = name
    self._configured_interpreters = configured_interpreters

  @property
  def id(self):
    """
    A guid id for this template configuration.
    """
    return self._id

  @property
  def name(self):
    """
    The name of this template configuration
    """
    return self._name

  @property
  def interpreters(self):
    """
    Loads the underlying template for this configuration which will interpret student data sheets.
    """
    if self._configured_interpreters:
      return self._configured_interpreters
    else:
      # Need to load from store.
      raise NotImplementedError()

  def to_data_sheet_interpreter(self):
    """
    Constructs a StudentDataSheetInterpreter from this template, using its
    configured interpreters as the session data templates.
    """
    return StudentDataSheetInterpreter(self.interpreters)