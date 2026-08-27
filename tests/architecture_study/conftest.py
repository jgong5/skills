import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "architecture-study"
sys.path.insert(0, str(SKILL_DIR))

# Three skills now ship a check_pdf.py, a make_pdf.py, or both --
# skills/asm-tutorial/, skills/implementation-study/, and this one -- and every
# suite imports them by bare module name. This directory sorts first, so a
# whole-`tests/` run caches THIS skill's copies under those names before the
# other suites collect; each of the other conftests evicts them again. Evict
# here too, so running one suite at a time works in any order. The full
# ordering analysis lives in tests/implementation_study/conftest.py.
for script in SKILL_DIR.glob("*.py"):
    cached = sys.modules.get(script.stem)
    if cached is not None and Path(getattr(cached, "__file__", "")).resolve() != script.resolve():
        del sys.modules[script.stem]
