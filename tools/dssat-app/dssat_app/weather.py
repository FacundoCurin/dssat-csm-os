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

import math
import re
from pathlib import Path
from typing import List, Optional, Tuple, Union

PathLike = Union[str, Path]


def _extraterrestrial_radiation(lat_deg: float, doy: int) -> float:
    """Radiacion extraterrestre Ra (MJ/m2/dia) para latitud y dia juliano."""
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi / 365 * doy)
    dec = 0.409 * math.sin(2 * math.pi / 365 * doy - 1.39)
    x = -math.tan(phi) * math.tan(dec)
    x = max(-1.0, min(1.0, x))
    ws = math.acos(x)
    ra = (24 * 60 / math.pi) * 0.0820 * dr * (
        ws * math.sin(phi) * math.sin(dec)
        + math.cos(phi) * math.cos(dec) * math.sin(ws))
    return max(ra, 0.0)


def _parse_latlon_header(header: List[str]) -> Optional[float]:
    """Latitud (grados) de la linea @INSI ... LAT ..."""
    for i, ln in enumerate(header):
        if ln.lstrip().upper().startswith("@") and "LAT" in ln.upper():
            for nxt in header[i + 1:]:
                toks = nxt.split()
                if len(toks) >= 2:
                    try:
                        return float(toks[1])
                    except ValueError:
                        continue
    return None


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


def fill_srad(src: PathLike, out: Optional[PathLike] = None,
              lat: Optional[float] = None, kr: float = 0.16,
              missing: float = -90.0) -> Tuple[Path, int]:
    """Rellena la radiacion solar faltante (SRAD <= -90) estimandola con
    Hargreaves: SRAD = kr * sqrt(Tmax - Tmin) * Ra(lat, dia).

    kr ~ 0.16 (continental) a 0.19 (costero). Devuelve (ruta, nº rellenados).
    Escribe sobre ``out`` (o sobre ``src`` si out es None).
    """
    src = Path(src)
    out = Path(out) if out else src
    lines = src.read_text(encoding="latin-1").split("\n")

    header: List[str] = []
    date_idx = None
    cols: List[str] = []
    out_lines: List[str] = []
    filled = 0
    in_data = False
    for ln in lines:
        s = ln.rstrip("\r")
        stripped = s.lstrip()
        if not in_data and stripped[:1] == "@":
            toks = stripped[1:].split()
            if toks and toks[0].upper() == "DATE":
                cols = ["DATE"] + toks[1:]
                date_idx = 0
                in_data = True
                out_lines.append(s)
                continue
        if not in_data:
            header.append(s)
            out_lines.append(s)
            continue
        if not (s.strip() and s.lstrip()[0].isdigit()):
            out_lines.append(s)
            continue
        parts = s.split()
        try:
            ci_s = cols.index("SRAD"); ci_x = cols.index("TMAX"); ci_n = cols.index("TMIN")
        except ValueError:
            out_lines.append(s); continue
        try:
            srad = float(parts[ci_s])
        except (ValueError, IndexError):
            out_lines.append(s); continue
        if srad <= missing:
            if lat is None:
                lat = _parse_latlon_header(header) or -33.0
            token = parts[date_idx]
            doy = int(token.zfill(5)[-3:]) if len(token) <= 5 else int(token.zfill(7)[-3:])
            try:
                tmax = float(parts[ci_x]); tmin = float(parts[ci_n])
                dt = max(tmax - tmin, 0.0)
                ra = _extraterrestrial_radiation(lat, doy)
                est = round(max(kr * math.sqrt(dt) * ra, 0.5), 1)
                # reemplazar el token SRAD preservando ancho aproximado
                w = len(parts[ci_s])
                parts[ci_s] = f"{est:.1f}".rjust(w)
                out_lines.append(_rejoin(s, parts, cols))
                filled += 1
                continue
            except (ValueError, IndexError):
                pass
        out_lines.append(s)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(out_lines), encoding="latin-1")
    return out, filled


def _rejoin(original: str, parts: List[str], cols: List[str]) -> str:
    """Reescribe la fila de datos con los valores (posiblemente editados),
    en formato de ancho fijo legible por DSSAT."""
    date = parts[0]
    rest = parts[1:]
    out = f"{date:>5}"
    for v in rest:
        out += f" {v:>5}"
    return out
