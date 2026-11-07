import os
from pathlib import Path

import pytest

from dssat_app.filex import FileX

FIX = Path(__file__).parent / "fixtures" / "UFGA8201.MZX"


@pytest.fixture
def fx():
    return FileX.read(FIX)


def test_sections_indexed(fx):
    names = fx.section_names()
    assert any(n.startswith("TREATMENTS") for n in names)
    assert any(n.startswith("FERTILIZERS") for n in names)
    assert "SIMULATION CONTROLS" in names


def test_get_planting(fx):
    assert fx.get("PLANTING DETAILS", "PDATE", level=1) == "82057"
    assert fx.get("PLANTING DETAILS", "PPOP", level=1) == "7.2"
    assert fx.get("PLANTING DETAILS", "PLRS", level=1) == "76"


def test_get_cultivar_and_fert(fx):
    assert fx.get("CULTIVARS", "INGENO", level=1) == "IB0035"
    assert fx.get("CULTIVARS", "CR", level=1) == "MZ"
    assert fx.get("FERTILIZERS", "FAMN", level=1) == "0"
    assert fx.get("FERTILIZERS", "FAMN", level=2) == "200"


def test_simulation_controls(fx):
    assert fx.get("SIMULATION CONTROLS", "NYERS", level=1) == "1"
    assert fx.get("SIMULATION CONTROLS", "SDATE", level=1) == "82057"


def test_treatment_pointers(fx):
    assert fx.treatment_pointer(1, "MP") == 1
    assert fx.treatment_pointer(1, "MF") == 1
    assert fx.treatment_pointer(2, "MF") == 2


def test_set_preserves_width_and_neighbors(fx):
    li = fx.table("PLANTING DETAILS").data_line_idxs[0]
    before_len = len(fx.lines[li])
    fx.set("PLANTING DETAILS", "PDATE", "82084", level=1)
    fx.set("PLANTING DETAILS", "PPOP", "8.5", level=1)
    assert fx.get("PLANTING DETAILS", "PDATE", level=1) == "82084"
    assert fx.get("PLANTING DETAILS", "PPOP", level=1) == "8.5"
    # vecinos intactos
    assert fx.get("PLANTING DETAILS", "EDATE", level=1) == "-99"
    assert fx.get("PLANTING DETAILS", "PPOE", level=1) == "7.2"
    assert len(fx.lines[li]) == before_len


def test_set_rejects_overflow(fx):
    with pytest.raises(ValueError):
        fx.set("PLANTING DETAILS", "PPOP", "1234567", level=1)


def test_roundtrip_string(fx):
    txt = fx.to_string()
    fx2 = FileX.from_string(txt)
    assert fx2.get("CULTIVARS", "INGENO", level=1) == "IB0035"


def test_treatments_table(fx):
    trts = fx.treatments()
    assert len(trts) == 2
    assert trts[0]["N"] == "1"
