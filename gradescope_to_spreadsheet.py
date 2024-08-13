from fullGSapi.api import client
import os.path
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# CS10 Su24 course id
COURSE_ID = 782967
# CS10 Su24 lab2 assignment id
ASSIGNMENT_ID = sys.argv[1]#"4486584"
# This scope allows for write access.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1yrHEpO5dOMutG6mfDRwauxqT6F0nirqFAEdqMn8kRhU"

"""
Allows the user authenticate their google account, allowing the script to modify spreadsheets in their name.
Borrowed from here: https://developers.google.com/sheets/api/quickstart/python
"""
def allow_user_to_authenticate_google_account():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
              "credentials.json", SCOPES
           )
            creds = flow.run_local_server(port=0)
            print("Authentication succesful")
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())
    return creds

def writeToSheet(creds, assignment_scores):
    try:

        service = build("sheets", "v4", credentials=creds)
        sheet_api_instance = service.spreadsheets()

        sheets = sheet_api_instance.get(spreadsheetId=SPREADSHEET_ID, fields='sheets/properties').execute()

        sub_sheet_titles_to_ids = {sheet['properties']['title'] : sheet['properties']['sheetId'] for sheet in sheets['sheets']}


        sheet_id = None

        if ASSIGNMENT_ID not in sub_sheet_titles_to_ids:
            create_sheet_request = {
                "requests":{
                    "addSheet":{
                        "properties":{
                            "title": ASSIGNMENT_ID
                        }
                    }
                }
            }
            response = sheet_api_instance.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=create_sheet_request).execute()
            sheet_id = response['replies'][0]['addSheet']['sheetId']
        else:
            sheet_id = sub_sheet_titles_to_ids[str(ASSIGNMENT_ID)]


        push_grade_data_request = {
                'requests': [
                    {
                    'pasteData': {
                        "coordinate": {
                            "sheetId": sheet_id,
                            "rowIndex": 0,
                            "columnIndex": 0,
                        },
                        "data": assignment_scores,
                        "type": 'PASTE_NORMAL',
                        "delimiter": ',',
                    }
                }
                ]
        }
        sheet_api_instance.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=push_grade_data_request).execute()
        print("Successfully updated spreadsheet with new score data")
    except HttpError as err:
        print(err)

def retrieve_grades_from_gradescope():
    gradescope_client = client.GradescopeClient()
    gradescope_client.prompt_login()
    assignment_scores = str(gradescope_client.download_scores(COURSE_ID, ASSIGNMENT_ID)).replace("\\n", "\n")
    return assignment_scores

def main():
    assignment_scores = retrieve_grades_from_gradescope()
    creds = allow_user_to_authenticate_google_account()
    writeToSheet(creds, assignment_scores)

main()
