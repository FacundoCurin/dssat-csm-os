@echo off
REM ============================================================
REM  Generador de manejos DSSAT - Shiny app (R) - Windows
REM  Requisitos: DSSAT instalado (ej. C:\DSSAT48) y R instalado.
REM  Doble clic en este archivo (funciona aunque la ruta tenga espacios).
REM ============================================================
cd /d "%~dp0"

REM 1) buscar Rscript en el PATH
set "RS="
for /f "delims=" %%I in ('where Rscript 2^>nul') do if not defined RS set "RS=%%I"

REM 2) si no esta en el PATH, buscar en las instalaciones tipicas de R
if not defined RS (
  for /d %%D in ("C:\Program Files\R\R-*") do set "RS=%%D\bin\Rscript.exe"
)
if not defined RS (
  for /d %%D in ("C:\Program Files\Microsoft\R Open\R-*") do set "RS=%%D\bin\Rscript.exe"
)

if not defined RS (
  echo.
  echo  *** No encontre R ***
  echo  Instala R desde: https://cran.r-project.org/bin/windows/base/
  echo  Si ya lo tenes, abri la app desde RStudio (ver LEEME.md).
  echo.
  pause & exit /b 1
)

echo Usando R: %RS%
echo Abriendo la app (la primera vez instala 'shiny', puede tardar)...
"%RS%" launch.R
pause
