@echo off
title SportsHub - AI Sports Management Platform
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
  echo Creating virtual environment...
  python -m venv venv
)
echo Installing/updating requirements...
venv\Scripts\python.exe -m pip install -r requirements.txt
echo Applying migrations...
venv\Scripts\python.exe manage.py migrate
echo Seeding demo data...
venv\Scripts\python.exe manage.py seed_data
echo Starting SportsHub at http://127.0.0.1:8000/
start "" http://127.0.0.1:8000/login/
venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
pause
