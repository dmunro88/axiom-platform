@echo off
cd /d "%~dp0"
echo Starting Axiom Command Center...
echo (First run installs a few packages -- this can take a minute.)
echo.

python -m pip install --quiet streamlit python-docx openpyxl requests

if errorlevel 1 (
    echo.
    echo Something went wrong installing required packages.
    echo Make sure Python is installed and on your PATH, then try again.
    pause
    exit /b 1
)

echo.
echo Launching in your browser...
python -m streamlit run axiom_ui.py

pause
