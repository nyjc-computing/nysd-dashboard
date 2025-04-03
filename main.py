import os

import requests
from flask import Flask, render_template

NYCOMP_PAT = os.environ.get("GH_PAT")
app = Flask(__name__)


def get_resources(url: str, params=None) -> dict | list[dict]:
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


def get_finished(accepted: list[dict]) -> dict:
    '''Given the accepted JSON returned by GitHub's API,
    returns a dictionary containing a boolean value based on whether
    the student's Feedback pull request is closed.'''
    finished = {}
    for assignment in accepted:
        studentName = assignment['students'][0]['login']
        repository = assignment['repository']['full_name']

        # gets pull requests
        closed_pull_requests = get_resources(
            f'https://api.github.com/repos/{repository}/pulls',
            {"state": "closed"}
        )

        """This function filters all pull requests for ones with title "Feedback", and
    checks for its existence in the CLOSED pull requests."""
        if next(filter(lambda item: item["title"] == "Feedback", closed_pull_requests), None):
            finished[studentName] = True
        else:
            finished[studentName] = False

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
