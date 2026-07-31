"""Turn `chkbox:` and `note:` link anchors in a Chrome-printed PDF into form fields.

Chrome's --print-to-pdf flattens HTML form controls into static ink. This script
replaces them with AcroForm widgets, so the decision boxes are clickable and the
reword notes typable in any PDF viewer, and the box copies in the index table
and on the comment card stay in sync.

Authoring contract: in the HTML, write each decision box and reword note as

    <a class="box" href="chkbox:C1.publish"></a>
    <a class="note" href="note:C1"></a>

The chkbox anchor's id is `<field>.<state>`. Every anchor sharing a field id
becomes one radio group -- so `C1.publish` and `C1.drop` are mutually exclusive,
and the two `C1.publish` anchors (index table and comment card) are two widgets
of one field, checked and cleared in unison. A `note:C1` anchor becomes a
multiline text field named `C1_note`, where the user writes how C1 should be
reworded; a later run reads it back with --read and rewrites the comment.

Chrome emits each anchor as a link annotation carrying its exact rectangle; this
script reads those rectangles, drops the links, and writes widgets in their
place via an incremental update, leaving the original bytes untouched.

Usage: python pdf_forms.py dossier.pdf            # rewrites in place
       python pdf_forms.py in.pdf out.pdf
       python pdf_forms.py --read filled.pdf      # decisions + notes as JSON

No third-party dependencies. The write path assumes only what Chrome emits: a
classic xref table with uncompressed object dictionaries. The read path also
unpacks /ObjStm object streams, because saving the filled form from any viewer
rewrites the file that way.
"""

import binascii
import json
import re
import sys
import zlib

# Button field flags (PDF 32000-1 table 226).
RADIO = 1 << 15
RADIOS_IN_UNISON = 1 << 25  # same on-state name => widgets toggle together
FLAGS = RADIO | RADIOS_IN_UNISON  # NoToggleToOff left clear, so a box can be cleared
MULTILINE = 1 << 12  # text field flag: wrap instead of one long line

NOTE_SUFFIX = "_note"  # a period would make it a child field in PDF's name tree

OBJ_RE = re.compile(rb"(\d+)\s+0\s+obj\b(.*?)\bendobj", re.S)
URI_RE = re.compile(rb"/URI\s*\((chkbox|note):([A-Za-z0-9_.-]+)\)")
RECT_RE = re.compile(rb"/Rect\s*\[([^\]]*)\]")
ANNOTS_RE = re.compile(rb"/Annots\s*\[([^\]]*)\]")


def parse_objects(data):
    return {int(m.group(1)): (m.start(), m.group(2)) for m in OBJ_RE.finditer(data)}


def find_anchors(objects):
    """anchor object number -> (kind, field, state, rect string).

    kind is "box" (state is the radio on-state) or "note" (state is None).
    """
    out = {}
    for num, (_, body) in objects.items():
        uri = URI_RE.search(body)
        rect = RECT_RE.search(body)
        if not (uri and rect and b"/Link" in body):
            continue
        scheme, name = uri.group(1).decode(), uri.group(2).decode()
        if scheme == "note":
            out[num] = ("note", name + NOTE_SUFFIX, None, rect.group(1).strip())
        else:
            field, _, state = name.partition(".")
            if field and state:
                out[num] = ("box", field, state.capitalize(), rect.group(1).strip())
    return out


def page_numbers(objects):
    return [n for n, (_, body) in objects.items() if re.search(rb"/Type\s*/Page[^s]", body)]


def appearance(width, height, checked):
    """Appearance stream for one widget state.

    The box outline is already drawn by the page's CSS border, so the off state
    paints nothing and the on state paints only a ZapfDingbats check mark.
    """
    if checked:
        size = max(height * 0.78, 4.0)
        x, y = width * 0.16, height * 0.22
        ops = f"/Tx BMC q BT /ZaDb {size:.2f} Tf 0 g {x:.2f} {y:.2f} Td (4) Tj ET Q EMC"
    else:
        ops = "/Tx BMC EMC"
    body = ops.encode()
    return (
        b"<< /Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 %.2f %.2f]"
        b" /Resources << /ProcSet [/PDF /Text] /Font << /ZaDb %d 0 R >> >>"
        b" /Length %d >>\nstream\n%s\nendstream" % (width, height, ZADB[0], len(body), body)
    )


ZADB = [0]  # object number, filled in by convert()
HELV = [0]


def convert(src, dst):
    data = open(src, "rb").read()
    objects = parse_objects(data)
    anchors = find_anchors(objects)
    if not anchors:
        raise SystemExit("no chkbox:/note: anchors found -- was the HTML written with them?")

    root = int(re.search(rb"/Root\s+(\d+)\s+0\s+R", data[data.rfind(b"trailer"):]).group(1))
    prev = int(re.search(rb"startxref\s+(\d+)", data[data.rfind(b"startxref"):]).group(1))
    next_num = int(re.search(rb"/Size\s+(\d+)", data[data.rfind(b"trailer"):]).group(1))

    def alloc():
        nonlocal next_num
        next_num += 1
        return next_num - 1

    new = {}  # object number -> body bytes
    ZADB[0] = alloc()
    new[ZADB[0]] = b"<< /Type /Font /Subtype /Type1 /BaseFont /ZapfDingbats /Name /ZaDb >>"
    HELV[0] = alloc()
    new[HELV[0]] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica"
        b" /Encoding /WinAnsiEncoding /Name /Helv >>"
    )

    # Which page holds each anchor, so the widget lands on the right page.
    page_of, page_annots = {}, {}
    for pnum in page_numbers(objects):
        _, body = objects[pnum]
        m = ANNOTS_RE.search(body)
        refs = [int(r) for r in re.findall(rb"(\d+)\s+0\s+R", m.group(1))] if m else []
        page_annots[pnum] = [r for r in refs if r not in anchors]
        for r in refs:
            if r in anchors:
                page_of[r] = pnum

    # One field per name, its widgets as kids. Notes get the same treatment as
    # boxes because a note block split by a page break arrives as two rects.
    fields, notes = {}, {}
    for _, (kind, name, _, _) in sorted(anchors.items()):
        target = notes if kind == "note" else fields
        target.setdefault(name, alloc())

    kids = {name: [] for name in list(fields) + list(notes)}
    for anum, (kind, field, state, rect) in sorted(anchors.items()):
        if kind == "note":
            wnum = alloc()
            new[wnum] = (
                b"<< /Type /Annot /Subtype /Widget /Rect [%s] /Parent %d 0 R"
                b" /F 4 /MK << >> >>" % (rect, notes[field])
            )
            kids[field].append(wnum)
        else:
            x0, y0, x1, y1 = (float(v) for v in rect.split())
            w, h = x1 - x0, y1 - y0
            on_ref, off_ref = alloc(), alloc()
            new[on_ref] = appearance(w, h, True)
            new[off_ref] = appearance(w, h, False)
            wnum = alloc()
            new[wnum] = (
                b"<< /Type /Annot /Subtype /Widget /FT /Btn /Ff %d /Rect [%s]"
                b" /Parent %d 0 R /F 4 /AS /Off /MK << >> /DA (/ZaDb 0 Tf 0 g)"
                b" /AP << /N << /%s %d 0 R /Off %d 0 R >> >> >>"
                % (FLAGS, rect, fields[field], state.encode(), on_ref, off_ref)
            )
            kids[field].append(wnum)
        page_annots[page_of[anum]].append(wnum)

    for name, fnum in fields.items():
        refs = b" ".join(b"%d 0 R" % k for k in kids[name])
        new[fnum] = (
            b"<< /FT /Btn /Ff %d /T (%s) /V /Off /DA (/ZaDb 0 Tf 0 g) /Kids [%s] >>"
            % (FLAGS, name.encode(), refs)
        )

    for name, fnum in notes.items():
        refs = b" ".join(b"%d 0 R" % k for k in kids[name])
        new[fnum] = (
            b"<< /FT /Tx /Ff %d /T (%s) /V () /DA (/Helv 8 Tf 0 g) /Kids [%s] >>"
            % (MULTILINE, name.encode(), refs)
        )

    acro = alloc()
    # NeedAppearances makes viewers lay out typed note text themselves; without
    # it a note keeps whatever appearance stream it was born with (none).
    new[acro] = (
        b"<< /Fields [%s] /NeedAppearances true /DA (/Helv 8 Tf 0 g)"
        b" /DR << /Font << /ZaDb %d 0 R /Helv %d 0 R >> >> >>"
        % (
            b" ".join(b"%d 0 R" % f for f in list(fields.values()) + list(notes.values())),
            ZADB[0],
            HELV[0],
        )
    )

    # Rewrite the pages (swap link annots for widgets) and the catalog (add /AcroForm).
    for pnum, refs in page_annots.items():
        _, body = objects[pnum]
        arr = b"/Annots [%s]" % b" ".join(b"%d 0 R" % r for r in refs)
        new[pnum] = ANNOTS_RE.sub(arr, body) if ANNOTS_RE.search(body) else _insert(body, arr)
    new[root] = _insert(objects[root][1], b"/AcroForm %d 0 R" % acro)

    out = bytearray(data)
    if not out.endswith(b"\n"):
        out += b"\n"
    offsets = {}
    for num in sorted(new):
        offsets[num] = len(out)
        out += b"%d 0 obj\n" % num + new[num] + b"\nendobj\n"

    start = len(out)
    out += b"xref\n"
    for first, group in _subsections(sorted(offsets)):
        out += b"%d %d\n" % (first, len(group))
        for num in group:
            out += b"%010d %05d n \n" % (offsets[num], 0)
    out += b"trailer\n<< /Size %d /Root %d 0 R /Prev %d >>\nstartxref\n%d\n%%%%EOF\n" % (
        next_num, root, prev, start
    )
    open(dst, "wb").write(bytes(out))
    boxes = sum(1 for kind, _, _, _ in anchors.values() if kind == "box")
    print(
        f"{boxes} boxes in {len(fields)} synced groups, "
        f"{len(notes)} reword notes -> {dst}"
    )


def _insert(body, entry):
    i = body.rstrip().rfind(b">>")
    return body[:i] + b" " + entry + b" " + body[i:]


def _scan_string(body, i):
    """The PDF string starting at body[i] -- literal `(...)` or hex `<...>`."""
    if body[i : i + 1] == b"<":
        digits = re.sub(rb"\s", b"", body[i + 1 : body.index(b">", i)])
        return binascii.unhexlify(digits + b"0" * (len(digits) % 2))
    escapes = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f"}
    out, depth, j = bytearray(), 1, i + 1
    while j < len(body) and depth:
        c = body[j : j + 1]
        if c == b"\\":
            octal = re.match(rb"[0-7]{1,3}", body[j + 1 : j + 4])
            if octal:
                out.append(int(octal.group(), 8) & 0xFF)
                j += 1 + len(octal.group())
            elif body[j + 1 : j + 2] in (b"\n", b"\r"):  # line continuation
                j += 2
            else:
                out += escapes.get(body[j + 1 : j + 2], body[j + 1 : j + 2])
                j += 2
            continue
        if c == b"(":
            depth += 1
        elif c == b")":
            depth -= 1
            if not depth:
                break
        out += c
        j += 1
    return bytes(out)


def _entry(body, key):
    """Value of /key in a dictionary body, as (kind, text) or None."""
    for m in re.finditer(rb"/" + key.encode() + rb"\b\s*", body):
        j = m.end()
        head = body[j : j + 2]
        if head[:1] == b"/":
            token = re.match(rb"/([^\s/\[\]<>()]*)", body[j:]).group(1)
            return ("name", token.decode("latin-1"))
        if head[:1] == b"(" or (head[:1] == b"<" and head != b"<<"):
            raw = _scan_string(body, j)
            if raw.startswith(b"\xfe\xff"):
                return ("str", raw[2:].decode("utf-16-be", "replace"))
            return ("str", raw.decode("latin-1"))
    return None


def _objstm_contents(offset, body):
    """Objects packed inside a /Type /ObjStm stream: [(offset, num, body), ...].

    Viewers that re-save a form (Chrome, Edge, Acrobat all do) rewrite the file
    with the field dictionaries compressed into object streams, so a --read that
    only scans for `N 0 obj` finds nothing. Every unpacked object inherits the
    containing stream's file offset, which is what orders it against the rest.
    """
    if b"/ObjStm" not in body:
        return []
    m = re.search(rb"stream\r?\n", body)
    if not m:
        return []
    try:
        raw = zlib.decompress(body[m.end() : body.find(b"endstream", m.end())])
        n = int(re.search(rb"/N\s+(\d+)", body).group(1))
        first = int(re.search(rb"/First\s+(\d+)", body).group(1))
    except Exception:  # not Flate, or a malformed header -- skip the stream
        return []
    head = raw[:first].split()
    pairs = [(int(head[i]), int(head[i + 1])) for i in range(0, 2 * n, 2)]
    out = []
    for i, (num, start) in enumerate(pairs):
        stop = first + (pairs[i + 1][1] if i + 1 < len(pairs) else len(raw) - first)
        out.append((offset, num, raw[first + start : stop]))
    return out


def _latest_objects(data):
    """obj number -> body, with the definition latest in the file winning.

    An incremental save appends, so file order is revision order. Objects lifted
    out of an /ObjStm are ordered by the stream's own offset.
    """
    entries = []
    for m in OBJ_RE.finditer(data):
        entries.append((m.start(), int(m.group(1)), m.group(2)))
        entries.extend(_objstm_contents(m.start(), m.group(2)))
    return {num: body for _, num, body in sorted(entries, key=lambda e: e[0])}


def _widget_states(latest, body):
    """On-states of a field's kid widgets -- the appearance the viewer renders."""
    kids = re.search(rb"/Kids\s*\[([^\]]*)\]", body)
    if not kids:
        return []
    states = []
    for ref in re.findall(rb"(\d+)\s+\d+\s+R", kids.group(1)):
        state = _entry(latest.get(int(ref), b""), "AS")
        if state and state[1] != "Off":
            states.append(state[1])
    return sorted(set(states))


def read(path):
    """Print the decisions and reword notes a filled-in dossier carries, as JSON."""
    data = open(path, "rb").read()
    latest = _latest_objects(data)

    out, disagree = {}, []
    for body in latest.values():
        name = _entry(body, "T")
        if not name or name[0] != "str":
            continue
        value = _entry(body, "V")
        cid, is_note = name[1], name[1].endswith(NOTE_SUFFIX)
        if is_note:
            cid = cid[: -len(NOTE_SUFFIX)]
        rec = out.setdefault(cid, {"decision": None, "note": ""})
        if is_note:
            rec["note"] = value[1].strip() if value and value[0] == "str" else ""
            continue
        if value and value[1] != "Off":
            rec["decision"] = value[1]
        # Cross-check /V against what the widgets actually paint. A field whose
        # value and appearance disagree means the parse is wrong, or the viewer
        # left the file inconsistent -- either way, do not report a decision.
        states = _widget_states(latest, body)
        if states != ([rec["decision"]] if rec["decision"] else []):
            disagree.append(f"  {cid}: /V={rec['decision']} but widgets show {states}")

    if not out:
        raise SystemExit(
            f"no form fields in {path} -- it was probably never run through this "
            "script; run `python pdf_forms.py {path}` on the Chrome-printed PDF first"
        )
    if disagree:
        raise SystemExit(
            "field values and widget appearances disagree -- refusing to guess:\n"
            + "\n".join(disagree)
        )

    def key(cid):  # C10 sorts after C9, not between C1 and C2
        m = re.search(r"\d+$", cid)
        return (cid[: m.start()] if m else cid, int(m.group()) if m else 0)

    print(json.dumps({k: out[k] for k in sorted(out, key=key)}, indent=2))
    if all(r["decision"] is None for r in out.values()):
        print(
            "warning: nothing is ticked -- ticks live only in a copy saved from the "
            "PDF viewer, so check you were handed the saved file",
            file=sys.stderr,
        )


def _subsections(nums):
    runs, run = [], [nums[0]]
    for n in nums[1:]:
        if n == run[-1] + 1:
            run.append(n)
        else:
            runs.append((run[0], run))
            run = [n]
    runs.append((run[0], run))
    return runs


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--read":
        read(args[1])
    else:
        convert(args[0], args[1] if len(args) > 1 else args[0])
