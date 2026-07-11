#!/usr/bin/env python3
"""Generate a guitar-theory cheat sheet entirely from programmatic data.

The artwork is drawn from scratch as SVG and then rasterized to PNG.
No source image pixels are copied into the result.

Orientation used everywhere:
    string 1 (high E) = top horizontal string
    string 6 (low E)  = bottom horizontal string
    frets increase from left to right

Default output is 3840x2160 (2x Full HD). A 1920x1080 preview is also
created unless --no-preview is passed.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

import cairosvg
import svgwrite

# -----------------------------------------------------------------------------
# Music data
# -----------------------------------------------------------------------------

# Top-to-bottom string order: string 1 through string 6.
# Pitch classes are E, B, G, D, A, E in standard tuning.
OPEN_STRING_PCS: Tuple[int, ...] = (4, 11, 7, 2, 9, 4)
ROOT_PC = 0  # C is used only to place the movable interval patterns.


@dataclass(frozen=True)
class Position:
    shape: str
    position_number: int
    fret_start: int
    fret_end: int

    @property
    def label(self) -> str:
        return f"{self.shape} Shape"

    @property
    def position_label(self) -> str:
        return f"Position {self.position_number}"


# Five overlapping CAGED windows around C. Each window spans five frets.
POSITIONS: Mapping[str, Position] = {
    "E": Position("E", 1, 7, 11),
    "D": Position("D", 2, 9, 13),
    "C": Position("C", 3, 12, 16),
    "A": Position("A", 4, 14, 18),
    "G": Position("G", 5, 16, 20),
}

LEFT_ROW_ORDER: Tuple[str, ...] = ("C", "A", "G", "E", "D")

# The right-side mode/scale strip follows the CAGED cycle from the lower
# G-shape position and stops when it returns to G. It intentionally does not
# continue to the next E shape above fret 20.
SCALE_POSITIONS: Tuple[Position, ...] = (
    Position("G", 1, 4, 8),
    Position("E", 2, 7, 11),
    Position("D", 3, 9, 13),
    Position("C", 4, 12, 16),
    Position("A", 5, 14, 18),
    Position("G", 6, 16, 20),
)
SCALE_SPAN = Position(
    "Scale",
    0,
    min(p.fret_start for p in SCALE_POSITIONS),
    max(p.fret_end for p in SCALE_POSITIONS),
)

# Explicit major-chord CAGED voicings for C major. Keys are string numbers
# (1=high E at top, 6=low E at bottom); values are absolute fret numbers.
CAGED_VOICINGS: Mapping[str, Mapping[int, int]] = {
    "C": {1: 12, 2: 13, 3: 12, 4: 14, 5: 15},
    "A": {1: 15, 2: 17, 3: 17, 4: 17, 5: 15},
    "G": {1: 20, 2: 17, 3: 17, 4: 17, 5: 19, 6: 20},
    "E": {1: 8, 2: 8, 3: 9, 4: 10, 5: 10, 6: 8},
    "D": {1: 12, 2: 13, 3: 12, 4: 10},
}


@dataclass(frozen=True)
class Formula:
    title: str
    intervals: Tuple[Tuple[int, str], ...]

    @property
    def pitch_classes(self) -> Tuple[int, ...]:
        return tuple(pc for pc, _ in self.intervals)

    @property
    def labels(self) -> Tuple[str, ...]:
        return tuple(label for _, label in self.intervals)

    @property
    def label_by_pc(self) -> Dict[int, str]:
        return dict(self.intervals)


ARPEGGIOS: Tuple[Formula, ...] = (
    Formula("Major Arpeggio", ((0, "R"), (4, "3"), (7, "5"))),
    Formula("Minor Arpeggio", ((0, "R"), (3, "b3"), (7, "5"))),
    Formula("Dim Arpeggio", ((0, "R"), (3, "b3"), (6, "b5"))),
    Formula("Major 7 Arpeggio", ((0, "R"), (4, "3"), (7, "5"), (11, "7"))),
    Formula("Dominant 7 Arpeggio", ((0, "R"), (4, "3"), (7, "5"), (10, "b7"))),
    Formula("Minor 7 Arpeggio", ((0, "R"), (3, "b3"), (7, "5"), (10, "b7"))),
    Formula("Dim 7 Arpeggio", ((0, "R"), (3, "b3"), (6, "b5"), (9, "bb7"))),
)

SCALES: Tuple[Formula, ...] = (
    Formula("Ionian Mode (Major Scale)", ((0, "R"), (2, "2"), (4, "3"), (5, "4"), (7, "5"), (9, "6"), (11, "7"))),
    Formula("Aeolian Mode (Natural Minor Scale)", ((0, "R"), (2, "2"), (3, "b3"), (5, "4"), (7, "5"), (8, "b6"), (10, "b7"))),
    Formula("Major Pentatonic Scale", ((0, "R"), (2, "2"), (4, "3"), (7, "5"), (9, "6"))),
    Formula("Minor Pentatonic Scale", ((0, "R"), (3, "b3"), (5, "4"), (7, "5"), (10, "b7"))),
    Formula("Major Blues Scale", ((0, "R"), (2, "2"), (3, "b3"), (4, "3"), (7, "5"), (9, "6"))),
    Formula("Minor Blues Scale", ((0, "R"), (3, "b3"), (5, "4"), (6, "b5"), (7, "5"), (10, "b7"))),
)

# Rainbow system requested by the user. Flattened intervals stay in the same
# hue family but use a distinguishable shade.
NOTE_COLORS: Mapping[str, str] = {
    "R": "#FF3B30",
    "1": "#FF3B30",
    "2": "#FF8A1F",
    "b3": "#E5A100",
    "3": "#FFD60A",
    "4": "#34C759",
    "b5": "#5E5CE6",
    "5": "#0A84FF",
    "b6": "#7557E8",
    "6": "#8E44AD",
    "b7": "#C23BB7",
    "7": "#BF5AF2",
    "bb7": "#A442B8",
}

# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------


def interval_at(string_number: int, fret: int) -> int:
    """Return the pitch-class interval from C at a string/fret coordinate."""
    open_pc = OPEN_STRING_PCS[string_number - 1]
    return (open_pc + fret - ROOT_PC) % 12


def validate_music_data() -> None:
    """Fail early if a hard-coded voicing or formula is inconsistent."""
    major_triad = {0, 4, 7}
    for shape, voicing in CAGED_VOICINGS.items():
        found = {interval_at(string_no, fret) for string_no, fret in voicing.items()}
        if not found.issubset(major_triad) or 0 not in found or 4 not in found or 7 not in found:
            raise ValueError(f"Invalid {shape}-shape CAGED voicing: intervals={sorted(found)}")
        p = POSITIONS[shape]
        for fret in voicing.values():
            if not (p.fret_start <= fret <= p.fret_end):
                raise ValueError(f"{shape}-shape fret {fret} is outside its drawing window")

    expected = {
        "Major Arpeggio": (0, 4, 7),
        "Minor Arpeggio": (0, 3, 7),
        "Dim Arpeggio": (0, 3, 6),
        "Major 7 Arpeggio": (0, 4, 7, 11),
        "Dominant 7 Arpeggio": (0, 4, 7, 10),
        "Minor 7 Arpeggio": (0, 3, 7, 10),
        "Dim 7 Arpeggio": (0, 3, 6, 9),
    }
    for formula in ARPEGGIOS:
        if formula.pitch_classes != expected[formula.title]:
            raise ValueError(f"Unexpected formula for {formula.title}")


# -----------------------------------------------------------------------------
# SVG drawing helpers
# --------------------------------------------------------------------------------------

BG = "#07090C"
PANEL = "#0E1218"
PANEL_ALT = "#111720"
HEADER = "#141B24"
GRID = "#8B949E"
GRID_DIM = "#4A535E"
BORDER = "#66717E"
TEXT = "#F5F7FA"
TEXT_MUTED = "#AAB2BC"
BLACK = "#050608"

FONT_FAMILY = "DejaVu Sans, Arial, sans-serif"
FONT_CONDENSED = "DejaVu Sans Condensed, Arial Narrow, sans-serif"


def add_rect(dwg: svgwrite.Drawing, x: float, y: float, w: float, h: float, *,
             fill: str, stroke: str | None = None, stroke_width: float = 1,
             radius: float = 0) -> None:
    dwg.add(dwg.rect(insert=(x, y), size=(w, h), rx=radius, ry=radius,
                     fill=fill, stroke=stroke or "none", stroke_width=stroke_width))


def add_line(dwg: svgwrite.Drawing, x1: float, y1: float, x2: float, y2: float,
             *, stroke: str = GRID, stroke_width: float = 1, opacity: float = 1.0) -> None:
    dwg.add(dwg.line(start=(x1, y1), end=(x2, y2), stroke=stroke,
                     stroke_width=stroke_width, opacity=opacity))


def add_text(dwg: svgwrite.Drawing, x: float, y: float, text: str, *,
             size: float, fill: str = TEXT, weight: str = "normal",
             anchor: str = "start", family: str = FONT_FAMILY,
             opacity: float = 1.0, letter_spacing: float = 0) -> None:
    dwg.add(dwg.text(text, insert=(x, y), fill=fill, font_size=size,
                     font_family=family, font_weight=weight,
                     text_anchor=anchor, opacity=opacity,
                     letter_spacing=letter_spacing))


def add_multiline_centered(dwg: svgwrite.Drawing, cx: float, top_y: float,
                           lines: Sequence[str], *, size: float,
                           line_height: float, fill: str = TEXT,
                           weight: str = "bold") -> None:
    for i, line in enumerate(lines):
        add_text(dwg, cx, top_y + i * line_height, line, size=size,
                 fill=fill, weight=weight, anchor="middle", family=FONT_CONDENSED)


def split_heading(title: str) -> Tuple[str, ...]:
    replacements = {
        "Major Arpeggio": ("Major", "Arpeggio"),
        "Minor Arpeggio": ("Minor", "Arpeggio"),
        "Dim Arpeggio": ("Dim", "Arpeggio"),
        "Major 7 Arpeggio": ("Major 7", "Arpeggio"),
        "Dominant 7 Arpeggio": ("Dominant 7", "Arpeggio"),
        "Minor 7 Arpeggio": ("Minor 7", "Arpeggio"),
        "Dim 7 Arpeggio": ("Dim 7", "Arpeggio"),
    }
    return replacements.get(title, (title,))


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    color = hex_color.lstrip("#")
    return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def label_text_color(fill: str) -> str:
    r, g, b = hex_to_rgb(fill)
    # Relative perceived brightness. Dark text on bright yellow/green/orange.
    brightness = 0.299 * r + 0.587 * g + 0.114 * b
    return BLACK if brightness > 155 else "#FFFFFF"


def draw_note_chip(dwg: svgwrite.Drawing, cx: float, cy: float, label: str,
                   radius: float, *, outline: bool = True) -> None:
    fill = NOTE_COLORS.get(label, "#67717D")
    dwg.add(dwg.circle(center=(cx, cy), r=radius, fill=fill,
                       stroke="#FFFFFF" if outline else "none",
                       stroke_width=max(1.0, radius * 0.09)))
    fs = radius * (0.93 if len(label) == 1 else 0.72)
    add_text(dwg, cx, cy + fs * 0.36, label, size=fs,
             fill=label_text_color(fill), weight="bold", anchor="middle",
             family=FONT_CONDENSED)


def draw_formula_chips(dwg: svgwrite.Drawing, labels: Sequence[str],
                       x: float, cy: float, *, max_width: float,
                       radius: float = 15, gap: float = 8,
                       align: str = "left") -> None:
    total = len(labels) * radius * 2 + max(0, len(labels) - 1) * gap
    start_x = x if align == "left" else x - total
    if total > max_width and len(labels) > 0:
        scale = max_width / total
        radius *= scale
        gap *= scale
        total = len(labels) * radius * 2 + max(0, len(labels) - 1) * gap
        start_x = x if align == "left" else x - total
    for i, label in enumerate(labels):
        cx = start_x + radius + i * (2 * radius + gap)
        draw_note_chip(dwg, cx, cy, label, radius, outline=False)


def chord_notes_for_window(position: Position, formula: Formula) -> List[Tuple[int, int, str]]:
    labels = formula.label_by_pc
    notes: List[Tuple[int, int, str]] = []
    for string_number in range(1, 7):
        for fret in range(position.fret_start, position.fret_end + 1):
            pc = interval_at(string_number, fret)
            if pc in labels:
                notes.append((string_number, fret, labels[pc]))
    return notes


def caged_notes(shape: str) -> List[Tuple[int, int, str]]:
    labels = {0: "R", 4: "3", 7: "5"}
    return [
        (string_number, fret, labels[interval_at(string_number, fret)])
        for string_number, fret in CAGED_VOICINGS[shape].items()
    ]


def draw_fretboard(dwg: svgwrite.Drawing, x: float, y: float, w: float, h: float,
                   position: Position, notes: Sequence[Tuple[int, int, str]], *,
                   show_orientation_labels: bool = True,
                   compact: bool = False) -> None:
    """Draw a horizontal fretboard with string 1 on top and string 6 at bottom."""
    # Extra left room for string-number labels.
    label_pad = 17 if show_orientation_labels else 0
    gx = x + label_pad
    gw = w - label_pad
    gh = h
    n_frets = position.fret_end - position.fret_start + 1
    string_gap = gh / 5.0
    fret_cell = gw / n_frets

    # Subtle backing makes the fretboard readable inside dense cells.
    add_rect(dwg, gx, y, gw, gh, fill="#090C10", stroke=GRID_DIM,
             stroke_width=1.2, radius=4)

    # Six horizontal strings: 1/high-E on top; 6/low-E on bottom.
    for s in range(1, 7):
        yy = y + (s - 1) * string_gap
        width = 1.1 + (s - 1) * 0.22
        add_line(dwg, gx, yy, gx + gw, yy, stroke=GRID,
                 stroke_width=width, opacity=0.95)

    # Fret boundaries, increasing left to right.
    for i in range(n_frets + 1):
        xx = gx + i * fret_cell
        add_line(dwg, xx, y, xx, y + gh, stroke=GRID,
                 stroke_width=1.35 if i else 2.2, opacity=0.90)

    if show_orientation_labels:
        fs = 13 if compact else 15
        add_text(dwg, x + 5, y + fs * 0.34, "1", size=fs, fill=TEXT_MUTED,
                 weight="bold", anchor="middle", family=FONT_CONDENSED)
        add_text(dwg, x + 5, y + gh + fs * 0.34, "6", size=fs, fill=TEXT_MUTED,
                 weight="bold", anchor="middle", family=FONT_CONDENSED)

    radius = min(string_gap * 0.31, fret_cell * 0.25)
    radius = max(7.0, radius)
    for string_number, fret, label in notes:
        if not (position.fret_start <= fret <= position.fret_end):
            continue
        cx = gx + (fret - position.fret_start + 0.5) * fret_cell
        cy = y + (string_number - 1) * string_gap
        draw_note_chip(dwg, cx, cy, label, radius)


def draw_panel_border(dwg: svgwrite.Drawing, x: float, y: float, w: float, h: float,
                      radius: float = 10) -> None:
    add_rect(dwg, x, y, w, h, fill=PANEL, stroke=BORDER,
             stroke_width=2, radius=radius)


# -----------------------------------------------------------------------------
# Poster construction
# -----------------------------------------------------------------------------


def create_svg(width: int, height: int, svg_path: Path) -> None:
    if abs(width / height - 16 / 9) > 0.015:
        raise ValueError("This layout is designed for a 16:9 canvas.")

    validate_music_data()

    dwg = svgwrite.Drawing(str(svg_path), size=(width, height),
                           viewBox=f"0 0 {width} {height}")
    add_rect(dwg, 0, 0, width, height, fill=BG)

    # Global layout.
    margin = width * 0.012
    title_h = height * 0.070
    legend_h = height * 0.090
    content_y = margin + title_h
    content_h = height - content_y - legend_h - margin * 1.4
    gap = width * 0.008
    left_w = width * 0.642
    right_x = margin + left_w + gap
    right_w = width - right_x - margin

    # Title and orientation statement.
    add_text(dwg, margin, margin + height * 0.034,
             "GUITAR THEORY — CAGED ARPEGGIOS & SCALES",
             size=height * 0.026, fill=TEXT, weight="bold",
             family=FONT_CONDENSED, letter_spacing=0.8)
    orientation = (
        "STANDARD TUNING • STRING 1 / HIGH E IS THE TOP LINE • "
        "STRING 6 / LOW E IS THE BOTTOM LINE • FRETS INCREASE LEFT → RIGHT"
    )
    add_text(dwg, width - margin, margin + height * 0.033,
             orientation, size=height * 0.0102, fill=TEXT_MUTED,
             weight="bold", anchor="end", family=FONT_CONDENSED,
             letter_spacing=0.25)

    # ------------------------------- Left grid -------------------------------
    left_x = margin
    draw_panel_border(dwg, left_x, content_y, left_w, content_h, radius=10)

    header_h = content_h * 0.105
    row_h = (content_h - header_h) / len(LEFT_ROW_ORDER)
    shape_col_w = left_w * 0.096
    data_col_w = (left_w - shape_col_w) / 8.0

    # Header backgrounds and column divisions.
    add_rect(dwg, left_x, content_y, left_w, header_h,
             fill=HEADER, stroke="none", radius=10)
    add_text(dwg, left_x + shape_col_w / 2, content_y + header_h * 0.42,
             "SHAPE", size=header_h * 0.20, weight="bold", anchor="middle",
             family=FONT_CONDENSED)
    add_text(dwg, left_x + shape_col_w / 2, content_y + header_h * 0.70,
             "POSITION", size=header_h * 0.12, fill=TEXT_MUTED,
             weight="bold", anchor="middle", family=FONT_CONDENSED)

    column_defs: List[Tuple[str, Tuple[str, ...]]] = [
        ("CAGED", ("R", "3", "5")),
        *[(f.title, f.labels) for f in ARPEGGIOS],
    ]

    for i, (title, formula_labels) in enumerate(column_defs):
        x = left_x + shape_col_w + i * data_col_w
        add_line(dwg, x, content_y, x, content_y + content_h,
                 stroke=BORDER, stroke_width=1.5)
        lines = split_heading(title)
        top = content_y + header_h * (0.30 if len(lines) == 1 else 0.25)
        add_multiline_centered(dwg, x + data_col_w / 2, top, lines,
                               size=header_h * 0.165,
                               line_height=header_h * 0.18,
                               weight="bold")
        draw_formula_chips(dwg, formula_labels,
                           x + data_col_w / 2,
                           content_y + header_h * 0.82,
                           max_width=data_col_w * 0.78,
                           radius=header_h * 0.070,
                           gap=header_h * 0.025,
                           align="right")

    # Rows and fretboards.
    for row_index, shape in enumerate(LEFT_ROW_ORDER):
        position = POSITIONS[shape]
        y = content_y + header_h + row_index * row_h
        if row_index % 2 == 1:
            add_rect(dwg, left_x, y, left_w, row_h, fill=PANEL_ALT)
        add_line(dwg, left_x, y, left_x + left_w, y,
                 stroke=BORDER, stroke_width=1.3)

        add_text(dwg, left_x + shape_col_w / 2,
                 y + row_h * 0.43, position.label,
                 size=row_h * 0.082, weight="bold", anchor="middle",
                 family=FONT_CONDENSED)
        add_text(dwg, left_x + shape_col_w / 2,
                 y + row_h * 0.58, position.position_label,
                 size=row_h * 0.060, fill=TEXT_MUTED, anchor="middle",
                 family=FONT_CONDENSED)

        for col_index, (title, _) in enumerate(column_defs):
            cell_x = left_x + shape_col_w + col_index * data_col_w
            if col_index > 0:
                add_line(dwg, cell_x, y, cell_x, y + row_h,
                         stroke=GRID_DIM, stroke_width=0.8, opacity=0.75)
            pad_x = data_col_w * 0.075
            board_x = cell_x + pad_x
            board_w = data_col_w - 2 * pad_x
            board_h = row_h * 0.58
            board_y = y + row_h * 0.22

            if title == "CAGED":
                notes = caged_notes(shape)
            else:
                formula = next(f for f in ARPEGGIOS if f.title == title)
                notes = chord_notes_for_window(position, formula)
            draw_fretboard(dwg, board_x, board_y, board_w, board_h,
                           position, notes, show_orientation_labels=True)

    # ----------------------------- Right scales ------------------------------
    panel_gap = content_h * 0.010
    scale_panel_h = (content_h - panel_gap * (len(SCALES) - 1)) / len(SCALES)

    for idx, scale in enumerate(SCALES):
        py = content_y + idx * (scale_panel_h + panel_gap)
        draw_panel_border(dwg, right_x, py, right_w, scale_panel_h, radius=10)
        title_bar_h = scale_panel_h * 0.245
        add_rect(dwg, right_x, py, right_w, title_bar_h,
                 fill=HEADER, radius=10)
        # Cover bottom title-bar rounding so only the outer panel corners remain rounded.
        add_rect(dwg, right_x, py + title_bar_h * 0.60, right_w,
                 title_bar_h * 0.40, fill=HEADER)

        add_text(dwg, right_x + right_w * 0.025,
                 py + title_bar_h * 0.58, scale.title,
                 size=title_bar_h * 0.35, weight="bold",
                 family=FONT_CONDENSED)
        add_text(dwg, right_x + right_w * 0.720,
                 py + title_bar_h * 0.56, f"{len(scale.intervals)} NOTES",
                 size=title_bar_h * 0.24, fill=TEXT_MUTED,
                 weight="bold", anchor="end", family=FONT_CONDENSED)
        draw_formula_chips(dwg, scale.labels,
                           right_x + right_w * 0.975,
                           py + title_bar_h * 0.50,
                           max_width=right_w * 0.24,
                           radius=title_bar_h * 0.17,
                           gap=title_bar_h * 0.06,
                           align="right")

        inner_x = right_x + right_w * 0.020
        inner_w = right_w * 0.960
        label_h = scale_panel_h * 0.14
        board_y = py + title_bar_h + label_h
        board_h = scale_panel_h - title_bar_h - label_h - scale_panel_h * 0.060

        label_pad = 17
        grid_x = inner_x + label_pad
        grid_w = inner_w - label_pad
        fret_count = SCALE_SPAN.fret_end - SCALE_SPAN.fret_start + 1
        fret_cell = grid_w / fret_count
        label_y = py + title_bar_h + label_h * 0.68
        for position in SCALE_POSITIONS:
            position_x = grid_x + (position.fret_start - SCALE_SPAN.fret_start) * fret_cell
            add_line(dwg, position_x, board_y - label_h * 0.28,
                     position_x, board_y + board_h,
                     stroke=GRID_DIM, stroke_width=0.9, opacity=0.85)
            add_text(dwg, position_x + fret_cell * 0.06, label_y,
                     f"Position {position.position_number} ({position.shape})",
                     size=label_h * 0.43, fill=TEXT_MUTED,
                     weight="bold", anchor="start", family=FONT_CONDENSED)
        notes = chord_notes_for_window(SCALE_SPAN, scale)
        draw_fretboard(dwg, inner_x, board_y, inner_w, board_h,
                       SCALE_SPAN, notes,
                       show_orientation_labels=True, compact=True)

    # ------------------------------ Bottom legend ----------------------------
    legend_y = height - legend_h - margin * 0.45
    legend_x = margin
    legend_w = width - 2 * margin
    draw_panel_border(dwg, legend_x, legend_y, legend_w, legend_h, radius=10)

    add_text(dwg, legend_x + legend_w * 0.018,
             legend_y + legend_h * 0.47, "NOTE COLOR LEGEND",
             size=legend_h * 0.19, weight="bold", family=FONT_CONDENSED)
    add_text(dwg, legend_x + legend_w * 0.018,
             legend_y + legend_h * 0.72,
             "Movable interval patterns; C is used only for placement.",
             size=legend_h * 0.105, fill=TEXT_MUTED,
             family=FONT_CONDENSED)

    legend_items = (
        ("R", "Root / 1"), ("2", "Major 2nd"), ("b3", "Minor 3rd"),
        ("3", "Major 3rd"), ("4", "Perfect 4th"),
        ("b5", "Diminished 5th"), ("5", "Perfect 5th"),
        ("b6", "Minor 6th"), ("6", "Major 6th"),
        ("b7", "Minor 7th"), ("7", "Major 7th"),
        ("bb7", "Diminished 7th"),
    )
    start_x = legend_x + legend_w * 0.245
    available = legend_w * 0.735
    item_w = available / len(legend_items)
    for i, (label, desc) in enumerate(legend_items):
        ix = start_x + i * item_w
        cy = legend_y + legend_h * 0.38
        radius = legend_h * 0.13
        draw_note_chip(dwg, ix + radius, cy, label, radius)
        add_text(dwg, ix + radius, legend_y + legend_h * 0.76,
                 desc, size=legend_h * 0.095, fill=TEXT_MUTED,
                 weight="bold", anchor="middle", family=FONT_CONDENSED)

    dwg.save(pretty=True)


def render_outputs(width: int, height: int, out_dir: Path,
                   stem: str, make_preview: bool = True) -> Tuple[Path, Path, Path | None]:
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_path = out_dir / f"{stem}.svg"
    png_path = out_dir / f"{stem}_{width}x{height}.png"
    preview_path = out_dir / f"{stem}_1920x1080.png" if make_preview else None

    create_svg(width, height, svg_path)
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path),
                     output_width=width, output_height=height)
    if make_preview and preview_path is not None:
        cairosvg.svg2png(url=str(svg_path), write_to=str(preview_path),
                         output_width=1920, output_height=1080)
    return svg_path, png_path, preview_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=3840,
                        help="Output width; default 3840")
    parser.add_argument("--height", type=int, default=2160,
                        help="Output height; default 2160")
    parser.add_argument("--out-dir", type=Path, default=Path("."),
                        help="Output directory")
    parser.add_argument("--stem", default="guitar_theory_cheatsheet",
                        help="Base filename")
    parser.add_argument("--no-preview", action="store_true",
                        help="Do not create a 1920x1080 preview")
    args = parser.parse_args()

    svg_path, png_path, preview_path = render_outputs(
        args.width, args.height, args.out_dir, args.stem,
        make_preview=not args.no_preview,
    )
    print(f"SVG: {svg_path}")
    print(f"PNG: {png_path}")
    if preview_path is not None:
        print(f"Preview: {preview_path}")


if __name__ == "__main__":
    main()
