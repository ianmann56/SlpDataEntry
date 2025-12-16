class StudentDataSheetTemplate:
  _id = ""
  _name = ""
  _file_location = ""
  _configured_interpreter = None

  def __init__(self, id, name, file_location, configured_interpreter=None):
    self._id = id
    self._name = name
    self._file_location = file_location
    self._configured_interpreter = configured_interpreter

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
  def file_location(self):
    """
    The location of this template configuration on the local system
    """
    return self._file_location

  @property
  def interpreter(self):
    """
    Loads the underlying template for this configuration which will interpret student data sheets.
    """
    if self._configured_interpreter:
      return self._configured_interpreter
    else:
      # Need to load from store.
      raise NotImplementedError()