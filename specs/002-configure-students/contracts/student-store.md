# Contract: Student Store

**Feature**: [../spec.md](../spec.md) | **Date**: 2026-09-30

Data access for students goes only through this interface (research R2). Every signature
is fully annotated (Principle VI). The types it uses are defined in
[../data-model.md](../data-model.md).

## `students.student_store.StudentStore` (ABC)

```python
class StudentStore(ABC):
    @abstractmethod
    def list_students(self) -> list[Student]: ...
    @abstractmethod
    def get_student(self, student_key: str) -> Student | None: ...
    @abstractmethod
    def add_student(self, student: Student) -> Student: ...
    @abstractmethod
    def update_student(self, original_key: str, student: Student) -> Student: ...
    @abstractmethod
    def delete_student(self, student_key: str) -> None: ...
    @abstractmethod
    def recover_unreadable_records(self) -> str: ...
```

| Method | Behavior | Raises |
| --- | --- | --- |
| `list_students` | Returns every student, sorted by key ignoring case (research R10) | `UnreadableStudentRecordsError` |
| `get_student` | Returns the student whose key matches `student_keys_match`, or `None` | `UnreadableStudentRecordsError` |
| `add_student` | Validates the key, then saves. Returns the saved student, with its key normalized. | `StudentKeyError`, `DuplicateStudentKeyError`, `UnreadableStudentRecordsError` |
| `update_student` | Replaces the student matching `original_key`. A new key must not match any *other* student. Changing only letter case or spaces is allowed. | `StudentKeyError`, `DuplicateStudentKeyError`, `StudentNotFoundError`, `UnreadableStudentRecordsError` |
| `delete_student` | Removes the matching student | `StudentNotFoundError`, `UnreadableStudentRecordsError` |
| `recover_unreadable_records` | Moves the damaged file to a new backup name beside it and returns that path. Afterwards the store is empty. If the file is missing or readable, it does nothing and returns `""`. | `OSError` if the move fails |

- The store is the only place that knows records are stored in a file.
- It never calls Tkinter and never contacts an external service (FR-017).
- The key-change warning (FR-004a) is a UI decision. The store only enforces
  validity and uniqueness.

## `students.json_student_store.JsonStudentStore` (concrete)

```python
class JsonStudentStore(StudentStore):
    def __init__(self, file_path: str) -> None: ...
```

- Constructing it does no file I/O, so launch stays fast and can't fail on a damaged
  file. The file is read on each call (a caseload in the tens), and written on each
  change.
- Implements the file format and atomic write in [../data-model.md](../data-model.md),
  and the backup naming in research R5:
  `<stem>.unreadable-<YYYYmmdd-HHMMSS>[-N].json`.

## Who receives it

| Consumer | How | Notes |
| --- | --- | --- |
| `program.py` | Builds one `JsonStudentStore(student_storage_file_path)` | The only place it is constructed (layers.md rule 6) |
| `StudentsWindow` | Constructor parameter `student_store: StudentStore` | Typed as the interface |
| `StudentEditorWindow` | Constructor parameter from `StudentsWindow` | The same instance |
