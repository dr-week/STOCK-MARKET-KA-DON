Option Explicit

Dim shell, fso, launcherDir, scriptPath, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

launcherDir = fso.GetParentFolderName(WScript.ScriptFullName)
scriptPath = fso.BuildPath(launcherDir, "launch.py")
shell.CurrentDirectory = fso.GetParentFolderName(launcherDir)
command = "pythonw.exe """ & scriptPath & """"
shell.Run command, 0, False
