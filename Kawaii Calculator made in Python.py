"""
✿ baby calc ✿ — an aesthetic baby-pink & baby-blue calculator
Features:
- OS-aware Dark/Light mode with manual toggle
- Kawaii pop-out Calendar with Country/Timezone selection
- Crash-free and optimized for zero flickering
Run:  python baby_calc.py
"""

import pygame
import sys
import os
import math
import traceback
from datetime import datetime

# Initialize pygame immediately to prevent font/display errors
pygame.init()

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # Fallback for Python < 3.9

# ────────────────────────────────────────────────────────
#  OS Theme Detection
# ────────────────────────────────────────────────────────
def detect_os_theme():
    """Detects if the OS is in dark or light mode."""
    try:
        if sys.platform == 'win32':
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return 'light' if value == 1 else 'dark'
        elif sys.platform == 'darwin':
            import subprocess
            result = subprocess.run(['defaults', 'read', '-g', 'AppleInterfaceStyle'], capture_output=True, text=True)
            if 'Dark' in result.stdout:
                return 'dark'
            return 'light'
        else:
            if 'GTK_THEME' in os.environ and 'dark' in os.environ['GTK_THEME'].lower():
                return 'dark'
            home = os.path.expanduser('~/.config/gtk-3.0/settings.ini')
            if os.path.exists(home):
                with open(home, 'r') as f:
                    if 'gtk-application-prefer-dark-theme=1' in f.read():
                        return 'dark'
    except Exception:
        pass
    return 'light'  # Default to light mode

# ────────────────────────────────────────────────────────
#  Palettes
# ────────────────────────────────────────────────────────
THEMES = {
    'light': {
        'BG': (255, 251, 253),
        'WHITE': (255, 255, 255),
        'DISPLAY_BG_START': (255, 214, 224),
        'DISPLAY_BG_END': (214, 237, 251),
        'TEXT_DARK': (92, 78, 98),
        'NUM_BG': (255, 255, 255),
        'NUM_DEEP': (242, 240, 248),
        'PINK_LIGHT': (255, 214, 224),
        'PINK_DEEP': (255, 140, 165),
        'BABY_PINK': (255, 182, 193),
        'BLUE_LIGHT': (214, 237, 251),
        'BLUE_DEEP': (120, 180, 225),
        'BABY_BLUE': (173, 216, 230),
        'SHADOW': (210, 190, 220, 80),
        'FOOT': (200, 185, 210),
        'EQ_TEXT': (255, 255, 255),
        'ICON_BG': (255, 255, 255),
        'OVERLAY': (0, 0, 0, 80)
    },
    'dark': {
        'BG': (28, 25, 38),
        'WHITE': (45, 43, 65),
        'DISPLAY_BG_START': (70, 55, 80),
        'DISPLAY_BG_END': (45, 65, 95),
        'TEXT_DARK': (245, 245, 255),
        'NUM_BG': (45, 43, 65),
        'NUM_DEEP': (60, 58, 85),
        'PINK_LIGHT': (110, 75, 100),
        'PINK_DEEP': (255, 150, 175),
        'BABY_PINK': (200, 120, 150),
        'BLUE_LIGHT': (55, 75, 105),
        'BLUE_DEEP': (130, 190, 235),
        'BABY_BLUE': (100, 150, 200),
        'SHADOW': (0, 0, 0, 120),
        'FOOT': (120, 110, 150),
        'EQ_TEXT': (255, 255, 255),
        'ICON_BG': (55, 53, 75),
        'OVERLAY': (0, 0, 0, 140)
    }
}

T = {}          # Global active theme dict
COLORS = {}     # Button color config
current_theme = 'light'
static_bg = None
cal_overlay = None

def apply_theme(theme_name):
    global T, COLORS, current_theme
    current_theme = theme_name
    T = THEMES[theme_name]
    COLORS = {
        "fn":  (T['BLUE_LIGHT'], T['BLUE_DEEP'],  T['TEXT_DARK']),
        "op":  (T['PINK_LIGHT'], T['PINK_DEEP'],  T['TEXT_DARK']),
        "num": (T['WHITE'],      T['NUM_DEEP'],   T['TEXT_DARK']),
        "eq":  (T['BABY_PINK'],  T['PINK_DEEP'],  T['EQ_TEXT']),
    }
    build_static_surfaces()

# ────────────────────────────────────────────────────────
#  Setup
# ────────────────────────────────────────────────────────
WIDTH, HEIGHT = 420, 660
MARGIN = 22
TOP    = 200
GAP    = 12
COLS   = 4
ROWS   = 5
BW = (WIDTH - 2 * MARGIN - (COLS - 1) * GAP) / COLS
BH = (HEIGHT - TOP - MARGIN - (ROWS - 1) * GAP) / ROWS

display_rect = pygame.Rect(MARGIN, 40, WIDTH - 2 * MARGIN, 140)
theme_btn_rect = pygame.Rect(display_rect.right - 88, display_rect.y + 14, 36, 36)
cal_btn_rect   = pygame.Rect(display_rect.right - 44, display_rect.y + 14, 36, 36)

# Calendar UI States & Rects
is_cal_open = False
current_country_idx = 0
COUNTRIES = [
    ("Bangladesh",      "Asia/Dhaka"),
    ("United States",   "America/New_York"),
    ("United Kingdom",  "Europe/London"),
    ("Japan",           "Asia/Tokyo"),
    ("Australia",       "Australia/Sydney"),
    ("Germany",         "Europe/Berlin"),
    ("India",           "Asia/Kolkata"),
    ("Canada",          "America/Toronto")
]

cal_panel_rect = pygame.Rect(50, 150, 320, 300)
cal_close_rect = pygame.Rect(cal_panel_rect.centerx - 40, cal_panel_rect.bottom - 55, 80, 35)
cal_left_rect  = pygame.Rect(cal_panel_rect.left + 15, cal_panel_rect.top + 55, 30, 30)
cal_right_rect = pygame.Rect(cal_panel_rect.right - 45, cal_panel_rect.top + 55, 30, 30)


def lerp(a, b, t):
    return a + (b - a) * t

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (int(lerp(c1[0], c2[0], t)),
            int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))


# ────────────────────────────────────────────────────────
#  Calculator logic (Unchanged)
# ────────────────────────────────────────────────────────
class Calculator:
    def __init__(self):
        self.reset()

    def reset(self):
        self.display   = "0"
        self.previous  = None
        self.operator  = None
        self.waiting   = False
        self.error     = False

    def _safe_float(self):
        try:
            return float(self.display)
        except ValueError:
            self.error = True
            return 0.0

    def _fmt(self, v):
        if self.error or v in (None,):
            return "error"
        if v == 0:
            return "0"
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        s = f"{v:.8g}"
        return s

    def input_digit(self, d):
        if self.error:
            self.reset()
        if self.waiting:
            self.display = d
            self.waiting = False
        elif self.display == "0":
            self.display = d
        elif len(self.display) < 14:
            self.display += d

    def input_dot(self):
        if self.error:
            self.reset()
        if self.waiting:
            self.display = "0."
            self.waiting = False
        elif "." not in self.display:
            self.display += "."

    def negate(self):
        if self.error or self.display == "0":
            return
        if self.display.startswith("-"):
            self.display = self.display[1:]
        else:
            self.display = "-" + self.display

    def percent(self):
        if self.error:
            return
        v = self._safe_float()
        self.display = self._fmt(v / 100)

    def _compute(self, a, b, op):
        if op == "+": return a + b
        if op == "−": return a - b
        if op == "×": return a * b
        if op == "÷":
            if b == 0:
                self.error = True
                return 0
            return a / b

    def operate(self, op):
        if self.error:
            return
        v = self._safe_float()
        if self.previous is None:
            self.previous = v
        elif self.operator and not self.waiting:
            self.previous = self._compute(self.previous, v, self.operator)
            self.display  = self._fmt(self.previous)
        self.operator = op
        self.waiting  = True

    def equals(self):
        if self.error or self.operator is None or self.previous is None:
            return
        v = self._safe_float()
        result = self._compute(self.previous, v, self.operator)
        self.display  = self._fmt(result)
        self.previous = None
        self.operator = None
        self.waiting  = True
        if self.error:
            self.display = "error ♡"

    def backspace(self):
        if self.error:
            self.reset()
            return
        if self.waiting:
            return
        if len(self.display) > 1:
            self.display = self.display[:-1]
            if self.display == "-":
                self.display = "0"
        else:
            self.display = "0"

calc = Calculator()


# ────────────────────────────────────────────────────────
#  Button layout (Unchanged)
# ────────────────────────────────────────────────────────
buttons = []

def make_button(label, btype, col, row, span=1):
    x = MARGIN + col * (BW + GAP)
    y = TOP + row * (BH + GAP)
    w = BW * span + GAP * (span - 1)
    buttons.append({
        "label": label,
        "type":  btype,
        "rect":  pygame.Rect(int(x), int(y), int(w), int(BH)),
        "hover": 0.0,
        "press": 0.0,
        "flash": 0.0,
    })

make_button("AC",  "fn",  0, 0)
make_button("±",   "fn",  1, 0)
make_button("%",   "fn",  2, 0)
make_button("÷",   "op",  3, 0)

make_button("7",   "num", 0, 1)
make_button("8",   "num", 1, 1)
make_button("9",   "num", 2, 1)
make_button("×",   "op",  3, 1)

make_button("4",   "num", 0, 2)
make_button("5",   "num", 1, 2)
make_button("6",   "num", 2, 2)
make_button("−",   "op",  3, 2)

make_button("1",   "num", 0, 3)
make_button("2",   "num", 1, 3)
make_button("3",   "num", 2, 3)
make_button("+",   "op",  3, 3)

make_button("0",   "num", 0, 4, span=2)
make_button(".",   "num", 2, 4)
make_button("=",   "eq",  3, 4)


# ────────────────────────────────────────────────────────
#  Pre-rendering Static Assets (Fixes Flickering)
# ────────────────────────────────────────────────────────
def build_static_surfaces():
    global static_bg, cal_overlay
    
    # 1. Pre-render Main Background
    static_bg = pygame.Surface((WIDTH, HEIGHT))
    static_bg.fill(T['BG'])
    
    # soft pink blob
    s = pygame.Surface((260, 260), pygame.SRCALPHA)
    pygame.draw.circle(s, (255, 200, 220, 30 if current_theme == 'dark' else 55), (130, 130), 130)
    static_bg.blit(s, (-90, -90))
    # soft blue blob
    s2 = pygame.Surface((260, 260), pygame.SRCALPHA)
    pygame.draw.circle(s2, (180, 220, 255, 30 if current_theme == 'dark' else 55), (130, 130), 130)
    static_bg.blit(s2, (WIDTH - 170, HEIGHT - 170))
    # tiny sparkle dots
    for (x, y, c) in [(60, 620, T['PINK_DEEP']), (360, 50, T['BLUE_DEEP']),
                      (380, 600, T['PINK_DEEP']), (40, 130, T['BLUE_DEEP'])]:
        pygame.draw.circle(static_bg, c, (x, y), 2)

    # Display shadow
    sh = pygame.Surface((display_rect.w + 24, display_rect.h + 24), pygame.SRCALPHA)
    pygame.draw.rect(sh, T['SHADOW'], (12, 14, display_rect.w, display_rect.h), border_radius=32)
    static_bg.blit(sh, (display_rect.x - 12, display_rect.y - 12))

    # Display Gradient
    grad = pygame.Surface(display_rect.size, pygame.SRCALPHA)
    for y in range(display_rect.h):
        t = y / display_rect.h
        c = lerp_color(T['DISPLAY_BG_START'], T['DISPLAY_BG_END'], t)
        pygame.draw.line(grad, c, (0, y), (display_rect.w, y))
    mask = pygame.Surface(display_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=28)
    grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    static_bg.blit(grad, display_rect.topleft)

    # Crisp inner border
    pygame.draw.rect(static_bg, T['WHITE'], display_rect, width=2, border_radius=28)

    # 2. Pre-render Calendar Overlay
    cal_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    cal_overlay.fill(T['OVERLAY'])


# ────────────────────────────────────────────────────────
#  Drawing Dynamic UI
# ────────────────────────────────────────────────────────
def get_font(size, bold=False):
    try:
        return pygame.font.SysFont("arial", size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)

# Global font placeholders (Initialized in run_app)
font_display = None
font_button  = None
font_label   = None
font_cal_h   = None
font_cal_t   = None
font_cal_d   = None


def draw_dynamic_display_text():
    text = calc.display
    f = font_display
    ts = f.render(text, True, T['TEXT_DARK'])
    if ts.get_width() > display_rect.w - 120:  # Leaves room for icons
        scale = (display_rect.w - 120) / ts.get_width()
        f = get_font(max(18, int(56 * scale)), bold=True)
        ts = f.render(text, True, T['TEXT_DARK'])
    screen.blit(ts, ts.get_rect(midright=(display_rect.right - 20, display_rect.centery + 10)))


def draw_theme_icon(rect, mouse_pos):
    is_hover = rect.collidepoint(mouse_pos)
    pygame.draw.rect(screen, T['ICON_BG'], rect, border_radius=12)
    border_col = T['PINK_DEEP'] if is_hover else T['PINK_LIGHT']
    pygame.draw.rect(screen, border_col, rect, width=2, border_radius=12)
    
    cx, cy = rect.center
    if current_theme == 'light':
        # Sun
        pygame.draw.circle(screen, T['PINK_DEEP'], (cx, cy), 8)
        for i in range(8):
            angle = i * (math.pi / 4)
            x1 = cx + int(10 * math.cos(angle))
            y1 = cy + int(10 * math.sin(angle))
            x2 = cx + int(14 * math.cos(angle))
            y2 = cy + int(14 * math.sin(angle))
            pygame.draw.line(screen, T['PINK_DEEP'], (x1, y1), (x2, y2), 2)
    else:
        # Moon
        pygame.draw.circle(screen, T['BLUE_DEEP'], (cx, cy), 9)
        pygame.draw.circle(screen, T['ICON_BG'], (cx + 4, cy - 2), 8)


def draw_cal_icon(rect, mouse_pos):
    is_hover = rect.collidepoint(mouse_pos)
    pygame.draw.rect(screen, T['ICON_BG'], rect, border_radius=12)
    border_col = T['BLUE_DEEP'] if is_hover else T['BLUE_LIGHT']
    pygame.draw.rect(screen, border_col, rect, width=2, border_radius=12)
    
    inner = rect.inflate(-12, -12)
    pygame.draw.rect(screen, T['BLUE_DEEP'], inner, width=2, border_radius=4)
    pygame.draw.line(screen, T['BLUE_DEEP'], (inner.left, inner.top + 6), (inner.right, inner.top + 6), 2)
    pygame.draw.circle(screen, T['PINK_DEEP'], (inner.left + 4, inner.top + 3), 2)
    pygame.draw.circle(screen, T['PINK_DEEP'], (inner.right - 4, inner.top + 3), 2)


def draw_calendar_panel(mouse_pos):
    # Use pre-rendered overlay
    screen.blit(cal_overlay, (0, 0))

    # Panel Shadow
    sh = pygame.Surface((cal_panel_rect.w + 24, cal_panel_rect.h + 24), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, 120), (12, 14, cal_panel_rect.w, cal_panel_rect.h), border_radius=28)
    screen.blit(sh, (cal_panel_rect.x - 12, cal_panel_rect.y - 12))

    # Panel Body
    pygame.draw.rect(screen, T['BG'], cal_panel_rect, border_radius=24)
    pygame.draw.rect(screen, T['PINK_DEEP'], cal_panel_rect, width=3, border_radius=24)

    # Title
    title = font_label.render("✿ kawaii calendar ✿", True, T['PINK_DEEP'])
    screen.blit(title, title.get_rect(midtop=(cal_panel_rect.centerx, cal_panel_rect.top + 15)))

    # Country Selector
    country_name = COUNTRIES[current_country_idx][0]
    c_text = font_cal_h.render(country_name, True, T['TEXT_DARK'])
    screen.blit(c_text, c_text.get_rect(center=(cal_panel_rect.centerx, cal_panel_rect.top + 70)))

    # Arrows
    left_arr = font_button.render("<", True, T['BLUE_DEEP'])
    right_arr = font_button.render(">", True, T['BLUE_DEEP'])
    screen.blit(left_arr, left_arr.get_rect(center=cal_left_rect.center))
    screen.blit(right_arr, right_arr.get_rect(center=cal_right_rect.center))

    # Date and Time Logic (Safe Fallback)
    tz_name = COUNTRIES[current_country_idx][1]
    try:
        if ZoneInfo:
            tz = ZoneInfo(tz_name)
            now = datetime.now(tz)
            date_str = now.strftime("%A, %B %d, %Y")
            time_str = now.strftime("%I:%M:%S %p")
        else:
            now = datetime.now()
            date_str = now.strftime("%A, %B %d, %Y")
            time_str = now.strftime("%I:%M:%S %p")
    except Exception:
        # Fallback if tzdata module is missing on Windows
        now = datetime.now()
        date_str = "Local Time (Install tzdata)"
        time_str = now.strftime("%I:%M:%S %p")
        tz_name = "Local"

    d_text = font_cal_h.render(date_str, True, T['TEXT_DARK'])
    screen.blit(d_text, d_text.get_rect(center=(cal_panel_rect.centerx, cal_panel_rect.top + 130)))

    t_text = font_cal_t.render(time_str, True, T['PINK_DEEP'])
    screen.blit(t_text, t_text.get_rect(center=(cal_panel_rect.centerx, cal_panel_rect.top + 170)))

    # Note
    note = font_label.render(f"Timezone: {tz_name}", True, T['FOOT'])
    screen.blit(note, note.get_rect(center=(cal_panel_rect.centerx, cal_panel_rect.top + 210)))

    # Close Button
    is_hover = cal_close_rect.collidepoint(mouse_pos)
    c_col = T['PINK_LIGHT'] if not is_hover else T['BABY_PINK']
    pygame.draw.rect(screen, c_col, cal_close_rect, border_radius=12)
    pygame.draw.rect(screen, T['PINK_DEEP'], cal_close_rect, width=2, border_radius=12)
    close_text = font_label.render("close ♡", True, T['TEXT_DARK'])
    screen.blit(close_text, close_text.get_rect(center=cal_close_rect.center))


def draw_button(b, mouse_pos, mouse_down):
    r = b["rect"]
    base, deep, text_col = COLORS[b["type"]]

    is_hover = r.collidepoint(mouse_pos)
    b["hover"] += ((1.0 if is_hover else 0.0) - b["hover"]) * 0.20
    is_press = is_hover and mouse_down
    b["press"] += ((1.0 if is_press else 0.0) - b["press"]) * 0.35
    b["flash"] *= 0.86

    t = b["hover"] * 0.35 + b["press"] * 0.40 + b["flash"] * 0.55
    col = lerp_color(base, deep, t)

    # drop shadow
    sy = 5 - int(b["press"] * 3)
    shadow = pygame.Surface((r.w + 16, r.h + 16), pygame.SRCALPHA)
    pygame.draw.rect(shadow, T['SHADOW'], (8, 8 + sy, r.w, r.h), border_radius=24)
    screen.blit(shadow, (r.x - 8, r.y - 8))

    # body
    body = r.move(0, int(b["press"] * 2))
    pygame.draw.rect(screen, col, body, border_radius=22)

    # top highlight strip
    hl = pygame.Surface((body.w - 10, 10), pygame.SRCALPHA)
    pygame.draw.rect(hl, (255, 255, 255, 95), hl.get_rect(), border_radius=6)
    screen.blit(hl, (body.x + 5, body.y + 5))

    # label
    s = font_button.render(b["label"], True, text_col)
    screen.blit(s, s.get_rect(center=body.center))


def handle_calc(label):
    if   label == "AC":  calc.reset()
    elif label == "±":   calc.negate()
    elif label == "%":   calc.percent()
    elif label == ".":   calc.input_dot()
    elif label in "0123456789": calc.input_digit(label)
    elif label in "+−×÷":       calc.operate(label)
    elif label == "=":   calc.equals()


# ────────────────────────────────────────────────────────
#  Main Application Loop
# ────────────────────────────────────────────────────────
def run_app():
    global screen, is_cal_open, current_country_idx
    global font_display, font_button, font_label, font_cal_h, font_cal_t, font_cal_d
    
    try:
        # Use SCALED for vsync to prevent flickering on modern displays
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED, vsync=1)
    except Exception:
        # Fallback for older pygame versions
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        
    pygame.display.set_caption("✿ baby calc ✿")
    clock = pygame.time.Clock()

    # Initialize fonts now that pygame.init() has been called
    font_display = get_font(56, bold=True)
    font_button  = get_font(28, bold=False)
    font_label   = get_font(14, bold=True)
    font_cal_h   = get_font(20, bold=True)
    font_cal_t   = get_font(28, bold=True)
    font_cal_d   = get_font(18, bold=False)

    apply_theme(detect_os_theme())

    running = True
    mouse_down = False

    while running:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_down = True
                
                # Prioritize Calendar UI if open
                if is_cal_open:
                    if cal_close_rect.collidepoint(event.pos):
                        is_cal_open = False
                    elif cal_left_rect.collidepoint(event.pos):
                        current_country_idx = (current_country_idx - 1) % len(COUNTRIES)
                    elif cal_right_rect.collidepoint(event.pos):
                        current_country_idx = (current_country_idx + 1) % len(COUNTRIES)
                    elif not cal_panel_rect.collidepoint(event.pos):
                        is_cal_open = False  # Click outside closes it
                
                # Main UI Clicks
                else:
                    if theme_btn_rect.collidepoint(event.pos):
                        apply_theme('dark' if current_theme == 'light' else 'light')
                    elif cal_btn_rect.collidepoint(event.pos):
                        is_cal_open = True
                    else:
                        for b in buttons:
                            if b["rect"].collidepoint(event.pos):
                                handle_calc(b["label"])
                                b["flash"] = 1.0

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_down = False

            elif event.type == pygame.KEYDOWN and not is_cal_open:
                k = event.unicode
                if k in "0123456789":
                    calc.input_digit(k)
                elif k == ".":
                    calc.input_dot()
                elif k == "+":
                    calc.operate("+")
                elif k == "-":
                    calc.operate("−")
                elif k == "*":
                    calc.operate("×")
                elif k == "/":
                    calc.operate("÷")
                elif event.key in (pygame.K_RETURN, pygame.K_EQUALS):
                    calc.equals()
                elif event.key == pygame.K_BACKSPACE:
                    calc.backspace()
                elif event.key in (pygame.K_ESCAPE, pygame.K_c):
                    calc.reset()
                elif k == "%":
                    calc.percent()

        # ── render ───────────────────────────────────────
        # Blit pre-rendered static background (Fixes flicker)
        screen.blit(static_bg, (0, 0))
        
        draw_dynamic_display_text()
        draw_theme_icon(theme_btn_rect, mouse_pos)
        draw_cal_icon(cal_btn_rect, mouse_pos)

        for b in buttons:
            draw_button(b, mouse_pos, mouse_down)

        if is_cal_open:
            draw_calendar_panel(mouse_pos)

        # little footer
        foot = font_label.render("made by deadcron6900", True, T['FOOT'])
        screen.blit(foot, foot.get_rect(midbottom=(WIDTH // 2, HEIGHT - 6)))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    try:
        run_app()
    except Exception:
        # Print exact error to console instead of flickering away
        traceback.print_exc()
        input("\nPress Enter to exit...")
