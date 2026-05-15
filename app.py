# need pip install pygame
# Main entry file, run this using python app.py

import sys
import pygame

from config import (
    ANIMATION_SPEED, WINDOW_WIDTH, WINDOW_HEIGHT, FPS,
    WHITE, OFF_WHITE, LIGHT_GRAY, MID_GRAY, DARK_GRAY, CHARCOAL,
    ACCENT, PROCESS_COLORS, ALGO_NAMES,
    ALGO_HAS_PRIORITY, ALGO_HAS_QUANTUM, ALGO_IS_PREEMPTIVE,
)
from data_structures import Process, GanttBlock
from scheduler import (
    run_fcfs, run_sjf, run_srtf, run_rr,
    run_priority_np, run_priority_p, run_priority_rr,
)
from ui_helpers import load_fonts, draw_text, draw_rounded_rect
from ui_widgets import Button, TextInput, Dropdown, Toggle
from process_row import ProcessRow
from animations import GanttBlockAnim, AverageAnim, SlideIn


class CPUSchedulerSim:
    """
    Main CPU Scheduler Simulator Application.
    
    Manages:
        - UI layout (settings, table, Gantt chart panels)
        - User input handling
        - Algorithm dispatch and simulation
        - Animation timing and coordination
        - Rendering of all visual elements
    
    Layout:
        Top-left:     Settings panel (algorithm, quantum, priority, input list)
        Top-right:    Results table (process metrics)
        Bottom:       Gantt chart (execution timeline)
    """

    # Panel dimensions
    TOP_H = 480
    GANTT_H = WINDOW_HEIGHT - TOP_H - 30

    def __init__(self):
        """Initialize pygame, screen, fonts, and UI elements."""
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("CPU Scheduling Algorithms")
        self.clock = pygame.time.Clock()
        self.fonts = load_fonts()

        # Panel geometry
        SETTINGS_W = 320
        self.panel_settings = pygame.Rect(10, 30, SETTINGS_W, self.TOP_H)
        self.panel_table = pygame.Rect(SETTINGS_W + 20, 30, WINDOW_WIDTH - SETTINGS_W - 30, self.TOP_H)
        gantt_y = self.TOP_H + 40
        self.panel_gantt = pygame.Rect(10, gantt_y, WINDOW_WIDTH - 20, self.GANTT_H)

        #  App configuration
        self.lower_is_higher = True  # Priority convention
        self.quantum = 2

        self._build_input_processes()
        self._build_settings_ui()

        #  Simulation state
        self.sim_running = False
        self.sim_done = False
        self.process_rows = []  # ProcessRow objects
        self.gantt_blocks = []  # GanttBlock results
        self.sim_procs = []  # Process objects after simulation
        self.gantt_anims = []  # Animating blocks
        self.completed_gantt = []  # Finished blocks

        # ── Animation tracking 
        self.anim_step = 0  # Which gantt block to animate
        self.tick_acc = 0  # Accumulator for frame skipping
        self.tick_phase = 0  # Phase within current block animation
        self.preempt_pause = 0  # Pause after preemption
        self.current_block_anim = None  # Currently animating Gantt block
        self.avg_anim = None  # Average metrics animation

        # Animation speed (1=slow, 2=normal, 3=fast)
        self._speed_tick = {1: 4, 2: 2, 3: 1}.get(ANIMATION_SPEED, 2)

        # Scrolling state
        self.input_scroll = 0  # Scroll position for input list
        self.results_scroll = 0  # Scroll position for results table

    # ─────────────────────────────────────────────────────────────────
    # CONFIGURATION & STATE HELPERS
    # ─────────────────────────────────────────────────────────────────

    def _build_input_processes(self):
        """Create default process input list."""
        defaults = [(1, 0, 8, 3), (2, 1, 4, 1), (3, 2, 9, 4), (4, 3, 5, 2), (5, 4, 2, 5)]
        self.input_procs = []
        for pid, arr, burst, pri in defaults:
            self.input_procs.append({
                'pid': pid,
                'arrival': TextInput(0, 0, 52, 24, arr, True, 0, 99),
                'burst': TextInput(0, 0, 52, 24, burst, True, 1, 99),
                'priority': TextInput(0, 0, 52, 24, pri, True, 1, 99),
            })

    def _build_settings_ui(self):
        """Create settings panel UI elements."""
        sx = self.panel_settings.x + 14
        self.algo_dropdown = Dropdown(sx, 60, self.panel_settings.w - 28, ALGO_NAMES, 0)
        self.quantum_input = TextInput(sx, 110, 75, 26, "2", True, 1, 20, "Quantum")
        self.lower_toggle = Toggle(sx, 150, "Lower=Higher", "Higher=Higher", True)

        bott = self.panel_settings.bottom
        self.add_row_btn = Button(sx, bott - 70, 100, 26, "+ Add Row", (80, 160, 80))
        self.del_row_btn = Button(sx + 110, bott - 70, 100, 26, "- Del Row", (200, 80, 80))
        self.start_btn = Button(sx, bott - 36, 120, 30, "▶  Run", ACCENT)
        self.reset_btn = Button(sx + 130, bott - 36, 100, 30, "↺  Reset", (80, 90, 110))

    def get_algo(self) -> int:
        """Get currently selected algorithm index."""
        return self.algo_dropdown.selected

    def has_priority(self) -> bool:
        """Check if current algorithm uses priorities."""
        return ALGO_HAS_PRIORITY[self.get_algo()]

    def has_quantum(self) -> bool:
        """Check if current algorithm uses time quantum."""
        return ALGO_HAS_QUANTUM[self.get_algo()]

    def is_preemptive(self) -> bool:
        """Check if current algorithm is preemptive."""
        return ALGO_IS_PREEMPTIVE[self.get_algo()]

    def _get_columns(self, has_priority: bool) -> list:
        """Get column layout for results table."""
        tx = self.panel_table.x + 28
        defs = [('PID', 45), ('Arrival', 58), ('Burst', 78)]
        if has_priority:
            defs.append(('Priority', 62))
        defs += [('WT', 62), ('TAT', 62)]
        cols, x = [], tx
        for lbl, w in defs:
            cols.append((lbl, x, w))
            x += w + 6
        return cols

    def _input_visible_rows(self) -> int:
        """Calculate how many input rows fit in settings panel."""
        available = self.panel_settings.h - 190 - 80
        return max(1, available // 30)

    def _results_visible_rows(self) -> int:
        """Calculate how many result rows fit in table panel."""
        rows_top = self.panel_table.y + 74
        rows_bottom = self.panel_table.bottom - 124
        return max(1, (rows_bottom - rows_top) // 38)

    # SIMULATION LOGIC
    def build_processes(self) -> list:
        return [
            Process(
                pid=row['pid'],
                arrival=row['arrival'].int_val(),
                burst=row['burst'].int_val(),
                priority=row['priority'].int_val() if self.has_priority() else 0,
                color=PROCESS_COLORS[i % len(PROCESS_COLORS)],
            )
            for i, row in enumerate(self.input_procs)
        ]

    def run_simulation(self) -> tuple:

        # Returns: (gantt_blocks, completed_processes)

        procs = self.build_processes()
        algo = self.get_algo()
        quantum = self.quantum_input.int_val()
        low = self.lower_toggle.state

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

    def start_simulation(self):
        self.sim_running = True
        self.sim_done = False
        self.anim_step = 0
        self.tick_phase = 0
        self.tick_acc = 0
        self.preempt_pause = 0
        self.avg_anim = None
        self.current_block_anim = None
        self.results_scroll = 0

        # Run algorithm
        self.gantt_blocks, self.sim_procs = self.run_simulation()

        # Calculate Gantt chart dimensions
        total_time = max((b.end for b in self.gantt_blocks), default=1)
        self.gantt_total_time = total_time
        self.gantt_tpu = (self.panel_gantt.w - 80) / max(1, total_time)
        self.gantt_anims = []
        self.completed_gantt = []

        # Create process rows
        has_p = self.has_priority()
        columns = self._get_columns(has_p)
        row_h = 34
        start_y = self.panel_table.y + 74
        self.process_rows = []
        for i, p in enumerate(self.sim_procs):
            pr = ProcessRow(p, start_y + i * (row_h + 4), has_p, columns)
            pr.slide_in = SlideIn(20 + i * 5, 'right')
            pr.state = 'future'
            self.process_rows.append(pr)

    def update_simulation(self):
        """Update simulation animation state."""
        if not self.sim_running or self.sim_done:
            return

        if self.current_block_anim:
            self.current_block_anim.update()

        if self.preempt_pause > 0:
            self.preempt_pause -= 1
            return

        # Frame skipping for animation speed
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

        # Get current block to animate
        block = self.gantt_blocks[self.anim_step]
        pid = block.pid
        proc = next((p for p in self.sim_procs if p.pid == pid), None)
        if proc is None:
            self.anim_step += 1
            return
        row = next((r for r in self.process_rows if r.proc.pid == pid), None)

        if self.tick_phase == 0:
            # Mark arrived processes
            for r in self.process_rows:
                if r.proc.arrival <= block.start and r.state == 'future':
                    r.state = 'active'

            # Update arrows
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
            bx = self.panel_gantt.x + 55 + int(block.start * self.gantt_tpu)
            max_bw = max(2, int((block.end - block.start) * self.gantt_tpu))
            dur = max(15, int((block.end - block.start) * (6 // max(1, ANIMATION_SPEED))))
            b_anim = GanttBlockAnim(block, max_bw, dur)
            b_anim._bx = bx
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

                # Update remaining counter
                used = sum(
                    (b.block.end - b.block.start)
                    for b in self.completed_gantt if b.block.pid == pid
                )
                new_rem = max(0, proc.burst - used)
                if row:
                    row.set_remaining(new_rem)
                    if proc.finish_time == block.end:
                        row.set_remaining(0)
                        row.mark_done()
                        row.arrow_visible = False

                self.anim_step += 1
                self.tick_phase = 0

        for r in self.process_rows:
            r.update()

    # RENDERING

    def draw_settings_panel(self):
        """Draw settings panel with algorithm selection and input list."""
        surf = self.screen
        p = self.panel_settings
        draw_rounded_rect(surf, WHITE, p, 10)
        pygame.draw.rect(surf, LIGHT_GRAY, p, 1, border_radius=10)

        draw_text(surf, "⚙  Settings", self.fonts['large'], CHARCOAL, p.x + 14, p.y + 12)
        draw_text(surf, "Algorithm", self.fonts['small'], DARK_GRAY, p.x + 14, p.y + 42)
        self.algo_dropdown.rect.topleft = (p.x + 14, p.y + 54)
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
            self.lower_toggle.x = p.x + 14
            self.lower_toggle.y = y_cur + 14
            self.lower_toggle.draw(surf, self.fonts)
            y_cur += 46

        # Process input section
        draw_text(surf, "Processes", self.fonts['medium'], CHARCOAL, p.x + 14, y_cur + 4)
        y_cur += 22

        col_x = p.x + 14
        draw_text(surf, "PID", self.fonts['small'], DARK_GRAY, col_x + 10, y_cur)
        draw_text(surf, "Arrival", self.fonts['small'], DARK_GRAY, col_x + 48, y_cur)
        draw_text(surf, "Burst", self.fonts['small'], DARK_GRAY, col_x + 104, y_cur)
        if self.has_priority():
            draw_text(surf, "Pri", self.fonts['small'], DARK_GRAY, col_x + 158, y_cur)
        y_cur += 16

        row_h = 30
        max_rows_y = p.bottom - 80
        clip_rect = pygame.Rect(p.x + 6, y_cur, p.w - 12, max_rows_y - y_cur)
        old_clip = surf.get_clip()
        surf.set_clip(clip_rect)

        for i, row in enumerate(self.input_procs):
            display_i = i - self.input_scroll
            ry = y_cur + display_i * row_h
            if ry < y_cur or ry + row_h > max_rows_y:
                row['arrival'].rect = pygame.Rect(-200, ry + 3, 52, 24)
                row['burst'].rect = pygame.Rect(-200, ry + 3, 52, 24)
                row['priority'].rect = pygame.Rect(-200, ry + 3, 52, 24)
                continue

            rx = p.x + 14
            bg = (248, 252, 255) if i % 2 == 0 else WHITE
            draw_rounded_rect(surf, bg, pygame.Rect(rx, ry, p.w - 28, row_h - 2), 4)
            c = PROCESS_COLORS[i % len(PROCESS_COLORS)]
            pygame.draw.circle(surf, c, (rx + 8, ry + row_h // 2), 4)
            draw_text(surf, f"P{row['pid']}", self.fonts['small'], CHARCOAL, rx + 18, ry + row_h // 2, cy=True)

            row['arrival'].rect = pygame.Rect(rx + 44, ry + 3, 52, 24)
            row['burst'].rect = pygame.Rect(rx + 100, ry + 3, 52, 24)
            row['priority'].rect = pygame.Rect(rx + 154, ry + 3, 52, 24)
            row['arrival'].draw(surf, self.fonts)
            row['burst'].draw(surf, self.fonts)
            if self.has_priority():
                row['priority'].draw(surf, self.fonts)

        surf.set_clip(old_clip)

        # Scrollbar
        total_input = len(self.input_procs)
        visible_input = self._input_visible_rows()
        if total_input > visible_input:
            sb_x = p.right - 10
            sb_top = y_cur
            sb_height = max_rows_y - y_cur
            thumb_h = max(20, int(sb_height * visible_input / total_input))
            thumb_pct = self.input_scroll / max(1, total_input - visible_input)
            thumb_y = sb_top + int((sb_height - thumb_h) * thumb_pct)
            pygame.draw.rect(surf, LIGHT_GRAY, pygame.Rect(sb_x, sb_top, 4, sb_height), border_radius=2)
            pygame.draw.rect(surf, MID_GRAY, pygame.Rect(sb_x, thumb_y, 4, thumb_h), border_radius=2)

        # Buttons
        for btn in (self.add_row_btn, self.del_row_btn, self.start_btn, self.reset_btn):
            btn.draw(surf, self.fonts)

    def draw_table_panel(self):
        """Draw results table with process metrics."""
        surf = self.screen
        p = self.panel_table
        draw_rounded_rect(surf, WHITE, p, 10)
        pygame.draw.rect(surf, LIGHT_GRAY, p, 1, border_radius=10)

        algo_name = ALGO_NAMES[self.get_algo()]
        draw_text(surf, "Results", self.fonts['large'], CHARCOAL, p.x + 14, p.y + 12)
        draw_text(surf, algo_name, self.fonts['small'], ACCENT, p.x + 14, p.y + 34)

        if not self.process_rows:
            draw_text(
                surf, "Press  ▶  Run  to simulate", self.fonts['body'],
                MID_GRAY, p.centerx, p.centery, cx=True, cy=True
            )
            return

        has_p = self.has_priority()
        columns = self._get_columns(has_p)

        hy = p.y + 52
        for lbl, col_x, col_w in columns:
            draw_text(surf, lbl, self.fonts['small'], DARK_GRAY, col_x + col_w // 2, hy, cx=True)
        pygame.draw.line(surf, LIGHT_GRAY, (p.x + 10, hy + 16), (p.right - 10, hy + 16), 1)

        row_h, row_gap = 34, 4
        rows_top = hy + 22
        rows_bottom = p.bottom - 124
        clip = pygame.Rect(p.x + 4, rows_top, p.w - 8, rows_bottom - rows_top)

        for i, row in enumerate(self.process_rows):
            row.y = row.base_y - self.results_scroll * (row_h + row_gap)

        for row in self.process_rows:
            row.draw(surf, self.fonts, clip, row_h)

        # Scrollbar
        total_rows = len(self.process_rows)
        visible_rows = self._results_visible_rows()
        if total_rows > visible_rows:
            sb_x = p.right - 10
            sb_top = rows_top
            sb_height = rows_bottom - rows_top
            thumb_h = max(20, int(sb_height * visible_rows / total_rows))
            thumb_pct = self.results_scroll / max(1, total_rows - visible_rows)
            thumb_y = sb_top + int((sb_height - thumb_h) * thumb_pct)
            pygame.draw.rect(surf, LIGHT_GRAY, pygame.Rect(sb_x, sb_top, 4, sb_height), border_radius=2)
            pygame.draw.rect(surf, MID_GRAY, pygame.Rect(sb_x, thumb_y, 4, thumb_h), border_radius=2)

        # Average metrics background
        avg_y = rows_bottom + 8
        draw_rounded_rect(surf, (245, 248, 255), pygame.Rect(p.x + 10, avg_y, p.w - 20, 110), 8, 1, LIGHT_GRAY)
        if self.avg_anim:
            self.avg_anim.draw(surf, self.fonts, p.x + 10, avg_y, p.w - 20)

    def draw_gantt_panel(self):
        """Draw Gantt chart with execution timeline."""
        surf = self.screen
        p = self.panel_gantt
        draw_rounded_rect(surf, WHITE, p, 10)
        pygame.draw.rect(surf, LIGHT_GRAY, p, 1, border_radius=10)

        draw_text(surf, "Gantt Chart", self.fonts['large'], CHARCOAL, p.x + 14, p.y + 10)

        if not self.gantt_blocks:
            draw_text(
                surf, "Gantt chart will appear here after running",
                self.fonts['body'], MID_GRAY, p.centerx, p.centery, cx=True, cy=True
            )
            return

        chart_x = p.x + 55
        chart_w = p.w - 75
        chart_y = p.y + 42
        block_h = min(44, p.h - 90)
        tpu = self.gantt_tpu
        total_t = self.gantt_total_time

        # Draw completed bars
        for banim in self.completed_gantt:
            b = banim.block
            bx = chart_x + int(b.start * tpu)
            bw = max(2, int((b.end - b.start) * tpu))
            br = pygame.Rect(bx, chart_y, bw, block_h)
            col = b.color
            light = tuple(min(255, c + 85) for c in col)
            draw_rounded_rect(surf, light, br, 4)
            pygame.draw.rect(surf, col, br, 2, border_radius=4)
            if bw > 18:
                draw_text(
                    surf, f'P{b.pid}', self.fonts['small'], CHARCOAL,
                    bx + bw // 2, chart_y + block_h // 2, cx=True, cy=True
                )

        # Draw animating bars
        for banim in self.gantt_anims:
            if banim in self.completed_gantt:
                continue
            b = banim.block
            bx = getattr(banim, '_bx', chart_x + int(b.start * tpu))
            bw = banim.current_w()
            br = pygame.Rect(bx, chart_y, bw, block_h)
            col = b.color
            light = tuple(min(255, c + 85) for c in col)
            draw_rounded_rect(surf, light, br, 4)
            pygame.draw.rect(surf, col, br, 2, border_radius=4)
            if bw > 18:
                draw_text(
                    surf, f'P{b.pid}', self.fonts['small'], CHARCOAL,
                    bx + bw // 2, chart_y + block_h // 2, cx=True, cy=True
                )

        # Draw time axis
        axis_y = chart_y + block_h + 6
        pygame.draw.line(surf, LIGHT_GRAY, (chart_x, axis_y), (chart_x + chart_w, axis_y), 1)
        step = max(1, total_t // 24)
        for t in range(0, total_t + 1, step):
            tx = chart_x + int(t * tpu)
            if tx > p.right - 8:
                break
            pygame.draw.line(surf, MID_GRAY, (tx, axis_y), (tx, axis_y + 4), 1)
            draw_text(surf, str(t), self.fonts['small'], DARK_GRAY, tx, axis_y + 7, cx=True)

    def draw_header(self):
        """Draw application title."""
        draw_text(
            self.screen, "CPU Scheduling Algorithms",
            self.fonts['medium'], CHARCOAL, WINDOW_WIDTH // 2, 14, cx=True
        )

    # EVENT HANDLING

    def handle_events(self):
        """Process all input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

            # Algorithm selection
            self.algo_dropdown.handle_event(event)
            self.quantum_input.handle_event(event)
            self.lower_toggle.handle_event(event)

            # Process inputs
            for row in self.input_procs:
                row['arrival'].handle_event(event)
                row['burst'].handle_event(event)
                row['priority'].handle_event(event)

            # Buttons
            if self.start_btn.handle_event(event):
                self.start_simulation()

            if self.reset_btn.handle_event(event):
                self.sim_running = False
                self.sim_done = False
                self.process_rows = []
                self.gantt_blocks = []
                self.gantt_anims = []
                self.completed_gantt = []
                self.avg_anim = None
                self.current_block_anim = None
                self.results_scroll = 0

            if self.add_row_btn.handle_event(event):
                pid = len(self.input_procs) + 1
                self.input_procs.append({
                    'pid': pid,
                    'arrival': TextInput(0, 0, 52, 24, 0, True, 0, 99),
                    'burst': TextInput(0, 0, 52, 24, 4, True, 1, 99),
                    'priority': TextInput(0, 0, 52, 24, 1, True, 1, 99),
                })
                self.input_scroll = max(0, len(self.input_procs) - self._input_visible_rows())

            if self.del_row_btn.handle_event(event):
                if len(self.input_procs) > 1:
                    self.input_procs.pop()
                    self.input_scroll = max(0, min(
                        self.input_scroll,
                        max(0, len(self.input_procs) - self._input_visible_rows())
                    ))

            # Scrolling
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

    # MAIN LOOP
    def run(self):
        """Main event loop."""
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
            self.algo_dropdown.draw_open_list(self.screen, self.fonts)

            pygame.display.flip()

if __name__ == "__main__":
    sim = CPUSchedulerSim()
    sim.run()
