@echo off
REM Hermes — pull entire data folder from VPS to D:\Hermes-data-backup\
REM
REM Usage: double-click this file from File Explorer, OR run from cmd:
REM   D:\Hermes\scripts\download-from-vps.bat
REM
REM You'll be prompted for your VPS root password once. The script downloads
REM the SQLite database, raw bhav copy CSVs, and any logs to a timestamped
REM local folder so each run is preserved separately.

setlocal

set VPS_HOST=root@187.127.173.149
set VPS_PATH=/opt/hermes/data/
set LOCAL_BASE=D:\Hermes-data-backup

REM Build a date-stamped target folder so successive backups don't overwrite.
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set DATESTAMP=%%c-%%a-%%b)
for /f "tokens=1-2 delims=:" %%a in ('time /t') do (set TIMESTAMP=%%a%%b)
set TARGET=%LOCAL_BASE%\%DATESTAMP%-%TIMESTAMP%

echo.
echo ============================================================
echo  Hermes VPS data backup
echo ============================================================
echo  From:  %VPS_HOST%:%VPS_PATH%
echo  To:    %TARGET%
echo ============================================================
echo.

if not exist "%LOCAL_BASE%" mkdir "%LOCAL_BASE%"
mkdir "%TARGET%"

echo Starting scp (you may be prompted for VPS password)...
scp -r %VPS_HOST%:%VPS_PATH% "%TARGET%"

if errorlevel 1 (
    echo.
    echo FAILED — check VPS connectivity / password.
    pause
    exit /b 1
)

echo.
echo Done. Files are at: %TARGET%
echo.
echo To inspect:
echo   - Open %TARGET%\data\hermes.db with DB Browser for SQLite
echo   - Or in Python: pd.read_sql(query, sqlite3.connect(r"%TARGET%\data\hermes.db"))
echo.
pause
