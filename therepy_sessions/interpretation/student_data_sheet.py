from __future__ import annotations

from collections import namedtuple
from enum import Enum
import json
from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
  # Imported for type checking only: the template module imports the interpreters, which import this module
  from interpretation.template_manager.student_data_sheet_template import StudentDataSheetTemplate

"""
Represents a scalar in a student session data sheet.

Properties:
  key: The name of the scalar field
  value: The value of the scalar field
  type: The type that the scalar field value takes on (like int, vs choice, vs date).
  choice_options: The options that this scalar could be. This is only applicable if type is CHOICE.
"""
DataSheetScalarDto = namedtuple('DataSheetScalarDto', ['key', 'value', 'type', 'choice_options'])

class DataSheetScalarType(Enum):
  TEXT = 'text' # For plain text
  INT = 'int'
  CHOICE = 'choice' # When field contains a selection out of discrete choices
  DATE = 'date'
  BOOLEAN = 'boolean'

class DataSheetTable(TypedDict):
  """
  One interpreted table in a StudentDataSheet.

  Properties:
    columns: The table's columns, in order.
    data: One mapping per row, from column name to that cell's scalar.
    section_id: The id of the interpreter that produced the table.
  """
  columns: list[object]  # ColumnDefinition (TableInterpreter) or str (RunningTallyInterpreter)
  data: list[dict[str, DataSheetScalarDto]]
  section_id: NotRequired[str]

class StudentDataSheet:

  def __init__(
    self,
    student_key: str,
    student_goal: str,
    date: str,
    time_in: str,
    time_out: str,
    measure: str,
    template: StudentDataSheetTemplate,
  ) -> None:
    self._student_key = student_key
    self._student_goal = student_goal
    self._date = date
    self._time_in = time_in
    self._time_out = time_out
    self._measure = measure
    self._template = template
    # Created per instance so sheets never share tables or scalars
    self._tables: list[DataSheetTable] = []
    self._scalars: dict[str, DataSheetScalarDto | str] = {}  # SimpleFormInterpreter stores the raw form text

  @property
  def student_key(self) -> str:
    return self._student_key

  def use_student_key(self, student_key: str) -> None:
    """
    Replace the Student Key read from the sheet with the stored one, once the student is matched.
    """
    self._student_key = student_key

  @property
  def template(self) -> StudentDataSheetTemplate:
    """
    The template this sheet was interpreted with. Storage reads it only through the sheet.
    """
    return self._template

  @property
  def student_goal(self) -> str:
    return self._student_goal

  @property
  def date(self) -> str:
    return self._date
  
  @property
  def time_in(self) -> str:
    return self._time_in
  
  @property
  def time_out(self) -> str:
    return self._time_out

  @property
  def measure(self) -> str:
    return self._measure
  
  @property
  def tables(self) -> list[DataSheetTable]:
    return self._tables
  
  def register_table(self, table: DataSheetTable, section_id: str) -> None:
    """
    Add a table, tagged with the id of the interpreter that produced it.
    """
    self._tables.append({**table, "section_id": section_id})
  
  @property
  def scalars(self) -> dict[str, DataSheetScalarDto | str]:
    return self._scalars
  
  def register_scalar(self, scalar_name: str, scalar_dto: DataSheetScalarDto | str) -> None:  # SimpleFormInterpreter stores the raw form text
    self._scalars[scalar_name] = scalar_dto

  def debug(self) -> None:
    print('========== Data Sheet ===========\nStudent Key:')
    print(self.student_key)
    print('=================================\nTemplate:')
    print(self.template.name)
    print('=================================\nDate:')
    print(self.date)
    print('=================================\nTime In:')
    print(self.time_in)
    print('=================================\nTime Out:')
    print(self.time_out)
    print('=================================\nGoal:')
    print(self.student_goal)
    print('=================================\nMeasure:')
    print(self.measure)
    print('=================================\nOther Scalars:')
    print(self.scalars)
    print('=================================\nTables:')
    print(json.dumps(self.tables, indent=4, default=lambda o: o.to_json() if 'to_json' in dir(o) else o.value))
    print('======== End Data Sheet =========')
