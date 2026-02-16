@echo off
cd /d "%~dp0"

set "VENV_DIR=%LOCALAPPDATA%\FortuneShorts-venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo First run: creating venv...
    py -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERROR: venv failed. Install Python.
        pause
        exit /b 1
    )
    echo First run: installing packages...
    "%PYTHON_EXE%" -m pip install --upgrade pip -q
    "%PYTHON_EXE%" -m pip install -r requirements.txt --prefer-binary
    if errorlevel 1 (
        echo ERROR: pip install failed.
        pause
        exit /b 1
    )
    echo Done.
    echo.
)

echo Starting Tarot Channel (port 8502)...
start "TarotChannel" /D "%~dp0" "%PYTHON_EXE%" -m streamlit run app.py --server.port 8502
echo Waiting for server...
ping localhost -n 7 >nul
start http://localhost:8502
echo.
echo Browser opened. URL must be :8502 (not 8501).
echo Close the server window to exit.
pause
