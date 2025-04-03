import os
from typing import Any

import requests
from flask import Flask, render_template

JsonDict = dict[str, Any]

NYCOMP_PAT = os.environ.get("GH_PAT")
app = Flask(__name__)


def get_resources(url: str, params=None) -> JsonDict | list[JsonDict]:
    """Given a URL to be accessed,
    uses personal access token stored in GH_PAT to send a request and recieve a response.
    If request was successful, returns the JSON, else returns JSON with an error message."""

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


def get_finished(accepted: list[JsonDict]) -> JsonDict:
    '''Given the accepted JSON returned by GitHub's API,
    returns a dictionary containing a boolean value based on whether
    the student's Feedback pull request is closed.'''
    finished = {}
    for assignment in accepted:
        studentName = assignment['students'][0]['login']
        repository = assignment['repository']['full_name']
        closed_pull_requests = get_resources(
            f'https://api.github.com/repos/{repository}/pulls',
            {"state": "closed"}
        )
        # Check if there's a closed PR named "Feedback"
        finished[studentName] = any(
            item["title"] == "Feedback"
            for item in closed_pull_requests
        )
    return finished

# Error page


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Home page


@app.route('/')
def index():
    classrooms = get_resources("https://api.github.com/classrooms")
    return render_template("home.html", classrooms=classrooms)

# Classrooms page


@app.route('/classrooms/<int:classroomId>')
def classroom(classroomId):
    assignments = get_resources(
        f"https://api.github.com/classrooms/{classroomId}/assignments")
    return render_template("classroom.html", id=classroomId, assignments=assignments)


@app.route('/assignments/<int:assignmentId>')
def assignment(assignmentId):
    details = get_resources(
        f"https://api.github.com/assignments/{assignmentId}")
    accepted = get_resources(
        f"https://api.github.com/assignments/{assignmentId}/accepted_assignments")
    # get_resources() will try and request a response to the URL specified.
    # if an error occurred, get_resources() will return a JSON with a key-value pair:
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
