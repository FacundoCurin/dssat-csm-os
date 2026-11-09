# Imagen web autocontenida: compila DSSAT-CSM, instala la app y sirve la UI.
#
# Construir (contexto = raíz del repo dssat-csm-os):
#   docker build -f tools/dssat-app/Dockerfile -t dssat-app .
# Correr:
#   docker run --rm -p 8501:8501 dssat-app
# Luego abrir http://localhost:8501
#
# ---------- etapa 1: compilar el modelo ----------
FROM ubuntu:24.04 AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
        gfortran cmake make git ca-certificates && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY . /src
RUN cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/opt/dssathome && \
    cmake --build build -j"$(nproc)" && \
    cmake --install build
# datos de ejemplo (clima/suelo/experimentos) desde el repo oficial de datos
RUN git clone --depth 1 https://github.com/DSSAT/dssat-csm-data /tmp/data || true && \
    for d in Weather Soil; do \
      mkdir -p /opt/dssathome/$d && cp -n /tmp/data/$d/* /opt/dssathome/$d/ 2>/dev/null || true; \
    done && \
    for c in Maize Wheat Soybean; do \
      mkdir -p /opt/dssathome/$c && cp -n /tmp/data/$c/* /opt/dssathome/$c/ 2>/dev/null || true; \
    done && \
    rm -rf /tmp/data

# ---------- etapa 2: runtime ----------
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgfortran5 && rm -rf /var/lib/apt/lists/*
COPY --from=build /opt/dssathome /opt/dssathome
COPY tools/dssat-app /app
WORKDIR /app
RUN pip install --no-cache-dir -e ".[ui]"
ENV DSSAT_HOME=/opt/dssathome
EXPOSE 8501
CMD ["streamlit", "run", "app/streamlit_app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
