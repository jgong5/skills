from pathlib import Path

import annotate_asm

CDNA_FACTS = Path(__file__).resolve().parents[2] / "skills" / "asm-tutorial" / "cdna-facts.md"


def test_every_arch_key_is_documented():
    text = CDNA_FACTS.read_text()
    for key in annotate_asm.ARCH:
        assert f"## {key}" in text, f"{key} missing a section in cdna-facts.md"
