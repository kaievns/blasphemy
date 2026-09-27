from blasphemy import check

SOURCE = (
    "Generic code is usually as fast, and part of the reason is monomorphization. "
    "DNS is an application-layer protocol."
)
BODY = (
    "# 2 Types\n\nGeneric code is as fast because of monomorphization. "
    "DNS is too dynamic for the kernel.\n\n"
    "## Shape\n\nShape text.\n\n```\n# not a heading\n```\n\n"
    "## Second\n\nMore.\n\n## Third\n\nDepth text."
)


def fix(sentence, replacement, source=""):
    return {"sentence": sentence, "replacement": replacement, "source": source, "problem": "p"}


def test_split_top_keeps_answer_and_two_sections_and_ignores_code():
    top, rest = check.split_top(BODY)
    assert top.endswith("More.\n") and rest.startswith("## Third")
    assert check.split_top("# T\n\nonly an answer") == ("# T\n\nonly an answer", "")


def test_parse_fixes_tolerates_chatter_and_drops_malformed_entries():
    reply = 'Here:\n```json\n{"fixes": [{"sentence": "A.", "replacement": "B."}, {"sentence": 3}]}\n```'
    assert check.parse_fixes(reply) == [{"sentence": "A.", "replacement": "B."}]
    assert check.parse_fixes("no json at all") == []
    assert check.parse_fixes("{broken") == []


def test_apply_fixes_restores_the_hedge():
    top, _ = check.split_top(BODY)
    patched, applied, rejected = check.apply_fixes(top, SOURCE, [fix(
        "Generic code is as fast because of monomorphization.",
        "Generic code is usually as fast, and part of the reason is monomorphization.",
        "part of the reason is monomorphization",
    )])
    assert "usually as fast" in patched and len(applied) == 1 and not rejected


def test_apply_fixes_rejects_invented_evidence_and_missing_sentences():
    top, _ = check.split_top(BODY)
    _, applied, rejected = check.apply_fixes(top, SOURCE, [
        fix("DNS is too dynamic for the kernel.", "DNS is fine.", "a quote the original never had"),
        fix("A sentence the rewrite does not contain.", "x"),
    ])
    assert not applied
    assert [r["rejected"] for r in rejected] == [
        "quoted evidence is not in the original",
        "sentence not found once in the opening",
    ]


def test_apply_fixes_can_delete_an_unsupported_sentence():
    top, _ = check.split_top(BODY)
    patched, applied, _ = check.apply_fixes(top, SOURCE, [fix("DNS is too dynamic for the kernel.", "")])
    assert "too dynamic" not in patched and applied


def test_apply_fixes_never_drops_a_token():
    top = "Answer ⟦ANCHOR:a⟧ holds."
    _, applied, rejected = check.apply_fixes(top, "src", [fix("Answer ⟦ANCHOR:a⟧ holds.", "Answer holds.")])
    assert not applied and rejected[0]["rejected"] == "replacement drops a ⟦token⟧"


def test_patch_reassembles_the_body():
    reply = (
        '{"fixes": [{"sentence": "DNS is too dynamic for the kernel.", '
        '"source": "DNS is an application-layer protocol", '
        '"replacement": "DNS is an application-layer protocol."}]}'
    )
    patched, report = check.patch(SOURCE, BODY, lambda text: reply)
    assert "DNS is an application-layer protocol." in patched
    assert patched.endswith("Depth text.") and len(report["applied"]) == 1
