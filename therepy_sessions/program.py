#!/bin/python3

import os
import sys
import traceback
from clients.google_service import create_google_service
from clients.aws_clients import construct_textract_client
from collection.images.aws_image_collection import image_to_text
from storage.file_creator import create_therapy_session_sheet
from interpretation.template_types.simple_table_student_data_sheet_template import ColumnTableStudentDataSheetTemplate
from interpretation.student_data_sheet_interpreter import StudentDataSheetInterpreter

def main():
    file_to_import = sys.argv[1]

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

    template = StudentDataSheetInterpreter([
        ColumnTableStudentDataSheetTemplate(["Category", "Sort Tally", "Label"])
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