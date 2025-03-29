from flask import Flask, render_template
import os
import requests

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
    print(resp.json())
    return {"Error": "There was an error when fetching classrooms: " + str(resp.status_code) + " " + resp.reason}


# Home page
@app.route('/')
def index():
  CLASSROOMS = get_resources("https://api.github.com/classrooms")

  print(CLASSROOMS)
  return render_template("home.html", crs=CLASSROOMS)

# Classrooms page
@app.route('/classrooms/<classroomId>')
def classroom(classroomId):
  assignments = get_resources(f"https://api.github.com/classrooms/{classroomId}/assignments")
  print(assignments)
  return render_template("classroom.html", id=classroomId, assignments=assignments)

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000, debug=True)
