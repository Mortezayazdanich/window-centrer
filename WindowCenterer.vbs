' Window Centerer Silent Launcher
' Runs the app in background without opening or flashing a console window.
Dim fso, scriptDir, pythonwPath, wshShell

Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

Set wshShell = CreateObject("WScript.Shell")
wshShell.CurrentDirectory = scriptDir

' Launch pythonw main.py silently (0 = hide window, False = don't wait)
wshShell.Run "cmd.exe /c pythonw main.py", 0, False

Set wshShell = Nothing
Set fso = Nothing
