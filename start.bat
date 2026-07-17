@echo off
echo =========================================
echo  Vulnerable Shop - Starting...
echo =========================================
echo.
echo Access: http://localhost:5000
echo Test credentials: admin / admin123
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Starting application...
python main.py
pause
