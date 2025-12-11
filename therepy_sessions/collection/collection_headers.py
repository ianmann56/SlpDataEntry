class StudentDataSheetImport:
  form_data = ""
  tables = []

  def __init__(self, form_data, tables):
    self.form_data = form_data
    self.tables = tables