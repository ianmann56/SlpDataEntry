"""
The Import Batch: the list of Selected Files in the Import window, and the rules for
importing them.

Each file is read into an Import, matched to a student by the Student Key on the sheet,
and interpreted with that student's Current Template. The template is chosen per sheet,
so one batch can mix students with different sheet layouts. A failure on one sheet never
stops the others, and becomes a Sheet Outcome whose message names the fix.

A file keeps its Import while the window is open. A later Import press reuses it unless
the file changed on disk, so each successful reading is paid for once.

This module has no Tkinter, and no I/O of its own beyond checking a file's modified
time. Reading sheets, finding students, and loading templates are all injected.
"""

import os
import traceback
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

from collection.collection_headers import StudentDataSheetImport
from interpretation.student_data_sheet import StudentDataSheet
from interpretation.template_manager.student_data_sheet_template import StudentDataSheetTemplate
from students.student import UnreadableStudentRecordsError
from students.student_store import StudentStore


class SheetStatus(Enum):
    NOT_IMPORTED = "not_imported"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class FailureReason(Enum):
    FILE_UNREADABLE = "file_unreadable"
    READING_FAILED = "reading_failed"
    NO_STUDENT_KEY = "no_student_key"
    UNKNOWN_STUDENT = "unknown_student"
    NO_CURRENT_TEMPLATE = "no_current_template"
    TEMPLATE_MISSING = "template_missing"
    TEMPLATE_MISMATCH = "template_mismatch"
    STUDENT_RECORDS_UNREADABLE = "student_records_unreadable"


class SheetOutcome(NamedTuple):
    """
    One file's latest result.

    Properties:
      status: Whether the file is not yet imported, succeeded, or failed.
      student_key: The Student Key read from the sheet, once known.
      template_name: The template used, on success or when the sheet did not match it.
      failure_reason: Why the file failed. Set only when status is FAILED.
      message: Text shown to the SLP. Names students only by Student Key.
    """
    status: SheetStatus
    student_key: str | None = None
    template_name: str | None = None
    failure_reason: FailureReason | None = None
    message: str = ""


class ProcessedSheet(NamedTuple):
    """The result of processing one file. `data_sheet` is set only on success."""
    outcome: SheetOutcome
    data_sheet: StudentDataSheet | None


class ListTotals(NamedTuple):
    """How many files in the whole list are in each status."""
    succeeded: int
    failed: int
    not_imported: int


SUPPORTED_IMAGE_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".tif", ".tiff")


@dataclass
class SelectedFile:
    """
    One image the SLP added to the list.

    Properties:
      path: The path as picked.
      identity: The resolved path, unique within the list.
      outcome: The latest result.
      sheet_import: The saved reading, reused while the file is unchanged.
      read_mtime_ns: The file's modified time just before `sheet_import` was read.
    """
    path: str
    identity: str
    outcome: SheetOutcome = SheetOutcome(SheetStatus.NOT_IMPORTED)
    sheet_import: StudentDataSheetImport | None = None
    read_mtime_ns: int | None = None


def _file_identity(path: str) -> str:
    """Return the key that tells whether two paths are the same file."""
    return os.path.normcase(os.path.realpath(path))


def _is_supported_image(path: str) -> bool:
    """Return whether the path has an image extension the reading service accepts."""
    return os.path.splitext(path)[1].casefold() in SUPPORTED_IMAGE_EXTENSIONS


def _os_stat_mtime_ns(path: str) -> int:
    """Return the file's modified time in nanoseconds."""
    return os.stat(path).st_mtime_ns


# Header labels the interpreter reads from every sheet
_HEADER_LABELS: tuple[str, ...] = ("Student Key", "Date", "Time IN", "Time OUT", "Goal", "Measure")

# One message per failure, each naming the fix. Students are named only by Student Key.
_FAILURE_MESSAGES: dict[FailureReason, str] = {
    FailureReason.FILE_UNREADABLE: "The file could not be opened. Check it still exists, or add it again.",
    FailureReason.READING_FAILED: "The sheet could not be read: {detail}. Check the connection, or retake the photo.",
    FailureReason.NO_STUDENT_KEY: "No Student Key was found on the sheet. Retake the photo so the key is clear.",
    FailureReason.UNKNOWN_STUDENT: 'No student has the Student Key "{student_key}". Add the student in Setup, or retake the photo.',
    FailureReason.NO_CURRENT_TEMPLATE: "Student {student_key} has no Current Template. Choose one in Setup → Students.",
    FailureReason.TEMPLATE_MISSING: "Student {student_key}'s Current Template no longer exists or could not be loaded. Choose another in Setup → Students.",
    FailureReason.TEMPLATE_MISMATCH: 'The sheet does not match template "{template_name}": {detail}. Fix the template, or retake the photo.',
    FailureReason.STUDENT_RECORDS_UNREADABLE: "The student records could not be read. Fix them in Setup → Students.",
}


class _SheetFailed(Exception):
    """One step of processing a sheet failed. Carries what the outcome should show."""

    def __init__(
        self,
        reason: FailureReason,
        student_key: str | None = None,
        template_name: str | None = None,
        detail: str = "",
    ) -> None:
        self.reason = reason
        self.student_key = student_key
        self.template_name = template_name
        self.message = _FAILURE_MESSAGES[reason].format(
            student_key=student_key, template_name=template_name, detail=detail.rstrip(". "),
        )
        super().__init__(self.message)


def _mismatch_detail(error: Exception) -> str:
    """Describe why a sheet did not match its template."""
    if isinstance(error, KeyError) and error.args and error.args[0] in _HEADER_LABELS:
        return f"the sheet has no '{error.args[0]}' field"
    return str(error)


class SheetImportBatch:
    """
    The list of Selected Files, and the rules for adding, removing, and importing them.

    The window calls `process_file` from one worker thread at a time, and changes the
    list only between runs, so no locks are needed.
    """

    def __init__(
        self,
        read_sheet: Callable[[str], StudentDataSheetImport],
        student_store: StudentStore,
        get_template: Callable[[str], StudentDataSheetTemplate | None],
        stat_mtime_ns: Callable[[str], int] = _os_stat_mtime_ns,
    ) -> None:
        """
        Initialize an empty batch.

        Args:
            read_sheet: Reads one image into an Import
            student_store: Finds the student named on a sheet
            get_template: Loads a template by id, or returns None if it no longer exists
            stat_mtime_ns: Returns a file's modified time in nanoseconds
        """
        self._read_sheet = read_sheet
        self._student_store = student_store
        self._get_template = get_template
        self._stat_mtime_ns = stat_mtime_ns
        self._files: list[SelectedFile] = []

    @property
    def files(self) -> list[SelectedFile]:
        """Every Selected File, in list order."""
        return list(self._files)

    def add_files(self, paths: Sequence[str]) -> list[SelectedFile]:
        """
        Append each supported image not already in the list, in order.

        Paths with other extensions, and paths already listed, are skipped. A missing
        file is not checked here; it fails when it is processed.

        Returns:
            The files actually added
        """
        listed = {selected.identity for selected in self._files}
        added = []
        for path in paths:
            if not _is_supported_image(path):
                continue
            identity = _file_identity(path)
            if identity in listed:
                continue
            selected = SelectedFile(path, identity)
            self._files.append(selected)
            listed.add(identity)
            added.append(selected)
        return added

    def remove_files(self, identities: Collection[str]) -> None:
        """Remove the files with these identities, and their saved Imports. Unknown ids are ignored."""
        removing = set(identities)
        self._files = [selected for selected in self._files if selected.identity not in removing]

    def files_to_process(self) -> list[SelectedFile]:
        """Every file that has not yet succeeded, in list order."""
        return [selected for selected in self._files if selected.outcome.status != SheetStatus.SUCCEEDED]

    def process_file(self, identity: str) -> ProcessedSheet:
        """
        Read, match, and interpret one file, and record its outcome.

        A saved Import is reused while the file's modified time is unchanged. Never
        raises for a problem with the sheet: every failure becomes a FAILED outcome
        whose message names the fix, and its cause is printed to the console.

        Raises:
            KeyError: If no file in the list has this identity
        """
        selected = self._find(identity)
        try:
            outcome, data_sheet = self._interpret(selected)
        except _SheetFailed as failure:
            if failure.__cause__ is not None:
                traceback.print_exception(failure.__cause__)
            outcome = SheetOutcome(
                SheetStatus.FAILED,
                student_key=failure.student_key,
                template_name=failure.template_name,
                failure_reason=failure.reason,
                message=failure.message,
            )
            data_sheet = None

        selected.outcome = outcome
        return ProcessedSheet(outcome, data_sheet)

    def _interpret(self, selected: SelectedFile) -> tuple[SheetOutcome, StudentDataSheet]:
        """Run every step for one file, raising _SheetFailed at the first that fails."""
        sheet_import = self._current_import(selected)

        student_key = sheet_import.form_data.get("Student Key", "").strip()
        if not student_key:
            raise _SheetFailed(FailureReason.NO_STUDENT_KEY)

        try:
            student = self._student_store.get_student(student_key)
        except UnreadableStudentRecordsError as e:
            raise _SheetFailed(FailureReason.STUDENT_RECORDS_UNREADABLE, student_key=student_key) from e
        if student is None:
            raise _SheetFailed(FailureReason.UNKNOWN_STUDENT, student_key=student_key)
        if student.current_template_id is None:
            raise _SheetFailed(FailureReason.NO_CURRENT_TEMPLATE, student_key=student_key)

        # Loaded fresh for every sheet, so each uses its own student's template as saved now
        try:
            template = self._get_template(student.current_template_id)
        except Exception as e:
            raise _SheetFailed(FailureReason.TEMPLATE_MISSING, student_key=student_key) from e
        if template is None:
            raise _SheetFailed(FailureReason.TEMPLATE_MISSING, student_key=student_key)

        try:
            data_sheet = template.to_data_sheet_interpreter().interpret_student_data_sheet(sheet_import)
        except Exception as e:
            raise _SheetFailed(
                FailureReason.TEMPLATE_MISMATCH,
                student_key=student_key,
                template_name=template.name,
                detail=_mismatch_detail(e),
            ) from e

        return SheetOutcome(SheetStatus.SUCCEEDED, student_key=student_key, template_name=template.name), data_sheet

    def _current_import(self, selected: SelectedFile) -> StudentDataSheetImport:
        """Return the file's saved Import if the file is unchanged, otherwise read it again."""
        try:
            mtime_ns = self._stat_mtime_ns(selected.path)
        except OSError as e:
            raise _SheetFailed(FailureReason.FILE_UNREADABLE) from e

        if selected.sheet_import is not None and selected.read_mtime_ns == mtime_ns:
            return selected.sheet_import

        selected.sheet_import = None
        selected.read_mtime_ns = None
        try:
            sheet_import = self._read_sheet(selected.path)
        except OSError as e:
            raise _SheetFailed(FailureReason.FILE_UNREADABLE) from e
        except Exception as e:
            raise _SheetFailed(FailureReason.READING_FAILED, detail=str(e)) from e

        selected.sheet_import = sheet_import
        selected.read_mtime_ns = mtime_ns
        return sheet_import

    def totals(self) -> ListTotals:
        """Count the files in the whole list by status."""
        statuses = [selected.outcome.status for selected in self._files]
        return ListTotals(
            succeeded=statuses.count(SheetStatus.SUCCEEDED),
            failed=statuses.count(SheetStatus.FAILED),
            not_imported=statuses.count(SheetStatus.NOT_IMPORTED),
        )

    def _find(self, identity: str) -> SelectedFile:
        """Return the Selected File with this identity, or raise KeyError."""
        for selected in self._files:
            if selected.identity == identity:
                return selected
        raise KeyError(identity)
