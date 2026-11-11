# Instalación y puesta en marcha — dssat-app

Guía verificada end-to-end en Linux (Ubuntu). Cubre: compilar DSSAT-CSM nativo,
instalar la app Python, preparar los datos y correr.

---

## 1. Requisitos

```bash
sudo apt-get update
sudo apt-get install -y gfortran cmake make git python3 python3-pip
```

- **gfortran** (probado con 13.3) para compilar el modelo.
- **Python ≥ 3.9** para la app.

> El ejecutable de DSSAT para **Windows** (`.exe`) no corre en Linux sin Wine;
> en Linux conviene compilar el binario nativo (paso 2).

---

## 2. Compilar DSSAT-CSM nativo

Desde la raíz del repositorio `dssat-csm-os`:

```bash
cmake -S . -B build -DCMAKE_INSTALL_PREFIX="$HOME/dssathome"
cmake --build build -j
cmake --install build
```

Esto crea `$HOME/dssathome/` con:
- el binario `dscsm048`,
- `DSSATPRO.L48` (rutas Linux ya configuradas),
- `Genotype/`, los `*.CDE`, etc.

Comprobá que arranca:

```bash
$HOME/dssathome/dscsm048   # imprime la ayuda de uso
```

---

## 3. Instalar la app Python

```bash
cd tools/dssat-app
pip install -e ".[ui,dev]"      # núcleo + UI (streamlit) + tests
python -m pytest -q             # 34 tests, no requieren el binario
```

---

## 4. Preparar los datos

DSSAT necesita, además del binario: experimento (**FileX**), clima (**.WTH**),
suelo (**.SOL**) y genotipo (**.CUL/.ECO/.SPE**). Los datos de ejemplo de DSSAT
están en el repo [`DSSAT/dssat-csm-data`](https://github.com/DSSAT/dssat-csm-data).

```bash
# datos de ejemplo
git clone --depth 1 https://github.com/DSSAT/dssat-csm-data ~/dssat-csm-data
cp ~/dssat-csm-data/Weather/*.WTH   ~/dssathome/Weather/
cp ~/dssat-csm-data/Soil/*.SOL      ~/dssathome/Soil/
mkdir -p ~/dssathome/Maize && cp ~/dssat-csm-data/Maize/* ~/dssathome/Maize/
# tus genotipos calibrados sobrescriben los por defecto:
cp MZCER048.CUL MZCER048.ECO MZCER048.SPE ~/dssathome/Genotype/
```

### Utilidades de clima (para series argentinas)

Las series climáticas largas necesitan dos tratamientos antes de usarse
(ver `dssat_app/weather.py`):

```bash
# 1) rellenar radiación solar faltante (SRAD = -99) por Hargreaves
dssat-app weather-fill RAPE8442.WTH --out RAPE_ok.WTH --lat -33.938

# 2) partir la serie larga en archivos anuales <WSTA><AA>01.WTH
#    (CSM sólo cruza el 31-dic con archivos anuales)
dssat-app weather-split RAPE_ok.WTH --out ~/dssathome/Weather --wsta RAPE
```

> **Nota sobre `SOIL.SOL`**: si los nombres de perfil tienen acentos mal
> codificados (bytes `U+FFFD`), CSM puede rechazar el perfil (error 5010).
> Limpialos a ASCII antes de usar el archivo.

---

## 5. Correr

### Línea de comandos

```bash
# inspeccionar un experimento
dssat-app info ~/dssathome/Maize/UFGA8201.MZX

# barrido de fecha de siembra (análisis tipo sensibilidad), modo seasonal
dssat-app sweep ~/dssathome/Maize/UFGA8201.MZX --crop maize --trt 1 \
    --factor pdate=84300,84320,84340 --mode N \
    --out ./_run --dssat-dir ~/dssathome

# rotación (modo sequence Q)
dssat-app sequence MSKB8902.SQX --dssat-dir ~/dssathome --out ./_seq
```

### Interfaz web

```bash
streamlit run app/streamlit_app.py
```

### Python

```python
from dssat_app import Sweep
sw = Sweep("UFGA8201.MZX", crop="maize", model="MZCER048", trtno=1)
sw.add_factor("pdate", ["84300", "84320", "84340"])
res = sw.run("./_run", mode="N", dssat_dir="~/dssathome")
print(res.table[["pdate", "HWAM"]])
```

---

## 6. Resumen de rutas

| Qué | Dónde |
|---|---|
| Código de la app | `tools/dssat-app/` (este repo) |
| Binario compilado | `~/dssathome/dscsm048` (lo generás vos; no va al repo) |
| Datos (clima/suelo/genotipo) | `~/dssathome/{Weather,Soil,Genotype,Maize}` (tuyos; no van al repo) |
| Ejemplos de salida | `tools/dssat-app/examples/` (ver `EJEMPLOS.md`) |

Para qué hace cada módulo y la hoja de ruta, ver [`README.md`](README.md).
