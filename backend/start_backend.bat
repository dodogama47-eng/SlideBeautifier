@echo off
cd /d %~dp0

echo Starting Slide Beautifier backend...

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate

echo Installing requirements...
pip install -r requirements.txt

echo Checking environment file...

if not exist .env (
    echo WARNING: .env file not found.
    echo Please create backend\.env and add:
    echo OPENAI_API_KEY=your_api_key_here
    echo.
)

echo Running FastAPI server...
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

pause