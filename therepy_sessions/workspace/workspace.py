"""
The Workspace: the folder chosen at launch that holds the application's local files.

A Workspace holds the Student Store's file (`students.json`) and the Template Store's
file (`templates.json`). Its Workspace State says whether it is complete, partial, or
not set up yet. This module decides that state and runs the launch flow. It imports no
Tkinter and builds no store: the dialogs and file creators it needs are injected by
`program.py`.
"""

import os
from collections.abc import Callable
from enum import Enum
from typing import NamedTuple

STUDENTS_FILE_NAME: str = "students.json"
TEMPLATES_FILE_NAME: str = "templates.json"


class WorkspaceState(Enum):
    """Which Workspace files a folder holds."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    NOT_SET_UP = "not_set_up"


class WorkspaceFiles(NamedTuple):
    """The Workspace folder and the paths of its two files."""

    folder: str
    students_file: str
    templates_file: str


class WorkspaceInspection(NamedTuple):
    """The Workspace State of a folder, and the missing file when it is partial."""

    files: WorkspaceFiles
    state: WorkspaceState
    missing_file: str | None


class WorkspaceFolderError(Exception):
    """The Workspace folder, or a Workspace file name in it, cannot be used."""

    def __init__(self, path: str, reason: str) -> None:
        """
        Args:
            path: The path the problem is about
            reason: The full sentence shown to the SLP
        """
        super().__init__(reason)
        self.path: str = path
        self.reason: str = reason


class WorkspaceCreateError(Exception):
    """A file for a new Workspace could not be created."""

    def __init__(self, path: str, reason: str) -> None:
        """
        Args:
            path: The file that could not be created
            reason: The full sentence shown to the SLP
        """
        super().__init__(reason)
        self.path: str = path
        self.reason: str = reason


def workspace_files(folder: str) -> WorkspaceFiles:
    """Return the Workspace file paths in `folder`. Touches nothing on disk."""
    return WorkspaceFiles(
        folder,
        os.path.join(folder, STUDENTS_FILE_NAME),
        os.path.join(folder, TEMPLATES_FILE_NAME),
    )


def inspect_workspace(folder: str) -> WorkspaceInspection:
    """
    Decide the Workspace State of `folder`.

    Only the two Workspace file paths are checked. The folder is never listed, and no
    file is read.

    Raises:
        WorkspaceFolderError: The folder does not exist or is not a folder, or a
            Workspace file name in it is a folder or a broken link
    """
    if not os.path.exists(folder):
        raise WorkspaceFolderError(folder, f"This folder doesn't exist: {folder}")
    if not os.path.isdir(folder):
        raise WorkspaceFolderError(
            folder,
            f"This isn't a folder: {folder}. "
            f"Choose the folder that holds {STUDENTS_FILE_NAME} and {TEMPLATES_FILE_NAME}.",
        )

    files = workspace_files(folder)
    present: dict[str, bool] = {}
    for path in (files.students_file, files.templates_file):
        if os.path.isdir(path):
            raise WorkspaceFolderError(
                path,
                f"{path} is a folder, but it should be a file. "
                "Fix this in the Workspace folder, then launch again.",
            )
        # A broken link must not count as present, because the stores would then see no file
        if os.path.lexists(path) and not os.path.exists(path):
            raise WorkspaceFolderError(
                path,
                f"{path} is a link to a file that doesn't exist. "
                "Fix this in the Workspace folder, then launch again.",
            )
        present[path] = os.path.lexists(path)

    if all(present.values()):
        return WorkspaceInspection(files, WorkspaceState.COMPLETE, None)
    if not any(present.values()):
        return WorkspaceInspection(files, WorkspaceState.NOT_SET_UP, None)
    missing_file = next(path for path, exists in present.items() if not exists)
    return WorkspaceInspection(files, WorkspaceState.PARTIAL, missing_file)


def open_workspace(
    folder: str,
    ask_to_start_new_workspace: Callable[[str], bool],
    show_missing_workspace_file: Callable[[WorkspaceInspection], None],
    create_students_file: Callable[[], None],
    create_templates_file: Callable[[], None],
) -> WorkspaceFiles | None:
    """
    Open the Workspace in `folder`, asking the SLP when it is not complete.

    A partial Workspace is never opened: the SLP is told which file to restore.

    A new Workspace is all or nothing: if the templates file can't be created, the
    students file just created is removed again, so the folder is never left partial.

    Args:
        folder: The Workspace folder
        ask_to_start_new_workspace: Asks whether to start a new Workspace in the folder
        show_missing_workspace_file: Tells the SLP which file is missing, offering only Close
        create_students_file: Creates the empty student records file
        create_templates_file: Creates the empty templates file

    Returns:
        The Workspace files when the Workspace is (now) complete, or None when the SLP
        declined a new Workspace or the Workspace is partial. Nothing is created, changed, or deleted when None is
        returned.

    Raises:
        WorkspaceFolderError: From inspect_workspace
        WorkspaceCreateError: A new Workspace file could not be created; any file
            created for it was removed again
    """
    inspection = inspect_workspace(folder)
    files = inspection.files
    if inspection.state is WorkspaceState.COMPLETE:
        return files
    if inspection.state is WorkspaceState.PARTIAL:
        show_missing_workspace_file(inspection)
        return None

    if not ask_to_start_new_workspace(folder):
        return None
    try:
        create_students_file()
    except OSError as e:
        raise WorkspaceCreateError(files.students_file, _create_failed(files.students_file, e)) from e
    try:
        create_templates_file()
    except OSError as e:
        try:
            os.remove(files.students_file)
        except OSError as remove_error:
            raise WorkspaceCreateError(
                files.templates_file,
                f"Couldn't create {files.templates_file}: {_os_reason(e)}. "
                f"{files.students_file} was created but couldn't be removed again "
                f"({_os_reason(remove_error)}). Remove it, then launch again.",
            ) from e
        raise WorkspaceCreateError(files.templates_file, _create_failed(files.templates_file, e)) from e
    return files


def _create_failed(path: str, error: OSError) -> str:
    """Return the message for a new Workspace file that could not be created."""
    return f"Couldn't create {path}: {_os_reason(error)}. Nothing was set up in this folder."


def _os_reason(error: OSError) -> str:
    """Return the plain reason for an OS error, without its error number."""
    return error.strerror or str(error)
