#!/bin/bash

VENV_NAME=cSMTP
REQUIREMENTS=requirements.txt

echo Creating virtual environment...
python3 -m venv $VENV_NAME
source $VENV_NAME/bin/activate

echo Virtual environment is created!

echo Installing requirements...
pip3 install -r $REQUIREMENTS

echo To activate the virtual environment please run the following command: $VENV_NAME/bin/activate