Option Explicit

Dim shell, fso, launcherDir, rootDir, scriptPath, pythonwPath, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

launcherDir = fso.GetParentFolderName(WScript.ScriptFullName)
rootDir = fso.GetParentFolderName(launcherDir)
scriptPath = fso.BuildPath(launcherDir, "launch.py")
shell.CurrentDirectory = rootDir
If WScript.Arguments.Count > 0 Then
    pythonwPath = WScript.Arguments(0)
Else
    pythonwPath = "pythonw.exe"
End If
command = """" & pythonwPath & """ """ & scriptPath & """"
shell.Run command, 0, False
