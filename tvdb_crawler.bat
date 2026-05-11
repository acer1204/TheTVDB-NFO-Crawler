@echo off
chcp 65001 >nul 2>&1
if "%1"=="web" goto web
if "%1"=="server" goto web
py "%~dp0tvdb_crawler.py" %*
goto end
:web
py "%~dp0server.py"
:end
