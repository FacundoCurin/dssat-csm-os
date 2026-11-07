"""Lectura y edicion de archivos de experimento DSSAT (FileX).

El FileX es un archivo de texto organizado en *secciones* (lineas que
empiezan con ``*``). Dentro de cada seccion hay una o mas *tablas*, cada una
con una linea de encabezado que empieza con ``@`` seguida de lineas de datos.
Los valores se alinean por columnas de ancho fijo: el ultimo caracter de cada
dato queda bajo el ultimo caracter del token correspondiente del encabezado.

Este modulo implementa un parser *consciente de columnas* que permite leer y
editar celdas sin romper el alineamiento, que es lo que CSM exige para leer
el archivo correctamente.

Diseno intencional: la edicion es *in situ* (se cambia el valor en la celda
conservando el ancho). Para barridos de sensibilidad generamos una copia del
FileX por combinacion y editamos la celda del nivel que usa el tratamiento
elegido. Asi evitamos cirugia fragil sobre la tabla de tratamientos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

PathLike = Union[str, Path]

# Caracteres que marcan lineas que NO son datos.
_HEADER = "@"
_SECTION = "*"
_COMMENT = "!"
_DOLLAR = "$"


def _is_section(line: str) -> bool:
    return line[:1] == _SECTION


def _is_header(line: str) -> bool:
    return line.lstrip()[:1] == _HEADER


def _is_comment(line: str) -> bool:
    s = line.lstrip()
    return s[:1] in (_COMMENT, _DOLLAR)


def _is_blank(line: str) -> bool:
    return line.strip() == ""


def _column_ends(header: str) -> List[int]:
    """Posiciones (indice 0-based del ultimo caracter) de cada token del header.

    Para ``@P PDATE EDATE`` devuelve el indice de ``P`` (en ``@P``), de la
    ``E`` final de ``PDATE``, etc. Esos indices definen el limite derecho de
    cada columna de datos.
    """
    ends: List[int] = []
    for m in re.finditer(r"\S+", header):
        ends.append(m.end() - 1)
    return ends


def _field_slice(ends: List[int], i: int, line_len: int, last: bool) -> Tuple[int, int]:
    """Rango [start, stop) de la columna ``i`` en una linea de datos."""
    start = 0 if i == 0 else ends[i - 1] + 1
    if last:
        stop = max(line_len, ends[i] + 1)
    else:
        stop = ends[i] + 1
    return start, stop


@dataclass
class Table:
    """Una tabla (encabezado + datos) dentro de una seccion del FileX."""

    header_line_idx: int      # indice de la linea de encabezado en FileX.lines
    data_line_idxs: List[int] # indices de lineas de datos
    columns: List[str]        # nombres de columnas (sin el '@' inicial)
    _ends: List[int]          # posiciones finales de columnas

    def col_index(self, col: str) -> int:
        target = col.strip().upper().rstrip(".")
        for i, c in enumerate(self.columns):
            if c.upper().rstrip(".") == target:
                return i
        raise KeyError(
            f"Columna '{col}' no encontrada. Columnas: {', '.join(self.columns)}"
        )


class FileX:
    """Representa un FileX en memoria como lista de lineas + indice de tablas."""

    def __init__(self, lines: List[str], path: Optional[Path] = None):
        self.lines: List[str] = lines
        self.path: Optional[Path] = path
        # mapa: nombre de seccion (mayusculas, sin '*') -> lista de Table
        self.sections: Dict[str, List[Table]] = {}
        self._index()

    # ----- construccion -------------------------------------------------
    @classmethod
    def read(cls, path: PathLike) -> "FileX":
        p = Path(path)
        text = p.read_text(encoding="latin-1")
        lines = text.split("\n")
        # quitar un posible salto final espurio conservando contenido
        if lines and lines[-1] == "":
            lines = lines[:-1]
        return cls(lines, path=p)

    @classmethod
    def from_string(cls, text: str) -> "FileX":
        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        return cls(lines)

    def _index(self) -> None:
        self.sections = {}
        current_section: Optional[str] = None
        i = 0
        n = len(self.lines)
        while i < n:
            line = self.lines[i]
            if _is_section(line):
                current_section = line[1:].strip().upper()
                self.sections.setdefault(current_section, [])
                i += 1
                continue
            if _is_header(line) and current_section is not None:
                ends = _column_ends(line)
                # el primer token suele ser "@X" -> nombre de columna sin '@'
                cols = line.split()
                cols = [cols[0].lstrip(_HEADER)] + cols[1:]
                data_idxs: List[int] = []
                j = i + 1
                while j < n:
                    l2 = self.lines[j]
                    if _is_section(l2) or _is_header(l2):
                        break
                    if _is_blank(l2) or _is_comment(l2):
                        j += 1
                        continue
                    data_idxs.append(j)
                    j += 1
                self.sections[current_section].append(
                    Table(header_line_idx=i, data_line_idxs=data_idxs,
                          columns=cols, _ends=ends)
                )
                i = j
                continue
            i += 1

    # ----- utilidades de seccion/tabla ----------------------------------
    def _resolve_section(self, section: str) -> str:
        """Encuentra el nombre real de la seccion.

        Las secciones del FileX pueden traer sufijos ('FERTILIZERS
        (INORGANIC)', 'TREATMENTS   ----FACTOR LEVELS----'). Se acepta una
        consulta por nombre canonico y se busca por coincidencia exacta o por
        prefijo.
        """
        sec = section.strip().upper()
        if sec in self.sections:
            return sec
        for name in self.sections:
            if name.startswith(sec):
                return name
        raise KeyError(f"Seccion '{section}' no encontrada en el FileX.")

    def table(self, section: str, table_index: int = 0) -> Table:
        sec = self._resolve_section(section)
        if not self.sections[sec]:
            raise KeyError(f"Seccion '{section}' sin tablas en el FileX.")
        tables = self.sections[sec]
        if table_index >= len(tables):
            raise IndexError(
                f"La seccion '{section}' tiene {len(tables)} tabla(s); "
                f"se pidio indice {table_index}."
            )
        return tables[table_index]

    def section_names(self) -> List[str]:
        return list(self.sections.keys())

    def _row_index_for_level(self, tbl: Table, level: int) -> int:
        """Devuelve el indice (en tbl.data_line_idxs) de la fila cuyo nivel
        (primera columna) == level."""
        for pos, li in enumerate(tbl.data_line_idxs):
            first = self.lines[li][: tbl._ends[0] + 1].strip()
            try:
                if int(first) == int(level):
                    return pos
            except ValueError:
                continue
        raise KeyError(
            f"No existe el nivel {level} en la tabla (seccion). "
            f"Niveles disponibles: {self.levels_in(tbl)}"
        )

    def levels_in(self, tbl: Table) -> List[int]:
        out: List[int] = []
        for li in tbl.data_line_idxs:
            first = self.lines[li][: tbl._ends[0] + 1].strip()
            try:
                out.append(int(first))
            except ValueError:
                pass
        return out

    # ----- lectura ------------------------------------------------------
    def get(self, section: str, col: str, level: Optional[int] = None,
            row: int = 0, table_index: int = 0) -> str:
        """Lee una celda. Si ``level`` se da, busca la fila por nivel;
        si no, usa el indice ``row`` (0-based) dentro de la tabla."""
        tbl = self.table(section, table_index)
        if not tbl.data_line_idxs:
            raise KeyError(f"La seccion '{section}' no tiene filas de datos.")
        pos = self._row_index_for_level(tbl, level) if level is not None else row
        li = tbl.data_line_idxs[pos]
        line = self.lines[li]
        ci = tbl.col_index(col)
        last = ci == len(tbl.columns) - 1
        start, stop = _field_slice(tbl._ends, ci, len(line), last)
        return line[start:stop].strip()

    def rows(self, section: str, table_index: int = 0) -> List[Dict[str, str]]:
        """Devuelve la tabla como lista de dicts {columna: valor}."""
        tbl = self.table(section, table_index)
        out: List[Dict[str, str]] = []
        for li in tbl.data_line_idxs:
            line = self.lines[li]
            d: Dict[str, str] = {}
            for ci, col in enumerate(tbl.columns):
                last = ci == len(tbl.columns) - 1
                start, stop = _field_slice(tbl._ends, ci, len(line), last)
                d[col] = line[start:stop].strip()
            out.append(d)
        return out

    # ----- edicion ------------------------------------------------------
    def set(self, section: str, col: str, value: Union[str, int, float],
            level: Optional[int] = None, row: int = 0, table_index: int = 0,
            justify: str = "right") -> "FileX":
        """Edita una celda preservando el ancho de columna.

        ``justify='right'`` (default) para numeros/codigos; ``'left'`` para
        texto. Devuelve self para encadenar.
        """
        tbl = self.table(section, table_index)
        pos = self._row_index_for_level(tbl, level) if level is not None else row
        li = tbl.data_line_idxs[pos]
        line = self.lines[li]
        ci = tbl.col_index(col)
        last = ci == len(tbl.columns) - 1
        start, stop = _field_slice(tbl._ends, ci, len(line), last)
        width = stop - start
        sval = str(value)
        # asegurar longitud de linea
        if len(line) < stop:
            line = line + " " * (stop - len(line))
        if last:
            # columna final: no truncar; dejar valor tal cual (texto largo)
            new_field = sval if justify == "left" else sval.rjust(width)
            new_line = line[:start] + new_field
        else:
            if len(sval) > width:
                raise ValueError(
                    f"El valor '{sval}' ({len(sval)} car.) no entra en la "
                    f"columna '{col}' (ancho {width}) de la seccion "
                    f"'{section}'."
                )
            new_field = sval.ljust(width) if justify == "left" else sval.rjust(width)
            new_line = line[:start] + new_field + line[stop:]
        self.lines[li] = new_line
        return self

    # ----- tratamientos -------------------------------------------------
    def treatment_pointer(self, trtno: int, pointer: str) -> int:
        """Nivel referenciado por un tratamiento para una columna puntero.

        Ej. ``treatment_pointer(1, 'MP')`` devuelve el nivel de PLANTING
        DETAILS que usa el tratamiento 1. Punteros: CU FL SA IC MP MI MF MR
        MC MT ME MH SM.
        """
        val = self.get("TREATMENTS", pointer, level=trtno, table_index=0)
        return int(val)

    def treatments(self) -> List[Dict[str, str]]:
        return self.rows("TREATMENTS")

    # ----- escritura ----------------------------------------------------
    def to_string(self) -> str:
        return "\n".join(self.lines) + "\n"

    def write(self, path: PathLike) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_string(), encoding="latin-1")
        return p

    def copy(self) -> "FileX":
        return FileX(list(self.lines), path=self.path)


# ---------------------------------------------------------------------------
# Registro de factores de barrido: mapea un nombre amistoso a
# (seccion, columna, puntero-de-tratamiento). El puntero indica que columna de
# la tabla TREATMENTS referencia al nivel que hay que editar.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Factor:
    key: str
    section: str
    column: str
    pointer: str
    label_es: str
    justify: str = "right"
    # columnas espejo en la misma seccion/nivel que reciben el mismo valor
    # (p. ej. densidad: PPOP y PPOE deben ir juntas; CERES usa la emergida).
    also_columns: Tuple[str, ...] = ()


FACTORS: Dict[str, Factor] = {
    "pdate": Factor("pdate", "PLANTING DETAILS", "PDATE", "MP",
                    "Fecha de siembra (YYDDD)"),
    "ppop": Factor("ppop", "PLANTING DETAILS", "PPOP", "MP",
                   "Densidad de plantas (pl/m2)", also_columns=("PPOE",)),
    "plrs": Factor("plrs", "PLANTING DETAILS", "PLRS", "MP",
                   "Espaciamiento entre hileras (cm)"),
    "pldp": Factor("pldp", "PLANTING DETAILS", "PLDP", "MP",
                   "Profundidad de siembra (cm)"),
    "ingeno": Factor("ingeno", "CULTIVARS", "INGENO", "CU",
                     "Cultivar (codigo INGENO)"),
    "famn": Factor("famn", "FERTILIZERS", "FAMN", "MF",
                   "N aplicado (kg/ha)", justify="right"),
    "sdate": Factor("sdate", "SIMULATION CONTROLS", "SDATE", "SM",
                    "Fecha de inicio de simulacion (YYDDD)"),
    "nyers": Factor("nyers", "SIMULATION CONTROLS", "NYERS", "SM",
                    "Numero de anios (seasonal/sequence)"),
}
