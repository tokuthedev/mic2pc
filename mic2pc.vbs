Set WshShell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
pythonwPath = scriptDir & "\pc-receiver\venv\Scripts\pythonw.exe"
mainPath = scriptDir & "\pc-receiver\main.py"
WshShell.Run """" & pythonwPath & """ """ & mainPath & """", 0, False
