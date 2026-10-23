@echo off
setlocal
rem Usa Python instalado o, dentro de Codex, el runtime ya disponible.
py -3 -c "import sys; assert sys.version_info >= (3, 12)" >nul 2>nul
if not errorlevel 1 goto installed
set "MONITOR_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%MONITOR_PYTHON%" goto bundled
echo No se encontro Python 3.12 o posterior. Instala Python y ejecuta python monitor.py.
exit /b 2

:installed
py -3 "%~dp0monitor.py" %*
exit /b %errorlevel%

:bundled
"%MONITOR_PYTHON%" "%~dp0monitor.py" %*
exit /b %errorlevel%
