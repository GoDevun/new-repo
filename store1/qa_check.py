#!/usr/bin/env python3
"""Quinn, QA agent: automated checks against store1/SPEC.md.

Usage: python3 store1/qa_check.py [product_dir ...]   (defaults to every product)
Exit code 1 if any product fails.
"""
import re, sys, glob, os
from pypdf import PdfReader

MARGIN_PT = 36 * 0.95  # 0.5 in, with a small tolerance
SIZES = {"US-Letter": (612, 792), "A4": (595.28, 841.89)}
BANNED = re.compile(r"\b(recipe|knitting pattern|crochet pattern|sewing pattern|disney|marvel|nike|harry potter|taylor swift)\b", re.I)


def fonts_embedded(page):
    bad = []
    res = page.get("/Resources") or {}
    fonts = res.get("/Font") or {}
    for name, ref in fonts.items():
        f = ref.get_object()
        desc = f.get("/FontDescriptor")
        if f.get("/Subtype") == "/Type0":
            desc = f["/DescendantFonts"][0].get_object().get("/FontDescriptor")
        if desc is None:
            bad.append(str(f.get("/BaseFont")))
            continue
        d = desc.get_object()
        if not any(k in d for k in ("/FontFile", "/FontFile2", "/FontFile3")):
            bad.append(str(f.get("/BaseFont")))
    return bad


def text_bounds_ok(reader, w, h):
    """Return pages whose text starts inside the 0.5 in margin."""
    offenders = []
    for i, page in enumerate(reader.pages, 1):
        hits = []

        def visit(text, cm, tm, fd, fs):
            if not text.strip():
                return
            x = cm[0] * tm[4] + cm[2] * tm[5] + cm[4]
            y = cm[1] * tm[4] + cm[3] * tm[5] + cm[5]
            if x < MARGIN_PT or y < MARGIN_PT * 0.6 or x > w - MARGIN_PT or y > h - MARGIN_PT:
                hits.append((round(x), round(y), text.strip()[:20]))

        page.extract_text(visitor_text=visit)
        if hits:
            offenders.append((i, hits[:3]))
    return offenders


def check(d):
    slug = os.path.basename(d.rstrip("/"))
    errs, notes = [], []
    pagecounts = {}
    for label, (w, h) in SIZES.items():
        f = os.path.join(d, f"{slug}-{label}.pdf")
        if not os.path.exists(f):
            errs.append(f"missing {os.path.basename(f)}")
            continue
        r = PdfReader(f)
        pagecounts[label] = len(r.pages)
        for i, p in enumerate(r.pages, 1):
            pw, ph = float(p.mediabox.width), float(p.mediabox.height)
            if abs(pw - w) > 2 or abs(ph - h) > 2:
                errs.append(f"{label} p{i} size {pw:.0f}x{ph:.0f}, expected {w:.0f}x{h:.0f}")
                break
        nf = set()
        for p in r.pages:
            nf.update(fonts_embedded(p))
        if nf:
            errs.append(f"{label}: fonts not embedded: {sorted(nf)}")
        off = text_bounds_ok(r, w, h)
        if off:
            notes.append(f"{label}: text near/inside margin on pages {[o[0] for o in off]} e.g. {off[0][1][0]}")
        txt = " ".join((p.extract_text() or "") for p in r.pages)
        if BANNED.search(txt):
            errs.append(f"{label}: banned term '{BANNED.search(txt).group(0)}'")
    if len(set(pagecounts.values())) > 1:
        errs.append(f"page counts differ between sizes: {pagecounts}")

    previews = glob.glob(os.path.join(d, "previews", "*.png"))
    if len(previews) < 5:
        errs.append(f"only {len(previews)} preview images (need 5+)")

    lf = os.path.join(d, "listing.md")
    if not os.path.exists(lf):
        errs.append("missing listing.md")
    else:
        L = open(lf).read()
        title = (re.search(r"^#\s+(.+)$", L, re.M) or [None, ""])[1].strip()
        if not title or len(title) > 140:
            errs.append(f"title length {len(title)} (max 140)")
        if title and title.isupper():
            errs.append("title is ALL CAPS")
        m = re.search(r"Tags[^:]*:\s*(.+)", L)
        tags = [t.strip() for t in m.group(1).split(",")] if m else []
        if len(tags) != 13:
            errs.append(f"{len(tags)} tags (need 13)")
        long = [t for t in tags if len(t) > 20]
        if long:
            errs.append(f"tags over 20 chars: {long}")
        if not re.search(r"^Price:\s*\$\d", L, re.M):
            errs.append("no price line")
        if "AI disclosure" not in L:
            errs.append("no AI disclosure section")
        if BANNED.search(L):
            errs.append(f"listing has banned term '{BANNED.search(L).group(0)}'")
        if pagecounts:
            n = list(pagecounts.values())[0]
            mm = re.search(r"(\d+)[ -]page", L)
            if mm and int(mm.group(1)) != n:
                errs.append(f"listing says {mm.group(1)} pages but PDF has {n}")
    return slug, errs, notes, pagecounts


def main():
    dirs = sys.argv[1:] or sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "products", "*/")))
    failed = False
    for d in dirs:
        slug, errs, notes, pc = check(d)
        status = "FAIL" if errs else "PASS"
        failed |= bool(errs)
        print(f"[{status}] {slug}  pages={pc}")
        for e in errs:
            print("   x", e)
        for n in notes:
            print("   ~", n)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
