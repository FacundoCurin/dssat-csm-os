#!/usr/bin/env bash
# ============================================================
#  Generador de manejos DSSAT - Shiny app (R) - Linux / macOS
#  Requisitos: DSSAT instalado y R instalado.
#  Ejecutar:  ./run_shiny.sh
# ============================================================
cd "$(dirname "$0")"

if ! command -v Rscript >/dev/null 2>&1; then
  echo "*** Falta R ***  Instalalo (ej. 'sudo apt install r-base') y reintentá."
  exit 1
fi

echo "Abriendo la app (la primera vez instala 'shiny', puede tardar)..."
Rscript launch.R
