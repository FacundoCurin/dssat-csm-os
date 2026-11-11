"""Catalogo de cultivos y modelos de DSSAT-CSM relevantes para la app.

La app se enfoca (por pedido) en maiz, trigo y soja, pero la tabla es
extensible. Los codigos de modelo (``MODEL``) son los que CSM espera como
primer argumento de linea de comando, p. ej.::

    DSCSM048.EXE MZCER048 B DSSBatch.v48

Referencias: ``CSM_Main/CSM.for`` (manejo de RNMODE y MODEL) y los
``Data/BatchFiles/*.v48`` del repositorio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class Crop:
    """Metadatos minimos de un cultivo soportado."""

    key: str                 # identificador interno (ej. "maize")
    name_es: str             # nombre en espanol
    filex_ext: str           # extension del FileX (ej. "MZX")
    crop_code: str           # codigo de 2 letras usado en FileX (*CULTIVARS CR, ej. "MZ")
    models: List[str]        # codigos de modelo CSM disponibles; el primero es el default
    default_version: str = "048"

    @property
    def default_model(self) -> str:
        return self.models[0]


# Version de DSSAT a la que apunta este repo (DSCSM048 / v4.8).
DSSAT_VERSION = "048"


CROPS: Dict[str, Crop] = {
    "maize": Crop(
        key="maize",
        name_es="Maiz",
        filex_ext="MZX",
        crop_code="MZ",
        # CERES-Maize (MZCER) e IXIM (MZIXM) estan ambos en el repo (Plant/).
        models=["MZCER048", "MZIXM048"],
    ),
    "wheat": Crop(
        key="wheat",
        name_es="Trigo",
        filex_ext="WHX",
        crop_code="WH",
        # CERES-Wheat (WHCER), CROPSIM-Wheat (WHCRP), Nwheat (WHAPS).
        models=["WHCER048", "WHCRP048", "WHAPS048"],
    ),
    "soybean": Crop(
        key="soybean",
        name_es="Soja",
        filex_ext="SBX",
        crop_code="SB",
        # CROPGRO-Soybean.
        models=["CRGRO048"],
    ),
}


# Codigos de modo de corrida de CSM (primer/segundo GETARG en CSM.for).
# Ver CSM_Main/CSM.for ~linea 155-175.
RUN_MODES: Dict[str, str] = {
    "A": "Correr todos los tratamientos del FileX",
    "B": "Batch: FileX + tratamientos definidos en DSSBatch.v48",
    "N": "Seasonal: analisis estacional (usa batch file)",
    "Q": "Sequence: analisis de secuencia/rotacion (usa batch file)",
    "S": "Spatial",
    "E": "Sensibilidad (sensitivity)",
    "D": "Debug (lee FILEIO)",
    "I": "Interactivo",
}

# Modos que soporta esta app de forma primaria.
SUPPORTED_MODES: List[str] = ["N", "Q", "B"]


def get_crop(key: str) -> Crop:
    k = key.strip().lower()
    if k not in CROPS:
        raise KeyError(
            f"Cultivo '{key}' no soportado. Opciones: {', '.join(CROPS)}"
        )
    return CROPS[k]


def crop_by_filex_ext(ext: str) -> Crop:
    """Devuelve el cultivo a partir de la extension del FileX (ej. 'MZX')."""
    e = ext.strip().upper().lstrip(".")
    for crop in CROPS.values():
        if crop.filex_ext == e:
            return crop
    raise KeyError(f"Extension de FileX '{ext}' no reconocida.")
