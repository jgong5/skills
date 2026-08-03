from pathlib import Path

import annotate_asm

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_detect_arch_reads_amdgcn_target():
    lines = FIXTURES.joinpath("fixture_kernel_gfx942.s").read_text().splitlines()
    assert annotate_asm.detect_arch(lines) == "gfx942"


def test_mfma_note_gfx942_cost():
    note = annotate_asm.mfma_note("v_mfma_f32_16x16x16_f16",
                                  "a[0:3], v[2:3], v[4:5], a[0:3]", "gfx942")
    assert "8192 FLOP in ~16 cyc" in note


def test_mfma_note_unknown_arch_has_no_cost():
    note = annotate_asm.mfma_note("v_mfma_f32_16x16x16_f16",
                                  "a[0:3], v[2:3], v[4:5], a[0:3]", "gfx1100")
    assert "FLOP in ~" not in note


def test_annotate_gfx942_reports_cost(tmp_path):
    src = FIXTURES / "fixture_kernel_gfx942.s"
    dest, n = annotate_asm.annotate(src, tmp_path)
    text = dest.read_text()
    assert "8192 FLOP in ~16 cyc" in text
    assert n > 0


def test_annotate_unknown_arch_warns_and_skips_cost(tmp_path, capsys):
    src = FIXTURES / "fixture_kernel_gfx1100.s"
    dest, n = annotate_asm.annotate(src, tmp_path)
    text = dest.read_text()
    assert "FLOP in ~" not in text
    assert "unrecognized target" in capsys.readouterr().err
