import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "implementation-study"
sys.path.insert(0, str(SKILL_DIR))

# Every skill's conftest.py inserts its own directory so tests can import its
# scripts by bare module name (see the repo's top-level CLAUDE.md). That
# breaks when two skills ship a same-named script -- skills/asm-tutorial/ and
# skills/implementation-study/ both have a check_pdf.py and a make_pdf.py --
# and a whole-suite run imports asm-tutorial's copy first (it collects first,
# alphabetically), caching it under the bare name. Evict any such module from
# the cache before this skill's own tests run, so `from check_pdf import ...`
# here resolves to this directory's file, not whichever one Python cached
# first.
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
# provenance assertions in this suite's test_check_pdf.py and test_make_pdf.py
# only guarantee which copy THIS suite imports. The symmetric guarantee for
# asm-tutorial's suite has to live in tests/asm_tutorial/conftest.py. Until
# then: run the whole `tests/` directory, or one suite at a time.
for script in SKILL_DIR.glob("*.py"):
    cached = sys.modules.get(script.stem)
    if cached is not None and Path(getattr(cached, "__file__", "")).resolve() != script.resolve():
        del sys.modules[script.stem]
