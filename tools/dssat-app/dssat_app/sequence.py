"""Soporte de corridas de secuencia (modo Q): rotaciones multi-cultivo.

En una secuencia, un *tratamiento* (columna N de TREATMENTS) esta compuesto
por varios *componentes de rotacion* (columna R: R=1,2,3,...), cada uno una
campana con su cultivo/cultivar/siembra. CSM corre los componentes en orden
arrastrando el estado del suelo (agua, N, residuos, carbono) de una campana a
la siguiente, y cicla por la rotacion hasta cubrir NYERS anios.

Puntos que CSM exige y que este modulo maneja:

* El ``DSSBatch.v48`` debe tener **una linea por componente de rotacion**, con
  ``TRTNO`` = el tratamiento y ``SQ`` = el numero de componente (R). Con una
  sola linea, CSM repite el primer componente todos los anios (monocultivo).
* La salida estandar (``Summary.OUT``) solo se produce con ``SUMRY=Y`` y
  ``FNAME=N`` en SIMULATION CONTROLS; con ``FNAME=Y`` el resumen se renombra a
  ``<EXP>.OSU``. El modulo fuerza ``SUMRY=Y`` y ``FNAME=N``.
* Cada cultivar referenciado debe existir en el archivo de genotipo; si falta,
  CSM aborta con "Error in Cultivar entry".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

import pandas as pd

from . import batch as batch_mod
from . import outputs as out_mod
from .crops import Crop, crop_by_filex_ext, get_crop
from .filex import FileX
from .runner import DssatRunner, RunResult

PathLike = Union[str, Path]

# Mapa codigo de cultivo (columna CR) -> nombre en espanol
CROP_CODE_ES = {
    "MZ": "Maiz", "WH": "Trigo", "SB": "Soja", "FA": "Barbecho",
    "CO": "Algodon", "BN": "Poroto", "RI": "Arroz", "SG": "Sorgo",
    "BA": "Cebada", "SU": "Girasol", "PN": "Mani", "CH": "Garbanzo",
}


@dataclass
class RotationComponent:
    """Un paso de la rotacion (una fila de TREATMENTS del tratamiento)."""

    r: int                 # numero de componente (columna R)
    crop_code: str         # CR del cultivar que usa (via puntero CU)
    cultivar: str          # INGENO
    name: str              # TNAME


class SequenceExperiment:
    """Envuelve un FileX de secuencia (.SQX) y permite correrlo en modo Q."""

    def __init__(self, filex: PathLike, trtno: int = 1):
        self.path = Path(filex)
        self.trtno = trtno
        self.fx = FileX.read(self.path)

    # ----- lectura de la rotacion ---------------------------------------
    def rotation(self) -> List[RotationComponent]:
        """Componentes de rotacion del tratamiento, en orden."""
        comps: List[RotationComponent] = []
        cultivars = {int(c["C"]): c for c in self.fx.rows("CULTIVARS")}
        for t in self.fx.treatments():
            try:
                if int(t["N"]) != self.trtno:
                    continue
                r = int(t["R"])
            except (KeyError, ValueError):
                continue
            cu = int(t.get("CU", "0") or 0)
            crow = cultivars.get(cu, {})
            comps.append(RotationComponent(
                r=r,
                crop_code=crow.get("CR", "?"),
                cultivar=crow.get("INGENO", "?"),
                name=next((v for k, v in t.items()
                           if k.upper().startswith("TNAME")), ""),
            ))
        comps.sort(key=lambda c: c.r)
        return comps

    def crops_used(self) -> List[str]:
        return sorted({c.crop_code for c in self.rotation()})

    # ----- ediciones ----------------------------------------------------
    def force_standard_outputs(self) -> None:
        """Garantiza Summary.OUT con nombre estandar."""
        self.fx.set_all("SIMULATION CONTROLS", "SUMRY", "Y")
        self.fx.set_all("SIMULATION CONTROLS", "FNAME", "N")

    def set_nyers(self, nyers: int) -> None:
        self.fx.set_all("SIMULATION CONTROLS", "NYERS", int(nyers))

    def set_cultivar(self, cu_level: int, ingeno: str) -> None:
        self.fx.set("CULTIVARS", "INGENO", ingeno, level=cu_level)

    # ----- ejecucion ----------------------------------------------------
    def build_batch_entries(self) -> List[batch_mod.BatchEntry]:
        """Una linea por componente de rotacion (clave para que avance)."""
        name = self.path.name
        return [
            batch_mod.BatchEntry(filex=name, trtno=self.trtno, rp=1, sq=c.r)
            for c in self.rotation()
        ]

    def run(self, out_dir: PathLike, model: Optional[str] = None,
            dssat_dir: Optional[PathLike] = None,
            nyers: Optional[int] = None,
            timeout: Optional[float] = None) -> "SequenceResult":
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        self.force_standard_outputs()
        if nyers is not None:
            self.set_nyers(nyers)

        # escribir el .SQX (posiblemente editado) en el dir de trabajo
        sqx_path = out_dir / self.path.name
        self.fx.write(sqx_path)

        # modelo por defecto segun el 1er cultivo de la rotacion
        if model is None:
            crop = crop_by_filex_ext(self.path.suffix)
            model = crop.default_model

        entries = self.build_batch_entries()
        batch_path = out_dir / "DSSBatch.v48"
        batch_mod.write_batch(batch_path, entries, "SEQUENCE", model, "Q")

        runner = DssatRunner.locate(out_dir, dssat_dir=dssat_dir)
        result = runner.run(model, "Q", batch_path, timeout=timeout)

        summary = pd.DataFrame()
        spath = out_dir / "Summary.OUT"
        if spath.exists():
            summary = out_mod.read_summary(spath)
            summary = _tag_crops(summary)
        return SequenceResult(experiment=self, run=result, summary=summary,
                              work_dir=out_dir)


def _tag_crops(summary: pd.DataFrame) -> pd.DataFrame:
    if "CR" in summary.columns:
        summary = summary.copy()
        summary.insert(summary.columns.get_loc("CR") + 1, "cultivo",
                       summary["CR"].map(CROP_CODE_ES).fillna(summary["CR"]))
    return summary


@dataclass
class SequenceResult:
    experiment: SequenceExperiment
    run: RunResult
    summary: pd.DataFrame
    work_dir: Path

    @property
    def ok(self) -> bool:
        return self.run.ok and not self.summary.empty

    def yield_by_crop(self, var: str = "HWAM") -> pd.DataFrame:
        """Rinde medio por cultivo a lo largo de la rotacion."""
        if self.summary.empty or "cultivo" not in self.summary.columns:
            return pd.DataFrame()
        df = self.summary[self.summary["CR"] != "FA"]
        return (df.groupby("cultivo")[var]
                .agg(["count", "mean", "min", "max"]).round(0))

    def soil_carbon_change(self, var: str = "OCTAM") -> Optional[float]:
        """Cambio de carbono organico del suelo entre inicio y fin (kg/ha)."""
        if self.summary.empty or var not in self.summary.columns:
            return None
        return float(self.summary[var].iloc[-1] - self.summary[var].iloc[0])
