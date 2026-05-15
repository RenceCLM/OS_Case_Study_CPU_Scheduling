"""
Animation module
"""

import math
import pygame
from typing import List
from data_structures import GanttBlock, Process


class Shake:
    """
    Horizontal shake animation for UI elements.
    Used to indicate preemption or context switches.
    
    Animation: Oscillates horizontally with damping over duration.
    """
    def __init__(self, dur=18, amp=5):
        """
        Args:
            dur: Duration in frames (18 = ~0.3s at 60fps)
            amp: Amplitude of shake in pixels (5 = default)
        """
        self.t = 0
        self.dur = dur
        self.amp = amp

    def update(self):
        """Advance animation frame."""
        self.t += 1

    def offset(self):
        """Return current horizontal offset in pixels."""
        if self.t >= self.dur:
            return 0
        return int(
            self.amp * math.sin(self.t * math.pi * 3 / self.dur) * (1 - self.t / self.dur)
        )

    @property
    def done(self):
        """Check if animation has completed."""
        return self.t >= self.dur


class NumberRoll:
    """
    Animated number transition (value appears to roll up from below).
    Used for displaying computed metrics like WT, TAT, and remaining burst.
    
    Animation: Number slides in from above with fading.
    """
    def __init__(self, old, new, dur=25):
        """
        Args:
            old: Starting value (shown initially)
            new: Ending value (animated to)
            dur: Duration in frames (25 = ~0.4s at 60fps)
        """
        self.old = old
        self.new = new
        self.t = 0
        self.dur = dur

    def update(self):
        """Advance animation frame."""
        self.t = min(self.t + 1, self.dur)

    @property
    def done(self):
        """Check if animation has completed."""
        return self.t >= self.dur

    def alpha(self):
        """Return current opacity (0.0 to 1.0)."""
        return min(1.0, self.t / self.dur)

    def offset(self):
        """Return vertical offset (slides in from above)."""
        ease = 1 - (1 - self.t / self.dur) ** 3
        return int((1 - ease) * 18)


class SlideIn:
    """
    Eased slide-in animation from a specified direction.
    Used for bringing rows and panels into view.
    
    Animation: Smoothly slides in with cubic easing.
    """
    def __init__(self, dur=20, direction='right'):
        """
        Args:
            dur: Duration in frames (20 = ~0.33s at 60fps)
            direction: 'right', 'left', 'up', or 'down'
        """
        self.t = 0
        self.dur = dur
        self.direction = direction

    def update(self):
        """Advance animation frame."""
        self.t = min(self.t + 1, self.dur)

    @property
    def done(self):
        """Check if animation has completed."""
        return self.t >= self.dur

    def progress(self):
        """Return eased progress (0.0 to 1.0) with cubic ease-out."""
        raw = self.t / self.dur
        return 1 - (1 - raw) ** 3

    def offset(self):
        """Return (x, y) offset in pixels."""
        directions = {
            'right': (1, 0),
            'left': (-1, 0),
            'up': (0, -1),
            'down': (0, 1),
        }
        d = directions[self.direction]
        p = 1 - self.progress()  # Reverse for slide-in effect
        return (int(d[0] * 40 * p), int(d[1] * 30 * p))


class GanttBlockAnim:
    """
    Animation for Gantt chart bars.
    Bar grows from left to right over duration.
    
    Animation: Width increases with easing, includes brief slide-in.
    """
    def __init__(self, block: GanttBlock, max_w: int, dur: int):
        """
        Args:
            block: GanttBlock to animate
            max_w: Final width in pixels
            dur: Duration in frames
        """
        self.block = block
        self.max_w = max_w
        self.dur = max(1, dur)
        self.t = 0
        self.slide = SlideIn(12, 'right')

    def update(self):
        """Advance animation frame."""
        self.slide.update()
        self.t = min(self.t + 1, self.dur)

    @property
    def done(self):
        """Check if animation has completed."""
        return self.t >= self.dur

    def current_w(self):
        """Return current bar width in pixels."""
        raw = self.t / self.dur
        ease = 1 - (1 - raw) ** 2  # Ease-out
        return max(2, int(self.max_w * ease))


class FadeIn:
    """
    Simple fade-in animation (opacity increasing).
    Used for showing completion state and metrics.
    
    Animation: Alpha increases from 0 to 1 linearly.
    """
    def __init__(self, dur=20):
        """
        Args:
            dur: Duration in frames (20 = ~0.33s at 60fps)
        """
        self.t = 0
        self.dur = dur

    def update(self):
        """Advance animation frame."""
        self.t = min(self.t + 1, self.dur)

    @property
    def done(self):
        """Check if animation has completed."""
        return self.t >= self.dur

    def alpha(self):
        """Return current opacity (0.0 to 1.0)."""
        return self.t / self.dur


class AverageAnim:
    """
    Animated display of average metrics (waiting time and turnaround time).
    
    Animation phases:
        0 - Waiting: Box slides in
        1 - Summing: Per-process values animate in
        2 - Averaging: Computed averages roll in
        3 - Done: All animations complete
    
    This creates a nice visual explanation of how averages are calculated.
    """
    def __init__(self, procs: List[Process]):
        """
        Args:
            procs: List of completed processes
        """
        self.procs = procs
        self.t = 0
        self.phase = 0  # 0=waiting, 1=summing, 2=averaging, 3=done
        self.sum_wt = 0
        self.sum_tat = 0
        self.wt_rolls = []  # NumberRoll for each process's WT
        self.tat_rolls = []  # NumberRoll for each process's TAT
        self.avg_wt_roll = None  # NumberRoll for average WT
        self.avg_tat_roll = None  # NumberRoll for average TAT
        self.slide = SlideIn(20, 'up')
        self._started = False

    def start(self):
        """Begin the animation sequence."""
        self._started = True
        for p in self.procs:
            self.wt_rolls.append(NumberRoll(0, p.waiting, 20))
            self.tat_rolls.append(NumberRoll(0, p.turnaround, 20))

    def update(self):
        """Update animation state and advance phases."""
        if not self._started:
            return

        self.t += 1
        self.slide.update()

        # Phase 0: Initial slide-in (20 frames)
        if self.phase == 0 and self.t > 20:
            self.phase = 1

        # Phase 1: Animate per-process values
        if self.phase == 1:
            for r in self.wt_rolls + self.tat_rolls:
                r.update()
            if all(r.done for r in self.wt_rolls + self.tat_rolls):
                self.sum_wt = sum(p.waiting for p in self.procs)
                self.sum_tat = sum(p.turnaround for p in self.procs)
                self.phase = 2

        # Phase 2: Animate average calculations
        if self.phase == 2 and not self.avg_wt_roll:
            n = len(self.procs)
            self.avg_wt_roll = NumberRoll(0, round(self.sum_wt / n, 2), 35)
            self.avg_tat_roll = NumberRoll(0, round(self.sum_tat / n, 2), 35)

        if self.phase == 2 and self.avg_wt_roll:
            self.avg_wt_roll.update()
            self.avg_tat_roll.update()
            if self.avg_wt_roll.done:
                self.phase = 3

    @property
    def done(self):
        """Check if animation has completed all phases."""
        return self.phase == 3

    def draw(self, surf, fonts, x, y, w):
        """
        Draw the average metrics animation.
        
        Args:
            surf: Pygame surface to draw on
            fonts: Font dictionary
            x, y: Top-left position
            w: Width of display area
        """
        if not self._started:
            return

        # Get slide offset
        oy = self.slide.offset()[1]
        ry = y + oy

        # Import colors here to avoid circular imports
        from config import LIGHT_GRAY, CHARCOAL, DARK_GRAY, ACCENT

        # Draw background box
        from ui_helpers import draw_rounded_rect

        draw_rounded_rect(surf, (245, 248, 255), pygame.Rect(x, ry, w, 110), 8, 1, LIGHT_GRAY)
        from ui_helpers import draw_text

        draw_text(surf, "Average Metrics", fonts['medium'], CHARCOAL, x + 12, ry + 10)
        n = len(self.procs)

        # Phase 1+: Show per-process values
        if self.phase >= 1:
            parts_wt = [
                f"P{p.pid}({(r.new if r.done else r.old)})"
                for p, r in zip(self.procs, self.wt_rolls)
            ]
            parts_tat = [
                f"P{p.pid}({(r.new if r.done else r.old)})"
                for p, r in zip(self.procs, self.tat_rolls)
            ]
            draw_text(
                surf,
                f"WT: {' + '.join(parts_wt)}",
                fonts['small'],
                DARK_GRAY,
                x + 12,
                ry + 32,
            )
            draw_text(
                surf,
                f"TAT: {' + '.join(parts_tat)}",
                fonts['small'],
                DARK_GRAY,
                x + 12,
                ry + 48,
            )

        # Phase 2+: Show average calculation
        if self.phase >= 2 and self.avg_wt_roll and self.avg_tat_roll:
            yoff_wt = self.avg_wt_roll.offset() if not self.avg_wt_roll.done else 0
            yoff_tat = self.avg_tat_roll.offset() if not self.avg_tat_roll.done else 0

            draw_text(
                surf,
                f"Avg WT  = {self.sum_wt}/{n} =",
                fonts['body'],
                CHARCOAL,
                x + 12,
                ry + 68,
            )
            draw_text(
                surf,
                str(round(self.sum_wt / n, 2)),
                fonts['body_b'],
                ACCENT,
                x + 170,
                ry + 68 - yoff_wt,
            )

            draw_text(
                surf,
                f"Avg TAT = {self.sum_tat}/{n} =",
                fonts['body'],
                CHARCOAL,
                x + 12,
                ry + 86,
            )
            draw_text(
                surf,
                str(round(self.sum_tat / n, 2)),
                fonts['body_b'],
                ACCENT,
                x + 170,
                ry + 86 - yoff_tat,
            )
