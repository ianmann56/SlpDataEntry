from collections import namedtuple
from enum import Enum

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

class StudentDataSheet:
  _student_key = ""
  _student_goal = ""
  _date = ""
  _time_in = ""
  _time_out = ""
  _measure = ""
  _tables = []
  _scalars = {}

  def __init__(self, student_key, student_goal, date, time_in, time_out, measure):
    self._student_key = student_key
    self._student_goal = student_goal
    self._date = date
    self._time_in = time_in
    self._time_out = time_out
    self._measure = measure

  @property
  def student_key(self):
    return self._student_key

  @property
  def student_goal(self):
    return self._student_goal

  @property
  def date(self):
    return self._date
  
  @property
  def time_in(self):
    return self._time_in
  
  @property
  def time_out(self):
    return self._time_out

  @property
  def measure(self):
    return self._measure
  
  @property
  def tables(self):
    return self._tables
  
  def register_table(self, table):
    self._tables.append(table)
  
  @property
  def scalars(self):
    return self._scalars
  
  def register_scalar(self, scalar_name, scalar_dto):
    self._scalars[scalar_name] = scalar_dto

  def debug(self):
    print('========== Data Sheet ===========\nStudent Key:')
    print(self.student_key)
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
    print(self.tables)
    print('======== End Data Sheet =========')
