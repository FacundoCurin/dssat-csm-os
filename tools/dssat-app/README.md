# dssat-app

Driver y GUI en **Python** para armar corridas **seasonal** (modo `N`) y
**sequence** (modo `Q`) de DSSAT-CSM, y para hacer **barridos de parámetros
tipo análisis de sensibilidad**, enfocado en **maíz, trigo y soja**.

Es el equivalente en Python del programa interactivo de *Sensitivity Analysis*
de DSSAT (`InputModule/SENS.for` + familia `SE*.for`): parte de un
**experimento real** (FileX) y lo **perturba** de forma controlada, pero en
lugar de tocar un cultivar/experimento a la vez permite definir un barrido
factorial, correr todo en batch y comparar las salidas.

> Vive en `tools/dssat-app/`, aislado del árbol Fortran del modelo. No modifica
> el código de CSM.

## Qué hace

1. **Generar entradas** — lee y edita el FileX conservando el formato de
   columnas fijas que CSM exige (fechas de siembra, densidad, cultivar, N,
   riego, controles de simulación…).
2. **Lanzar corridas** — escribe un `DSSBatch.v48` byte-exacto y ejecuta
   `DSCSM0XX` en modo `N`/`Q`/`B`.
3. **Analizar salidas** — parsea `Summary.OUT` y series diarias
   (`PlantGro.OUT`, etc.) a `pandas.DataFrame`.
4. **Barrido de sensibilidad** — producto cartesiano de factores × niveles,
   una variante de FileX por combinación, y tabla final que une cada corrida
   con su combinación.

## Arquitectura

```
dssat_app/
  crops.py    Catálogo de cultivos y códigos de modelo/modo (MZCER048, ...)
  filex.py    Lector/editor del FileX consciente de columnas  ← núcleo
  batch.py    Generación del DSSBatch.v48 (alineado a CSM_Main/CSM.for)
  runner.py   Ejecución del binario DSCSM0XX en un dir de trabajo
  outputs.py  Parseo de *.OUT (Summary + series diarias)
  sweep.py    Motor de barrido (análisis tipo sensibilidad)
  cli.py      Línea de comandos (info / batch / sweep)
app/
  streamlit_app.py   Interfaz web
tests/        Suite con un FileX de maíz de ejemplo (no requiere CSM)
```

### Por qué así

- El **FileX** es de columnas de ancho fijo; el valor se alinea con el último
  carácter del token del encabezado `@`. `filex.py` usa esa regla para
  leer/escribir sin romper el alineamiento (requisito de CSM).
- El **batch** lo lee CSM en `CSM_Main/CSM.for` (~líneas 264-293): la ruta+FileX
  ocupa las columnas 1-92 (el nombre son los últimos 12 caracteres) y luego
  `3(1X,I6)` para `TRTNO`, `RP` y `SQ`/rotación. `batch.py` reproduce eso
  exactamente; para evitar problemas de ruta se referencia el FileX por su
  nombre (12 car.) y se corre con *cwd* en el directorio de trabajo.
- El **barrido** genera un FileX por combinación y edita, para el nivel que
  usa el tratamiento elegido, la celda del factor. Así se evita cirugía frágil
  sobre la tabla de tratamientos.

## Instalación

```bash
cd tools/dssat-app
pip install -e ".[ui,dev]"
```

## Uso (CLI)

```bash
# Inspeccionar un FileX
dssat-app info UFGA8201.MZX

# Solo generar el diseño (variantes de FileX), sin correr
dssat-app sweep UFGA8201.MZX --crop maize --trt 1 \
    --factor pdate=82030,82057,82084 --factor ppop=6,7.2,8.5 \
    --mode N --out ./_run --design-only

# Generar y correr CSM (requiere ejecutable + archivos de clima/suelo/genotipo)
dssat-app sweep UFGA8201.MZX --crop maize --trt 1 \
    --factor pdate=82030,82057,82084 \
    --mode N --out ./_run --dssat-dir /opt/dssat \
    --input GAINESVL.WTH --input SOIL.SOL
```

## Uso (web)

```bash
streamlit run app/streamlit_app.py
```

## Uso (Python)

```python
from dssat_app import Sweep

sw = Sweep("UFGA8201.MZX", crop="maize", trtno=1)
sw.add_factor("pdate", ["82030", "82057", "82084"])
sw.add_factor("famn",  ["0", "100", "200"])
res = sw.run("./_run", mode="N", dssat_dir="/opt/dssat")
print(res.table[["pdate", "famn", "HWAM"]])
```

## Factores de barrido disponibles

| clave  | sección             | columna | descripción                         |
|--------|---------------------|---------|-------------------------------------|
| pdate  | PLANTING DETAILS    | PDATE   | fecha de siembra (YYDDD)            |
| ppop   | PLANTING DETAILS    | PPOP    | densidad (pl/m²)                    |
| plrs   | PLANTING DETAILS    | PLRS    | espaciamiento entre hileras (cm)    |
| pldp   | PLANTING DETAILS    | PLDP    | profundidad de siembra (cm)         |
| ingeno | CULTIVARS           | INGENO  | cultivar (código)                   |
| famn   | FERTILIZERS         | FAMN    | N aplicado (kg/ha)                  |
| sdate  | SIMULATION CONTROLS | SDATE   | inicio de simulación (YYDDD)        |
| nyers  | SIMULATION CONTROLS | NYERS   | nº de años (seasonal/sequence)      |

Agregar un factor nuevo = una línea en `FACTORS` (en `dssat_app/filex.py`).

## Requisitos para correr de verdad

La app **no incluye** el modelo ni los datos. Para corridas reales necesitás:

- Un **ejecutable `DSCSM0XX`** compilado (desde la raíz de este repo con CMake).
- Los **archivos de entrada** que CSM espera: FileX + clima (`*.WTH`) + suelo
  (`*.SOL`) + genotipo (`*.CUL`/`*.ECO`/`*.SPE`) y el archivo `DSSATPRO`/`.CTR`
  que indica dónde están. Normalmente vienen de `dssat-csm-data`.

Sin ejecutable, la app igual sirve para **generar y validar entradas** y para
**analizar salidas** ya producidas.

## Estado y hoja de ruta

- [x] Núcleo FileX (leer/editar), batch N/Q/B, parser de salidas, barrido
      factorial, CLI y UI. 21 tests en verde (no requieren CSM).
- [ ] Modo **sequence (Q)** completo: edición de la sección de rotaciones
      (`*TILLAGE AND ROTATIONS` / enlaces de secuencia) y armado de rotaciones
      multi-cultivo maíz→trigo→soja.
- [ ] Autodetección del `DSSATPRO`/`.CTR` y copia automática de clima/suelo.
- [ ] Parseo multi-año (NYERS>1) con mapeo por `RUNNO` y agregados estadísticos.
- [ ] Lectura de más salidas diarias (SoilWat, ET, N) y gráficos comparativos.

## Pruebas

```bash
cd tools/dssat-app
python -m pytest -q
```
