from abc import ABC, abstractmethod

from students.student import Student


class StudentStore(ABC):
    """
    Saves and loads Students, identified by Student Key.

    Windows receive a StudentStore by injection and never know how students are stored.
    """

    @abstractmethod
    def list_students(self) -> list[Student]:
        """
        Return every student, sorted by Student Key ignoring letter case.

        Raises:
            UnreadableStudentRecordsError: If the saved records cannot be read
        """

    @abstractmethod
    def get_student(self, student_key: str) -> Student | None:
        """
        Return the student whose key matches `student_key`, or None.

        Raises:
            UnreadableStudentRecordsError: If the saved records cannot be read
        """

    @abstractmethod
    def add_student(self, student: Student) -> Student:
        """
        Validate and save a new student, and return it with its key normalized.

        Raises:
            StudentKeyError: If the key is invalid
            DuplicateStudentKeyError: If another student already uses the key
            UnreadableStudentRecordsError: If the saved records cannot be read
        """

    @abstractmethod
    def update_student(self, original_key: str, student: Student) -> Student:
        """
        Replace the student matching `original_key`, and return the saved student.

        The new key may differ only in letter case or spaces, or be a key no other
        student uses.

        Raises:
            StudentKeyError: If the new key is invalid
            DuplicateStudentKeyError: If another student already uses the new key
            StudentNotFoundError: If no student matches `original_key`
            UnreadableStudentRecordsError: If the saved records cannot be read
        """

    @abstractmethod
    def delete_student(self, student_key: str) -> None:
        """
        Remove the student matching `student_key`.

        Raises:
            StudentNotFoundError: If no student matches `student_key`
            UnreadableStudentRecordsError: If the saved records cannot be read
        """

    @abstractmethod
    def recover_unreadable_records(self) -> str:
        """
        Move unreadable saved records to a new backup, leaving the store empty.

        Returns:
            The backup's path, or "" if the records were missing or readable

        Raises:
            OSError: If the backup cannot be made
        """
