@echo off
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo Done. Activate with: .venv\Scripts\activate
echo Run app: streamlit run streamlit_app.py
