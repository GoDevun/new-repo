#!/usr/bin/env python3
"""Reproducible generator: Small Business Order & Inventory Planner.
Run `python3 build.py` from this folder. Produces US Letter + A4 PDFs and previews/.
"""
import os, subprocess, glob, shutil, tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import mm, inch
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth

HERE = os.path.dirname(os.path.abspath(__file__))
SLUG = "small-business-planner"
CX = "/usr/share/fonts/truetype/crosextra/"
for name, f in [("Head", "Caladea-Bold.ttf"), ("HeadReg", "Caladea-Regular.ttf"),
                ("HeadIt", "Caladea-Italic.ttf"), ("Body", "Carlito-Regular.ttf"),
                ("BodyB", "Carlito-Bold.ttf"), ("BodyI", "Carlito-Italic.ttf")]:
    pdfmetrics.registerFont(TTFont(name, CX + f))

# Palette: warm charcoal ink, one terracotta accent, pale tints
INK = HexColor("#3B3632")
SOFT = HexColor("#8A817A")
RULE = HexColor("#B9B0A8")
FAINT = HexColor("#DDD6CF")
ACC = HexColor("#B4654A")
TINT = HexColor("#F6EBE5")
BRAND = "Quiet Desk Printables · personal use only"
TITLE = "Small Business Planner"

M = 0.6 * inch          # page margin (spec minimum 0.5 in)
ROW = 8 * mm            # write-in row height (spec >= 7 mm)
BOX = 4.4 * mm          # checkbox size (spec >= 4 mm)

PAGES = []              # (title, function)


def page(title):
    def deco(fn):
        PAGES.append((title, fn))
        return fn
    return deco


def fit(text, font, size, maxw, minsize=6):
    while size > minsize and stringWidth(text, font, size) > maxw:
        size -= 0.25
    return size


class P:
    """Page context with top-down helpers."""
    def __init__(self, c, size):
        self.c = c
        self.W, self.H = size
        self.x0, self.x1 = M, self.W - M
        self.w = self.x1 - self.x0
        self.top = self.H - M
        self.bottom = M + 7 * mm      # leave room for footer

    def header(self, title, hint=None, field=None):
        c = self.c
        y = self.top - 20
        c.setFillColor(INK); c.setFont("Head", 22)
        c.drawString(self.x0, y, title)
        if field:
            c.setFont("Body", 9.5); c.setFillColor(SOFT)
            fw = 48 * mm
            lx = self.x1 - fw
            c.drawRightString(lx - 3, y, field)
            c.setStrokeColor(RULE); c.setLineWidth(0.6)
            c.line(lx, y - 2, self.x1, y - 2)
        y -= 9
        c.setStrokeColor(ACC); c.setLineWidth(1.6)
        c.line(self.x0, y, self.x0 + 22 * mm, y)
        c.setStrokeColor(FAINT); c.setLineWidth(0.6)
        c.line(self.x0 + 22 * mm, y, self.x1, y)
        y -= 13
        if hint:
            c.setFont("BodyI", 9); c.setFillColor(SOFT)
            c.drawString(self.x0, y, hint)
            y -= 10
        return y - 4

    def footer(self, n):
        c = self.c
        c.setFont("Body", 7.5); c.setFillColor(SOFT)
        c.drawString(self.x0, M + 1, BRAND)
        c.drawRightString(self.x1, M + 1, f"{TITLE}  ·  {n}")

    def checkbox(self, x, y, s=BOX):
        c = self.c
        c.saveState()
        c.setStrokeColor(SOFT); c.setLineWidth(0.7)
        c.roundRect(x, y, s, s, 0.7, stroke=1, fill=0)
        c.restoreState()

    def section(self, x, y, label, w=None):
        c = self.c
        c.setFillColor(ACC); c.setFont("BodyB", 9.5)
        c.drawString(x, y - 9, label.upper())
        return y - 15

    def field_line(self, x, y, w, label, size=9):
        c = self.c
        c.setFont("Body", size); c.setFillColor(SOFT)
        c.drawString(x, y + 2.5, label)
        lw = stringWidth(label, "Body", size) + 4
        c.setStrokeColor(RULE); c.setLineWidth(0.6)
        c.line(x + lw, y, x + w, y)

    def lines(self, x, y, w, n, step=ROW):
        c = self.c
        c.setStrokeColor(RULE); c.setLineWidth(0.5)
        for i in range(n):
            y -= step
            c.line(x, y, x + w, y)
        return y

    def table(self, y, cols, rows=None, x=None, w=None, head_h=9 * mm, row_h=ROW,
              boxes=(), bottom=None, total_row=None, first_col_labels=None):
        """cols: list of (label, weight). Fills down to bottom unless rows given."""
        c = self.c
        x = self.x0 if x is None else x
        w = self.w if w is None else w
        bottom = self.bottom if bottom is None else bottom
        if rows is None:
            avail = y - head_h - bottom - (row_h if total_row else 0)
            rows = int(avail // row_h)
        tw = sum(wt for _, wt in cols)
        widths = [w * wt / tw for _, wt in cols]
        # header
        c.setFillColor(TINT); c.setStrokeColor(TINT)
        c.rect(x, y - head_h, w, head_h, stroke=0, fill=1)
        c.setFillColor(INK)
        cx = x
        for (label, _), cw in zip(cols, widths):
            s = fit(label, "BodyB", 8.5, cw - 6)
            c.setFont("BodyB", s)
            if label and cols.index((label, _)) in boxes:
                c.drawCentredString(cx + cw / 2, y - head_h / 2 - 3, label)
            else:
                c.drawString(cx + 4, y - head_h / 2 - 3, label)
            cx += cw
        yb = y - head_h
        n = rows + (1 if total_row else 0)
        ybot = yb - n * row_h
        # rows
        c.setStrokeColor(RULE); c.setLineWidth(0.5)
        for i in range(1, n + 1):
            yy = yb - i * row_h
            c.line(x, yy, x + w, yy)
        c.setStrokeColor(FAINT); c.setLineWidth(0.5)
        cx = x
        for cw in widths[:-1]:
            cx += cw
            c.line(cx, y - head_h, cx, ybot)
        c.setStrokeColor(ACC); c.setLineWidth(0.9)
        c.line(x, y - head_h, x + w, y - head_h)
        # checkboxes
        for bi in boxes:
            bx = x + sum(widths[:bi]) + widths[bi] / 2 - BOX / 2
            for i in range(rows):
                by = yb - (i + 1) * row_h + (row_h - BOX) / 2
                self.checkbox(bx, by)
        if first_col_labels:
            c.setFont("Body", 9); c.setFillColor(INK)
            for i, lab in enumerate(first_col_labels[:rows]):
                c.drawString(x + 4, yb - (i + 1) * row_h + row_h / 2 - 3, lab)
        if total_row:
            ty = ybot
            c.setStrokeColor(ACC); c.setLineWidth(0.9)
            c.line(x, ty + row_h, x + w, ty + row_h)
            c.setFont("BodyB", 9); c.setFillColor(ACC)
            c.drawString(x + 4, ty + row_h / 2 - 3, total_row)
        return ybot, rows


# ---------------------------------------------------------------- pages
@page("Cover")
def p_cover(p):
    c = p.c
    # thin double frame
    c.setStrokeColor(ACC); c.setLineWidth(1.2)
    c.rect(p.x0, p.bottom, p.w, p.top - p.bottom)
    c.setStrokeColor(FAINT); c.setLineWidth(0.6)
    c.rect(p.x0 + 6, p.bottom + 6, p.w - 12, p.top - p.bottom - 12)
    cx = p.W / 2
    y = p.top - (p.top - p.bottom) * 0.30
    c.setFillColor(ACC); c.setFont("BodyB", 11)
    c.drawCentredString(cx, y + 46, "O R D E R S   ·   I N V E N T O R Y   ·   I N C O M E")
    c.setFillColor(INK); c.setFont("Head", 44)
    c.drawCentredString(cx, y, "Small Business")
    c.drawCentredString(cx, y - 50, "Planner")
    c.setStrokeColor(ACC); c.setLineWidth(1.4)
    c.line(cx - 18 * mm, y - 72, cx + 18 * mm, y - 72)
    c.setFont("HeadIt", 14); c.setFillColor(SOFT)
    c.drawCentredString(cx, y - 96, "for handmade makers & small online shops")
    # write-in fields
    fy = y - 170
    fw = 110 * mm
    for lab in ("Business name", "Year", "Owner"):
        p.field_line(cx - fw / 2, fy, fw, lab, size=11)
        fy -= 13 * mm
    # contents
    fy -= 6 * mm
    c.setFont("BodyB", 9.5); c.setFillColor(ACC)
    c.drawCentredString(cx, fy, "INSIDE")
    fy -= 15
    names = [t for t, _ in PAGES[1:]]
    half = (len(names) + 1) // 2
    c.setFont("Body", 10); c.setFillColor(INK)
    colw = 72 * mm
    for i, nm in enumerate(names):
        col, r = divmod(i, half)
        xx = cx - colw + col * colw + 8 * mm
        c.drawString(xx, fy - r * 15, f"{i + 2:02d}   {nm}")


@page("Order Log")
def p_orders(p):
    y = p.header("Order Log", "One line per order. Tick the box once it ships.", "Month")
    p.table(y, [("Order #", 1.1), ("Date", 0.9), ("Customer", 2.0), ("Item", 2.4),
                ("Qty", 0.55), ("Price", 0.9), ("Shipped", 0.85)], boxes=(6,))


@page("Order Detail Forms")
def p_detail(p):
    c = p.c
    y = p.header("Order Details", "Two forms per sheet — cut on the dashed line or keep them together.")
    avail = y - p.bottom
    gap = 9 * mm
    fh = (avail - gap) / 2
    for k in range(2):
        top = y - k * (fh + gap)
        _detail_form(p, top, fh)
    cut = y - fh - gap / 2
    c.setDash(3, 3); c.setStrokeColor(RULE); c.setLineWidth(0.6)
    c.line(p.x0, cut, p.x1, cut); c.setDash()
    c.setFont("Body", 7); c.setFillColor(SOFT)
    c.drawRightString(p.x1, cut + 2, "✂ cut")


def _detail_form(p, top, fh):
    c = p.c
    x0, w = p.x0, p.w
    c.setStrokeColor(FAINT); c.setLineWidth(0.8)
    c.roundRect(x0, top - fh, w, fh, 4)
    pad = 4 * mm
    x = x0 + pad; ww = w - 2 * pad
    y = top - 7.5 * mm
    third = ww / 3
    p.field_line(x, y, third - 4 * mm, "Order #")
    p.field_line(x + third, y, third - 4 * mm, "Date")
    p.field_line(x + 2 * third, y, third, "Channel")
    colw = ww / 2 - 3 * mm
    xr = x + ww / 2 + 3 * mm
    y -= ROW
    yl = y; yr = y
    p.field_line(x, yl, colw, "Customer"); yl -= ROW
    p.field_line(x, yl, colw, "Email / phone"); yl -= ROW
    p.field_line(x, yl, colw, "Ship to"); yl -= ROW
    c.setStrokeColor(RULE); c.setLineWidth(0.6)
    c.line(x, yl, x + colw, yl); yl -= ROW
    c.line(x, yl, x + colw, yl)
    p.field_line(xr, yr, colw, "Item"); yr -= ROW
    p.field_line(xr, yr, colw * 0.5 - 2 * mm, "Size / color")
    p.field_line(xr + colw * 0.5, yr, colw * 0.5, "Qty"); yr -= ROW
    p.field_line(xr, yr, colw, "Personalization"); yr -= ROW
    p.field_line(xr, yr, colw * 0.5 - 2 * mm, "Price")
    p.field_line(xr + colw * 0.5, yr, colw * 0.5, "Shipping"); yr -= ROW
    p.field_line(xr, yr, colw, "Tracking #")
    y = min(yl, yr) - ROW
    p.field_line(x, y, ww, "Notes")
    # notes lines fill until status row
    status_y = top - fh + 4 * mm
    yy = y - ROW
    c.setStrokeColor(RULE); c.setLineWidth(0.5)
    while yy - ROW >= status_y + BOX:
        c.line(x, yy, x + ww, yy); yy -= ROW
    # status row
    sx = x
    c.setFont("BodyB", 9); c.setFillColor(INK)
    for lab in ("Paid", "Made", "Packed", "Shipped", "Reviewed"):
        p.checkbox(sx, status_y)
        c.drawString(sx + BOX + 2 * mm, status_y + 1.2 * mm, lab)
        sx += BOX + 2 * mm + stringWidth(lab, "BodyB", 9) + 9 * mm


@page("Inventory Tracker")
def p_inventory(p):
    y = p.header("Inventory Tracker", "Note your reorder point so you restock before you sell out.", "Updated")
    p.table(y, [("Item", 2.4), ("SKU", 1.1), ("Variation", 1.2), ("In stock", 0.85),
                ("Reorder at", 0.9), ("Supplier", 1.6), ("Reorder", 0.8)], boxes=(6,))


@page("Supply Purchase Log")
def p_supply(p):
    y = p.header("Supply & Material Purchases", "Track what you buy for your shop. Keep receipts with this page.", "Month")
    p.table(y, [("Date", 0.9), ("Supplier", 1.6), ("Material / item", 2.4), ("Qty", 0.6),
                ("Unit cost", 0.9), ("Total", 0.9), ("Receipt", 0.8)], boxes=(6,),
            total_row="Month total")


@page("Monthly Income & Expenses")
def p_month(p):
    c = p.c
    y = p.header("Monthly Income & Expenses", "Fill in your own figures for the month.", "Month")
    gap = 7 * mm
    lw = p.w * 0.56
    rx = p.x0 + lw + gap
    rw = p.w - lw - gap
    income = ["Product sales", "Shipping charged to buyers", "Other income"]
    exp = ["Platform & listing fees", "Payment processing fees", "Materials & supplies",
           "Packaging", "Shipping labels / postage", "Advertising", "Tools & equipment",
           "Software & subscriptions", "Other"]
    yy = p.section(p.x0, y, "Income")
    yy, _ = p.table(yy, [("Income", 3), ("Amount", 1.2)], rows=len(income), w=lw,
                    first_col_labels=income, total_row="Total income")
    yy = p.section(p.x0, yy - 5 * mm, "Expenses")
    yy, _ = p.table(yy, [("Expense", 3), ("Amount", 1.2)], rows=len(exp), w=lw,
                    first_col_labels=exp, total_row="Total expenses")
    # profit box
    yy -= 6 * mm
    bh = 15 * mm
    c.setStrokeColor(ACC); c.setLineWidth(1.1)
    c.roundRect(p.x0, yy - bh, lw, bh, 3)
    c.setFont("Head", 13); c.setFillColor(INK)
    c.drawString(p.x0 + 4 * mm, yy - bh / 2 - 4, "Profit")
    c.setFont("BodyI", 8.5); c.setFillColor(SOFT)
    c.drawString(p.x0 + 22 * mm, yy - bh / 2 - 3, "total income − total expenses")
    c.setStrokeColor(RULE); c.setLineWidth(0.6)
    c.line(p.x0 + lw - 38 * mm, yy - bh / 2 - 5, p.x0 + lw - 4 * mm, yy - bh / 2 - 5)
    # right column: weekly snapshot + notes
    ry = p.section(rx, y, "Weekly snapshot")
    ry, _ = p.table(ry, [("Week", 1), ("Orders", 1), ("Sales", 1.3)], rows=5, x=rx, w=rw,
                    first_col_labels=["Week 1", "Week 2", "Week 3", "Week 4", "Week 5"],
                    total_row="Total")
    ry = p.section(rx, ry - 5 * mm, "Best sellers this month")
    for i in range(3):
        ry -= ROW
        c.setFont("BodyB", 9); c.setFillColor(ACC)
        c.drawString(rx, ry + 2.5, f"{i + 1}.")
        c.setStrokeColor(RULE); c.setLineWidth(0.5)
        c.line(rx + 5 * mm, ry, rx + rw, ry)
    ry = p.section(rx, ry - 5 * mm, "Notes")
    n = int((ry - p.bottom) // ROW)
    p.lines(rx, ry, rw, n)


@page("Product Pricing Worksheet")
def p_pricing(p):
    c = p.c
    y = p.header("Product Pricing Worksheet", "Add up what one item really costs you, then choose your price.")
    hw = p.w / 2 - 3 * mm
    p.field_line(p.x0, y - 4, hw, "Product")
    p.field_line(p.x0 + p.w / 2 + 3 * mm, y - 4, hw, "SKU")
    y -= 10 * mm
    y = p.section(p.x0, y, "1  Materials")
    y, _ = p.table(y, [("Material", 3), ("Amount used", 1.2), ("Cost per unit", 1.2), ("Cost", 1)],
                   rows=6, total_row="Materials subtotal")
    y -= 5 * mm
    y = p.section(p.x0, y, "2  Time")
    y, _ = p.table(y, [("Task", 3), ("Minutes", 1.2), ("Hourly rate", 1.2), ("Cost", 1)],
                   rows=3, first_col_labels=["Making", "Packing & admin", ""],
                   total_row="Time subtotal")
    y -= 5 * mm
    y = p.section(p.x0, y, "3  Fees & extras")
    y, _ = p.table(y, [("Item", 5.4), ("Cost", 1)], rows=4,
                   first_col_labels=["Listing / platform fee", "Transaction & payment fees",
                                     "Packaging", "Other"],
                   total_row="Fees subtotal")
    y -= 6 * mm
    # summary boxes
    labels = ["Total cost per item", "Wholesale price", "Retail price", "Profit per item"]
    n = len(labels)
    g = 4 * mm
    bw = (p.w - g * (n - 1)) / n
    bh = min(22 * mm, y - p.bottom)
    for i, lab in enumerate(labels):
        bx = p.x0 + i * (bw + g)
        c.setStrokeColor(ACC if i in (2,) else RULE); c.setLineWidth(1.0)
        c.roundRect(bx, y - bh, bw, bh, 3)
        s = fit(lab, "BodyB", 9, bw - 6 * mm)
        c.setFont("BodyB", s); c.setFillColor(INK)
        c.drawString(bx + 3 * mm, y - 5.5 * mm, lab)
        c.setStrokeColor(RULE); c.setLineWidth(0.6)
        c.line(bx + 3 * mm, y - bh + 5 * mm, bx + bw - 3 * mm, y - bh + 5 * mm)


@page("Content Planner")
def p_content(p):
    c = p.c
    y = p.header("Content & Social Planner", "Plan a week of posts. Tick when the photo is ready and when it's live.", "Week of")
    hw = p.w / 2 - 3 * mm
    p.field_line(p.x0, y - 4, p.w, "This week's focus")
    y -= 10 * mm
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    rh = 2 * ROW
    ybot, _ = p.table(y, [("Day", 0.7), ("Platform", 1.3), ("Post idea / caption", 4.2),
                          ("Photo", 0.75), ("Posted", 0.75)], rows=7, row_h=rh, boxes=(3, 4))
    # middle rule inside caption column for two writing lines
    c.setStrokeColor(FAINT); c.setLineWidth(0.4)
    tw = 0.7 + 1.3 + 4.2 + 0.75 + 0.75
    xa = p.x0 + p.w * 0.7 / tw
    xb = p.x0 + p.w * (0.7 + 1.3 + 4.2) / tw
    yb = y - 9 * mm
    c.setFont("BodyB", 10); c.setFillColor(INK)
    for i, d in enumerate(days):
        r0 = yb - i * rh
        c.line(xa, r0 - rh / 2, xb, r0 - rh / 2)
        c.drawString(p.x0 + 4, r0 - rh / 2 - 3.5, d)
    yy = ybot - 6 * mm
    cw = p.w / 2 - 3 * mm
    ya = p.section(p.x0, yy, "Hashtags & keywords")
    yb2 = p.section(p.x0 + p.w / 2 + 3 * mm, yy, "Ideas for next week")
    n = int((ya - p.bottom) // ROW)
    p.lines(p.x0, ya, cw, n)
    p.lines(p.x0 + p.w / 2 + 3 * mm, yb2, cw, n)


@page("Yearly Sales Overview")
def p_year(p):
    c = p.c
    y = p.header("Yearly Sales Overview", "Copy your monthly totals here to see the whole year at a glance.", "Year")
    third = p.w / 3
    for i, lab in enumerate(("Sales goal", "Orders goal", "Products goal")):
        p.field_line(p.x0 + i * third, y - 4, third - 5 * mm, lab)
    y -= 11 * mm
    months = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December"]
    rh = 9.5 * mm
    ybot, _ = p.table(y, [("Month", 1.3), ("Orders", 0.8), ("Sales", 1), ("Expenses", 1),
                          ("Profit", 1), ("Best seller", 1.9)], rows=12, row_h=rh,
                      first_col_labels=months, total_row="Year total")
    yy = p.section(p.x0, ybot - 6 * mm, "Year in review — what worked, what to change")
    n = int((yy - p.bottom) // ROW)
    p.lines(p.x0, yy, p.w, n)


@page("Supplier Contacts")
def p_suppliers(p):
    c = p.c
    y = p.header("Supplier Contacts", "Keep the people and shops you buy from in one place.")
    cols, g = 2, 5 * mm
    cw = (p.w - g) / cols
    fields = ["Supplier", "Contact", "Phone", "Email / website", "Supplies", "Min. order"]
    ch0 = (len(fields) + 1) * ROW + 2 * mm
    rows = int((y - p.bottom + g) // (ch0 + g))
    ch = (y - p.bottom - g * (rows - 1)) / rows
    for r in range(rows):
        for k in range(cols):
            bx = p.x0 + k * (cw + g)
            by = y - r * (ch + g)
            c.setStrokeColor(FAINT); c.setLineWidth(0.8)
            c.roundRect(bx, by - ch, cw, ch, 3)
            c.setStrokeColor(ACC); c.setLineWidth(1.6)
            c.line(bx, by - 3, bx, by - ch + 3)
            fy = by - 3 * mm
            for f in fields:
                fy -= ROW
                p.field_line(bx + 4 * mm, fy, cw - 8 * mm, f)
            p.field_line(bx + 4 * mm, fy - ROW, cw - 8 * mm, "Notes")


@page("Goals & Ideas")
def p_goals(p):
    c = p.c
    y = p.header("Goals & Ideas", "Big-picture goals for each quarter, plus a running list of product ideas.", "Year")
    g = 5 * mm
    cw = (p.w - g) / 2
    qh = 5 * ROW + 9 * mm
    for i in range(4):
        r, k = divmod(i, 2)
        bx = p.x0 + k * (cw + g)
        by = y - r * (qh + g)
        c.setStrokeColor(FAINT); c.setLineWidth(0.8)
        c.roundRect(bx, by - qh, cw, qh, 3)
        c.setFont("Head", 12); c.setFillColor(ACC)
        c.drawString(bx + 4 * mm, by - 6.5 * mm, f"Q{i + 1}")
        c.setFont("BodyI", 8.5); c.setFillColor(SOFT)
        c.drawString(bx + 13 * mm, by - 6.5 * mm, "goals")
        yy = by - 8 * mm
        for j in range(5):
            yy -= ROW
            p.checkbox(bx + 4 * mm, yy + 1.2 * mm)
            c.setStrokeColor(RULE); c.setLineWidth(0.5)
            c.line(bx + 4 * mm + BOX + 2 * mm, yy, bx + cw - 4 * mm, yy)
    y = y - 2 * (qh + g) - 1 * mm
    p.table(y, [("Product idea", 3.2), ("Materials needed", 2.2), ("Try it", 0.7)], boxes=(2,))


def draw_pdf(path, size):
    c = canvas.Canvas(path, pagesize=size, initialFontName="Body")
    c.setTitle(TITLE + " — Order & Inventory Planner")
    c.setAuthor("Quiet Desk Printables")
    c.setSubject("Printable small business planner")
    for i, (_, fn) in enumerate(PAGES):
        p = P(c, size)
        fn(p)
        p.footer(i + 1)
        c.showPage()
    c.save()


# ---------------------------------------------------------------- previews
BG = HexColor("#F3EDE6")
BG2 = HexColor("#E9DFD5")
PW, PH = 800.0, 600.0  # 4:3 canvas, rendered at 180 dpi -> 2000 x 1500 px


def render_pages(pdf, outdir, dpi):
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), pdf, os.path.join(outdir, "pg")], check=True)
    return sorted(glob.glob(os.path.join(outdir, "pg-*.png")))


def paper(c, img, x, y, w, h, angle=0):
    c.saveState()
    c.translate(x + w / 2, y + h / 2)
    c.rotate(angle)
    for d, a in ((7, 0.06), (4, 0.08), (2, 0.10)):
        c.setFillColor(HexColor("#3B3632"), alpha=a)
        c.rect(-w / 2 + d * 0.6, -h / 2 - d, w, h, stroke=0, fill=1)
    c.setFillAlpha(1)
    c.drawImage(img, -w / 2, -h / 2, w, h)
    c.setStrokeColor(HexColor("#D8CFC6")); c.setLineWidth(0.4)
    c.rect(-w / 2, -h / 2, w, h, stroke=1, fill=0)
    c.restoreState()


def bg(c):
    c.setFillColor(BG); c.rect(0, 0, PW, PH, stroke=0, fill=1)


def pill(c, x, y, text, size=13, fill=ACC, color=white):
    w = stringWidth(text, "BodyB", size) + 26
    c.setFillColor(fill); c.roundRect(x, y, w, size + 14, (size + 14) / 2, stroke=0, fill=1)
    c.setFillColor(color); c.setFont("BodyB", size)
    c.drawString(x + 13, y + 9, text)
    return w


def preview_pdf(path, imgs, n_pages):
    asp = 11 / 8.5
    c = canvas.Canvas(path, pagesize=(PW, PH), initialFontName="Body")
    # 1. hero
    bg(c)
    c.setFillColor(BG2); c.circle(610, 300, 270, stroke=0, fill=1)
    ph = 430; pw = ph / asp
    paper(c, imgs[5], 435, 95, pw, ph, angle=-3)
    paper(c, imgs[1], 420, 80, pw, ph, angle=3)
    paper(c, imgs[0], 385, 70, pw, ph, angle=0)
    x = 46
    c.setFillColor(ACC); c.setFont("BodyB", 13)
    c.drawString(x, 470, "PRINTABLE PLANNER FOR MAKERS")
    c.setFillColor(INK); c.setFont("Head", 46)
    c.drawString(x, 410, "Small Business")
    c.drawString(x, 362, "Planner")
    c.setFont("HeadIt", 19); c.setFillColor(SOFT)
    c.drawString(x, 326, "Orders  \u00b7  Inventory  \u00b7  Income  \u00b7  Pricing")
    c.setStrokeColor(ACC); c.setLineWidth(2); c.line(x, 305, x + 60, 305)
    pill(c, x, 240, f"{n_pages} printable pages", size=15)
    c.setFont("BodyB", 14); c.setFillColor(INK)
    c.drawString(x, 205, "Instant download · US Letter + A4")
    c.setFont("Body", 12.5); c.setFillColor(SOFT)
    c.drawString(x, 182, "Print at home — fill in by hand")
    c.setFont("Body", 10); c.setFillColor(SOFT)
    c.drawString(x, 40, "Quiet Desk Printables · digital download")
    c.showPage()

    # 2-4: page spotlights
    spots = [
        (1, "Order Log", "Track every order on one line — date, customer, item, qty, price and a shipped box.",
         [2, 3]),
        (5, "Monthly Income & Expenses", "Fill-in summary of sales, fees, materials and shipping, with a profit line.",
         [6, 8]),
        (3, "Inventory Tracker", "Item, SKU, stock level, reorder point and supplier — never run out mid-season.",
         [4, 9]),
    ]
    for main, title, blurb, extra in spots:
        bg(c)
        ph = 510; pw = ph / asp
        c.setFillColor(BG2); c.roundRect(430, -40, 420, 680, 30, stroke=0, fill=1)
        paper(c, imgs[extra[0]], 545, 90, pw * 0.58, ph * 0.58, angle=5)
        paper(c, imgs[main], 385, 45, pw, ph)
        x = 46
        c.setFillColor(ACC); c.setFont("BodyB", 12)
        c.drawString(x, 470, "INSIDE THE PLANNER")
        c.setFillColor(INK)
        s = fit(title, "Head", 38, 330)
        c.setFont("Head", s)
        words = title.split(" ")
        # wrap title to two lines if wide
        if stringWidth(title, "Head", 38) > 330:
            mid = len(words) // 2 + (1 if len(words) % 2 else 0)
            c.setFont("Head", 36)
            c.drawString(x, 420, " ".join(words[:mid]))
            c.drawString(x, 378, " ".join(words[mid:]))
            ty = 350
        else:
            c.setFont("Head", 38)
            c.drawString(x, 420, title)
            ty = 392
        c.setStrokeColor(ACC); c.setLineWidth(2); c.line(x, ty, x + 60, ty)
        c.setFont("Body", 15); c.setFillColor(SOFT)
        _wrap(c, blurb, x, ty - 30, 320, "Body", 15, 21)
        pill(c, x, 120, "US Letter + A4", size=13)
        c.setFont("Body", 12); c.setFillColor(SOFT)
        c.drawString(x, 90, f"{n_pages} pages · instant download")
        c.showPage()

    # 5. what's included
    bg(c)
    c.setFillColor(INK); c.setFont("Head", 32)
    c.drawCentredString(PW / 2, 548, "What's Included")
    c.setFont("Body", 13); c.setFillColor(SOFT)
    c.drawCentredString(PW / 2, 526, f"{n_pages} pages · US Letter + A4 PDFs · print as many copies as you need")
    cols = 6
    tw = 104; th = tw * asp; gx = 22
    total_w = cols * tw + (cols - 1) * gx
    x0 = (PW - total_w) / 2
    rows_y = [338, 96]
    for i, (name, _) in enumerate(PAGES):
        r, k = divmod(i, cols)
        x = x0 + k * (tw + gx)
        y = rows_y[r]
        paper(c, imgs[i], x, y, tw, th)
        c.setFont("BodyB", 9.5); c.setFillColor(ACC)
        c.drawCentredString(x + tw / 2, y - 16, f"{i + 1:02d}")
        nm = name
        s = fit(nm, "Body", 10, tw + gx - 4)
        c.setFont("Body", s); c.setFillColor(INK)
        c.drawCentredString(x + tw / 2, y - 29, nm)
    if len(PAGES) < 2 * cols:
        # final slot: format card
        k = len(PAGES) - cols
        x = x0 + k * (tw + gx); y = rows_y[1]
        c.setStrokeColor(ACC); c.setLineWidth(1.2); c.setDash(4, 3)
        c.roundRect(x, y, tw, th, 6, stroke=1, fill=0); c.setDash()
        c.setFillColor(ACC); c.setFont("Head", 15)
        c.drawCentredString(x + tw / 2, y + th / 2 + 18, "2 sizes")
        c.setFont("Body", 10.5); c.setFillColor(INK)
        c.drawCentredString(x + tw / 2, y + th / 2 - 2, "US Letter")
        c.drawCentredString(x + tw / 2, y + th / 2 - 16, "8.5 × 11 in")
        c.drawCentredString(x + tw / 2, y + th / 2 - 36, "A4")
        c.drawCentredString(x + tw / 2, y + th / 2 - 50, "210 × 297 mm")
    c.setFont("Body", 9.5); c.setFillColor(SOFT)
    c.drawCentredString(PW / 2, 26, "Digital download — no physical item ships")
    c.showPage()
    c.save()


def _wrap(c, text, x, y, w, font, size, lead):
    words = text.split(); line = ""
    c.setFont(font, size)
    for wd in words:
        t = (line + " " + wd).strip()
        if stringWidth(t, font, size) > w and line:
            c.drawString(x, y, line); y -= lead; line = wd
        else:
            line = t
    if line:
        c.drawString(x, y, line)


def main():
    letter_pdf = os.path.join(HERE, f"{SLUG}-US-Letter.pdf")
    a4_pdf = os.path.join(HERE, f"{SLUG}-A4.pdf")
    draw_pdf(letter_pdf, letter)
    draw_pdf(a4_pdf, A4)
    prev = os.path.join(HERE, "previews")
    os.makedirs(prev, exist_ok=True)
    for f in glob.glob(os.path.join(prev, "*.png")):
        os.remove(f)
    tmp = tempfile.mkdtemp()
    try:
        imgs = render_pages(letter_pdf, tmp, 150)
        ppdf = os.path.join(tmp, "previews.pdf")
        preview_pdf(ppdf, imgs, len(PAGES))
        subprocess.run(["pdftoppm", "-png", "-r", "180", ppdf, os.path.join(tmp, "pv")], check=True)
        names = ["01-hero", "02-order-log", "03-income-expenses", "04-inventory", "05-whats-included"]
        for src, nm in zip(sorted(glob.glob(os.path.join(tmp, "pv-*.png"))), names):
            shutil.move(src, os.path.join(prev, nm + ".png"))
    finally:
        shutil.rmtree(tmp)
    print(f"Built {len(PAGES)} pages:", letter_pdf, a4_pdf)


if __name__ == "__main__":
    main()
