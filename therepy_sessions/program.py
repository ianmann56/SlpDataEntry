#!/bin/python3

import os
import sys
from clients.google_service import create_google_service
from clients.aws_clients import construct_textract_client
from collection.images.aws_image_collection import image_to_text
from storage.file_creator import create_therapy_session_sheet
from interpretation.student_data_template import ColumnTableStudentDataSheetTemplate

FOLDER_PATH = r'<Folder Path>'

# Construct the various clients
google_service = create_google_service()
textract_client = construct_textract_client()

# Create the spreadsheet
try:
    file_to_import = sys.argv[1]

    data_sheet_content = image_to_text(file_to_import, lambda: textract_client)
        
    print(f"Successfully extracted text from: {file_to_import}")
    print(f"Text:")
    print(data_sheet_content.text)
    print(f"Tables:")
    print(data_sheet_content.tables)

    template = ColumnTableStudentDataSheetTemplate(["Word", "Times w/Prompting", "Times w/o Prompting"])
    data_sheet = template.interpret_student_data_sheet(data_sheet_content)

    print(data_sheet.student_key)
    print(data_sheet.date)
    print(data_sheet.student_goal)
    print(data_sheet.tables)
    
    # file_result = create_therapy_session_sheet(data, "Therapy Session Data", lambda: google_service)

    # print(f"Successfully created spreadsheet with ID: {file_result['spreadsheet_id']}")
    # print(f"Updated {file_result['updated_cells']} cells")
    # print(f"Spreadsheet URL: {file_result['url']}")
except Exception as e:
    print(f"Error creating spreadsheet: {e}")