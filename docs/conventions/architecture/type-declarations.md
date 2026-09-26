# Type Declarations on Public Interfaces

Public members and constructs MUST have type declarations. They are the contracts
between layers ([layers.md](layers.md)), and types keep those contracts checkable instead
of leaving them to docstrings.

## What counts as public

A name is public unless it starts with `_`. That covers:

- Module-level functions, classes, and constants (e.g. `image_to_text`, `TemplateStore`,
  `SCOPES`).
- Methods, properties, and class attributes of public classes, including `__init__`.
- DTOs and records passed between layers (`StudentDataSheetImport`, `DataSheetScalarDto`,
  `DataSheetInterpretationDto`, template DTOs).

Private (`_`-prefixed) members and local variables are exempt. Annotate them anyway when
the type isn't obvious.

## Rules

1. **Annotate every parameter and the return.** Public functions and methods annotate
   every parameter (except `self` and `cls`) and the return type, including `-> None`.
2. **Annotate properties and attributes.** Properties annotate their return type. Public
   class and instance attributes are annotated where they're declared.
3. **Annotate constants whose type isn't obvious.** Public module constants get an
   annotation unless the type is plain from a literal. `SCOPES: list[str] = [...]` is
   preferred.
4. **Use typed records for DTOs.** Use `typing.NamedTuple` or `@dataclass` instead of an
   untyped `collections.namedtuple` or a bare `dict`. A `dict` with a fixed shape that
   crosses a boundary is declared as a `TypedDict`.
5. **Use modern syntax.** The project runs on Python 3.12, so write built-in generics
   (`list[str]`, `dict[str, X]`) and `X | None` rather than `typing.List` or `Optional`.
   Use `collections.abc.Callable` for providers, e.g.
   `inject_textract_client: Callable[[], TextractClient]`.
6. **Name the real type.** Use `Any` only for untyped third-party objects, and add a
   comment giving the concrete type. Boto3 and Google clients may be typed with `Any`, or
   with stub packages if they're added as dependencies.
7. **Abstract methods declare the full signature.** Every subclass's signature
   (`SessionDataSectionInterpreterBase`, `InterpreterConfig`, `InterpreterSerializer`)
   must be compatible with it.
8. **Types don't replace docstrings.** Docstrings still explain meaning, units, and
   domain rules. They don't need to repeat the types.

## Example

```python
from collections.abc import Callable
from typing import Any, NamedTuple

class DataSheetScalarDto(NamedTuple):
    key: str
    value: str
    type: DataSheetScalarType
    choice_options: list[str] | None = None

def image_to_text(
    image_path: str,
    inject_textract_client: Callable[[], Any],  # boto3 Textract client
) -> StudentDataSheetImport:
    ...
```

## Existing code

Most current modules predate this rule. Any public member that a change adds or
modifies MUST be annotated in that same change. Untouched code is annotated
opportunistically.
