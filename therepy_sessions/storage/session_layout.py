"""
Pure rules for laying out a Session Tab and naming it.

This module has no Google imports and does no I/O, so all of it can be checked offline.
It decides:

- the Session Moment of a sheet (its Date and Time IN)
- tab and workbook names
- the Workbook Layout Order, and the rows a session tab holds
"""

import json
import re
import unicodedata
from collections.abc import Collection, Sequence
from datetime import date, datetime, time
from enum import Enum
from typing import NamedTuple

from interpretation.student_data_sheet import DataSheetScalarDto, DataSheetScalarType, StudentDataSheet
from storage.template_structure import SectionShape, TemplateShape, shape_of

# The longest tab name Google Sheets allows
TAB_NAME_MAX: int = 100
LAYOUT_VERSION: int = 1

# Room kept at the end of a base tab name for a " N" suffix (up to " 999")
_SUFFIX_ROOM: int = 4
# Used only if a Session Moment has nothing printable in it
_FALLBACK_TAB_NAME: str = "Session"

# Header fields, in the order they are written at the top of every tab (FR-021)
HEADER_LABELS: tuple[str, ...] = ("Student Key", "Date", "Time IN", "Time OUT", "Goal", "Measure")

# Section kinds whose keys are form fields, written in the vertical field list. Every
# other kind produces table blocks. A new interpreter type that emits form scalars
# instead of tables must be added here.
FORM_SECTION_KINDS: frozenset[str] = frozenset({"SimpleFormInterpreter"})


class CellKind(Enum):
    """How a value is written to its cell."""
    NUMBER = "number"
    TEXT = "text"


# How each interpreted type is saved (FR-024a). Only INT values become numbers.
CELL_KIND_BY_TYPE: dict[DataSheetScalarType, CellKind] = {
    scalar_type: CellKind.NUMBER if scalar_type is DataSheetScalarType.INT else CellKind.TEXT
    for scalar_type in DataSheetScalarType
}

_INTEGER_PATTERN = re.compile(r"[+-]?\d+")

# Formats US school sheets use, tried in order. Used only to order tabs (FR-018a).
_DATE_FORMATS: tuple[str, ...] = ("%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y")
_TIME_FORMATS: tuple[str, ...] = ("%I:%M %p", "%I:%M%p", "%I %p", "%H:%M")


class CellValue(NamedTuple):
    """
    One cell of a session tab.

    Properties:
      text: The text written, or None for an empty cell.
      number: The number written, set only when the value is saved as a number.
    """
    text: str | None
    number: int | None


EMPTY_CELL: CellValue = CellValue(None, None)


class SessionMoment(NamedTuple):
    """
    A sheet's session Date plus its Time IN, as read. Time IN may be blank.

    It names a Session Tab and identifies the session within its workbook.
    """
    date_text: str
    time_text: str

    @property
    def sort_key(self) -> tuple[bool, date, bool, time]:
        """
        (has_date, date, has_time, time), for ordering tabs newest first.

        A date or time that can't be read sorts before (older than) every one that can,
        so unreadable dates go after all dated tabs, and a blank or unreadable time goes
        after the timed tabs of the same date.
        """
        parsed_date = _parse_date(self.date_text)
        parsed_time = _parse_time(self.time_text)
        return (
            parsed_date is not None, parsed_date or date.min,
            parsed_time is not None, parsed_time or time.min,
        )

    def matches(self, other: "SessionMoment") -> bool:
        """
        Whether two moments are the same session (FR-016): both have a Time IN, and the
        dates and times are equal ignoring letter case and surrounding spaces. A blank
        Time IN never matches.
        """
        if not self.time_text.strip() or not other.time_text.strip():
            return False
        return (
            self.date_text.strip().casefold() == other.date_text.strip().casefold()
            and self.time_text.strip().casefold() == other.time_text.strip().casefold()
        )


def _parse_date(text: str) -> date | None:
    """Read a month/day/year date, or None."""
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), date_format).date()
        except ValueError:
            continue
    return None


def _parse_time(text: str) -> time | None:
    """Read a clock time such as "11:00 AM", "11 a.m.", or "13:30", or None."""
    cleaned = " ".join(text.upper().replace(".", "").split())
    for time_format in _TIME_FORMATS:
        try:
            return datetime.strptime(cleaned, time_format).time()
        except ValueError:
            continue
    return None


class LayoutSection(NamedTuple):
    """
    One section of a Workbook Layout Order.

    Properties:
      kind: The interpreter's section_kind.
      title: The section title.
      keys: The section's keys, in the order the workbook writes them.
    """
    kind: str
    title: str
    keys: tuple[str, ...]


class WorkbookLayout(NamedTuple):
    """
    The Workbook Layout Order: the order of sections, form fields, and columns taken
    from the template that started a workbook. Every tab in that workbook uses it.

    It holds template keys only: no values, no Student Key, no types or choices.
    """
    sections: tuple[LayoutSection, ...]

    def to_json(self) -> str:
        """The layout as compact JSON, for the workbook's hidden metadata."""
        return json.dumps(
            {
                "version": LAYOUT_VERSION,
                "sections": [
                    {"kind": section.kind, "title": section.title, "keys": list(section.keys)}
                    for section in self.sections
                ],
            },
            separators=(",", ":"),
        )

    @staticmethod
    def from_json(text: str) -> "WorkbookLayout":
        """
        Read a layout written by `to_json`.

        Raises:
            ValueError: If the text is not a layout this version can read
        """
        try:
            data = json.loads(text)
            if data["version"] != LAYOUT_VERSION:
                raise ValueError(f"unsupported layout version {data['version']!r}")
            sections = tuple(
                LayoutSection(str(section["kind"]), str(section["title"]), tuple(str(key) for key in section["keys"]))
                for section in data["sections"]
            )
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            raise ValueError(f"unreadable workbook layout: {e}") from e
        return WorkbookLayout(sections)

    @staticmethod
    def from_shape(shape: TemplateShape) -> "WorkbookLayout":
        """The layout of a template, in its own order. Used when a workbook is started."""
        return WorkbookLayout(tuple(LayoutSection(section.kind, section.title, section.keys) for section in shape.sections))


def moment_of(sheet: StudentDataSheet) -> SessionMoment:
    """Return the sheet's Session Moment, as read from the sheet."""
    return SessionMoment(sheet.date, sheet.time_in)


def _clean(text: str) -> str:
    """Drop control characters, and collapse whitespace runs (including newlines) to one space."""
    without_controls = "".join(" " if unicodedata.category(c) in ("Cc", "Cf") else c for c in text)
    return " ".join(without_controls.split())


def moment_from_rows(rows: list[list[str]]) -> SessionMoment | None:
    """
    The Session Moment held in a tab, from its A1:B6 values: the column B values next to
    the "Date" and "Time IN" labels. None if the tab has no Date label there, as with a
    tab the SLP added. Read from the values, not the tab name, so renamed tabs still count.
    """
    values: dict[str, str] = {}
    for row in rows[:len(HEADER_LABELS)]:
        if row:
            values.setdefault(str(row[0]).strip(), str(row[1]) if len(row) > 1 else "")
    if "Date" not in values:
        return None
    return SessionMoment(values["Date"], values.get("Time IN", ""))


def insert_index(new: SessionMoment, existing: Sequence[SessionMoment | None]) -> int:
    """
    Where a new tab goes among existing tabs (in tab order), so tabs read newest first
    (FR-018a): before the first tab whose moment is not newer than the new one. A tie
    puts the new tab first. A tab with no moment counts as the oldest.
    """
    new_key = new.sort_key
    for i, moment in enumerate(existing):
        if moment is None or moment.sort_key <= new_key:
            return i
    return len(existing)


def tab_base_name(moment: SessionMoment) -> str:
    """
    The tab name for a Session Moment, before any " N" suffix.

    "{date} {time}", or "{date}" when Time IN is blank. Control characters are removed,
    whitespace is collapsed, and the name is trimmed so a " N" suffix still fits within
    TAB_NAME_MAX (FR-015, FR-017a, FR-018).
    """
    date_text = _clean(moment.date_text)
    time_text = _clean(moment.time_text)
    name = f"{date_text} {time_text}" if time_text else date_text
    name = name[:TAB_NAME_MAX - _SUFFIX_ROOM].rstrip()
    return name or _FALLBACK_TAB_NAME


def unique_tab_name(base: str, taken: Collection[str]) -> str:
    """
    `base` if no tab uses it, otherwise `base` plus the lowest " N" (N ≥ 2) that is free.

    Names are compared ignoring letter case, as Google Sheets does (FR-016b, FR-017a).
    """
    used = {name.casefold() for name in taken}
    if base.casefold() not in used:
        return base
    n = 2
    while f"{base} {n}".casefold() in used:
        n += 1
    return f"{base} {n}"


def workbook_name(student_key: str, template_name: str) -> str:
    """The name of a new Student Session Workbook, e.g. "AG - Emotion Causes" (FR-011)."""
    return f"{student_key} - {template_name}"


def cell_for(value: DataSheetScalarDto | str | None) -> CellValue:
    """
    The cell for one interpreted value (FR-024, FR-024a, FR-024b).

    - None or blank: an empty cell, so the values after it keep their place.
    - A raw str (form text, header values): text, exactly as read.
    - A scalar whose type saves as a number (CELL_KIND_BY_TYPE), and whose text is an
      integer: that number.
    - Anything else: text, exactly as read. A number-typed value that isn't an integer is
      kept as text rather than dropped.

    The decision comes only from the interpreted type, never from the content. This is
    the single place a later per-field save setting on the template plugs in.
    """
    if value is None:
        return EMPTY_CELL
    if isinstance(value, str):
        return CellValue(value, None) if value.strip() else EMPTY_CELL

    text = "" if value.value is None else str(value.value)
    if not text.strip():
        return EMPTY_CELL
    kind = CELL_KIND_BY_TYPE.get(value.type, CellKind.TEXT) if isinstance(value.type, DataSheetScalarType) else CellKind.TEXT
    if kind is CellKind.NUMBER and _INTEGER_PATTERN.fullmatch(text.strip()):
        return CellValue(None, int(text.strip()))
    return CellValue(text, None)


def _structure_key(kind: str, title: str, keys: Collection[str]) -> tuple[str, str, tuple[str, ...]]:
    """What makes two sections the same, ignoring key order. The same form the fingerprint uses."""
    return (kind, title, tuple(sorted(keys)))


def _match_sections(
    layout: WorkbookLayout,
    sheet_sections: tuple[SectionShape, ...],
) -> list[tuple[LayoutSection, str | None]]:
    """
    Pair each layout section with the sheet section it stands for, in layout order.

    Each sheet section takes the next unused layout section with the same kind, title,
    and keys. A sheet section with no match (only if the stored layout disagrees with
    the template) is added at the end in its own order, so no value is ever dropped.
    """
    pairs: list[tuple[LayoutSection, str | None]] = [(section, None) for section in layout.sections]
    for sheet_section in sheet_sections:
        wanted = _structure_key(sheet_section.kind, sheet_section.title, sheet_section.keys)
        for i, (layout_section, matched_id) in enumerate(pairs):
            if matched_id is None and _structure_key(*layout_section) == wanted:
                pairs[i] = (layout_section, sheet_section.section_id)
                break
        else:
            pairs.append((LayoutSection(sheet_section.kind, sheet_section.title, sheet_section.keys), sheet_section.section_id))
    return pairs


def session_rows(sheet: StudentDataSheet, layout: WorkbookLayout) -> list[list[CellValue]]:
    """
    The rows of a session tab, top to bottom (research R9):

    1. the header fields, one per row: name in column A, value in column B
    2. one row per form field, across the form sections in layout order
    3. a blank row
    4. for each table section in layout order, and each table it produced on this sheet:
       a title row (when the section has a title), a column-header row in layout order,
       and one row per data row in sheet order, then a blank row

    Values are placed by key, so a template that lists the same keys in another order
    still writes them in the workbook's order (FR-025, FR-025a). A missing value is an
    empty cell. Only values are written: no choices, types, ids, or template details
    (FR-023).
    """
    rows: list[list[CellValue]] = []

    header_values = (sheet.student_key, sheet.date, sheet.time_in, sheet.time_out, sheet.student_goal, sheet.measure)
    for label, value in zip(HEADER_LABELS, header_values):
        rows.append([CellValue(label, None), cell_for(value)])

    pairs = _match_sections(layout, shape_of(sheet.template).sections)

    for section, _section_id in pairs:
        if section.kind in FORM_SECTION_KINDS:
            for key in section.keys:
                rows.append([CellValue(key, None), cell_for(sheet.scalars.get(key))])

    rows.append([])

    matched_ids = {section_id for _section, section_id in pairs if section_id is not None}
    blocks: list[tuple[str, tuple[str, ...], list[dict[str, DataSheetScalarDto]]]] = []
    for section, section_id in pairs:
        if section.kind in FORM_SECTION_KINDS or section_id is None:
            continue
        for table in sheet.tables:
            if table.get("section_id") == section_id:
                blocks.append((section.title, section.keys, table["data"]))
    # A table not tagged with a known section is still written, with its own columns
    for table in sheet.tables:
        if table.get("section_id") not in matched_ids:
            keys = tuple(table["data"][0].keys()) if table["data"] else ()
            blocks.append(("", keys, table["data"]))

    for title, keys, data in blocks:
        if title:
            rows.append([CellValue(title, None)])
        rows.append([CellValue(key, None) for key in keys])
        for data_row in data:
            rows.append([cell_for(data_row.get(key)) for key in keys])
        rows.append([])

    return rows
