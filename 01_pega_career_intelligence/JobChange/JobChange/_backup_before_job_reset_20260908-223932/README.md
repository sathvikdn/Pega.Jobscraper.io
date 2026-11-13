# Sathvik's Career Desk

Private Pega career research portal with the original **Dossiers**, **Career Hub** and category/depth → Python search flow.

The saved GCC review covers 191 catalogue entries and 698 associated records. The complete catalogue keeps 522 company entries and 574 distinct LinkedIn profile identities. Review status is shown per record; these numbers are not current team headcounts.

## Run locally

Python 3.10+:

~~~bash
pip install -r requirements.txt
python app.py --port 5050
~~~

Open http://127.0.0.1:5050. Windows can also use START_CAREER_DESK.cmd after setup.

## Run online

See [README-CLOUD.md](README-CLOUD.md) for the private repository, authenticated Docker/Render deployment and GitHub Actions jobs. The repository contains personal career information and must remain private.

- The online portal's existing Search button executes Python on the hosting server.
- The online GitHub workflow starts that same server job; results appear in the same portal.
- The standalone GitHub workflow runs Python on a GitHub runner and returns a separate results artifact.
- No recurring schedule is enabled.

## Evidence and state

The salary floor is ₹20 LPA annual total CTC; ₹35 LPA is the goal, not an assumed employer budget. Unknown pay, location, vacancy acceptance and profile identity remain unknown. Indexed sources can be stale. Public search does not bypass LinkedIn login/access restrictions and does not guarantee complete employee or vacancy coverage.

The Python job refreshes public job discovery and descriptions. It does not automatically reproduce the manually reviewed, 1,073-check company/profile investigation. Those curated reviews remain preloaded.

research/preloaded_search.json contains resumable scan results. data/workspace.sqlite3 contains notes, preferences and pipeline state. The cloud entry point places these on persistent storage. Original study material and historical observations remain available; Interview Masterclass is not exposed as a route.

## Validate

~~~bash
python -B -m unittest discover -s . -p 'test_*.py'
python -B job_runner.py --mode gcc_all --dry-run
~~~

The tests mock external sources; a successful test run does not prove public sites will accept requests from a cloud IP address.

## Pega recommendations and resume comparison

The scanner now recommends only roles whose saved full description establishes Pega/PRPC responsibilities and explicit experience below eight years. A range including eight is excluded; a minimum-only requirement such as four-plus is labelled as such. Requirements above the candidate's four years are labelled Stretch. A title, a query hit or an employer's Pega branding is not enough. Unread descriptions or unstated experience appear under Needs verification. Earlier discoveries remain saved.

View description opens the captured plain-text posting, source URL/date, and a resume evidence score against sathvik_resume_v2.html. The score explains matched resume evidence, missing requirements, listed-only skills, experience gaps and its weighting. It is not an ATS score or a hiring probability. Refresh description rechecks the exact public posting and preserves the prior snapshot if access fails.

GET /api/opportunities and /api/scan-results default to recommendations. Use scope=review for incomplete evidence or scope=all for explicit archival access. GET /api/opportunities/<id> reads saved detail without network access. POST /api/opportunities/<id>/description requires the portal CSRF token and updates only the saved description cache, preserving pipeline notes.
