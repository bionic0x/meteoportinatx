@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -3 MeteoPortinatx.pyz & goto :eof)
where python >nul 2>nul && (python MeteoPortinatx.pyz & goto :eof)
echo Portinatx Nowcast necesita Python 3: https://www.python.org/downloads/
pause
