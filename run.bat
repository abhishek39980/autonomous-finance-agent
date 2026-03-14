@echo off
REM ─────────────────────────────────────────────────────────────────
REM  Bank Statement Analyzer — One-Click Launcher
REM  Requires: LM Studio running with server on port 1234
REM            OR Ollama running (ollama serve)
REM ─────────────────────────────────────────────────────────────────

echo.
echo  ====================================================
echo   💰 Bank Statement Analyzer — Starting...
echo  ====================================================
echo.

REM Activate virtual environment (try .venv first, then venv)
IF EXIST ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) ELSE IF EXIST "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) ELSE (
    echo  ⚠ No virtual environment found. Using system Python.
)

echo  📦 Installing/verifying dependencies...
pip install -q -r requirements.txt

echo.
echo  🚀 Starting Streamlit app...
echo  📌 Open your browser at: http://localhost:8501
echo.
echo  ℹ Make sure LM Studio is running with the server started on port 1234
echo    OR Ollama is running (run: ollama serve)
echo.

streamlit run bank_app.py --server.port=8501 --server.headless=false

pause
