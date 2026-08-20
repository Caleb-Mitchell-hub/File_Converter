' Double-click entry: stop the local service (backend + frontend).
' Runs stop.ps1 hidden, waits for it to finish, then shows a confirmation box.
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & dir & "\stop.ps1"""
shell.Run cmd, 0, True
MsgBox "Local service stopped." & vbCrLf & "See logs\ for details.", vbInformation, "Stop Service"
