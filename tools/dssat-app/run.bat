@echo off
REM ============================================================
REM  Generador de manejos DSSAT - lanzador para Windows
REM  Requisitos: DSSAT instalado (ej. C:\DSSAT48) y Python 3.9+
REM  Doble clic en este archivo.
REM ============================================================
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo  *** Falta Python ***
    echo  Instala Python 3.9 o superior desde:
    echo      https://www.python.org/downloads/
    echo  Durante la instalacion marca "Add Python to PATH".
    echo  Luego volve a hacer doble clic en este archivo.
    echo.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Creando entorno de Python (solo la primera vez)...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo Instalando/actualizando la app (solo la primera vez tarda)...
python -m pip install --upgrade pip >nul 2>nul
pip install -e ".[ui]" >nul 2>nul
if errorlevel 1 (
    echo Hubo un problema instalando dependencias. Reintentando con detalle...
    pip install -e ".[ui]"
)

echo.
echo ============================================================
echo  Abriendo la app en el navegador: http://localhost:8501
echo  (para cerrarla, cerra esta ventana)
echo ============================================================
echo.
streamlit run app\streamlit_app.py
pause
