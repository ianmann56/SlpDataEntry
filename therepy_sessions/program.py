#!/bin/python3

import os
import sys
import traceback
import darkdetect
import tkinter as tk

import sv_ttk
from clients.google_service import create_google_service
from clients.aws_clients import construct_textract_client
from collection.images.aws_image_collection import image_to_text
from interpretation.template_manager.interpreter_configs import STUB_INTERPRETER_CONFIGS
from interpretation.template_store import TemplateStore
from interpretation.template_manager.template_management_window import DataSheetTemplateManagementWindow
from storage.file_creator import create_therapy_session_sheet
from interpretation.interpreter_types.running_tally_interpreter import RunningTallyInterpreter
from interpretation.student_data_sheet_interpreter import StudentDataSheetInterpreter
from interpretation.student_data_sheet import DataSheetScalarType

def main():
    # Parse command line arguments
    args = parse_command_line_args()
    storage_file_path = args[0]
    
    # Create root Tkinter window
    root = tk.Tk()

    # Set theme to light or dark based on system.
    sv_ttk.set_theme(darkdetect.theme())
    
    # Create template store and show the template management window
    template_store = TemplateStore(storage_file_path)
    app = DataSheetTemplateManagementWindow(template_store, root, close_callback=root.quit, interpreter_configs=STUB_INTERPRETER_CONFIGS)
    app.show()
    
    # Start the main event loop
    root.mainloop()

def validate_storage_file_path(file_path):
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

def parse_command_line_args():
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

def blah():
    # Construct the various clients
    google_service = create_google_service()
    textract_client = construct_textract_client()

    data_sheet_content = image_to_text(file_to_import, lambda: textract_client)
        
    print(f"Successfully extracted text from: {file_to_import}")
    print(f"Text:")
    print(data_sheet_content.form_data)
    print(f"Tables:")
    print(data_sheet_content.tables)

    # template = ColumnTableStudentDataSheetTemplate(["Strategy", "Cause of Emotion"])
    # template = ColumnTableStudentDataSheetTemplate(["Category", "Sort Tally", "Label"])

    # template = StudentDataSheetInterpreter([
    #     TableInterpreter(["Category", "Sort Tally", "Label"])
    # ])

    template = StudentDataSheetInterpreter([
        RunningTallyInterpreter(DataSheetScalarType.CHOICE)
    ])
    data_sheet = template.interpret_student_data_sheet(data_sheet_content)

    data_sheet.debug()
    
    # file_result = create_therapy_session_sheet(data, "Therapy Session Data", lambda: google_service)

    # print(f"Successfully created spreadsheet with ID: {file_result['spreadsheet_id']}")
    # print(f"Updated {file_result['updated_cells']} cells")
    # print(f"Spreadsheet URL: {file_result['url']}")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"An unahandled exception occurred: {e}")
        traceback.print_exc()