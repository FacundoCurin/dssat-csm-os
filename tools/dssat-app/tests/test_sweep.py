from pathlib import Path

import pytest

from dssat_app.filex import FileX
from dssat_app.outputs import read_summary
from dssat_app.sweep import Sweep, _join_design_summary

FIXDIR = Path(__file__).parent / "fixtures"
MZX = FIXDIR / "UFGA8201.MZX"
SUMMARY = FIXDIR / "Summary.OUT"


def test_build_generates_variants(tmp_path):
    sw = Sweep(MZX, crop="maize", trtno=1)
    sw.add_factor("pdate", ["82030", "82057", "82084"])
    design = sw.build(tmp_path)
    assert len(design.variant_files) == 3
    for name, combo in zip(design.variant_files, design.combinations):
        fx = FileX.read(tmp_path / name)
        assert fx.get("PLANTING DETAILS", "PDATE", level=1) == str(combo["pdate"])


def test_build_factorial(tmp_path):
    sw = Sweep(MZX, crop="maize", trtno=1)
    sw.add_factor("pdate", ["82030", "82057"])
    sw.add_factor("ppop", ["6", "8.5"])
    design = sw.build(tmp_path)
    assert len(design.variant_files) == 4            # 2 x 2
    fx = FileX.read(tmp_path / design.variant_files[-1])
    assert fx.get("PLANTING DETAILS", "PDATE", level=1) == "82057"
    assert fx.get("PLANTING DETAILS", "PPOP", level=1) == "8.5"


def test_join_design_summary_by_order(tmp_path):
    sw = Sweep(MZX, crop="maize", trtno=1)
    sw.add_factor("pdate", ["82030", "82057", "82084"])
    design = sw.build(tmp_path)
    summ = read_summary(SUMMARY)
    joined = _join_design_summary(design, summ)
    assert len(joined) == 3
    assert "pdate" in joined.columns and "HWAM" in joined.columns
    assert joined["HWAM"].tolist() == [9500, 10200, 8700]


def test_fert_factor_edits_correct_level(tmp_path):
    # el tratamiento 2 usa el nivel 2 de FERTILIZERS (MF=2)
    sw = Sweep(MZX, crop="maize", trtno=2)
    sw.add_factor("famn", ["100", "150"])
    design = sw.build(tmp_path)
    fx = FileX.read(tmp_path / design.variant_files[0])
    assert fx.get("FERTILIZERS", "FAMN", level=2) == "100"
    # el nivel 1 (usado por trt 1) queda intacto
    assert fx.get("FERTILIZERS", "FAMN", level=1) == "0"


def test_unknown_factor_raises(tmp_path):
    sw = Sweep(MZX, crop="maize", trtno=1)
    with pytest.raises(KeyError):
        sw.add_factor("nope", [1, 2])
