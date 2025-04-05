import os
import json
from typing import Any

import requests
from flask import Flask, render_template

from google.oauth2 import service_account
from google.auth.transport.requests import Request

JsonDict = dict[str, Any]

NYCOMP_PAT = os.environ.get("GH_PAT")
# Typo is intentional; when key is renamed, will change this too
SERVICE_ACCOUNT_JSON = json.loads(
    os.environ.get('GOOGLE_SEVICE_ACCOUNT')
)

credentials = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_JSON,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

# Refresh token before assigning it to access_token
credentials.refresh(Request())
access_token = credentials.token

spreadsheetId = "11qiZH2TYsOXbe1DwBFTaY-ndjG8TNr7UoX3UOsuR9yY"

app = Flask(__name__)

# ------------ THIS IS FOR GITHUB API. ------------


def GH_get_resources(url: str, params=None) -> JsonDict | list[JsonDict]:
    """Given a URL to be accessed,
    uses personal access token stored in GH_PAT to send a request and recieve a response.
    If request was successful, returns the JSON, else returns JSON with an error message.
    ## Parameters
    - `url: str`: The URL to be requested to.
    - `params: dict`: Any parameters to be sent together with the request.

    ## Returns:
    - A JSON dictionary, if the request was successful, or
    - a dictionary with an error message, stored in the key `error`."""

    # Gets the resources from the URL
    resp = requests.get(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {NYCOMP_PAT}",
    }, params=params)

    # Check if status code is OK
    if resp.ok:
        return resp.json()
    else:
        return {"error": "There was an error when fetching resources: " + str(resp.status_code) + " " + resp.reason}

# ------------ THIS IS FOR GOOGLE SHEETS API. (we can make a class for this.) ------------


def GS_make_request(url: str, method="GET", data=None) -> JsonDict | list[JsonDict]:
    """Given a URL to be accessed,
    uses GSheet's access token to send a request and recieve a response.
    If request was successful, returns the JSON, else returns JSON with an error message.

    ## Parameters
    - `url: str`: The URL to be requested to.
    - `method: str`: Determines the request method. "GET" for reading, and "POST" / "PUT" for updating.
    - `data: JsonDict`: Any data to be sent together with the request. (Note: should only be used with updates.)

    ## Returns:
    - A JSON dictionary, if the request was successful, or
    - a dictionary with an error message, stored in the key `error`."""

    if method == "GET":
        resp = requests.get(url, headers={
            "Authorization": f"Bearer {access_token}"
        }, data=data)
    elif method == "POST":
        resp = requests.post(url, headers={
            "Authorization": f"Bearer {access_token}"
        }, json=data)
    else:
        return {"error": "Invalid request method."}

    if resp.ok:
        return resp.json()
    else:
        return {"error": "There was an error when fetching resources: " + str(resp.status_code) + " " + resp.reason}


def read_gs_range(sheetName: str, range: str):
    """
    Takes in a sheetName and a range,
    and returns a ValueRange that is given from the API.
    """
    cells = GS_make_request(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/{sheetName}!{range}")

    return cells


def write_gs_range(ValueRange: JsonDict):
    """
    More information on ValueRanges: [Link](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values#resource-valuerange)

    Input a ValueRange, and this function returns the JSON of the response after updating the range.
    """
    update = GS_make_request(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values:batchUpdate",
        method="POST",
        data={
            "valueInputOption": "USER_ENTERED",
            "data": ValueRange,
        }
    )

    return update

# ---------- This is for GitHub convenience. (we can make a class too.) ----------


def get_finished(accepted: list[JsonDict]) -> JsonDict:
    '''Given the accepted JSON returned by GitHub's API,
    returns a dictionary containing a boolean value based on whether
    the student's Feedback pull request is closed.'''
    finished = {}
    for assignment in accepted:
        studentName = assignment['students'][0]['login']
        repository = assignment['repository']['full_name']
        closed_pull_requests = GH_get_resources(
            f'https://api.github.com/repos/{repository}/pulls',
            {"state": "closed"}
        )
        # Check if there's a closed PR named "Feedback"
        finished[studentName] = any(
            item["title"] == "Feedback"
            for item in closed_pull_requests
        )
    return finished


def get_assignments(classroomId: int, titles: list[str]):
    """
    ## Inputs:
    - `classroomId`: The classroom ID that you want to get assignments from.
    - `titles`: Titles of assignments you want to get.

    ## Returns:
    - JSON Dictionary with names of found assignments and its finished status for each accepted
    repository in it.
    """

    resultDict = {}
    assignments = GH_get_resources(
        f"https://api.github.com/classrooms/{classroomId}/assignments")

    for assignment in assignments:
        id, name = assignment["id"], assignment["title"]
        if name in titles:
            accepted = GH_get_resources(
                f"https://api.github.com/assignments/{id}/accepted_assignments")

            resultDict[name] = get_finished(accepted)

    return resultDict

# Error page


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Home page


@app.route('/')
def index():
    classrooms = GH_get_resources("https://api.github.com/classrooms")
    return render_template("home.html", classrooms=classrooms)

# Classrooms page


@app.route('/classrooms/<int:classroomId>')
def classroom(classroomId):
    assignments = GH_get_resources(
        f"https://api.github.com/classrooms/{classroomId}/assignments")
    return render_template("classroom.html", id=classroomId, assignments=assignments)


@app.route('/assignments/<int:assignmentId>')
def assignment(assignmentId):
    details = GH_get_resources(
        f"https://api.github.com/assignments/{assignmentId}")
    accepted = GH_get_resources(
        f"https://api.github.com/assignments/{assignmentId}/accepted_assignments")
    # GH_get_resources() will try and request a response to the URL specified.
    # if an error occurred, GH_get_resources() will return a JSON with a key-value pair:
    # {"error": <error message>}

    # We need to check whether the request was valid or invalid, by checking for this
    # "error" key. If it exists, an error occurred.

    if "error" in accepted:
        return render_template("assignment.html", accepted=accepted, assignment_id=assignmentId)
    finished = get_finished(accepted)

    return render_template(
        "assignment.html",
        assignment_details=details,
        accepted=accepted,
        finished=finished
    )

# Only used for testing!


# not ideal hardcoding, but suitable for the situation.
FOLLOWERS_CLASSROOM_ID = 255972


@app.route('/development')
def test_gsheets():
    sheetName = "Followers"
    # might be a little excessive, but will do the job.

    cells = read_gs_range(sheetName, "A1:I1000")
    values = cells.get("values", [])

    headers = values[0]

    finished = get_assignments(FOLLOWERS_CLASSROOM_ID, titles=headers)

    for row in range(1, len(values)):
        # HARDCODE: will fix if needed
        for column in range(2, len(headers)):
            # values[row][1]: the GitHub ID of the student
            # headers[column]: the "title" of the assignment, if there IS one.
            # Since finished only has repositories in which students has created,
            # if the student did NOT create a repo, report False as default.

            if headers[column] in finished and finished[headers[column]].get(values[row][1], False):
                values[row][column] = "Completed"

            else:
                values[row][column] = "Uncompleted"

    cells["values"] = values
    write_gs_range(cells)

    return render_template("development.html", values=cells.get("values", []))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
