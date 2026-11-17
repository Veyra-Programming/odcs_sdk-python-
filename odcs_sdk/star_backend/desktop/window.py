"""
Star Desktop Windowing Abstraction
Authoritative Reference: STAR_DESKTOP.md
"""

import sys
from typing import Optional, Callable, Dict, Any, List, Tuple


ICON_GLYPHS: Dict[str, str] = {
    "star": "★",
    "heart": "♥",
    "check": "✓",
    "close": "✕",
    "cross": "✕",
    "search": "🔍",
    "settings": "⚙",
    "user": "👤",
    "bell": "🔔",
    "arrow_right": "➔",
    "arrow_left": "⬅",
    "chevron_right": "❯",
    "chevron_left": "❮",
    "plus": "＋",
    "minus": "－",
    "refresh": "↻",
    "shield": "🛡",
    "zap": "⚡",
    "home": "🏠",
    "code": "</>",
    "info": "ℹ",
    "alert": "⚠",
    "chart": "📊",
    "sparkles": "✨",
    "moon": "🌙",
    "sun": "☀️"
}


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c * 2 for c in hex_color])
    if len(hex_color) < 6:
        return (0, 0, 0)
    try:
        return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    except Exception:
        return (0, 0, 0)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"


def _interpolate_color(c1: str, c2: str, factor: float) -> str:
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    factor = max(0.0, min(1.0, factor))
    r = int(r1 + (r2 - r1) * factor)
    g = int(g1 + (g2 - g1) * factor)
    b = int(b1 + (b2 - b1) * factor)
    return _rgb_to_hex(r, g, b)


class DesktopWindow:
    def __init__(self, title: str = "Star Application", width: int = 800, height: int = 600, bg_color: str = "#0f172a", headless: bool = False):
        self.title = title
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.headless = headless
        self.is_running = False
        self.click_handlers: List[Callable[[int, int], None]] = []
        self.motion_handlers: List[Callable[[int, int], None]] = []
        self.key_handlers: List[Callable[[str], None]] = []
        self.resize_handlers: List[Callable[[int, int], None]] = []
        self.draw_commands: List[Dict[str, Any]] = []

        self._tk_root = None
        self._tk_canvas = None
        if not self.headless:
            try:
                import tkinter as tk
                self._tk_root = tk.Tk()
                self._tk_root.title(self.title)
                self._tk_root.geometry(f"{self.width}x{self.height}")
                self._tk_root.configure(bg=self.bg_color)

                self._tk_canvas = tk.Canvas(
                    self._tk_root,
                    width=self.width,
                    height=self.height,
                    bg=self.bg_color,
                    highlightthickness=0
                )
                self._tk_canvas.pack(fill=tk.BOTH, expand=True)

                self._tk_canvas.bind("<Button-1>", self._on_tk_click)
                self._tk_canvas.bind("<Motion>", self._on_tk_motion)
                self._tk_root.bind("<Key>", self._on_tk_key)
                self._tk_root.bind("<Configure>", self._on_tk_resize)
            except Exception:
                # Fallback to virtual headless window surface
                self._tk_root = None
                self._tk_canvas = None
                self.headless = True

    def _on_tk_click(self, event):
        for h in self.click_handlers:
            h(event.x, event.y)

    def _on_tk_motion(self, event):
        for h in self.motion_handlers:
            h(event.x, event.y)

    def _on_tk_key(self, event):
        for h in self.key_handlers:
            h(event.char or event.keysym)

    def _on_tk_resize(self, event):
        if event.widget == self._tk_root:
            if event.width != self.width or event.height != self.height:
                self.width = event.width
                self.height = event.height
                for h in self.resize_handlers:
                    h(self.width, self.height)

    def bind_click(self, handler: Callable[[int, int], None]):
        self.click_handlers.append(handler)

    def bind_motion(self, handler: Callable[[int, int], None]):
        self.motion_handlers.append(handler)

    def bind_key(self, handler: Callable[[str], None]):
        self.key_handlers.append(handler)

    def bind_resize(self, handler: Callable[[int, int], None]):
        self.resize_handlers.append(handler)

    def clear(self):
        self.draw_commands.clear()
        if self._tk_canvas:
            self._tk_canvas.delete("all")

    def draw_rect(self, x: int, y: int, w: int, h: int, fill: str = "#1e293b", outline: str = "", corner_radius: int = 0):
        self.draw_commands.append({
            "type": "rect", "x": x, "y": y, "w": w, "h": h,
            "fill": fill, "outline": outline, "radius": corner_radius
        })
        if not self._tk_canvas or w <= 0 or h <= 0:
            return

        r = min(corner_radius, min(w, h) // 2)
        if r <= 2:
            kwargs: Dict[str, Any] = {"fill": fill}
            if outline:
                kwargs["outline"] = outline
            else:
                kwargs["outline"] = fill
            self._tk_canvas.create_rectangle(x, y, x + w, y + h, **kwargs)
        else:
            # Pixel-perfect rounded rectangle with 4 corner arcs + center fill
            d = 2 * r
            # Corner arcs
            self._tk_canvas.create_arc(x, y, x + d, y + d, start=90, extent=90, fill=fill, outline="")
            self._tk_canvas.create_arc(x + w - d, y, x + w, y + d, start=0, extent=90, fill=fill, outline="")
            self._tk_canvas.create_arc(x + w - d, y + h - d, x + w, y + h, start=270, extent=90, fill=fill, outline="")
            self._tk_canvas.create_arc(x, y + h - d, x + d, y + h, start=180, extent=90, fill=fill, outline="")
            # Center fill rectangles
            self._tk_canvas.create_rectangle(x + r, y, x + w - r, y + h, fill=fill, outline="")
            self._tk_canvas.create_rectangle(x, y + r, x + w, y + h - r, fill=fill, outline="")

            # Border outline if present
            if outline and outline != fill:
                self._tk_canvas.create_arc(x, y, x + d, y + d, start=90, extent=90, style="arc", outline=outline)
                self._tk_canvas.create_arc(x + w - d, y, x + w, y + d, start=0, extent=90, style="arc", outline=outline)
                self._tk_canvas.create_arc(x + w - d, y + h - d, x + w, y + h, start=270, extent=90, style="arc", outline=outline)
                self._tk_canvas.create_arc(x, y + h - d, x + d, y + h, start=180, extent=90, style="arc", outline=outline)
                self._tk_canvas.create_line(x + r, y, x + w - r, y, fill=outline)
                self._tk_canvas.create_line(x + w, y + r, x + w, y + h - r, fill=outline)
                self._tk_canvas.create_line(x + r, y + h, x + w - r, y + h, fill=outline)
                self._tk_canvas.create_line(x, y + r, x, y + h - r, fill=outline)

    def draw_gradient_rect(self, x: int, y: int, w: int, h: int, c1: str, c2: str, horizontal: bool = True, corner_radius: int = 0):
        self.draw_commands.append({
            "type": "gradient_rect", "x": x, "y": y, "w": w, "h": h,
            "c1": c1, "c2": c2, "horizontal": horizontal, "radius": corner_radius
        })
        if not self._tk_canvas or w <= 0 or h <= 0:
            return

        steps = 16
        if horizontal:
            step_w = max(1, w // steps)
            for i in range(steps):
                curr_x = x + (i * step_w)
                curr_w = step_w if i < steps - 1 else (x + w - curr_x)
                if curr_w <= 0:
                    break
                color = _interpolate_color(c1, c2, i / float(steps - 1))
                r = corner_radius if (i == 0 or i == steps - 1) else 0
                self.draw_rect(curr_x, y, curr_w, h, fill=color, corner_radius=r)
        else:
            step_h = max(1, h // steps)
            for i in range(steps):
                curr_y = y + (i * step_h)
                curr_h = step_h if i < steps - 1 else (y + h - curr_y)
                if curr_h <= 0:
                    break
                color = _interpolate_color(c1, c2, i / float(steps - 1))
                r = corner_radius if (i == 0 or i == steps - 1) else 0
                self.draw_rect(x, curr_y, w, curr_h, fill=color, corner_radius=r)

    def draw_shadow(self, x: int, y: int, w: int, h: int, corner_radius: int = 8, elevation: int = 2):
        self.draw_commands.append({
            "type": "shadow", "x": x, "y": y, "w": w, "h": h,
            "radius": corner_radius, "elevation": elevation
        })
        if not self._tk_canvas or w <= 0 or h <= 0:
            return

        # Multi-layered soft drop shadow
        layers = min(elevation, 3)
        shadow_colors = ["#070b14", "#0b1120", "#0f172a"]
        for i in range(layers):
            offset_y = (i + 1) * 2
            spread = (layers - i) * 2
            col = shadow_colors[min(i, len(shadow_colors) - 1)]
            self.draw_rect(x - spread, y + offset_y, w + (spread * 2), h, fill=col, corner_radius=corner_radius + 2)

    def draw_text(self, x: int, y: int, text: str, font: str = "Inter", size: int = 14, fill: str = "#f8fafc", anchor: str = "nw", weight: str = "normal"):
        self.draw_commands.append({
            "type": "text", "x": x, "y": y, "text": text,
            "font": font, "size": size, "fill": fill, "anchor": anchor, "weight": weight
        })
        if self._tk_canvas:
            font_tuple = (font, size, weight) if weight and weight != "normal" else (font, size)
            self._tk_canvas.create_text(x, y, text=text, fill=fill, font=font_tuple, anchor=anchor)

    def draw_button(self, x: int, y: int, w: int, h: int, label: str, bg: str = "#6366f1", fg: str = "#ffffff", corner_radius: int = 8, is_hovered: bool = False):
        button_bg = bg
        if is_hovered:
            button_bg = _interpolate_color(bg, "#ffffff", 0.15)
        self.draw_shadow(x, y, w, h, corner_radius=corner_radius, elevation=2 if is_hovered else 1)
        self.draw_rect(x, y, w, h, fill=button_bg, corner_radius=corner_radius)
        tx = x + (w // 2)
        ty = y + (h // 2)
        self.draw_text(tx, ty, label, size=13, fill=fg, anchor="center", weight="bold")

    def draw_card(self, x: int, y: int, w: int, h: int, bg: str = "#1e293b", border: str = "#334155", corner_radius: int = 12, elevation: int = 2):
        if elevation > 0:
            self.draw_shadow(x, y, w, h, corner_radius=corner_radius, elevation=elevation)
        self.draw_rect(x, y, w, h, fill=bg, outline=border, corner_radius=corner_radius)

    def draw_badge(self, x: int, y: int, label: str, bg: str = "#4f46e5", fg: str = "#ffffff") -> int:
        pad_x = 12
        pad_y = 4
        text_len = len(label) * 8
        w = text_len + (pad_x * 2)
        h = 24
        self.draw_rect(x, y, w, h, fill=bg, corner_radius=12)
        self.draw_text(x + (w // 2), y + (h // 2), label, size=11, fill=fg, anchor="center", weight="bold")
        return w

    def draw_divider(self, x: int, y: int, w: int, color: str = "#334155"):
        self.draw_commands.append({"type": "divider", "x": x, "y": y, "w": w, "color": color})
        if self._tk_canvas:
            self._tk_canvas.create_line(x, y, x + w, y, fill=color)

    def draw_input(self, x: int, y: int, w: int, h: int, placeholder: str = "", text: str = "", bg: str = "#1e293b", border: str = "#334155"):
        self.draw_rect(x, y, w, h, fill=bg, outline=border, corner_radius=8)
        display_text = text if text else placeholder
        color = "#f8fafc" if text else "#64748b"
        self.draw_text(x + 14, y + (h // 2), display_text, size=13, fill=color, anchor="w")

    def draw_icon(self, x: int, y: int, name: str, size: int = 18, fill: str = "#38bdf8"):
        glyph = ICON_GLYPHS.get(name.lower(), "★")
        self.draw_commands.append({"type": "icon", "x": x, "y": y, "name": name, "glyph": glyph, "size": size, "fill": fill})
        self.draw_text(x, y, glyph, size=size, fill=fill, anchor="center")

    def draw_avatar(self, x: int, y: int, size: int = 40, label: str = "U", bg: str = "#6366f1", fg: str = "#ffffff"):
        self.draw_rect(x, y, size, size, fill=bg, corner_radius=size // 2)
        initials = label[:2].upper() if label else "U"
        self.draw_text(x + (size // 2), y + (size // 2), initials, size=max(11, size // 3), fill=fg, anchor="center", weight="bold")

    def draw_switch(self, x: int, y: int, w: int = 48, h: int = 26, active: bool = False, active_color: str = "#10b981", inactive_color: str = "#334155"):
        self.draw_commands.append({"type": "switch", "x": x, "y": y, "w": w, "h": h, "active": active})
        bg = active_color if active else inactive_color
        r = h // 2
        self.draw_rect(x, y, w, h, fill=bg, corner_radius=r)
        thumb_r = (h - 6) // 2
        thumb_x = x + w - (thumb_r * 2) - 3 if active else x + 3
        thumb_y = y + 3
        self.draw_rect(thumb_x, thumb_y, thumb_r * 2, thumb_r * 2, fill="#ffffff", corner_radius=thumb_r)

    def draw_slider(self, x: int, y: int, w: int, h: int = 24, value: float = 50.0, min_v: float = 0.0, max_v: float = 100.0, active_color: str = "#6366f1", bg_color: str = "#334155"):
        self.draw_commands.append({"type": "slider", "x": x, "y": y, "w": w, "h": h, "value": value, "min": min_v, "max": max_v})
        track_h = 6
        track_y = y + (h - track_h) // 2
        self.draw_rect(x, track_y, w, track_h, fill=bg_color, corner_radius=3)
        span = max_v - min_v if max_v > min_v else 1.0
        frac = max(0.0, min(1.0, (value - min_v) / span))
        fill_w = int(w * frac)
        if fill_w > 0:
            self.draw_rect(x, track_y, fill_w, track_h, fill=active_color, corner_radius=3)
        knob_r = 7
        knob_x = x + fill_w - knob_r
        knob_y = y + (h // 2) - knob_r
        self.draw_rect(knob_x, knob_y, knob_r * 2, knob_r * 2, fill="#ffffff", outline=active_color, corner_radius=knob_r)

    def draw_tabs(self, x: int, y: int, w: int, h: int, tabs: List[str], active_idx: int = 0, bg: str = "#1e293b", active_bg: str = "#6366f1", fg: str = "#f8fafc"):
        self.draw_commands.append({"type": "tabs", "x": x, "y": y, "w": w, "h": h, "tabs": tabs, "active": active_idx})
        self.draw_rect(x, y, w, h, fill=bg, corner_radius=8)
        if not tabs:
            return
        tab_w = w // len(tabs)
        for i, tab_label in enumerate(tabs):
            tx = x + (i * tab_w)
            if i == active_idx:
                self.draw_rect(tx + 2, y + 2, tab_w - 4, h - 4, fill=active_bg, corner_radius=6)
                self.draw_text(tx + (tab_w // 2), y + (h // 2), tab_label, size=12, fill="#ffffff", anchor="center", weight="bold")
            else:
                self.draw_text(tx + (tab_w // 2), y + (h // 2), tab_label, size=12, fill="#94a3b8", anchor="center")

    def draw_toast(self, x: int, y: int, w: int, h: int, message: str, variant: str = "info", bg: str = "#1e293b", border: str = "#334155"):
        self.draw_commands.append({"type": "toast", "x": x, "y": y, "w": w, "h": h, "message": message, "variant": variant})
        variant_colors = {
            "info": "#38bdf8",
            "success": "#10b981",
            "warning": "#f59e0b",
            "danger": "#ef4444"
        }
        accent = variant_colors.get(variant, "#38bdf8")
        self.draw_shadow(x, y, w, h, corner_radius=10, elevation=2)
        self.draw_rect(x, y, w, h, fill=bg, outline=border, corner_radius=10)
        self.draw_rect(x + 2, y + 6, 4, h - 12, fill=accent, corner_radius=2)
        self.draw_text(x + 18, y + (h // 2), message, size=12, fill="#f8fafc", anchor="w", weight="bold")

    def draw_spinner(self, x: int, y: int, size: int = 24, color: str = "#6366f1"):
        self.draw_commands.append({"type": "spinner", "x": x, "y": y, "size": size, "color": color})
        if self._tk_canvas:
            self._tk_canvas.create_arc(x, y, x + size, y + size, start=45, extent=270, style="arc", outline=color, width=3)

    def draw_image(self, x: int, y: int, w: int, h: int, src: str = "", fit: str = "cover"):
        self.draw_commands.append({"type": "image", "x": x, "y": y, "w": w, "h": h, "src": src, "fit": fit})
        # Render clean frame with image placeholder glyph
        self.draw_rect(x, y, w, h, fill="#1e293b", outline="#334155", corner_radius=8)
        self.draw_icon(x + (w // 2), y + (h // 2) - 6, "sparkles", size=18, fill="#64748b")
        if src:
            filename = src.split("/")[-1].split("\\")[-1]
            self.draw_text(x + (w // 2), y + (h // 2) + 12, filename[:16], size=10, fill="#94a3b8", anchor="center")

    def update(self):
        if self._tk_root:
            self._tk_root.update()

    def run(self):
        self.is_running = True
        if self._tk_root:
            self._tk_root.mainloop()

    def close(self):
        self.is_running = False
        if self._tk_root:
            try:
                self._tk_root.destroy()
            except Exception:
                pass
            self._tk_root = None
            self._tk_canvas = None

