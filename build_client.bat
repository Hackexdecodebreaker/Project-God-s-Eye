@echo off
echo Building Client Agent Executable...
python -m PyInstaller --noconsole --onefile --name GodsEyeAgent client/agent.py
echo Build Complete. Executable is in the 'dist' folder.
pause
