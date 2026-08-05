import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "kernel-perf"
sys.path.insert(0, str(SKILL_DIR))
