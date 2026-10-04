import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "implementation-study"
sys.path.insert(0, str(SKILL_DIR))

# Every skill's conftest.py inserts its own directory so tests can import its
# scripts by bare module name (see the repo's top-level CLAUDE.md). That
# breaks when skills ship a same-named script -- skills/architecture-study/,
# skills/asm-tutorial/ and skills/implementation-study/ each have a
# check_pdf.py and a make_pdf.py. A whole-suite run caches architecture-study's
# copy under the bare name first (its suite sorts ahead of the others), then
# asm-tutorial's suite replaces it with its own. Evict any such module from the
# cache before this skill's own tests run, so `from check_pdf import ...` here
# resolves to this directory's file, not whichever copy an earlier suite left
# cached.
#
# That covers the documented invocations: the whole `tests/` directory, or
# either suite on its own. Passing both suite directories explicitly on one
# command line is unsupported in BOTH orders, and the two orders fail
# differently. pytest loads every initial argument's conftest before importing
# any test module, so the conftest loaded last owns sys.path[0] and nothing is
# in the module cache yet for the eviction below to catch:
#
#   pytest tests/implementation_study tests/asm_tutorial
#     Loud. asm-tutorial's insertion lands on top, so this suite's modules
#     import asm-tutorial's check_pdf.py, which lacks the names only this
#     skill's copy defines -- collection stops with an ImportError.
#
#   pytest tests/asm_tutorial tests/implementation_study
#     Silent, and the dangerous one. This conftest's insertion lands on top,
#     so asm-tutorial's OWN test modules import this skill's check_pdf.py and
#     make_pdf.py; the two copies share most of their public names, so that
#     run can report all green while testing the wrong files.
#
# This file cannot close the second case: the eviction below and the
# provenance assertions in this suite's test_check_evidence.py,
# test_check_pdf.py and test_make_pdf.py only guarantee which copy THIS suite
# imports. Every other suite whose skill ships a same-named script runs the
# same eviction in its own conftest, which is what keeps a whole-`tests/` run
# correct no matter which directory collects first -- but only for imports
# that run at collection. An `import check_pdf` inside a test function runs
# after every suite has collected, so it gets whichever copy the suite that
# collected last left cached. Import this skill's scripts at module level
# only. Both explicit-directory cases above stay unsupported: there, both
# conftests load before any test module is imported, so nothing is cached yet
# for either eviction to catch.
# Run the whole `tests/` directory, or one suite at a time.
for script in SKILL_DIR.glob("*.py"):
    cached = sys.modules.get(script.stem)
    if cached is not None and Path(getattr(cached, "__file__", "")).resolve() != script.resolve():
        del sys.modules[script.stem]
