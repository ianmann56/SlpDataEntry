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
from interpretation.template_types.running_tally_interpreter import RunningTallyInterpreter
from interpretation.student_data_sheet_interpreter import StudentDataSheetInterpreter
from interpretation.student_data_sheet import DataSheetScalarType

def main():
    # Create root Tkinter window
    root = tk.Tk()

    # Set theme to light or dark based on system.
    sv_ttk.set_theme(darkdetect.theme())
    
    # Create template store and show the template management window
    template_store = TemplateStore()
    app = DataSheetTemplateManagementWindow(template_store, root, close_callback=root.quit, interpreter_configs=STUB_INTERPRETER_CONFIGS)
    app.show()
    
    # Start the main event loop
    root.mainloop()

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