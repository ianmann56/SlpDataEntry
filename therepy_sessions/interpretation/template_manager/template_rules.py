"""
Rules shared by the Create window and the Template Details window.

Both windows call these functions instead of deciding rules in widget callbacks, so the
two can never drift apart (layers rule 5). Nothing here imports Tkinter or `students/`:
the windows receive student information only as a `TemplateUsage`, built in
`program.py`.
"""

from collections.abc import Callable
from enum import Enum
from typing import Any, NamedTuple

from interpretation.template_manager.storage.serialization import serialize
from interpretation.template_manager.student_data_sheet_template import StudentDataSheetTemplate
from interpretation.template_store import TemplateEditDto
from interpretation.templates.student_data_sheet_interpreter import SessionDataSectionInterpreterBase

# Shown beside every editable Template Description (Principle I)
DESCRIPTION_HINT: str = "Describe the sheet layout. Don't include student names."


class TitleConflictError(ValueError):
    """Another interpreter in the template already has this non-blank title. The message is shown to the SLP."""

    def __init__(self, title: str) -> None:
        super().__init__(f'An interpreter titled "{title.strip()}" has already been added.')
        self.title: str = title


def find_title_conflict(
    title: str,
    interpreters: list[SessionDataSectionInterpreterBase],
    ignore_index: int | None = None,
) -> bool:
    """
    Return whether another interpreter already uses this title.

    Titles are compared after trimming leading and trailing spaces, with exact letter
    case. A blank title never conflicts, so any number of interpreters may be untitled.

    Args:
        title: The title to check
        interpreters: The template's interpreters
        ignore_index: The position of the interpreter being replaced, which is not compared
    """
    trimmed = title.strip()
    if not trimmed:
        return False
    return any(
        index != ignore_index and (interpreter.title or "").strip() == trimmed
        for index, interpreter in enumerate(interpreters)
    )


def validate_template(name: str, interpreters: list[SessionDataSectionInterpreterBase]) -> list[str]:
    """
    Return every problem that stops a template from being saved, in order, or [] when it is valid.

    A name is required, at least one interpreter is required, and no two interpreters
    may share a non-blank title.
    """
    problems: list[str] = []
    if not name.strip():
        problems.append("Template name is required.")
    if not interpreters:
        problems.append("At least one interpreter must be added.")

    seen: set[str] = set()
    reported: set[str] = set()
    for interpreter in interpreters:
        title = (interpreter.title or "").strip()
        if not title:
            continue
        if title in seen and title not in reported:
            problems.append(f'The title "{title}" is used by more than one interpreter.')
            reported.add(title)
        seen.add(title)
    return problems


class TemplateUsage(NamedTuple):
    """
    Which students use each template, by Student Key.

    Only Student Keys are held, never any other student information (Principle I).
    """

    student_keys_by_template_id: dict[str, list[str]]

    def keys_for(self, template_id: str) -> list[str]:
        """Return the Student Keys of the students using the template, or [] when none do."""
        return list(self.student_keys_by_template_id.get(template_id, []))

    def count_for(self, template_id: str) -> int:
        """Return how many students use the template."""
        return len(self.student_keys_by_template_id.get(template_id, []))


def group_usage(pairs: list[tuple[str, str | None]]) -> TemplateUsage:
    """
    Build a TemplateUsage from (Student Key, Current Template ID) pairs.

    Students with no Current Template are skipped. Each template's keys are sorted
    ignoring letter case.
    """
    keys_by_template_id: dict[str, list[str]] = {}
    for student_key, template_id in pairs:
        if template_id is None:
            continue
        keys_by_template_id.setdefault(template_id, []).append(student_key)
    for keys in keys_by_template_id.values():
        keys.sort(key=str.casefold)
    return TemplateUsage(keys_by_template_id)


class TemplateDraft:
    """
    The working copy of a saved template that edit mode changes before Save.

    An interpreter the SLP does not change stays the same object it was loaded as, so it
    is saved exactly as it was (interpreters rule 7).
    """

    def __init__(
        self,
        template_id: str,
        name: str,
        description: str,
        interpreters: list[SessionDataSectionInterpreterBase],
    ) -> None:
        self.template_id: str = template_id
        self.name: str = name
        self.description: str = description
        self.interpreters: list[SessionDataSectionInterpreterBase] = list(interpreters)

    @classmethod
    def from_template(cls, template: StudentDataSheetTemplate) -> "TemplateDraft":
        """Start a draft from a saved template."""
        return cls(template.id, template.name, template.description, list(template.interpreters))

    def add(self, interpreter: SessionDataSectionInterpreterBase) -> None:
        """
        Append an interpreter.

        Raises:
            TitleConflictError: If another interpreter already has its non-blank title; the draft is unchanged
        """
        if find_title_conflict(interpreter.title or "", self.interpreters):
            raise TitleConflictError(interpreter.title or "")
        self.interpreters.append(interpreter)

    def replace(self, index: int, interpreter: SessionDataSectionInterpreterBase) -> None:
        """
        Swap in a rebuilt interpreter at the same position. The caller builds it with the
        old interpreter's id, so an interpreter's id never changes.

        Raises:
            ValueError: If the rebuilt interpreter has a different id
            TitleConflictError: If another interpreter already has its non-blank title; the draft is unchanged
        """
        if interpreter.id != self.interpreters[index].id:
            raise ValueError("A changed interpreter must keep its id.")
        if find_title_conflict(interpreter.title or "", self.interpreters, ignore_index=index):
            raise TitleConflictError(interpreter.title or "")
        self.interpreters[index] = interpreter

    def remove(self, index: int) -> None:
        """Remove the interpreter at this position."""
        del self.interpreters[index]

    def move(self, index: int, offset: int) -> int:
        """
        Move an interpreter up (offset -1) or down (offset +1). A move past either end does nothing.

        Returns:
            The interpreter's position after the move
        """
        target = index + offset
        if target < 0 or target >= len(self.interpreters):
            return index
        self.interpreters[index], self.interpreters[target] = self.interpreters[target], self.interpreters[index]
        return target

    def problems(self) -> list[str]:
        """Return every problem that stops the draft from being saved, or [] when it can be saved."""
        return validate_template(self.name, self.interpreters)

    def has_changes_from(self, template: StudentDataSheetTemplate) -> bool:
        """Return whether the draft differs from the saved template."""
        return (
            self.name.strip() != template.name.strip()
            or self.description != template.description
            or _serialized(self.interpreters) != _serialized(template.interpreters)
        )

    def to_edit_dto(self) -> TemplateEditDto:
        """Return the values to save."""
        return TemplateEditDto(self.name.strip(), list(self.interpreters), self.description)


def _serialized(interpreters: list[SessionDataSectionInterpreterBase]) -> list[dict[str, Any]]:
    """Return interpreters in their saved form, for comparing."""
    return [serialize(interpreter) for interpreter in interpreters]


def _join_keys(student_keys: list[str]) -> str:
    """Join Student Keys for a message."""
    return ", ".join(student_keys)


def save_confirmation(template_name: str, template_id: str, usage: TemplateUsage | None) -> str | None:
    """
    Return the text asking the SLP to confirm saving an edit, or None when no confirmation
    is needed because it is known that no student uses the template.
    """
    if usage is None:
        return f'It could not be checked which students use "{template_name}". Save the changes anyway?'
    student_keys = usage.keys_for(template_id)
    if not student_keys:
        return None
    return (
        f'Saving changes "{template_name}" for students {_join_keys(student_keys)}. '
        "Their next data sheets will be read with the changed template."
    )


def delete_confirmation(template_name: str, template_id: str, usage: TemplateUsage | None) -> str:
    """Return the text asking the SLP to confirm deleting a template."""
    if usage is None:
        return (
            f'It could not be checked which students use "{template_name}". '
            "Delete it anyway? No student records will be changed."
        )
    student_keys = usage.keys_for(template_id)
    if not student_keys:
        return f'Are you sure you want to delete the template "{template_name}"?'
    return (
        f'Students {_join_keys(student_keys)} use "{template_name}". '
        "Deleting it leaves them with no Current Template, and they will need a new one."
    )


class DeleteResult(Enum):
    """How a delete ended."""

    DELETED = "deleted"
    # The template was already gone. Students are cleared only if usage listed them.
    NOT_FOUND = "not_found"
    # Students were cleared, then deleting the template failed
    FAILED_AFTER_CLEARING = "failed_after_clearing"


class DeleteOutcome(NamedTuple):
    """The result of deleting a template, and the Student Keys whose Current Template was cleared."""

    result: DeleteResult
    cleared_student_keys: list[str]
    detail: str = ""


def delete_template_and_clear_students(
    template_id: str,
    usage: TemplateUsage | None,
    clear_template_from_students: Callable[[str], list[str]],
    delete_template: Callable[[str], bool],
) -> DeleteOutcome:
    """
    Delete a template, first clearing it from every student who uses it.

    Students are cleared only when usage is known and lists any. When usage is unknown,
    no student is changed.

    Raises:
        Exception: Whatever clearing raises, before the template is touched; or whatever
            deleting raises when no student was cleared
    """
    cleared: list[str] = []
    if usage is not None and usage.keys_for(template_id):
        cleared = clear_template_from_students(template_id)

    try:
        deleted = delete_template(template_id)
    except Exception as e:
        if not cleared:
            raise
        return DeleteOutcome(DeleteResult.FAILED_AFTER_CLEARING, cleared, str(e))

    if not deleted:
        return DeleteOutcome(DeleteResult.NOT_FOUND, cleared)
    return DeleteOutcome(DeleteResult.DELETED, cleared)
