' Runs run_windows.bat with a hidden window, for start-at-login use
' (avoids popping up a console window on every login).
' autostart_windows.py points the login-run registry value at this file:
'   wscript.exe "<path to this file>"
Dim fso, shell, scriptDir
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.Run """" & scriptDir & "\run_windows.bat""", 0, False
