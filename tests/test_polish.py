from blasphemy import polish

SOURCE = "# 1 Routing\n\n" + "Routers are computers with two interfaces. Pedantry aside, subnets group hosts. " * 12
BODY = (
    "⟦TITLE-1⟧\n\n"
    + "A router is a computer with two interfaces. Subnets group hosts. " * 10
    + "\n\n## Routers\n\n"
    "A router is a computer with two interfaces. See [the table](t.html#x) and ⟦FIG-1: plot⟧.\n\n"
    "| host | subnet |\n|---|---|\n| a | 10.0.0.0/24 |\n\n"
    "```\n# not a heading\nip route\n```\n"
)
REVISED = BODY.replace(
    "## Routers\n\nA router is a computer with two interfaces. See",
    "## Routers\n\nPedantry aside, see",
)


def test_revision_that_keeps_structure_is_accepted():
    assert polish.revision_problem(SOURCE, BODY, REVISED) == ""


def test_revision_may_not_touch_structure_tokens_or_links():
    cases = {
        "⟦tokens⟧ changed": REVISED.replace("⟦FIG-1: plot⟧", "the plot"),
        "headings changed": REVISED.replace("## Routers", "## Routers Forward Packets"),
        "code changed": REVISED.replace("ip route", "ip r"),
        "tables changed": REVISED.replace("| a |", "| b |"),
        "a link was dropped": REVISED.replace("[the table](t.html#x)", "the table"),
        "banned word": REVISED.replace("Pedantry aside", "At the gate"),
    }
    for reason, revised in cases.items():
        assert polish.revision_problem(SOURCE, BODY, revised) == reason


def test_hash_lines_inside_code_are_not_headings():
    revised = REVISED.replace("# not a heading", "# still not a heading")
    assert polish.revision_problem(SOURCE, BODY, revised) == "code changed"


def test_revision_length_and_body_check_are_enforced():
    sentence = "A router is a computer with two interfaces. Subnets group hosts. "
    short = REVISED.replace(sentence * 10, sentence * 3)
    assert polish.revision_problem(SOURCE, BODY, short).startswith("length")
    assert polish.revision_problem(SOURCE, BODY, "Preamble.\n\n" + REVISED) == "body does not open with the chapter title"


def test_polish_retries_then_keeps_the_body():
    replies = iter(["no title here", REVISED])
    body, report = polish.polish(SOURCE, BODY, lambda text: next(replies))
    assert body == REVISED and report == {"attempts": 2, "rejected": ["body does not open with the chapter title"]}
    body, report = polish.polish(SOURCE, BODY, lambda text: "no title here")
    assert body == BODY and report["kept_body"] and len(report["rejected"]) == polish.ATTEMPTS


def test_request_carries_original_then_rewrite():
    text = polish.request("SRC", "BODY")
    assert text.index("ORIGINAL") < text.index("SRC") < text.index("REWRITE") < text.index("BODY")
