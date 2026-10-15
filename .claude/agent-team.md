---
repo: jgong5/skills
integration_branch: main
gate_task: python3 -m pytest tests -q --ignore-glob='tests/*/test_make_pdf.py' --ignore-glob='tests/*/test_deckkit.py'
design_entry: CLAUDE.md
new_tests_dir: tests
prose_tests: tests/*/test_skill_md.py, tests/*/test_reference_docs.py, tests/asm_tutorial/test_cdna_facts.py
---
`gate_task` leaves out `tests/*/test_make_pdf.py`: those tests need pandoc,
a Chrome-family binary and poppler, which the dev container lacks. A change
to a skill's `make_pdf.py`, `check_pdf.py` or `tutorial.css` runs them where
those tools exist, and its PR states the result and the commit.

`gate_task` also leaves out `tests/*/test_deckkit.py`: it builds a real deck
with Node and installs `pptxgenjs` with npm, and the dev container has no
Node. A change to `skills/tutorial-deck/deckkit.js` runs it on a machine with
Node and npm (with network), and its PR states the result, the commit and the
machine.

A change to `.claude-plugin/marketplace.json` also runs `claude plugin
validate .` and `claude plugin details <bundle>` (CLAUDE.md, Commands).

Run commands the way `CLAUDE.local.md` says when it exists.
