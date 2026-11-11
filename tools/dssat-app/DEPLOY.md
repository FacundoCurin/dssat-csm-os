# Desplegar la app web (sin instalar nada para el usuario)

La app es un servicio web (Streamlit) con DSSAT compilado adentro. El usuario
final entra por el navegador y no instala nada. Acá están las formas de
hostearla, de la más simple a la más robusta.

---

## Opción A — Docker (recomendada)

Una sola imagen trae el modelo compilado, un set de datos de ejemplo y la UI.

```bash
# construir (el contexto es la RAÍZ del repo dssat-csm-os)
docker build -f tools/dssat-app/Dockerfile -t dssat-app .

# correr
docker run --rm -p 8501:8501 dssat-app
```

Abrir **http://localhost:8501**. Para que otros entren por red, corré la
imagen en un servidor y publicá el puerto 8501 (detrás de un reverse proxy
con HTTPS si es público).

### Usar TUS datos (Pergamino, etc.)

Montá tus carpetas de datos sobre las del contenedor:

```bash
docker run --rm -p 8501:8501 \
  -v /ruta/a/mis/Weather:/opt/dssathome/Weather \
  -v /ruta/a/mi/SOIL.SOL:/opt/dssathome/Soil/SOIL.SOL \
  -v /ruta/a/mis/Genotype:/opt/dssathome/Genotype \
  -v /ruta/a/mis/Maize:/opt/dssathome/Maize \
  dssat-app
```

> Recordá preparar el clima con `weather-fill` + `weather-split` (ver
> `INSTALL.md`) y limpiar el `SOIL.SOL` de caracteres corruptos.

---

## Opción B — Servidor de la cátedra / VM en la nube

En cualquier VM Linux (institución, Google Cloud, AWS, etc.):

```bash
git clone https://github.com/FacundoCurin/dssat-csm-os.git
cd dssat-csm-os
docker build -f tools/dssat-app/Dockerfile -t dssat-app .
docker run -d --restart unless-stopped -p 80:8501 dssat-app
```

Queda sirviendo en el puerto 80 de la VM, accesible por su IP/dominio.

---

## Opción C — Hugging Face Spaces (gratis, sin servidor propio)

1. Crear un *Space* nuevo tipo **Docker**.
2. Subir el contenido de `tools/dssat-app/` + el código fuente del modelo
   (o apuntar el Dockerfile a este repo).
3. HF construye la imagen y publica una URL pública automáticamente.

> Nota: el build compila DSSAT (~5–10 min la primera vez). Spaces tiene
> límites de CPU/RAM; alcanza para corridas seasonal y barridos moderados.

---

## Opción D — Streamlit Community Cloud

Sólo sirve la UI de Python; **no compila Fortran**. Serviría si el binario y
los datos se proveen aparte (p. ej. descargándolos en el arranque). Para una
solución todo-en-uno, preferí Docker (A/B/C).

---

## Notas de producción

- **Recursos**: una corrida seasonal es de segundos; un barrido de 40 años ×
  decenas de combinaciones puede tardar minutos. Dimensioná CPU según uso.
- **Concurrencia**: Streamlit maneja una sesión por usuario; para varios
  usuarios simultáneos, corré varias réplicas detrás de un balanceador.
- **Persistencia**: la imagen es efímera; los resultados se descargan como CSV
  desde la UI. Si querés guardar corridas, montá un volumen.
- **Seguridad**: si la exponés a internet, poné HTTPS y, si hace falta,
  autenticación (reverse proxy o el login de HF Spaces).
