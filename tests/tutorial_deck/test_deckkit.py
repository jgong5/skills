import json
import os
import re
import subprocess
import zipfile

import pytest

from conftest import DECKKIT

# One deck covering every helper. Slides whose comment names a warning kind
# must raise exactly that warning; every other slide must raise none.
BUILD = r"""
const { deck } = require(process.env.DECKKIT);
const box = { x: 0.5, y: 1.4, w: 12, h: 5.4 };
(async () => {
  const d = deck({ title: 'Fixture', pin: 'abc1234', footer: 'fixture talk', minutes: Number(process.argv[2]) });
  d.slide('Fixture deck').notes({ min: 1, say: 'Opening.' });                         // 1
  d.agenda().notes({ min: 1, say: 'The plan.' });                                     // 2
  d.section('Mechanism');
  d.slide('Bullets, a box and an arrow')                                              // 3
    .bullets(['one', ['one point one'], 'two'], { x: 0.5, y: 1.4, w: 6, h: 3 })
    .box('cache', { x: 8, y: 1.5, w: 2, h: 0.8 })
    .arrow({ x: 10, y: 1.9 }, { x: 11.5, y: 3 }, { label: 'miss' })
    .notes({ min: 3, say: 'Clean.', ask: 'Why?', table: [['a', 'b']], open: 'Unverified.' });
  d.slide('A timeline').timeline(['client', 'server'],                                // 4
    [{ lane: 'client', from: 0, to: 2, label: 'send' }, { lane: 1, from: 2, to: 5, label: 'work' }], box)
    .notes({ min: 2, say: 'Clean.' });
  d.slide('A sequence').sequence(['A', 'B'],                                          // 5
    [{ from: 'A', to: 'B', label: 'req' }, { from: 'B', to: 'B', label: 'think' }, { from: 'B', to: 'A', label: 'resp', reply: true }], box)
    .notes({ min: 2, say: 'Clean.' });
  d.slide('A table').table([['k', 'v'], ['x', '1']], { x: 0.5, y: 1.4, w: 6, h: 2 })  // 6
    .notes({ min: 1, say: 'Clean.' });
  d.section('Code');
  d.slide('An overlong title that keeps going well past the width of one line on the slide')  // 7 title-wraps
    .notes({ min: 2, say: 'Long.' });
  d.slide('Undersized code')                                                          // 8 code-size
    .code('def f():\n' + '    x = 1  # ' + 'y'.repeat(120) + '\n', { x: 0.5, y: 1.4, w: 6, h: 3 }, { cite: 'src/a.py: f', hl: [1] })
    .notes({ min: 4, say: 'Small.' });
  d.slide('No minutes').notes({ say: 'Forgot min.' });                                // 9 notes
  d.slide('Overflowing text').text('word '.repeat(400), { x: 0.5, y: 1.4, w: 4, h: 1 })  // 10 fit-floor
    .notes({ min: 1, say: 'Too much.' });
  d.slide('Overflowing text, unchecked')                                              // 11
    .text('word '.repeat(400), { x: 0.5, y: 1.4, w: 4, h: 1 }, { noFitCheck: true })
    .notes({ min: 1, say: 'Silenced.' });
  process.stdout.write(JSON.stringify(await d.write(process.argv[3])));
})().catch((e) => { console.error(e); process.exit(1); });
"""
TOTAL = 18
EXPECTED = {7: ["title-wraps"], 8: ["code-size"], 9: ["notes"], 10: ["fit-floor"]}


def build(deck_dir, minutes):
    (deck_dir / "build.js").write_text(BUILD)
    out = deck_dir / ("deck_%d.pptx" % minutes)
    run = subprocess.run(
        ["node", str(deck_dir / "build.js"), str(minutes), str(out)],
        capture_output=True, text=True, env=dict(os.environ, DECKKIT=str(DECKKIT)),
    )
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout), zipfile.ZipFile(out)


def texts(z, name):
    return re.findall(r"<a:t>([^<]*)</a:t>", z.read(name).decode())


def notes(z, i):
    return "\n".join(texts(z, "ppt/notesSlides/notesSlide%d.xml" % i)).splitlines()


@pytest.fixture(scope="module")
def on_plan(deck_dir):
    return build(deck_dir, TOTAL)


def test_each_check_fires_on_its_slide_and_clean_slides_raise_none(on_plan):
    warnings, _ = on_plan
    by_slide = {}
    for w in warnings:
        by_slide.setdefault(w["slide"], []).append(w["kind"])
    assert by_slide == EXPECTED


def test_every_slide_has_notes(on_plan):
    _, z = on_plan
    slides = [n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
    assert len(slides) == 11
    for i in range(1, len(slides) + 1):
        assert any(line.startswith("SAY: ") for line in notes(z, i)), i


def test_agenda_minutes_are_the_sum_of_min(on_plan):
    _, z = on_plan
    mins = [int(line[5:]) for i in range(1, 12) for line in notes(z, i) if line.startswith("MIN: ")]
    table = re.search(r"<a:tbl>.*</a:tbl>", z.read("ppt/slides/slide2.xml").decode(), re.S).group(0)
    cells = re.findall(r"<a:t>([^<]*)</a:t>", table)
    rows = dict(zip(cells[::2], cells[1::2]))
    assert rows == {"Mechanism": "10 min", "Code": "8 min", "Total": "%d min" % sum(mins)}
    assert sum(mins) == TOTAL


def test_code_is_highlighted_and_cited(on_plan):
    _, z = on_plan
    xml = z.read("ppt/slides/slide8.xml").decode()
    assert "<a:highlight>" in xml
    assert "src/a.py: f" in texts(z, "ppt/slides/slide8.xml")


# 10% of 18 is 1.8 minutes: one minute off stays quiet, three warn.
@pytest.mark.parametrize("plan, fires", [(TOTAL, False), (TOTAL + 1, False), (TOTAL - 3, True), (TOTAL + 3, True)])
def test_total_off_plan_warns(deck_dir, plan, fires):
    warnings, _ = build(deck_dir, plan)
    assert any(w["kind"] == "plan" and w["slide"] is None for w in warnings) == fires
