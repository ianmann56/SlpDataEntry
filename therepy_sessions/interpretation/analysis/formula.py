"""
The formula language of Formula calculations: a tokenizer and recursive-descent parser.

    formula    := expr
    expr       := term (("+" | "-") term)*
    term       := unary (("*" | "/") unary)*
    unary      := "-" unary | primary
    primary    := NUMBER | result_ref | value_ref | aggregate | "(" expr ")"
    aggregate  := ("SUM" | "AVERAGE") "(" measure ")"
    measure    := column_ref | "COUNT" "(" STRING ("," column_ref)+ ")"
    result_ref := "{" name "}"                            a lower-layer calculation's result
    value_ref  := "[" section "/" item "]"                a Numeric Sheet Value
    column_ref := "[" section "/" column ("/" part)? "]"  a table column, in a Row Measure

Inside `[...]`, `{...}`, and strings, `\\` escapes the next character. Function names
ignore letter case. `<...>` is a placeholder inserted by the Formula Legend, and is
always a problem until it is replaced.

Formulas are only parsed here, never run. Every token and reference keeps its character
span, so problems can point at their place in the text, and renames can rewrite only the
references they touch.
"""

import re
from enum import Enum
from typing import NamedTuple


class ReferenceKind(Enum):
  """What a reference in a formula points at."""
  RESULT = "result"            # {name}
  SHEET_VALUE = "sheet_value"  # [section/value], outside an aggregation
  COLUMN = "column"            # [section/column] or [section/column/part], inside SUM or AVERAGE


class FormulaReference(NamedTuple):
  """
  One reference in a formula.

  Properties:
    kind: What it points at.
    parts: The names, unescaped: (name,), (section, item), or (section, column, part).
    start: Offset of its opening bracket.
    end: Offset just past its closing bracket.
    choice: For a column inside COUNT, the choice it counts. None otherwise.
    choice_start: Offset of that choice's opening quote, or -1.
    choice_end: Offset just past that choice's closing quote, or -1.
    aggregate_start: Offset of the enclosing SUM or AVERAGE, so the columns of one Row
      Measure can be grouped. -1 outside an aggregation.
  """
  kind: ReferenceKind
  parts: tuple[str, ...]
  start: int
  end: int
  choice: str | None = None
  choice_start: int = -1
  choice_end: int = -1
  aggregate_start: int = -1


class FormulaProblem(NamedTuple):
  """
  Why a formula can't be used, and where.

  Properties:
    message: What is wrong, in the SLP's terms.
    start: Offset of the problem in the formula text, 0-based.
    end: Offset just past it. Equal to start for something missing at a position.
  """
  message: str
  start: int
  end: int


class FormulaParse(NamedTuple):
  """
  The result of parsing a formula.

  Properties:
    problem: The first syntax problem, or None when the formula parses.
    references: Every reference, in text order. Empty when there is a problem.
  """
  problem: FormulaProblem | None
  references: list[FormulaReference]


class LegendOperation(NamedTuple):
  """
  One operation the Formula Legend offers.

  Properties:
    label: How the legend shows it, with its parameters.
    insert_text: What clicking it inserts.
    placeholder_spans: The (start, end) of each placeholder in insert_text.
    description: What it does.
  """
  label: str
  insert_text: str
  placeholder_spans: list[tuple[int, int]]
  description: str


def _operation(label: str, insert_text: str, description: str) -> LegendOperation:
  spans = [(match.start(), match.end()) for match in re.finditer(r"<[^<>]*>", insert_text)]
  return LegendOperation(label, insert_text, spans, description)


# The operations a formula may use, in the order the Formula Legend lists them
OPERATIONS: list[LegendOperation] = [
  _operation("SUM(row measure)", "SUM(<row measure>)", "Total of a row measure over every row of a table"),
  _operation("AVERAGE(row measure)", "AVERAGE(<row measure>)",
             "Average of a row measure over the rows that have a value"),
  _operation('COUNT("choice", column, …)', 'COUNT("<choice>", <column>)',
             "Per row, how many of the columns hold the choice. Only inside SUM or AVERAGE"),
  _operation("+  add", " + ", "Add two values"),
  _operation("−  subtract", " - ", "Subtract the second value from the first"),
  _operation("×  multiply", " * ", "Multiply two values"),
  _operation("÷  divide", " / ", "Divide the first value by the second"),
  _operation("( )  group", "(<expression>)", "Work out the part inside first"),
]

_AGGREGATES: frozenset[str] = frozenset({"SUM", "AVERAGE"})
_FUNCTIONS: frozenset[str] = _AGGREGATES | {"COUNT"}
_NAME_ESCAPES: frozenset[str] = frozenset({"\\", "/", "]", "}"})


def escape_name(name: str) -> str:
  """Escape `\\`, `/`, `]`, and `}` with `\\`, for writing a name inside a reference."""
  return "".join(f"\\{character}" if character in _NAME_ESCAPES else character for character in name)


def quote_choice(choice: str) -> str:
  """Write a choice as a formula string: in double quotes, with `\\` and `"` escaped."""
  escaped = choice.replace("\\", "\\\\").replace('"', '\\"')
  return f'"{escaped}"'


# ----- Tokens -----

class _Kind(Enum):
  NUMBER = "number"
  STRING = "string"
  RESULT = "result"
  SHEET = "sheet"
  WORD = "word"
  PLACEHOLDER = "placeholder"
  SYMBOL = "symbol"
  END = "end"


class _Token(NamedTuple):
  kind: _Kind
  text: str                 # the token as written
  start: int
  end: int
  value: str = ""           # a string's or result name's unescaped value; a word in upper case
  parts: tuple[str, ...] = ()


class _Problem(Exception):
  """Raised inside the parser to stop at the first problem."""

  def __init__(self, message: str, start: int, end: int) -> None:
    super().__init__(message)
    self.problem: FormulaProblem = FormulaProblem(message, start, end)


_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?|\.\d+")
_WORD_PATTERN = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_SYMBOLS: frozenset[str] = frozenset("+-*/(),")


def _read_bracketed(text: str, start: int, closing: str, split: bool) -> tuple[list[str], int]:
  """
  Read a bracketed name from the character after `start`, unescaping it.

  Returns:
    The parts (one unless `split`, which splits on unescaped "/"), and the offset just
    past the closing bracket
  """
  parts: list[str] = []
  current: list[str] = []
  index = start + 1
  while index < len(text):
    character = text[index]
    if character == "\\" and index + 1 < len(text):
      current.append(text[index + 1])
      index += 2
      continue
    if character == closing:
      parts.append("".join(current))
      return parts, index + 1
    if split and character == "/":
      parts.append("".join(current))
      current = []
    else:
      current.append(character)
    index += 1
  raise _Problem(f'"{text[start]}" is never closed', start, len(text))


def _read_string(text: str, start: int) -> tuple[str, int]:
  """Read a double-quoted string from `start`. Returns its value and the offset past it."""
  value: list[str] = []
  index = start + 1
  while index < len(text):
    character = text[index]
    if character == "\\" and index + 1 < len(text):
      value.append(text[index + 1])
      index += 2
      continue
    if character == '"':
      return "".join(value), index + 1
    value.append(character)
    index += 1
  raise _Problem('The quote " is never closed', start, len(text))


def _tokenize(text: str) -> list[_Token]:
  tokens: list[_Token] = []
  index = 0
  while index < len(text):
    character = text[index]
    if character.isspace():
      index += 1
      continue
    start = index
    if character == "[":
      parts, index = _read_bracketed(text, start, "]", split=True)
      tokens.append(_Token(_Kind.SHEET, text[start:index], start, index, parts=tuple(parts)))
    elif character == "{":
      parts, index = _read_bracketed(text, start, "}", split=False)
      tokens.append(_Token(_Kind.RESULT, text[start:index], start, index, value=parts[0]))
    elif character == '"':
      value, index = _read_string(text, start)
      tokens.append(_Token(_Kind.STRING, text[start:index], start, index, value=value))
    elif character == "<":
      close = text.find(">", start)
      if close < 0:
        raise _Problem('"<" is never closed', start, len(text))
      index = close + 1
      tokens.append(_Token(_Kind.PLACEHOLDER, text[start:index], start, index))
    elif character in _SYMBOLS:
      index += 1
      tokens.append(_Token(_Kind.SYMBOL, character, start, index))
    elif (match := _NUMBER_PATTERN.match(text, index)) is not None:
      index = match.end()
      tokens.append(_Token(_Kind.NUMBER, match.group(), start, index))
    elif (match := _WORD_PATTERN.match(text, index)) is not None:
      index = match.end()
      tokens.append(_Token(_Kind.WORD, match.group(), start, index, value=match.group().upper()))
    else:
      raise _Problem(f'Unexpected "{character}"', start, start + 1)
  tokens.append(_Token(_Kind.END, "", len(text), len(text)))
  return tokens


# ----- Parser -----

class _Parser:
  def __init__(self, tokens: list[_Token]) -> None:
    self._tokens = tokens
    self._position = 0
    self.references: list[FormulaReference] = []

  def _peek(self) -> _Token:
    return self._tokens[self._position]

  def _next(self) -> _Token:
    token = self._tokens[self._position]
    if token.kind is not _Kind.END:
      self._position += 1
    return token

  def _is_symbol(self, symbol: str) -> bool:
    token = self._peek()
    return token.kind is _Kind.SYMBOL and token.text == symbol

  def _expect_symbol(self, symbol: str, context: str) -> _Token:
    token = self._peek()
    if token.kind is _Kind.SYMBOL and token.text == symbol:
      return self._next()
    raise _Problem(f'Expected "{symbol}" {context}', token.start, token.end)

  def parse(self) -> None:
    self._expression()
    token = self._peek()
    if token.kind is not _Kind.END:
      if token.kind is _Kind.SYMBOL and token.text in ",)":
        raise _Problem(f'Unexpected "{token.text}"', token.start, token.end)
      raise _Problem(f'Expected an operator (+, -, *, /) before "{token.text}"', token.start, token.end)

  def _expression(self) -> None:
    self._term()
    while self._is_symbol("+") or self._is_symbol("-"):
      operator = self._next()
      self._operand_after(operator, self._term)

  def _term(self) -> None:
    self._unary()
    while self._is_symbol("*") or self._is_symbol("/"):
      operator = self._next()
      self._operand_after(operator, self._unary)

  def _operand_after(self, operator: _Token, parse_operand) -> None:
    if self._peek().kind is _Kind.END:
      raise _Problem(f'Expected a value after "{operator.text}"', operator.end, operator.end)
    parse_operand()

  def _unary(self) -> None:
    if self._is_symbol("-"):
      operator = self._next()
      self._operand_after(operator, self._unary)
      return
    self._primary()

  def _primary(self) -> None:
    token = self._peek()
    if token.kind is _Kind.NUMBER:
      self._next()
    elif token.kind is _Kind.RESULT:
      self._next()
      if not token.value.strip():
        raise _Problem("Write a calculation's name inside { }", token.start, token.end)
      self.references.append(FormulaReference(ReferenceKind.RESULT, (token.value,), token.start, token.end))
    elif token.kind is _Kind.SHEET:
      self._next()
      if len(token.parts) == 3:
        raise _Problem(f'{token.text} is a table column, so it can only be used inside SUM or AVERAGE',
                       token.start, token.end)
      if len(token.parts) != 2 or not all(part.strip() for part in token.parts):
        raise _Problem("A sheet value is written [Section/Value]", token.start, token.end)
      self.references.append(FormulaReference(ReferenceKind.SHEET_VALUE, token.parts, token.start, token.end))
    elif token.kind is _Kind.WORD:
      self._function(token)
    elif token.kind is _Kind.PLACEHOLDER:
      raise _Problem(f"Fill in {token.text}", token.start, token.end)
    elif self._is_symbol("("):
      opening = self._next()
      if self._is_symbol(")"):
        raise _Problem("Write something inside ( )", opening.start, self._peek().end)
      self._expression()
      self._expect_symbol(")", 'to close "("')
    elif token.kind is _Kind.END:
      raise _Problem("Expected a number, a reference, or a function", token.start, token.end)
    elif token.kind is _Kind.STRING:
      raise _Problem('A quoted choice can only be used inside COUNT', token.start, token.end)
    else:
      raise _Problem(f'Unexpected "{token.text}"', token.start, token.end)

  def _function(self, word: _Token) -> None:
    self._next()
    if word.value not in _FUNCTIONS:
      if self._is_symbol("("):
        raise _Problem(f'Unknown function "{word.text}"', word.start, word.end)
      raise _Problem(
        "Names go in brackets: {Name} for a calculation, or [Section/Item] for sheet data",
        word.start, word.end,
      )
    if word.value == "COUNT":
      raise _Problem("COUNT can only be used inside SUM or AVERAGE", word.start, word.end)
    self._expect_symbol("(", f'after "{word.text}"')
    self._measure(word)
    if self._is_symbol(","):
      comma = self._next()
      raise _Problem(f"{word.text.upper()} takes one row measure", comma.start, comma.end)
    self._expect_symbol(")", f'to close "{word.text}("')

  def _measure(self, aggregate: _Token) -> None:
    token = self._peek()
    if token.kind is _Kind.SHEET:
      self._next()
      self._column(token, aggregate)
    elif token.kind is _Kind.WORD and token.value == "COUNT":
      self._next()
      self._count(token, aggregate)
    elif token.kind is _Kind.PLACEHOLDER:
      raise _Problem(f"Fill in {token.text}", token.start, token.end)
    else:
      raise _Problem(
        f'{aggregate.text.upper()} takes one row measure: a column like [Table/Column], or COUNT(...)',
        token.start, token.end,
      )

  def _column(self, token: _Token, aggregate: _Token, choice: _Token | None = None) -> None:
    allowed = (2,) if choice is not None else (2, 3)
    if len(token.parts) not in allowed or not all(part.strip() for part in token.parts):
      shape = "[Table/Column]" if choice is not None else "[Table/Column] or [Table/Column/Mark]"
      raise _Problem(f"A column is written {shape}", token.start, token.end)
    self.references.append(FormulaReference(
      ReferenceKind.COLUMN, token.parts, token.start, token.end,
      choice=choice.value if choice is not None else None,
      choice_start=choice.start if choice is not None else -1,
      choice_end=choice.end if choice is not None else -1,
      aggregate_start=aggregate.start,
    ))

  def _count(self, count: _Token, aggregate: _Token) -> None:
    self._expect_symbol("(", 'after "COUNT"')
    choice = self._peek()
    if choice.kind is not _Kind.STRING:
      if choice.kind is _Kind.PLACEHOLDER:
        raise _Problem(f"Fill in {choice.text}", choice.start, choice.end)
      raise _Problem('COUNT starts with the choice to count, in quotes, like "+"', choice.start, choice.end)
    self._next()
    if re.fullmatch(r"<[^<>]*>", choice.value):
      raise _Problem(f"Fill in {choice.value}", choice.start, choice.end)
    if not choice.value.strip():
      raise _Problem("Write the choice to count inside the quotes", choice.start, choice.end)
    if not self._is_symbol(","):
      raise _Problem("COUNT needs at least one column after the choice", self._peek().start, self._peek().end)
    while self._is_symbol(","):
      self._next()
      column = self._peek()
      if column.kind is _Kind.PLACEHOLDER:
        raise _Problem(f"Fill in {column.text}", column.start, column.end)
      if column.kind is not _Kind.SHEET:
        raise _Problem("Expected a column like [Table/Column]", column.start, column.end)
      self._next()
      self._column(column, aggregate, choice)
    self._expect_symbol(")", 'to close "COUNT("')


def parse_formula(text: str) -> FormulaParse:
  """Parse a formula, returning its references in text order, or its first syntax problem."""
  try:
    parser = _Parser(_tokenize(text))
    if parser._peek().kind is _Kind.END:
      return FormulaParse(FormulaProblem("Write a formula", 0, 0), [])
    parser.parse()
  except _Problem as e:
    return FormulaParse(e.problem, [])
  return FormulaParse(None, parser.references)
