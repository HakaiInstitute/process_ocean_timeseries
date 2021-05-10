
from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import requests

import pandas as pd

# Create functions to be used for handling Hakai Metadata
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
# Google Drive Interaction


def get_google_creds():
    # Get Google Authorizations
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials_quickstart.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds


def get_google_sheet(SAMPLE_SPREADSHEET_ID,SAMPLE_RANGE_NAME):
    # Get Google Authorizations
    creds = get_google_creds()

    service = build('sheets', 'v4', credentials=creds)
    
    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME).execute()
    values = result.get('values', [])
    return values


def get_google_drive_file(file_id,path):
    # Get Google Authorization
    creds = get_google_creds()
    
    drive = build('drive', 'v3', credentials=creds)
   
    request = drive.files().get_media(fileId=file_id)
    #fh = io.BytesIO()
    fh = open(path, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    
    while done is False:
        status, done = downloader.next_chunk()
        print("Download %d%%." % int(status.progress() * 100))         
    return None


def convert_google_sheet_to_dataframe(values):
    # Assume that the first line corresponds to the columns name
    df = pd.DataFrame(values[1:], columns=values[0][:])
    return df