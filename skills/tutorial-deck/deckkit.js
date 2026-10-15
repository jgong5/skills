// deckkit.js -- the helper library every tutorial-deck build.js requires.
//
//   const { deck } = require('<skill-dir>/deckkit.js');
//   const d = deck({ title, pin, footer, minutes });
//   const s = d.slide('Title');
//   s.code(src, { x, y, w, h }, { cite: 'path: symbol', hl: [3] });
//   s.notes({ min: 2, say: '...' });
//   const warnings = await d.write('talk.pptx');
//
// Positions are inches on a 13.333 x 7.5 slide. pptxgenjs is resolved from the
// build script's own directory, not from here: each deck installs its own
// pinned copy in its node_modules, and this file lives in the skill directory.

'use strict';
const path = require('path');
const { createRequire } = require('module');

// The pptxgenjs version a deck installs (`npm install pptxgenjs@<this>`).
const PPTXGENJS_VERSION = '4.0.1';

// Every threshold a build-time check uses, one number per line.
const LIMITS = {
  titleMaxLines: 1,     // a title estimated to wrap past this many lines warns
  fitFloor: 12,         // auto-fit text never shrinks below this size (pt)
  codeMinSize: 11,      // code sized below this (pt) warns
  planTolerance: 0.1,   // total minutes may differ from the plan by this fraction
  latinEm: 0.55,        // estimated width of a non-CJK character, in em
  wideEm: 1.0,          // estimated width of a CJK or full-width character, in em
  lineSpacing: 1.2,     // estimated line height, as a multiple of the font size
};

const SIZE = { title: 28, body: 18, code: 16, small: 12, footer: 10 };
const PAD_W = 0.2;  // PowerPoint's default text inset, left plus right (in)
const PAD_H = 0.1;  // top plus bottom (in)
const SLIDE_W = 13.333;
const TITLE_BOX = { x: 0.5, y: 0.3, w: 12.333, h: 0.8 };

const DEFAULT_PALETTE = {
  text: '1F2937', muted: '6B7280', accent: '2563EB', line: '9CA3AF',
  fill: 'EFF6FF', codeBg: 'F3F4F6', highlight: 'FFF3B0', header: 'DBEAFE',
};

// ponytail: a per-character width heuristic, not font metrics; it misjudges
// runs of wide Latin capitals. Measure with the real font if that matters.
function ems(str) {
  let w = 0;
  for (const ch of str) w += ch.codePointAt(0) >= 0x2e80 ? LIMITS.wideEm : LIMITS.latinEm;
  return w;
}

// Wrapped line count of `str` at `size` pt in a box `wIn` inches wide.
function lineCount(str, size, wIn) {
  const perLine = Math.max(wIn, 0.01) * 72 / size;
  return String(str).split('\n')
    .reduce((n, para) => n + Math.max(1, Math.ceil(ems(para) / perLine)), 0);
}

const height = (lines, size) => lines * size * LIMITS.lineSpacing / 72;

const asList = (v) => (v === undefined ? [] : Array.isArray(v) ? v : [v]);

function notesText(n) {
  const out = [];
  if (n.min !== undefined) out.push(`MIN: ${n.min}`);
  if (n.say !== undefined) out.push(`SAY: ${n.say}`);
  for (const q of asList(n.ask)) out.push(`ASK: ${q}`);
  if (n.table) out.push('TABLE:', ...n.table.map((r) => r.join(' | ')));
  for (const q of asList(n.open)) out.push(`OPEN: ${q}`);
  return out.join('\n');
}

function deck(opts) {
  const req = createRequire(require.main ? require.main.filename : path.join(process.cwd(), 'build.js'));
  let PptxGenJS;
  try {
    PptxGenJS = req('pptxgenjs');
  } catch (e) {
    throw new Error(`deckkit: pptxgenjs not found next to the build script; ` +
      `run \`npm install pptxgenjs@${PPTXGENJS_VERSION}\` in the deck directory (${e.message})`);
  }
  const pptx = new PptxGenJS();
  pptx.layout = 'LAYOUT_WIDE';
  pptx.title = opts.title || '';
  const fonts = Object.assign({ body: 'Microsoft YaHei', code: 'Consolas' }, opts.fonts);
  const pal = Object.assign({}, DEFAULT_PALETTE, opts.palette);
  const footer = [opts.footer, opts.pin].filter(Boolean).join('  |  ');
  const slides = [];
  const sections = [];
  const warnings = [];
  let agendaSlide = null;

  function makeSlide(title, sOpts = {}) {
    const raw = pptx.addSlide();
    const n = slides.length + 1;
    const rec = { raw, n, notes: null, section: Math.max(sections.length - 1, 0) };
    slides.push(rec);
    const warn = (kind, message) => warnings.push({ slide: n, kind, message });
    const linesAt = (paras, size, box) =>
      paras.reduce((k, p) => k + lineCount(p.text, size, box.w - PAD_W - p.indent), 0);

    // Auto-fit shrinks from the requested size towards LIMITS.fitFloor until
    // the estimate fits; `fit: false` keeps the size and checks for overflow.
    function fitted(paras, box, o, what) {
      const size = o.size || SIZE.body;
      if (o.fit === false) {
        if (!o.noFitCheck && height(linesAt(paras, size, box), size) > box.h - PAD_H) {
          warn('overflow', `${what} estimated to overflow its box`);
        }
        return size;
      }
      for (let s = size; s >= LIMITS.fitFloor; s--) {
        if (height(linesAt(paras, s, box), s) <= box.h - PAD_H) return s;
      }
      if (!o.noFitCheck) warn('fit-floor', `${what} still overflows at the fit floor (${LIMITS.fitFloor}pt)`);
      return LIMITS.fitFloor;
    }

    const base = (o) => ({ fontFace: fonts.body, color: o.color || pal.text, valign: o.valign || 'top', align: o.align || 'left' });

    const s = {
      raw,
      number: n,
      text(str, box, o = {}) {
        const size = fitted([{ text: str, indent: 0 }], box, o, `text "${String(str).slice(0, 40)}"`);
        raw.addText(String(str), Object.assign(base(o), box, { fontSize: size, bold: !!o.bold },
          o.shape ? { shape: o.shape } : {}, o.fill ? { fill: { color: o.fill } } : {},
          o.border ? { line: { color: o.border, width: 1 } } : {}));
        return s;
      },
      // items: strings; an array after a string holds that item's sub-bullets.
      bullets(items, box, o = {}) {
        const paras = [];
        const walk = (list, level) => list.forEach((it) => (Array.isArray(it)
          ? walk(it, level + 1)
          : paras.push({ text: String(it), indent: 0.4 * (level + 1), level })));
        walk(items, 0);
        const size = fitted(paras, box, o, 'bullets');
        raw.addText(paras.map((p) => ({ text: p.text, options: { bullet: true, indentLevel: p.level, breakLine: true } })),
          Object.assign(base(o), box, { fontSize: size }));
        return s;
      },
      // Code never wraps: it is sized to fit both box dimensions, and warns
      // when that size falls below LIMITS.codeMinSize. hl: 1-based line numbers.
      code(src, box, o = {}) {
        const lines = String(src).replace(/\n$/, '').split('\n');
        const citeH = o.cite ? 0.3 : 0;
        const longest = Math.max(...lines.map(ems), 1);
        const byW = (box.w - PAD_W) * 72 / longest;
        const byH = (box.h - citeH - PAD_H) * 72 / (lines.length * LIMITS.lineSpacing);
        const size = Math.floor(Math.min(o.size || SIZE.code, byW, byH) * 2) / 2;
        if (size < LIMITS.codeMinSize && !o.noFitCheck) {
          warn('code-size', `code sized ${size}pt, below ${LIMITS.codeMinSize}pt: shorten the excerpt or widen the box`);
        }
        const hl = new Set(o.hl || []);
        raw.addText(lines.map((l, i) => ({
          text: l || ' ',
          options: Object.assign({ breakLine: true }, hl.has(i + 1) ? { highlight: pal.highlight, bold: true } : {}),
        })), {
          x: box.x, y: box.y, w: box.w, h: box.h - citeH, fontFace: fonts.code, fontSize: size,
          color: pal.text, fill: { color: pal.codeBg }, valign: 'top', align: 'left',
        });
        if (o.cite) {
          raw.addText(o.cite, {
            x: box.x, y: box.y + box.h - citeH, w: box.w, h: citeH, fontFace: fonts.code,
            fontSize: SIZE.footer, color: pal.muted, align: 'right', valign: 'middle',
          });
        }
        return s;
      },
      // rows: arrays of strings; the first row is the header unless header: false.
      table(rows, box, o = {}) {
        const size = o.size || 14;
        const colW = o.colW || Array(rows[0].length).fill(box.w / rows[0].length);
        const est = rows.reduce((t, r) => t + 0.1 + height(Math.max(...r.map((c, j) =>
          lineCount(c, size, colW[j] - 0.1))), size), 0);
        if (est > box.h && !o.noFitCheck) warn('overflow', `table estimated ${est.toFixed(2)}in tall in a ${box.h}in box`);
        const header = o.header !== false;
        raw.addTable(rows.map((r, i) => r.map((c) => ({
          text: String(c),
          options: header && i === 0 ? { bold: true, fill: { color: pal.header } } : {},
        }))), {
          x: box.x, y: box.y, w: box.w, colW, fontFace: fonts.body, fontSize: size, color: pal.text,
          border: { type: 'solid', pt: 0.75, color: pal.line }, valign: 'middle',
        });
        return s;
      },
      box(label, box, o = {}) {
        return s.text(label, box, Object.assign({
          shape: pptx.ShapeType.roundRect, fill: pal.fill, border: pal.accent,
          align: 'center', valign: 'middle', size: SIZE.small + 2,
        }, o));
      },
      // from, to: points { x, y }. A line shape has no direction of its own,
      // so a leftward or upward arrow is a flipped bounding box.
      arrow(from, to, o = {}) {
        raw.addShape(pptx.ShapeType.line, {
          x: Math.min(from.x, to.x), y: Math.min(from.y, to.y),
          w: Math.abs(to.x - from.x), h: Math.abs(to.y - from.y),
          flipH: to.x < from.x, flipV: to.y < from.y,
          line: {
            color: o.color || pal.accent, width: o.width || 1.5, dashType: o.dash ? 'dash' : 'solid',
            endArrowType: o.head === false ? 'none' : 'triangle',
          },
        });
        if (o.label) {
          const mx = (from.x + to.x) / 2;
          const my = (from.y + to.y) / 2;
          s.text(o.label, { x: mx - 1.5, y: my - 0.4, w: 3, h: 0.4 }, { size: SIZE.small, align: 'center', valign: 'bottom' });
        }
        return s;
      },
      // lanes: names. events: { lane (name or index), from, to, label } on one
      // shared time axis spanning the earliest `from` to the latest `to`.
      timeline(lanes, events, box, o = {}) {
        const labelW = o.labelW || 1.6;
        const laneH = box.h / lanes.length;
        const t0 = Math.min(...events.map((e) => e.from));
        const t1 = Math.max(...events.map((e) => e.to));
        const scale = (box.w - labelW) / Math.max(t1 - t0, 1e-9);
        lanes.forEach((name, i) => {
          const y = box.y + i * laneH;
          s.text(name, { x: box.x, y, w: labelW, h: laneH }, { size: SIZE.small + 2, bold: true, valign: 'middle' });
          if (i) s.arrow({ x: box.x, y }, { x: box.x + box.w, y }, { color: pal.line, width: 0.75, head: false });
        });
        for (const e of events) {
          const i = typeof e.lane === 'number' ? e.lane : lanes.indexOf(e.lane);
          if (i < 0) throw new Error(`deckkit: timeline event "${e.label}" names unknown lane "${e.lane}"`);
          s.box(e.label || '', {
            x: box.x + labelW + (e.from - t0) * scale, y: box.y + i * laneH + 0.08,
            w: Math.max((e.to - e.from) * scale, 0.1), h: laneH - 0.16,
          }, Object.assign({ size: SIZE.small }, e.fill ? { fill: e.fill } : {}, e.noFitCheck ? { noFitCheck: true } : {}));
        }
        return s;
      },
      // actors: names. messages: { from, to, label, reply }, top to bottom;
      // a reply is dashed, and from === to draws a self-call loop.
      sequence(actors, messages, box, o = {}) {
        const headH = o.headH || 0.5;
        const colW = box.w / actors.length;
        const cx = (name) => {
          const i = actors.indexOf(name);
          if (i < 0) throw new Error(`deckkit: sequence message names unknown actor "${name}"`);
          return box.x + (i + 0.5) * colW;
        };
        actors.forEach((a) => {
          s.box(a, { x: cx(a) - colW * 0.4, y: box.y, w: colW * 0.8, h: headH }, { bold: true });
          s.arrow({ x: cx(a), y: box.y + headH }, { x: cx(a), y: box.y + box.h },
            { color: pal.line, width: 0.75, dash: true, head: false });
        });
        const step = (box.h - headH) / (messages.length + 1);
        messages.forEach((m, i) => {
          const y = box.y + headH + step * (i + 1);
          const a = { x: cx(m.from), y };
          if (m.from === m.to) {
            const out = { x: a.x + 0.4, y };
            const down = { x: a.x + 0.4, y: y + step * 0.4 };
            s.arrow(a, out, { head: false }).arrow(out, down, { head: false }).arrow(down, { x: a.x, y: down.y });
            s.text(m.label || '', { x: a.x + 0.45, y: y - 0.05, w: colW * 0.9, h: step * 0.5 }, { size: SIZE.small });
          } else {
            s.arrow(a, { x: cx(m.to), y }, { label: m.label, dash: !!m.reply });
          }
        });
        return s;
      },
      // min: minutes this slide takes; say: what the speaker says; ask: a
      // question for the audience; table: rows moved off the slide; open:
      // unverified claims, kept as open questions.
      notes(n) {
        rec.notes = n;
        return s;
      },
    };

    raw.addText(String(title), Object.assign({}, TITLE_BOX, {
      fontFace: fonts.body, fontSize: SIZE.title, bold: true, color: pal.text, valign: 'middle',
    }));
    if (!sOpts.noFitCheck && lineCount(title, SIZE.title, TITLE_BOX.w - PAD_W) > LIMITS.titleMaxLines) {
      warn('title-wraps', `title "${title}" estimated to wrap at ${SIZE.title}pt`);
    }
    if (footer) {
      raw.addText(footer, {
        x: 0.5, y: 7.05, w: SLIDE_W - 2, h: 0.3, fontFace: fonts.body, fontSize: SIZE.footer, color: pal.muted,
      });
    }
    raw.slideNumber = {
      x: SLIDE_W - 1.2, y: 7.05, w: 0.7, h: 0.3, fontFace: fonts.body, fontSize: SIZE.footer, color: pal.muted, align: 'right',
    };
    return s;
  }

  return {
    pptx,
    slide: makeSlide,
    // Slides after this call count towards this section's agenda minutes;
    // slides before the first section count towards the first.
    section(name) {
      sections.push(name);
    },
    // The agenda's rows are filled in by write(), from every slide's `min`.
    agenda(title = 'Agenda', sOpts = {}) {
      agendaSlide = makeSlide(title, sOpts);
      return agendaSlide;
    },
    // Writes the file and returns the warnings: { slide (null for the deck),
    // kind, message }. Each is also printed, so a build cannot drop them.
    async write(file) {
      const mins = sections.map(() => 0);
      let total = 0;
      for (const rec of slides) {
        const n = rec.notes || {};
        const missing = [typeof n.min === 'number' ? null : 'min', n.say ? null : 'say'].filter(Boolean);
        if (missing.length) warnings.push({ slide: rec.n, kind: 'notes', message: `notes missing ${missing.join(' and ')}` });
        if (rec.notes) rec.raw.addNotes(notesText(rec.notes));
        const m = typeof n.min === 'number' ? n.min : 0;
        total += m;
        if (mins.length) mins[rec.section] += m;
      }
      if (agendaSlide) {
        const rows = sections.map((name, i) => [name, `${mins[i]} min`]).concat([['Total', `${total} min`]]);
        agendaSlide.table(rows, { x: 1.5, y: 1.4, w: 10.333, h: 5.4 }, { header: false, size: 18, colW: [8.333, 2] });
      }
      if (opts.minutes && Math.abs(total - opts.minutes) > opts.minutes * LIMITS.planTolerance) {
        warnings.push({ slide: null, kind: 'plan', message: `slides total ${total} min against a plan of ${opts.minutes} min` });
      }
      await pptx.writeFile({ fileName: file });
      for (const w of warnings) console.warn(`deckkit: ${w.slide ? `slide ${w.slide}: ` : ''}${w.kind}: ${w.message}`);
      return warnings;
    },
  };
}

module.exports = { deck, LIMITS, PPTXGENJS_VERSION };
