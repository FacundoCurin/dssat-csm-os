# Generador de manejos DSSAT — versión R / Shiny

App web para armar manejos (fecha de siembra, densidad, N, cultivar) y correr
DSSAT para **maíz, trigo y soja**, con resultados y gráficos en el navegador.
**Escrita 100% en R** (no necesita Python).

---

## Lo único que necesitás

1. **DSSAT instalado** (por ejemplo `C:\DSSAT48`). Usa tu propia instalación:
   su ejecutable `DSCSM0XX` y tus datos (clima, suelo, genotipos, experimentos).
2. **R** — https://cran.r-project.org (en Windows, el instalador estándar).

La primera vez, la app instala sola el paquete **`shiny`** (único extra).

---

## Cómo arrancarla

### Windows
- Descomprimí la carpeta y **doble clic en `run_shiny.bat`**.
- La primera vez instala `shiny` (tarda un poco) y después abre el navegador.

### Linux / macOS
```bash
cd dssat-app-R
./run_shiny.sh
```

---

## Cómo usarla

1. **Carpeta DSSAT**: la app intenta detectarla (`C:\DSSAT48`, etc.); si no,
   escribí la ruta.
2. Elegí **cultivo** y **experimento** (son los `.MZX/.WHX/.SBX` de tu DSSAT).
3. **Condiciones**: secano, N no limitante, años a simular, humedad inicial.
4. **Manejos a comparar**: tildá qué variar (fecha, densidad, N, cultivar) y
   escribí los niveles separados por coma.
5. **▶ Generar y correr** → tabla, gráfico y descarga de CSV.

---

## Qué hay adentro (para quien programa en R)

| Archivo | Qué es |
|---|---|
| `dssat_engine.R` | Motor en R base: leer/editar FileX (ancho fijo), generar `DSSBatch.v48`, correr CSM, leer `Summary.OUT`. Sin dependencias. |
| `app.R` | La interfaz Shiny (usa el motor). |
| `launch.R` | Instala `shiny` si falta y abre la app. |
| `run_shiny.bat` / `.sh` | Arranque de un clic. |

El motor expone funciones reutilizables desde tus propios scripts:
`fx_read()`, `fx_get()`, `fx_set()`, `fx_set_all()`, `fx_trt_pointer()`,
`write_dssbatch()`, `run_dssat()`, `read_summary()`.

```r
source("dssat_engine.R")
fx <- fx_read("C:/DSSAT48/Maize/UFGA8201.MZX")
fx <- fx_set(fx, "PLANTING DETAILS", "PDATE", "15320", level = 1)
fx_write(fx, "C:/DSSAT48/Maize/MIEXP001.MZX")
write_dssbatch("DSSBatch.v48", "MIEXP001.MZX", trtno = 1)
run_dssat("C:/DSSAT48", "MZCER048", "N", "DSSBatch.v48", work_dir = getwd())
read_summary("Summary.OUT")$HWAM
```

> **Importante**: los FileX deben tener nombre **8.3** (8 caracteres + `.MZX`,
> p. ej. `MIEXP001.MZX`); DSSAT deriva el nombre del experimento de ahí.

---

## Notas

- Alternativa: existe el paquete **`DSSAT`** de R (Alderman) en CRAN, muy
  completo para leer/escribir FileX. Este motor es autocontenido (R base) para
  no depender de nada más que `shiny`, pero podés combinarlos.
- Hay una versión equivalente en Python en `tools/dssat-app/`.
