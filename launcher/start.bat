@echo off
setlocal
set "BACKEND_PYTHONW=%~dp0..\stock-signal-bot\backend\.venv\Scripts\pythonw.exe"
if exist "%BACKEND_PYTHONW%" goto start_hidden
set "BACKEND_PYTHONW=%~dp0..\.venv\Scripts\pythonw.exe"
if exist "%BACKEND_PYTHONW%" goto start_hidden
set "BACKEND_PYTHONW=pythonw.exe"
:start_hidden
wscript.exe //nologo "%~dp0start-hidden.vbs" "%BACKEND_PYTHONW%"
endlocal
exit /b
