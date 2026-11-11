from dssat_app.batch import BatchEntry, build_batch, seasonal_batch, sequence_batch


def test_entry_column_alignment():
    """El FileX debe quedar en los ultimos 12 chars de la col 1-92 y los
    enteros en 3(1X,I6) desde la col 93 (ver CSM_Main/CSM.for)."""
    line = BatchEntry("UFGA8201.MZX", trtno=1, rp=1, sq=0).to_line()
    assert line[:92].rstrip()[-12:] == "UFGA8201.MZX"
    assert line[92] == " "              # col 93 = 1X
    assert line[93:99] == "     1"      # TRTNO en I6 (cols 94-99)
    assert line[100:106] == "     1"    # RP
    assert line[107:113] == "     0"    # SQ


def test_long_name_truncated_to_12():
    line = BatchEntry("UFGA8201extra.MZX", trtno=2).to_line()
    assert line[:92].rstrip()[-12:] == "8201extra.MZX"[-12:]


def test_build_batch_has_header_and_rows():
    entries = seasonal_batch("UFGA8201.MZX", [1, 2, 3], "MZCER048", "Maize")
    txt = build_batch(entries, "Maize", "MZCER048", "N")
    assert txt.startswith("$BATCH(MAIZE)")
    assert "@FILEX" in txt
    # una linea de datos por tratamiento
    data_lines = [l for l in txt.splitlines()
                  if l[:1] not in ("$", "!", "@") and l.strip()]
    assert len(data_lines) == 3


def test_sequence_sets_rotation():
    entries = sequence_batch("ROTN0001.MZX", [1, 2], rotation=1)
    assert all(e.sq == 1 for e in entries)
    line = entries[0].to_line()
    assert line[107:113] == "     1"
