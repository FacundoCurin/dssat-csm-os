from pathlib import Path

from dssat_app.sequence import SequenceExperiment, CROP_CODE_ES

SQX = Path(__file__).parent / "fixtures" / "ROTN0001.SQX"


def test_rotation_parsed():
    seq = SequenceExperiment(SQX, trtno=1)
    rot = seq.rotation()
    assert len(rot) > 3
    # está ordenada por R
    assert [c.r for c in rot] == sorted(c.r for c in rot)
    # rotación maíz-soja-trigo-barbecho
    assert set(seq.crops_used()) >= {"MZ", "SB", "WH", "FA"}


def test_first_component_is_maize():
    seq = SequenceExperiment(SQX, trtno=1)
    rot = seq.rotation()
    assert rot[0].crop_code == "MZ"


def test_batch_one_line_per_component():
    seq = SequenceExperiment(SQX, trtno=1)
    entries = seq.build_batch_entries()
    rot = seq.rotation()
    assert len(entries) == len(rot)
    # SQ (rotación) = R del componente; TRTNO constante
    assert [e.sq for e in entries] == [c.r for c in rot]
    assert all(e.trtno == 1 for e in entries)


def test_force_standard_outputs():
    seq = SequenceExperiment(SQX, trtno=1)
    seq.force_standard_outputs()
    # todas las tablas OUTPUTS deben quedar con SUMRY=Y y FNAME=N
    for ti, tbl in enumerate(seq.fx.sections[
            seq.fx._resolve_section("SIMULATION CONTROLS")]):
        try:
            tbl.col_index("SUMRY")
        except KeyError:
            continue
        for pos in range(len(tbl.data_line_idxs)):
            assert seq.fx.get("SIMULATION CONTROLS", "SUMRY",
                              row=pos, table_index=ti) == "Y"
            assert seq.fx.get("SIMULATION CONTROLS", "FNAME",
                              row=pos, table_index=ti) == "N"


def test_set_cultivar_and_nyers():
    seq = SequenceExperiment(SQX, trtno=1)
    seq.set_cultivar(1, "IB0089")
    assert seq.fx.get("CULTIVARS", "INGENO", level=1) == "IB0089"
    seq.set_nyers(10)
    assert seq.fx.get("SIMULATION CONTROLS", "NYERS", level=1) == "10"


def test_crop_code_map():
    assert CROP_CODE_ES["MZ"] == "Maiz"
    assert CROP_CODE_ES["SB"] == "Soja"
    assert CROP_CODE_ES["WH"] == "Trigo"
