@echo off
cd d %~dp0

echo Starting Slide Beautifier backend...

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venvScriptsactivate

echo Installing requirements...
pip install -r requirements.txt

echo Running FastAPI server...

uvicorn main:app --host 0.0.0.0 --port 8080 --reload
pause