@echo off
echo Building Anti-Client Agent Executable...
venv\Scripts\python.exe -m PyInstaller --noconsole --onefile --name AntiClientAgent client/anti_agent.py --clean
echo Build Complete. Executable is in the 'dist' folder.
pause
