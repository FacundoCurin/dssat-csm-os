@echo off
REM ============================================================
REM  Generador de manejos DSSAT - Shiny app (R) - Windows
REM  Requisitos: DSSAT instalado (ej. C:\DSSAT48) y R instalado.
REM  Doble clic en este archivo.
REM ============================================================
cd /d "%~dp0"

where Rscript >nul 2>nul
if errorlevel 1 (
  echo.
  echo  *** Falta R ***
  echo  Instala R desde: https://cran.r-project.org/bin/windows/base/
  echo  Luego volve a hacer doble clic en este archivo.
  echo.
  pause & exit /b 1
)

echo Abriendo la app (la primera vez instala 'shiny', puede tardar)...
Rscript launch.R
pause
