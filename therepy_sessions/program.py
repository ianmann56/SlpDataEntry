#!/bin/python3

import os
from google_service import Create_Service
from file_creator import create_therapy_session_sheet

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
    file_result = create_therapy_session_sheet(service, "Therapy Session Data")

    print(f"Successfully created spreadsheet with ID: {file_result['spreadsheet_id']}")
    print(f"Updated {file_result['updated_cells']} cells")
    print(f"Spreadsheet URL: {file_result['url']}")
except Exception as e:
    print(f"Error creating spreadsheet: {e}")