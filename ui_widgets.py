"""
UI Widget module for interactive controls.
Contains Button, TextInput, Dropdown, and Toggle widgets for the UI.
"""

import pygame
from config import (
    WHITE, OFF_WHITE, LIGHT_GRAY, MID_GRAY, DARK_GRAY, CHARCOAL,
    ACCENT, ACCENT_DARK
)
from ui_helpers import draw_text, draw_rounded_rect


class Button:
    """
    Clickable button widget with hover and press states.
    
    Features:
        - Hover highlight
        - Press effect (darkening)
        - Rounded corners
        - Custom text and colors
    """
    def __init__(self, x, y, w, h, text, color=ACCENT, text_color=WHITE, radius=6):
        """
        Args:
            x, y: Top-left position
            w, h: Width and height
            text: Button label
            color: Button background RGB color
            text_color: Text RGB color
            radius: Corner radius
        """
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.radius = radius
        self.hovered = False
        self.pressed = False

    def handle_event(self, event):
        """
        Process mouse events.
        
        Returns:
            bool: True if button was clicked, False otherwise
        """
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.pressed = True
            return True

        if event.type == pygame.MOUSEBUTTONUP:
            self.pressed = False

        return False

    def draw(self, surf, fonts):
        """Draw the button with current state."""
        # Adjust color based on hover/press state
        col = tuple(min(255, c + 20) for c in self.color) if self.hovered else self.color
        if self.pressed:
            col = tuple(max(0, c - 20) for c in self.color)

        draw_rounded_rect(surf, col, self.rect, self.radius)
        draw_text(
            surf,
            self.text,
            fonts['body_b'],
            self.text_color,
            self.rect.centerx,
            self.rect.centery,
            cx=True,
            cy=True,
        )


class TextInput:
    """
    Single-line text input field with cursor and validation.
    
    Features:
        - Numeric validation option
        - Min/max value clamping
        - Blinking cursor
        - Placeholder text
    """
    def __init__(self, x, y, w, h, value="", numeric=True, min_val=1, max_val=99, placeholder=""):
        """
        Args:
            x, y: Top-left position
            w, h: Width and height
            value: Initial value
            numeric: If True, only accept digits
            min_val: Minimum value for clamping
            max_val: Maximum value for clamping
            placeholder: Placeholder text when empty
        """
        self.rect = pygame.Rect(x, y, w, h)
        self.value = str(value)
        self.numeric = numeric
        self.min_val = min_val
        self.max_val = max_val
        self.placeholder = placeholder
        self.active = False
        self.cursor_vis = True
        self.cursor_t = 0

    def handle_event(self, event):
        """
        Process keyboard and mouse events.
        
        Returns:
            bool: True if field was interacted with
        """
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
        """Clamp value to min/max range if numeric."""
        if self.numeric and self.value:
            v = max(self.min_val, min(self.max_val, int(self.value)))
            self.value = str(v)

    def int_val(self):
        """Get value as integer, clamped to valid range."""
        try:
            return max(self.min_val, min(self.max_val, int(self.value)))
        except ValueError:
            return self.min_val

    def draw(self, surf, fonts):
        """Draw the input field with cursor."""
        # Blinking cursor
        self.cursor_t += 1
        if self.cursor_t > 30:
            self.cursor_vis = not self.cursor_vis
            self.cursor_t = 0

        # Background and border
        bg = WHITE if self.active else OFF_WHITE
        bc = ACCENT if self.active else LIGHT_GRAY
        draw_rounded_rect(surf, bg, self.rect, 4, 1, bc)

        # Text display
        disp = self.value if self.value else self.placeholder
        col = CHARCOAL if self.value else MID_GRAY
        cx, cy = self.rect.x + 6, self.rect.centery
        draw_text(surf, disp, fonts['body'], col, cx, cy, cy=True)

        # Cursor
        if self.active and self.cursor_vis:
            tw = fonts['body'].size(self.value)[0]
            pygame.draw.line(surf, CHARCOAL, (cx + tw, cy - 6), (cx + tw, cy + 6), 1)


class Dropdown:
    """
    Dropdown selection menu.
    
    Features:
        - Single selection
        - Hover highlighting
        - Click to open/close
        - Keyboard support through pygame events
    """
    def __init__(self, x, y, w, options, selected=0):
        """
        Args:
            x, y: Top-left position
            w: Width
            options: List of option strings
            selected: Initial selected index
        """
        self.rect = pygame.Rect(x, y, w, 28)
        self.options = options
        self.selected = selected
        self.open = False
        self.hovered_item = -1

    def handle_event(self, event):
        """
        Process mouse events for opening/closing and selection.
        
        Returns:
            bool: True if state changed
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.open = not self.open
                return True

            if self.open:
                for i in range(len(self.options)):
                    r = pygame.Rect(self.rect.x, self.rect.y + 28 + i * 26, self.rect.w, 26)
                    if r.collidepoint(event.pos):
                        self.selected = i
                        self.open = False
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
        """
        Draw only the dropdown bar (selected item + arrow).
        Does not draw the open list (use draw_open_list for that).
        """
        draw_rounded_rect(surf, WHITE, self.rect, 5, 1, LIGHT_GRAY)
        draw_text(
            surf,
            self.options[self.selected],
            fonts['body'],
            CHARCOAL,
            self.rect.x + 8,
            self.rect.centery,
            cy=True,
        )

        # Draw arrow (pointing up if open, down if closed)
        ax, ay = self.rect.right - 14, self.rect.centery
        if self.open:
            pygame.draw.polygon(
                surf, DARK_GRAY, [(ax, ay + 3), (ax + 8, ay + 3), (ax + 4, ay - 3)]
            )
        else:
            pygame.draw.polygon(
                surf, DARK_GRAY, [(ax, ay - 3), (ax + 8, ay - 3), (ax + 4, ay + 3)]
            )

    def draw_open_list(self, surf, fonts):
        """
        Draw the expanded option list.
        Call this LAST so dropdown options render above all other panels.
        """
        if not self.open:
            return

        for i, opt in enumerate(self.options):
            r = pygame.Rect(self.rect.x, self.rect.y + 28 + i * 26, self.rect.w, 26)

            # Background color
            bg = LIGHT_GRAY if i == self.hovered_item else WHITE
            if i == self.selected:
                bg = (230, 238, 255)

            draw_rounded_rect(surf, bg, r, 3)
            pygame.draw.rect(surf, LIGHT_GRAY, r, 1, border_radius=3)
            draw_text(surf, opt, fonts['body'], CHARCOAL, r.x + 8, r.centery, cy=True)


class Toggle:
    """
    Two-state toggle switch widget.
    
    Features:
        - Two distinct states
        - Label text for each state
        - Animated appearance
        - Click to toggle
    """
    def __init__(self, x, y, label_on="Lower=Higher", label_off="Higher=Higher", state=True):
        """
        Args:
            x, y: Top-left position
            label_on: Label text when state=True
            label_off: Label text when state=False
            state: Initial state (True/False)
        """
        self.x = x
        self.y = y
        self.state = state
        self.label_on = label_on
        self.label_off = label_off
        self.rect = pygame.Rect(x, y, 40, 20)

    def handle_event(self, event):
        """
        Process click events to toggle state.
        
        Returns:
            bool: True if toggled
        """
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.state = not self.state
            return True
        return False

    def draw(self, surf, fonts):
        """Draw the toggle switch."""
        # Background capsule
        bg = ACCENT if self.state else MID_GRAY
        draw_rounded_rect(surf, bg, self.rect, 10)

        # White circle
        cx = self.rect.x + (24 if self.state else 6)
        pygame.draw.circle(surf, WHITE, (cx, self.rect.centery), 8)

        # Label
        label = self.label_on if self.state else self.label_off
        draw_text(
            surf,
            label,
            fonts['small'],
            DARK_GRAY,
            self.rect.right + 6,
            self.rect.centery,
            cy=True,
        )
