Option Explicit

Dim shell, fso, launcherDir, rootDir, scriptPath, pythonwPath, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

launcherDir = fso.GetParentFolderName(WScript.ScriptFullName)
rootDir = fso.GetParentFolderName(launcherDir)
scriptPath = fso.BuildPath(launcherDir, "launch.py")
shell.CurrentDirectory = rootDir
pythonwPath = fso.BuildPath(rootDir, "stock-signal-bot\backend\.venv\Scripts\pythonw.exe")
If Not fso.FileExists(pythonwPath) Then
    pythonwPath = "pythonw.exe"
End If
command = """" & pythonwPath & """ """ & scriptPath & """"
shell.Run command, 0, False
