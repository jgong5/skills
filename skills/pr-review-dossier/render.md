# Rendering the dossier PDF

This route assumes no PDF toolchain (no pandoc, reportlab, weasyprint, pypdf) --
do not install one. The zero-install path is a self-contained HTML file printed
by headless Chrome, then post-processed by `pdf_forms.py` (pure stdlib) to make
the decision boxes clickable. Chrome or Edge is the only external dependency,
and one of them is already present on nearly every desktop.

`<skill-dir>` and `<scratch>` below are as defined in [SKILL.md](SKILL.md).

## Step A -- print the HTML

Pass **absolute paths** for both `--print-to-pdf` and the input. Chrome does not
resolve relative paths, and on Windows it rejects a Git Bash `/c/...` path with
`The system cannot find the path specified` -- convert to `C:\...` form there
(`cygpath -w`).

```bash
# Windows
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
# Fallback: "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
# macOS:  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# Linux:  google-chrome  |  chromium

"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$(cygpath -w <scratch>/pr-<N>-dossier.pdf)" \
  "$(cygpath -w <scratch>/pr-<N>-dossier.html)"
```

Success prints `NNNNN bytes written to file ...` on stderr. The GCM/MCS
`ERROR:` lines about registration endpoints are unrelated browser startup noise
-- ignore them and look for the bytes-written line.

## Step B -- make the boxes clickable and the notes typable

Chrome flattens HTML form controls into static ink, so the decision boxes and
reword notes are authored as **link anchors** and converted into real PDF form
fields afterwards:

```bash
python "<skill-dir>/pdf_forms.py" <scratch>/pr-<N>-dossier.pdf
```

It prints e.g. `12 boxes in 4 synced groups, 4 reword notes -> ...`. Check the
box count against the number of comments times three, and the note count against
the number of comments.

**The anchor contract.** Every decision box is an empty anchor whose href is
`chkbox:<comment-id>.<publish|reword|drop>`, and every reword note an empty
anchor whose href is `note:<comment-id>`:

```html
<a class="box" href="chkbox:C1.publish"></a>
<a class="note" href="note:C1"></a>
```

Chrome records each anchor's exact rectangle as a link annotation;
`pdf_forms.py` swaps those for widgets -- radio buttons for `chkbox:`, a
multiline text field named `C1_note` for `note:`. Anchors sharing a comment id
form one radio group, which buys two behaviors at once:

- **Sync** -- the `C1.publish` box in the index table and the `C1.publish` box on
  C1's card are two widgets of one field with the same on-state, so ticking
  either ticks both (the PDF `RadiosInUnison` flag).
- **Exclusivity** -- ticking `C1.drop` clears `C1.publish` everywhere.

So write all three boxes for every comment in *both* places: the index table row
and the card's decision block. Clicking a ticked box again clears it.

The note field is what makes **Reword** an instruction rather than a shrug: the
user ticks R and types *how* the comment should be reworded, and Step C reads
that text back so a later run can rewrite the comment to order. Give every
comment a note box -- the field is inert when Reword is not ticked, and a user
who has to hunt for a place to write will not write. One note box per comment,
on the card; the index row stays narrow.

Filling requires a viewer that supports forms -- Chrome, Edge, Acrobat, most
others. Ticks and notes persist only if the user saves the PDF from the viewer.

## Step C -- read a filled dossier back

When the user hands back a saved copy, read their decisions instead of asking
them to retype:

```bash
python "<skill-dir>/pdf_forms.py" --read <scratch>/pr-<N>-dossier.pdf
```

```json
{
  "C1": { "decision": "Reword", "note": "soften: say (maybe) take the lock, and cite line 288" },
  "C2": { "decision": "Drop",   "note": "" }
}
```

`decision` is `Publish`, `Reword`, `Drop`, or `null` when the comment was left
unticked; `note` is `""` when nothing was typed. The reader takes the last
version of each object in the file, which is how an incremental save from a
viewer records the new values.

Two ways this comes back empty, both worth naming to the user rather than
guessing at: the file is the *unsaved* original (nothing ticked -- the script
warns), or the viewer rewrote it with compressed object streams, which this
stdlib parser cannot walk (the script says so and exits). Chrome, Edge and
Acrobat all save in a form it reads.

## Diagrams: SVG, not ASCII

`pr-explain` draws ASCII for the terminal; the dossier is a printed page, so
**redraw those diagrams as inline SVG**. Chrome preserves inline SVG as true
vector paths -- scalable, sharp at any zoom, with real selectable text and no
raster images.

Recipe, using the architecture diagram in [example.html](example.html) as the
model:

- One `<svg>` per figure with `width`/`height` in px and a matching `viewBox`,
  wrapped in `<figure>` with a `<figcaption>` naming what the reader is seeing.
- Nodes: `<rect rx="4">` plus a centered `<text text-anchor="middle">`. A second
  smaller `<text>` line beneath carries the qualifier (module path, type).
- Edges: `<line>` or `<path>` with `marker-end` pointing at a `<marker>` arrowhead
  defined once in `<defs>`. Dashed (`stroke-dasharray="4 3"`) for a new or
  proposed edge.
- Mark what the PR touches: red stroke `#c0392b` on a `#fdecea` fill, against
  `#0b5394` on `#eaf4fb` for untouched nodes. State the convention in the caption.
- Set `font-family`/`font-size` on the root `<svg>` so text inherits it, and keep
  the whole figure inside the 180mm content width.

Draw both diagrams the briefing calls for: the architecture/blast radius, and the
data/control flow with the changed path marked.

## Template

Self-contained -- no external CSS, fonts, or images -- so the HTML stands alone
and the PDF renders identically anywhere. [example.html](example.html) is a
complete two-comment dossier to copy from -- it is built from a real PyTorch PR,
used here purely as a layout and density reference, not because anything in this
skill is PyTorch-specific. The essentials:

```html
<style>
  @page { size: A4; margin: 16mm 14mm; }
  html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { font: 10.5pt/1.45 "Segoe UI", Arial, sans-serif; color: #1a1a1a; }
  h2 { font-size: 14pt; color: #0b5394; border-bottom: 1.5px solid #0b5394;
       padding-bottom: 3pt; margin: 18pt 0 6pt; break-after: avoid; }
  pre { font: 8.5pt/1.32 Consolas, monospace; background: #f7f9fb;
        border: 1px solid #d5dde5; border-left: 3px solid #0b5394;
        padding: 6pt 8pt; white-space: pre; overflow-x: hidden; break-inside: avoid; }
  table { border-collapse: collapse; width: 100%; font-size: 9pt; }
  th, td { border: 1px solid #c9d3dc; padding: 4pt 6pt; vertical-align: top; }
  th { background: #0b5394; color: #fff; }
  td.c { text-align: center; width: 22pt; }        /* checkbox columns */
  figure { margin: 8pt 0; text-align: center; break-inside: avoid; }
  .card { break-before: page; }                     /* one comment per page */
  .comment { background: #fffbe6; border: 1px solid #e0d28a; padding: 6pt 9pt; }
  .ai-note { font-size: 7.5pt; color: #806b00; letter-spacing: .6pt; }
  .hit { background: #ffe0e0; display: block; }     /* the flagged source line */
  .verdict { font-size: 8.5pt; font-weight: 600; padding: 1pt 6pt; border-radius: 3pt; }
  .confirmed { background: #d8f0d8; } .speculative { background: #fdf0d0; }
  .refuted { background: #f5d5d5; }
  .decide { border: 1.5px solid #333; padding: 7pt 10pt; margin-top: 10pt;
            break-inside: avoid; }
  .box { display: inline-block; width: 11pt; height: 11pt; border: 1px solid #333;
         background: #fff; text-decoration: none; vertical-align: -2pt;
         margin: 0 4pt 0 12pt; }
  td.c .box { margin: 0; }
  .note-label { font-size: 8pt; color: #555; margin: 6pt 0 2pt; }
  .note { display: block; height: 42pt; border: 1px solid #888; background: #fff;
          text-decoration: none; }                /* the reword note field */
</style>
```

Index row and decision block, the two places every comment's boxes appear:

```html
<tr><td>C1</td><td><code>src/foo.py:412</code></td><td>Thread safety</td>
    <td><span class="verdict confirmed">Confirmed</span></td><td>One-line summary</td>
    <td class="c"><a class="box" href="chkbox:C1.publish"></a></td>
    <td class="c"><a class="box" href="chkbox:C1.reword"></a></td>
    <td class="c"><a class="box" href="chkbox:C1.drop"></a></td></tr>

<div class="decide"><b>Decision:</b>
<a class="box" href="chkbox:C1.publish"></a>Publish
<a class="box" href="chkbox:C1.reword"></a>Reword
<a class="box" href="chkbox:C1.drop"></a>Drop
<div class="note-label">If reworded &mdash; how (this text is read back and applied):</div>
<a class="note" href="note:C1"></a></div>
```

Head the checkbox columns `P` / `R` / `D`, put the legend above the table, and
say in the legend that the reword note lives on the comment's own page.

## Rules that keep it readable on paper

- `.card` starts each comment on a fresh page. A card longer than a page still
  splits -- when a long code quote causes that, trim the quote to the part the
  comment turns on rather than letting the decision box drift onto page two.
- `break-inside: avoid` on `.decide` is load-bearing, not cosmetic: a note box
  split across a page break arrives as two link rectangles, and while
  `pdf_forms.py` handles that by making them two widgets of one field, half a
  note box at the foot of a page reads as a printing accident.
- `white-space: pre` with `overflow-x: hidden` keeps quoted code aligned;
  wrapping would scramble it. Keep source lines under ~95 columns at 8.5pt so
  nothing is clipped.
- Escape `<`, `>`, and `&` inside `<pre>` -- unescaped generics or comparisons in
  quoted C++/Python silently swallow the rest of the block.
- `print-color-adjust: exact` is what makes the highlight, verdict, and comment
  backgrounds survive printing; without it they can render as plain white.
- The `.box` CSS border is what the reader sees; the widget on top paints only
  the check mark, so keep the border on the anchor.

If the project already has an HTML-to-PDF report convention of its own, read one
of those for the house look before diverging from it.
