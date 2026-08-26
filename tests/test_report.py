import io
import time

from blasphemy import report
from blasphemy.pipeline import Result


class FakeTTY(io.StringIO):
    def __init__(self, tty=True):
        super().__init__()
        self._tty = tty

    def isatty(self):
        return self._tty


def result(index=1, status="rewritten", words_in=1000, words_out=700, detail=""):
    return Result(index, f"ch{index}", f"Chapter {index}", status, words_in, words_out, detail)


def test_human_time():
    assert report.human_time(9) == "9s"
    assert report.human_time(75) == "1m15s"
    assert report.human_time(3725) == "1h02m"


def test_ratio_rounds_and_survives_zero():
    assert report.ratio(1000, 700) == "70%"
    assert report.ratio(0, 0) == "0%"


def test_plain_stream_has_no_ansi():
    stream = FakeTTY(tty=False)
    reporter = report.Reporter(3, stream=stream)
    reporter.start("Chapter 1")
    reporter.finish(result())
    reporter.close()
    out = stream.getvalue()
    assert "\x1b[" not in out
    assert "\r" not in out
    assert "[  1/3] rewritten" in out
    assert "1,000w →" in out and "700w" in out and "70%" in out


def test_tty_stream_paints_and_rewrites_status():
    stream = FakeTTY(tty=True)
    reporter = report.Reporter(2, stream=stream, tick=99)
    reporter.start("Chapter 1")
    assert "Chapter 1" in stream.getvalue()
    reporter.finish(result())
    reporter.close()
    out = stream.getvalue()
    assert report.CLEAR_LINE in out
    assert "\x1b[32m" in out  # rewritten is coloured


def test_colour_disabled_by_no_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    reporter = report.Reporter(1, stream=FakeTTY(tty=True))
    assert reporter.colour is False
    assert reporter.paint("x", "failed") == "x"


def test_status_line_reports_position_and_elapsed():
    reporter = report.Reporter(10, stream=FakeTTY(tty=False))
    reporter.results = [result(), result(2)]
    reporter._current = ("Chapter 3", time.monotonic() - 65)
    line = reporter.status_line()
    assert "[2/10]" in line and "Chapter 3" in line and "1m05s" in line


def test_skipped_line_omits_ratio():
    stream = FakeTTY(tty=False)
    reporter = report.Reporter(1, stream=stream)
    reporter.finish(result(status="skipped", words_in=120, words_out=120))
    assert "→" not in stream.getvalue()


def test_summary_totals_only_count_changed_chapters(tmp_path):
    out = tmp_path / "book.epub"
    out.write_bytes(b"x" * 2048)
    reporter = report.Reporter(4, stream=FakeTTY(tty=False))
    for item in (
        result(1, "rewritten", 1000, 700),
        result(2, "cached", 1000, 500),
        result(3, "skipped", 50, 50),
    ):
        reporter.finish(item)
    text = reporter.summary(out, tmp_path / "cache")
    assert "rewritten    1" in text and "cached       1" in text and "skipped      1" in text
    assert "2,000 → 1,200" in text and "60% of original" in text
    assert "2.0 KB" in text
    assert "failed" not in text


def test_summary_lists_failures(tmp_path):
    reporter = report.Reporter(1, stream=FakeTTY(tty=False))
    reporter.finish(result(7, "failed", 900, 0, detail="quota exhausted"))
    text = reporter.summary(tmp_path / "book.epub", tmp_path)
    assert "failed       1" in text
    assert "! [7] Chapter 7 — quota exhausted" in text
    assert "-" in text  # missing output file size


def test_ticker_repaints_until_closed():
    stream = FakeTTY(tty=True)
    reporter = report.Reporter(1, stream=stream, tick=0.01)
    reporter.start("Chapter 1")
    time.sleep(0.05)
    reporter.close()
    assert stream.getvalue().count("Chapter 1") > 1
    assert reporter._ticker is None
