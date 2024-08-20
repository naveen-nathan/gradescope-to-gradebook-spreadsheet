import json

from fullGSapi.api import client
import os.path
import sys
import re
import pandas as pd
import io

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# CS10 Su24 course id
COURSE_ID = "782967"
# User provided ASSIGNMENT_ID
ASSIGNMENT_ID = (len(sys.argv) > 1) and sys.argv[1]
# This scope allows for write access.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1kaC1SyYCbQKyZByxu_sX96D-bdGAlMrFWqLXKrivcxU" #"1yrHEpO5dOMutG6mfDRwauxqT6F0nirqFAEdqMn8kRhU"
NUMBER_OF_STUDENTS = 77

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


def writeToSheet(creds, assignment_scores, assignment_id = ASSIGNMENT_ID):
    try:

        sheet_api_instance = create_sheet_api_instance(creds)

        sub_sheet_titles_to_ids = get_sub_sheet_titles_to_ids(sheet_api_instance)

        sheet_id = None

        if assignment_id not in sub_sheet_titles_to_ids:
            create_sheet_request = {
                "requests": {
                    "addSheet": {
                        "properties": {
                            "title": assignment_id
                        }
                    }
                }
            }
            response = sheet_api_instance.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=create_sheet_request).execute()
            sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
        else:
            sheet_id = sub_sheet_titles_to_ids[assignment_id]

        update_sheet_with_csv(assignment_scores, sheet_api_instance, sheet_id)
        print("Successfully updated spreadsheet with new score data")
    except HttpError as err:
        print(err)


def create_sheet_api_instance(creds):
    service = build("sheets", "v4", credentials=creds)
    sheet_api_instance = service.spreadsheets()
    return sheet_api_instance


def get_sub_sheet_titles_to_ids(sheet_api_instance):
    sheets = sheet_api_instance.get(spreadsheetId=SPREADSHEET_ID, fields='sheets/properties').execute()
    sub_sheet_titles_to_ids = {sheet['properties']['title']: sheet['properties']['sheetId'] for sheet in
                               sheets['sheets']}
    return sub_sheet_titles_to_ids


def update_sheet_with_csv(assignment_scores, sheet_api_instance, sheet_id, rowIndex = 0, columnIndex=0):
    push_grade_data_request = {
        'requests': [
            {
                'pasteData': {
                    "coordinate": {
                        "sheetId": sheet_id,
                        "rowIndex": rowIndex,
                        "columnIndex": columnIndex,
                    },
                    "data": assignment_scores,
                    "type": 'PASTE_NORMAL',
                    "delimiter": ',',
                }
            }
        ]
    }
    sheet_api_instance.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=push_grade_data_request).execute()


def retrieve_grades_from_gradescope(gradescope_client, assignment_id = ASSIGNMENT_ID):
    #gradescope_client = initialize_gs_client()
    assignment_scores = str(gradescope_client.download_scores(COURSE_ID, assignment_id)).replace("\\n", "\n")
    return assignment_scores


def initialize_gs_client():
    gradescope_client = client.GradescopeClient()
    gradescope_client.prompt_login()
    return gradescope_client


def get_assignment_info(gs_instance, class_id: str) -> bytes:
    if not gs_instance.logged_in:
        print("You must be logged in to download grades!")
        return False
    gs_instance.last_res = res = gs_instance.session.get(f"https://www.gradescope.com/courses/{class_id}/assignments")
    if not res or not res.ok:
        print(f"Failed to get a response from gradescope! Got: {res}")
        return False
    return res.content


def make_score_sheet_for_one_assignment(creds, gradescope_client, assignment_id = ASSIGNMENT_ID):
    assignment_scores = retrieve_grades_from_gradescope(gradescope_client = gradescope_client, assignment_id = assignment_id)
    writeToSheet(creds, assignment_scores, assignment_id)

"""
This method returns a dictionary mapping assignment IDs to the names (titles) of the assignments
"""
def get_assignment_id_to_names(gradescope_client):
    # The response cannot be parsed as a json as is.
    course_info_response = str(get_assignment_info(gradescope_client, COURSE_ID)).replace("\\\\", "\\")
    pattern = '{"id":[0-9]+,"title":"[\w,:\+\s()]+?"}'
    info_for_all_assignments = re.findall(pattern, course_info_response)
    assignment_to_names = { str(json.loads(assignment)['id']) : json.loads(assignment)['title'] for assignment in info_for_all_assignments }
    return assignment_to_names

def main():
    creds = allow_user_to_authenticate_google_account()
    gradescope_client = initialize_gs_client()
    make_score_sheet_for_one_assignment(creds, gradescope_client = gradescope_client)

def populate_instructor_dashboard():
    creds = allow_user_to_authenticate_google_account()
    gradescope_client = initialize_gs_client()
    assignment_id_to_names = get_assignment_id_to_names(gradescope_client)
    labs = filter(lambda assignment: "lab" in assignment.lower(),
                  assignment_id_to_names.values())
    sorted_labs = sorted(labs, key=lambda lab: int(re.findall("\d+", lab)[0]))

    assignment_names_to_ids = {v: k for k, v in assignment_id_to_names.items()}
    projects = set(filter(lambda assignment: "project" in assignment.lower(),
                  assignment_id_to_names.values()))
    sorted_projects = sorted(projects, key=lambda project: assignment_names_to_ids[project])

    sheet_api_instance = create_sheet_api_instance(creds)
    sub_sheet_titles_to_ids = get_sub_sheet_titles_to_ids(sheet_api_instance)
    dashboard_sheet_id = sub_sheet_titles_to_ids['Instructor_Dashboard']
    dashboard_dict = {}

    for assignment_name in sorted_labs:
        assignment_id = assignment_names_to_ids[assignment_name]
        make_score_sheet_for_one_assignment(creds,gradescope_client = gradescope_client, assignment_id= assignment_id)
        spreadsheet_query = f"=DIVIDE(XLOOKUP(A:A, {assignment_id}!A:A, {assignment_id}!E:E), XLOOKUP(A:A, {assignment_id}!A:A, {assignment_id}!F:F))"
        dashboard_dict[assignment_name] = [spreadsheet_query] * NUMBER_OF_STUDENTS

    for assignment_name in sorted_projects:
        assignment_id = assignment_names_to_ids[assignment_name]
        make_score_sheet_for_one_assignment(creds,gradescope_client = gradescope_client, assignment_id= assignment_id)
        spreadsheet_query = f"=DIVIDE(XLOOKUP(A:A, {assignment_id}!A:A, {assignment_id}!E:E), XLOOKUP(A:A, {assignment_id}!A:A, {assignment_id}!F:F))"
        dashboard_dict[assignment_name] = [spreadsheet_query] * NUMBER_OF_STUDENTS

    dashboard_df = pd.DataFrame(dashboard_dict).set_index(sorted_labs[0])
    output = io.StringIO()
    dashboard_df.to_csv(output)
    update_sheet_with_csv(output.getvalue(), sheet_api_instance, dashboard_sheet_id, 0, 3)
    output.close()


populate_instructor_dashboard()
