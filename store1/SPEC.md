# Store 1 — Etsy digital downloads: product spec

Every product follows this spec. QA rejects anything that misses a line.

## Files per product (`store1/products/<slug>/`)
- `build.py` — reproducible generator (reportlab). Running `python3 build.py` from that folder rebuilds everything.
- `<slug>-US-Letter.pdf` (8.5 × 11 in) and `<slug>-A4.pdf` (210 × 297 mm). Both sizes are mandatory.
- `previews/` — PNG listing images rendered from the real PDF pages (2000 px on the long side). At least 5:
  1. cover/hero image (shows the product, product name, page count, "Instant download · US Letter + A4")
  2–4. real page previews
  5. "What's included" image listing every page
- `listing.md` — title, price, 13 tags, description, AI disclosure, file list (format below).

## Design rules
- Fonts: only TrueType fonts with resale-safe licences already on this machine: Carlito (OFL), Caladea (Apache 2.0), Liberation (OFL), JetBrains Mono (OFL), DejaVu. reportlab cannot embed CFF `.otf` files.
- Print-first: white background, no full-page colour fills, ink-light accents, ≥ 0.5 in (12.7 mm) margins on every side so home printers don't clip.
- Write-in areas must be usable by hand: lines ≥ 7 mm apart, checkboxes ≥ 4 mm.
- No copyrighted characters, brand names, trademarked phrases or celebrity references.
- No instructions/recipes/patterns (banned for AI-made items on Etsy). Short "how to use this page" hints are fine.
- Shop brand (placeholder until Devun names the shop): small footer `Quiet Desk Printables · personal use only` on every page.

## listing.md format
```
# Title (≤ 140 chars, keywords first, no ALL CAPS)
Price: $X.XX
Tags (13, each ≤ 20 chars): tag1, tag2, ...
## Description
...(what it is, who it's for, page list, sizes, how to print, personal-use licence, "digital download: no physical item ships")
## AI disclosure
"Designed by the shop owner with AI tools assisting layout and copy; every file reviewed and approved by a person before listing."
## Files
- list of PDFs buyers receive
```

## QA checklist
Both sizes exist · page count matches description · nothing touches the 0.5 in margin · no text overflow · spelling · fonts embedded · previews come from real pages · 13 tags ≤ 20 chars · title ≤ 140 chars · AI disclosure present · no banned content.
