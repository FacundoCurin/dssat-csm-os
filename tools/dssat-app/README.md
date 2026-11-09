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

📦 **Instalación paso a paso:** [`INSTALL.md`](INSTALL.md) ·
📊 **Ejemplos de resultados (Pampa):** [`EJEMPLOS.md`](EJEMPLOS.md)

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
  sweep.py    Motor de barrido seasonal (análisis tipo sensibilidad)
  sequence.py Rotaciones multi-cultivo (modo Q): maíz→soja→trigo
  weather.py  Parte series largas .WTH en archivos anuales DSSAT
  cli.py      Línea de comandos (info / batch / sweep / sequence / weather-split)
app/
  streamlit_app.py   Interfaz web
tests/        Suite con FileX de maíz (.MZX) y rotación (.SQX) de ejemplo
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

### Secuencias / rotaciones (modo Q)

```bash
# Ver la rotación de un experimento de secuencia
dssat-app sequence MSKB8902.SQX --rotation-only

# Correr la rotación maíz→soja→trigo (remapeando un cultivar ausente)
dssat-app sequence MSKB8902.SQX --model MZCER048 --dssat-dir "$HOME/dssathome" \
    --cultivar 6=IB0091 --out ./_seq
```

```python
from dssat_app import SequenceExperiment

seq = SequenceExperiment("MSKB8902.SQX", trtno=1)
seq.set_cultivar(6, "IB0091")      # usar un cultivar presente en tu .CUL
res = seq.run("./_seq", model="MZCER048", dssat_dir="~/dssathome")
print(res.yield_by_crop())          # rinde medio por cultivo
print(res.soil_carbon_change())     # evolución del C orgánico del suelo
```

Qué resuelve el modo secuencia (todo verificado contra CSM):
- **Una línea de batch por componente de rotación** (`SQ`=R); con una sola
  línea CSM repite el primer cultivo (monocultivo).
- Fuerza `SUMRY=Y` y `FNAME=N` para que la salida sea `Summary.OUT` estándar
  (con `FNAME=Y` se renombra a `<EXP>.OSU`).
- Etiqueta cada campaña con su cultivo y resume rinde por cultivo y el cambio
  de carbono orgánico del suelo a lo largo de la rotación.
- Si un cultivar del experimento no está en tu archivo de genotipo, CSM aborta
  ("Error in Cultivar entry"): remapealo con `set_cultivar`/`--cultivar`.

### Clima: series largas → archivos anuales

CSM cruza bien el 31-dic (campañas de primavera a otoño del año siguiente)
sólo con **archivos anuales** `<WSTA><AA>01.WTH`; una única serie larga suele
cortar en fin de año (error 29 / salidas -99). Para partir una serie:

```bash
dssat-app weather-split RAPE8442.WTH --out "$HOME/dssathome/Weather" --wsta RAPE
```

```python
from dssat_app import split_multiyear
split_multiyear("RAPE.WTH", "~/dssathome/Weather", wsta="RAPE")
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

### Compilar DSSAT para Linux (verificado)

```bash
sudo apt-get install -y gfortran cmake make        # toolchain
cd <raíz del repo dssat-csm-os>
cmake -S . -B build -DCMAKE_INSTALL_PREFIX="$HOME/dssathome"
cmake --build build -j
cmake --install build            # arma $HOME/dssathome con DSSATPRO.L48 + Genotype + .CDE
```

Después se copian los datos (clima/suelo/experimento) y, si corresponde, tus
genotipos calibrados dentro de `$HOME/dssathome/{Weather,Soil,Maize,Genotype}`.
Al correr, pasá `dssat_dir="$HOME/dssathome"`: el runner exporta `DSSAT_HOME`
para que CSM encuentre `DSSATPRO.L48` y los directorios.

> **Nota:** el `.exe` de Windows (PE32+) no corre en Linux sin Wine; en Linux
> conviene el binario nativo ELF que produce la compilación de arriba.

### Detalles agronómicos que la app maneja por vos

- **Acople de `SDATE`** (`couple_start=True`, por defecto): al barrer fecha de
  siembra, baja el inicio de simulación a `min(SDATE original, siembra más
  temprana)` para no disparar el error de CSM *"Planting date is defined prior
  to the start of simulation date"* ni dejar eventos (riego/fertilización)
  antes del inicio.
- **Densidad** (`ppop`): setea `PPOP` **y** `PPOE` juntas, porque CERES usa la
  población *emergida*; variar sólo `PPOP` no cambia el resultado.

## Relocalizar un experimento a otro sitio (ej. Pergamino)

Verificado: tomar un FileX, apuntarlo a otra estación de clima + suelo + tu
cultivar, y correr. El editor maneja el `ID_SOIL` (10 car., más ancho que su
rótulo) sin pisar columnas vecinas.

```python
from dssat_app.filex import FileX
fx = FileX.read("UFGA8201.MZX")
fx.set("FIELDS", "WSTA", "CNPE", level=1, justify="left")        # Pergamino
fx.set("FIELDS", "ID_SOIL", "WI_PLAR020", level=1, justify="left")
fx.set("CULTIVARS", "INGENO", "UAIC10", level=1)                 # DK 682 (FAUBA)
fx.set_all("SIMULATION CONTROLS", "IRRIG", "N")                  # secano
fx.set_all("SIMULATION CONTROLS", "FERTI", "A")                  # N automático
fx.write("PERGbase.MZX")
# luego: Sweep("PERGbase.MZX", crop="maize", ...).add_factor("pdate", [...]).run(...)
```

> Para rinde absoluto realista en tu zona hay que calibrar condiciones
> iniciales (agua/N del suelo) y manejo con datos locales; el flujo y la
> respuesta relativa (fecha de siembra, densidad, N) ya funcionan.

## Estado y hoja de ruta

- [x] Núcleo FileX (leer/editar), batch N/Q/B, parser de salidas, barrido
      factorial, secuencias, CLI y UI. 29 tests en verde (no requieren CSM).
- [x] **Corrida seasonal (N) real verificada** end-to-end con binario nativo
      Linux + `UFGA8201.MZX` (maíz, Gainesville 1982): barridos de fecha de
      siembra y densidad con respuestas agronómicas coherentes.
- [x] **Secuencia (Q) real verificada**: rotación maíz→soja→trigo (MSKB8902,
      Kellogg, 27 años) corriendo con los 3 modelos de cultivo, estado de suelo
      acoplado entre campañas y resumen de rinde por cultivo + carbono del suelo.
- [x] **Relocalización a Pergamino verificada**: clima real `CNPE` (1967–2007)
      + suelo local `WI_PLAR020` + cultivar argentino, con barrido de fecha de
      siembra funcionando.
- [ ] Construir una rotación nueva desde cero (insertar componentes/campañas),
      no solo editar una existente.
- [ ] Autodetección del `DSSATPRO`/`.CTR` y copia automática de clima/suelo.
- [ ] Parseo multi-año (NYERS>1) con mapeo por `RUNNO` y agregados estadísticos.
- [ ] Lectura de más salidas diarias (SoilWat, ET, N) y gráficos comparativos.

## Pruebas

```bash
cd tools/dssat-app
python -m pytest -q
```
