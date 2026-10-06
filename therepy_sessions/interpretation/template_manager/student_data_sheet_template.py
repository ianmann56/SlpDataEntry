from interpretation.templates.student_data_sheet_interpreter import SessionDataSectionInterpreterBase, StudentDataSheetInterpreter


class StudentDataSheetTemplate:

  def __init__(
    self,
    id: str,
    name: str,
    configured_interpreters: list[SessionDataSectionInterpreterBase] | None = None,
    description: str = "",
  ) -> None:
    self._id: str = id
    self._name: str = name
    self._configured_interpreters: list[SessionDataSectionInterpreterBase] | None = configured_interpreters
    self._description: str = description

  @property
  def id(self) -> str:
    """
    A guid id for this template configuration.
    """
    return self._id

  @property
  def name(self) -> str:
    """
    The name of this template configuration
    """
    return self._name

  @property
  def description(self) -> str:
    """
    Optional free text describing the sheet layout this template reads. Empty when none was given.
    """
    return self._description

  @property
  def interpreters(self) -> list[SessionDataSectionInterpreterBase]:
    """
    Loads the underlying template for this configuration which will interpret student data sheets.
    """
    if self._configured_interpreters:
      return self._configured_interpreters
    else:
      # Need to load from store.
      raise NotImplementedError()

  def to_data_sheet_interpreter(self) -> StudentDataSheetInterpreter:
    """
    Constructs a StudentDataSheetInterpreter from this template, using its
    configured interpreters as the session data templates. Every sheet it
    interprets carries this template.
    """
    return StudentDataSheetInterpreter(self.interpreters, self)
