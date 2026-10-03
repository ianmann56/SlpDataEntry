"""
The Template Structure: the shape of a template that decides which Student Session
Workbook its sessions are saved to.

A template's structure is its sections and, within each, its set of keys, compared
without regard to order. The template's name, description, and ids, and its value types
and choice options, are not part of it.

This module is pure: no I/O. It reads only the interpreters' public `id`, `title`,
`section_kind`, and `section_keys()`, and never checks interpreter types.
"""

import hashlib
import json
from typing import NamedTuple

from interpretation.template_manager.student_data_sheet_template import StudentDataSheetTemplate

# Bump when the structure definition changes, so old workbooks are never matched by mistake
_FINGERPRINT_VERSION: str = "s1"
_FINGERPRINT_HEX_LENGTH: int = 32


class SectionShape(NamedTuple):
    """
    One section of a template, as Storage sees it.

    Properties:
      section_id: The interpreter id. Matches tables on a sheet; never part of the structure.
      kind: The interpreter's section_kind.
      title: The section title.
      keys: The section's keys, in template order.
    """
    section_id: str
    kind: str
    title: str
    keys: tuple[str, ...]


class TemplateShape(NamedTuple):
    """
    The sections of a template, in template order, with the template's name.

    Properties:
      template_name: The template name. A new workbook is named from it.
      sections: Every section, in template order.
    """
    template_name: str
    sections: tuple[SectionShape, ...]

    def structure_identity(self) -> list[tuple[str, str, list[str]]]:
        """
        The Template Structure: each section's (kind, title, sorted keys), sorted.

        Sorting at both levels makes it independent of order. Sections are kept as a
        multiset, so two identical sections both count.
        """
        return sorted((section.kind, section.title, sorted(section.keys)) for section in self.sections)

    def structure_fingerprint(self) -> str:
        """
        A short, stable fingerprint of the Template Structure: "s1-" plus 32 hex characters.
        """
        canonical = json.dumps(self.structure_identity(), separators=(",", ":"), sort_keys=True)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"{_FINGERPRINT_VERSION}-{digest[:_FINGERPRINT_HEX_LENGTH]}"


def shape_of(template: StudentDataSheetTemplate) -> TemplateShape:
    """Return the shape of a template, with its sections in template order."""
    return TemplateShape(
        template_name=template.name,
        sections=tuple(
            SectionShape(
                section_id=interpreter.id,
                kind=interpreter.section_kind,
                title=interpreter.title,
                keys=tuple(interpreter.section_keys()),
            )
            for interpreter in template.interpreters
        ),
    )
