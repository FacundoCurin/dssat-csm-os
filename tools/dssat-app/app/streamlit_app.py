"""UI web (Streamlit) para dssat-app.

Ejecutar con::

    pip install -e ".[ui]"
    streamlit run app/streamlit_app.py

Flujo:
  1. Cargar un FileX (maiz/trigo/soja) e inspeccionar tratamientos.
  2. Elegir modo (N seasonal / Q sequence / B batch), tratamiento y factores.
  3. Definir niveles de cada factor (barrido tipo sensibilidad).
  4. Generar variantes + batch. Opcionalmente correr CSM si hay ejecutable.
  5. Ver tabla y graficos comparativos de las salidas (Summary.OUT).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# permitir correr sin instalar el paquete
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from dssat_app.crops import CROPS, crop_by_filex_ext, get_crop
from dssat_app.filex import FACTORS, FileX
from dssat_app.sweep import Sweep

st.set_page_config(page_title="DSSAT seasonal/sequence", layout="wide")
st.title("🌽🌾🫘 DSSAT — corridas seasonal / sequence y sensibilidad")
st.caption(
    "Genera entradas, lanza CSM y compara salidas para maiz, trigo y soja. "
    "Parte de un FileX real y lo perturba, igual que el analisis de "
    "sensibilidad de DSSAT."
)

with st.sidebar:
    st.header("1. Experimento")
    uploaded = st.file_uploader("FileX (.MZX / .WHX / .SBX)",
                                type=["MZX", "WHX", "SBX", "mzx", "whx", "sbx"])
    crop_key = st.selectbox(
        "Cultivo",
        options=list(CROPS),
        format_func=lambda k: CROPS[k].name_es,
    )
    crop = get_crop(crop_key)
    model = st.selectbox("Modelo CSM", options=crop.models)
    mode = st.radio(
        "Modo de corrida (RNMODE)",
        options=["N", "Q", "B"],
        format_func=lambda m: {
            "N": "N — Seasonal",
            "Q": "Q — Sequence",
            "B": "B — Batch simple",
        }[m],
    )
    st.header("2. Ejecucion")
    dssat_dir = st.text_input("Carpeta de instalacion de DSSAT (opcional)",
                              help="Donde esta DSCSM0XX y los directorios de "
                                   "clima/suelo/genotipo. Si se deja vacio se "
                                   "usa $DSSAT_HOME o el PATH.")
    run_now = st.checkbox("Correr CSM ahora (requiere ejecutable)", value=False)


if uploaded is None:
    st.info("Subi un FileX en la barra lateral para empezar. "
            "Podes usar los experimentos del repositorio dssat-csm-data.")
    st.stop()

# guardar el FileX subido en un temporal
tmp_dir = Path(tempfile.mkdtemp(prefix="dssat_app_"))
filex_path = tmp_dir / uploaded.name
filex_path.write_bytes(uploaded.getvalue())

fx = FileX.read(filex_path)

col1, col2 = st.columns([1, 1])
with col1:
    st.subheader("Tratamientos del FileX")
    trts = fx.treatments()
    trt_df = pd.DataFrame(trts)
    st.dataframe(trt_df, use_container_width=True, hide_index=True)

with col2:
    st.subheader("Secciones detectadas")
    st.write(", ".join(fx.section_names()[:12]) + " ...")

# ---- seleccion de tratamiento y factores ----
st.subheader("3. Barrido de parametros (sensibilidad)")
trt_options = [int(t["N"]) for t in trts if t.get("N", "").strip().isdigit()]
trtno = st.selectbox("Tratamiento base", options=trt_options or [1])

st.markdown("Elegi los factores a variar y sus niveles (separados por coma):")
chosen = st.multiselect(
    "Factores",
    options=list(FACTORS),
    format_func=lambda k: f"{k} — {FACTORS[k].label_es}",
)

factor_levels = {}
for key in chosen:
    fac = FACTORS[key]
    try:
        current = fx.get(fac.section, fac.column, level=fx.treatment_pointer(trtno, fac.pointer))
    except Exception:
        current = ""
    raw = st.text_input(
        f"{key} ({fac.label_es}) — actual: {current}",
        value=current,
        key=f"lv_{key}",
        help="Valores separados por coma, ej: 82030,82057,82084",
    )
    vals = [v.strip() for v in raw.split(",") if v.strip()]
    if vals:
        factor_levels[key] = vals

n_combos = 1
for v in factor_levels.values():
    n_combos *= len(v)
st.write(f"**Combinaciones a generar: {n_combos}**")

if st.button("Generar / Correr", type="primary"):
    sweep = Sweep(filex_path, crop=crop, model=model, trtno=trtno)
    for key, vals in factor_levels.items():
        sweep.add_factor(key, vals)

    work = tmp_dir / "_run"
    if run_now:
        with st.spinner("Corriendo CSM..."):
            try:
                result = sweep.run(work, mode=mode,
                                   dssat_dir=dssat_dir or None)
            except FileNotFoundError as e:
                st.error(str(e))
                st.stop()
        if not result.run.ok:
            st.error(f"CSM devolvio codigo {result.run.returncode}")
            if result.run.error_out:
                st.code(result.run.error_out, language="text")
        table = result.table
    else:
        design = sweep.build(work)
        table = design.to_frame()
        st.success(f"Se generaron {len(design.variant_files)} variantes en {work}")

    st.subheader("Resultados")
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button("Descargar CSV", table.to_csv(index=False),
                       file_name="sweep_resultados.csv", mime="text/csv")

    # grafico si hay salidas
    out_var = None
    for candidate in ("HWAM", "HWAH", "CWAM"):
        if candidate in table.columns:
            out_var = candidate
            break
    if out_var and factor_levels:
        import matplotlib.pyplot as plt
        first_factor = list(factor_levels)[0]
        if first_factor in table.columns:
            fig, ax = plt.subplots()
            ax.plot(table[first_factor].astype(str), table[out_var], "o-")
            ax.set_xlabel(FACTORS[first_factor].label_es)
            ax.set_ylabel(f"{out_var} (kg/ha)")
            ax.set_title("Respuesta simulada")
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
