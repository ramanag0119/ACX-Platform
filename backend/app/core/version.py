"""The API's release version.

Lives here rather than in `app.main` so endpoints can report it without
importing the application factory. `app.main` passes it to FastAPI, which puts
it in /openapi.json.
"""

API_VERSION = "0.3.0"
