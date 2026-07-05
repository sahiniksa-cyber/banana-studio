@echo off
chcp 65001 > nul
title منصة القوالب - توليد الصور
cd /d "%~dp0"

echo.
echo  ===================================
echo    منصة القوالب - جاري التشغيل
echo  ===================================
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo [خطأ] Python غير مثبت!
    echo حمّله من: https://python.org  ثم أعد المحاولة
    pause
    exit /b
)

echo [1/2] تثبيت المتطلبات (مرة واحدة فقط)...
python -m pip install -r requirements.txt -q

echo [2/2] تشغيل المنصة...
echo.
echo  المتصفح بينفتح تلقائيًا على: http://localhost:5001
echo  لإيقاف المنصة: اضغط Ctrl+C أو اقفل هذه النافذة
echo.

REM افتح المتصفح تلقائيًا بعد ثانيتين
start "" /b cmd /c "timeout /t 2 > nul & start http://localhost:5001"

python app.py

pause
