import os
import shutil
import sys
import threading
import time

CLEAR_LINE = "\r\x1b[2K"
COLOURS = {
    "rewritten": "32",
    "cached": "36",
    "skipped": "90",
    "failed": "31",
    "dim": "90",
    "bold": "1",
}
WORKING = ("rewritten", "cached")


def human_time(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m{seconds % 60:02d}s"
    return f"{seconds // 3600}h{seconds % 3600 // 60:02d}m"


def human_size(path) -> str:
    try:
        size = os.path.getsize(path)
    except OSError:
        return "-"
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def ratio(words_in: int, words_out: int) -> str:
    return f"{round(100 * words_out / max(words_in, 1))}%"


class Reporter:
    """Live progress on a terminal, plain append-only lines when redirected."""

    def __init__(self, total: int, stream=None, colour: bool | None = None, tick=1.0):
        self.total = total
        self.stream = stream or sys.stdout
        self.live = self.stream.isatty()
        self.colour = (
            self.live and not os.environ.get("NO_COLOR") if colour is None else colour
        )
        self.tick = tick
        self.results: list = []
        self.started = time.monotonic()
        self._current: tuple[str, float] | None = None
        self._lock = threading.RLock()
        self._ticker: threading.Thread | None = None
        self._stop = threading.Event()

    def paint(self, text: str, *styles: str) -> str:
        if not self.colour or not styles:
            return text
        codes = ";".join(COLOURS.get(style, style) for style in styles)
        return f"\x1b[{codes}m{text}\x1b[0m"

    def write(self, text: str) -> None:
        with self._lock:
            if self.live:
                self.stream.write(CLEAR_LINE)
            self.stream.write(text + "\n")
            self.stream.flush()
            self._paint_status()

    def note(self, text: str) -> None:
        self.write(self.paint(text, "dim"))

    def status_line(self) -> str:
        if not self._current:
            return ""
        title, since = self._current
        done = len(self.results)
        width = shutil.get_terminal_size((100, 24)).columns
        bar = f"[{done}/{self.total}]"
        elapsed = human_time(time.monotonic() - since)
        line = f"{bar} {title} … {elapsed}"
        return line[: max(width - 1, 20)]

    def _paint_status(self) -> None:
        if self.live and self._current:
            self.stream.write(CLEAR_LINE + self.paint(self.status_line(), "dim"))
            self.stream.flush()

    def start(self, title: str) -> None:
        with self._lock:
            self._current = (title, time.monotonic())
            self._paint_status()
        if self.live and self._ticker is None:
            self._stop.clear()
            self._ticker = threading.Thread(target=self._run_ticker, daemon=True)
            self._ticker.start()

    def _run_ticker(self) -> None:
        while not self._stop.wait(self.tick):
            with self._lock:
                self._paint_status()

    def finish(self, result) -> None:
        with self._lock:
            self.results.append(result)
            self._current = None
        change = (
            f"{result.words_in:>6,}w → {result.words_out:>6,}w  "
            f"{ratio(result.words_in, result.words_out):>4}"
            if result.status in WORKING
            else f"{result.words_in:>6,}w" + " " * 15
        )
        line = (
            f"[{len(self.results):>3}/{self.total}] "
            f"{self.paint(f'{result.status:<9}', result.status)} "
            f"{change}  {result.title or result.item_id}"
        )
        if result.detail:
            line += self.paint(f"  ({result.detail})", "dim")
        self.write(line)

    def close(self) -> None:
        self._stop.set()
        if self._ticker:
            self._ticker.join(timeout=self.tick * 2)
            self._ticker = None
        with self._lock:
            self._current = None
            if self.live:
                self.stream.write(CLEAR_LINE)
                self.stream.flush()

    def summary(self, out_path, workdir) -> str:
        counts: dict[str, int] = {}
        for result in self.results:
            counts[result.status] = counts.get(result.status, 0) + 1
        changed = [r for r in self.results if r.status in WORKING]
        words_in = sum(r.words_in for r in changed)
        words_out = sum(r.words_out for r in changed)

        rule = self.paint("─" * 52, "dim")
        lines = [rule, self.paint("  summary", "bold")]
        for status in ("rewritten", "cached", "skipped", "failed"):
            if counts.get(status):
                lines.append(
                    f"  {self.paint(f'{status:<10}', status)} {counts[status]:>3}"
                )
        if changed:
            lines.append(
                f"  {'words':<10} {words_in:>7,} → {words_out:,} "
                f"({ratio(words_in, words_out)} of original)"
            )
        lines.append(f"  {'elapsed':<10} {human_time(time.monotonic() - self.started)}")
        lines.append(f"  {'output':<10} {out_path} ({human_size(out_path)})")
        lines.append(f"  {'cache':<10} {workdir}")
        for result in self.results:
            if result.status == "failed":
                lines.append(
                    self.paint(
                        f"  ! [{result.index}] {result.title or result.item_id}"
                        f" — {result.detail}",
                        "failed",
                    )
                )
        lines.append(rule)
        return "\n".join(lines)
