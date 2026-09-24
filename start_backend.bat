@echo off
title DataMind AI - Enterprise Backend Server
color 0b
echo ===============================================================================
echo            DATAMIND AI - ENTERPRISE BACKEND SERVER LAUNCHER
echo ===============================================================================
echo.
echo [1/3] Checking Python environment...
python --version
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH. Please install Python 3.10+.
    pause
    exit /b 1
)

echo.
echo [2/3] Verifying PostgreSQL connection & database...
python -c "from backend.database.connection import check_db_connection; d = check_db_connection(); print('Database Status:', d.get('status'), '| DB:', d.get('database'))"

echo.
echo [3/3] Starting Uvicorn API Server on http://127.0.0.1:8000 ...
echo - Frontend Application URL : http://127.0.0.1:8000
echo - Interactive Swagger Docs : http://127.0.0.1:8000/docs
echo - PostgreSQL Health Check  : http://127.0.0.1:8000/api/health
echo.
echo [INFO] Press Ctrl+C anytime to stop the server.
echo ===============================================================================
echo.

python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
pause
