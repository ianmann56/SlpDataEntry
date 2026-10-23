# Contract: Analysis Model, Formulas, and Rules

The public, typed interface of `interpretation/analysis/` and the template changes. All
of it is pure (layers rule 3): no Tkinter and no I/O. The entities are in
[../data-model.md](../data-model.md).

## Modules

| Module | Public members |
| --- | --- |
| `analysis/parts.py` | `TableColumnPart`, `SectionParts` (imports only `value_types`, so the interpreter base can use it without a cycle) |
| `analysis/model.py` | `DataSheetAnalysis`, `AnalysisLayer`, `Calculation`, `RowAggregate`, `NumberColumnMeasure`, `TallyCountMeasure`, `ChoiceCountMeasure`, `RowMeasure`, `Combination`, `Arithmetic`, `ArithmeticOperation`, `ResultOperand`, `SheetValueOperand`, `NumberOperand`, `Operand`, `Formula` |
| `analysis/formula.py` | `parse_formula`, `FormulaParse`, `FormulaProblem`, `FormulaReference`, `ReferenceKind`, `escape_name`, `OPERATIONS` |
| `analysis/scope.py` | `analysis_scope`, `AnalysisScope`, `ScopeEntry`, `ScopeTable`, `section_name_counts` |
| `analysis/rules.py` | `analysis_problems`, `calculation_problems`, `formula_problems`, `calculations_using`, `describe_calculation` |
| `analysis/renames.py` | `PartKind`, `PartRename`, `apply_renames` |
| `analysis/serialization.py` | `analysis_to_json`, `analysis_from_json` |

## Model

The records are frozen dataclasses (type-declarations rule 4). `DataSheetAnalysis` and
`AnalysisLayer` hold tuples, so they stay comparable, and are changed only by building
new values:

```python
DataSheetAnalysis.empty() -> DataSheetAnalysis
DataSheetAnalysis.with_layer_added() -> DataSheetAnalysis
DataSheetAnalysis.with_highest_layer_removed() -> DataSheetAnalysis
DataSheetAnalysis.with_calculation(layer_number: int, index: int | None, calculation: Calculation) -> DataSheetAnalysis
    # index None appends; otherwise replaces at index
DataSheetAnalysis.with_calculation_removed(layer_number: int, index: int) -> DataSheetAnalysis
DataSheetAnalysis.with_calculation_moved(layer_number: int, index: int, offset: int) -> tuple[DataSheetAnalysis, int]
DataSheetAnalysis.is_empty: bool
```

`with_calculation_removed` does no dependency check, because the model can't import
the rules. Callers first check `calculations_using(...)` in `rules.py`, and refuse the
removal while it is not empty (FR-017). `with_highest_layer_removed` raises `ValueError`
when there are no layers.

`Calculation.result_references() -> list[str]` returns the calculation names its
definition uses: `ResultOperand`s for Arithmetic, and the `RESULT` references of a
parsed Formula (none if it doesn't parse). `model.py` imports `formula.py`, never the
reverse.

## Formula grammar

The grammar is in research R3. Lexical details:

| Token | Form |
| --- | --- |
| Number | `\d+(\.\d+)?` or `\.\d+` |
| String | `"` … `"`, where `\"` and `\\` are escapes |
| Result reference | `{` name `}`, where `\` escapes the next character |
| Sheet reference | `[` part (`/` part){1,2} `]`, where `\` escapes the next character in a part |
| Function | `SUM`, `AVERAGE`, `COUNT`, ignoring letter case |
| Placeholder | `<` text `>`, inserted by the legend; always a problem until replaced |
| Operators | `+ - * / ( ) ,` |
| Space | Ignored between tokens |

Names inside references are compared with the template's names ignoring letter case
and surrounding spaces.

```python
def escape_name(name: str) -> str
    """Escape `\`, `/`, `]`, and `}` with `\`, for inserting a name into a reference."""

def quote_choice(choice: str) -> str
    """Write a choice as a formula string, in double quotes, with `\` and `"` escaped."""

def parse_formula(text: str) -> FormulaParse

class FormulaProblem(NamedTuple):
    message: str     # in the SLP's terms, e.g. 'Expected ")" to close "SUM("'
    start: int       # character offset into the text, 0-based
    end: int         # exclusive; start == end for "missing" problems at a position

class ReferenceKind(Enum):
    RESULT = "result"            # {name}
    SHEET_VALUE = "sheet_value"  # [section/value], outside an aggregation
    COLUMN = "column"            # [section/column] or [section/column/part], inside SUM/AVERAGE

class FormulaReference(NamedTuple):
    kind: ReferenceKind
    parts: tuple[str, ...]       # unescaped: (name,) | (section, item) | (section, column, part)
    start: int
    end: int                     # span of the whole bracketed reference, brackets included
    choice: str | None = None    # for a COLUMN inside COUNT, its choice string
    choice_start: int = -1       # span of that choice's quoted string, for rewriting it on a rename
    choice_end: int = -1
    aggregate_start: int = -1    # start of the enclosing SUM/AVERAGE, to group a measure's columns

class FormulaParse(NamedTuple):
    problem: FormulaProblem | None       # the first syntax problem, or None
    references: list[FormulaReference]   # every reference, in text order (empty when problem is set)
```

`OPERATIONS: list[LegendOperation]` lists the Formula Legend's operations, each a
`NamedTuple(label: str, insert_text: str, placeholder_spans: list[tuple[int, int]], description: str)`:

| Label | Inserts |
| --- | --- |
| `SUM(row measure)` | `SUM(<row measure>)` |
| `AVERAGE(row measure)` | `AVERAGE(<row measure>)` |
| `COUNT("choice", column, …)` (only inside SUM or AVERAGE) | `COUNT("<choice>", <column>)` |
| `+  add` | ` + ` |
| `−  subtract` | ` - ` |
| `×  multiply` | ` * ` |
| `÷  divide` | ` / ` |
| `( )  group` | `(<expression>)` |

## Scope

```python
def section_name_counts(interpreters: list[SessionDataSectionInterpreterBase]) -> dict[str, int]
    """Section Names folded (casefold, stripped) → how many sections use them."""

def analysis_scope(
    interpreters: list[SessionDataSectionInterpreterBase],
    analysis: DataSheetAnalysis,
    layer_number: int,
) -> AnalysisScope

class ScopeEntry(NamedTuple):
    label: str          # e.g. "Session Info › Prompts given", or a calculation name
    reference: str      # exact formula text, e.g. "[Session Info/Prompts given]" or "{Accuracy}"
    description: str    # Calculation Description, or "" for sheet values

class ScopeTable(NamedTuple):
    section: str
    number_columns: list[ScopeEntry]
    tally_columns: list[tuple[str, list[ScopeEntry]]]          # column → its marks then Total, as [section/column/part]
    choice_columns: list[tuple[str, list[str], ScopeEntry]]    # column, its choices, [section/column]

class AnalysisScope(NamedTuple):
    sheet_values: list[ScopeEntry]
    tables: list[ScopeTable]
    results: list[ScopeEntry]   # layers 1 .. layer_number - 1 only
```

## Rules

```python
def formula_problems(
    text: str,
    interpreters: list[SessionDataSectionInterpreterBase],
    analysis: DataSheetAnalysis,
    layer_number: int,
) -> list[FormulaProblem]
    """
    The syntax problem, if any. Otherwise every reference problem, in text order:
    an unknown, ambiguous, or out-of-scope name, the wrong type, columns from two tables
    in one aggregation, a COUNT choice that a column doesn't offer, or a placeholder.
    """

def calculation_problems(
    calculation: Calculation,
    interpreters: list[SessionDataSectionInterpreterBase],
    analysis: DataSheetAnalysis,
    layer_number: int,
    index: int | None,
) -> list[str]
    """
    Problems with one calculation as it would be applied at (layer_number, index).
    index None means it is being added. Each message starts with the calculation's name.
    """

def analysis_problems(
    interpreters: list[SessionDataSectionInterpreterBase],
    analysis: DataSheetAnalysis,
) -> list[str]
    """Every problem in the analysis, in layer then calculation order (FR-007, FR-016)."""

def calculations_using(analysis: DataSheetAnalysis, calculation_name: str) -> list[str]
    """Names of the calculations whose definition references this calculation (FR-017)."""

def describe_calculation(calculation: Calculation) -> str
    """
    Plain language for view mode (FR-002), e.g.
    'Sum over rows of Trials: count of "+" in Trial 1, Trial 2, Trial 3'
    'Average over rows of Trials: Attempts P count'
    'Correct trials as a percentage of Total trials'
    For a formula, the formula text.
    """
```

Problem message examples:

- `Calculation "Accuracy": "Total trials" is not a calculation in a lower layer.`
- `Calculation "Correct trials": the table "Trials" has no column "Trial 4".`
- `Calculation "Prompted": "Attempts" is a Text column, so it can't be summed.`
- `Calculation "Form total": give one of the sections named "Form" a title, so it can be told apart.`
- `Two calculations are named "Accuracy".`

## Renames

```python
class PartKind(Enum):
    SECTION = "section"
    ITEM = "item"            # a column or a field
    OPTION = "option"        # a choice or a tally mark
    CALCULATION = "calculation"

class PartRename(NamedTuple):
    kind: PartKind
    section: str
    item: str
    old: str
    new: str

def apply_renames(analysis: DataSheetAnalysis, renames: list[PartRename]) -> DataSheetAnalysis
```

`apply_renames` rewrites:

- every menu field that names the old part
- every matching reference span in a formula, re-escaped
- a `COUNT` choice string, re-quoted, for an `OPTION` rename of a Choice column it counts

All other formula text is left exactly as it was (FR-016a). A formula that doesn't parse
is left unchanged. It is already a problem, and is reported at Save.

## Serialization

```python
def analysis_to_json(analysis: DataSheetAnalysis) -> dict[str, Any]
def analysis_from_json(data: dict[str, Any] | None) -> DataSheetAnalysis
    """None or a missing key → empty analysis (FR-019)."""
```

The shape is in [../data-model.md](../data-model.md). `TemplateStore` writes the
`"analysis"` key only when `not analysis.is_empty`.

## Interpreter changes

```python
class SessionDataSectionInterpreterBase:
    @property
    def fallback_section_name(self) -> str:
        """The name used when the section is untitled. Default "Section"; each type overrides it."""
    @property
    def section_name(self) -> str:
        """The title, or fallback_section_name when untitled."""
    def analysis_parts(self) -> SectionParts:
        """What this section offers to Data Sheet Analysis. Default: nothing."""

class InterpreterConfig:
    def renames(self, config_values: dict[str, Any]) -> list[PartRename]:
        """
        Column, field, and option renames in the form's values. Default: [].
        Uses the Section Name the values would give, for PartRename.section.
        """
```

- `TableInterpreter`, `SimpleFormInterpreter`, and `RunningTallyInterpreter` override
  `fallback_section_name` (with their existing `_FALLBACK_SECTION_NAME`) and
  `analysis_parts()`, and replace their `self.title or _FALLBACK_SECTION_NAME`
  expressions with `section_name`.
- `TableInterpreterConfig`, `SimpleFormInterpreterConfig`, and
  `RunningTallyInterpreterConfig` override `renames()`.

## Template changes

```python
class StudentDataSheetTemplate:
    def __init__(self, id, name, configured_interpreters=None, description="",
                 analysis: DataSheetAnalysis | None = None) -> None
    @property
    def analysis(self) -> DataSheetAnalysis

class TemplateDraft:
    analysis: DataSheetAnalysis
    def rename_parts(self, renames: list[PartRename]) -> None
    # problems() appends analysis_problems(...)
    # has_changes_from() also compares analysis_to_json(...)
    # to_edit_dto() / to_create_dto() carry analysis
```

`TemplateCreateDto.analysis` and `TemplateEditDto.analysis` both default to
`DataSheetAnalysis.empty()`.
