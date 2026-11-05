@echo off
REM AI Yordamchi — Windows uchun .exe yig'ish
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "AI-Yordamchi" --icon assets\icon.ico app.py
echo.
echo Tayyor: dist\AI-Yordamchi.exe
pause
