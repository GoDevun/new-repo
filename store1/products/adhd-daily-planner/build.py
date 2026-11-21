#!/usr/bin/env python3
"""ADHD-friendly daily & weekly planner (undated, printable).

Run `python3 build.py` from this folder to rebuild:
  - adhd-daily-planner-US-Letter.pdf
  - adhd-daily-planner-A4.pdf
  - previews/*.png (2000 px long side, composited from real page renders)
Requires: reportlab, Pillow, pdftoppm (poppler-utils).
"""
import os
import shutil
import subprocess
import tempfile

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
SLUG = "adhd-daily-planner"
PREV = os.path.join(HERE, "previews")

FD = "/usr/share/fonts/truetype/crosextra/"
for name, fn in [("Body", "Carlito-Regular.ttf"), ("Body-Bold", "Carlito-Bold.ttf"),
                 ("Body-Italic", "Carlito-Italic.ttf"), ("Head", "Caladea-Bold.ttf"),
                 ("Head-Reg", "Caladea-Regular.ttf"), ("Head-Italic", "Caladea-Italic.ttf")]:
    pdfmetrics.registerFont(TTFont(name, FD + fn))

# Calm palette: one accent + one soft tint, plus neutrals.
ACCENT = HexColor("#4E7E77")   # muted sage-teal
TINT = HexColor("#E4EEEB")     # soft sage tint
INK = HexColor("#2E3836")
MUTED = HexColor("#6F7D7A")
LINE = HexColor("#B7C6C2")
BOX = HexColor("#A9BCB7")

FOOTER = "Quiet Desk Printables · personal use only"
LINE_GAP = 9 * mm      # writing lines (spec: >= 7 mm)
CB = 5.5 * mm          # checkbox (spec: >= 4 mm)

PAGE_NAMES = [
    "Cover", "Today", "Gentle day", "This week", "Week in review",
    "Habit tracker", "Brain dump", "One thing at a time",
    "Morning routine", "Evening routine", "Mood & energy", "Notes",
]


# ---------------------------------------------------------------- helpers
class P:
    def __init__(self, c, size):
        self.c = c
        self.W, self.H = size
        self.L = 0.6 * inch
        self.R = self.W - 0.6 * inch
        self.T = self.H - 0.6 * inch
        self.B = 0.8 * inch
        self.CW = self.R - self.L

    # text -------------------------------------------------------------
    def text(self, x, y, s, font="Body", size=11, color=INK, align="left", maxw=None):
        c = self.c
        if maxw:
            while pdfmetrics.stringWidth(s, font, size) > maxw and size > 6:
                size -= 0.5
        c.setFont(font, size)
        c.setFillColor(color)
        if align == "left":
            c.drawString(x, y, s)
        elif align == "center":
            c.drawCentredString(x, y, s)
        else:
            c.drawRightString(x, y, s)
        return pdfmetrics.stringWidth(s, font, size)

    def spaced(self, x, y, s, font="Body-Bold", size=10, color=ACCENT, cs=1.2, align="left"):
        w = pdfmetrics.stringWidth(s, font, size) + cs * (len(s) - 1)
        if align == "center":
            x -= w / 2
        elif align == "right":
            x -= w
        self.c.saveState()
        t = self.c.beginText(x, y)
        t.setFont(font, size)
        t.setCharSpace(cs)
        t.setFillColor(color)
        t.textOut(s)
        self.c.drawText(t)
        self.c.restoreState()
        return w

    # shapes -----------------------------------------------------------
    def hline(self, x0, x1, y, color=LINE, w=0.7):
        c = self.c
        c.setStrokeColor(color)
        c.setLineWidth(w)
        c.line(x0, y, x1, y)

    def lines(self, x0, x1, y_top, y_bot, gap=LINE_GAP):
        y = y_top
        n = 0
        while y >= y_bot - 0.01:
            self.hline(x0, x1, y)
            y -= gap
            n += 1
        return n

    def checkbox(self, x, y, s=CB, color=ACCENT):
        c = self.c
        c.setStrokeColor(color)
        c.setLineWidth(0.9)
        c.setFillColor(white)
        c.roundRect(x, y, s, s, 1.6, stroke=1, fill=0)

    def ring_dot(self, cx, cy, r, color=ACCENT, w=0.9):
        c = self.c
        c.setStrokeColor(color)
        c.setLineWidth(w)
        c.circle(cx, cy, r, stroke=1, fill=0)

    def box(self, x, y_top, w, h, label=None, hint=None):
        """Rounded box; returns y where content may start."""
        c = self.c
        c.setStrokeColor(BOX)
        c.setLineWidth(0.9)
        c.roundRect(x, y_top - h, w, h, 9, stroke=1, fill=0)
        if not label:
            return y_top - 12
        lw = pdfmetrics.stringWidth(label.upper(), "Body-Bold", 9.5) + 1.1 * (len(label) - 1)
        c.setFillColor(TINT)
        c.roundRect(x + 10, y_top - 25, lw + 18, 17, 8.5, stroke=0, fill=1)
        self.spaced(x + 19, y_top - 19.6, label.upper(), size=9.5, cs=1.1)
        if hint:
            self.text(x + 10 + lw + 26, y_top - 19.6, hint, "Body-Italic", 10, MUTED,
                      maxw=w - lw - 46)
        return y_top - 34

    def dots(self, x0, x1, y_top, y_bot, step=6 * mm):
        c = self.c
        c.setFillColor(BOX)
        y = y_top
        while y >= y_bot:
            x = x0
            while x <= x1:
                c.circle(x, y, 0.8, stroke=0, fill=1)
                x += step
            y -= step

    def header(self, title, right=None, hint=None):
        y = self.T - 30
        self.text(self.L, y, title, "Head", 32, INK)
        if right:
            lx = self.R - 150
            self.text(lx, y + 2, right, "Body", 11, MUTED)
            rw = pdfmetrics.stringWidth(right, "Body", 11)
            self.hline(lx + rw + 6, self.R, y, BOX, 0.8)
        c = self.c
        c.setFillColor(ACCENT)
        c.roundRect(self.L, y - 15, 34, 3.2, 1.6, stroke=0, fill=1)
        if hint:
            self.text(self.L + 44, y - 16.2, hint, "Body-Italic", 11.5, MUTED,
                      maxw=self.CW - 44 - (170 if right else 0))
        return y - 34

    def footer(self):
        self.text(self.W / 2, 0.56 * inch, FOOTER, "Body", 8, MUTED, align="center")

    def ring(self, cx, cy, r_out, r_in, n=5, start=90):
        """Timer ring split into n empty slices to colour in."""
        c = self.c
        ext = -360.0 / n
        c.setStrokeColor(ACCENT)
        c.setLineWidth(1.0)
        for i in range(n):
            a = start + i * ext
            p = c.beginPath()
            p.arc(cx - r_out, cy - r_out, cx + r_out, cy + r_out, a, ext)
            p.arcTo(cx - r_in, cy - r_in, cx + r_in, cy + r_in, a + ext, -ext)
            p.close()
            c.drawPath(p, stroke=1, fill=0)


# ------------------------------------------------------------------ pages
def page_cover(p):
    c = p.c
    cx = p.W / 2
    cy = p.H * 0.62
    # decorative timer ring motif (light tint + thin accent outlines)
    c.setFillColor(TINT)
    c.circle(cx, cy, 120, stroke=0, fill=1)
    c.setFillColor(white)
    c.circle(cx, cy, 78, stroke=0, fill=1)
    p.ring(cx, cy, 120, 78, n=4, start=90)
    p.text(cx, cy + 6, "one thing", "Head-Italic", 21, ACCENT, align="center")
    p.text(cx, cy - 18, "at a time", "Head-Italic", 21, ACCENT, align="center")

    y = p.H * 0.62 - 175
    p.spaced(cx, y, "UNDATED  ·  PRINTABLE  ·  LOW-OVERWHELM", size=11, cs=2.2,
             align="center")
    p.text(cx, y - 62, "Daily & Weekly", "Head", 50, INK, align="center")
    p.text(cx, y - 116, "Planner", "Head", 50, INK, align="center")
    p.text(cx, y - 148, "Simple pages for busy, wandering minds", "Body-Italic", 15, MUTED,
           align="center")
    # name line
    yb = p.B + 62
    p.text(cx - 140, yb + 2, "This planner belongs to", "Body", 12, MUTED)
    p.hline(cx - 140 + pdfmetrics.stringWidth("This planner belongs to", "Body", 12) + 8,
            cx + 140, yb, BOX, 0.8)
    p.text(cx - 140, yb - 34, "Started on", "Body", 12, MUTED)
    p.hline(cx - 140 + pdfmetrics.stringWidth("Started on", "Body", 12) + 8, cx + 140,
            yb - 36, BOX, 0.8)


def numbered_rows(p, x, y, w, n, gap=32, start=1):
    """Top-3 style rows: numbered circle, writing line, checkbox."""
    for i in range(n):
        yy = y - i * gap
        p.ring_dot(x + 12, yy + 5, 9.5)
        p.text(x + 12, yy + 0.8, str(start + i), "Head", 12.5, ACCENT, align="center")
        p.hline(x + 30, x + w - CB - 12, yy - 2)
        p.checkbox(x + w - CB, yy - 2)


def check_rows(p, x, y, w, items, gap=30):
    for i, s in enumerate(items):
        yy = y - i * gap
        p.checkbox(x, yy)
        if s:
            p.text(x + CB + 8, yy + 3.5, s, "Body", 12, INK, maxw=w - CB - 10)
        else:
            p.hline(x + CB + 8, x + w, yy)


def page_today(p):
    y = p.header("Today", "Date", "Pick three. Everything else is a bonus.")
    gap = 12
    # energy meter on hint line, right side
    ex = p.R - 5 * 15
    p.text(ex - 8, y + 18 - 0.2, "Energy", "Body", 11, MUTED, align="right")
    for i in range(5):
        p.ring_dot(ex + 6 + i * 15, y + 21.6, 5.4)

    h1 = 138
    top = p.box(p.L, y, p.CW, h1, "Top 3", "the only must-dos today")
    numbered_rows(p, p.L + 14, top - 14, p.CW - 28, 3, gap=31)
    y -= h1 + gap

    avail = y - p.B
    h2 = avail * 0.54
    h3 = avail - h2 - gap
    wl = p.CW * 0.57
    wr = p.CW - wl - gap
    # time blocks
    top = p.box(p.L, y, wl, h2, "Time blocks")
    sub = (top - (y - h2) - 6) / 3
    for i, lab in enumerate(["Morning", "Afternoon", "Evening"]):
        sy = top - i * sub
        if i:
            p.hline(p.L + 12, p.L + wl - 12, sy + 2, TINT, 1.2)
        p.text(p.L + 14, sy - 18, lab, "Head", 13, INK)
        p.lines(p.L + 88, p.L + wl - 14, sy - 20, sy - sub + 12)
    # brain dump (dot grid)
    xr = p.L + wl + gap
    top = p.box(xr, y, wr, h2, "Brain dump", "park stray thoughts")
    p.dots(xr + 16, xr + wr - 14, top - 8, y - h2 + 14)
    y -= h2 + gap
    # done list
    top = p.box(p.L, y, wl, h3, "Done list", "yes, that counts")
    p.lines(p.L + 14, p.L + wl - 14, top - 18, y - h3 + 12)
    # check-ins
    top = p.box(xr, y, wr, h3, "Check-ins")
    ix = xr + 14
    p.text(ix, top - 14, "Water", "Head", 12.5, INK)
    for i in range(8):
        p.ring_dot(ix + 60 + (i % 4) * 22 + 7, top - 10 - (i // 4) * 22, 7.2)
    yy = top - 52
    p.text(ix, yy - 14, "Meds", "Head", 12.5, INK)
    for i, lab in enumerate(["AM", "PM"]):
        bx = ix + 60 + i * 52
        p.checkbox(bx, yy - 16)
        p.text(bx + CB + 5, yy - 12.5, lab, "Body", 11.5, INK)
    yy -= 36
    p.text(ix, yy - 14, "Meals", "Head", 12.5, INK)
    for i, lab in enumerate(["Breakfast", "Lunch", "Dinner", "Snack"]):
        bx = ix + 60 + (i % 2) * 78
        by = yy - 16 - (i // 2) * 24
        p.checkbox(bx, by)
        p.text(bx + CB + 5, by + 3.5, lab, "Body", 11.5, INK, maxw=78 - CB - 10)


def page_gentle(p):
    y = p.header("Gentle day", "Date", "Low battery? Shrink the day. Small still counts.")
    gap = 12
    h = 132
    top = p.box(p.L, y, p.CW, h, "The basics", "tick what you manage")
    items = ["Drink some water", "Eat something", "Meds / vitamins",
             "Fresh air or an open window", "Rest without guilt", "Wash face or shower"]
    colw = (p.CW - 28) / 2
    for i, s in enumerate(items):
        p.checkbox(p.L + 16 + (i // 3) * colw, top - 18 - (i % 3) * 29)
        p.text(p.L + 16 + (i // 3) * colw + CB + 8, top - 14.5 - (i % 3) * 29, s,
               "Body", 12.5, INK, maxw=colw - CB - 16)
    y -= h + gap
    for lab, hint in [("One small thing I'll do", None), ("One kind thing for me", None)]:
        h = 88
        top = p.box(p.L, y, p.CW, h, lab, hint)
        p.lines(p.L + 14, p.R - 14, top - 18, y - h + 12)
        y -= h + gap
    avail = y - p.B
    w = (p.CW - gap) / 2
    for i, (lab, hint) in enumerate([("What I need right now", None),
                                     ("Done anyway", "every bit counts")]):
        x = p.L + i * (w + gap)
        top = p.box(x, y, w, avail, lab, hint)
        p.lines(x + 14, x + w - 14, top - 18, y - avail + 12)


def page_week(p):
    y = p.header("This week", "Week of", "Plan loosely. Moving things around is allowed.")
    gap = 10
    h = 134
    top = p.box(p.L, y, p.CW, h, "Big 3 for the week")
    numbered_rows(p, p.L + 14, top - 14, p.CW - 28, 3, gap=31)
    y -= h + gap
    avail = y - p.B
    ch = (avail - 3 * gap) / 4
    cw = (p.CW - gap) / 2
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
            "Don't forget"]
    for i, d in enumerate(days):
        x = p.L + (i % 2) * (cw + gap)
        yt = y - (i // 2) * (ch + gap)
        top = p.box(x, yt, cw, ch, d)
        p.lines(x + 14, x + cw - 14, top - 18, yt - ch + 12)


def page_review(p):
    y = p.header("Week in review", "Week of", "No grades. Just notice what happened.")
    gap = 12
    h = 64
    top = p.box(p.L, y, p.CW, h, "How did this week feel?")
    x0 = p.L + 236
    p.text(x0 - 12, top + 13.8, "rough", "Body-Italic", 11, MUTED, align="right")
    for i in range(5):
        p.ring_dot(x0 + 10 + i * 34, top + 18, 10)
        p.text(x0 + 10 + i * 34, top + 14.2, str(i + 1), "Body", 11, MUTED, align="center")
    p.text(x0 + 4 * 34 + 32, top + 13.8, "really good", "Body-Italic", 11, MUTED)
    y -= h + gap
    h_last = 92
    avail = y - p.B - h_last - gap
    ch = (avail - gap) / 2
    cw = (p.CW - gap) / 2
    cells = [("Wins", "big or small"), ("What helped", None),
             ("What got in the way", None), ("Carry forward / let go", None)]
    for i, (lab, hint) in enumerate(cells):
        x = p.L + (i % 2) * (cw + gap)
        yt = y - (i // 2) * (ch + gap)
        top = p.box(x, yt, cw, ch, lab, hint)
        p.lines(x + 14, x + cw - 14, top - 18, yt - ch + 12)
    y -= 2 * ch + 2 * gap
    top = p.box(p.L, y, p.CW, h_last, "Next week I want to feel")
    p.lines(p.L + 14, p.R - 14, top - 18, y - h_last + 12)


def page_habits(p):
    y = p.header("Habit tracker", "Month", "Tick it when you do it. Missed a day? Just start again.")
    namew = 112
    gridx = p.L + namew
    cell = (p.R - gridx) / 31
    rows = 14
    rh = 9 * mm
    # day numbers
    for d in range(31):
        p.text(gridx + (d + 0.5) * cell, y - 12, str(d + 1), "Body-Bold", 8, ACCENT,
               align="center")
    p.spaced(p.L, y - 12, "HABIT", size=9, cs=1.1)
    top = y - 20
    c = p.c
    bottom = top - rows * rh
    # light row guides
    for r in range(rows + 1):
        yy = top - r * rh
        p.hline(p.L, p.R, yy, LINE, 0.6)
    for d in range(32):
        xx = gridx + d * cell
        c.setStrokeColor(LINE if d % 7 else BOX)
        c.setLineWidth(0.6 if d % 7 else 0.9)
        c.line(xx, top, xx, bottom)
    y = bottom - 14
    h = y - p.B
    top = p.box(p.L, y, p.CW, h, "Little wins this month")
    p.lines(p.L + 14, p.R - 14, top - 18, y - h + 12)


def page_braindump(p):
    y = p.header("Brain dump", "Date", "Empty your head onto the page. Sort it later (or never).")
    gap = 12
    avail = y - p.B
    h1 = avail * 0.6
    top = p.box(p.L, y, p.CW, h1, "Everything on my mind")
    p.lines(p.L + 14, p.R - 14, top - 18, y - h1 + 12)
    y -= h1 + gap
    h2 = avail - h1 - gap
    w = (p.CW - gap) / 2
    for i, lab in enumerate(["Do soon", "Later", "Ask someone", "Let it go"]):
        x = p.L + (i % 2) * (w + gap)
        hh = (h2 - gap) / 2
        yt = y - (i // 2) * (hh + gap)
        top = p.box(x, yt, w, hh, lab)
        p.lines(x + 14, x + w - 14, top - 16, yt - hh + 12)


def page_focus(p):
    y = p.header("One thing at a time", "Date",
                 "Colour one slice every 5 minutes. Rest after each ring.")
    gap = 12
    h = 92
    top = p.box(p.L, y, p.CW, h, "My one thing")
    p.lines(p.L + 14, p.R - 14, top - 18, y - h + 12)
    y -= h + gap
    h = 72
    top = p.box(p.L, y, p.CW, h, "First tiny step")
    p.lines(p.L + 14, p.R - 14, top - 18, y - h + 12)
    y -= h + gap
    # rings
    h = 200
    top = p.box(p.L, y, p.CW, h, "Focus rings", "4 × 25 minutes")
    slot = (p.CW - 20) / 4
    r_out = min(slot / 2 - 10, 54)
    for i in range(4):
        cx = p.L + 10 + slot * (i + 0.5)
        cy = top - 14 - r_out
        p.ring(cx, cy, r_out, r_out * 0.6, n=5)
        p.text(cx, cy - 4, "25", "Head", 16, ACCENT, align="center")
        p.text(cx, cy - 15, "min", "Body", 8.5, MUTED, align="center")
        by = cy - r_out - 30
        p.checkbox(cx - 26, by)
        p.text(cx - 26 + CB + 6, by + 3.5, "break", "Body", 11.5, INK)
    y -= h + gap
    avail = y - p.B
    h1 = avail - 88 - gap
    top = p.box(p.L, y, p.CW, h1, "Distraction parking lot", "write it, then let it wait")
    p.lines(p.L + 14, p.R - 14, top - 18, y - h1 + 12)
    y -= h1 + gap
    top = p.box(p.L, y, p.CW, 88, "When I finish, I get to")
    p.lines(p.L + 14, p.R - 14, top - 18, y - 88 + 12)


def page_routine(p, title, hint, hard_label):
    y = p.header(title, "Week of", hint)
    gap = 12
    days = ["M", "T", "W", "T", "F", "S", "S"]
    dcol = 26
    stepw = p.CW - 7 * dcol - 28
    rows = 11
    rh = 30
    h = 34 + 18 + rows * rh + 6
    top = p.box(p.L, y, p.CW, h, "My steps", "write them once, tick daily")
    gx = p.L + 14 + stepw + 8
    for i, d in enumerate(days):
        p.text(gx + i * dcol + dcol / 2, top - 8, d, "Body-Bold", 10, ACCENT, align="center")
    for r in range(rows):
        yy = top - 22 - (r + 1) * rh + 8
        p.hline(p.L + 14, p.L + 14 + stepw, yy)
        for i in range(7):
            p.checkbox(gx + i * dcol + (dcol - CB) / 2, yy)
    y -= h + gap
    avail = y - p.B
    h2 = 132
    top = p.box(p.L, y, p.CW, h2, hard_label, "the bare minimum")
    check_rows(p, p.L + 16, top - 18, p.CW - 32, [None, None, None], gap=31)
    y -= h2 + gap
    h3 = avail - h2 - gap
    top = p.box(p.L, y, p.CW, h3, "How I want to feel")
    p.lines(p.L + 14, p.R - 14, top - 18, y - h3 + 12)


def page_morning(p):
    page_routine(p, "Morning routine", "Same steps, less deciding. Tick each day.",
                 "Hard-day version")


def page_evening(p):
    page_routine(p, "Evening routine", "Set up tomorrow-you for an easier start.",
                 "Hard-day version")


def page_mood(p):
    y = p.header("Mood & energy", "Month", "Fill one circle for each, every day. Patterns will appear.")
    gap = 16
    half = (p.CW - gap) / 2
    rows = 16
    rh = 26
    step = 14
    r = 6.3
    c = p.c
    for col in range(2):
        x = p.L + col * (half + gap)
        dx, mx = x + 4, x + 26
        ex = mx + 5 * step + 8
        nx = ex + 5 * step + 8
        p.spaced(dx, y - 12, "DAY", size=8.5, cs=1)
        p.spaced(mx, y - 12, "MOOD", size=8.5, cs=1)
        p.spaced(ex, y - 12, "ENERGY", size=8.5, cs=1)
        p.spaced(nx, y - 12, "NOTE", size=8.5, cs=1)
        for i in range(rows):
            d = col * rows + i + 1
            if d > 31:
                break
            yy = y - 22 - (i + 1) * rh
            p.text(dx + 6, yy + 8, str(d), "Head", 11, INK, align="center")
            for k in range(5):
                p.ring_dot(mx + r + k * step, yy + 12, r, ACCENT, 0.8)
                p.ring_dot(ex + r + k * step, yy + 12, r, ACCENT, 0.8)
            p.hline(nx, x + half, yy + 4)
    y = y - 22 - rows * rh - 18
    p.text(p.L, y, "Key:", "Body-Bold", 10.5, ACCENT)
    p.text(p.L + 28, y, "circles go 1 to 5, left to right.  Mood: 1 = low, 5 = great.  "
           "Energy: 1 = running on empty, 5 = fully charged.", "Body", 10.5, MUTED,
           maxw=p.CW - 30)
    y -= 14
    h = y - p.B
    top = p.box(p.L, y, p.CW, h, "Patterns I noticed")
    p.lines(p.L + 14, p.R - 14, top - 18, y - h + 12)


def page_notes(p):
    y = p.header("Notes", "Date")
    p.lines(p.L, p.R, y - 24, p.B + 4)


PAGES = [page_cover, page_today, page_gentle, page_week, page_review, page_habits,
         page_braindump, page_focus, page_morning, page_evening, page_mood, page_notes]


def build_pdf(size, path):
    c = canvas.Canvas(path, pagesize=size, initialFontName="Body", initialFontSize=11)
    c.setTitle("ADHD-Friendly Daily & Weekly Planner (Undated)")
    c.setAuthor("Quiet Desk Printables")
    for fn in PAGES:
        p = P(c, size)
        fn(p)
        p.footer()
        c.showPage()
    c.save()


# --------------------------------------------------------------- previews
PBG = HexColor("#EEF3F1")


def render_pages(pdf, outdir, dpi=170):
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), pdf, os.path.join(outdir, "pg")],
                   check=True)
    files = sorted(f for f in os.listdir(outdir) if f.startswith("pg"))
    return [os.path.join(outdir, f) for f in files]


def draw_page_img(c, img, cx, cy, h, angle=0, aspect=8.5 / 11):
    w = h * aspect
    c.saveState()
    c.translate(cx, cy)
    c.rotate(angle)
    # soft shadow
    c.saveState()
    for i, a in enumerate([0.05, 0.05, 0.06, 0.07]):
        o = 14 - i * 3
        c.setFillColor(HexColor("#2E3836"), alpha=a)
        c.roundRect(-w / 2 - o / 2 + 6, -h / 2 - o / 2 - 10, w + o, h + o, 6, stroke=0, fill=1)
    c.restoreState()
    c.drawImage(img, -w / 2, -h / 2, w, h)
    c.setStrokeColor(HexColor("#D5DEDB"))
    c.setLineWidth(1)
    c.rect(-w / 2, -h / 2, w, h, stroke=1, fill=0)
    c.restoreState()
    return w


def pill(c, x, y, s, size=26, fg=white, bg=ACCENT, font="Body-Bold"):
    w = pdfmetrics.stringWidth(s, font, size) + size * 1.4
    h = size * 1.75
    c.setFillColor(bg)
    c.roundRect(x, y, w, h, h / 2, stroke=0, fill=1)
    c.setFillColor(fg)
    c.setFont(font, size)
    c.drawCentredString(x + w / 2, y + h * 0.33, s)
    return w


def preview_canvas(path, W=1600, H=1200):
    c = canvas.Canvas(path, pagesize=(W, H))
    c.setFillColor(PBG)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    return c


def bullets(c, x, y, items, size=30, gap=62, maxw=600):
    for s in items:
        c.setFillColor(ACCENT)
        c.circle(x + 8, y + size * 0.32, 7, stroke=0, fill=1)
        fs = size
        while pdfmetrics.stringWidth(s, "Body", fs) > maxw - 34:
            fs -= 1
        c.setFillColor(INK)
        c.setFont("Body", fs)
        c.drawString(x + 34, y, s)
        y -= gap
    return y


def make_previews(imgs, tmp):
    n = len(PAGE_NAMES)
    out = []

    # 1. hero
    pdf = os.path.join(tmp, "p1.pdf")
    c = preview_canvas(pdf)
    draw_page_img(c, imgs[7], 1150, 610, 840, angle=7)
    draw_page_img(c, imgs[1], 1060, 590, 900, angle=-3)
    x = 90
    sp = P(c, (1600, 1200))
    sp.spaced(x, 1010, "PRINTABLE  ·  UNDATED", size=24, cs=4)
    c.setFillColor(INK)
    for i, s in enumerate(["ADHD-Friendly", "Daily & Weekly", "Planner"]):
        c.setFont("Head", 84)
        c.drawString(x, 900 - i * 98, s)
    c.setFont("Body-Italic", 32)
    c.setFillColor(MUTED)
    c.drawString(x, 640, "Calm, low-overwhelm pages that help")
    c.drawString(x, 598, "you focus on one thing at a time")
    pill(c, x, 470, f"{n} pages", size=34)
    c.setFillColor(INK)
    c.setFont("Body-Bold", 30)
    c.drawString(x, 400, "Instant download · US Letter + A4")
    bullets(c, x, 320, ["Top 3 daily page + gentle day page", "Habit, mood & energy trackers",
                        "Focus rings + routine checklists"], size=27, gap=52, maxw=560)
    c.showPage()
    c.save()
    out.append(("01-hero.png", pdf))

    # 2. Today page feature
    pdf = os.path.join(tmp, "p2.pdf")
    c = preview_canvas(pdf)
    draw_page_img(c, imgs[1], 480, 600, 1060)
    x = 940
    c.setFillColor(ACCENT)
    sp = P(c, (1600, 1200))
    sp.spaced(x, 1000, "THE DAILY PAGE", size=24, cs=4)
    c.setFillColor(INK)
    c.setFont("Head", 66)
    c.drawString(x, 910, "Today,")
    c.drawString(x, 834, "simplified")
    bullets(c, x, 700, ["Top 3 only, no endless lists", "Big morning / afternoon / evening blocks",
                        "Brain-dump box for stray thoughts",
                        "A done list to see your wins", "Water, meds & meal check-ins",
                        "Energy meter to colour in"], size=30, gap=66, maxw=620)
    c.showPage()
    c.save()
    out.append(("02-today-page.png", pdf))

    # 3 & 4. two-page spreads
    for fname, title, sub, a, b in [
        ("03-focus-routines.png", "Focus & routines",
         "Colour-in focus rings, a distraction parking lot and tick-box routines", 7, 8),
        ("04-trackers.png", "Habit, mood & energy trackers",
         "31-day grids you can reuse every month", 5, 10),
    ]:
        pdf = os.path.join(tmp, fname + ".pdf")
        c = preview_canvas(pdf)
        c.setFillColor(INK)
        c.setFont("Head", 62)
        c.drawCentredString(800, 1090, title)
        c.setFont("Body-Italic", 30)
        c.setFillColor(MUTED)
        c.drawCentredString(800, 1040, sub)
        draw_page_img(c, imgs[a], 800 - 375, 500, 920)
        draw_page_img(c, imgs[b], 800 + 375, 500, 920)
        c.showPage()
        c.save()
        out.append((fname, pdf))

    # 5. what's included
    pdf = os.path.join(tmp, "p5.pdf")
    c = preview_canvas(pdf)
    c.setFillColor(INK)
    c.setFont("Head", 64)
    c.drawCentredString(800, 1080, f"What's included: {n} pages")
    c.setFont("Body", 30)
    c.setFillColor(MUTED)
    c.drawCentredString(800, 1030, "Undated PDFs in US Letter + A4 · print as many as you like")
    cols, tw, gx = 6, 230, 26
    th = tw * 11 / 8.5
    x0 = (1600 - (cols * tw + (cols - 1) * gx)) / 2
    for i in range(n):
        col, row = i % cols, i // cols
        cx = x0 + col * (tw + gx) + tw / 2
        cy = 950 - row * (th + 110) - th / 2
        draw_page_img(c, imgs[i], cx, cy, th)
        c.setFillColor(INK)
        c.setFont("Body-Bold", 23)
        lab = f"{i + 1}. {PAGE_NAMES[i]}"
        fs = 23
        while pdfmetrics.stringWidth(lab, "Body-Bold", fs) > tw + gx - 6:
            fs -= 1
        c.setFont("Body-Bold", fs)
        c.drawCentredString(cx, cy - th / 2 - 40, lab)
    c.showPage()
    c.save()
    out.append(("05-whats-included.png", pdf))

    # 6. sizes / print info
    pdf = os.path.join(tmp, "p6.pdf")
    c = preview_canvas(pdf)
    draw_page_img(c, imgs[0], 470, 600, 940)
    x = 900
    sp = P(c, (1600, 1200))
    sp.spaced(x, 940, "PRINT AT HOME", size=24, cs=4)
    c.setFillColor(INK)
    c.setFont("Head", 62)
    c.drawString(x, 850, "Two sizes,")
    c.drawString(x, 778, "ready to print")
    bullets(c, x, 650, ["US Letter (8.5 × 11 in)", "A4 (210 × 297 mm)",
                        "Undated: reuse any week", "White background, light ink",
                        "Instant digital download"], size=32, gap=68, maxw=640)
    c.showPage()
    c.save()
    out.append(("06-sizes.png", pdf))

    for fname, pdfp in out:
        base = os.path.join(tmp, "o_" + fname[:-4])
        subprocess.run(["pdftoppm", "-png", "-singlefile", "-scale-to", "2000", pdfp, base],
                       check=True)
        shutil.move(base + ".png", os.path.join(PREV, fname))


def main():
    os.makedirs(PREV, exist_ok=True)
    letter_pdf = os.path.join(HERE, f"{SLUG}-US-Letter.pdf")
    a4_pdf = os.path.join(HERE, f"{SLUG}-A4.pdf")
    build_pdf(letter, letter_pdf)
    build_pdf(A4, a4_pdf)
    tmp = tempfile.mkdtemp()
    try:
        imgs = render_pages(letter_pdf, tmp)
        assert len(imgs) == len(PAGE_NAMES)
        for f in os.listdir(PREV):
            if f.endswith(".png"):
                os.remove(os.path.join(PREV, f))
        make_previews(imgs, tmp)
    finally:
        shutil.rmtree(tmp)
    print("built", letter_pdf, a4_pdf, sorted(os.listdir(PREV)))


if __name__ == "__main__":
    main()
