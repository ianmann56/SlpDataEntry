#!../.venv/bin/python3

import sys
import traceback
import darkdetect
import tkinter as tk

import sv_ttk
from app_shell.home_window import HomeWindow
from interpretation.importing.import_window import ImportWindow
from interpretation.template_manager.interpreter_configs import STUB_INTERPRETER_CONFIGS
from interpretation.template_manager.template_management_window import DataSheetTemplateManagementWindow
from interpretation.template_store import TemplateStore

def main() -> None:
    # Parse command line arguments
    args = parse_command_line_args()
    storage_file_path = args[0]

    # Create root Tkinter window
    root = tk.Tk()

    # Set theme to light or dark based on system.
    sv_ttk.set_theme(darkdetect.theme())

    # Create the template store shared by every visit to template management
    template_store = TemplateStore(storage_file_path)

    def open_import_path() -> None:
        path_window = _open_path_window(root)
        ImportWindow(
            path_window,
            on_back=lambda: _return_home(root, path_window),
            on_exit=root.destroy,
        )

    def open_management_path() -> None:
        path_window = _open_path_window(root)
        app = DataSheetTemplateManagementWindow(
            template_store,
            path_window,
            close_callback=root.destroy,
            interpreter_configs=STUB_INTERPRETER_CONFIGS,
            back_callback=lambda: _return_home(root, path_window),
        )
        app.show()

    # Show the home screen; each choice opens its path
    HomeWindow(root, on_import=open_import_path, on_manage=open_management_path, on_exit=root.destroy)

    # Start the main event loop
    root.mainloop()

def _open_path_window(root: tk.Tk) -> tk.Toplevel:
    """Hide the home screen and create a fresh window for a path."""
    root.withdraw()
    return tk.Toplevel(root)

def _return_home(root: tk.Tk, path_window: tk.Toplevel) -> None:
    """Close a path's window and show the home screen again."""
    path_window.destroy()
    root.deiconify()

def validate_storage_file_path(file_path: str) -> None:
    """
    Validate that the storage file path has a .json extension.
    
    Args:
        file_path (str): The file path to validate
        
    Exits:
        If the file path does not have a .json extension
    """
    if not file_path.lower().endswith('.json'):
        print(f"Error: Storage file must be a JSON file (got: {file_path})")
        print("Please provide a file path with .json extension")
        sys.exit(1)

def parse_command_line_args() -> list[str]:
    """
    Parse command line arguments and return configuration.
    
    Returns:
        list: The command line arguments (excluding script name)
        
    Exits:
        If required arguments are missing or invalid
    """
    # Check if file path argument is provided
    if len(sys.argv) < 2:
        print("Usage: python program.py <template_storage_file_path>")
        print("Example: python program.py templates.json")
        sys.exit(1)
    
    # Validate the storage file path
    validate_storage_file_path(sys.argv[1])
    
    return sys.argv[1:]

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"An unhandled exception occurred: {e}")
        traceback.print_exc()
