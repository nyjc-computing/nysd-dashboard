from flask import Flask, render_template
import os
import requests
import json

app = Flask(__name__)
NYCOMP_PAT = os.environ.get("GH_PAT")

def get_resources(URL, params=None):
  """Given a URL to be accessed,
  uses personal access token stored in GH_PAT to send a request and recieve a response.
  If request was successful, returns the JSON, else returns JSON with an error message."""

  # Gets the resources from the URL
  resp = requests.get(URL, headers={
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {NYCOMP_PAT}",
  }, params=params)

  # Check if status code is OK
  if resp.ok:
    return resp.json()

  else:
    return {"error": "There was an error when fetching resources: " + str(resp.status_code) + " " + resp.reason}


# Home page
@app.route('/')
def index():
  CLASSROOMS = get_resources("https://api.github.com/classrooms")
  return render_template("home.html", crs=CLASSROOMS)

# Classrooms page
@app.route('/classrooms/<int:classroomId>')
def classroom(classroomId):
  # assignments = get_resources(f"https://api.github.com/classrooms/{classroomId}/assignments")
  
  # While debugging assignment listing issue, use assignments.json as a placeholder.
  with open('assignments.json', 'r') as f:
    assignments = json.load(f)
  
  return render_template("classroom.html", id=classroomId, assignments=assignments)

@app.route('/assignments/<int:assignmentId>')
def assignment(assignmentId):
  # accepted = get_resources(f"https://api.github.com/assignments/{assignmentId}")
  
  # While debugging assignment listing issue, use accepted.json as a placeholder.
  with open('accepted.json', 'r') as f:
    accepted = json.load(f)
  
  if "error" in accepted:
    return render_template("assignment.html", accepted=accepted, assignment_id=assignmentId)
  
  print(accepted)
  finished = {}
  for assignment in accepted:
    studentName = assignment['students'][0]['login']
    repository = assignment['repository']['full_name']
    
    # gets pull requests
    pull_requests = get_resources(f'https://api.github.com/repos/{repository}/pulls', {
      "state": "closed"
    })
    
    """This function filters all pull requests for ones with title "Feedback", and
    checks for its existence in the CLOSED pull requests."""
    if next(filter(lambda item: item["title"] == "Feedback", pull_requests), None):
      finished[studentName] = True
    else:
      finished[studentName] = False

  return render_template(
    "assignment.html", 
    assignment_id=assignmentId, 
    accepted=accepted,
    finished=finished)
  

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000, debug=True)
