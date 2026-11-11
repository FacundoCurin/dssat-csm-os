"""Generador de manejos DSSAT — interfaz web (Streamlit).

Flujo pensado para reemplazar los scripts: elegís cultivo + experimento,
definís los manejos a comparar (fecha de siembra, densidad, N, cultivar…),
corrés DSSAT y ves/descargás los resultados, todo desde el navegador.

Ejecutar localmente:
    pip install -e ".[ui]"
    streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from dssat_app.crops import CROPS, get_crop
from dssat_app.filex import FACTORS, FileX
from dssat_app.sweep import Sweep

st.set_page_config(page_title="Generador de manejos DSSAT", layout="wide")
st.title("🌱 Generador de manejos DSSAT")
st.caption("Armá los manejos (fecha, densidad, N, cultivar, riego), corré el "
           "modelo y compará resultados — maíz, trigo y soja.")

CROP_DIR = {"maize": "Maize", "wheat": "Wheat", "soybean": "Soybean"}


def detect_dssat_home() -> str:
    """Busca una instalación de DSSAT en ubicaciones habituales."""
    env = os.environ.get("DSSAT_HOME")
    if env and Path(env).exists():
        return env
    candidates = [
        Path.home() / "dssathome",
        *[Path(f"{d}:/DSSAT{v}") for d in ("C", "D")
          for v in ("48", "47", "49", "46")],
        Path("/opt/dssat"), Path("/usr/local/dssat"),
        Path.home() / "DSSAT48", Path.home() / "dssat",
    ]
    for c in candidates:
        try:
            if c.exists() and (list(c.glob("DSCSM*")) or list(c.glob("dscsm*"))):
                return str(c)
        except OSError:
            continue
    return env or str(Path.home() / "dssathome")


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("1 · Modelo y datos")
    dssat_dir = st.text_input(
        "Carpeta DSSAT (binario + datos)", value=detect_dssat_home(),
        help="Carpeta de tu instalación de DSSAT (p. ej. C:\\DSSAT48). "
             "Debe tener el ejecutable DSCSM0XX y las carpetas Maize/Wheat/Soybean.")
    if not (Path(dssat_dir).exists() and
            (list(Path(dssat_dir).glob("DSCSM*")) or list(Path(dssat_dir).glob("dscsm*")))):
        st.warning("No encuentro el ejecutable de DSSAT en esa carpeta. "
                   "Verificá la ruta de tu instalación.")
    crop_key = st.selectbox("Cultivo", list(CROPS),
                            format_func=lambda k: CROPS[k].name_es)
    crop = get_crop(crop_key)
    model = st.selectbox("Modelo", crop.models)

    # experimentos disponibles en la carpeta del cultivo
    exp_dir = Path(dssat_dir) / CROP_DIR[crop_key]
    exts = {"maize": "MZX", "wheat": "WHX", "soybean": "SBX"}[crop_key]
    exps = sorted(p.name for p in exp_dir.glob(f"*.{exts}")) if exp_dir.exists() else []
    uploaded = st.file_uploader(f"…o subí un FileX (.{exts})",
                                type=[exts, exts.lower()])
    exp_name = st.selectbox("Experimento", exps) if exps else None

    st.header("2 · Condiciones")
    secano = st.checkbox("Secano (sin riego)", value=True)
    n_no_lim = st.checkbox("N no limitante", value=False,
                           help="Rinde alcanzable sin estrés de N")
    nyers = st.number_input("Años a simular (variabilidad climática)",
                            1, 60, 1)
    sh2o = st.slider("Humedad inicial del perfil (cm³/cm³)", 0.05, 0.40, 0.26, 0.01)

    st.header("3 · Ejecución")
    run_now = st.checkbox("Correr DSSAT (si hay binario)", value=True)

# cargar FileX base
tmp_dir = Path(tempfile.mkdtemp(prefix="dssat_app_"))
if uploaded is not None:
    base_path = tmp_dir / uploaded.name
    base_path.write_bytes(uploaded.getvalue())
elif exp_name:
    base_path = exp_dir / exp_name
else:
    st.info("Elegí un experimento o subí un FileX para empezar.")
    st.stop()

fx = FileX.read(base_path)

c1, c2 = st.columns([3, 2])
with c1:
    st.subheader("Tratamientos del experimento")
    trts = fx.treatments()
    st.dataframe(pd.DataFrame(trts), use_container_width=True, hide_index=True)
with c2:
    st.subheader("Experimento")
    st.write(f"**{base_path.name}** · cultivo: {crop.name_es} · modelo: {model}")
    try:
        st.write("Clima (WSTA):", fx.get("FIELDS", "WSTA", level=1),
                 "· Suelo:", fx.get("FIELDS", "ID_SOIL", level=1))
    except Exception:
        pass

trt_opts = [int(t["N"]) for t in trts if t.get("N", "").strip().isdigit()]
trtno = st.selectbox("Tratamiento base", trt_opts or [1])

# ---------------------------------------------------------------- manejos
st.subheader("Manejos a comparar")
st.caption("Elegí qué variar y con qué niveles (separados por coma). "
           "El producto de todos = las corridas que se generan.")
chosen = st.multiselect("Factores de manejo", list(FACTORS),
                        format_func=lambda k: f"{k} — {FACTORS[k].label_es}")
levels = {}
cols = st.columns(2)
for i, key in enumerate(chosen):
    fac = FACTORS[key]
    with cols[i % 2]:
        try:
            cur = fx.get(fac.section, fac.column,
                         level=fx.treatment_pointer(trtno, fac.pointer))
        except Exception:
            cur = ""
        raw = st.text_input(f"{key} — {fac.label_es} (actual: {cur})",
                            value=cur, key=f"lv_{key}")
        vals = [v.strip() for v in raw.split(",") if v.strip()]
        if vals:
            levels[key] = vals

n_combos = 1
for v in levels.values():
    n_combos *= len(v)
st.write(f"**Corridas a generar: {n_combos}**"
         + (f" × {nyers} años" if nyers > 1 else ""))

# ---------------------------------------------------------------- correr
if st.button("▶ Generar y correr", type="primary"):
    # preprocesar el FileX base con las condiciones elegidas
    base2 = fx.copy()
    try:
        base2.set_all("SIMULATION CONTROLS", "IRRIG", "N" if secano else "R")
        base2.set_all("SIMULATION CONTROLS", "NITRO", "N" if n_no_lim else "Y")
        base2.set_all("SIMULATION CONTROLS", "NYERS", int(nyers))
        base2.set_all("INITIAL CONDITIONS", "SH2O", sh2o)
    except Exception as e:
        st.warning(f"No pude ajustar algunas opciones: {e}")
    base2_path = tmp_dir / base_path.name
    base2.write(base2_path)

    sweep = Sweep(base2_path, crop=crop, model=model, trtno=trtno)
    for key, vals in levels.items():
        sweep.add_factor(key, vals)

    work = tmp_dir / "_run"
    if run_now:
        with st.spinner("Corriendo DSSAT…"):
            try:
                res = sweep.run(work, mode="N", dssat_dir=dssat_dir or None)
            except FileNotFoundError as e:
                st.error(str(e)); st.stop()
        if not res.run.ok:
            st.error(f"DSSAT devolvió código {res.run.returncode}")
            if res.run.error_out:
                st.code(res.run.error_out[-1500:], language="text")
        table = res.table
    else:
        design = sweep.build(work)
        table = design.to_frame()
        st.success(f"{len(design.variant_files)} variantes generadas en {work}")

    st.subheader("Resultados")
    # columnas de interés primero
    show = [c for c in list(levels) + ["PDAT", "ADAT", "MDAT", "HWAM", "CWAM",
            "PRCP", "NUCM"] if c in table.columns]
    show = show or list(table.columns)
    st.dataframe(table[show] if show else table, use_container_width=True,
                 hide_index=True)
    st.download_button("⬇ Descargar CSV", table.to_csv(index=False),
                       file_name="manejos_resultados.csv", mime="text/csv")

    # gráfico de respuesta
    yvar = next((v for v in ("HWAM", "HWAH", "CWAM") if v in table.columns), None)
    if yvar and levels:
        import matplotlib.pyplot as plt
        f0 = list(levels)[0]
        if f0 in table.columns:
            fig, ax = plt.subplots()
            if nyers > 1:
                g = table.groupby(f0)[yvar].mean()
                ax.plot(g.index.astype(str), g.values, "o-")
                ax.set_ylabel(f"{yvar} medio (kg/ha)")
            else:
                ax.plot(table[f0].astype(str), table[yvar], "o-")
                ax.set_ylabel(f"{yvar} (kg/ha)")
            ax.set_xlabel(FACTORS[f0].label_es)
            ax.set_title("Respuesta simulada")
            ax.grid(alpha=.3)
            st.pyplot(fig)
