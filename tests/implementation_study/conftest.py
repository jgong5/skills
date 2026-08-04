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
# here always resolves to this directory's file, not whichever one Python
# cached first.
for script in SKILL_DIR.glob("*.py"):
    cached = sys.modules.get(script.stem)
    if cached is not None and Path(getattr(cached, "__file__", "")).resolve() != script.resolve():
        del sys.modules[script.stem]
