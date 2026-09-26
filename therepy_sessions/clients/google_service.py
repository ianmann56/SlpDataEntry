import datetime
import pickle
import os
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

CLIENT_SECRET_FILE = '../../slpdataentry_3_credentials.json'
# CLIENT_SECRET_FILE = '../../slpdataentry-client-key.json'
API_SERVICE_NAME = 'sheets'
API_VERSION = 'v4'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def create_google_service():
    cred = None

    pickle_file = f'.token_{API_SERVICE_NAME}_{API_VERSION}.pickle'
    # print(pickle_file)

    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as token:
            cred = pickle.load(token)

    if not cred or not cred.valid:
        refreshed = False
        if cred and cred.expired and cred.refresh_token:
            try:
                cred.refresh(Request())
                refreshed = True
            except RefreshError:
                # Refresh token was expired or revoked, so fall back to logging in again.
                print('Cached Google token is expired or revoked. Opening browser to log in again.')

        if not refreshed:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            cred = flow.run_local_server()

        with open(pickle_file, 'wb') as token:
            pickle.dump(cred, token)

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
        return service
    except Exception as e:
        print('Unable to connect to Google Service.')
        raise e

def convert_to_RFC_datetime(year=1900, month=1, day=1, hour=0, minute=0):
    dt = datetime.datetime(year, month, day, hour, minute, 0).isoformat() + 'Z'
    return dt