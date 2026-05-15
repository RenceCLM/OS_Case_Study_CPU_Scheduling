"""
Process row widget for results table display.
"""

import math
import pygame
from data_structures import Process
from animations import Shake, NumberRoll, SlideIn, FadeIn
from config import (
    WHITE, OFF_WHITE, CHARCOAL, GRAY_FUTURE_TEXT, ACCENT, GREEN_DONE,
    GREEN_LIGHT, DARK_GRAY, LIGHT_GRAY, ARROW_COL
)
from ui_helpers import draw_text, draw_rounded_rect


class ProcessRow:
    """
    One row in the results table for a process.
    
    Displays:
        - Process ID, Arrival time, Burst time, Priority
        - Remaining burst time (updates during execution)
        - Waiting time and turnaround time (animates when done)
    
    Animations:
        - Slide-in from right when process starts
        - Shake when preempted
        - Rolling numbers for metrics
        - Fade to green when process completes
    """

    def __init__(self, proc: Process, y: int, has_priority: bool, columns: list):
        """
        Args:
            proc: Process object
            y: Y position in table
            has_priority: Whether to display priority column
            columns: List of (label, x, width) for layout
        """
        self.proc = proc
        self.base_y = y
        self.y = y
        self.has_priority = has_priority
        self.columns = columns

        # Animation helpers
        self.shake = None  # Shake animation
        self.slide_in = SlideIn(20, 'right')  # Initial slide-in
        self.state = 'future'  # 'future' | 'active' | 'done'

        # Metric animations
        self.remaining_anim = None  # NumberRoll for remaining burst
        self.wt_anim = None  # NumberRoll for waiting time
        self.tat_anim = None  # NumberRoll for turnaround time
        self.arrow_visible = False  # Execution pointer
        self.done_fade = FadeIn(30)

        # Tracking
        self.done_triggered = False
        self.remaining_display = proc.burst

    def trigger_shake(self, amp=5):
        """Start shake animation (when preempted)."""
        self.shake = Shake(20, amp)

    def set_remaining(self, new_val):
        """Update remaining burst with animation."""
        if new_val != self.remaining_display:
            self.remaining_anim = NumberRoll(self.remaining_display, new_val, 15)
            self.remaining_display = new_val

    def mark_done(self):
        """Mark process as complete and start result animations."""
        if not self.done_triggered:
            self.done_triggered = True
            self.done_fade = FadeIn(40)
            self.state = 'done'
            self.wt_anim = NumberRoll(0, self.proc.waiting, 30)
            self.tat_anim = NumberRoll(0, self.proc.turnaround, 30)

    def update(self):
        """Update all animations."""
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
        """
        Draw this row, clipped to clip_rect so it never overflows its panel.
        
        Args:
            surf: Pygame surface
            fonts: Font dictionary
            clip_rect: Clipping region
            row_h: Row height in pixels
        """
        # Calculate offsets for animations
        ox = self.slide_in.offset()[0]
        shake_x = self.shake.offset() if self.shake else 0
        x_off = ox + shake_x
        y = self.y

        # Skip rows completely outside clip area
        if y + row_h < clip_rect.top or y > clip_rect.bottom:
            return

        # Determine background color based on state
        if self.state == 'done':
            alpha = self.done_fade.alpha()
            bg = tuple(
                int(a + (b - a) * alpha) for a, b in zip(WHITE, GREEN_LIGHT)
            )
        elif self.state == 'active':
            bg = (240, 245, 255)
        else:
            bg = OFF_WHITE

        row_rect = pygame.Rect(clip_rect.x + 4 + x_off, y, clip_rect.w - 8, row_h)

        # Set clipping to prevent overflow
        old_clip = surf.get_clip()
        surf.set_clip(clip_rect)

        # Draw background and border
        draw_rounded_rect(surf, bg, row_rect, 5)
        border_col = GREEN_DONE if self.state == 'done' else (
            ACCENT if self.state == 'active' else LIGHT_GRAY
        )
        pygame.draw.rect(surf, border_col, row_rect, 1, border_radius=5)

        # Color indicator pill
        c = self.proc.color if self.state != 'future' else DARK_GRAY
        pygame.draw.rect(
            surf, c, pygame.Rect(row_rect.x + 4, y + row_h // 2 - 8, 4, 16), border_radius=2
        )

        text_col = GRAY_FUTURE_TEXT if self.state == 'future' else CHARCOAL

        # Draw each column
        for col_label, col_x, col_w in self.columns:
            cx = col_x + x_off + col_w // 2
            cy = y + row_h // 2

            if col_label == 'PID':
                draw_text(surf, f'P{self.proc.pid}', fonts['body_b'], text_col, cx, cy, cx=True, cy=True)

            elif col_label == 'Arrival':
                draw_text(surf, str(self.proc.arrival), fonts['body'], text_col, cx, cy, cx=True, cy=True)

            elif col_label == 'Burst':
                draw_text(surf, str(self.proc.burst), fonts['body'], text_col, cx - 10, cy, cx=True, cy=True)
                # Show remaining burst when process is running
                if self.state != 'future' and self.remaining_display < self.proc.burst:
                    rem_col = ACCENT if self.state == 'active' else DARK_GRAY
                    if self.remaining_anim and not self.remaining_anim.done:
                        yoff = self.remaining_anim.offset()
                        al = int(self.remaining_anim.alpha() * 255)
                        draw_text(
                            surf,
                            f'({self.remaining_anim.new})',
                            fonts['small'],
                            rem_col,
                            cx + 10,
                            cy - yoff,
                            al,
                            cx=True,
                            cy=True,
                        )
                    else:
                        draw_text(
                            surf,
                            f'({self.remaining_display})',
                            fonts['small'],
                            rem_col,
                            cx + 10,
                            cy,
                            cx=True,
                            cy=True,
                        )

            elif col_label == 'Priority' and self.has_priority:
                draw_text(surf, str(self.proc.priority), fonts['body'], text_col, cx, cy, cx=True, cy=True)

            elif col_label == 'WT' and self.state == 'done' and self.wt_anim:
                if not self.wt_anim.done:
                    yoff = self.wt_anim.offset()
                    al = int(self.wt_anim.alpha() * 255)
                    draw_text(
                        surf,
                        str(self.wt_anim.new),
                        fonts['body'],
                        GREEN_DONE,
                        cx,
                        cy - yoff,
                        al,
                        cx=True,
                        cy=True,
                    )
                else:
                    draw_text(
                        surf,
                        str(self.proc.waiting),
                        fonts['body'],
                        GREEN_DONE,
                        cx,
                        cy,
                        cx=True,
                        cy=True,
                    )

            elif col_label == 'TAT' and self.state == 'done' and self.tat_anim:
                if not self.tat_anim.done:
                    yoff = self.tat_anim.offset()
                    al = int(self.tat_anim.alpha() * 255)
                    draw_text(
                        surf,
                        str(self.tat_anim.new),
                        fonts['body'],
                        GREEN_DONE,
                        cx,
                        cy - yoff,
                        al,
                        cx=True,
                        cy=True,
                    )
                else:
                    draw_text(
                        surf,
                        str(self.proc.turnaround),
                        fonts['body'],
                        GREEN_DONE,
                        cx,
                        cy,
                        cx=True,
                        cy=True,
                    )

        # Draw execution arrow
        if self.arrow_visible:
            ax = row_rect.x + 2 + x_off
            ay = y + row_h // 2
            pulse = int(3 * math.sin(pygame.time.get_ticks() * 0.008))
            pygame.draw.polygon(
                surf,
                ARROW_COL,
                [(ax + pulse, ay), (ax + pulse - 8, ay - 5), (ax + pulse - 8, ay + 5)],
            )

        surf.set_clip(old_clip)
