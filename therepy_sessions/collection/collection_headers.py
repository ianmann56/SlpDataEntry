class StudentDataSheetImport:
  """
  Raw OCR output for one sheet. It carries no meaning yet.

  Properties:
    form_data: Label → text, with any trailing ':' removed from labels.
    tables: Each table as a row-major 2D array of cell text.
    table_titles: The title printed above each table, in the same order as `tables`,
      with any trailing ':' removed. "" for a table with no title found.
  """

  def __init__(
    self,
    form_data: dict[str, str],
    tables: list[list[list[str]]],
    table_titles: list[str] | None = None,
  ) -> None:
    self.form_data: dict[str, str] = form_data
    self.tables: list[list[list[str]]] = tables
    # Imports saved before titles were read have none, so every table counts as untitled
    titles = list(table_titles or [])
    self.table_titles: list[str] = titles[:len(tables)] + [""] * (len(tables) - len(titles))
