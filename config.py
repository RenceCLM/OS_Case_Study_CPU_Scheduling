"""
Configuration module
"""

# ─── Animation speed configuration ─────────────────────────────────────────────
# Set animation speed here: 1 = slow, 2 = normal, 3 = fast
ANIMATION_SPEED = 2  # <-- change this value to adjust animation speed

# ─── Window dimensions and FPS ────────────────────────────────────────────────
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 820
FPS = 60

# ─── Color palette ────────────────────────────────────────────────────────────
"""
Comprehensive color palette for all UI elements and visualizations.
Colors are defined as RGB tuples for Pygame compatibility.
"""
WHITE = (255, 255, 255)
OFF_WHITE = (248, 249, 250)
LIGHT_GRAY = (230, 234, 238)
MID_GRAY = (180, 186, 195)
DARK_GRAY = (100, 108, 120)
CHARCOAL = (40, 44, 52)
BLACK = (15, 17, 21)

# Accent colors for highlights and active states
ACCENT = (67, 120, 220)
ACCENT_DARK = (40, 80, 180)

# Status colors
GREEN_DONE = (52, 168, 83)
GREEN_LIGHT = (220, 245, 225)

# Text colors for future/inactive elements
GRAY_FUTURE_TEXT = (170, 175, 185)

# Arrow color (for execution pointer)
ARROW_COL = (220, 60, 60)

# ─── Per-process colors (cycled for multiple processes) ─────────────────────
"""
Process colors are cycled when there are more than 8 processes.
Each process is assigned a color from this palette.
"""
PROCESS_COLORS = [
    (67, 120, 220),    # blue
    (236, 100, 75),    # coral
    (52, 168, 83),     # green
    (251, 166, 0),     # amber
    (157, 85, 201),    # purple
    (0, 172, 193),     # teal
    (244, 81, 30),     # deep orange
    (30, 136, 229),    # light blue
]

# ─── Algorithm metadata ──────────────────────────────────────────────────────
"""
Metadata describing the 7 CPU scheduling algorithms and their properties.
Used for UI elements and algorithm dispatch.
"""
ALGO_NAMES = [
    "FCFS",
    "SJF (Non-Preemptive)",
    "SRTF (Preemptive)",
    "Round Robin",
    "Priority (Non-Preemptive)",
    "Priority (Preemptive)",
    "Priority + Round Robin",
]

# Algorithm feature flags: maps algorithm index to boolean
ALGO_HAS_PRIORITY = {
    0: False,  # FCFS
    1: False,  # SJF
    2: False,  # SRTF
    3: False,  # Round Robin
    4: True,   # Priority NP
    5: True,   # Priority P
    6: True,   # Priority + RR
}

ALGO_HAS_QUANTUM = {
    0: False,  # FCFS
    1: False,  # SJF
    2: False,  # SRTF
    3: True,   # Round Robin (uses quantum)
    4: False,  # Priority NP
    5: False,  # Priority P
    6: True,   # Priority + RR (uses quantum)
}

ALGO_IS_PREEMPTIVE = {
    0: False,  # FCFS
    1: False,  # SJF
    2: True,   # SRTF (preemptive)
    3: True,   # Round Robin (preemptive)
    4: False,  # Priority NP
    5: True,   # Priority P (preemptive)
    6: True,   # Priority + RR (preemptive)
}
