import json

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
    assert check.parse_fixes("no json at all") is None
    assert check.parse_fixes("{broken") is None
    assert check.parse_fixes('Braces {like these} first. {"fixes": []} and {after}') == []


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


def test_split_top_skips_a_title_behind_an_anchor():
    # Pandoc (SRE) bodies open with the chapter anchor, then the title
    body = "⟦ANCHOR:ch-3⟧\n\n# Chapter 3\n\nAnswer.\n\n## A\n\na\n\n## B\n\nb\n\n## C\n\nc"
    top, rest = check.split_top(body)
    assert rest.startswith("## C") and "## B" in top


def test_fixes_that_touch_headings_or_tables_are_rejected():
    top = "# 2 Types\n\n| a | b |\n| --- | --- |\n| x | y |\n\nProse claim here."
    _, applied, rejected = check.apply_fixes(top, "src", [
        fix("# 2 Types", "# Types"), fix("| x | y |", "| x | z |"), fix("Prose claim here.", "Line one.\nLine two."),
    ])
    assert not applied
    assert [r["rejected"] for r in rejected] == [
        "sentence is structure, not prose", "sentence is structure, not prose", "replacement changes structure",
    ]


def test_a_fix_that_breaks_the_body_check_is_dropped_alone():
    source = " ".join(["w"] * 100)
    top = "Keep this. Change that."
    good = fix("Keep this.", "Keep this, usually.")
    bad = fix("Change that.", "Change ⟦AN that.")
    patched, applied, rejected = check.apply_fixes(top, source, [good, bad], " ".join(["w"] * 60))
    assert applied == [good] and patched == "Keep this, usually. Change that."
    assert rejected[0]["rejected"] == "breaks the body check"


def test_unparseable_reply_leaves_the_body_and_says_so():
    body, report = check.patch(SOURCE, BODY, lambda text: "Sorry, I cannot do that.")
    assert body == BODY and report["error"] == "unparseable reply"


def test_patch_repeatedly_checks_the_already_fixed_opening_again():
    seen = []
    first = {"fixes": [fix("DNS is too dynamic for the kernel.", "DNS is an application-layer protocol.", "DNS is an application-layer protocol")]}
    second = {"fixes": [fix("Generic code is as fast because of monomorphization.", "Generic code is usually as fast.", "usually as fast")]}
    replies = iter([json.dumps(first), json.dumps(second)])
    def ask(text):
        seen.append(text); return next(replies)
    out, report = check.patch_repeatedly(SOURCE, BODY, ask)
    assert "application-layer protocol." in seen[1] and "usually as fast." in out
    assert [len(p["applied"]) for p in report["passes"]] == [1, 1]


def test_patch_repeatedly_keeps_earlier_fixes_when_a_later_pass_fails():
    first = json.dumps({"fixes": [fix("DNS is too dynamic for the kernel.", "DNS is an application-layer protocol.", "DNS is an application-layer protocol")]})
    replies = iter([first])
    def ask(text):
        try:
            return next(replies)
        except StopIteration:
            raise RuntimeError("quota")
    out, report = check.patch_repeatedly(SOURCE, BODY, ask)
    assert "application-layer protocol." in out
    assert report["passes"][1] == {"error": "quota"}
