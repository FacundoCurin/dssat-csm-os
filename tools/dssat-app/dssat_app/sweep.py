"""Motor de barrido de parametros (analisis tipo sensibilidad).

Dado un FileX base, un tratamiento y una lista de factores con sus niveles,
genera el producto cartesiano de combinaciones. Para cada combinacion:

1. Copia el FileX base.
2. Edita, para el nivel que usa el tratamiento elegido, la celda de cada
   factor (p. ej. PDATE en PLANTING DETAILS).
3. Escribe una variante del FileX con nombre unico (8.3 = 12 caracteres).

Luego arma un unico ``DSSBatch.v48`` con una linea por combinacion, corre CSM
en el modo pedido (N seasonal / Q sequence / B batch) y une cada fila del
``Summary.OUT`` con su combinacion (por orden de corrida).

Este es el mismo paradigma que la herramienta de sensibilidad de DSSAT:
partir de un experimento real y perturbarlo de forma controlada.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

import pandas as pd

from . import batch as batch_mod
from . import outputs as out_mod
from .crops import Crop, get_crop
from .filex import FACTORS, Factor, FileX
from .runner import DssatRunner, RunResult

PathLike = Union[str, Path]


@dataclass
class SweepFactor:
    """Un factor a barrer y sus niveles."""

    factor: Factor
    levels: List[Union[str, int, float]]

    @classmethod
    def by_key(cls, key: str, levels: Sequence) -> "SweepFactor":
        if key not in FACTORS:
            raise KeyError(
                f"Factor '{key}' desconocido. Opciones: {', '.join(FACTORS)}"
            )
        return cls(factor=FACTORS[key], levels=list(levels))


@dataclass
class SweepDesign:
    """El diseno experimental resultante (combinaciones + nombres de variante)."""

    combinations: List[Dict[str, Union[str, int, float]]]
    variant_files: List[str]

    def to_frame(self) -> pd.DataFrame:
        df = pd.DataFrame(self.combinations)
        df.insert(0, "variant", self.variant_files)
        df.insert(0, "run", range(1, len(self.combinations) + 1))
        return df


def _variant_name(index: int, ext: str) -> str:
    """Nombre de FileX de 12 caracteres (8.3) para la variante ``index``."""
    stem = f"SWP{index:05d}"          # 8 caracteres
    return f"{stem}.{ext.upper()}"     # SWP00001.MZX


class Sweep:
    """Construye y ejecuta un barrido."""

    def __init__(self, base_filex: PathLike, crop: Union[str, Crop],
                 model: Optional[str] = None, trtno: int = 1):
        self.base_filex = Path(base_filex)
        self.crop: Crop = crop if isinstance(crop, Crop) else get_crop(crop)
        self.model = model or self.crop.default_model
        self.trtno = trtno
        self.base = FileX.read(self.base_filex)
        self.factors: List[SweepFactor] = []

    def add_factor(self, key: str, levels: Sequence) -> "Sweep":
        self.factors.append(SweepFactor.by_key(key, levels))
        return self

    # ----- diseno -------------------------------------------------------
    def build(self, out_dir: PathLike) -> SweepDesign:
        """Genera las variantes de FileX en ``out_dir`` y devuelve el diseno."""
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        level_lists = [f.levels for f in self.factors]
        combos = list(itertools.product(*level_lists)) if level_lists else [()]

        combinations: List[Dict] = []
        variant_files: List[str] = []

        for idx, combo in enumerate(combos, start=1):
            fx = self.base.copy()
            record: Dict[str, Union[str, int, float]] = {}
            for sf, value in zip(self.factors, combo):
                fac = sf.factor
                # nivel que usa el tratamiento para este factor
                lvl = self.base.treatment_pointer(self.trtno, fac.pointer)
                fx.set(fac.section, fac.column, value, level=lvl,
                       justify=fac.justify)
                record[fac.key] = value
            name = _variant_name(idx, self.crop.filex_ext)
            fx.write(out_dir / name)
            combinations.append(record)
            variant_files.append(name)

        return SweepDesign(combinations=combinations, variant_files=variant_files)

    # ----- ejecucion ----------------------------------------------------
    def run(self, out_dir: PathLike, mode: str = "N",
            runner: Optional[DssatRunner] = None,
            dssat_dir: Optional[PathLike] = None,
            extra_inputs: Optional[Sequence[PathLike]] = None,
            timeout: Optional[float] = None) -> "SweepResult":
        """Construye las variantes, arma el batch, corre CSM y une resultados."""
        out_dir = Path(out_dir)
        design = self.build(out_dir)

        if runner is None:
            runner = DssatRunner.locate(out_dir, dssat_dir=dssat_dir)

        # copiar insumos (clima, suelo, etc.) al directorio de trabajo
        for extra in (extra_inputs or []):
            runner.stage_file(extra)

        entries = [
            batch_mod.BatchEntry(filex=v, trtno=self.trtno, rp=1,
                                 sq=(1 if mode == "Q" else 0))
            for v in design.variant_files
        ]
        batch_path = out_dir / "DSSBatch.v48"
        batch_mod.write_batch(batch_path, entries, self.crop.name_es,
                              self.model, mode)

        result = runner.run(self.model, mode, batch_path, timeout=timeout)
        summary = _safe_summary(out_dir / "Summary.OUT")
        joined = _join_design_summary(design, summary)
        return SweepResult(design=design, run=result, summary=summary,
                           table=joined, work_dir=out_dir)


@dataclass
class SweepResult:
    design: SweepDesign
    run: RunResult
    summary: pd.DataFrame
    table: pd.DataFrame            # diseno + variables de salida
    work_dir: Path

    @property
    def ok(self) -> bool:
        return self.run.ok and not self.summary.empty


def _safe_summary(path: Path) -> pd.DataFrame:
    if path.exists():
        return out_mod.read_summary(path)
    return pd.DataFrame()


def _join_design_summary(design: SweepDesign,
                         summary: pd.DataFrame) -> pd.DataFrame:
    """Une el diseno con el Summary.OUT.

    Caso simple (recomendado para barridos): 1 fila de Summary por variante,
    en el mismo orden -> union por posicion. Si no coincide la cantidad de
    filas (p. ej. NYERS>1), devuelve el Summary con una columna 'run' por
    RUNNO si existe, para que el usuario una manualmente.
    """
    design_df = design.to_frame()
    if summary.empty:
        return design_df

    if len(summary) == len(design_df):
        out = pd.concat(
            [design_df.reset_index(drop=True), summary.reset_index(drop=True)],
            axis=1,
        )
        return out

    # fallback: no hay mapeo 1:1 (multi-anio/reps). Adjuntar RUNNO si existe.
    summary = summary.copy()
    if "RUNNO" in summary.columns:
        summary["run"] = summary["RUNNO"]
    return summary
