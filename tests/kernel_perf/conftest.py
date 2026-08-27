import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "kernel-perf"
sys.path.insert(0, str(SKILL_DIR))

# Two other skills ship a same-named check_pdf.py / make_pdf.py, and every
# suite imports them by bare module name. Evict whichever copy collected
# first so this suite's modules resolve to this skill's files. The full
# ordering analysis lives in tests/implementation_study/conftest.py.
for script in SKILL_DIR.glob("*.py"):
    cached = sys.modules.get(script.stem)
    if cached is not None and Path(getattr(cached, "__file__", "")).resolve() != script.resolve():
        del sys.modules[script.stem]
