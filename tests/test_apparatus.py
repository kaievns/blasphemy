from blasphemy import apparatus

RAW = """=== ORIENT ===
This chapter installs the machinery.

=== WATCH FOR ===
- The load-bearing phrase.

=== PAUSES ===
AFTER: ends exactly like this.
PAUSE: Predict what follows.

=== KEY POINTS ===
- Claim one.

=== CHECK YOURSELF ===
1. Why does X imply Y?

=== ANSWERS ===
1. Because Z.
"""

BODY = "\n\n".join(
    ["# Original Title", "Para one.", "Para two.", "Para three.", "Para four ends exactly like this.", "Para five."]
)


def test_sections_parsed():
    assert apparatus.section(RAW, "ORIENT") == "This chapter installs the machinery."
    assert apparatus.section(RAW, "ANSWERS") == "1. Because Z."
    assert apparatus.section(RAW, "MISSING") == ""


def test_assemble_full():
    final = apparatus.assemble("# Src Title\n\nx", BODY, RAW)
    assert final.startswith("# Original Title")
    assert "**Orient.** This chapter installs the machinery." in final
    assert "**Watch for**" in final
    assert "**Pause:** Predict what follows." in final
    assert "## Key points" in final
    assert "## Check yourself" in final
    assert "**Answers**" in final
    assert final.index("**Orient.") < final.index("Para one.")


def test_assemble_title_from_source_when_body_lacks_one():
    body = BODY.replace("# Original Title\n\n", "")
    final = apparatus.assemble("# Src Title\n\nx", body, RAW)
    assert final.startswith("# Src Title")


def test_assemble_empty_apparatus_returns_body():
    final = apparatus.assemble("# Src Title\n\nx", BODY, "no delimiters here")
    assert "Orient" not in final
    assert final.startswith("# Original Title")
    assert "Para five." in final


def test_pause_skipped_when_early_or_before_heading():
    body = "\n\n".join(["P0 ends exactly like this.", "P1.", "P2.", "P3 also ends like that.", "## Head", "P4."])
    pauses = (
        "AFTER: ends exactly like this.\nPAUSE: too early\n"
        "AFTER: also ends like that.\nPAUSE: before heading\n"
    )
    out, inserted, skipped = apparatus.insert_pauses(body, pauses)
    assert inserted == 0
    assert skipped == 2
    assert "**Pause:**" not in out


def test_pause_inserted_at_locator():
    out, inserted, skipped = apparatus.insert_pauses(BODY, apparatus.section(RAW, "PAUSES"))
    assert inserted == 1 and skipped == 0
    assert out.index("ends exactly like this.") < out.index("**Pause:**") < out.index("Para five.")


def test_title_token_recognised_as_chapter_title():
    body = "⟦TITLE-0: 1 Foundations⟧\n\nThe answer paragraph."
    raw = "=== ORIENT ===\nWhat this is.\n\n=== KEY POINTS ===\n- One."
    out = apparatus.assemble("⟦TITLE-0: 1 Foundations⟧\n\nsource", body, raw)
    lines = out.split("\n\n")
    assert lines[0] == "⟦TITLE-0: 1 Foundations⟧"
    assert lines[1].startswith("**Orient.**")
    assert "The answer paragraph." in out


PRODUCTION_RAW = """=== KEY POINTS ===
- Claim one.

=== CHECK YOURSELF ===
1. Why does X imply Y?

=== ANSWERS ===
1. Because Z.
"""


def test_assemble_production_shape_without_orient():
    final = apparatus.assemble("# Src Title\n\nx", BODY, PRODUCTION_RAW)
    assert "Orient" not in final
    order = [final.index(s) for s in ("Para five.", "## Key points", "## Check yourself", "**Answers**")]
    assert order == sorted(order)
    assert "- Claim one." in final and "1. Because Z." in final


def test_sections_tolerate_delimiter_drift():
    raw = "=== Key Points === \r\n- a\r\n\r\n===CHECK YOURSELF===\r\n1. q\r\n"
    assert apparatus.section(raw, "KEY POINTS") == "- a"
    assert apparatus.section(raw, "CHECK YOURSELF") == "1. q"
