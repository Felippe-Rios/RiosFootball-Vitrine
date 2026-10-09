@echo off
cd /d "%~dp0"

py --version >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)

if not exist venv\Scripts\activate.bat (
  echo Criando o ambiente virtual, so na primeira vez...
  %PY% -m venv venv
)
call venv\Scripts\activate.bat

python -c "import flask" >nul 2>nul
if errorlevel 1 (
  echo Instalando o Flask, so na primeira vez...
  python -m pip install flask
)

echo.
echo RiosFootball no ar! Abra no navegador: http://localhost:5000
echo Para desligar, feche esta janela.
echo.
python backend\app.py
pause
