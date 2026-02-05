#!/usr/bin/env bash
set -e

python3 -m venv .venv
# Activate and install dependencies
# Note: running this script will run in a subshell; to activate the venv in your shell run:
#   source .venv/bin/activate
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "Done. Activate with: source .venv/bin/activate"
echo "Run app: streamlit run streamlit_app.py"
