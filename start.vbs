' Double-click entry: start the local service (backend + frontend) without a console window.
' It silently launches start.ps1 via PowerShell with a hidden window (style 0).
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & dir & "\start.ps1"""
shell.Run cmd, 0, False
