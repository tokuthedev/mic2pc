Set WshShell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
pythonwPath = scriptDir & "\venv\Scripts\pythonw.exe"
mainPath = scriptDir & "\main.py"
WshShell.Run """" & pythonwPath & """ """ & mainPath & """", 0, False
