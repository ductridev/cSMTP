@echo off

set VENV_NAME=cSMTP
set REQUIREMENTS=requirements.txt

echo Creating virtual environment...
python -m venv %VENV_NAME%
call %VENV_NAME%\Scripts\activate

echo Virtual environment is created!

echo Installing requirements...
pip install -r %REQUIREMENTS%

echo To activate the virtual environment please run the following command: %VENV_NAME%\Scripts\activate