#!/usr/bin/env python3
"""Paycheck Budget Kit -- reproducible generator.

Run `python3 build.py` from this folder. Produces:
  paycheck-budget-kit-US-Letter.pdf, paycheck-budget-kit-A4.pdf, previews/*.png
Requires: reportlab, pypdf, Pillow, poppler-utils (pdftoppm).
"""
import os
import shutil
import subprocess
import tempfile

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
SLUG = "paycheck-budget-kit"
PRODUCT = "Paycheck Budget Kit"
BRAND = "Quiet Desk Printables · personal use only"

# ---------------------------------------------------------------- fonts
FD = "/usr/share/fonts/truetype/crosextra/"
pdfmetrics.registerFont(TTFont("Sans", FD + "Carlito-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Sans-B", FD + "Carlito-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Sans-I", FD + "Carlito-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Serif-B", FD + "Caladea-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Serif", FD + "Caladea-Regular.ttf"))

# ---------------------------------------------------------------- colours
TEAL = HexColor("#1D7A70")      # the one accent
TINT = HexColor("#E7F2F0")      # very light teal for header rows
INK = HexColor("#24302E")
MUTED = HexColor("#6B7A77")
RULE = HexColor("#B9C4C2")
FAINT = HexColor("#A7B3B1")

MARGIN = 0.6 * inch             # spec minimum is 0.5 in
ROW = 8 * mm                    # standard write-in row (spec min 7 mm)
BOX = 4.6 * mm                  # checkbox size (spec min 4 mm)

PAGES = [
    "Cover",
    "Paycheck Budget",
    "Monthly Bill Tracker",
    "Bill Payment Calendar",
    "Expense Log",
    "Sinking Funds",
    "Savings Challenge",
    "Debt Payoff Tracker",
    "No-Spend Challenge",
    "Monthly Review",
    "Financial Goals",
    "Year at a Glance",
]


class Page:
    def __init__(self, c, size):
        self.c = c
        self.W, self.H = size
        self.L = MARGIN
        self.R = self.W - MARGIN
        self.T = self.H - MARGIN
        self.B = MARGIN
        self.CW = self.R - self.L
        self.CB = self.B + 18          # content bottom (above footer)

    # ---------------- primitives
    def text(self, x, y, s, font="Sans", size=10, color=INK, align="left"):
        c = self.c
        c.setFont(font, size)
        c.setFillColor(color)
        if align == "left":
            c.drawString(x, y, s)
        elif align == "right":
            c.drawRightString(x, y, s)
        else:
            c.drawCentredString(x, y, s)

    def spaced(self, x, y, s, font="Sans-B", size=8.5, color=TEAL, sp=1.2):
        t = self.c.beginText(x, y)
        t.setFont(font, size)
        t.setFillColor(color)
        t.setCharSpace(sp)
        t.textLine(s)
        t.setCharSpace(0)
        self.c.drawText(t)
        return stringWidth(s, font, size) + sp * len(s)

    def hline(self, x0, x1, y, color=RULE, w=0.6):
        c = self.c
        c.setStrokeColor(color)
        c.setLineWidth(w)
        c.line(x0, y, x1, y)

    def vline(self, x, y0, y1, color=RULE, w=0.6):
        c = self.c
        c.setStrokeColor(color)
        c.setLineWidth(w)
        c.line(x, y0, x, y1)

    def box(self, x, y, w, h, stroke=FAINT, fill=None, lw=0.7, r=0):
        c = self.c
        c.setStrokeColor(stroke)
        c.setLineWidth(lw)
        if fill is not None:
            c.setFillColor(fill)
        if r:
            c.roundRect(x, y, w, h, r, stroke=1, fill=1 if fill is not None else 0)
        else:
            c.rect(x, y, w, h, stroke=1, fill=1 if fill is not None else 0)

    def checkbox(self, cx, cy, s=BOX):
        self.box(cx - s / 2, cy - s / 2, s, s, stroke=MUTED, lw=0.7, r=1)

    def field(self, x, y, label, width, size=10):
        """Label followed by a write-in line. Returns x after the field."""
        lw = stringWidth(label, "Sans-B", size)
        self.text(x, y, label, "Sans-B", size, INK)
        self.hline(x + lw + 4, x + width, y - 2, MUTED, 0.6)
        return x + width

    # ---------------- page furniture
    def header(self, title, hint=None, fields=()):
        """Title top-left, optional write-in fields top-right. Returns content top y."""
        y = self.T - 22
        self.text(self.L, y, title, "Serif-B", 23, INK)
        # fields on the right, laid out right-to-left
        x = self.R
        for label, w in reversed(fields):
            self.field(x - w, y + 2, label, w, 10)
            x -= w + 12
        self.c.setStrokeColor(TEAL)
        self.c.setLineWidth(2)
        self.c.line(self.L, y - 10, self.L + 42, y - 10)
        self.hline(self.L + 46, self.R, y - 10, RULE, 0.6)
        top = y - 14
        if hint:
            self.text(self.L, y - 25, hint, "Sans-I", 9.5, MUTED)
            top = y - 33
        return top - 6

    def footer(self, num=None):
        y = self.B + 2
        self.text(self.L, y, BRAND, "Sans", 7.5, MUTED)
        if num is not None:
            self.text(self.R, y, PRODUCT + "  ·  " + str(num), "Sans", 7.5, MUTED, "right")

    def section(self, x, y, label, width):
        """Small spaced-caps section label with rule. Returns y below."""
        w = self.spaced(x, y - 9, label.upper(), size=8.5)
        self.hline(x + w + 6, x + width, y - 6, RULE, 0.5)
        return y - 16

    # ---------------- tables
    def table(self, x, ytop, cols, nrows, rowh=ROW, header_h=16, total=None):
        """cols: list of (label, width, kind) kind in text|money|check|num|center.
        Widths may be fractions (<=1) of remaining width. Returns bottom y."""
        fixed = sum(w for _, w, _ in cols if w > 1)
        fracs = sum(w for _, w, _ in cols if w <= 1)
        avail = self._tw - fixed
        widths = [w if w > 1 else avail * w / fracs for _, w, _ in cols]
        tw = sum(widths)
        c = self.c
        # header
        self.box(x, ytop - header_h, tw, header_h, stroke=TINT, fill=TINT, lw=0.1)
        cx = x
        for (label, _, kind), w in zip(cols, widths):
            if kind in ("money", "num"):
                self.text(cx + w - 5, ytop - header_h + 5, label, "Sans-B", 8.5, INK, "right")
            elif kind in ("check", "center"):
                self.text(cx + w / 2, ytop - header_h + 5, label, "Sans-B", 8.5, INK, "center")
            else:
                self.text(cx + 5, ytop - header_h + 5, label, "Sans-B", 8.5, INK)
            cx += w
        y = ytop - header_h
        rows = nrows + (1 if total else 0)
        for i in range(rows):
            yb = y - rowh
            is_total = total and i == rows - 1
            cx = x
            for j, ((label, _, kind), w) in enumerate(zip(cols, widths)):
                if is_total:
                    if j == 0:
                        self.text(cx + 5, yb + rowh / 2 - 3.5, total, "Sans-B", 9.5, TEAL)
                    if kind == "money":
                        self.text(cx + 5, yb + rowh / 2 - 3, "$", "Sans", 8, FAINT)
                else:
                    if kind == "check":
                        self.checkbox(cx + w / 2, yb + rowh / 2)
                    elif kind == "money":
                        self.text(cx + 5, yb + rowh / 2 - 3, "$", "Sans", 8, FAINT)
                cx += w
            self.hline(x, x + tw, yb, TEAL if is_total else RULE, 1.0 if is_total else 0.6)
            y = yb
        # vertical separators
        cx = x
        for w in widths[:-1]:
            cx += w
            self.vline(cx, y, ytop - header_h, RULE, 0.4)
        self.hline(x, x + tw, ytop, TEAL, 1.0)
        return y

    def tbl(self, x, ytop, width, cols, nrows, **kw):
        self._tw = width
        return self.table(x, ytop, cols, nrows, **kw)

    def lines(self, x, ytop, width, n, gap=ROW):
        y = ytop
        for _ in range(n):
            y -= gap
            self.hline(x, x + width, y, RULE, 0.6)
        return y


def rows_fit(height, rowh=ROW, header_h=16, extra=0):
    return int((height - header_h - extra) // rowh)


# ====================================================================== pages
def p_cover(p):
    c = p.c
    # thin frame inside the margin
    p.box(p.L, p.CB, p.CW, p.T - p.CB, stroke=TEAL, lw=1.0)
    p.box(p.L + 6, p.CB + 6, p.CW - 12, p.T - p.CB - 12, stroke=RULE, lw=0.5)
    cx = p.W / 2
    y = p.T - 0.3 * (p.T - p.CB) + 40
    lab = "PRINTABLE BUDGET KIT"
    w = stringWidth(lab, "Sans-B", 10) + 2.2 * len(lab)
    p.spaced(cx - w / 2, y + 70, lab, size=10, sp=2.2)
    p.text(cx, y, "Paycheck", "Serif-B", 54, INK, "center")
    p.text(cx, y - 58, "Budget Kit", "Serif-B", 54, INK, "center")
    c.setStrokeColor(TEAL)
    c.setLineWidth(2)
    c.line(cx - 30, y - 82, cx + 30, y - 82)
    p.text(cx, y - 106, "Plan every paycheck · for weekly & biweekly pay", "Sans", 13, MUTED, "center")

    # decorative coin stack / bar motif (light line art)
    by = y - 190
    bars = [18, 30, 24, 40, 34, 52]
    bw = 16
    total = len(bars) * bw + (len(bars) - 1) * 8
    bx = cx - total / 2
    for i, h in enumerate(bars):
        p.box(bx + i * (bw + 8), by, bw, h, stroke=TEAL, fill=TINT if i < 5 else TEAL, lw=1)
    p.hline(cx - total / 2 - 14, cx + total / 2 + 14, by, TEAL, 1.2)

    # name / year
    fy = by - 50
    fw = 230
    p.field(cx - fw / 2, fy, "Name", fw, 11)
    p.field(cx - fw / 2, fy - 30, "Year", fw, 11)

    # contents
    ty = fy - 72
    p.text(cx, ty, "INSIDE", "Sans-B", 9, TEAL, "center")
    items = PAGES[1:]
    half = (len(items) + 1) // 2
    colw = 190
    for col in range(2):
        for i, name in enumerate(items[col * half:(col + 1) * half]):
            n = col * half + i + 2
            xx = cx - colw - 10 + col * (colw + 20)
            yy = ty - 20 - i * 15
            p.text(xx, yy, "%02d" % n, "Sans-B", 9.5, TEAL)
            p.text(xx + 20, yy, name, "Sans", 10, INK)
    p.footer()


def p_paycheck(p):
    top = p.header("Paycheck Budget",
                   "Use one page per paycheck. Give every dollar a job before you spend it.")
    # info strip
    y = top - 14
    w = p.CW
    x = p.L
    x = p.field(x, y, "Pay date", w * 0.28) + 14
    x = p.field(x, y, "Pay period", w * 0.42) + 14
    p.field(x, y, "Paycheck #", p.R - x)
    y -= 16
    gap = 14
    lw = (p.CW - gap) * 0.56
    rw = p.CW - gap - lw
    lx, rx = p.L, p.L + lw + gap
    avail = y - p.CB

    # left: income + fixed bills
    yy = p.section(lx, y, "Income", lw)
    yy = p.tbl(lx, yy, lw, [("Source", 1, "text"), ("Amount", 80, "money")], 3, total="Total income")
    yy -= 12
    yy = p.section(lx, yy, "Fixed bills", lw)
    n = rows_fit(yy - p.CB, extra=ROW)
    yy = p.tbl(lx, yy, lw, [("Bill", 1, "text"), ("Due", 44, "center"),
                            ("Amount", 70, "money"), ("Paid", 30, "check")], n, total="Total bills")

    # right: variable, savings, summary
    summ_h = 16 + 5 * 22 + 8
    sav_h = 16 + 16 + 3 * ROW + 12
    ry = p.section(rx, y, "Variable spending", rw)
    n = rows_fit(ry - p.CB - summ_h - sav_h - 12, extra=ROW)
    ry = p.tbl(rx, ry, rw, [("Category", 1, "text"), ("Plan", 58, "money"),
                            ("Actual", 58, "money")], n, total="Total")
    ry -= 12
    ry = p.section(rx, ry, "Savings & debt", rw)
    ry = p.tbl(rx, ry, rw, [("Goal / debt", 1, "text"), ("Amount", 70, "money")], 3)
    ry -= 12
    ry = p.section(rx, ry, "Summary", rw)
    labels = [("Total income", ""), ("Fixed bills", "−"), ("Variable spending", "−"),
              ("Savings & debt", "−"), ("Left over", "=")]
    sh = 22
    by = ry - 5 * sh
    p.box(rx, by, rw, 5 * sh, stroke=TEAL, lw=1, r=3)
    for i, (lab, op) in enumerate(labels):
        yb = ry - (i + 1) * sh
        last = i == 4
        if last:
            p.box(rx + 0.5, yb + 0.5, rw - 1, sh - 1, stroke=TINT, fill=TINT, lw=0.1, r=3)
        p.text(rx + 8, yb + 7, op, "Sans-B", 11, TEAL)
        p.text(rx + 22, yb + 7, lab, "Sans-B" if last else "Sans", 10.5, TEAL if last else INK)
        p.text(rx + rw - 82, yb + 7, "$", "Sans", 8, FAINT)
        p.hline(rx + rw - 74, rx + rw - 8, yb + 5, MUTED, 0.5)


def p_bills(p):
    top = p.header("Monthly Bill Tracker", "List each bill once, then tick it off as it is paid.",
                   fields=[("Month", 150)])
    n = rows_fit(top - p.CB - 6, extra=ROW)
    p.tbl(p.L, top - 6, p.CW, [("Bill / company", 1, "text"), ("Due date", 62, "center"),
                               ("Amount", 80, "money"), ("Paid on", 62, "center"),
                               ("Paid", 36, "check"), ("Notes", 0.6, "text")], n,
          total="Total for the month")


def p_calendar(p):
    top = p.header("Bill Payment Calendar", "Write in the dates, then add bills and paydays to each day.",
                   fields=[("Month", 130), ("Year", 80)])
    notes_h = 3 * ROW + 20
    gy = top - 6
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    cw = p.CW / 7
    hh = 16
    p.box(p.L, gy - hh, p.CW, hh, stroke=TINT, fill=TINT, lw=0.1)
    for i, d in enumerate(days):
        p.text(p.L + i * cw + cw / 2, gy - hh + 5, d, "Sans-B", 8.5, INK, "center")
    rh = (gy - hh - p.CB - notes_h) / 6
    yb = gy - hh - 6 * rh
    for r in range(7):
        p.hline(p.L, p.R, gy - hh - r * rh, RULE, 0.6)
    for i in range(8):
        p.vline(p.L + i * cw, yb, gy - hh, RULE, 0.6)
    p.hline(p.L, p.R, gy, TEAL, 1)
    for r in range(6):
        for i in range(7):
            p.box(p.L + i * cw + 4, gy - hh - r * rh - 4 - 15, 17, 15, stroke=RULE, lw=0.5, r=2)
    # bottom
    y = yb - 10
    w2 = (p.CW - 14) / 2
    y1 = p.section(p.L, y, "Paydays this month", w2)
    p.lines(p.L, y1 + 4, w2, 3)
    y2 = p.section(p.L + w2 + 14, y, "Notes", w2)
    p.lines(p.L + w2 + 14, y2 + 4, w2, 3)


def p_expense(p):
    top = p.header("Expense Log", "Write down every purchase, big or small.",
                   fields=[("Month", 150)])
    n = rows_fit(top - p.CB - 6, extra=ROW)
    p.tbl(p.L, top - 6, p.CW, [("Date", 58, "center"), ("Item / where", 1, "text"),
                               ("Category", 0.55, "text"), ("Amount", 84, "money")], n,
          total="Total this page")


def p_sinking(p):
    top = p.header("Sinking Funds",
                   "Name a fund, set a goal, then color the thermometer as you add money.")
    gap = 12
    cw = (p.CW - gap) / 2
    ch = (top - 4 - p.CB - 2 * gap) / 3
    for r in range(3):
        for col in range(2):
            x = p.L + col * (cw + gap)
            yt = top - 4 - r * (ch + gap)
            p.box(x, yt - ch, cw, ch, stroke=RULE, lw=0.8, r=5)
            ix = x + 10
            iw = cw - 20
            y = yt - 20
            p.field(ix, y, "Fund", iw, 10)
            y -= 22
            p.field(ix, y, "Goal $", iw * 0.5 - 4, 10)
            p.field(ix + iw * 0.5 + 4, y, "By", iw * 0.5 - 4, 10)
            # thermometer
            tb = yt - ch + 12
            tt = y - 14
            tx = ix + 14
            br = 10
            tw = 12
            c = p.c
            c.setStrokeColor(TEAL)
            c.setLineWidth(1)
            c.setFillColor(white)
            c.roundRect(tx - tw / 2, tb + br, tw, tt - tb - br, tw / 2, stroke=1, fill=0)
            c.setFillColor(TINT)
            c.circle(tx, tb + br, br, stroke=1, fill=1)
            seg = (tt - tb - 2 * br - 6) / 10
            for k in range(1, 11):
                yy = tb + 2 * br + k * seg
                c.setStrokeColor(TEAL)
                c.setLineWidth(0.6)
                c.line(tx + tw / 2, yy, tx + tw / 2 + 5, yy)
                if k % 2 == 0:
                    p.text(tx + tw / 2 + 7, yy - 2.5, "%d%%" % (k * 10), "Sans", 6.5, MUTED)
            # deposit log
            lx = ix + 48
            lwid = ix + iw - lx
            nrow = int((tt - tb + 4 - 15) // (7.2 * mm))
            p.tbl(lx, tt + 4, lwid, [("Date", 0.32, "center"), ("Added", 0.34, "money"),
                                     ("Saved", 0.34, "money")], nrow, rowh=7.2 * mm, header_h=15)


def p_savings(p):
    top = p.header("Savings Challenge",
                   "Write an amount in each box. Color it in when that amount is saved.")
    y = top - 14
    x = p.field(p.L, y, "Saving for", p.CW * 0.45) + 14
    x = p.field(x, y, "Goal $", p.CW * 0.25) + 14
    p.field(x, y, "Start", p.R - x)
    y -= 16
    bottom_h = 34
    cw = p.CW / 10
    rh = min((y - p.CB - bottom_h) / 10, cw * 0.9)
    gy = y
    for r in range(10):
        for col in range(10):
            bx = p.L + col * cw
            byy = gy - (r + 1) * rh
            p.box(bx + 1.5, byy + 1.5, cw - 3, rh - 3, stroke=FAINT, lw=0.6, r=3)
            p.text(bx + 5, byy + rh - 10, str(r * 10 + col + 1), "Sans", 6.5, FAINT)
    yb = gy - 10 * rh - 22
    w3 = (p.CW - 28) / 3
    for i, lab in enumerate(["Saved so far $", "Still to go $", "Done on"]):
        p.field(p.L + i * (w3 + 14), yb, lab, w3, 10)


def p_debt(p):
    top = p.header("Debt Payoff Tracker",
                   "List debts in the order you will pay them. Shade one box for every 10% paid off.")
    y = top - 6
    rowh = 11 * mm
    prog_w = 10 * BOX + 9 * 1.6 + 12
    cols = [("#", 18, "center"), ("Debt", 1, "text"), ("Balance", 70, "money"),
            ("Min. payment", 66, "money"), ("Due", 36, "center"), ("Paid off", prog_w, "text")]
    nd = 9
    yb = p.tbl(p.L, y, p.CW, cols, nd, rowh=rowh, total="Total debt")
    # number + progress boxes
    px = p.R - prog_w + 6
    for i in range(nd):
        cy = y - 16 - i * rowh - rowh / 2
        p.text(p.L + 9, cy - 3.5, str(i + 1), "Sans-B", 9.5, TEAL, "center")
        for k in range(10):
            p.box(px + k * (BOX + 1.6), cy - BOX / 2, BOX, BOX, stroke=TEAL, lw=0.6, r=1)
    # log
    y = yb - 14
    y = p.section(p.L, y, "Payment log", p.CW)
    n = rows_fit(y - p.CB)
    p.tbl(p.L, y, p.CW, [("Date", 64, "center"), ("Debt", 1, "text"), ("Amount paid", 90, "money"),
                         ("New balance", 90, "money")], n)


def p_nospend(p):
    top = p.header("No-Spend Challenge",
                   "Color a circle for each day you spend only on essentials.",
                   fields=[("Month", 150)])
    cols = 7
    cw = p.CW / cols
    bottom_h = 5 * ROW + 40
    rh = min((top - 10 - p.CB - bottom_h) / 5, cw)
    rad = min(cw, rh) * 0.38
    for d in range(31):
        r, col = divmod(d, cols)
        cx = p.L + col * cw + cw / 2
        cy = top - 10 - r * rh - rh / 2
        c = p.c
        c.setStrokeColor(TEAL)
        c.setLineWidth(1)
        c.circle(cx, cy, rad, stroke=1, fill=0)
        p.text(cx, cy - 5, str(d + 1), "Serif", 14, MUTED, "center")
    # bottom area in the free slots of last row + below
    y = top - 10 - 5 * rh - 6
    w2 = (p.CW - 14) / 2
    y1 = p.section(p.L, y, "Essentials I will still pay for", w2)
    p.lines(p.L, y1 + 4, w2, 4)
    y2 = p.section(p.L + w2 + 14, y, "My reward", w2)
    p.lines(p.L + w2 + 14, y2 + 4, w2, 2)
    yy = y2 + 4 - 2 * ROW - 22
    p.field(p.L + w2 + 14, yy, "No-spend days", w2 * 0.5 - 6, 10)
    p.field(p.L + w2 + 14 + w2 * 0.5 + 6, yy, "Kept $", w2 * 0.5 - 6, 10)
    # free slots in last row: small tally box
    sx = p.L + 3 * cw + 8
    sy = top - 10 - 4 * rh
    p.box(sx, sy - rh + 8, p.R - sx, rh - 16, stroke=RULE, lw=0.7, r=5)
    p.text(sx + 12, sy - 22, "THIS MONTH", "Sans-B", 8.5, TEAL)
    p.field(sx + 12, sy - 46, "Started", (p.R - sx) * 0.5 - 18, 10)
    p.field(sx + (p.R - sx) * 0.5 + 6, sy - 46, "Streak", (p.R - sx) * 0.5 - 18, 10)


def p_review(p):
    top = p.header("Monthly Review", "Compare the plan with what really happened.",
                   fields=[("Month", 150)])
    y = top - 6
    y = p.section(p.L, y, "The numbers", p.CW)
    rows = ["Income", "Fixed bills", "Variable spending", "Savings", "Debt payments", "Left over"]
    rowh = ROW
    cols = [("Category", 1, "text"), ("Planned", 100, "money"), ("Actual", 100, "money"),
            ("Difference", 100, "money")]
    yb = p.tbl(p.L, y, p.CW, cols, len(rows), rowh=rowh)
    for i, lab in enumerate(rows):
        p.text(p.L + 5, y - 16 - i * rowh - rowh / 2 - 3.5, lab, "Sans", 10, INK)
    y = yb - 14
    x = p.field(p.L, y, "Savings balance $", p.CW * 0.5 - 7)
    p.field(x + 14, y, "Total debt balance $", p.R - x - 14)
    y -= 14
    w2 = (p.CW - 14) / 2
    avail = y - p.CB
    nl = int((avail / 2 - 22) // ROW)
    y1 = p.section(p.L, y, "What went well", w2)
    p.lines(p.L, y1 + 4, w2, nl)
    y2 = p.section(p.L + w2 + 14, y, "What I will adjust", w2)
    p.lines(p.L + w2 + 14, y2 + 4, w2, nl)
    y = y1 + 4 - nl * ROW - 14
    y1 = p.section(p.L, y, "Biggest expenses", w2)
    n = rows_fit(y1 - p.CB)
    p.tbl(p.L, y1, w2, [("Item", 1, "text"), ("Amount", 70, "money")], n)
    y2 = p.section(p.L + w2 + 14, y, "Focus for next month", w2)
    p.lines(p.L + w2 + 14, y2 + 4, w2, int((y2 + 4 - p.CB) // ROW))


def p_goals(p):
    top = p.header("Financial Goals",
                   "Write each goal, then shade a box for every 10% reached.")
    n = 5
    gap = 10
    ch = (top - 4 - p.CB - (n - 1) * gap) / n
    for i in range(n):
        yt = top - 4 - i * (ch + gap)
        p.box(p.L, yt - ch, p.CW, ch, stroke=RULE, lw=0.8, r=5)
        p.c.setFillColor(TEAL)
        p.c.circle(p.L + 18, yt - 20, 9, stroke=0, fill=1)
        p.text(p.L + 18, yt - 23.5, str(i + 1), "Sans-B", 10, white, "center")
        ix = p.L + 36
        iw = p.R - 10 - ix
        y = yt - 24
        p.field(ix, y, "Goal", iw, 10)
        y -= 24
        x = p.field(ix, y, "Amount $", iw * 0.33 - 8) + 12
        x = p.field(x, y, "Target date", iw * 0.33 - 4) + 12
        p.field(x, y, "Per paycheck $", ix + iw - x)
        y -= 24
        p.field(ix, y, "Why it matters", iw * 0.52, 10)
        # progress boxes
        bx = ix + iw * 0.52 + 16
        p.text(bx, y, "Progress", "Sans-B", 10, INK)
        bx += 50
        bs = min(BOX * 1.15, (ix + iw - bx - 9 * 2) / 10)
        for k in range(10):
            p.box(bx + k * (bs + 2), y - 3, bs, bs, stroke=TEAL, lw=0.6, r=1)


def p_year(p):
    top = p.header("Year at a Glance", "Copy each month's totals from your monthly review.",
                   fields=[("Year", 110)])
    months = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December"]
    y = top - 6
    rowh = min((y - p.CB - 16) / 13, 13 * mm)
    cols = [("Month", 1, "text"), ("Income", 0.9, "money"), ("Bills", 0.9, "money"),
            ("Spending", 0.9, "money"), ("Saved", 0.9, "money"), ("Debt paid", 0.9, "money"),
            ("Left over", 0.9, "money")]
    p.tbl(p.L, y, p.CW, cols, 12, rowh=rowh, total="Year total")
    for i, m in enumerate(months):
        p.text(p.L + 5, y - 16 - i * rowh - rowh / 2 - 3.5, m, "Sans", 10, INK)


RENDER = [p_cover, p_paycheck, p_bills, p_calendar, p_expense, p_sinking, p_savings,
          p_debt, p_nospend, p_review, p_goals, p_year]


def build_pdf(path, size):
    c = canvas.Canvas(path, pagesize=size, initialFontName="Sans", initialFontSize=10)
    c.setTitle(PRODUCT)
    c.setAuthor("Quiet Desk Printables")
    c.setSubject("Printable paycheck-to-paycheck budget kit")
    for i, fn in enumerate(RENDER):
        p = Page(c, size)
        fn(p)
        if i:
            p.footer(i + 1)
        c.showPage()
    c.save()


# ====================================================================== previews
def render_pages(pdf, dpi, outdir):
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", pdf, os.path.join(outdir, "p")], check=True)
    files = sorted(f for f in os.listdir(outdir) if f.startswith("p-") and f.endswith(".png"))
    return [os.path.join(outdir, f) for f in files]


def build_previews(pdf):
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    out = os.path.join(HERE, "previews")
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    tmp = tempfile.mkdtemp()
    pages = [Image.open(f).convert("RGB") for f in render_pages(pdf, 200, tmp)]

    BG = (243, 240, 234)
    TEALc = (29, 122, 112)
    INKc = (36, 48, 46)
    MUT = (107, 122, 119)

    def font(name, size):
        return ImageFont.truetype(FD + name, size)

    SERIFB = "Caladea-Bold.ttf"
    SANS = "Carlito-Regular.ttf"
    SANSB = "Carlito-Bold.ttf"

    def page_img(idx, h):
        im = pages[idx]
        w = int(im.width * h / im.height)
        return im.resize((w, h), Image.LANCZOS)

    def paste_shadow(canvas_im, im, x, y, angle=0, blur=18, off=(10, 16), alpha=70):
        im = im.convert("RGBA")
        # 1px hairline border so white pages separate from the light background
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, im.width - 1, im.height - 1], outline=(214, 214, 210, 255))
        if angle:
            im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
        mask = im.split()[3]
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(mask.point(lambda v: alpha if v > 0 else 0))
        pad = blur * 3
        shc = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
        shc.paste(sh, (pad, pad))
        shc = shc.filter(ImageFilter.GaussianBlur(blur))
        canvas_im.alpha_composite(shc, (x - pad + off[0], y - pad + off[1]))
        canvas_im.alpha_composite(im, (x, y))
        return im.size

    def base(w=2000, h=1500):
        im = Image.new("RGBA", (w, h), BG + (255,))
        d = ImageDraw.Draw(im)
        # soft accent blob, bottom-right
        d.ellipse([w - 700, h - 520, w + 500, h + 600], fill=(226, 237, 234, 255))
        return im

    def pill(d, x, y, text, f, fill=TEALc, fg=(255, 255, 255), padx=28, pady=14):
        tw = d.textlength(text, font=f)
        bb = f.getbbox("Ag")
        th = bb[3] - bb[1]
        d.rounded_rectangle([x, y, x + tw + 2 * padx, y + th + 2 * pady], radius=(th + 2 * pady) // 2, fill=fill)
        d.text((x + padx, y + pady - bb[1]), text, font=f, fill=fg)
        return x + tw + 2 * padx

    def caption_bar(im, title, sub):
        d = ImageDraw.Draw(im)
        f1 = font(SERIFB, 76)
        f2 = font(SANS, 38)
        d.text((90, 70), title, font=f1, fill=INKc)
        d.text((92, 168), sub, font=f2, fill=MUT)
        d.rectangle([92, 230, 172, 236], fill=TEALc)

    def footer_tag(im):
        d = ImageDraw.Draw(im)
        f = font(SANSB, 30)
        t = "US Letter + A4  ·  Instant download"
        tw = d.textlength(t, font=f)
        d.text((im.width - 90 - tw, im.height - 80), t, font=f, fill=TEALc)

    n = len(pages)

    # 1. hero
    im = base()
    d = ImageDraw.Draw(im)
    pill(d, 110, 150, "PRINTABLE  ·  %d PAGES" % n, font(SANSB, 30))
    f_title = font(SERIFB, 128)
    d.text((104, 240), "Paycheck", font=f_title, fill=INKc)
    d.text((104, 380), "Budget Kit", font=f_title, fill=INKc)
    d.rectangle([112, 560, 222, 568], fill=TEALc)
    f_sub = font(SANS, 46)
    d.text((110, 600), "For weekly & biweekly pay", font=f_sub, fill=MUT)
    f_b = font(SANS, 38)
    bullets = ["Per-paycheck budget page", "Bill tracker + bill calendar",
               "Sinking funds & savings challenge", "Debt payoff + no-spend challenge"]
    for i, b in enumerate(bullets):
        yy = 720 + i * 66
        d.ellipse([114, yy + 14, 130, yy + 30], fill=TEALc)
        d.text((150, yy), b, font=f_b, fill=INKc)
    pill(d, 110, 1040, "Instant download · US Letter + A4", font(SANSB, 36))
    d.text((112, 1150), "Fill in by hand · print as many as you need", font=font(SANS, 32), fill=MUT)
    # pages fan
    ph = 1000
    back2 = page_img(2, int(ph * 0.9))
    back1 = page_img(1, int(ph * 0.92))
    front = page_img(0, ph)
    paste_shadow(im, back1, 860, 300, angle=6, alpha=50)
    paste_shadow(im, back2, 1150, 270, angle=-6, alpha=50)
    paste_shadow(im, front, 1010, 250, angle=0, alpha=80)
    im.convert("RGB").save(os.path.join(out, "01-hero.png"), optimize=True)

    # 2-4 (+5) real page previews: two pages side by side
    sets = [
        ("02-paycheck-budget-and-bills.png", (1, 2), "Plan every paycheck",
         "Per-paycheck budget with a “left over” line, plus a monthly bill tracker"),
        ("03-sinking-funds-and-savings.png", (5, 6), "Watch your savings grow",
         "Six sinking fund thermometers and a 100-box savings challenge"),
        ("04-debt-and-no-spend.png", (7, 8), "Pay it down, day by day",
         "Debt payoff tracker with progress boxes and a 31-day no-spend challenge"),
        ("05-calendar-and-expense-log.png", (3, 4), "Never miss a due date",
         "Blank bill payment calendar and an expense log with roomy columns"),
        ("06-review-goals-year.png", (9, 10, 11), "Review and set goals",
         "Monthly review, financial goals and a year-at-a-glance summary"),
    ]
    for fname, idxs, title, sub in sets:
        im = base()
        caption_bar(im, title, sub)
        k = len(idxs)
        ph = 1080 if k == 2 else 960
        imgs = [page_img(i, ph) for i in idxs]
        gap = 70 if k == 2 else 50
        total = sum(i.width for i in imgs) + gap * (k - 1)
        x = (im.width - total) // 2
        y = 290 if k == 2 else 330
        for pi in imgs:
            paste_shadow(im, pi, x, y)
            x += pi.width + gap
        footer_tag(im)
        im.convert("RGB").save(os.path.join(out, fname), optimize=True)

    # 7. what's included
    im = base()
    d = ImageDraw.Draw(im)
    caption_bar(im, "What’s included", "%d printable pages · US Letter + A4 PDFs" % n)
    cols = 6
    th = 380
    thumbs = [page_img(i, th) for i in range(n)]
    tw = thumbs[0].width
    gx = (im.width - 180 - cols * tw) // (cols - 1)
    f_l = font(SANSB, 25)
    f_n = font(SANSB, 23)
    for i, t in enumerate(thumbs):
        r, ccol = divmod(i, cols)
        x = 90 + ccol * (tw + gx)
        y = 300 + r * (th + 160)
        paste_shadow(im, t, x, y, blur=10, off=(5, 8), alpha=60)
        label = PAGES[i]
        num = "%02d" % (i + 1)
        lw_ = d.textlength(num + "  " + label, font=f_l)
        lx = x + (tw - lw_) / 2
        d.text((lx, y + th + 22), num, font=f_n, fill=TEALc)
        d.text((lx + d.textlength(num + "  ", font=f_l), y + th + 22), label, font=f_l, fill=INKc)
    footer_tag(im)
    im.convert("RGB").save(os.path.join(out, "07-whats-included.png"), optimize=True)
    shutil.rmtree(tmp)


def main():
    os.chdir(HERE)
    letter_pdf = os.path.join(HERE, SLUG + "-US-Letter.pdf")
    a4_pdf = os.path.join(HERE, SLUG + "-A4.pdf")
    build_pdf(letter_pdf, letter)
    build_pdf(a4_pdf, A4)
    build_previews(letter_pdf)
    print("built", letter_pdf, a4_pdf)


if __name__ == "__main__":
    main()
