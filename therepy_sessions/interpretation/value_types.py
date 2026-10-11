"""
Column Types, and the rules for reading a value written on a sheet as its type.

Every interpreter reads values through this module, so a column and a form field of the
same type are read the same way. It is pure: no I/O and no UI, so all of it can be
checked offline with plain strings.

It imports from `interpretation/student_data_sheet.py`, which never imports it back.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import date
from enum import Enum
from typing import NamedTuple

from interpretation.student_data_sheet import DataSheetScalarDto, DataSheetScalarType, TypedValue


class ColumnType(Enum):
  """
  The type of a table column or form field, as the SLP configured it. A Tally column
  emits several scalars (its Tally Summary), so this is not the same as a Scalar Type.
  """
  TEXT = "text"
  INT = "int"
  DECIMAL = "decimal"
  BOOLEAN = "boolean"
  DATE = "date"
  CHOICE = "choice"
  TALLY = "tally"


# The Field Types: every Column Type a Simple Form field can have. Tally is for columns only.
FIELD_TYPES: tuple[ColumnType, ...] = tuple(t for t in ColumnType if t is not ColumnType.TALLY)

# The name the SLP sees for each type
COLUMN_TYPE_LABELS: dict[ColumnType, str] = {
  ColumnType.TEXT: "Text",
  ColumnType.INT: "Integer",
  ColumnType.DECIMAL: "Decimal",
  ColumnType.BOOLEAN: "True/False",
  ColumnType.DATE: "Date",
  ColumnType.CHOICE: "Choice",
  ColumnType.TALLY: "Tally",
}


def has_options(column_type: ColumnType) -> bool:
  """Whether a column or field of this type has a list of options (choices or tally marks)."""
  return column_type in (ColumnType.CHOICE, ColumnType.TALLY)


class ChoiceOption(NamedTuple):
  """
  One choice of a Choice column or field.

  Properties:
    value: The code written on the sheet, e.g. "+". May be several characters.
    description: What the code means, e.g. "correct". Never identifies a student.
  """
  value: str
  description: str = ""


class TallyOption(NamedTuple):
  """
  One mark of a Tally column or Running Tally section.

  Properties:
    mark: The one character written on the sheet, e.g. "Y".
    description: What the mark means, e.g. "yes". Never identifies a student.
  """
  mark: str
  description: str = ""


class TallySummary(NamedTuple):
  """
  What a tally holds once read.

  Properties:
    marks: The marks in reading order, each as configured, e.g. "YYNP".
    counts: How many times each option was marked, in option order, including zeros.
    total: How many marks there are.
    percentages: Each option's count / total, or None when total is 0.
  """
  marks: str
  counts: dict[str, int]
  total: int
  percentages: dict[str, float | None]


class ValueReadError(ValueError):
  """A value on the sheet doesn't fit its type. Raised by a single read."""

  def __init__(self, expected: str, found: str = "") -> None:
    """
    :param expected: What the value should be, e.g. "a whole number".
    :param found: The offending part of the text, such as one bad tally mark. Empty means
      the whole text.
    """
    super().__init__(expected)
    self.expected: str = expected
    self.found: str = found


class ValueProblem(NamedTuple):
  """
  One value on a sheet that doesn't fit its column or field.

  Properties:
    section: The section title, or the interpreter's fallback name such as "Table".
    item: The column or field name, or "" for a Running Tally section.
    row: Where in the section, e.g. "row 3" or "table 2, row 3", or "".
    value: The value as read.
    expected: What it should be, e.g. "a whole number".
    item_kind: What `item` names in the message: "column" or "field".
  """
  section: str
  item: str
  row: str
  value: str
  expected: str
  item_kind: str = "column"

  def message(self) -> str:
    """E.g. `"Words", column "Trials", row 3: "l" is not a whole number`."""
    where = [f'"{self.section}"']
    if self.item:
      where.append(f'{self.item_kind} "{self.item}"')
    if self.row:
      where.append(self.row)
    return f'{", ".join(where)}: "{self.value}" is not {self.expected}'


class InvalidValuesError(ValueError):
  """Values on a sheet don't fit the template. Holds every one, so they can all be fixed at once."""

  def __init__(self, problems: list[ValueProblem]) -> None:
    self.problems: list[ValueProblem] = list(problems)
    super().__init__("; ".join(problem.message() for problem in self.problems))


class OptionDescription(NamedTuple):
  """
  One choice or tally option and what it means, for the Workbook Key.

  Properties:
    section: The section title, or the interpreter's fallback name.
    item: The column or field, or "" for a Running Tally section.
    item_type: "Choice" or "Tally".
    option: The code, e.g. "+".
    description: What it means, e.g. "correct".
  """
  section: str
  item: str
  item_type: str
  option: str
  description: str


_SCALAR_TYPE_BY_COLUMN_TYPE: dict[ColumnType, DataSheetScalarType] = {
  ColumnType.TEXT: DataSheetScalarType.TEXT,
  ColumnType.INT: DataSheetScalarType.INT,
  ColumnType.DECIMAL: DataSheetScalarType.DECIMAL,
  ColumnType.BOOLEAN: DataSheetScalarType.BOOLEAN,
  ColumnType.DATE: DataSheetScalarType.DATE,
  ColumnType.CHOICE: DataSheetScalarType.CHOICE,
}


def scalar_type_for(column_type: ColumnType) -> DataSheetScalarType:
  """
  The Scalar Type a column of this type emits.

  :raises ValueError: For TALLY, which emits a Tally Summary of several types (tally_scalars)
  """
  if column_type is ColumnType.TALLY:
    raise ValueError("a Tally column emits several scalars; use tally_scalars")
  return _SCALAR_TYPE_BY_COLUMN_TYPE[column_type]


_INTEGER_PATTERN = re.compile(r"([+-]?\d+)(?:\.0+)?")
_DECIMAL_PATTERN = re.compile(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)")
_DATE_PATTERN = re.compile(r"(\d{1,2})([/-])(\d{1,2})\2(\d{4}|\d{2})")
_TRUE_TEXTS: frozenset[str] = frozenset({"y", "yes", "t", "true", "1", "✓", "✔", "☑"})
_FALSE_TEXTS: frozenset[str] = frozenset({"n", "no", "f", "false", "0"})


def _choice_phrase(values: Sequence[str]) -> str:
  return "one of " + ", ".join(values) if values else "one of the choices (there are none)"


def read_value(column_type: ColumnType, text: str, choices: Sequence[ChoiceOption] = ()) -> TypedValue:
  """
  Read one value written on a sheet as its type.

  Blank or whitespace text is None, whatever the type. Text is kept exactly as read.
  Every other type is trimmed first:

  - Integer: `7`, `-3`, `7.0`
  - Decimal: `3`, `2.5`, `.5`, with an optional sign
  - True/False, ignoring letter case: `Y yes T true 1 ✓ ✔ ☑` or `N no F false 0`
  - Date: `M/D/YYYY`, `M/D/YY`, `M-D-YYYY`, `M-D-YY`; a two-digit year is 20YY
  - Choice: a choice's value ignoring letter case and surrounding spaces, returned as
    configured

  :raises ValueReadError: If the text doesn't fit the type
  :raises ValueError: For TALLY, which is read with read_tally
  """
  if column_type is ColumnType.TALLY:
    raise ValueError("a Tally is read with read_tally")
  if not text.strip():
    return None
  if column_type is ColumnType.TEXT:
    return text

  trimmed = text.strip()
  if column_type is ColumnType.INT:
    match = _INTEGER_PATTERN.fullmatch(trimmed)
    if match is None:
      raise ValueReadError("a whole number")
    return int(match.group(1))

  if column_type is ColumnType.DECIMAL:
    if _DECIMAL_PATTERN.fullmatch(trimmed) is None:
      raise ValueReadError("a number")
    return float(trimmed)

  if column_type is ColumnType.BOOLEAN:
    folded = trimmed.casefold()
    if folded in _TRUE_TEXTS:
      return True
    if folded in _FALSE_TEXTS:
      return False
    raise ValueReadError("yes or no (Y, N, ✓, …)")

  if column_type is ColumnType.DATE:
    match = _DATE_PATTERN.fullmatch(trimmed)
    if match is None:
      raise ValueReadError("a date (month/day/year)")
    month, _separator, day, year_text = match.groups()
    # Expanded by hand: strptime's %y puts 69-99 in the 1900s
    year = 2000 + int(year_text) if len(year_text) == 2 else int(year_text)
    try:
      return date(year, int(month), int(day))
    except ValueError:
      raise ValueReadError("a date (month/day/year)") from None

  # CHOICE
  folded = trimmed.casefold()
  for choice in choices:
    if choice.value.strip().casefold() == folded:
      return choice.value
  raise ValueReadError(_choice_phrase([choice.value for choice in choices]))


def read_tally(text: str, options: Sequence[TallyOption]) -> TallySummary:
  """
  Read a tally: every non-space character is one mark, matched to an option ignoring
  letter case. Blank text is a tally with no marks.

  :raises ValueReadError: At the first character that isn't an option's mark, with
    `found` set to that character as read
  """
  mark_by_folded = {option.mark.casefold(): option.mark for option in options}
  counts = {option.mark: 0 for option in options}
  marks: list[str] = []
  for character in text:
    if character.isspace():
      continue
    mark = mark_by_folded.get(character.casefold())
    if mark is None:
      raise ValueReadError(_marks_phrase(options), found=character)
    marks.append(mark)
    counts[mark] += 1

  total = len(marks)
  percentages = {mark: (count / total if total else None) for mark, count in counts.items()}
  return TallySummary("".join(marks), counts, total, percentages)


def _marks_phrase(options: Sequence[TallyOption]) -> str:
  return "one of the marks " + ", ".join(option.mark for option in options)


def tally_keys(base: str, options: Sequence[TallyOption]) -> list[str]:
  """
  The keys of a Tally Summary, in order: the marks, a count per option, the total, and a
  percentage per option, e.g. "Attempts", "Attempts Y", …, "Attempts Total", "Attempts Y %", ….
  """
  return (
    [base]
    + [f"{base} {option.mark}" for option in options]
    + [f"{base} Total"]
    + [f"{base} {option.mark} %" for option in options]
  )


def tally_scalars(base: str, summary: TallySummary, options: Sequence[TallyOption]) -> dict[str, DataSheetScalarDto]:
  """
  A Tally Summary as scalars, keyed and ordered as tally_keys: the marks as TEXT, the
  counts and total as INT, and the percentages as PERCENT fractions (None when there are
  no marks).
  """
  keys = tally_keys(base, options)
  scalars = [DataSheetScalarDto(keys[0], summary.marks, DataSheetScalarType.TEXT, None, summary.marks or None)]
  for option in options:
    count = summary.counts.get(option.mark, 0)
    scalars.append(DataSheetScalarDto(f"{base} {option.mark}", str(count), DataSheetScalarType.INT, None, count))
  scalars.append(DataSheetScalarDto(f"{base} Total", str(summary.total), DataSheetScalarType.INT, None, summary.total))
  for option in options:
    fraction = summary.percentages.get(option.mark)
    text = "" if fraction is None else f"{fraction:.0%}"
    scalars.append(DataSheetScalarDto(f"{base} {option.mark} %", text, DataSheetScalarType.PERCENT, None, fraction))
  return {scalar.key: scalar for scalar in scalars}
