"""
CPU Scheduling Algorithms
===================================
Simulates 6 CPU scheduling algorithms with animated Gantt chart and process table.

Layout:
  Top-left   : Settings panel  (algorithm, quantum, priority direction, process inputs)
  Top-right  : Process table   (animated rows showing WT, TAT, remaining burst)
  Bottom     : Gantt chart     (wide horizontal timeline)

Algorithms implemented:
  1. FCFS               – First-Come, First-Served (non-preemptive)
  2. SJF                – Shortest Job First (non-preemptive)
  3. SRTF               – Shortest Remaining Time First (preemptive)
  4. Round Robin        – Time-quantum based (preemptive)
  5. Priority NP        – Priority Scheduling, Non-Preemptive (lower value = higher priority)
  6. Priority P         – Priority Scheduling, Preemptive
  7. Priority + RR      – Priority with Round Robin

Author note:
  Priority convention: lower numeric value = higher priority (can be toggled in UI).
"""

import pygame
import sys
import math
import copy
from dataclasses import dataclass
from typing import List, Optional, Tuple

# ─── Tunable constant ─────────────────────────────────────────────────────────
# Set animation speed here: 1 = slow, 2 = normal, 3 = fast
ANIMATION_SPEED = 2   # <-- change this value to adjust animation speed

# ─── Window / FPS ─────────────────────────────────────────────────────────────
W, H = 1400, 820
FPS  = 60

# ─── Color palette ────────────────────────────────────────────────────────────
WHITE            = (255, 255, 255)
OFF_WHITE        = (248, 249, 250)
LIGHT_GRAY       = (230, 234, 238)
MID_GRAY         = (180, 186, 195)
DARK_GRAY        = (100, 108, 120)
CHARCOAL         = (40,  44,  52)
BLACK            = (15,  17,  21)
ACCENT           = (67,  120, 220)
ACCENT_DARK      = (40,  80,  180)
GREEN_DONE       = (52,  168, 83)
GREEN_LIGHT      = (220, 245, 225)
GRAY_FUTURE_TEXT = (170, 175, 185)
ARROW_COL        = (220, 60,  60)

# Per-process colors (cycled when > 8 processes)
PROCESS_COLORS = [
    (67,  120, 220),   # blue
    (236, 100,  75),   # coral
    (52,  168,  83),   # green
    (251, 166,   0),   # amber
    (157,  85, 201),   # purple
    (0,   172, 193),   # teal
    (244,  81,  30),   # deep orange
    (30,  136, 229),   # light blue
]

# Algorithm metadata
ALGO_NAMES = [
    "FCFS",
    "SJF (Non-Preemptive)",
    "SRTF (Preemptive)",
    "Round Robin",
    "Priority (Non-Preemptive)",
    "Priority (Preemptive)",
    "Priority + Round Robin",
]
ALGO_HAS_PRIORITY  = {0: False, 1: False, 2: False, 3: False, 4: True, 5: True, 6: True}
ALGO_HAS_QUANTUM   = {0: False, 1: False, 2: False, 3: True,  4: False, 5: False, 6: True}
ALGO_IS_PREEMPTIVE = {0: False, 1: False, 2: True,  3: True,  4: False, 5: True,  6: True}


# ─── Data structures ──────────────────────────────────────────────────────────

@dataclass
class Process:
    """Holds all scheduling-relevant data for one process."""
    pid:       int
    arrival:   int
    burst:     int
    priority:  int  = 0
    color:     Tuple = (67, 120, 220)
    # Computed fields (set during simulation)
    start_time:  int = -1
    finish_time: int = -1
    remaining:   int = 0
    waiting:     int = 0
    turnaround:  int = 0
    done:        bool = False

    def __post_init__(self):
        self.remaining = self.burst


@dataclass
class GanttBlock:
    """One colored segment in the Gantt chart."""
    pid:   int
    start: int
    end:   int
    color: Tuple


# ─── Scheduling algorithms ────────────────────────────────────────────────────

def run_fcfs(procs: List[Process]):
    """
    First-Come, First-Served (non-preemptive).
    Processes run in arrival order; ties broken by PID.
    """
    procs = sorted(procs, key=lambda p: (p.arrival, p.pid))
    t, blocks = 0, []
    for p in procs:
        if t < p.arrival:
            t = p.arrival
        p.start_time = t
        blocks.append(GanttBlock(p.pid, t, t + p.burst, p.color))
        t += p.burst
        p.finish_time = t
        p.turnaround  = p.finish_time - p.arrival
        p.waiting     = p.turnaround  - p.burst
        p.done        = True
    return blocks, procs


def run_sjf(procs: List[Process]):
    """
    Shortest Job First – Non-Preemptive.
    Among all arrived processes, pick the one with the smallest burst time.
    """
    t, done, blocks, remaining = 0, [], [], list(
        sorted(procs, key=lambda p: (p.arrival, p.pid))
    )
    while remaining:
        available = [p for p in remaining if p.arrival <= t]
        if not available:
            t = min(p.arrival for p in remaining)
            available = [p for p in remaining if p.arrival <= t]
        p = min(available, key=lambda x: (x.burst, x.pid))
        p.start_time = t
        blocks.append(GanttBlock(p.pid, t, t + p.burst, p.color))
        t += p.burst
        p.finish_time = t
        p.turnaround  = p.finish_time - p.arrival
        p.waiting     = p.turnaround  - p.burst
        p.done        = True
        remaining.remove(p)
        done.append(p)
    return blocks, done


def run_srtf(procs: List[Process]):
    """
    Shortest Remaining Time First – Preemptive.
    Each tick, the process with the least remaining burst runs.
    Consecutive same-PID blocks are merged afterward.
    """
    procs_work = [copy.deepcopy(p) for p in
                  sorted(procs, key=lambda p: (p.arrival, p.pid))]
    t, blocks, done = 0, [], []
    end_t = sum(p.burst for p in procs_work) + max(p.arrival for p in procs_work) + 10

    for _ in range(end_t * 3):
        available = [p for p in procs_work if p.arrival <= t and not p.done]
        if not available:
            if all(p.done for p in procs_work):
                break
            t += 1
            continue
        p = min(available, key=lambda x: (x.remaining, x.pid))
        if p.start_time == -1:
            p.start_time = t
        if blocks and blocks[-1].pid == p.pid:
            blocks[-1].end = t + 1
        else:
            blocks.append(GanttBlock(p.pid, t, t + 1, p.color))
        p.remaining -= 1
        t += 1
        if p.remaining == 0:
            p.finish_time = t
            p.turnaround  = t - p.arrival
            p.waiting     = p.turnaround - p.burst
            p.done        = True
            done.append(p)
        if all(p.done for p in procs_work):
            break

    # Merge adjacent same-PID blocks (reduces Gantt noise)
    merged = []
    for b in blocks:
        if merged and merged[-1].pid == b.pid:
            merged[-1].end = b.end
        else:
            merged.append(b)
    return merged, done


def run_rr(procs: List[Process], quantum: int):
    """
    Round Robin – Preemptive.
    Each process runs for at most `quantum` time units, then yields.
    Newly arrived processes are enqueued before the preempted one re-queues.
    """
    procs_work = sorted([copy.deepcopy(p) for p in procs], key=lambda p: (p.arrival, p.pid))
    t, queue, blocks, done, arrived = 0, [], [], [], set()

    def enqueue_new(time):
        for p in procs_work:
            if p.pid not in arrived and p.arrival <= time and not p.done:
                queue.append(p)
                arrived.add(p.pid)

    enqueue_new(0)
    safety = 0
    while (queue or any(not p.done for p in procs_work)) and safety < 100_000:
        safety += 1
        if not queue:
            t = min(p.arrival for p in procs_work if not p.done)
            enqueue_new(t)
        p = queue.pop(0)
        if p.start_time == -1:
            p.start_time = t
        run = min(quantum, p.remaining)
        blocks.append(GanttBlock(p.pid, t, t + run, p.color))
        t += run
        p.remaining -= run
        enqueue_new(t)
        if p.remaining == 0:
            p.finish_time = t
            p.turnaround  = t - p.arrival
            p.waiting     = p.turnaround - p.burst
            p.done        = True
            done.append(p)
        else:
            queue.append(p)
    return blocks, done


def run_priority_np(procs: List[Process], lower_is_higher: bool):
    """
    Priority Scheduling – Non-Preemptive.
    Among arrived processes, pick highest-priority one and run to completion.
    `lower_is_higher=True` means smaller value = higher priority.
    """
    procs_work = sorted([copy.deepcopy(p) for p in procs], key=lambda p: (p.arrival, p.pid))
    t, remaining, blocks, done = 0, list(procs_work), [], []
    while remaining:
        available = [p for p in remaining if p.arrival <= t]
        if not available:
            t = min(p.arrival for p in remaining)
            available = [p for p in remaining if p.arrival <= t]
        key = (lambda x: (x.priority, x.pid)) if lower_is_higher else (lambda x: (-x.priority, x.pid))
        p = min(available, key=key)
        p.start_time = t
        blocks.append(GanttBlock(p.pid, t, t + p.burst, p.color))
        t += p.burst
        p.finish_time = t
        p.turnaround  = t - p.arrival
        p.waiting     = p.turnaround - p.burst
        p.done        = True
        remaining.remove(p)
        done.append(p)
    return blocks, done


def run_priority_p(procs: List[Process], lower_is_higher: bool):
    """
    Priority Scheduling – Preemptive.
    Each tick, the highest-priority arrived process runs.
    Consecutive same-PID blocks are merged.
    """
    procs_work = sorted([copy.deepcopy(p) for p in procs], key=lambda p: (p.arrival, p.pid))
    t, blocks, done = 0, [], []
    end_t = max(p.arrival for p in procs_work) + sum(p.burst for p in procs_work) + 1
    key_fn = (lambda x: (x.priority, x.pid)) if lower_is_higher else (lambda x: (-x.priority, x.pid))

    for _ in range(end_t * 2):
        available = [p for p in procs_work if p.arrival <= t and not p.done]
        if not available:
            if all(p.done for p in procs_work):
                break
            t += 1
            continue
        p = min(available, key=key_fn)
        if p.start_time == -1:
            p.start_time = t
        if blocks and blocks[-1].pid == p.pid:
            blocks[-1].end = t + 1
        else:
            blocks.append(GanttBlock(p.pid, t, t + 1, p.color))
        p.remaining -= 1
        t += 1
        if p.remaining == 0:
            p.finish_time = t
            p.turnaround  = t - p.arrival
            p.waiting     = p.turnaround - p.burst
            p.done        = True
            done.append(p)
        if all(p.done for p in procs_work):
            break

    merged = []
    for b in blocks:
        if merged and merged[-1].pid == b.pid:
            merged[-1].end = b.end
        else:
            merged.append(b)
    return merged, done


def run_priority_rr(procs: List[Process], quantum: int, lower_is_higher: bool):
    """
    Priority + Round Robin.
    Queue is ordered by priority; each quantum slice uses RR within same-priority group.
    """
    procs_work = sorted([copy.deepcopy(p) for p in procs], key=lambda p: (p.arrival, p.pid))
    t, blocks, done, arrived, queue = 0, [], [], set(), []
    key_fn = (lambda x: (x.priority, x.pid)) if lower_is_higher else (lambda x: (-x.priority, x.pid))

    def enqueue_new(time):
        newly = [p for p in procs_work if p.pid not in arrived and p.arrival <= time and not p.done]
        newly.sort(key=key_fn)
        for p in newly:
            queue.append(p)
            arrived.add(p.pid)

    enqueue_new(0)
    safety = 0
    while (queue or any(not p.done for p in procs_work)) and safety < 100_000:
        safety += 1
        if not queue:
            t = min(p.arrival for p in procs_work if not p.done)
            enqueue_new(t)
        p = queue.pop(0)
        if p.start_time == -1:
            p.start_time = t
        run = min(quantum, p.remaining)
        blocks.append(GanttBlock(p.pid, t, t + run, p.color))
        t += run
        p.remaining -= run
        enqueue_new(t)
        if p.remaining == 0:
            p.finish_time = t
            p.turnaround  = t - p.arrival
            p.waiting     = p.turnaround - p.burst
            p.done        = True
            done.append(p)
        else:
            # Re-insert by priority order
            insert_idx = len(queue)
            for i, q in enumerate(queue):
                if key_fn(p) < key_fn(q):
                    insert_idx = i
                    break
            queue.insert(insert_idx, p)
    return blocks, done


# ─── Animation helpers ────────────────────────────────────────────────────────

class Shake:
    """Horizontal shake animation for a UI element (used on preemption)."""
    def __init__(self, dur=18, amp=5):
        self.t, self.dur, self.amp = 0, dur, amp

    def update(self):
        self.t += 1

    def offset(self):
        if self.t >= self.dur:
            return 0
        return int(self.amp * math.sin(self.t * math.pi * 3 / self.dur) * (1 - self.t / self.dur))

    @property
    def done(self):
        return self.t >= self.dur


class NumberRoll:
    """Animates a number changing (slides in from above)."""
    def __init__(self, old, new, dur=25):
        self.old, self.new, self.t, self.dur = old, new, 0, dur

    def update(self):
        self.t = min(self.t + 1, self.dur)

    @property
    def done(self):
        return self.t >= self.dur

    def alpha(self):
        return min(1.0, self.t / self.dur)

    def offset(self):
        ease = 1 - (1 - self.t / self.dur) ** 3
        return int((1 - ease) * 18)


class SlideIn:
    """Eased slide-in animation from a given direction."""
    def __init__(self, dur=20, direction='right'):
        self.t, self.dur, self.direction = 0, dur, direction

    def update(self):
        self.t = min(self.t + 1, self.dur)

    @property
    def done(self):
        return self.t >= self.dur

    def progress(self):
        raw = self.t / self.dur
        return 1 - (1 - raw) ** 3

    def offset(self):
        d = {'right': (1, 0), 'left': (-1, 0), 'up': (0, -1), 'down': (0, 1)}[self.direction]
        p = 1 - self.progress()
        return (int(d[0] * 40 * p), int(d[1] * 30 * p))


class GanttBlockAnim:
    """A Gantt bar that grows from left to right over `dur` frames."""
    def __init__(self, block: GanttBlock, max_w: int, dur: int):
        self.block = block
        self.max_w = max_w
        self.dur   = max(1, dur)
        self.t     = 0
        self.slide = SlideIn(12, 'right')

    def update(self):
        self.slide.update()
        self.t = min(self.t + 1, self.dur)

    @property
    def done(self):
        return self.t >= self.dur

    def current_w(self):
        raw = self.t / self.dur
        ease = 1 - (1 - raw) ** 2
        return max(2, int(self.max_w * ease))


class FadeIn:
    def __init__(self, dur=20):
        self.t, self.dur = 0, dur

    def update(self):
        self.t = min(self.t + 1, self.dur)

    @property
    def done(self):
        return self.t >= self.dur

    def alpha(self):
        return self.t / self.dur


# ─── Font & drawing helpers ───────────────────────────────────────────────────

def load_fonts():
    """Load system fonts with fallback chain."""
    pygame.font.init()
    for name in ['DejaVuSans', 'FreeSans', 'LiberationSans', 'Verdana', 'Arial', '']:
        try:
            return {
                'small':  pygame.font.SysFont(name, 11),
                'body':   pygame.font.SysFont(name, 13),
                'body_b': pygame.font.SysFont(name, 13, bold=True),
                'medium': pygame.font.SysFont(name, 15, bold=True),
                'large':  pygame.font.SysFont(name, 20, bold=True),
            }
        except Exception:
            continue
    raise RuntimeError("No suitable font found")


def draw_text(surf, text, font, color, x, y, alpha=255, cx=False, cy=False):
    """Render text at (x,y); cx/cy center horizontally/vertically."""
    rendered = font.render(str(text), True, color)
    if alpha < 255:
        rendered.set_alpha(alpha)
    rx = x - (rendered.get_width()  // 2 if cx else 0)
    ry = y - (rendered.get_height() // 2 if cy else 0)
    surf.blit(rendered, (rx, ry))
    return rendered.get_width(), rendered.get_height()


def draw_rounded_rect(surf, color, rect, r=8, border=0, border_color=None):
    pygame.draw.rect(surf, color, rect, border_radius=r)
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=r)


# ─── UI Widgets ───────────────────────────────────────────────────────────────

class Button:
    def __init__(self, x, y, w, h, text, color=ACCENT, text_color=WHITE, radius=6):
        self.rect       = pygame.Rect(x, y, w, h)
        self.text       = text
        self.color      = color
        self.text_color = text_color
        self.radius     = radius
        self.hovered    = False
        self.pressed    = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.pressed = True
            return True
        if event.type == pygame.MOUSEBUTTONUP:
            self.pressed = False
        return False

    def draw(self, surf, fonts):
        col = tuple(min(255, c + 20) for c in self.color) if self.hovered else self.color
        if self.pressed:
            col = tuple(max(0, c - 20) for c in self.color)
        draw_rounded_rect(surf, col, self.rect, self.radius)
        draw_text(surf, self.text, fonts['body_b'], self.text_color,
                  self.rect.centerx, self.rect.centery, cx=True, cy=True)


class TextInput:
    """Single-line numeric (or text) input field with cursor."""
    def __init__(self, x, y, w, h, value="", numeric=True, min_val=1, max_val=99, placeholder=""):
        self.rect        = pygame.Rect(x, y, w, h)
        self.value       = str(value)
        self.numeric     = numeric
        self.min_val     = min_val
        self.max_val     = max_val
        self.placeholder = placeholder
        self.active      = False
        self.cursor_vis  = True
        self.cursor_t    = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_TAB):
                self.active = False
                self._clamp()
            else:
                ch = event.unicode
                if self.numeric:
                    if ch.isdigit() and len(self.value) < 3:
                        self.value += ch
                else:
                    self.value += ch
            return True
        return False

    def _clamp(self):
        if self.numeric and self.value:
            v = max(self.min_val, min(self.max_val, int(self.value)))
            self.value = str(v)

    def int_val(self):
        try:
            return max(self.min_val, min(self.max_val, int(self.value)))
        except ValueError:
            return self.min_val

    def draw(self, surf, fonts):
        self.cursor_t += 1
        if self.cursor_t > 30:
            self.cursor_vis = not self.cursor_vis
            self.cursor_t   = 0
        bg = WHITE if self.active else OFF_WHITE
        bc = ACCENT if self.active else LIGHT_GRAY
        draw_rounded_rect(surf, bg, self.rect, 4, 1, bc)
        disp = self.value if self.value else self.placeholder
        col  = CHARCOAL if self.value else MID_GRAY
        cx, cy = self.rect.x + 6, self.rect.centery
        draw_text(surf, disp, fonts['body'], col, cx, cy, cy=True)
        if self.active and self.cursor_vis:
            tw = fonts['body'].size(self.value)[0]
            pygame.draw.line(surf, CHARCOAL, (cx + tw, cy - 6), (cx + tw, cy + 6), 1)


class Dropdown:
    """Single-select dropdown menu."""
    def __init__(self, x, y, w, options, selected=0):
        self.rect         = pygame.Rect(x, y, w, 28)
        self.options      = options
        self.selected     = selected
        self.open         = False
        self.hovered_item = -1

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.open = not self.open
                return True
            if self.open:
                for i in range(len(self.options)):
                    r = pygame.Rect(self.rect.x, self.rect.y + 28 + i * 26, self.rect.w, 26)
                    if r.collidepoint(event.pos):
                        self.selected = i
                        self.open     = False
                        return True
                self.open = False
        if event.type == pygame.MOUSEMOTION and self.open:
            self.hovered_item = -1
            for i in range(len(self.options)):
                r = pygame.Rect(self.rect.x, self.rect.y + 28 + i * 26, self.rect.w, 26)
                if r.collidepoint(event.pos):
                    self.hovered_item = i
        return False

    def draw(self, surf, fonts):
        """Full draw (bar + list). Use draw_closed + draw_open_list separately for z-order control."""
        self.draw_closed(surf, fonts)
        self.draw_open_list(surf, fonts)

    def draw_closed(self, surf, fonts):
        """Draw only the dropdown bar (selected item + arrow). Does not draw the open list."""
        draw_rounded_rect(surf, WHITE, self.rect, 5, 1, LIGHT_GRAY)
        draw_text(surf, self.options[self.selected], fonts['body'], CHARCOAL,
                  self.rect.x + 8, self.rect.centery, cy=True)
        ax, ay = self.rect.right - 14, self.rect.centery
        if self.open:
            pygame.draw.polygon(surf, DARK_GRAY, [(ax, ay + 3), (ax + 8, ay + 3), (ax + 4, ay - 3)])
        else:
            pygame.draw.polygon(surf, DARK_GRAY, [(ax, ay - 3), (ax + 8, ay - 3), (ax + 4, ay + 3)])

    def draw_open_list(self, surf, fonts):
        """Draw the expanded option list. Call this last so it renders above all panels."""
        if not self.open:
            return
        for i, opt in enumerate(self.options):
            r  = pygame.Rect(self.rect.x, self.rect.y + 28 + i * 26, self.rect.w, 26)
            bg = LIGHT_GRAY if i == self.hovered_item else WHITE
            if i == self.selected:
                bg = (230, 238, 255)
            draw_rounded_rect(surf, bg, r, 3)
            pygame.draw.rect(surf, LIGHT_GRAY, r, 1, border_radius=3)
            draw_text(surf, opt, fonts['body'], CHARCOAL, r.x + 8, r.centery, cy=True)


class Toggle:
    """Two-state toggle switch."""
    def __init__(self, x, y, label_on="Lower=Higher", label_off="Higher=Higher", state=True):
        self.x         = x
        self.y         = y
        self.state     = state
        self.label_on  = label_on
        self.label_off = label_off
        self.rect      = pygame.Rect(x, y, 40, 20)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.state = not self.state
            return True
        return False

    def draw(self, surf, fonts):
        bg = ACCENT if self.state else MID_GRAY
        draw_rounded_rect(surf, bg, self.rect, 10)
        cx = self.rect.x + (24 if self.state else 6)
        pygame.draw.circle(surf, WHITE, (cx, self.rect.centery), 8)
        label = self.label_on if self.state else self.label_off
        draw_text(surf, label, fonts['small'], DARK_GRAY,
                  self.rect.right + 6, self.rect.centery, cy=True)


# ─── Process Table Row ────────────────────────────────────────────────────────

class ProcessRow:
    """
    One row in the results table for a process.
    Animates: slide-in, shake on preemption, rolling numbers for WT/TAT/remaining.
    """
    def __init__(self, proc: Process, y: int, has_priority: bool, columns: list):
        self.proc            = proc
        self.base_y          = y
        self.y               = y
        self.has_priority    = has_priority
        self.columns         = columns
        self.shake           = None
        self.slide_in        = SlideIn(20, 'right')
        self.state           = 'future'    # future | active | done
        self.remaining_anim  = None        # NumberRoll for remaining burst countdown
        self.wt_anim         = None        # NumberRoll for waiting time reveal
        self.tat_anim        = None        # NumberRoll for turnaround time reveal
        self.arrow_visible   = False
        self.done_fade       = FadeIn(30)
        self.done_triggered  = False
        self.remaining_display = proc.burst

    def trigger_shake(self, amp=5):
        self.shake = Shake(20, amp)

    def set_remaining(self, new_val):
        if new_val != self.remaining_display:
            self.remaining_anim    = NumberRoll(self.remaining_display, new_val, 15)
            self.remaining_display = new_val

    def mark_done(self):
        if not self.done_triggered:
            self.done_triggered = True
            self.done_fade      = FadeIn(40)
            self.state          = 'done'
            self.wt_anim        = NumberRoll(0, self.proc.waiting,     30)
            self.tat_anim       = NumberRoll(0, self.proc.turnaround,  30)

    def update(self):
        self.slide_in.update()
        if self.shake:
            self.shake.update()
            if self.shake.done:
                self.shake = None
        if self.remaining_anim:
            self.remaining_anim.update()
            if self.remaining_anim.done:
                self.remaining_anim = None
        if self.wt_anim:
            self.wt_anim.update()
        if self.tat_anim:
            self.tat_anim.update()
        if self.done_triggered:
            self.done_fade.update()

    def draw(self, surf, fonts, clip_rect: pygame.Rect, row_h=34):
        """Draw this row, clipped to `clip_rect` so it never overflows its panel."""
        ox      = self.slide_in.offset()[0]
        shake_x = self.shake.offset() if self.shake else 0
        x_off   = ox + shake_x
        y       = self.y

        # Skip rows that are completely outside the clip area
        if y + row_h < clip_rect.top or y > clip_rect.bottom:
            return

        # Row background
        if self.state == 'done':
            alpha = self.done_fade.alpha()
            bg    = tuple(int(a + (b - a) * alpha) for a, b in zip(WHITE, GREEN_LIGHT))
        elif self.state == 'active':
            bg = (240, 245, 255)
        else:
            bg = OFF_WHITE

        row_rect = pygame.Rect(clip_rect.x + 4 + x_off, y, clip_rect.w - 8, row_h)

        # Clip drawing to the panel
        old_clip = surf.get_clip()
        surf.set_clip(clip_rect)

        draw_rounded_rect(surf, bg, row_rect, 5)
        border_col = GREEN_DONE if self.state == 'done' else (ACCENT if self.state == 'active' else LIGHT_GRAY)
        pygame.draw.rect(surf, border_col, row_rect, 1, border_radius=5)

        # Color pill
        c = self.proc.color if self.state != 'future' else MID_GRAY
        pygame.draw.rect(surf, c, pygame.Rect(row_rect.x + 4, y + row_h // 2 - 8, 4, 16), border_radius=2)

        text_col = GRAY_FUTURE_TEXT if self.state == 'future' else CHARCOAL

        for col_label, col_x, col_w in self.columns:
            cx = col_x + x_off + col_w // 2
            cy = y + row_h // 2

            if col_label == 'PID':
                draw_text(surf, f'P{self.proc.pid}', fonts['body_b'], text_col, cx, cy, cx=True, cy=True)
            elif col_label == 'Arrival':
                draw_text(surf, str(self.proc.arrival), fonts['body'], text_col, cx, cy, cx=True, cy=True)
            elif col_label == 'Burst':
                draw_text(surf, str(self.proc.burst), fonts['body'], text_col, cx - 10, cy, cx=True, cy=True)
                if self.state != 'future' and self.remaining_display < self.proc.burst:
                    rem_col = ACCENT if self.state == 'active' else DARK_GRAY
                    if self.remaining_anim and not self.remaining_anim.done:
                        yoff = self.remaining_anim.offset()
                        al   = int(self.remaining_anim.alpha() * 255)
                        draw_text(surf, f'({self.remaining_anim.new})', fonts['small'],
                                  rem_col, cx + 10, cy - yoff, al, cx=True, cy=True)
                    else:
                        draw_text(surf, f'({self.remaining_display})', fonts['small'],
                                  rem_col, cx + 10, cy, cx=True, cy=True)
            elif col_label == 'Priority' and self.has_priority:
                draw_text(surf, str(self.proc.priority), fonts['body'], text_col, cx, cy, cx=True, cy=True)
            elif col_label == 'WT' and self.state == 'done' and self.wt_anim:
                if not self.wt_anim.done:
                    yoff = self.wt_anim.offset()
                    al   = int(self.wt_anim.alpha() * 255)
                    draw_text(surf, str(self.wt_anim.new), fonts['body'], GREEN_DONE,
                              cx, cy - yoff, al, cx=True, cy=True)
                else:
                    draw_text(surf, str(self.proc.waiting), fonts['body'], GREEN_DONE, cx, cy, cx=True, cy=True)
            elif col_label == 'TAT' and self.state == 'done' and self.tat_anim:
                if not self.tat_anim.done:
                    yoff = self.tat_anim.offset()
                    al   = int(self.tat_anim.alpha() * 255)
                    draw_text(surf, str(self.tat_anim.new), fonts['body'], GREEN_DONE,
                              cx, cy - yoff, al, cx=True, cy=True)
                else:
                    draw_text(surf, str(self.proc.turnaround), fonts['body'], GREEN_DONE, cx, cy, cx=True, cy=True)

        # Execution arrow
        if self.arrow_visible:
            ax    = row_rect.x + 2 + x_off
            ay    = y + row_h // 2
            pulse = int(3 * math.sin(pygame.time.get_ticks() * 0.008))
            pygame.draw.polygon(surf, ARROW_COL,
                [(ax + pulse, ay), (ax + pulse - 8, ay - 5), (ax + pulse - 8, ay + 5)])

        surf.set_clip(old_clip)


# ─── Average Metrics Animation ────────────────────────────────────────────────

class AverageAnim:
    """
    Animated display of average WT and TAT.
    Phases: slide-in → reveal per-process values → show avg computation → done.
    """
    def __init__(self, procs: List[Process]):
        self.procs        = procs
        self.t            = 0
        self.phase        = 0   # 0=waiting, 1=summing, 2=averaging, 3=done
        self.sum_wt       = 0
        self.sum_tat      = 0
        self.wt_rolls     = []
        self.tat_rolls    = []
        self.avg_wt_roll  = None
        self.avg_tat_roll = None
        self.slide        = SlideIn(20, 'up')
        self._started     = False

    def start(self):
        self._started = True
        for p in self.procs:
            self.wt_rolls.append(NumberRoll(0, p.waiting, 20))
            self.tat_rolls.append(NumberRoll(0, p.turnaround, 20))

    def update(self):
        if not self._started:
            return
        self.t += 1
        self.slide.update()
        if self.phase == 0 and self.t > 20:
            self.phase = 1
        if self.phase == 1:
            for r in self.wt_rolls + self.tat_rolls:
                r.update()
            if all(r.done for r in self.wt_rolls + self.tat_rolls):
                self.sum_wt  = sum(p.waiting     for p in self.procs)
                self.sum_tat = sum(p.turnaround  for p in self.procs)
                self.phase   = 2
        if self.phase == 2 and not self.avg_wt_roll:
            n = len(self.procs)
            self.avg_wt_roll  = NumberRoll(0, round(self.sum_wt  / n, 2), 35)
            self.avg_tat_roll = NumberRoll(0, round(self.sum_tat / n, 2), 35)
        if self.phase == 2 and self.avg_wt_roll:
            self.avg_wt_roll.update()
            self.avg_tat_roll.update()
            if self.avg_wt_roll.done:
                self.phase = 3

    @property
    def done(self):
        return self.phase == 3

    def draw(self, surf, fonts, x, y, w):
        if not self._started:
            return
        oy = self.slide.offset()[1]
        ry = y + oy
        draw_rounded_rect(surf, (245, 248, 255), pygame.Rect(x, ry, w, 110), 8, 1, LIGHT_GRAY)
        draw_text(surf, "Average Metrics", fonts['medium'], CHARCOAL, x + 12, ry + 10)
        n = len(self.procs)

        # Per-process values
        parts_wt  = [f"P{p.pid}({(r.new if r.done else r.old)})" for p, r in zip(self.procs, self.wt_rolls)]
        parts_tat = [f"P{p.pid}({(r.new if r.done else r.old)})" for p, r in zip(self.procs, self.tat_rolls)]
        draw_text(surf, f"WT: {' + '.join(parts_wt)}"  if self.phase >= 1 else "WT:", fonts['small'], DARK_GRAY, x + 12, ry + 32)
        draw_text(surf, f"TAT: {' + '.join(parts_tat)}" if self.phase >= 1 else "TAT:", fonts['small'], DARK_GRAY, x + 12, ry + 48)

        if self.phase >= 2 and self.avg_wt_roll and self.avg_tat_roll:
            yoff_wt  = self.avg_wt_roll.offset()  if not self.avg_wt_roll.done  else 0
            yoff_tat = self.avg_tat_roll.offset()  if not self.avg_tat_roll.done else 0
            draw_text(surf, f"Avg WT  = {self.sum_wt}/{n} =", fonts['body'], CHARCOAL, x + 12, ry + 68)
            draw_text(surf, str(round(self.sum_wt / n, 2)),   fonts['body_b'], ACCENT, x + 170, ry + 68 - yoff_wt)
            draw_text(surf, f"Avg TAT = {self.sum_tat}/{n} =", fonts['body'], CHARCOAL, x + 12, ry + 86)
            draw_text(surf, str(round(self.sum_tat / n, 2)),   fonts['body_b'], ACCENT, x + 170, ry + 86 - yoff_tat)


# ─── Main Simulator ───────────────────────────────────────────────────────────

class CPUSchedulerSim:
    """
    Main application class.
    Manages layout, UI state, simulation dispatch, and the render loop.

    Layout (portrait split):
      ┌──────────────────┬──────────────────────────────┐
      │  Settings panel  │      Process table panel      │  ← top half
      └──────────────────┴──────────────────────────────┘
      │              Gantt chart (full width)             │  ← bottom
      └───────────────────────────────────────────────────┘
    """

    # Heights for top / bottom split
    TOP_H    = 480
    GANTT_H  = H - TOP_H - 30   # remaining space for Gantt

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("CPU Scheduling Algorithms")
        self.clock  = pygame.time.Clock()
        self.fonts  = load_fonts()

        # ── Panel geometry ───────────────────────────────────────────
        SETTINGS_W = 320
        self.panel_settings = pygame.Rect(10,  30, SETTINGS_W, self.TOP_H)
        self.panel_table    = pygame.Rect(SETTINGS_W + 20, 30,
                                          W - SETTINGS_W - 30, self.TOP_H)
        gantt_y = self.TOP_H + 40
        self.panel_gantt    = pygame.Rect(10, gantt_y,
                                          W - 20, self.GANTT_H)

        # ── App state ────────────────────────────────────────────────
        self.lower_is_higher = True   # priority convention
        self.quantum         = 2

        self._build_input_processes()
        self._build_settings_ui()

        # Simulation state
        self.sim_running         = False
        self.sim_done            = False
        self.process_rows: List[ProcessRow]  = []
        self.gantt_blocks: List[GanttBlock]  = []
        self.sim_procs:   List[Process]      = []
        self.gantt_anims: List[GanttBlockAnim] = []
        self.completed_gantt:  List[GanttBlockAnim] = []

        self.anim_step   = 0
        self.tick_acc    = 0
        self.tick_phase  = 0
        self.preempt_pause = 0
        self.current_block_anim: Optional[GanttBlockAnim] = None
        self.avg_anim:           Optional[AverageAnim]    = None

        # Animation speed from the module-level constant
        self._speed_tick = {1: 4, 2: 2, 3: 1}.get(ANIMATION_SPEED, 2)
        self.input_scroll   = 0   # vertical scroll index for the process input list
        self.results_scroll = 0   # vertical scroll index for the results table

    # ── Scroll helpers ───────────────────────────────────────────────
    def _input_visible_rows(self):
        """How many input rows fit in the settings panel between header and buttons."""
        p        = self.panel_settings
        # y_cur at start of rows depends on algo options; use a conservative estimate
        # Buttons take bottom 80px; header+cols take ~190px min; each row is 30px
        top_used = 190  # settings header + dropdown + processes label + col headers
        available = p.h - top_used - 80  # subtract button area
        return max(1, available // 30)

    def _results_visible_rows(self):
        """How many result rows fit in the table panel between header and avg section."""
        p         = self.panel_table
        rows_top  = p.y + 74
        rows_bottom = p.bottom - 124
        return max(1, (rows_bottom - rows_top) // (34 + 4))

    # ── Input process defaults ────────────────────────────────────────
    def _build_input_processes(self):
        defaults = [(1, 0, 8, 3), (2, 1, 4, 1), (3, 2, 9, 4), (4, 3, 5, 2), (5, 4, 2, 5)]
        self.input_procs = []
        for pid, arr, burst, pri in defaults:
            self.input_procs.append({
                'pid':      pid,
                'arrival':  TextInput(0, 0, 52, 24, arr,   True, 0, 99),
                'burst':    TextInput(0, 0, 52, 24, burst,  True, 1, 99),
                'priority': TextInput(0, 0, 52, 24, pri,   True, 1, 99),
            })

    # ── Settings UI construction ──────────────────────────────────────
    def _build_settings_ui(self):
        sx = self.panel_settings.x + 14
        self.algo_dropdown = Dropdown(sx, 60, self.panel_settings.w - 28, ALGO_NAMES, 0)
        self.quantum_input = TextInput(sx, 110, 75, 26, "2", True, 1, 20, "Quantum")
        self.lower_toggle  = Toggle(sx, 150, "Lower=Higher", "Higher=Higher", True)
        # Process table buttons sit at the bottom of settings panel
        bott = self.panel_settings.bottom
        self.add_row_btn = Button(sx,       bott - 70, 100, 26, "+ Add Row",  (80, 160, 80))
        self.del_row_btn = Button(sx + 110, bott - 70, 100, 26, "- Del Row",  (200, 80, 80))
        self.start_btn   = Button(sx,       bott - 36, 120, 30, "▶  Run",     ACCENT)
        self.reset_btn   = Button(sx + 130, bott - 36, 100, 30, "↺  Reset",   (80, 90, 110))

    # ── Algorithm helpers ─────────────────────────────────────────────
    def get_algo(self):
        return self.algo_dropdown.selected

    def has_priority(self):
        return ALGO_HAS_PRIORITY[self.get_algo()]

    def has_quantum(self):
        return ALGO_HAS_QUANTUM[self.get_algo()]

    def is_preemptive(self):
        return ALGO_IS_PREEMPTIVE[self.get_algo()]

    # ── Column layout for process table ──────────────────────────────
    def _get_columns(self, has_priority: bool):
        """
        Returns a list of (label, absolute_x, width) for each column.
        Columns fit within the table panel; widths are proportional.
        """
        tx   = self.panel_table.x + 28
        defs = [('PID', 45), ('Arrival', 58), ('Burst', 78)]
        if has_priority:
            defs.append(('Priority', 62))
        defs += [('WT', 62), ('TAT', 62)]
        cols, x = [], tx
        for lbl, w in defs:
            cols.append((lbl, x, w))
            x += w + 6
        return cols

    # ── Process building ──────────────────────────────────────────────
    def build_processes(self) -> List[Process]:
        return [
            Process(
                pid      = row['pid'],
                arrival  = row['arrival'].int_val(),
                burst    = row['burst'].int_val(),
                priority = row['priority'].int_val() if self.has_priority() else 0,
                color    = PROCESS_COLORS[i % len(PROCESS_COLORS)],
            )
            for i, row in enumerate(self.input_procs)
        ]

    # ── Simulation dispatch ───────────────────────────────────────────
    def run_simulation(self):
        """Select and run the correct scheduling algorithm."""
        procs   = self.build_processes()
        algo    = self.get_algo()
        quantum = self.quantum_input.int_val()
        low     = self.lower_toggle.state
        dispatch = {
            0: lambda: run_fcfs(procs),
            1: lambda: run_sjf(procs),
            2: lambda: run_srtf(procs),
            3: lambda: run_rr(procs, quantum),
            4: lambda: run_priority_np(procs, low),
            5: lambda: run_priority_p(procs, low),
            6: lambda: run_priority_rr(procs, quantum, low),
        }
        return dispatch.get(algo, lambda: run_fcfs(procs))()

    # ── Start/reset ───────────────────────────────────────────────────
    def start_simulation(self):
        self.sim_running = True
        self.sim_done    = False
        self.anim_step      = 0
        self.tick_phase     = 0
        self.tick_acc       = 0
        self.preempt_pause  = 0
        self.avg_anim       = None
        self.current_block_anim = None
        self.results_scroll = 0   # reset results scroll on each new run

        self.gantt_blocks, self.sim_procs = self.run_simulation()

        total_time = max((b.end for b in self.gantt_blocks), default=1)
        self.gantt_total_time   = total_time
        self.gantt_tpu          = (self.panel_gantt.w - 80) / max(1, total_time)
        self.gantt_anims        = []
        self.completed_gantt    = []

        # Build process rows
        has_p   = self.has_priority()
        columns = self._get_columns(has_p)
        row_h   = 34
        start_y = self.panel_table.y + 74   # matches rows_top = header_y(52) + 22
        self.process_rows = []
        for i, p in enumerate(self.sim_procs):
            pr         = ProcessRow(p, start_y + i * (row_h + 4), has_p, columns)
            pr.slide_in = SlideIn(20 + i * 5, 'right')
            pr.state    = 'future'
            self.process_rows.append(pr)

    # ── Simulation tick ───────────────────────────────────────────────
    def update_simulation(self):
        if not self.sim_running or self.sim_done:
            return

        if self.current_block_anim:
            self.current_block_anim.update()

        if self.preempt_pause > 0:
            self.preempt_pause -= 1
            return

        self.tick_acc += 1
        if self.tick_acc < self._speed_tick:
            return
        self.tick_acc = 0

        # All blocks animated — show averages
        if self.anim_step >= len(self.gantt_blocks):
            if self.avg_anim is None:
                self.avg_anim = AverageAnim(self.sim_procs)
                self.avg_anim.start()
            self.avg_anim.update()
            if self.avg_anim.done:
                self.sim_done = True
            return

        block = self.gantt_blocks[self.anim_step]
        pid   = block.pid
        proc  = next((p for p in self.sim_procs if p.pid == pid), None)
        if proc is None:
            self.anim_step += 1
            return
        row = next((r for r in self.process_rows if r.proc.pid == pid), None)

        if self.tick_phase == 0:
            # Mark processes that have arrived
            for r in self.process_rows:
                if r.proc.arrival <= block.start and r.state == 'future':
                    r.state = 'active'
            # Move execution arrow
            for r in self.process_rows:
                r.arrow_visible = False
            if row:
                row.arrow_visible = True
                row.state = 'active'

            # Preemption shake
            if self.anim_step > 0:
                prev = self.gantt_blocks[self.anim_step - 1]
                if prev.pid != pid and ALGO_IS_PREEMPTIVE[self.get_algo()]:
                    if row:
                        row.trigger_shake(7)
                    self.preempt_pause = 30

            # Create Gantt bar animation
            bx     = self.panel_gantt.x + 55 + int(block.start * self.gantt_tpu)
            max_bw = max(2, int((block.end - block.start) * self.gantt_tpu))
            dur    = max(15, int((block.end - block.start) * (6 // max(1, ANIMATION_SPEED))))
            b_anim = GanttBlockAnim(block, max_bw, dur)
            b_anim._bx = bx   # store absolute x for drawing
            self.gantt_anims.append(b_anim)
            self.current_block_anim = b_anim
            self.tick_phase = 1
            return

        if self.tick_phase == 1:
            if self.current_block_anim:
                self.current_block_anim.update()
            if self.current_block_anim and self.current_block_anim.done:
                self.completed_gantt.append(self.current_block_anim)
                self.current_block_anim = None

                # Update remaining burst counter
                used = sum(
                    (b.block.end - b.block.start)
                    for b in self.completed_gantt if b.block.pid == pid
                )
                new_rem = max(0, proc.burst - used)
                if row:
                    row.set_remaining(new_rem)
                if proc.finish_time == block.end:
                    if row:
                        row.set_remaining(0)
                        row.mark_done()
                        row.arrow_visible = False

                self.anim_step += 1
                self.tick_phase = 0

        for r in self.process_rows:
            r.update()

    # ── Draw: settings panel ──────────────────────────────────────────
    def draw_settings_panel(self):
        surf = self.screen
        p    = self.panel_settings
        draw_rounded_rect(surf, WHITE, p, 10)
        pygame.draw.rect(surf, LIGHT_GRAY, p, 1, border_radius=10)

        draw_text(surf, "⚙  Settings", self.fonts['large'], CHARCOAL, p.x + 14, p.y + 12)
        draw_text(surf, "Algorithm",   self.fonts['small'], DARK_GRAY,  p.x + 14, p.y + 42)
        self.algo_dropdown.rect.topleft = (p.x + 14, p.y + 54)
        # Draw only the closed bar here; the open dropdown list is rendered last (above all panels)
        self.algo_dropdown.draw_closed(surf, self.fonts)

        y_cur = p.y + 96

        if self.has_quantum():
            draw_text(surf, "Time Quantum", self.fonts['small'], DARK_GRAY, p.x + 14, y_cur)
            self.quantum_input.rect.y = y_cur + 14
            self.quantum_input.rect.x = p.x + 14
            self.quantum_input.draw(surf, self.fonts)
            y_cur += 50

        if self.has_priority():
            draw_text(surf, "Priority Direction", self.fonts['small'], DARK_GRAY, p.x + 14, y_cur)
            self.lower_toggle.rect = pygame.Rect(p.x + 14, y_cur + 14, 40, 20)
            self.lower_toggle.x    = p.x + 14
            self.lower_toggle.y    = y_cur + 14
            self.lower_toggle.draw(surf, self.fonts)
            y_cur += 46

        # Process input sub-table (inside settings panel)
        draw_text(surf, "Processes", self.fonts['medium'], CHARCOAL, p.x + 14, y_cur + 4)
        y_cur += 22

        col_x = p.x + 14
        draw_text(surf, "PID",     self.fonts['small'], DARK_GRAY, col_x + 10, y_cur)
        draw_text(surf, "Arrival", self.fonts['small'], DARK_GRAY, col_x + 48, y_cur)
        draw_text(surf, "Burst",   self.fonts['small'], DARK_GRAY, col_x + 104, y_cur)
        if self.has_priority():
            draw_text(surf, "Pri",  self.fonts['small'], DARK_GRAY, col_x + 158, y_cur)
        y_cur += 16

        row_h = 30
        # Visible window: rows are clipped to the area above the buttons
        max_rows_y = p.bottom - 80
        clip_rect  = pygame.Rect(p.x + 6, y_cur, p.w - 12, max_rows_y - y_cur)
        old_clip   = surf.get_clip()
        surf.set_clip(clip_rect)
        for i, row in enumerate(self.input_procs):
            display_i = i - self.input_scroll      # visual row position (0-based)
            ry = y_cur + display_i * row_h
            if ry < y_cur or ry + row_h > max_rows_y:
                # Still update widget rects so they don't receive stale click targets
                row['arrival'].rect  = pygame.Rect(-200, ry + 3, 52, 24)
                row['burst'].rect    = pygame.Rect(-200, ry + 3, 52, 24)
                row['priority'].rect = pygame.Rect(-200, ry + 3, 52, 24)
                continue
            rx = p.x + 14
            bg = (248, 252, 255) if i % 2 == 0 else WHITE
            draw_rounded_rect(surf, bg, pygame.Rect(rx, ry, p.w - 28, row_h - 2), 4)
            c = PROCESS_COLORS[i % len(PROCESS_COLORS)]
            pygame.draw.circle(surf, c, (rx + 8, ry + row_h // 2), 4)
            draw_text(surf, f"P{row['pid']}", self.fonts['small'], CHARCOAL, rx + 18, ry + row_h // 2, cy=True)
            row['arrival'].rect  = pygame.Rect(rx + 44, ry + 3, 52, 24)
            row['burst'].rect    = pygame.Rect(rx + 100, ry + 3, 52, 24)
            row['priority'].rect = pygame.Rect(rx + 154, ry + 3, 52, 24)
            row['arrival'].draw(surf, self.fonts)
            row['burst'].draw(surf, self.fonts)
            if self.has_priority():
                row['priority'].draw(surf, self.fonts)
        surf.set_clip(old_clip)

        # Scrollbar for input list
        total_input   = len(self.input_procs)
        visible_input = self._input_visible_rows()
        if total_input > visible_input:
            sb_x      = p.right - 10
            sb_top    = y_cur
            sb_height = max_rows_y - y_cur
            thumb_h   = max(20, int(sb_height * visible_input / total_input))
            thumb_pct = self.input_scroll / max(1, total_input - visible_input)
            thumb_y   = sb_top + int((sb_height - thumb_h) * thumb_pct)
            pygame.draw.rect(surf, LIGHT_GRAY, pygame.Rect(sb_x, sb_top, 4, sb_height), border_radius=2)
            pygame.draw.rect(surf, MID_GRAY,   pygame.Rect(sb_x, thumb_y, 4, thumb_h),  border_radius=2)

        # Bottom buttons
        bott = p.bottom
        self.add_row_btn.rect.topleft = (p.x + 14, bott - 72)
        self.del_row_btn.rect.topleft = (p.x + 120, bott - 72)
        self.start_btn.rect.topleft   = (p.x + 14, bott - 38)
        self.reset_btn.rect.topleft   = (p.x + 144, bott - 38)
        for btn in (self.add_row_btn, self.del_row_btn, self.start_btn, self.reset_btn):
            btn.draw(surf, self.fonts)

    # ── Draw: process table panel ─────────────────────────────────────
    def draw_table_panel(self):
        surf = self.screen
        p    = self.panel_table
        draw_rounded_rect(surf, WHITE, p, 10)
        pygame.draw.rect(surf, LIGHT_GRAY, p, 1, border_radius=10)

        algo_name = ALGO_NAMES[self.get_algo()]
        draw_text(surf, "Results", self.fonts['large'], CHARCOAL, p.x + 14, p.y + 12)
        draw_text(surf, algo_name, self.fonts['small'], ACCENT,   p.x + 14, p.y + 34)

        if not self.process_rows:
            draw_text(surf, "Press  ▶  Run  to simulate", self.fonts['body'], MID_GRAY,
                      p.centerx, p.centery, cx=True, cy=True)
            return

        has_p   = self.has_priority()
        columns = self._get_columns(has_p)

        # Column headers
        hy = p.y + 52
        for lbl, col_x, col_w in columns:
            draw_text(surf, lbl, self.fonts['small'], DARK_GRAY,
                      col_x + col_w // 2, hy, cx=True)
        pygame.draw.line(surf, LIGHT_GRAY, (p.x + 10, hy + 16), (p.right - 10, hy + 16), 1)

        # Clipping rect: rows start well below the header separator line
        row_h       = 34
        row_gap     = 4
        rows_top    = hy + 22          # enough clearance below the header line
        rows_bottom = p.bottom - 124   # leave room for averages
        clip = pygame.Rect(p.x + 4, rows_top, p.w - 8, rows_bottom - rows_top)

        # Apply scroll offset: shift each row's y by -scroll * (row_h + gap)
        for i, row in enumerate(self.process_rows):
            row.y = row.base_y - self.results_scroll * (row_h + row_gap)

        for row in self.process_rows:
            row.draw(surf, self.fonts, clip, row_h)

        # Scrollbar for results panel
        total_rows   = len(self.process_rows)
        visible_rows = self._results_visible_rows()
        if total_rows > visible_rows:
            sb_x      = p.right - 10
            sb_top    = rows_top
            sb_height = rows_bottom - rows_top
            thumb_h   = max(20, int(sb_height * visible_rows / total_rows))
            thumb_pct = self.results_scroll / max(1, total_rows - visible_rows)
            thumb_y   = sb_top + int((sb_height - thumb_h) * thumb_pct)
            pygame.draw.rect(surf, LIGHT_GRAY, pygame.Rect(sb_x, sb_top, 4, sb_height), border_radius=2)
            pygame.draw.rect(surf, MID_GRAY,   pygame.Rect(sb_x, thumb_y, 4, thumb_h),  border_radius=2)

        # Average metrics
        avg_y = rows_bottom + 8
        # Always draw the background box for average metrics
        draw_rounded_rect(surf, (245, 248, 255), pygame.Rect(p.x + 10, avg_y, p.w - 20, 110), 8, 1, LIGHT_GRAY)
        if self.avg_anim:
            self.avg_anim.draw(surf, self.fonts, p.x + 10, avg_y, p.w - 20)

    # ── Draw: Gantt chart (bottom, wide) ──────────────────────────────
    def draw_gantt_panel(self):
        surf = self.screen
        p    = self.panel_gantt
        draw_rounded_rect(surf, WHITE, p, 10)
        pygame.draw.rect(surf, LIGHT_GRAY, p, 1, border_radius=10)

        draw_text(surf, "Gantt Chart", self.fonts['large'], CHARCOAL, p.x + 14, p.y + 10)

        if not self.gantt_blocks:
            draw_text(surf, "Gantt chart will appear here after running", self.fonts['body'],
                      MID_GRAY, p.centerx, p.centery, cx=True, cy=True)
            return

        chart_x = p.x + 55
        chart_w = p.w - 75
        chart_y = p.y + 42          # top of the bar row
        block_h = min(44, p.h - 90) # scale bar height to panel height
        tpu     = self.gantt_tpu
        total_t = self.gantt_total_time

        # ── Completed bars ────────────────────────────────────────────
        for banim in self.completed_gantt:
            b   = banim.block
            bx  = chart_x + int(b.start * tpu)
            bw  = max(2, int((b.end - b.start) * tpu))
            br  = pygame.Rect(bx, chart_y, bw, block_h)
            col   = b.color
            light = tuple(min(255, c + 85) for c in col)
            draw_rounded_rect(surf, light, br, 4)
            pygame.draw.rect(surf, col, br, 2, border_radius=4)
            if bw > 18:
                draw_text(surf, f'P{b.pid}', self.fonts['small'], CHARCOAL,
                          bx + bw // 2, chart_y + block_h // 2, cx=True, cy=True)

        # ── Currently animating bar ───────────────────────────────────
        for banim in self.gantt_anims:
            if banim in self.completed_gantt:
                continue
            b  = banim.block
            bx = getattr(banim, '_bx', chart_x + int(b.start * tpu))
            bw = banim.current_w()
            br = pygame.Rect(bx, chart_y, bw, block_h)
            col   = b.color
            light = tuple(min(255, c + 85) for c in col)
            draw_rounded_rect(surf, light, br, 4)
            pygame.draw.rect(surf, col, br, 2, border_radius=4)
            if bw > 18:
                draw_text(surf, f'P{b.pid}', self.fonts['small'], CHARCOAL,
                          bx + bw // 2, chart_y + block_h // 2, cx=True, cy=True)

        # ── Time axis ─────────────────────────────────────────────────
        axis_y = chart_y + block_h + 6
        pygame.draw.line(surf, LIGHT_GRAY, (chart_x, axis_y), (chart_x + chart_w, axis_y), 1)
        step = max(1, total_t // 24)
        for t in range(0, total_t + 1, step):
            tx = chart_x + int(t * tpu)
            if tx > p.right - 8:
                break
            pygame.draw.line(surf, MID_GRAY, (tx, axis_y), (tx, axis_y + 4), 1)
            draw_text(surf, str(t), self.fonts['small'], DARK_GRAY, tx, axis_y + 7, cx=True)

    # ── Draw: title bar ───────────────────────────────────────────────
    def draw_header(self):
        draw_text(self.screen, "CPU Scheduling Algorithms",
                  self.fonts['medium'], CHARCOAL, W // 2, 14, cx=True)

    # ── Event handling ────────────────────────────────────────────────
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

            self.algo_dropdown.handle_event(event)
            self.quantum_input.handle_event(event)
            self.lower_toggle.handle_event(event)

            for row in self.input_procs:
                row['arrival'].handle_event(event)
                row['burst'].handle_event(event)
                row['priority'].handle_event(event)

            if self.start_btn.handle_event(event):
                self.start_simulation()

            if self.reset_btn.handle_event(event):
                self.sim_running     = False
                self.sim_done        = False
                self.process_rows    = []
                self.gantt_blocks    = []
                self.gantt_anims     = []
                self.completed_gantt = []
                self.avg_anim        = None
                self.current_block_anim = None
                self.results_scroll  = 0

            if self.add_row_btn.handle_event(event):
                pid = len(self.input_procs) + 1
                self.input_procs.append({
                    'pid':      pid,
                    'arrival':  TextInput(0, 0, 52, 24, 0,   True, 0, 99),
                    'burst':    TextInput(0, 0, 52, 24, 4,   True, 1, 99),
                    'priority': TextInput(0, 0, 52, 24, 1,   True, 1, 99),
                })
                # Auto-scroll to show the newly added row
                self.input_scroll = max(0, len(self.input_procs) - self._input_visible_rows())

            if self.del_row_btn.handle_event(event):
                if len(self.input_procs) > 1:   # keep at least 1 row
                    self.input_procs.pop()
                    self.input_scroll = max(0, min(self.input_scroll,
                                                   max(0, len(self.input_procs) - self._input_visible_rows())))

            # Mouse-wheel scrolling — settings panel (input list) and table panel (results)
            if event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if self.panel_settings.collidepoint(mx, my):
                    self.input_scroll = max(0, min(
                        self.input_scroll - event.y,
                        max(0, len(self.input_procs) - self._input_visible_rows())
                    ))
                elif self.panel_table.collidepoint(mx, my):
                    self.results_scroll = max(0, min(
                        self.results_scroll - event.y,
                        max(0, len(self.process_rows) - self._results_visible_rows())
                    ))

    # ── Main loop ─────────────────────────────────────────────────────
    def run(self):
        while True:
            self.clock.tick(FPS)
            self.screen.fill(OFF_WHITE)

            self.handle_events()
            self.update_simulation()

            for r in self.process_rows:
                r.update()
            if self.avg_anim:
                self.avg_anim.update()

            self.draw_header()
            self.draw_settings_panel()
            self.draw_table_panel()
            self.draw_gantt_panel()
            # Draw dropdown open list last so it overlays all panels
            self.algo_dropdown.draw_open_list(self.screen, self.fonts)

            pygame.display.flip()


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sim = CPUSchedulerSim()
    sim.run()