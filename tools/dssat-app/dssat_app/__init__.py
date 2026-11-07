"""dssat-app: driver en Python para corridas seasonal/sequence y barridos de
sensibilidad en DSSAT-CSM (maiz, trigo, soja).

Modulos:
  * crops   -- catalogo de cultivos y codigos de modelo/modo.
  * filex   -- lectura/edicion consciente de columnas del FileX.
  * batch   -- generacion del DSSBatch.v48 (byte-exacto para CSM).
  * runner  -- ejecucion del ejecutable DSCSM0XX.
  * outputs -- parseo de Summary.OUT y series diarias (PlantGro.OUT, ...).
  * sweep   -- motor de barrido de parametros (analisis tipo sensibilidad).
"""

from .crops import CROPS, RUN_MODES, SUPPORTED_MODES, Crop, get_crop
from .filex import FACTORS, Factor, FileX
from .batch import BatchEntry, build_batch, write_batch
from .runner import DssatRunner, RunResult, find_executable
from .outputs import read_summary, read_daily, read_out_blocks
from .sweep import Sweep, SweepDesign, SweepResult, SweepFactor
from .sequence import (SequenceExperiment, SequenceResult, RotationComponent,
                       CROP_CODE_ES)
from .weather import split_multiyear

__version__ = "0.1.0"

__all__ = [
    "CROPS", "RUN_MODES", "SUPPORTED_MODES", "Crop", "get_crop",
    "FACTORS", "Factor", "FileX",
    "BatchEntry", "build_batch", "write_batch",
    "DssatRunner", "RunResult", "find_executable",
    "read_summary", "read_daily", "read_out_blocks",
    "Sweep", "SweepDesign", "SweepResult", "SweepFactor",
    "SequenceExperiment", "SequenceResult", "RotationComponent", "CROP_CODE_ES",
    "split_multiyear",
    "__version__",
]
