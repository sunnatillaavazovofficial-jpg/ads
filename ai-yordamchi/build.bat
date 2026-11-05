@echo off
chcp 65001 >nul
REM AI Yordamchi — Windows uchun .exe yig'ish
cd /d "%~dp0"

REM Python buyrug'ini topish: avval "py" (Windows launcher), keyin "python"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [XATO] Python topilmadi.
    echo https://www.python.org/downloads/ dan Python 3.10+ o'rnating
    echo va o'rnatishda "Add python.exe to PATH" belgisini qo'ying.
    pause
    exit /b 1
)

echo Python: %PY%
%PY% --version || goto :error

echo.
echo [1/2] Kutubxonalar o'rnatilmoqda...
%PY% -m pip install --upgrade pip || goto :error
%PY% -m pip install -r requirements.txt pyinstaller || goto :error

echo.
echo [2/2] .exe yig'ilmoqda...
%PY% -m PyInstaller --noconfirm --onefile --windowed --name "AI-Yordamchi" --icon assets\icon.ico app.py || goto :error

if not exist "dist\AI-Yordamchi.exe" goto :error

echo.
echo ==========================================
echo  Tayyor: %CD%\dist\AI-Yordamchi.exe
echo ==========================================
explorer dist
pause
exit /b 0

:error
echo.
echo [XATO] Yig'ish muvaffaqiyatsiz tugadi. Yuqoridagi xabarni o'qing.
pause
exit /b 1
