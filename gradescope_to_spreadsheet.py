from fullGSapi.api import client
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# CS10 Su24 course id
COURSE_ID = 782967 
# CS10 Su24 lab2 assignment id
ASSIGNMENT_ID = "4486584" 
# This scope allows for write access.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1yrHEpO5dOMutG6mfDRwauxqT6F0nirqFAEdqMn8kRhU"

def allow_user_to_authenticate_google_account():
  """
  Allows the user authenticate their google account, allowing the script to modify spreadsheets in their name.
  Borrowed from here: https://developers.google.com/sheets/api/quickstart/python  
  """
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
    
    # Call the Sheets API
    sheet = service.spreadsheets()

    sheet = service.spreadsheets()
    sheets = sheet.get(spreadsheetId=SPREADSHEET_ID, fields='sheets/properties/title').execute()
    sub_sheet_titles = [sheet['properties']['title'] for sheet in sheets['sheets']]
    # Need to keep track of subsheet ids as well

    print(sub_sheet_titles)

    if ASSIGNMENT_ID not in sub_sheet_titles:
      #create new sub_sheet
      try:
         sheetservice = build('sheets', 'v4', credentials=creds)
        
         body = {
            "requests":{
                "addSheet":{
                    "properties":{
                        "title": ASSIGNMENT_ID
                    }
                }
            }
         }
         sheetservice.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
         #f = open("assignment_scores.csv", "r")
         #file_contents = f.read()
         assignment_scores = assignment_scores.replace("\\n", "\n")
         body = {
            'requests': [
                {
                'pasteData': {
                    "coordinate": {
                        "sheetId": "0",
                        "rowIndex": "0",  
                        "columnIndex": "0",
                    },
                    "data": str(assignment_scores),
                    "type": 'PASTE_NORMAL',
                    "delimiter": ',',
                }
            }
            ]
        }
         sheetservice.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
    


        
      except HttpError as err:
        print(err)     
    else:
      #update existing sheet
      pass

  except HttpError as err:
    print(err)

def main():
    gradescope_client =  client.GradescopeClient()
    gradescope_client.prompt_login()
    assignment_scores = str(gradescope_client.download_scores(COURSE_ID, ASSIGNMENT_ID))
    creds = allow_user_to_authenticate_google_account()
    writeToSheet(creds, assignment_scores)

main()
