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
# either suite on its own. It does not cover passing both suite directories
# explicitly with this one first (`pytest tests/implementation_study
# tests/asm_tutorial`), which fails at collection -- pytest loads every
# initial argument's conftest before importing any test module, so in that
# order asm-tutorial's sys.path insertion lands on top of this one and its
# check_pdf.py shadows this file's at import time, with nothing yet in the
# module cache for the eviction below to catch. Fixing that needs both
# conftests to evict and to assert path precedence at module-import time, so
# it is not something this file can do one-sidedly: run the whole `tests/`
# directory, or one suite at a time.
for script in SKILL_DIR.glob("*.py"):
    cached = sys.modules.get(script.stem)
    if cached is not None and Path(getattr(cached, "__file__", "")).resolve() != script.resolve():
        del sys.modules[script.stem]
