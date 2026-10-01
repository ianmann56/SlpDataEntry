"""
The Student record and the rules for its Student Key.

A Student holds only a Student Key and the student's settings. It never holds the
student's name or any other direct identifier (Principle I, Student Data Privacy).
"""

from dataclasses import dataclass
from typing import NamedTuple

MAX_STUDENT_KEY_LENGTH: int = 5


@dataclass(frozen=True)
class Student:
    """
    One student, as configured for this application.

    Identified by its Student Key, which is unique among all students ignoring letter
    case. Later settings are added as new fields with defaults, so older records still
    load.
    """

    student_key: str
    current_template_id: str | None = None


class TemplateChoice(NamedTuple):
    """A read-only view of one Data Sheet Template that a student can use."""

    template_id: str
    name: str


class StudentKeyError(ValueError):
    """The Student Key is invalid. The message is shown to the SLP."""


class DuplicateStudentKeyError(StudentKeyError):
    """Another student already uses this Student Key."""

    def __init__(self, student_key: str) -> None:
        super().__init__(f'The Student Key "{student_key}" is already in use.')


class StudentNotFoundError(LookupError):
    """No student matches the given Student Key."""


class UnreadableStudentRecordsError(Exception):
    """The student records file exists but cannot be read."""

    def __init__(self, file_path: str, reason: str) -> None:
        super().__init__(f"Could not read student records from {file_path}: {reason}")
        self.file_path: str = file_path


def normalize_student_key(raw: str) -> str:
    """Return the Student Key with leading and trailing spaces trimmed."""
    return raw.strip()


def validate_student_key(raw: str) -> str:
    """
    Return the normalized Student Key, or raise if it is not valid.

    Raises:
        StudentKeyError: If the trimmed key is empty or longer than 5 characters
    """
    key = normalize_student_key(raw)
    if not key:
        raise StudentKeyError("A Student Key is required.")
    if len(key) > MAX_STUDENT_KEY_LENGTH:
        raise StudentKeyError(f"A Student Key can be at most {MAX_STUDENT_KEY_LENGTH} characters.")
    return key


def student_keys_match(a: str, b: str) -> bool:
    """Return whether two Student Keys are the same key, ignoring spaces and letter case."""
    return normalize_student_key(a).casefold() == normalize_student_key(b).casefold()
