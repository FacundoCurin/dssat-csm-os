from pathlib import Path

from dssat_app.outputs import read_summary, read_out_blocks

FIX = Path(__file__).parent / "fixtures" / "Summary.OUT"


def test_summary_columns():
    df = read_summary(FIX)
    assert "" not in df.columns          # sin columna fantasma por el '@'
    for c in ("RUNNO", "CR", "HWAM", "NICM"):
        assert c in df.columns


def test_summary_values_and_types():
    df = read_summary(FIX)
    assert len(df) == 3
    assert df["HWAM"].tolist() == [9500, 10200, 8700]
    assert df["NICM"].tolist() == [0, 200, 0]
    assert df["CR"].tolist() == ["MZ", "MZ", "MZ"]
    assert str(df["HWAM"].dtype).startswith("int")


def test_blocks_count():
    blocks = read_out_blocks(FIX)
    assert len(blocks) == 1
