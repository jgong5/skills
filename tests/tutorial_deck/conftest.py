import re
import subprocess
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "tutorial-deck"
DECKKIT = SKILL_DIR / "deckkit.js"


@pytest.fixture(scope="session")
def deck_dir(tmp_path_factory):
    """A deck directory with deckkit's pinned pptxgenjs in its node_modules,
    installed the way a deck installs it. Needs node, and npm with network."""
    version = re.search(r"PPTXGENJS_VERSION = '([^']+)'", DECKKIT.read_text()).group(1)
    d = tmp_path_factory.mktemp("deck")
    subprocess.run(
        ["npm", "install", "--no-save", "--no-package-lock", "--prefix", str(d), "pptxgenjs@" + version],
        check=True, capture_output=True,
    )
    return d
