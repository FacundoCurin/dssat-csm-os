"""Lectura de archivos de salida de DSSAT-CSM (``*.OUT``).

Todos los OUT comparten el mismo esquema: una (o varias) tabla(s) con una
linea de encabezado que empieza con ``@`` y filas de datos alineadas por
columnas. ``Summary.OUT`` tiene una sola tabla (una fila por corrida);
``PlantGro.OUT`` y similares tienen un bloque por corrida (series diarias).

Se parsea con el mismo criterio de anchos fijos que el FileX: el ultimo
caracter de cada dato queda bajo el ultimo caracter del token del encabezado.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd

PathLike = Union[str, Path]


def _column_ends(header: str) -> List[int]:
    return [m.end() - 1 for m in re.finditer(r"\S+", header)]


def _split_row(line: str, ends: List[int], ncols: int) -> List[str]:
    out: List[str] = []
    for i in range(ncols):
        start = 0 if i == 0 else ends[i - 1] + 1
        stop = ends[i] + 1 if i < ncols - 1 else max(len(line), ends[i] + 1)
        out.append(line[start:stop].strip())
    return out


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        # usar la version numerica solo si no perdemos todo (columna de texto)
        if converted.notna().any():
            # conservar texto donde no era numero? DSSAT separa texto/numero
            # por columna, asi que si la mayoria es numerica, convertimos.
            if converted.notna().mean() >= 0.5:
                df[col] = converted
    return df


def read_out_blocks(path: PathLike) -> List[pd.DataFrame]:
    """Devuelve una lista de DataFrames, uno por bloque ``@``-delimitado."""
    text = Path(path).read_text(encoding="latin-1")
    lines = text.split("\n")
    blocks: List[pd.DataFrame] = []

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line[:1] == "@":
            header = line
            # tokens con su posicion final; se descarta un '@' suelto (en los
            # .OUT el '@' va separado: '@   RUNNO'; en el FileX va pegado: '@P')
            toks = [(m.group(0), m.end() - 1)
                    for m in re.finditer(r"\S+", header)]
            toks = [(t.lstrip("@"), e) for t, e in toks if t != "@"]
            cols = [t for t, _ in toks]
            ends = [e for _, e in toks]
            ncols = len(cols)
            rows: List[List[str]] = []
            j = i + 1
            while j < n:
                l2 = lines[j]
                if l2.strip() == "":
                    break
                if l2[:1] in ("@", "*"):
                    break
                if l2[:1] == "!":
                    j += 1
                    continue
                rows.append(_split_row(l2, ends, ncols))
                j += 1
            if rows:
                df = pd.DataFrame(rows, columns=_dedupe(cols))
                blocks.append(_coerce_numeric(df))
            i = j
            continue
        i += 1
    return blocks


def _dedupe(cols: List[str]) -> List[str]:
    """Evita nombres de columna repetidos (p. ej. varios 'R#')."""
    seen: dict = {}
    out: List[str] = []
    for c in cols:
        if c in seen:
            seen[c] += 1
            out.append(f"{c}.{seen[c]}")
        else:
            seen[c] = 0
            out.append(c)
    return out


def read_summary(path: PathLike) -> pd.DataFrame:
    """Lee ``Summary.OUT`` como un unico DataFrame (una fila por corrida)."""
    blocks = read_out_blocks(path)
    if not blocks:
        return pd.DataFrame()
    df = pd.concat(blocks, ignore_index=True)
    return df


def read_daily(path: PathLike, block_col: str = "BLOCK") -> pd.DataFrame:
    """Lee un OUT diario (p. ej. ``PlantGro.OUT``) concatenando los bloques,
    agregando una columna ``BLOCK`` (indice de corrida 1-based)."""
    blocks = read_out_blocks(path)
    for k, b in enumerate(blocks, start=1):
        b[block_col] = k
    if not blocks:
        return pd.DataFrame()
    return pd.concat(blocks, ignore_index=True)


# Columnas de interes frecuentes en Summary.OUT (nombre -> descripcion)
SUMMARY_KEY_VARS = {
    "HWAM": "Rendimiento a cosecha (kg/ha)",
    "HWAH": "Rendimiento cosechado (kg/ha)",
    "CWAM": "Biomasa aerea a madurez (kg/ha)",
    "ADAT": "Fecha de antesis (YYDDD)",
    "MDAT": "Fecha de madurez (YYDDD)",
    "PDAT": "Fecha de siembra (YYDDD)",
    "NUCM": "N absorbido (kg/ha)",
    "PRCP": "Precipitacion del ciclo (mm)",
    "ETCP": "Evapotranspiracion del ciclo (mm)",
    "IR#M": "Numero de riegos",
    "IRCM": "Lamina de riego total (mm)",
    "NICM": "N aplicado (kg/ha)",
}
