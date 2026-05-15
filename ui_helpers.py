"""
UI helper functions for drawing text and shapes.
Low-level drawing utilities used throughout the application.
"""

import pygame
from config import CHARCOAL


def load_fonts():
    """
    Load system fonts with fallback chain for cross-platform compatibility.
    
    Returns:
        dict: Font dictionary with keys 'small', 'body', 'body_b', 'medium', 'large'
    
    Tries multiple font names to ensure compatibility across Windows, macOS, Linux.
    """
    pygame.font.init()
    for name in ['DejaVuSans', 'FreeSans', 'LiberationSans', 'Verdana', 'Arial', '']:
        try:
            return {
                'small': pygame.font.SysFont(name, 11),
                'body': pygame.font.SysFont(name, 13),
                'body_b': pygame.font.SysFont(name, 13, bold=True),
                'medium': pygame.font.SysFont(name, 15, bold=True),
                'large': pygame.font.SysFont(name, 20, bold=True),
            }
        except Exception:
            continue
    raise RuntimeError("No suitable font found")


def draw_text(surf, text, font, color, x, y, alpha=255, cx=False, cy=False):
    """
    Render and blit text onto a surface.
    
    Args:
        surf: Pygame surface to draw on
        text: String text to render
        font: Pygame font object
        color: RGB color tuple (r, g, b)
        x, y: Position to draw at
        alpha: Opacity (0-255, default 255 = opaque)
        cx: Center horizontally if True
        cy: Center vertically if True
    
    Returns:
        tuple: (width, height) of rendered text
    """
    rendered = font.render(str(text), True, color)
    if alpha < 255:
        rendered.set_alpha(alpha)
    
    rx = x - (rendered.get_width() // 2 if cx else 0)
    ry = y - (rendered.get_height() // 2 if cy else 0)
    
    surf.blit(rendered, (rx, ry))
    return rendered.get_width(), rendered.get_height()


def draw_rounded_rect(surf, color, rect, r=8, border=0, border_color=None):
    """
    Draw a rounded rectangle with optional border.
    
    Args:
        surf: Pygame surface to draw on
        color: RGB fill color
        rect: pygame.Rect object
        r: Corner radius in pixels (default 8)
        border: Border thickness (0 = no border)
        border_color: RGB color for border (if border > 0)
    """
    pygame.draw.rect(surf, color, rect, border_radius=r)
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=r)
