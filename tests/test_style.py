from blasphemy import style


def test_banned_words_absent_from_source_are_reported():
    assert style.banned("plain text", "we delve into the gated provenance") == [
        "gate", "provenance", "delve",
    ]


def test_inflections_and_case_count():
    assert style.banned("", "Gating and Delved") == ["gate", "delve"]


def test_source_keyword_is_allowed():
    src = "the NAND gate and the provenance record"
    assert style.banned(src, "each gate has provenance; we delve") == ["delve"]


def test_substrings_do_not_match():
    assert style.banned("", "delegate navigate provenanced") == []


def test_clean_output():
    assert style.banned("", "nothing to see here") == []
