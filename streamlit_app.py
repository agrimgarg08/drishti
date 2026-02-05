"""Launcher delegator for Streamlit Cloud/entry point.

This file delegates execution to `frontend/app.py` so deployments that point
at the top-level `streamlit_app.py` will run your main dashboard.
"""
import runpy
import os

APP_PATH = os.path.join(os.path.dirname(__file__), "frontend", "app.py")

if not os.path.exists(APP_PATH):
    raise RuntimeError(f"Missing dashboard: {APP_PATH} not found. Please ensure frontend/app.py exists.")

# Execute the dashboard as a script so Streamlit picks it up as the app
runpy.run_path(APP_PATH, run_name="__main__")
