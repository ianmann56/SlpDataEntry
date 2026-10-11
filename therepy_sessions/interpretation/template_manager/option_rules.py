"""
Rules for the names and options of columns and fields, with the messages the SLP sees.

The interpreters' `config_problems()` and the option editor both call these, so a rule is
decided in one place and the widgets only show its message (layers rule 5). Pure: no
Tkinter and no I/O.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from interpretation.value_types import ColumnType, tally_keys

if TYPE_CHECKING:
    # Imported for type checking only: the table interpreter imports this module
    from interpretation.interpreter_types.table_interpreter import ColumnDefinition


def _folded(text: str) -> str:
    """A name or option as compared: ignoring letter case and surrounding spaces."""
    return text.strip().casefold()


def _option_noun(column_type: ColumnType) -> str:
    return "tally mark" if column_type is ColumnType.TALLY else "choice"


def _subject(kind: str, item: str) -> str:
    """E.g. 'Column "Accuracy"', or just 'Running tally section' when there is no name."""
    return f'{kind[:1].upper()}{kind[1:]} "{item}"' if item.strip() else f"{kind[:1].upper()}{kind[1:]}"


def name_problems(kind: str, names: Sequence[str]) -> list[str]:
    """
    Blank names, and names used more than once ignoring letter case and surrounding spaces.

    Args:
        kind: What the names name, e.g. "column" or "field"
        names: The names, in order
    """
    problems: list[str] = []
    if any(not name.strip() for name in names):
        problems.append(f"{kind[:1].upper()}{kind[1:]} names must not be blank.")
    seen: set[str] = set()
    reported: set[str] = set()
    for name in names:
        folded = _folded(name)
        if not folded:
            continue
        if folded in seen and folded not in reported:
            problems.append(f'The {kind} name "{name.strip()}" is used more than once.')
            reported.add(folded)
        seen.add(folded)
    return problems


def option_problems(item: str, column_type: ColumnType, values: Sequence[str], kind: str = "column") -> list[str]:
    """
    The problems with a Choice or Tally's options: none at all, a blank one, one used more
    than once ignoring letter case and surrounding spaces, or (for a Tally) a mark that
    isn't exactly one character.

    Args:
        item: The column or field name, or the section title
        column_type: CHOICE or TALLY
        values: The choice values or tally marks, in order
        kind: What `item` is, e.g. "column", "field", or "running tally section"
    """
    noun = _option_noun(column_type)
    subject = _subject(kind, item)
    if not values:
        option_kind = "tally option" if column_type is ColumnType.TALLY else "choice"
        return [f"{subject} needs at least one {option_kind}."]

    problems: list[str] = []
    if any(not value.strip() for value in values):
        problems.append(f"{subject} has a blank {noun}.")
    seen: set[str] = set()
    reported: set[str] = set()
    for value in values:
        folded = _folded(value)
        if not folded:
            continue
        if folded in seen and folded not in reported:
            problems.append(f'{subject} has the {noun} "{value.strip()}" more than once.')
            reported.add(folded)
        seen.add(folded)
        if column_type is ColumnType.TALLY and len(value) != 1:
            problems.append(f'{subject} has the tally mark "{value}", but a tally mark must be exactly one character.')
    return problems


def check_new_option(column_type: ColumnType, value: str, existing: Sequence[str]) -> str | None:
    """
    The one problem with adding this option to a list, or None when it can be added.

    Args:
        column_type: CHOICE or TALLY
        value: The new choice value or tally mark
        existing: The options already in the list
    """
    noun = _option_noun(column_type)
    if not value.strip():
        return f"Enter a {noun} first."
    if column_type is ColumnType.TALLY and len(value.strip()) != 1:
        return f'"{value.strip()}" can\'t be a tally mark: a tally mark must be exactly one character.'
    if _folded(value) in {_folded(other) for other in existing}:
        return f'The {noun} "{value.strip()}" is already in the list.'
    return None


def tally_key_collisions(columns: Sequence[ColumnDefinition]) -> list[str]:
    """
    Tally columns whose summary keys (e.g. "Attempts Y") would equal another column's
    name, or another tally column's summary key, ignoring letter case and surrounding
    spaces. Two values can't share a key, so the template can't be saved until one is
    renamed.
    """
    problems: list[str] = []
    owner_by_key: dict[str, ColumnDefinition] = {_folded(column.column_name): column for column in columns}
    for column in columns:
        if column.column_type is not ColumnType.TALLY:
            continue
        for key in tally_keys(column.column_name, column.tally_options)[1:]:
            owner = owner_by_key.get(_folded(key))
            if owner is None:
                owner_by_key[_folded(key)] = column
            elif owner is column:
                continue
            elif _folded(owner.column_name) == _folded(key):
                problems.append(
                    f'The column "{owner.column_name}" has the same name as a summary column of tally "{column.column_name}". '
                    "Rename one of them."
                )
            else:
                problems.append(
                    f'The tally columns "{owner.column_name}" and "{column.column_name}" would both make a column named "{key}". '
                    "Rename one of them."
                )
    return problems
