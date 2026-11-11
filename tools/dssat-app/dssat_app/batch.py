"""Generacion del archivo batch de DSSAT (``DSSBatch.v48``).

El formato es de columnas fijas. CSM lo lee en ``CSM_Main/CSM.for`` (lineas
~236-293):

* La seccion arranca con una linea ``$BATCH(<CROP>)`` (la encuentra ``FIND``).
* ``IGNORE`` salta lineas que empiezan con ``!``, ``@`` o estan en blanco, y
  corta con ``*`` o ``$`` (ver ``Utilities/READS.for``).
* Cada linea de datos: columnas 1-92 = ruta+FileX; el nombre del FileX son
  los ultimos 12 caracteres. Columnas 93-113 = ``3(1X,I6)`` -> TRTNO, RP
  (repeticion) y SQ (numero de rotacion, usado en modo Q). OP y CO los
  ignora el lector.

Para evitar problemas de longitud/espacios en la ruta, referenciamos el
FileX por su nombre (12 caracteres) y corremos CSM con el directorio de
trabajo como *cwd* (PATHEX vacio -> CSM lee del directorio actual).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

PathLike = Union[str, Path]

# Ancho de la columna ruta+FileX (CSM usa CHARTEST(1:92)).
_PATH_WIDTH = 92


@dataclass
class BatchEntry:
    """Una corrida dentro del batch."""

    filex: str          # nombre del FileX (p. ej. 'UFGA8201.MZX'), sin ruta
    trtno: int = 1      # numero de tratamiento
    rp: int = 1         # repeticion
    sq: int = 0         # numero de rotacion/secuencia (modo Q)
    op: int = 0         # ignorado por CSM; se escribe por compatibilidad
    co: int = 0         # ignorado por CSM

    def to_line(self) -> str:
        name = self.filex.strip()
        if len(name) > 12:
            # CSM toma los ultimos 12 caracteres como nombre de FileX.
            name = name[-12:]
        # ruta+filex a la izquierda, relleno con espacios hasta la col 92
        left = name.ljust(_PATH_WIDTH)
        # 5 enteros I6 con 1 espacio adelante cada uno (3(1X,I6) + OP + CO)
        nums = f" {self.trtno:6d} {self.rp:6d} {self.sq:6d} {self.op:6d} {self.co:6d}"
        return left + nums


def _header_comment(crop_label: str, model: str, mode: str,
                    batch_name: str) -> List[str]:
    return [
        f"$BATCH({crop_label.upper()})",
        "!",
        f"! Generado por dssat-app",
        f"! Modelo       : {model}",
        f"! Modo (RNMODE): {mode}",
        f"! Batch file   : {batch_name}",
        "!",
        "@FILEX" + " " * 86 + "TRTNO     RP     SQ     OP     CO",
    ]


def build_batch(entries: List[BatchEntry], crop_label: str, model: str,
                mode: str, batch_name: str = "DSSBatch.v48") -> str:
    """Devuelve el contenido del batch como texto."""
    lines = _header_comment(crop_label, model, mode, batch_name)
    lines += [e.to_line() for e in entries]
    return "\n".join(lines) + "\n"


def write_batch(path: PathLike, entries: List[BatchEntry], crop_label: str,
                model: str, mode: str) -> Path:
    """Escribe el batch en ``path`` y lo devuelve."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    content = build_batch(entries, crop_label, model, mode, batch_name=p.name)
    p.write_text(content, encoding="latin-1")
    return p


def seasonal_batch(filex: str, treatments: List[int], model: str,
                   crop_label: str, reps: int = 1) -> List[BatchEntry]:
    """Entradas para una corrida seasonal (modo N): un tratamiento por linea."""
    out: List[BatchEntry] = []
    for t in treatments:
        out.append(BatchEntry(filex=filex, trtno=t, rp=reps, sq=0))
    return out


def sequence_batch(filex: str, treatments: List[int],
                   rotation: int = 1) -> List[BatchEntry]:
    """Entradas para una corrida de secuencia (modo Q).

    En modo Q las lineas representan los cultivos de la rotacion en orden; la
    columna SQ lleva el numero de rotacion (todas comparten el mismo numero
    de rotacion para una unica secuencia).
    """
    out: List[BatchEntry] = []
    for t in treatments:
        out.append(BatchEntry(filex=filex, trtno=t, rp=1, sq=rotation))
    return out
