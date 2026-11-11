"""Ejecucion de DSSAT-CSM (DSCSM0XX) desde Python.

Prepara un directorio de trabajo, escribe/copia los archivos de entrada y
lanza el ejecutable de CSM con la linea de comando estandar::

    DSCSM048  <MODEL>  <MODE>  <batchfile>

p. ej. ``DSCSM048 MZCER048 N DSSBatch.v48`` (ver el encabezado de
``Data/BatchFiles/Maize.v48`` y ``CSM_Main/CSM.for``).

Importante: CSM necesita ademas de un FileX, los archivos de clima (``*.WTH``),
suelo (``*.SOL``) y genotipo (``*.CUL``/``*.ECO``/``*.SPE``), mas un archivo
DSSATPRO/``.CTR`` que indica donde estan esos directorios. Esta clase no
inventa esos archivos: recibe la instalacion de DSSAT y el directorio de
trabajo, y se asegura de correr con el *cwd* correcto. El que arma las
entradas es el modulo ``sweep``/``filex``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

PathLike = Union[str, Path]


@dataclass
class RunResult:
    """Resultado de una corrida de CSM."""

    returncode: int
    cmd: List[str]
    work_dir: Path
    stdout: str = ""
    stderr: str = ""
    error_out: Optional[str] = None     # contenido de ERROR.OUT si existe
    warning_out: Optional[str] = None   # contenido de WARNING.OUT si existe

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def find_executable(dssat_dir: Optional[PathLike] = None,
                    name_hint: str = "DSCSM") -> Optional[Path]:
    """Intenta localizar el ejecutable de CSM.

    Busca en ``dssat_dir`` (si se da), luego en ``$DSSAT_HOME`` y en el PATH.
    Acepta nombres tipo ``DSCSM048``, ``DSCSM048.EXE``, ``dscsm048``.
    """
    candidates: List[Path] = []
    search_dirs: List[Path] = []
    if dssat_dir:
        search_dirs.append(Path(dssat_dir))
    env_home = os.environ.get("DSSAT_HOME")
    if env_home:
        search_dirs.append(Path(env_home))

    for d in search_dirs:
        if not d.exists():
            continue
        for p in d.iterdir():
            if p.is_file() and p.name.upper().startswith(name_hint.upper()):
                if os.access(p, os.X_OK) or p.suffix.upper() == ".EXE":
                    candidates.append(p)
    if candidates:
        # preferir el que no termina en .EXE en Linux, o el primero
        candidates.sort(key=lambda p: (p.suffix.upper() == ".EXE", p.name))
        return candidates[0]

    # PATH
    for cand in ("DSCSM048", "dscsm048", "DSCSM048.EXE"):
        found = shutil.which(cand)
        if found:
            return Path(found)
    return None


@dataclass
class DssatRunner:
    """Orquesta corridas de CSM en un directorio de trabajo."""

    executable: Path
    work_dir: Path
    extra_input_dirs: List[Path] = field(default_factory=list)
    dssat_home: Optional[Path] = None   # se exporta como $DSSAT_HOME al correr

    def __post_init__(self) -> None:
        self.executable = Path(self.executable)
        self.work_dir = Path(self.work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        if self.dssat_home is not None:
            self.dssat_home = Path(self.dssat_home)

    @classmethod
    def locate(cls, work_dir: PathLike,
               dssat_dir: Optional[PathLike] = None) -> "DssatRunner":
        exe = find_executable(dssat_dir)
        if exe is None:
            raise FileNotFoundError(
                "No se encontro el ejecutable de CSM (DSCSM0XX). Pase "
                "'dssat_dir' o defina $DSSAT_HOME, o compile el modelo con "
                "CMake desde la raiz del repo."
            )
        home = Path(dssat_dir) if dssat_dir else None
        return cls(executable=exe, work_dir=Path(work_dir), dssat_home=home)

    def stage_file(self, src: PathLike) -> Path:
        """Copia un archivo de entrada al directorio de trabajo."""
        src = Path(src)
        dst = self.work_dir / src.name
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
        return dst

    def run(self, model: str, mode: str, batch_file: PathLike,
            timeout: Optional[float] = None) -> RunResult:
        """Lanza CSM: ``DSCSM0XX MODEL MODE batch_file`` con cwd=work_dir."""
        batch = Path(batch_file)
        if batch.parent.resolve() != self.work_dir.resolve():
            batch = self.stage_file(batch)
        cmd = [str(self.executable), model, mode, batch.name]
        env = None
        home = self.dssat_home or self.executable.parent
        if home is not None:
            env = dict(os.environ)
            env.setdefault("DSSAT_HOME", str(home))
        proc = subprocess.run(
            cmd, cwd=str(self.work_dir), capture_output=True, text=True,
            timeout=timeout, env=env,
        )
        return RunResult(
            returncode=proc.returncode,
            cmd=cmd,
            work_dir=self.work_dir,
            stdout=proc.stdout,
            stderr=proc.stderr,
            error_out=self._read_optional("ERROR.OUT"),
            warning_out=self._read_optional("WARNING.OUT"),
        )

    def _read_optional(self, name: str) -> Optional[str]:
        p = self.work_dir / name
        if p.exists():
            try:
                return p.read_text(encoding="latin-1")
            except OSError:
                return None
        return None
