@echo off
setlocal
set "BACKEND_PYTHONW=%~dp0..\stock-signal-bot\backend\.venv\Scripts\pythonw.exe"
if not exist "%BACKEND_PYTHONW%" set "BACKEND_PYTHONW=pythonw.exe"
wscript.exe //nologo "%~dp0start-hidden.vbs" "%BACKEND_PYTHONW%"
endlocal
exit /b
