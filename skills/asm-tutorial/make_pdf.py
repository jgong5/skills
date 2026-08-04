#!/usr/bin/env python3
"""Render a tutorial markdown file to PDF.

    <skill-dir>/make_pdf.py <doc.md> [doc2.md ...]

Markdown paths are required -- this script does not own a docs/ directory to
glob, unlike the project-specific fork it was forked from. Output lands next
to each input as .pdf. --keep-html leaves the intermediate HTML there too,
which is the thing to look at when the PDF comes out wrong.

The route is markdown -> HTML -> Chrome's print-to-PDF. pandoc does the first
leg (tutorial.css is the print stylesheet, next to this file); Chrome does the
second over the DevTools protocol rather than the --print-to-pdf command-line
flag, because the flag gives no control over the running header and footer --
it either stamps every page with the file:// URL or, with
--print-to-pdf-no-header, drops the page numbers as well.

Requirements beyond the base image, neither of which survives `./teardown.sh`
or an image upgrade:

    google-chrome        installed into the container by hand
    python3 -c 'import websockets'   present in the image today, via vLLM

pandoc is preinstalled. Chrome finds "Liberation Serif" and friends through
fontconfig, so nothing here has to name a font file.
"""
import asyncio
import base64
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSS = HERE / "tutorial.css"

CHROME_CANDIDATES = ["google-chrome", "google-chrome-stable", "chromium",
                     "chromium-browser"]

# Inches. The side margins are what tutorial.css sizes the code font against;
# read the comment at the top of that file before changing them.
MARGIN_X = 21 / 25.4
MARGIN_TOP = 0.72
MARGIN_BOTTOM = 0.68

# Chrome renders these inside the page margins. An empty header still has to be
# a real element, and both need an explicit font-size -- the default is 8px.
HEADER_HTML = "<div></div>"
FOOTER_HTML = (
    '<div style="width:100%;text-align:center;font-size:11px;color:#555;'
    'font-family:\'Liberation Sans\',sans-serif;">'
    '<span class="pageNumber"></span></div>'
)


def find_chrome() -> str:
    for name in CHROME_CANDIDATES:
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError("no chrome binary found (looked for: "
                       + ", ".join(CHROME_CANDIDATES) + ")")


def to_html(md: Path, html: Path) -> None:
    subprocess.run(
        ["pandoc", str(md), "-t", "html5", "--standalone", "--embed-resources",
         "--shift-heading-level-by=-1", "--toc", "--toc-depth=2",
         "-V", "toc-title=Contents", "-c", str(CSS), "-o", str(html)],
        check=True,
    )


def start_chrome(chrome: str, profile: Path):
    """Launch headless Chrome and return (process, debugging port)."""
    proc = subprocess.Popen(
        [chrome, "--headless", "--no-sandbox", "--disable-gpu",
         "--disable-dev-shm-usage", "--no-first-run",
         "--no-default-browser-check", "--disable-extensions",
         "--hide-scrollbars", f"--user-data-dir={profile}",
         "--remote-debugging-port=0", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    port_file = profile / "DevToolsActivePort"
    for _ in range(400):
        if proc.poll() is not None:
            raise RuntimeError(f"chrome exited with {proc.returncode} at startup")
        if port_file.exists():
            lines = port_file.read_text().splitlines()
            if len(lines) >= 2 and lines[0].strip().isdigit():
                return proc, int(lines[0])
        time.sleep(0.05)
    proc.kill()
    raise RuntimeError("chrome never opened a debugging port")


async def print_to_pdf(port: int, url: str) -> bytes:
    import websockets

    req = urllib.request.Request(f"http://127.0.0.1:{port}/json/new?about:blank",
                                 method="PUT")
    target = json.loads(urllib.request.urlopen(req, timeout=15).read())

    async with websockets.connect(target["webSocketDebuggerUrl"],
                                  max_size=None) as ws:
        counter = 0

        async def call(method, **params):
            nonlocal counter
            counter += 1
            mine = counter
            await ws.send(json.dumps({"id": mine, "method": method,
                                      "params": params}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == mine:
                    if "error" in msg:
                        raise RuntimeError(f"{method}: {msg['error']}")
                    return msg["result"]

        await call("Page.navigate", url=url)

        ready = (f"location.href === {json.dumps(url)}"
                 " && document.readyState === 'complete'"
                 " && document.fonts.status === 'loaded'")
        for _ in range(300):
            result = await call("Runtime.evaluate", expression=ready,
                                returnByValue=True)
            if result["result"].get("value") is True:
                break
            await asyncio.sleep(0.05)
        else:
            raise RuntimeError("page never finished loading")

        pdf = await call(
            "Page.printToPDF",
            paperWidth=8.5, paperHeight=11.0,
            marginTop=MARGIN_TOP, marginBottom=MARGIN_BOTTOM,
            marginLeft=MARGIN_X, marginRight=MARGIN_X,
            printBackground=True,
            preferCSSPageSize=False,
            displayHeaderFooter=True,
            headerTemplate=HEADER_HTML, footerTemplate=FOOTER_HTML,
            generateDocumentOutline=True,
        )
        return base64.b64decode(pdf["data"])


def convert(md: Path, chrome: str, keep_html: bool = False) -> Path:
    pdf = md.with_suffix(".pdf")
    html = md.with_suffix(".html")
    profile = Path(tempfile.mkdtemp(prefix="make_pdf-chrome-"))
    proc = None
    try:
        to_html(md, html)
        proc, port = start_chrome(chrome, profile)
        data = asyncio.run(print_to_pdf(port, html.as_uri()))
        pdf.write_bytes(data)
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(profile, ignore_errors=True)
        if not keep_html:
            html.unlink(missing_ok=True)
    return pdf


def main(argv: list[str]) -> int:
    keep_html = "--keep-html" in argv
    docs = [Path(a).resolve() for a in argv if not a.startswith("--")]
    if not docs:
        print("usage: make_pdf.py <doc.md> [doc2.md ...] [--keep-html]",
              file=sys.stderr)
        return 1

    if not shutil.which("pandoc"):
        print("pandoc not found (expected in the image)", file=sys.stderr)
        return 1
    try:
        import websockets  # noqa: F401
    except ImportError:
        print("websockets not installed; run: pip install websockets",
              file=sys.stderr)
        return 1
    try:
        chrome = find_chrome()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    rc = 0
    for md in docs:
        if not md.exists():
            print(f"FAILED  {md.name}: no such file", file=sys.stderr)
            rc = 1
            continue
        try:
            pdf = convert(md, chrome, keep_html)
        except Exception as exc:
            print(f"FAILED  {md.name}: {exc}", file=sys.stderr)
            rc = 1
            continue
        print(f"{pdf}  ({pdf.stat().st_size // 1024} KB)")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
