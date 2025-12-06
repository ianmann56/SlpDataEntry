#!/bin/python3

import os
import sys
from google_service import Create_Service
from file_creator import create_therapy_session_sheet
from aws_sheet_importer import image_to_text
# from sheet_importer import image_to_text_simple, image_to_text_with_opencv, image_to_text, image_to_text_with_preprocessing, table_to_text, table_to_text_complex

FOLDER_PATH = r'<Folder Path>'
CLIENT_SECRET_FILE = '../../slpdataentry_3_credentials.json'
# CLIENT_SECRET_FILE = '../../slpdataentry-client-key.json'
API_SERVICE_NAME = 'sheets'
API_VERSION = 'v4'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Build the Sheets API service object
service = Create_Service(CLIENT_SECRET_FILE, API_SERVICE_NAME, API_VERSION, SCOPES)

# Create the spreadsheet
try:
    file_to_import = sys.argv[1]
    # file_to_import = 'sample_data/random_table.png'
    # file_to_import = 'sample_data/veriety_w_prompting.png'
    # file_to_import = 'sample_data/table_only.png'
    # file_to_import = 'sample_data/no_table_left_align.png'
    # data = image_to_text_simple(file_to_import)
    # data = image_to_text_with_preprocessing(file_to_import)
    # data = image_to_text_with_opencv(file_to_import)
    # data = table_to_text_complex(file_to_import)
    # data = table_to_text(file_to_import) # Best success so far
    data = image_to_text(file_to_import)
        
    print(f"Successfully extracted text from: {file_to_import}")
    print(f"Text length: {len(data)} characters")
    print(f"Text:")
    print(data)
    
    # file_result = create_therapy_session_sheet(service, "Therapy Session Data")

    # print(f"Successfully created spreadsheet with ID: {file_result['spreadsheet_id']}")
    # print(f"Updated {file_result['updated_cells']} cells")
    # print(f"Spreadsheet URL: {file_result['url']}")
except Exception as e:
    print(f"Error creating spreadsheet: {e}")