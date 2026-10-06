#!../.venv/bin/python3

import sys
import threading
import traceback
import webbrowser
import darkdetect
import tkinter as tk
from tkinter import filedialog
from typing import Any

import sv_ttk
from app_shell.home_window import HomeWindow
from app_shell.setup_window import SetupWindow
from clients.aws_clients import construct_textract_client
from clients.google_service import create_drive_service, create_sheets_service, load_google_credentials
from collection.images.aws_image_collection import image_to_text
from interpretation.data_sheet_store import DataSheetStore
from interpretation.importing.import_window import ImportWindow
from interpretation.importing.sheet_import_batch import SheetImportBatch
from interpretation.template_manager.interpreter_configs import STUB_INTERPRETER_CONFIGS
from interpretation.template_manager.template_management_window import DataSheetTemplateManagementWindow
from interpretation.template_manager.template_rules import TemplateUsage, group_usage
from interpretation.template_store import TemplateStore
from storage.google_drive_data_sheet_store import GoogleDriveDataSheetStore
from students.json_student_store import JsonStudentStore
from students.student import TemplateChoice, UnreadableStudentRecordsError
from students.student_store import StudentStore
from tk_utils import error_handling
from students.students_window import StudentsWindow, ask_to_start_fresh
from workspace.workspace import WorkspaceCreateError, WorkspaceFolderError, open_workspace, workspace_files
from workspace.workspace_dialogs import (
    ask_to_start_new_workspace,
    show_missing_workspace_file,
    show_workspace_error,
)

def main() -> None:
    # Parse command line arguments
    folder_arg = parse_command_line_args()

    # Create root Tkinter window
    root = tk.Tk()

    # Make the root's window exist before theming. The theme applies its colors when Tk
    # sends the root a theme-changed event, which Tk drops for a window that doesn't exist
    # yet, and the root is withdrawn below without ever being shown first.
    root.winfo_id()

    # Set theme to light or dark based on system.
    sv_ttk.set_theme(darkdetect.theme())

    # Keep the root hidden until the Workspace is open, so only its dialogs show
    root.withdraw()

    folder = folder_arg
    if folder is None:
        folder = filedialog.askdirectory(parent=root, title="Choose Workspace Folder", mustexist=True)
    if not folder:
        root.destroy()
        return

    files = workspace_files(folder)

    # Create the template store shared by every visit to template management
    template_store = TemplateStore(files.templates_file)

    # Create the one student store; windows receive it by injection
    student_store: StudentStore = JsonStudentStore(files.students_file)

    try:
        opened = open_workspace(
            folder,
            ask_to_start_new_workspace=lambda path: ask_to_start_new_workspace(root, path),
            show_missing_workspace_file=lambda inspection: show_missing_workspace_file(root, inspection),
            create_students_file=student_store.create_empty_file,
            create_templates_file=template_store.create_empty_file,
        )
    except (WorkspaceFolderError, WorkspaceCreateError) as e:
        show_workspace_error(root, e)
        opened = None
    if opened is None:
        root.destroy()
        return

    root.deiconify()

    def list_template_choices() -> list[TemplateChoice]:
        return [TemplateChoice(template.id, template.name) for template in template_store.get_all_templates()]

    # Template management learns which students use each template only through these two callables
    def load_template_usage() -> TemplateUsage | None:
        try:
            students = student_store.list_students()
        except UnreadableStudentRecordsError:
            return None
        return group_usage([(student.student_key, student.current_template_id) for student in students])

    # Build the Textract client on the first sheet read, so launching and Setup need no AWS credentials
    textract_lock = threading.Lock()
    textract_client: Any = None  # boto3 Textract client

    def inject_textract_client() -> Any:
        nonlocal textract_client
        with textract_lock:
            if textract_client is None:
                textract_client = construct_textract_client()
            return textract_client

    # Build the Google services on the first Import press, so launching and Setup need no sign-in.
    # They are rebuilt once the credentials stop being valid, which signs in again if needed.
    google_lock = threading.Lock()
    google_credentials: Any = None  # google.oauth2.credentials.Credentials
    sheets_service: Any = None      # googleapiclient Resource, sheets v4
    drive_service: Any = None       # googleapiclient Resource, drive v3

    def ensure_google_services() -> None:
        nonlocal google_credentials, sheets_service, drive_service
        if google_credentials is None or not google_credentials.valid:
            google_credentials = load_google_credentials()
            sheets_service = create_sheets_service(google_credentials)
            drive_service = create_drive_service(google_credentials)

    def inject_sheets_service() -> Any:
        with google_lock:
            ensure_google_services()
            return sheets_service

    def inject_drive_service() -> Any:
        with google_lock:
            ensure_google_services()
            return drive_service

    def check_records_readable() -> None:
        student_store.list_students()
        template_store.check_readable()

    def open_import_path() -> None:
        path_window = _open_child_window(root, root)
        # One store per visit, shared by the batch and the window
        data_sheet_store: DataSheetStore = GoogleDriveDataSheetStore(inject_drive_service, inject_sheets_service)
        ImportWindow(
            path_window,
            SheetImportBatch(
                read_sheet=lambda path: image_to_text(path, inject_textract_client),
                student_store=student_store,
                get_template=template_store.get_template_by_id,
                data_sheet_store=data_sheet_store,
            ),
            data_sheet_store,
            check_records_readable,
            open_url=webbrowser.open,
            on_back=lambda: _return_to(root, path_window),
            on_exit=root.destroy,
        )

    def open_templates(setup: tk.Toplevel) -> None:
        path_window = _open_child_window(root, setup)
        app = DataSheetTemplateManagementWindow(
            template_store,
            path_window,
            load_template_usage=load_template_usage,
            clear_template_from_students=student_store.clear_current_template,
            close_callback=root.destroy,
            interpreter_configs=STUB_INTERPRETER_CONFIGS,
            back_callback=lambda: _return_to(setup, path_window),
        )
        app.show()

    def open_students(setup: tk.Toplevel) -> None:
        # Unreadable records are handled before any window opens, so declining leaves Setup showing
        try:
            student_store.list_students()
        except UnreadableStudentRecordsError as e:
            if not ask_to_start_fresh(setup, e):
                return
            try:
                student_store.recover_unreadable_records()
            except OSError as backup_error:
                error_handling.throw(backup_error, "Could not back up the student records")
                return

        path_window = _open_child_window(root, setup)
        StudentsWindow(
            path_window,
            student_store,
            list_template_choices,
            on_back=lambda: _return_to(setup, path_window),
            on_exit=root.destroy,
        )

    def open_management_path() -> None:
        setup = _open_child_window(root, root)
        SetupWindow(
            setup,
            on_templates=lambda: open_templates(setup),
            on_students=lambda: open_students(setup),
            on_back=lambda: _return_to(root, setup),
            on_exit=root.destroy,
        )

    # Show the home screen; each choice opens its path
    HomeWindow(root, on_import=open_import_path, on_manage=open_management_path, on_exit=root.destroy)

    # Start the main event loop
    root.mainloop()

def _open_child_window(root: tk.Tk, parent: tk.Misc) -> tk.Toplevel:
    """Hide the window a screen is opened from, and create a fresh window for it."""
    parent.withdraw()
    return tk.Toplevel(root)

def _return_to(parent: tk.Misc, child: tk.Toplevel) -> None:
    """Close a screen's window and show the window it was opened from again."""
    child.destroy()
    parent.deiconify()

def parse_command_line_args() -> str | None:
    """
    Parse the command line.

    Returns:
        The Workspace folder given, or None when it was left out, so a picker opens

    Exits:
        If more than one argument is given
    """
    if len(sys.argv) > 2:
        print("Usage: python program.py [<workspace_folder>]")
        print("The Workspace folder holds students.json and templates.json.")
        print("Leave the folder out to choose it from a folder picker.")
        print("Example: python program.py ~/SLP-Workspace")
        sys.exit(1)

    return sys.argv[1] if len(sys.argv) == 2 else None

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"An unhandled exception occurred: {e}")
        traceback.print_exc()
