import json
import os
import tempfile
import time
from dataclasses import replace

from students.student import (
    DuplicateStudentKeyError,
    Student,
    StudentNotFoundError,
    UnreadableStudentRecordsError,
    student_keys_match,
    validate_student_key,
)
from students.student_store import StudentStore

FORMAT_VERSION: int = 1


class JsonStudentStore(StudentStore):
    """
    StudentStore that keeps students in a local JSON file.

    The file is read on every call and written on every change. Writes go to a temporary
    file that then replaces the real one, so a failed save never leaves a half-written
    file.
    """

    def __init__(self, file_path: str) -> None:
        """
        Initialize the store. No file is read or created until it is used.

        Args:
            file_path: Path to the student records JSON file
        """
        self._file_path = file_path

    def list_students(self) -> list[Student]:
        return sorted(self._load(), key=lambda student: student.student_key.casefold())

    def get_student(self, student_key: str) -> Student | None:
        for student in self._load():
            if student_keys_match(student.student_key, student_key):
                return student
        return None

    def add_student(self, student: Student) -> Student:
        key = validate_student_key(student.student_key)
        students = self._load()
        if any(student_keys_match(existing.student_key, key) for existing in students):
            raise DuplicateStudentKeyError(key)
        saved = replace(student, student_key=key)
        students.append(saved)
        self._save(students)
        return saved

    def update_student(self, original_key: str, student: Student) -> Student:
        students = self._load()
        index = self._index_of(students, original_key)
        key = validate_student_key(student.student_key)
        for other_index, other in enumerate(students):
            if other_index != index and student_keys_match(other.student_key, key):
                raise DuplicateStudentKeyError(key)
        saved = replace(student, student_key=key)
        students[index] = saved
        self._save(students)
        return saved

    def delete_student(self, student_key: str) -> None:
        students = self._load()
        del students[self._index_of(students, student_key)]
        self._save(students)

    def clear_current_template(self, template_id: str) -> list[str]:
        students = self._load()
        cleared: list[str] = []
        for index, student in enumerate(students):
            if student.current_template_id == template_id:
                students[index] = replace(student, current_template_id=None)
                cleared.append(student.student_key)
        if cleared:
            self._save(students)
        return sorted(cleared, key=str.casefold)

    def recover_unreadable_records(self) -> str:
        if not os.path.exists(self._file_path):
            return ""
        try:
            self._load()
            return ""
        except UnreadableStudentRecordsError:
            pass

        stem, _ = os.path.splitext(self._file_path)
        base = f"{stem}.unreadable-{time.strftime('%Y%m%d-%H%M%S')}"
        backup_path = f"{base}.json"
        counter = 1
        while os.path.exists(backup_path):
            backup_path = f"{base}-{counter}.json"
            counter += 1
        os.replace(self._file_path, backup_path)
        return backup_path

    def _index_of(self, students: list[Student], student_key: str) -> int:
        """Return the index of the student matching `student_key`, or raise."""
        for index, student in enumerate(students):
            if student_keys_match(student.student_key, student_key):
                return index
        raise StudentNotFoundError(f'No student has the Student Key "{student_key}".')

    def _load(self) -> list[Student]:
        """Read every student from the file. A missing file means no students."""
        if not os.path.exists(self._file_path):
            return []
        try:
            with open(self._file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise UnreadableStudentRecordsError(self._file_path, f"not valid JSON ({e})") from e

        if not isinstance(data, dict) or not isinstance(data.get("students"), list):
            raise UnreadableStudentRecordsError(self._file_path, "not in the expected format")
        format_version = data.get("format_version", FORMAT_VERSION)
        if not isinstance(format_version, int) or isinstance(format_version, bool):
            raise UnreadableStudentRecordsError(self._file_path, "invalid format_version")
        if format_version > FORMAT_VERSION:
            raise UnreadableStudentRecordsError(self._file_path, "written by a newer version of the app")

        students = []
        for entry in data["students"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("student_key"), str):
                raise UnreadableStudentRecordsError(self._file_path, "a student entry has no Student Key")
            template_id = entry.get("current_template_id")
            if template_id is not None and not isinstance(template_id, str):
                raise UnreadableStudentRecordsError(self._file_path, "a Current Template is not a template id")
            # Fields missing from older records take their defaults; unknown keys are ignored.
            students.append(Student(student_key=entry["student_key"], current_template_id=template_id))
        return students

    def _save(self, students: list[Student]) -> None:
        """Write every student to the file, replacing it in one step."""
        data = {
            "format_version": FORMAT_VERSION,
            "students": [
                {"student_key": student.student_key, "current_template_id": student.current_template_id}
                for student in students
            ],
        }
        directory = os.path.dirname(os.path.abspath(self._file_path))
        os.makedirs(directory, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=directory, suffix=".tmp", delete=False
        ) as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            temp_path = file.name
        os.replace(temp_path, self._file_path)
