class StudentDataSheet:
  _student_key = ""
  _student_goal = ""
  _date = ""
  _tables = []

  def __init__(self, student_key, student_goal, date):
    self._student_key = student_key
    self._student_goal = student_goal
    self._date = date

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
  def tables(self):
    return self._tables
  
  def register_table(self, table):
    self._tables.append(table)