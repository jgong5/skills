import subprocess
from pathlib import Path

import check_pdf
import make_pdf

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "architecture-study"


def figure(number, role, title, desc, labels):
    texts = "\n".join(
        f'<text x="{40 + 150 * i}" y="70" class="diagram-label">{label}</text>'
        for i, label in enumerate(labels)
    )
    return f"""\
<figure class="study-diagram" data-diagram="{role}" id="figure-{number}">
<svg viewBox="0 0 640 120" role="img" aria-labelledby="figure-{number}-title figure-{number}-desc">
<title id="figure-{number}-title">{title}</title>
<desc id="figure-{number}-desc">{desc}</desc>
{texts}
</svg>
<figcaption>Figure {number}. {title}</figcaption>
</figure>
"""


CONFORMING = f"""\
# Serving engine -- architecture study

## 1. Architectural deconstruction

**Boundary.** Inside: the scheduler and the executor. Excluded: the tokenizer,
whose source was not read.

{figure(1, "system-decomposition", "System decomposition",
        "The gateway hands work to the scheduler, which drives the executor.",
        ["gateway", "scheduler", "executor"])}
Figure 1 shows the batch state living in exactly one component <a id="ref-C1-1" href="#evidence-C1">[C1]</a>.

## 2. Key abstractions and data models

{figure(2, "contract-map", "Contract map",
        "Two seams cut; the executor seam leaks an ordering requirement.",
        ["gateway seam", "executor seam", "leaks ordering"])}
Figure 2 shows which seam a reader could actually cut.

## 3. Execution lifecycle and data flow

The scheduler holds the GIL (Global Interpreter Lock)[^gil] across the copy.

{figure(3, "execution-lifecycle", "Execution lifecycle",
        "One request from admission through a batched step to release.",
        ["admit", "batch step", "release"])}
Figure 3 follows one request from admission to release.

## 4. Trade-off analysis

**Decision.** Paged blocks.

**Alternatives.** One contiguous arena.

**Why this one.** Fragmentation dominates once sessions outlive a step.

{figure(4, "tradeoff-landscape", "Trade-off landscape",
        "Paged blocks and a contiguous arena meet at fragmentation.",
        ["chosen paged", "alternative arena", "deciding fragmentation"])}
Figure 4 places the choice against the constraint that decided it.

## 5. System constraints and vulnerabilities

Every enqueue parks the loop thread rather than yielding.

## 6. Alternative paradigms

An actor system wins once the participant set is open at run time.

## 7. Guided exploration

- Where does ownership of the batch actually end?
- What would have to be true for the executor seam to cut?

## 8. Sources

No external sources were used.

{check_pdf.LEDGER_START}
## 9. Evidence ledger

Each citation used above is defined here.

- <span id="evidence-C1">**[C1] The scheduler owns the batch state.** cite: sched.py:41 `self._batch = Batch()`</span> (cited at [1](#ref-C1-1))

{check_pdf.LEDGER_END}

[^gil]: CPython's interpreter-wide mutex, so a CPU-bound section serialises
    every other thread in the process.
"""


def test_imported_modules_are_this_skills_copies():
    # Two other skills ship a make_pdf.py and a check_pdf.py under the same
    # bare module names; only this copy carries the architecture contracts.
    assert Path(make_pdf.__file__).resolve() == SKILL_DIR / "make_pdf.py"
    assert Path(check_pdf.__file__).resolve() == SKILL_DIR / "check_pdf.py"


def test_css_lives_next_to_script():
    assert make_pdf.CSS.parent == Path(make_pdf.__file__).resolve().parent
    assert make_pdf.CSS.name == "tutorial.css"
    assert make_pdf.CSS.exists()


def test_no_args_returns_1(capsys):
    assert make_pdf.main([]) == 1
    assert "usage" in capsys.readouterr().err


def test_footnotes_render_as_a_notes_chapter(tmp_path):
    # Chrome implements no paged-media footnote model, so pandoc's footnotes
    # land at the back. tutorial.css titles that chapter "Notes" -- without
    # it the reader meets an unlabelled list of sentences after the ledger.
    md = tmp_path / "notes.md"
    md.write_text("# Footnote fixture\n\n## 1. Body\n\n"
                  "The GIL (Global Interpreter Lock)[^gil] serialises it.\n\n"
                  "[^gil]: CPython's interpreter-wide mutex.\n")
    pdf = make_pdf.convert(md, make_pdf.find_chrome())
    extracted = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                               capture_output=True, text=True, check=True).stdout
    assert "Notes" in extracted
    assert "interpreter-wide mutex" in extracted


def test_a_conforming_report_passes_every_check(tmp_path, capsys):
    # The contracts are spread over check_pdf.py, writing.md, and diagrams.md;
    # this is the one place that proves a single document can satisfy all of
    # them at once, rendered rather than in the abstract.
    md = tmp_path / "engine_architecture.md"
    md.write_text(CONFORMING)
    pdf = make_pdf.convert(md, make_pdf.find_chrome())
    assert check_pdf.main([str(pdf), str(md)]) == 0
    out = capsys.readouterr().out
    assert "clean:" in out
    for name in check_pdf.DIAGRAM_SAMPLE_NAMES.values():
        assert f"{name}" in out
