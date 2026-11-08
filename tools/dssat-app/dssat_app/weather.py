"""Utilidades de clima para DSSAT (archivos ``.WTH``).

CSM lee bien campanas que cruzan el 31 de diciembre cuando el clima esta en
*archivos anuales* ``<WSTA><AA>01.WTH`` (uno por anio): avanza solo al archivo
del anio siguiente. En cambio, con una **unica** serie larga multi-anual suele
cortar en fin de anio (error 29 / salidas -99).

Como el maiz/soja pampeano siempre cruza de anio (siembra primavera, cosecha
otonio del anio siguiente), este modulo parte una serie larga en archivos
anuales con el nombre que CSM espera.

Formato de fecha soportado en la columna DATE: ``YYYYDDD`` (7 digitos) o
``YYDDD`` (5 digitos).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Union

PathLike = Union[str, Path]


def _station_from_header(header_lines: List[str]) -> Optional[str]:
    """Extrae el INSI (codigo de estacion) del encabezado @INSI ... """
    for i, ln in enumerate(header_lines):
        if ln.lstrip().upper().startswith("@") and "INSI" in ln.upper():
            # la linea siguiente con datos tiene el INSI como primer token
            for nxt in header_lines[i + 1:]:
                toks = nxt.split()
                if toks:
                    return toks[0]
    return None


def split_multiyear(src: PathLike, out_dir: PathLike,
                    wsta: Optional[str] = None) -> List[Path]:
    """Parte un ``.WTH`` multi-anual en archivos anuales ``<WSTA><AA>01.WTH``.

    - ``src``: archivo de clima con varios anios.
    - ``out_dir``: carpeta de salida (normalmente el Weather/ de DSSAT).
    - ``wsta``: codigo de 4 letras a usar en el nombre; si es None, se toma el
      INSI del encabezado.

    Devuelve la lista de archivos escritos.
    """
    src = Path(src)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    lines = src.read_text(encoding="latin-1").split("\n")
    header: List[str] = []
    date_header: Optional[str] = None
    data: List[str] = []
    for ln in lines:
        s = ln.rstrip("\r")
        stripped = s.lstrip()
        if date_header is None and stripped[:1] == "@":
            toks = stripped[1:].split()
            if toks and toks[0].upper() == "DATE":
                date_header = s
                continue
        if date_header is None:
            header.append(s)
        else:
            if s.strip() and s.lstrip()[0].isdigit():
                data.append(s)

    if date_header is None:
        raise ValueError(f"{src}: no se encontro la linea de encabezado @DATE.")

    station = (wsta or _station_from_header(header) or src.stem[:4]).strip()
    if len(station) != 4:
        station = (station + "XXXX")[:4]

    # agrupar por anio a partir del campo DATE. Puede venir como YYYYDDD (7
    # digitos) o YYDDD (5); algunos archivos pierden los ceros a la izquierda
    # cerca del anio 2000 ("00001"->"1", "01001"->"1001"), asi que se rellena.
    by_year: dict = {}
    for d in data:
        token = d.split()[0]
        if len(token) >= 6:
            t = token.zfill(7)
            year = int(t[:4])
        else:                       # YYDDD (posibles ceros perdidos)
            t = token.zfill(5)
            yy = int(t[:2])
            year = 1900 + yy if yy > 30 else 2000 + yy
        by_year.setdefault(year, []).append(d)

    written: List[Path] = []
    hdr_text = "\n".join(header).rstrip("\n")
    for year, rows in sorted(by_year.items()):
        yy = year % 100
        fn = out_dir / f"{station}{yy:02d}01.WTH"
        with open(fn, "w", encoding="latin-1") as f:
            f.write(hdr_text + "\n" + date_header + "\n" + "\n".join(rows) + "\n")
        written.append(fn)
    return written
