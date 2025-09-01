@echo off
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del VotingSystem.spec 2>nul

pyinstaller --noconfirm --name wenhuah --onefile ^
  --icon wenhuah-logo.ico ^
  --hidden-import waitress ^
  --hidden-import flask_sqlalchemy ^
  --hidden-import flask_migrate ^
  --hidden-import jinja2 ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "instance;instance" ^
  run_server.py

pause
