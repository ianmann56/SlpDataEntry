"""
The formula language of Formula calculations: a tokenizer and recursive-descent parser.

    formula    := condition
    condition  := expr (COMPARE expr)?          1 when the comparison holds, else 0
    expr       := term (("+" | "-") term)*
    term       := unary (("*" | "/") unary)*
    unary      := "-" unary | primary
    primary    := NUMBER | result_ref | sheet_ref | aggregate | count | "(" condition ")"
    aggregate  := ("SUM" | "AVERAGE") "(" condition ")"     the condition is worked out per row
    count      := "COUNT" "(" STRING ("," sheet_ref)+ ")"   per row: columns holding the choice
                | "COUNT" "(" condition ("," condition)* ")"  how many of the conditions hold
    COMPARE    := "=" | "<>" | "!=" | "<" | "<=" | ">" | ">="
    result_ref := "{" name "}"                     a lower-layer result: a number, or a Row List
    sheet_ref  := "[" section "/" item ("/" part)? "]"

Outside SUM and AVERAGE everything is one value for the sheet: `[Section/Value]` is a
Numeric Sheet Value. Inside them the condition is worked out for each row of one table:
`[Table/Column]` and `[Table/Column/Mark]` are that row's cells (or, for a section that
isn't a table, a Numeric Sheet Value), and `{Name}` may be a Row List. A quoted choice is
only compared, with `=` or `<>`, to one column: `[Table/Column] = "+"`.

Inside `[...]`, `{...}`, and strings, `\\` escapes the next character. Function names
ignore letter case. `<...>` starting with a letter is a placeholder inserted by the
Formula Legend, and is always a problem until it is replaced.

Formulas are only parsed here, never run. Every token and reference keeps its character
span, so problems can point at their place in the text, and renames can rewrite only the
references they touch.
"""

import re
from enum import Enum
from typing import NamedTuple


class ReferenceKind(Enum):
  """What a reference in a formula points at."""
  RESULT = "result"            # {name}: a number, or (inside an aggregation) possibly a Row List
  SHEET_VALUE = "sheet_value"  # [section/value], outside an aggregation
  COLUMN = "column"            # [section/column] or [section/column/part], inside SUM or AVERAGE.
                               # [section/value] of a section that isn't a table is a sheet value.


class FormulaReference(NamedTuple):
  """
  One reference in a formula.

  Properties:
    kind: What it points at.
    parts: The names, unescaped: (name,), (section, item), or (section, column, part).
    start: Offset of its opening bracket.
    end: Offset just past its closing bracket.
    choice: For a column in a choice COUNT or compared with a quoted choice, that choice. None otherwise.
    choice_start: Offset of that choice's opening quote, or -1.
    choice_end: Offset just past that choice's closing quote, or -1.
    aggregate_start: Offset of the enclosing SUM or AVERAGE, so the columns of one Row
      Measure can be grouped, and a result used as a Row List told from one used as a
      number. -1 outside an aggregation.
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
    aggregates: The (start, end) of every SUM and AVERAGE, in the order they close.
  """
  problem: FormulaProblem | None
  references: list[FormulaReference]
  aggregates: tuple[tuple[int, int], ...] = ()


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


# A placeholder the Formula Legend inserts, like <row measure>. It starts with a letter, so
# it is never a comparison like "< 3" or "<>"
_PLACEHOLDER = re.compile(r"<[A-Za-z][^<>]*>")


def _operation(label: str, insert_text: str, description: str) -> LegendOperation:
  spans = [(match.start(), match.end()) for match in _PLACEHOLDER.finditer(insert_text)]
  return LegendOperation(label, insert_text, spans, description)


# The operations a formula may use, in the order the Formula Legend lists them
OPERATIONS: list[LegendOperation] = [
  _operation("SUM(row measure)", "SUM(<row measure>)",
             "Total over every row of a table. Inside, work out each row's value: a column, a per-row "
             "result, COUNT, a comparison, or arithmetic on them"),
  _operation("AVERAGE(row measure)", "AVERAGE(<row measure>)",
             "Average over the rows that have a value. Averaging a comparison gives the share of rows (0 to 1)"),
  _operation('COUNT("choice", column, …)', 'COUNT("<choice>", <column>)',
             "Per row, how many of the columns hold the choice (True/False columns: \"True\" or \"False\"). "
             "Only inside SUM or AVERAGE"),
  _operation("COUNT(condition, …)", "COUNT(<condition>, <condition>)",
             "How many of the conditions hold. Inside SUM or AVERAGE it is worked out for each row"),
  _operation("+  add", " + ", "Add two values"),
  _operation("−  subtract", " - ", "Subtract the second value from the first"),
  _operation("×  multiply", " * ", "Multiply two values"),
  _operation("÷  divide", " / ", "Divide the first value by the second"),
  _operation("=  equals", " = ",
             '1 if the values are equal, else 0. Compare a choice column with a quoted choice: [Table/Column] = "+"'),
  _operation("<>  is not", " <> ", "1 if the values differ, else 0. Also works with a quoted choice"),
  _operation("<  is less than", " < ", "1 if the first value is less than the second, else 0"),
  _operation("<=  is at most", " <= ", "1 if the first value is at most the second, else 0"),
  _operation(">  is more than", " > ", "1 if the first value is more than the second, else 0"),
  _operation(">=  is at least", " >= ", "1 if the first value is at least the second, else 0"),
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
  COMPARE = "compare"
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
_COMPARISONS: tuple[str, ...] = ("<=", ">=", "<>", "!=", "=", "<", ">")  # two-character ones first
_CHOICE_COMPARISONS: frozenset[str] = frozenset({"=", "<>", "!="})


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
    elif character == "<" and index + 1 < len(text) and text[index + 1].isalpha():
      close = text.find(">", start)
      if close < 0:
        raise _Problem('"<" is never closed', start, len(text))
      index = close + 1
      tokens.append(_Token(_Kind.PLACEHOLDER, text[start:index], start, index))
    elif (comparison := next((c for c in _COMPARISONS if text.startswith(c, index)), None)) is not None:
      index += len(comparison)
      tokens.append(_Token(_Kind.COMPARE, comparison, start, index))
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

class _Side(NamedTuple):
  """One side of a comparison, as parsed."""
  kind: str              # "string" (a quoted choice), "reference" (one [..] alone), or "value"
  start: int
  end: int
  token: _Token          # its first token
  reference_index: int   # for "reference", its index in the parser's references; else -1
  is_condition: bool     # whether it is itself a comparison or COUNT of conditions, in parentheses


class _Parser:
  def __init__(self, tokens: list[_Token]) -> None:
    self._tokens = tokens
    self._position = 0
    self.references: list[FormulaReference] = []
    self.aggregates: list[tuple[int, int]] = []
    # The SUM or AVERAGE being parsed, whose inside is worked out per row; None outside one
    self._aggregate: _Token | None = None

  def _peek(self, ahead: int = 0) -> _Token:
    return self._tokens[min(self._position + ahead, len(self._tokens) - 1)]

  def _next(self) -> _Token:
    token = self._tokens[self._position]
    if token.kind is not _Kind.END:
      self._position += 1
    return token

  def _last_end(self) -> int:
    return self._tokens[self._position - 1].end if self._position else 0

  def _is_symbol(self, symbol: str) -> bool:
    token = self._peek()
    return token.kind is _Kind.SYMBOL and token.text == symbol

  def _expect_symbol(self, symbol: str, context: str) -> _Token:
    token = self._peek()
    if token.kind is _Kind.SYMBOL and token.text == symbol:
      return self._next()
    raise _Problem(f'Expected "{symbol}" {context}', token.start, token.end)

  def parse(self) -> None:
    self._condition()
    token = self._peek()
    if token.kind is not _Kind.END:
      if token.kind is _Kind.SYMBOL and token.text in ",)":
        raise _Problem(f'Unexpected "{token.text}"', token.start, token.end)
      raise _Problem(f'Expected an operator (+, -, *, /) before "{token.text}"', token.start, token.end)

  # ----- Comparisons -----

  def _condition(self) -> bool:
    """Parse an expression, or a comparison of two. Returns whether it is a condition (gives 1 or 0)."""
    left = self._side()
    if self._peek().kind is not _Kind.COMPARE:
      if left.kind == "string":
        raise _Problem('Compare a quoted choice with a column, like [Table/Column] = "+"', left.start, left.end)
      return left.is_condition
    operator = self._next()
    if self._peek().kind is _Kind.END:
      raise _Problem(f'Expected a value after "{operator.text}"', operator.end, operator.end)
    right = self._side()
    extra = self._peek()
    if extra.kind is _Kind.COMPARE:
      raise _Problem("Compare two values at a time. To check several conditions, use COUNT(…)",
                     extra.start, extra.end)
    self._choice_comparison(left, operator, right)
    return True

  def _side(self) -> _Side:
    token = self._peek()
    if token.kind is _Kind.STRING:
      self._next()
      return _Side("string", token.start, token.end, token, -1, False)
    position, reference_count = self._position, len(self.references)
    is_condition = self._expression()
    alone = (token.kind is _Kind.SHEET and self._position == position + 1
             and len(self.references) == reference_count + 1)
    return _Side("reference" if alone else "value", token.start, self._last_end(), token,
                 reference_count if alone else -1, is_condition)

  def _choice_comparison(self, left: _Side, operator: _Token, right: _Side) -> None:
    """Check a comparison with a quoted choice, and attach the choice to the column it is compared with."""
    if left.kind != "string" and right.kind != "string":
      return
    if left.kind == "string" and right.kind == "string":
      raise _Problem("Compare a column with a choice, not two choices", left.start, right.end)
    choice, other = (left, right) if left.kind == "string" else (right, left)
    if operator.text not in _CHOICE_COMPARISONS:
      raise _Problem('A choice can only be compared with = or <>', operator.start, operator.end)
    if self._aggregate is None:
      raise _Problem("A choice can only be compared with a table column, inside SUM, AVERAGE, or COUNT",
                     choice.start, choice.end)
    if other.kind != "reference":
      raise _Problem('Compare a choice with one column, like [Table/Column] = "+"', other.start, other.end)
    self._check_choice(choice.token)
    reference = self.references[other.reference_index]
    if len(reference.parts) != 2:
      raise _Problem("A column compared with a choice is written [Table/Column]", reference.start, reference.end)
    self.references[other.reference_index] = reference._replace(
      choice=choice.token.value, choice_start=choice.token.start, choice_end=choice.token.end)

  @staticmethod
  def _check_choice(choice: _Token) -> None:
    if _PLACEHOLDER.fullmatch(choice.value):
      raise _Problem(f"Fill in {choice.value}", choice.start, choice.end)
    if not choice.value.strip():
      raise _Problem("Write the choice inside the quotes", choice.start, choice.end)

  # ----- Arithmetic -----

  def _expression(self) -> bool:
    is_condition = self._term()
    while self._is_symbol("+") or self._is_symbol("-"):
      operator = self._next()
      self._operand_after(operator, self._term)
      is_condition = False
    return is_condition

  def _term(self) -> bool:
    is_condition = self._unary()
    while self._is_symbol("*") or self._is_symbol("/"):
      operator = self._next()
      self._operand_after(operator, self._unary)
      is_condition = False
    return is_condition

  def _operand_after(self, operator: _Token, parse_operand) -> None:
    if self._peek().kind is _Kind.END:
      raise _Problem(f'Expected a value after "{operator.text}"', operator.end, operator.end)
    parse_operand()

  def _unary(self) -> bool:
    if self._is_symbol("-"):
      operator = self._next()
      self._operand_after(operator, self._unary)
      return False
    return self._primary()

  def _primary(self) -> bool:
    """Parse one value. Returns whether it is a condition in parentheses."""
    token = self._peek()
    if token.kind is _Kind.NUMBER:
      self._next()
    elif token.kind is _Kind.RESULT:
      self._next()
      if not token.value.strip():
        raise _Problem("Write a calculation's name inside { }", token.start, token.end)
      self.references.append(FormulaReference(
        ReferenceKind.RESULT, (token.value,), token.start, token.end,
        aggregate_start=self._aggregate.start if self._aggregate is not None else -1,
      ))
    elif token.kind is _Kind.SHEET:
      self._next()
      if self._aggregate is not None:
        self._column(token)
      elif len(token.parts) == 3:
        raise _Problem(f'{token.text} is a table column, so it can only be used inside SUM or AVERAGE',
                       token.start, token.end)
      elif len(token.parts) != 2 or not all(part.strip() for part in token.parts):
        raise _Problem("A sheet value is written [Section/Value]", token.start, token.end)
      else:
        self.references.append(FormulaReference(ReferenceKind.SHEET_VALUE, token.parts, token.start, token.end))
    elif token.kind is _Kind.WORD:
      self._function(token)
    elif token.kind is _Kind.PLACEHOLDER:
      raise _Problem(f"Fill in {token.text}", token.start, token.end)
    elif self._is_symbol("("):
      opening = self._next()
      if self._is_symbol(")"):
        raise _Problem("Write something inside ( )", opening.start, self._peek().end)
      is_condition = self._condition()
      self._expect_symbol(")", 'to close "("')
      return is_condition
    elif token.kind is _Kind.END:
      raise _Problem("Expected a number, a reference, or a function", token.start, token.end)
    elif token.kind is _Kind.STRING:
      raise _Problem('Compare a quoted choice with a column, like [Table/Column] = "+"', token.start, token.end)
    elif token.kind is _Kind.COMPARE:
      raise _Problem(f'Expected a value before "{token.text}"', token.start, token.end)
    else:
      raise _Problem(f'Unexpected "{token.text}"', token.start, token.end)
    return False

  # ----- Functions -----

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
      self._count(word)
      return
    if self._aggregate is not None:
      raise _Problem(f"{word.text.upper()} can't be used inside another SUM or AVERAGE", word.start, word.end)
    self._expect_symbol("(", f'after "{word.text}"')
    if self._is_symbol(")"):
      token = self._peek()
      raise _Problem(
        f'{word.text.upper()} takes one row measure: a column like [Table/Column], '
        'a per-row result like {Name}, COUNT(...), or a comparison',
        token.start, token.end,
      )
    self._aggregate = word
    try:
      self._condition()
    finally:
      self._aggregate = None
    if self._is_symbol(","):
      comma = self._next()
      raise _Problem(f"{word.text.upper()} takes one row measure", comma.start, comma.end)
    closing = self._expect_symbol(")", f'to close "{word.text}("')
    self.aggregates.append((word.start, closing.end))

  def _column(self, token: _Token, choice: _Token | None = None) -> None:
    allowed = (2,) if choice is not None else (2, 3)
    if len(token.parts) not in allowed or not all(part.strip() for part in token.parts):
      shape = "[Table/Column]" if choice is not None else "[Table/Column] or [Table/Column/Mark]"
      raise _Problem(f"A column is written {shape}", token.start, token.end)
    assert self._aggregate is not None
    self.references.append(FormulaReference(
      ReferenceKind.COLUMN, token.parts, token.start, token.end,
      choice=choice.value if choice is not None else None,
      choice_start=choice.start if choice is not None else -1,
      choice_end=choice.end if choice is not None else -1,
      aggregate_start=self._aggregate.start,
    ))

  def _count(self, count: _Token) -> None:
    self._expect_symbol("(", 'after "COUNT"')
    first = self._peek()
    second = self._peek(1)
    if first.kind is _Kind.STRING and second.kind is _Kind.SYMBOL and second.text == ",":
      self._choice_count(count)
      return
    if self._is_symbol(")"):
      raise _Problem("COUNT needs at least one condition, like [Table/Column] >= 3", first.start, first.end)
    while True:
      start = self._peek().start
      if not self._condition():
        raise _Problem("COUNT counts conditions, like [Table/Column] >= 3 or {Result} > 0",
                       start, self._last_end())
      if not self._is_symbol(","):
        break
      self._next()
    self._expect_symbol(")", 'to close "COUNT("')

  def _choice_count(self, count: _Token) -> None:
    """COUNT("choice", column, …): per row, how many of the columns hold the choice."""
    choice = self._next()
    if self._aggregate is None:
      raise _Problem('COUNT of a choice in columns can only be used inside SUM or AVERAGE. '
                     'Outside them, COUNT counts conditions', count.start, count.end)
    self._check_choice(choice)
    while self._is_symbol(","):
      self._next()
      column = self._peek()
      if column.kind is _Kind.PLACEHOLDER:
        raise _Problem(f"Fill in {column.text}", column.start, column.end)
      if column.kind is not _Kind.SHEET:
        raise _Problem("Expected a column like [Table/Column]", column.start, column.end)
      self._next()
      self._column(column, choice)
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
  return FormulaParse(None, parser.references, tuple(parser.aggregates))
