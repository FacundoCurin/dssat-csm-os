#!/usr/bin/env bash
# ============================================================
#  Generador de manejos DSSAT - lanzador para Linux / macOS
#  Requisitos: DSSAT instalado y Python 3.9+
#  Ejecutar:  ./run.sh
# ============================================================
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "*** Falta Python 3.9+ ***"
    echo "Instalalo (ej. 'sudo apt install python3 python3-venv' o desde python.org) y reintentá."
    exit 1
fi

if [ ! -d .venv ]; then
    echo "Creando entorno de Python (solo la primera vez)..."
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Instalando/actualizando la app (la primera vez tarda)..."
python -m pip install --upgrade pip >/dev/null
pip install -e ".[ui]" >/dev/null

echo
echo "============================================================"
echo " Abriendo la app en el navegador: http://localhost:8501"
echo " (para cerrarla, presioná Ctrl+C en esta terminal)"
echo "============================================================"
echo
streamlit run app/streamlit_app.py
