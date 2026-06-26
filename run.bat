@echo off
echo Starting PurrFacts Studio...
start "PurrFacts Backend"  cmd /k "cd /d "%~dp0backend"  && venv\Scripts\activate && uvicorn main:app --reload --port 8000"
timeout /t 4 >nul
start "PurrFacts Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"
timeout /t 3 >nul
start http://localhost:5173
