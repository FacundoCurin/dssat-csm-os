from pathlib import Path

from dssat_app.weather import split_multiyear

FIX = Path(__file__).parent / "fixtures" / "MULTIYR.WTH"


def test_split_creates_yearly_files(tmp_path):
    files = split_multiyear(FIX, tmp_path, wsta="TEST")
    names = sorted(p.name for p in files)
    assert names == ["TEST1001.WTH", "TEST1101.WTH", "TEST1201.WTH"]


def test_split_preserves_header_and_rows(tmp_path):
    files = split_multiyear(FIX, tmp_path, wsta="TEST")
    f2010 = tmp_path / "TEST1001.WTH"
    text = f2010.read_text(encoding="latin-1")
    assert "DATE" in text and text.lstrip()[:1] == "$"  # header @DATE conservado
    assert "INSI" in text                 # encabezado conservado
    # dos filas de 2010, ninguna de otros anios
    data = [l for l in text.splitlines() if l[:4] == "2010"]
    assert len(data) == 2
    assert not any(l[:4] in ("2011", "2012") for l in text.splitlines()
                   if l[:1].isdigit())


def test_station_inferred_from_header(tmp_path):
    files = split_multiyear(FIX, tmp_path)   # sin wsta -> INSI del encabezado
    assert all(p.name.startswith("TEST") for p in files)
