"""
Catppuccin Mocha theme for Shuttle Codec.

Single source of truth for every color used by the UI.
`build_stylesheet()` returns the full application stylesheet and
the palette constants are exported for the few places that need
inline styling of dynamically created labels.
"""


# ─── Catppuccin Mocha palette ──────────────────────────────────────────────────
BASE: str = "#1e1e2e"
MANTLE: str = "#181825"
CRUST: str = "#11111b"
SURFACE0: str = "#313244"
SURFACE1: str = "#45475a"
SURFACE2: str = "#585b70"
OVERLAY0: str = "#6c7086"
TEXT: str = "#cdd6f4"
SUBTEXT0: str = "#a6adc8"
SUBTEXT1: str = "#bac2de"
GREEN: str = "#a6e3a1"
TEAL: str = "#94e2d5"
SKY: str = "#89dceb"
SAPPHIRE: str = "#74c7ec"
BLUE: str = "#89b4fa"
LAVENDER: str = "#b4befe"
MAUVE: str = "#cba6f7"
RED: str = "#f38ba8"
PEACH: str = "#fab387"
YELLOW: str = "#f9e2af"

# Semantic aliases used across widgets
ACCENT: str = SAPPHIRE
SUCCESS: str = GREEN
DANGER: str = RED
WARNING: str = YELLOW
SECONDARY_TEXT: str = SUBTEXT0

# Panel background used for the left column / info panels
PANEL_BG: str = BASE


def color_map() -> dict[str, str]:
    """Return the palette as a plain dict (used by tests)."""
    return {
        "BASE": BASE, "MANTLE": MANTLE, "CRUST": CRUST,
        "SURFACE0": SURFACE0, "SURFACE1": SURFACE1, "SURFACE2": SURFACE2,
        "OVERLAY0": OVERLAY0, "TEXT": TEXT, "SUBTEXT0": SUBTEXT0,
        "SUBTEXT1": SUBTEXT1, "GREEN": GREEN, "TEAL": TEAL, "SKY": SKY,
        "SAPPHIRE": SAPPHIRE, "BLUE": BLUE, "LAVENDER": LAVENDER,
        "MAUVE": MAUVE, "RED": RED, "PEACH": PEACH, "YELLOW": YELLOW,
    }


def build_stylesheet() -> str:
    """Build the full application stylesheet from the palette constants."""
    return f"""
    QMainWindow {{ background-color: {BASE}; }}
    QLabel {{
        color: {TEXT};
        font-size: 13px;
    }}
    QPushButton {{
        background-color: {SURFACE1};
        color: {TEXT};
        border: 1px solid {SURFACE2};
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {SURFACE2};
        border: 1px solid {ACCENT};
    }}
    QPushButton:pressed {{ background-color: {SURFACE0}; }}
    QPushButton:disabled {{
        background-color: {SURFACE0};
        color: {OVERLAY0};
    }}
    QPushButton#btnConvert {{
        background-color: {GREEN};
        color: {BASE};
        border: none;
        font-size: 15px;
        padding: 12px;
    }}
    QPushButton#btnConvert:hover {{ background-color: {TEAL}; }}
    QPushButton#btnConvert:disabled {{
        background-color: {SURFACE1};
        color: {OVERLAY0};
    }}
    QPushButton#btnCancel {{
        background-color: {DANGER};
        color: {BASE};
        border: none;
        font-size: 15px;
        padding: 12px;
    }}
    QPushButton#btnCancel:hover {{ background-color: {PEACH}; }}
    QPushButton#btnExpert {{
        background-color: {PEACH};
        color: {BASE};
        border: none;
        font-size: 12px;
        padding: 4px 10px;
    }}
    QPushButton#btnExpert:hover {{ background-color: {WARNING}; }}
    QComboBox {{
        background-color: {SURFACE0};
        color: {TEXT};
        border: 1px solid {SURFACE2};
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 13px;
        min-height: 24px;
    }}
    QComboBox:hover {{ border: 1px solid {ACCENT}; }}
    QComboBox::drop-down {{ border: none; padding-right: 8px; }}
    QComboBox QAbstractItemView {{
        background-color: {SURFACE0};
        color: {TEXT};
        border: 1px solid {SURFACE2};
        selection-background-color: {SURFACE1};
    }}
    QGroupBox {{
        color: {TEXT};
        font-size: 14px;
        font-weight: bold;
        border: 1px solid {SURFACE2};
        border-radius: 8px;
        margin-top: 16px;
        padding: 16px 12px 12px 12px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        padding: 0 8px;
        color: {ACCENT};
    }}
    QSlider::groove:horizontal {{
        height: 6px;
        background: {SURFACE0};
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {ACCENT};
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }}
    QSlider::sub-page:horizontal {{
        background: {ACCENT};
        border-radius: 3px;
    }}
    QProgressBar {{
        background-color: {SURFACE0};
        border: 1px solid {SURFACE2};
        border-radius: 8px;
        text-align: center;
        color: {TEXT};
        font-size: 12px;
        min-height: 22px;
    }}
    QProgressBar::chunk {{ background-color: {GREEN}; border-radius: 7px; }}
    QCheckBox {{ color: {TEXT}; font-size: 13px; }}
    QCheckBox::indicator {{
        width: 18px; height: 18px;
        border-radius: 4px;
        border: 1px solid {SURFACE2};
        background-color: {SURFACE0};
    }}
    QCheckBox::indicator:checked {{
        background-color: {ACCENT};
        border: 1px solid {ACCENT};
    }}
    QSpinBox {{
        background-color: {SURFACE0};
        color: {TEXT};
        border: 1px solid {SURFACE2};
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 13px;
    }}
    QTextEdit {{
        background-color: {CRUST};
        color: {SUBTEXT0};
        border: 1px solid {SURFACE2};
        border-radius: 6px;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 12px;
        padding: 8px;
    }}
    QLineEdit {{
        background-color: {SURFACE0};
        color: {TEXT};
        border: 1px solid {SURFACE2};
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 13px;
    }}
    QStatusBar {{
        background-color: {MANTLE};
        color: {SUBTEXT0};
        font-size: 12px;
        border-top: 1px solid {SURFACE0};
    }}
    QListWidget {{
        background-color: {CRUST};
        color: {TEXT};
        border: 1px solid {SURFACE2};
        border-radius: 6px;
        font-size: 12px;
        padding: 4px;
    }}
    QListWidget::item {{
        padding: 6px;
        border-bottom: 1px solid {SURFACE0};
    }}
    QListWidget::item:selected {{
        background-color: {SURFACE1};
        color: {TEXT};
    }}
    QTimeEdit {{
        background-color: {SURFACE0};
        color: {TEXT};
        border: 1px solid {SURFACE2};
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 13px;
    }}
    QFrame#infoPanel {{
        background-color: {MANTLE};
        border: 1px solid {SURFACE0};
        border-radius: 8px;
        padding: 8px;
    }}
    /* Dialogs (QMessageBox, QFileDialog on non-native platforms).
       Without an explicit background the dialog keeps the system's LIGHT
       palette while inheriting the light QLabel text above, which renders
       the message unreadable (light text on light background). */
    QDialog {{ background-color: {BASE}; }}
    QMessageBox {{ background-color: {MANTLE}; }}
    QMessageBox QLabel {{
        color: {TEXT};
        font-size: 13px;
    }}
    QMessageBox QPushButton {{ min-width: 90px; }}
    QMessageBox QPushButton:default {{
        background-color: {ACCENT};
        color: {CRUST};
        border: none;
    }}
    QMessageBox QPushButton:default:hover {{ background-color: {SKY}; }}
    QToolTip {{
        background-color: {SURFACE0};
        color: {TEXT};
        border: 1px solid {SURFACE2};
        padding: 4px 6px;
    }}
    QScrollArea {{
        background-color: {BASE};
        border: none;
    }}
    QScrollBar:vertical {{
        background-color: {BASE};
        width: 10px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background-color: {SURFACE1};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{ background-color: {SURFACE2}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar:horizontal {{
        background-color: {BASE};
        height: 10px;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {SURFACE1};
        border-radius: 5px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{ background-color: {SURFACE2}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
    """
