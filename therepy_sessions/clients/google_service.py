import os
import pickle
from typing import Any

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Today's default path, outside the repo
DEFAULT_CLIENT_SECRET_FILE: str = '../../slpdataentry_3_credentials.json'
# Overrides the default when set. Read inside load_google_credentials(), never at import time.
CLIENT_SECRET_FILE_ENV: str = 'SLP_GOOGLE_CLIENT_SECRET_FILE'
SCOPES: list[str] = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
# How long the browser sign-in waits before giving up, so a closed or abandoned sign-in tab ends with an error
SIGN_IN_TIMEOUT_SECONDS: int = 300

# Kept from the earlier single-service version, so existing sign-ins keep working
_TOKEN_FILE: str = '.token_sheets_v4.pickle'


def load_google_credentials() -> Any:
    """
    Return Google credentials, signing in through the browser if needed.

    Uses the cached token when it is valid, refreshes it when it has expired, and falls
    back to the browser sign-in when there is no token or it can't be refreshed. The
    token is cached again after a refresh or sign-in.

    Returns:
        google.oauth2.credentials.Credentials

    Raises:
        google_auth_oauthlib.flow.WSGITimeoutError: If the browser sign-in is not
            finished within SIGN_IN_TIMEOUT_SECONDS
    """
    cred = None

    if os.path.exists(_TOKEN_FILE):
        with open(_TOKEN_FILE, 'rb') as token:
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
            client_secret_file = os.environ.get(CLIENT_SECRET_FILE_ENV, DEFAULT_CLIENT_SECRET_FILE)
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
            cred = flow.run_local_server(timeout_seconds=SIGN_IN_TIMEOUT_SECONDS)

        with open(_TOKEN_FILE, 'wb') as token:
            pickle.dump(cred, token)

    return cred


def create_sheets_service(credentials: Any) -> Any:
    """
    Build a Google Sheets v4 service.

    Args:
        credentials: google.oauth2.credentials.Credentials

    Returns:
        googleapiclient Resource for Sheets v4
    """
    return build('sheets', 'v4', credentials=credentials)


def create_drive_service(credentials: Any) -> Any:
    """
    Build a Google Drive v3 service.

    Args:
        credentials: google.oauth2.credentials.Credentials

    Returns:
        googleapiclient Resource for Drive v3
    """
    return build('drive', 'v3', credentials=credentials)
