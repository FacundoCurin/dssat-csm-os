# Generador de manejos DSSAT — Guía de uso

App web para armar manejos (fecha de siembra, densidad, nitrógeno, cultivar,
riego) y correr DSSAT para **maíz, trigo y soja**, con resultados y gráficos en
el navegador.

---

## Lo único que necesitás

1. **DSSAT instalado** (por ejemplo `C:\DSSAT48` en Windows). La app usa tu
   propia instalación: su ejecutable `DSCSM0XX` y tus datos (clima, suelo,
   genotipos, experimentos).
2. **Python 3.9 o superior** — https://www.python.org/downloads/
   (en Windows, al instalar marcá **“Add Python to PATH”**).

No hace falta compilar nada ni saber programar.

---

## Cómo arrancarla

### Windows
1. Descomprimí la carpeta `dssat-app` en cualquier lugar (p. ej. el Escritorio).
2. **Doble clic en `run.bat`**.
3. La primera vez tarda un par de minutos (instala lo que necesita). Después se
   abre sola en el navegador: **http://localhost:8501**

### Linux / macOS
```bash
cd dssat-app
./run.sh
```

> Si Windows muestra un aviso de seguridad (“Windows protegió tu PC”), hacé
> clic en **“Más información” → “Ejecutar de todas formas”**: el archivo es un
> script de texto, podés abrirlo con el Bloc de notas para verlo.

---

## Cómo usarla

1. **Barra lateral → Carpeta DSSAT**: la app intenta detectar tu instalación
   (p. ej. `C:\DSSAT48`). Si no la encuentra, escribí la ruta a mano.
2. **Cultivo y experimento**: elegí maíz/trigo/soja y un experimento de la
   lista (son los `.MZX/.WHX/.SBX` de tu DSSAT). También podés subir tu propio
   FileX.
3. **Condiciones**: secano o riego, N no limitante, cuántos años simular
   (variabilidad climática), humedad inicial del suelo.
4. **Manejos a comparar**: marcá qué variar (fecha, densidad, N, cultivar…) y
   escribí los niveles separados por coma. La app te dice cuántas corridas
   genera.
5. **▶ Generar y correr**: obtenés una tabla de resultados, un gráfico de
   respuesta y un botón para **descargar el CSV**.

---

## Problemas frecuentes

| Síntoma | Solución |
|---|---|
| “No encuentro el ejecutable de DSSAT” | Corregí la ruta de la carpeta DSSAT en la barra lateral (donde está `DSCSM048.EXE`). |
| La lista de experimentos está vacía | Esa carpeta no tiene `Maize/`, `Wheat/` o `Soybean/` con experimentos. Usá tu carpeta de DSSAT o subí un FileX. |
| Error de suelo / cultivar | El experimento referencia un suelo o cultivar que no está en tu DSSAT. Elegí otro, o agregalo a tu instalación. |
| “Falta Python” | Instalá Python 3.9+ y, en Windows, marcá “Add Python to PATH”. |

---

## Notas

- Los resultados se **descargan como CSV**; la app no guarda nada por su cuenta.
- Para series climáticas largas (análisis multi-anual) puede hacer falta
  preparar el clima: ver `INSTALL.md` (comandos `weather-fill` y
  `weather-split`).
- Documentación técnica y ejemplos: `README.md`, `EJEMPLOS.md`.
