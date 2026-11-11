# Ejemplos de resultados — Pampa Argentina

Salidas generadas con **dssat-app** sobre clima y suelo reales de sitios de la
Pampa, maíz calibrado FAUBA/Balcarce y modelos CERES/CROPGRO. Todas son
corridas de **rinde alcanzable en secano** (N no limitante en maíz/trigo; la
soja fija N), perfil inicial ≈ capacidad de campo. Son *demostraciones del
flujo*, no resultados calibrados para publicar (ver advertencias al final).

Los archivos (`.png` y `.csv`) están en [`examples/`](examples/).

---

## 1. Barrido fecha de siembra × densidad — Pergamino (40 campañas)

![Fecha x densidad](examples/pergamino_fecha_densidad.png)

Análisis tipo sensibilidad: el rinde medio sube hacia siembras tardías
(mediados de nov–dic) y mayor densidad (9–10 pl/m²), con óptimo medio ~10.9
t/ha. Datos: [`examples/pergamino_fecha_densidad.csv`](examples/pergamino_fecha_densidad.csv).

## 2. Respuesta al nitrógeno — Pergamino (40 campañas)

![Respuesta N](examples/pergamino_respuesta_N.png)

Curva clásica con rendimientos decrecientes y meseta ~9 t/ha a 160–200 kg N/ha
aplicados a la siembra. Datos: [`examples/pergamino_respuesta_N.csv`](examples/pergamino_respuesta_N.csv).

## 3. Tres cultivos — Pergamino (~40 campañas)

![Tres cultivos](examples/pergamino_3cultivos.png)

| Cultivo | Media (t/ha) | CV |
|---|---|---|
| Maíz | 12.1 | 30 % |
| Trigo | 7.7 | 16 % |
| Soja (MG IV) | 3.1 | 32 % |

Trigo el más estable (invierno), maíz el de mayor techo.

## 4. Comparación entre sitios — maíz (40 campañas)

![Sitios](examples/comparacion_sitios.png)

Boxplot del rinde de maíz por ambiente. Datos:
[`examples/comparacion_sitios.csv`](examples/comparacion_sitios.csv).

## 5. Matriz cultivo × ambiente (1985–2017)

![Matriz](examples/matriz_cultivo_sitio.png)

Rinde alcanzable secano (t/ha):

|        | Pergamino | M. Juárez | Junín | Rafaela | Anguil | Tres Arroyos |
|--------|-----------|-----------|-------|---------|--------|--------------|
| Maíz   | 12.8      | 12.7      | 13.6  | 11.9    | 9.0    | 7.2          |
| Trigo  | 7.8       | 8.4       | 8.9   | 8.6     | 8.5    | 6.9          |
| Soja   | 3.3       | 2.9       | 3.1   | 2.5     | 2.1    | 1.4          |

Gradiente geográfico claro: la Pampa húmeda del centro-norte rinde más; cae
hacia el oeste semiárido (Anguil) y el sur (Tres Arroyos).

---

## Advertencias de interpretación

- **Rinde alcanzable** (sin limitación de N en maíz/trigo). Los valores
  absolutos dependen de dos supuestos del experimento base que conviene
  reemplazar con datos locales: el **N inicial del suelo** y el **agua inicial
  del perfil** (se usó ≈ capacidad de campo).
- **Cultivares**: maíz DK 682 (calibración FAUBA); soja MG IV y trigo Newton
  son genéricos de DSSAT (no calibrados para Argentina).
- **Suelos proxy**: M. Juárez y Junín usan el Argiudol de Pergamino por no
  tener perfil propio disponible.
- **Calidad de datos detectada**: algunas series tenían radiación faltante
  (rellenada por Hargreaves, ver `weather-fill`) y perfiles de suelo con
  caracteres corruptos (`U+FFFD`) que CSM rechaza hasta limpiarlos.
