# Review queue: approved by Devun (2026-11-21)

Nothing is listed on Etsy until it is approved here. To approve a product, change `[ ]` to `[x]` or tell Claude "approve <slug>".

| ✓ | Product | Pages | Price | QA | Folder |
|---|---|---|---|---|---|
| [x] | ADHD-friendly daily & weekly planner | 12 | $5.50 | PASS | `products/adhd-daily-planner/` |
| [x] | Paycheck-to-paycheck budget kit | 12 | $6.50 | PASS | `products/paycheck-budget-kit/` |
| [x] | Small business order & inventory planner | 11 | $7.00 | PASS | `products/small-business-planner/` |

## Before approving, check
- Shop name: "Quiet Desk Printables" is a placeholder in every page footer. Rename it, then rebuild with `python3 build.py` in each folder.
- Each `listing.md` carries the AI disclosure Etsy requires. Keep it when you paste the listing.

## Known polish items (not blockers)
- Previews show US Letter pages only; none show the A4 version.
- ADHD planner: mood-tracker circles are tight (4.4 mm).
- Budget kit: one paycheck per page, so biweekly buyers print it twice a month.
- Small business planner: A4 pricing worksheet has spare space at the bottom.
