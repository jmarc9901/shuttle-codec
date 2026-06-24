import os
import sys
import time
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QSlider, QProgressBar,
    QFileDialog, QTabWidget, QGroupBox, QGridLayout, QSpinBox,
    QCheckBox, QMessageBox, QTextEdit, QLineEdit, QFrame,
    QListWidget, QListWidgetItem, QSplitter, QSizePolicy, QAbstractItemView,
    QTimeEdit, QScrollArea, QShortcut
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings, QSize, QByteArray, QPoint, QObject, QTime
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QDragEnterEvent, QDropEvent, QKeySequence

from .ffmpeg_handler import FFmpegHandler
from .ffmpeg_downloader import ensure_ffmpeg


def _get_icon_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "logo.png")
    return os.path.join(os.path.dirname(__file__), "..", "logo.png")


# ─── THREADS ────────────────────────────────────────────────────────────────────
class ConversionThread(QThread):
    progress = pyqtSignal(int, str)  # percent, status_text
    finished = pyqtSignal(bool, str, str)  # success, description, output_path
    log = pyqtSignal(str)
    eta_update = pyqtSignal(str, str)  # eta, speed

    def __init__(self, ffmpeg, cmd, description, output_path):
        super().__init__()
        self.ffmpeg = ffmpeg
        self.cmd = cmd
        self.description = description
        self.output_path = output_path
        self.start_time = 0

    def run(self):
        self.start_time = time.time()
        self.log.emit(f"▶ {self.description}")
        self.log.emit(f"  Comando: {' '.join(self.cmd)}")
        success = self.ffmpeg.start_conversion(
            self.cmd,
            progress_callback=self.on_progress,
            eta_callback=self.on_eta
        )
        elapsed = time.time() - self.start_time
        if success:
            self.log.emit(f"✅ Completado en {self._format_time(elapsed)}")
        else:
            self.log.emit("❌ Error durante la conversión")
        self.finished.emit(success, self.description, self.output_path)

    def on_progress(self, pct, status=""):
        self.progress.emit(pct, status)

    def on_eta(self, eta, speed):
        self.eta_update.emit(eta, speed)

    @staticmethod
    def _format_time(seconds):
        s = int(seconds)
        if s < 60:
            return f"{s}s"
        m, s = divmod(s, 60)
        if m < 60:
            return f"{m}m {s:02d}s"
        h, m = divmod(m, 60)
        return f"{h}h {m:02d}m {s:02d}s"


class BatchConversionManager(QObject):
    """Manages a queue of files to convert."""
    file_finished = pyqtSignal(int, bool, str)  # index, success, output_path
    all_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.queue = []  # [(input_path, output_path, cmd, description), ...]
        self.current_index = -1
        self.thread = None
        self.ffmpeg = None
        self.results = []

    def start(self, ffmpeg, items):
        self.ffmpeg = ffmpeg
        self.queue = items
        self.current_index = 0
        self.results = []
        self._process_next()

    def _process_next(self):
        if self.current_index >= len(self.queue) or self.current_index < 0:
            self.all_finished.emit()
            return
        item = self.queue[self.current_index]
        inp, out, cmd, desc = item
        self.thread = ConversionThread(self.ffmpeg, cmd, desc, out)
        self.thread.finished.connect(self._on_item_finished)
        self.thread.start()

    def _on_item_finished(self, success, desc, outpath):
        self.results.append((success, outpath))
        self.file_finished.emit(self.current_index, success, outpath)
        self.current_index += 1
        self._process_next()

    def cancel(self):
        if self.thread and self.thread.isRunning():
            self.ffmpeg.cancel_conversion()
        self.queue = []
        self.current_index = -1


# ─── MAIN WINDOW ────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ffmpeg = FFmpegHandler()
        self.current_thread = None
        self.batch_manager = BatchConversionManager()
        self.batch_items = []  # List of (input_path, output_path, settings_dict)
        self.input_file = None
        self.output_file = None
        self.media_info = None
        self.settings = QSettings("ShuttleCodec", "ShuttleCodec")
        self.simple_mode = True

        self.init_ui()
        self._load_settings()
        QTimer.singleShot(200, self._check_ffmpeg)

    # ─── UI INIT ────────────────────────────────────────────────────────────────
    def init_ui(self):
        self.setWindowTitle("Shuttle Codec")
        self.setMinimumSize(1100, 800)
        self.setAcceptDrops(True)
        self.setWindowIcon(QIcon(_get_icon_path()))

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        self._style_app()
        self._create_header(main_layout)

        # Top area: file select + presets
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        self._create_file_section(top_layout)
        main_layout.addWidget(top_widget)

        # Mode toggle
        self._create_mode_toggle(main_layout)

        # Main content: tabs + batch list
        content_splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._create_video_section(left_layout)
        self._create_trim_section(left_layout)
        content_splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self._create_batch_section(right_layout)
        content_splitter.addWidget(right_widget)

        content_splitter.setSizes([650, 350])
        main_layout.addWidget(content_splitter, 1)

        # Progress + ETA
        self._create_progress_section(main_layout)

        # Log
        self._create_log_section(main_layout)

        # Status bar
        self._create_status_bar()

        # Keyboard shortcuts
        self._setup_shortcuts()

    def _style_app(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e2e; }
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
            }
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: 1px solid #585b70;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #585b70;
                border: 1px solid #74c7ec;
            }
            QPushButton:pressed { background-color: #313244; }
            QPushButton:disabled {
                background-color: #313244;
                color: #6c7086;
            }
            QPushButton#btnConvert {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                font-size: 15px;
                padding: 12px;
            }
            QPushButton#btnConvert:hover { background-color: #94e2d5; }
            QPushButton#btnConvert:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
            QPushButton#btnCancel {
                background-color: #f38ba8;
                color: #1e1e2e;
                border: none;
                font-size: 15px;
                padding: 12px;
            }
            QPushButton#btnCancel:hover { background-color: #eba0ac; }
            QPushButton#btnExpert {
                background-color: #fab387;
                color: #1e1e2e;
                border: none;
                font-size: 12px;
                padding: 4px 10px;
            }
            QPushButton#btnExpert:hover { background-color: #f9e2af; }
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #585b70;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                min-height: 24px;
            }
            QComboBox:hover { border: 1px solid #74c7ec; }
            QComboBox::drop-down { border: none; padding-right: 8px; }
            QComboBox QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #585b70;
                selection-background-color: #45475a;
            }
            QGroupBox {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #585b70;
                border-radius: 8px;
                margin-top: 16px;
                padding: 16px 12px 12px 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                padding: 0 8px;
                color: #74c7ec;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #313244;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #74c7ec;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #74c7ec;
                border-radius: 3px;
            }
            QProgressBar {
                background-color: #313244;
                border: 1px solid #585b70;
                border-radius: 8px;
                text-align: center;
                color: #cdd6f4;
                font-size: 12px;
                min-height: 22px;
            }
            QProgressBar::chunk { background-color: #a6e3a1; border-radius: 7px; }
            QTabWidget::pane {
                background-color: #1e1e2e;
                border: 1px solid #585b70;
                border-radius: 8px;
                padding: 8px;
            }
            QTabBar::tab {
                background-color: #313244;
                color: #6c7086;
                border: 1px solid #585b70;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e2e;
                color: #74c7ec;
                border-bottom: 2px solid #74c7ec;
            }
            QTabBar::tab:hover { color: #cdd6f4; }
            QCheckBox { color: #cdd6f4; font-size: 13px; }
            QCheckBox::indicator {
                width: 18px; height: 18px;
                border-radius: 4px;
                border: 1px solid #585b70;
                background-color: #313244;
            }
            QCheckBox::indicator:checked {
                background-color: #74c7ec;
                border: 1px solid #74c7ec;
            }
            QSpinBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #585b70;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
            }
            QTextEdit {
                background-color: #11111b;
                color: #a6adc8;
                border: 1px solid #585b70;
                border-radius: 6px;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 12px;
                padding: 8px;
            }
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #585b70;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QStatusBar {
                background-color: #181825;
                color: #a6adc8;
                font-size: 12px;
                border-top: 1px solid #313244;
            }
            QListWidget {
                background-color: #11111b;
                color: #cdd6f4;
                border: 1px solid #585b70;
                border-radius: 6px;
                font-size: 12px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #313244;
            }
            QListWidget::item:selected {
                background-color: #45475a;
                color: #cdd6f4;
            }
            QTimeEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #585b70;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
            }
            QFrame#infoPanel {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 8px;
            }
        """)

    def _create_header(self, layout):
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 0, 4, 0)

        title = QLabel("Shuttle Codec")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color: #cba6f7;")

        subtitle = QLabel('Conversor de video · <a href="https://github.com/jmarc9901" style="color:#89b4fa; text-decoration:none;">Desarrollado por JMarc</a>')
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet("color: #a6adc8;")
        subtitle.setTextFormat(Qt.RichText)
        subtitle.setOpenExternalLinks(True)

        self.ffmpeg_status = QLabel("FFmpeg: ✓")
        self.ffmpeg_status.setStyleSheet("color: #a6e3a1; font-weight: bold; font-size: 13px;")

        # HW acceleration indicator
        self.hw_status = QLabel("")
        self.hw_status.setStyleSheet("color: #f9e2af; font-size: 12px;")

        self.mode_label = QLabel("🌓 Simple")
        self.mode_label.setStyleSheet("color: #fab387; font-size: 12px;")
        self.mode_label.setToolTip("Haz clic en 'Modo Experto' para ver opciones avanzadas")

        header_layout.addWidget(title)
        header_layout.addSpacing(8)
        header_layout.addWidget(subtitle)
        header_layout.addStretch()
        header_layout.addWidget(self.hw_status)
        header_layout.addSpacing(8)
        header_layout.addWidget(self.mode_label)
        header_layout.addSpacing(8)
        header_layout.addWidget(self.ffmpeg_status)

        layout.addWidget(header)

    def _create_file_section(self, layout):
        file_frame = QFrame()
        file_frame.setObjectName("infoPanel")
        file_layout = QHBoxLayout(file_frame)
        file_layout.setContentsMargins(8, 4, 8, 4)

        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("Arrastra archivos aquí o haz clic en Examinar... (Ctrl+O)")
        self.file_path.setReadOnly(True)
        file_layout.addWidget(self.file_path, 1)

        browse_btn = QPushButton("📁 Examinar")
        browse_btn.clicked.connect(self.browse_file)
        browse_btn.setFixedWidth(120)
        file_layout.addWidget(browse_btn)

        self.clear_btn = QPushButton("✕")
        self.clear_btn.clicked.connect(self.clear_file)
        self.clear_btn.setFixedWidth(40)
        file_layout.addWidget(self.clear_btn)

        layout.addWidget(file_frame)

    def _create_mode_toggle(self, layout):
        toggle_layout = QHBoxLayout()
        toggle_layout.setContentsMargins(0, 0, 0, 0)

        self.expert_btn = QPushButton("⚙ Mostrar opciones avanzadas")
        self.expert_btn.setObjectName("btnExpert")
        self.expert_btn.setCheckable(True)
        self.expert_btn.clicked.connect(self._toggle_mode)
        self.expert_btn.setFixedHeight(30)
        toggle_layout.addWidget(self.expert_btn)
        toggle_layout.addStretch()

        layout.addLayout(toggle_layout)

    def _create_video_section(self, layout):
        video_group = QGroupBox("🎬 Video")
        video_layout = QVBoxLayout(video_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Formato:"))
        self.video_format = QComboBox()
        self.video_format.addItems(self.ffmpeg.get_supported_video_formats())
        self.video_format.setMinimumWidth(200)
        self.video_format.currentIndexChanged.connect(self._on_video_format_change)
        row1.addWidget(self.video_format)
        row1.addStretch()
        video_layout.addLayout(row1)

        self.advanced_video = QWidget()
        adv = QVBoxLayout(self.advanced_video)
        adv.setContentsMargins(0, 0, 0, 0)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Preset:"))
        self.video_preset = QComboBox()
        self.video_preset.addItems(self.ffmpeg.VIDEO_FORMATS["MP4 (H.264)"]["presets"])
        self.video_preset.setCurrentText("medium")
        row2.addWidget(self.video_preset)
        row2.addStretch()
        adv.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Calidad (CRF):"))
        self.video_crf = QSlider(Qt.Horizontal)
        self.video_crf.setRange(0, 51)
        self.video_crf.setValue(23)
        self.video_crf.setFixedWidth(250)
        row3.addWidget(self.video_crf)
        self.video_crf_label = QLabel("23")
        self.video_crf_label.setFixedWidth(30)
        self.video_crf.valueChanged.connect(lambda v: self.video_crf_label.setText(str(v)))
        row3.addWidget(self.video_crf_label)

        # Quality tooltips
        self.crf_info = QLabel("Mejor")
        self.crf_info.setStyleSheet("color: #a6adc8; font-size: 11px;")
        self.video_crf.valueChanged.connect(self._update_crf_info)
        row3.addWidget(self.crf_info)
        row3.addStretch()
        adv.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Resolución:"))
        self.video_resolution = QComboBox()
        self.video_resolution.addItems([
            "Original", "3840x2160 (4K)", "2560x1440 (1440p)",
            "1920x1080 (1080p)", "1280x720 (720p)", "854x480 (480p)",
            "640x360 (360p)"
        ])
        row4.addWidget(self.video_resolution)
        row4.addStretch()
        adv.addLayout(row4)

        row5 = QHBoxLayout()
        row5.addWidget(QLabel("FPS:"))
        self.video_fps = QComboBox()
        self.video_fps.addItems(["Original", "60", "30", "24", "15"])
        row5.addWidget(self.video_fps)
        row5.addStretch()
        adv.addLayout(row5)

        row6 = QHBoxLayout()
        self.video_keep_audio = QCheckBox("Mantener audio original")
        self.video_keep_audio.setChecked(True)
        row6.addWidget(self.video_keep_audio)
        row6.addStretch()
        adv.addLayout(row6)

        # HW acceleration
        row7 = QHBoxLayout()
        self.hw_check = QCheckBox("Aceleración por hardware (NVENC)")
        self.hw_check.setVisible(False)
        row7.addWidget(self.hw_check)
        row7.addStretch()
        adv.addLayout(row7)

        self.advanced_video.setVisible(False)
        video_layout.addWidget(self.advanced_video)
        video_layout.addStretch()

        layout.addWidget(video_group)

    def _update_crf_info(self, val):
        if val <= 18:
            self.crf_info.setText("⚡ Calidad máxima")
            self.crf_info.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        elif val <= 23:
            self.crf_info.setText("👍 Alta calidad")
            self.crf_info.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        elif val <= 28:
            self.crf_info.setText("📦 Balanceado")
            self.crf_info.setStyleSheet("color: #f9e2af; font-size: 11px;")
        elif val <= 35:
            self.crf_info.setText("📉 Compresión alta")
            self.crf_info.setStyleSheet("color: #fab387; font-size: 11px;")
        else:
            self.crf_info.setText("⚠️ Muy comprimido")
            self.crf_info.setStyleSheet("color: #f38ba8; font-size: 11px;")

    def _on_video_format_change(self, index):
        fmt_name = self.video_format.currentText()
        fmt = self.ffmpeg.VIDEO_FORMATS.get(fmt_name)
        if fmt:
            self.video_preset.clear()
            self.video_preset.addItems(fmt["presets"])
            self.video_preset.setCurrentText("medium")
            self.video_crf.setRange(fmt["quality_range"][0], fmt["quality_range"][1])
            self.video_crf.setValue(fmt["default_crf"])
            self.video_crf_label.setText(str(fmt["default_crf"]))
            self._update_crf_info(fmt["default_crf"])

    def _create_trim_section(self, layout):
        trim_group = QGroupBox("✂ Recorte (opcional)")
        trim_layout = QHBoxLayout(trim_group)

        trim_layout.addWidget(QLabel("Inicio:"))
        self.trim_start = QTimeEdit(QTime(0, 0, 0))
        self.trim_start.setDisplayFormat("HH:mm:ss")
        trim_layout.addWidget(self.trim_start)

        trim_layout.addWidget(QLabel("Fin:"))
        self.trim_end = QTimeEdit(QTime(0, 0, 0))
        self.trim_end.setDisplayFormat("HH:mm:ss")
        trim_layout.addWidget(self.trim_end)

        trim_layout.addWidget(QLabel("Duración:"))
        self.trim_duration = QLabel("00:00:00")
        self.trim_duration.setStyleSheet("color: #a6e3a1; font-weight: bold; font-size: 13px;")
        trim_layout.addWidget(self.trim_duration)

        self.trim_enable = QCheckBox("Recortar")
        trim_layout.addWidget(self.trim_enable)

        trim_layout.addStretch()
        layout.addWidget(trim_group)

    def _create_batch_section(self, layout):
        batch_group = QGroupBox("📦 Lista de lote")
        batch_layout = QVBoxLayout(batch_group)

        self.batch_list = QListWidget()
        self.batch_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.batch_list.setAlternatingRowColors(False)
        batch_layout.addWidget(self.batch_list, 1)

        btn_row = QHBoxLayout()
        add_batch = QPushButton("➕ Agregar a lote")
        add_batch.clicked.connect(self._add_to_batch)
        add_batch.setFixedHeight(30)
        btn_row.addWidget(add_batch)

        remove_batch = QPushButton("➖ Quitar selección")
        remove_batch.clicked.connect(self._remove_from_batch)
        remove_batch.setFixedHeight(30)
        btn_row.addWidget(remove_batch)

        clear_batch = QPushButton("🗑 Limpiar")
        clear_batch.clicked.connect(self._clear_batch)
        clear_batch.setFixedHeight(30)
        btn_row.addWidget(clear_batch)

        batch_layout.addLayout(btn_row)

        self.batch_progress = QProgressBar()
        self.batch_progress.setVisible(False)
        self.batch_progress.setTextVisible(True)
        self.batch_progress.setFormat("%v / %m")
        batch_layout.addWidget(self.batch_progress)

        layout.addWidget(batch_group)

    def _create_progress_section(self, layout):
        progress_group = QGroupBox("Progreso")
        progress_layout = QVBoxLayout(progress_group)

        # ETA row
        eta_row = QHBoxLayout()
        self.eta_label = QLabel("")
        self.eta_label.setStyleSheet("color: #f9e2af; font-size: 12px;")
        eta_row.addWidget(self.eta_label)
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        eta_row.addWidget(self.speed_label)
        eta_row.addStretch()
        progress_layout.addLayout(eta_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)

        # Buttons
        btn_layout = QHBoxLayout()
        self.convert_btn = QPushButton("▶ Iniciar conversión")
        self.convert_btn.setObjectName("btnConvert")
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setMinimumHeight(48)
        btn_layout.addWidget(self.convert_btn)

        self.cancel_btn = QPushButton("✕ Cancelar")
        self.cancel_btn.setObjectName("btnCancel")
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setMinimumHeight(48)
        btn_layout.addWidget(self.cancel_btn)

        progress_layout.addLayout(btn_layout)
        layout.addWidget(progress_group)

    def _create_log_section(self, layout):
        log_group = QGroupBox("Registro")
        log_layout = QVBoxLayout(log_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(120)
        log_layout.addWidget(self.log_output)

        layout.addWidget(log_group)

    def _create_status_bar(self):
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Listo")

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.browse_file)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.start_conversion)
        QShortcut(QKeySequence("Delete"), self).activated.connect(self._remove_from_batch)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)

    # ─── SETTINGS PERSISTENCE ──────────────────────────────────────────────────
    def _save_settings(self):
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/state", self.saveState())
        self.settings.setValue("window/splitter", self.findChild(QSplitter).saveState())
        self.settings.setValue("last_dir", os.path.dirname(self.input_file) if self.input_file else "")
        self.settings.setValue("simple_mode", self.simple_mode)
        # Save last used settings
        self.settings.setValue("video/format", self.video_format.currentText())
        self.settings.setValue("video/crf", self.video_crf.value())
        self.settings.setValue("video/preset", self.video_preset.currentText())
        self.settings.setValue("video/resolution", self.video_resolution.currentText())
        self.settings.setValue("video/fps", self.video_fps.currentText())

    def _load_settings(self):
        geo = self.settings.value("window/geometry")
        if geo:
            self.restoreGeometry(geo)
        state = self.settings.value("window/state")
        if state:
            self.restoreState(state)
        splitter = self.findChild(QSplitter)
        if splitter:
            s = self.settings.value("window/splitter")
            if s:
                splitter.restoreState(s)

        # Restore last used settings
        vf = self.settings.value("video/format")
        if vf and self.video_format.findText(vf) >= 0:
            self.video_format.setCurrentText(vf)
        crf = self.settings.value("video/crf")
        if crf:
            self.video_crf.setValue(int(crf))
        pres = self.settings.value("video/preset")
        if pres and self.video_preset.findText(pres) >= 0:
            self.video_preset.setCurrentText(pres)
        res = self.settings.value("video/resolution")
        if res and self.video_resolution.findText(res) >= 0:
            self.video_resolution.setCurrentText(res)
        fps = self.settings.value("video/fps")
        if fps and self.video_fps.findText(fps) >= 0:
            self.video_fps.setCurrentText(fps)

    def closeEvent(self, event):
        self._save_settings()
        if self.current_thread and self.current_thread.isRunning():
            reply = QMessageBox.question(self, "Salir",
                "Hay una conversión en curso. ¿Cancelar y salir?",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.ffmpeg.cancel_conversion()
                self.current_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    # ─── FFMPEG CHECK ──────────────────────────────────────────────────────────
    def _check_ffmpeg(self):
        if self.ffmpeg.check_ffmpeg():
            self.ffmpeg_status.setText("FFmpeg: ✓")
            self.ffmpeg_status.setStyleSheet("color: #a6e3a1; font-weight: bold;")
            self.status_bar.showMessage("FFmpeg listo (embebido)")
            self._detect_hardware()
        else:
            self.ffmpeg_status.setText("FFmpeg: ✗")
            self.ffmpeg_status.setStyleSheet("color: #f38ba8; font-weight: bold;")
            QMessageBox.critical(self, "Error",
                "FFmpeg no se encontró. Asegúrate de que los binarios\n"
                "estén en la carpeta resources/bin/ del programa.")

    def _detect_hardware(self):
        """Detect hardware acceleration support"""
        hw_info = self.ffmpeg.detect_hardware_acceleration()
        if hw_info:
            self.hw_status.setText(hw_info)
            self.hw_status.setStyleSheet("color: #a6e3a1; font-size: 12px;")
            if "NVENC" in hw_info or "AMF" in hw_info or "QSV" in hw_info:
                self.hw_check.setText(f"Usar {hw_info.split()[0]}")
                self.hw_check.setVisible(True)

    # ─── MODE TOGGLE ────────────────────────────────────────────────────────────
    def _toggle_mode(self):
        self.simple_mode = not self.expert_btn.isChecked()
        self.advanced_video.setVisible(not self.simple_mode)
        if self.simple_mode:
            self.expert_btn.setText("⚙ Mostrar opciones avanzadas")
            self.mode_label.setText("🌓 Simple")
        else:
            self.expert_btn.setText("⚙ Ocultar opciones avanzadas")
            self.mode_label.setText("🔧 Experto")

    # ─── FILE HANDLING ──────────────────────────────────────────────────────────
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo multimedia",
            self.settings.value("last_dir", ""),
            "Archivos multimedia (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.mp3 *.wav *.flac *.ogg *.m4a *.aac *.wma *.jpg *.png *.gif);;Todos los archivos (*)"
        )
        if file_path:
            self.load_file(file_path)
            self.settings.setValue("last_dir", os.path.dirname(file_path))

    def clear_file(self):
        self.input_file = None
        self.output_file = None
        self.media_info = None
        self.file_path.clear()
        self.convert_btn.setEnabled(False)
        self.log_output.clear()
        self.progress_bar.setValue(0)
        self.eta_label.setText("")
        self.speed_label.setText("")

    def load_file(self, file_path):
        self.input_file = file_path
        self.file_path.setText(file_path)
        self.media_info = self.ffmpeg.get_media_info(file_path)
        self.convert_btn.setEnabled(True)
        self.log_output.clear()
        self.progress_bar.setValue(0)

        # Show file info
        codecs = self.ffmpeg.get_codecs(file_path)
        width, height = self.ffmpeg.get_resolution(file_path)
        duration = None
        bitrate = None
        if self.media_info and "format" in self.media_info:
            duration = float(self.media_info["format"].get("duration", 0))
            bitrate = self.media_info["format"].get("bit_rate", None)

        info_lines = [
            f"📄 {os.path.basename(file_path)}",
            f"📦 {os.path.getsize(file_path) / 1024 / 1024:.1f} MB",
        ]
        if codecs.get("video"):
            info_lines.append(f"🎬 {codecs['video']}")
            if width and height:
                info_lines.append(f"📐 {width}x{height}")
        if codecs.get("audio"):
            info_lines.append(f"🎵 {codecs['audio']}")
        if bitrate:
            info_lines.append(f"📊 {int(bitrate)//1000} kbps")
        if duration:
            info_lines.append(f"⏱ {self.ffmpeg.get_duration_string(duration)}")
        self.log_output.append(" | ".join(info_lines))

        # Auto-suggest best settings
        self._auto_detect_best(codecs, width, height)

    def _auto_detect_best(self, codecs, width, height):
        """Auto-suggest best preset based on file characteristics."""
        if width and height:
            # Suggest resolution
            max_dim = max(width, height)
            if max_dim >= 3800:
                res = "3840x2160 (4K)"
            elif max_dim >= 2500:
                res = "2560x1440 (1440p)"
            elif max_dim >= 1900:
                res = "1920x1080 (1080p)"
            elif max_dim >= 1200:
                res = "1280x720 (720p)"
            elif max_dim >= 800:
                res = "854x480 (480p)"
            else:
                res = "640x360 (360p)"

            if self.video_resolution.findText(res) >= 0:
                self.video_resolution.setCurrentText(res)

        # Suggest format based on codec
        vcodec = codecs.get("video", "")
        if vcodec and ("265" in vcodec or "hevc" in vcodec.lower()):
            if self.video_format.findText("MP4 (H.265)") >= 0:
                self.video_format.setCurrentText("MP4 (H.265)")
        elif vcodec and "264" in vcodec:
            if self.video_format.findText("MP4 (H.264)") >= 0:
                self.video_format.setCurrentText("MP4 (H.264)")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if not urls:
            return
        # If multiple files, add all to batch
        file_paths = [u.toLocalFile() for u in urls if os.path.isfile(u.toLocalFile())]
        if len(file_paths) == 1:
            self.load_file(file_paths[0])
        elif len(file_paths) > 1:
            self.load_file(file_paths[0])
            for fp in file_paths:
                self._add_single_to_batch(fp)

    # ─── BATCH ──────────────────────────────────────────────────────────────────
    def _add_to_batch(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Agregar archivos al lote",
            self.settings.value("last_dir", ""),
            "Archivos multimedia (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.mp3 *.wav *.flac *.ogg *.m4a *.aac);;Todos los archivos (*)"
        )
        for fp in files:
            self._add_single_to_batch(fp)

    def _add_single_to_batch(self, file_path):
        self.batch_items.append((file_path, None))  # output_path set later
        item = QListWidgetItem(os.path.basename(file_path))
        item.setToolTip(file_path)
        self.batch_list.addItem(item)
        self._update_batch_ui()

    def _remove_from_batch(self):
        for item in self.batch_list.selectedItems():
            row = self.batch_list.row(item)
            if row < len(self.batch_items):
                self.batch_items.pop(row)
            self.batch_list.takeItem(row)
        self._update_batch_ui()

    def _clear_batch(self):
        self.batch_items.clear()
        self.batch_list.clear()
        self._update_batch_ui()

    def _update_batch_ui(self):
        count = self.batch_list.count()
        if count > 0:
            self.convert_btn.setText(f"▶ Convertir {count} archivo(s)")
        else:
            self.convert_btn.setText("▶ Iniciar conversión")

    # ─── CONVERSION ─────────────────────────────────────────────────────────────
    def _get_trim_params(self):
        """Get trim start/end if enabled."""
        if not self.trim_enable.isChecked():
            return None, None
        start = self.trim_start.time()
        end = self.trim_end.time()
        start_s = start.hour() * 3600 + start.minute() * 60 + start.second()
        end_s = end.hour() * 3600 + end.minute() * 60 + end.second()
        if end_s <= start_s:
            return None, None
        return start_s, end_s - start_s

    def _get_settings_from_ui(self):
        """Get current video settings from UI."""
        fmt_name = self.video_format.currentText()
        fmt = self.ffmpeg.VIDEO_FORMATS.get(fmt_name)
        resolution = self.video_resolution.currentText()
        res_map = {
            "Original": None,
            "3840x2160 (4K)": "3840:2160",
            "2560x1440 (1440p)": "2560:1440",
            "1920x1080 (1080p)": "1920:1080",
            "1280x720 (720p)": "1280:720",
            "854x480 (480p)": "854:480",
            "640x360 (360p)": "640:360",
        }
        fps = self.video_fps.currentText()
        settings = {
            "format": fmt_name,
            "crf": self.video_crf.value(),
            "preset": self.video_preset.currentText(),
            "resolution": res_map.get(resolution),
            "framerate": None if fps == "Original" else fps,
            "keep_audio": self.video_keep_audio.isChecked(),
            "audio_codec": "aac",
            "audio_bitrate": "192k",
            "hw_accel": self.hw_check.isChecked() if self.hw_check.isVisible() else False,
            "extension": fmt["extension"] if fmt else ".mp4",
        }
        return "video", settings

    def _build_output_path(self, input_path):
        """Build output file path based on input."""
        base, _ = os.path.splitext(input_path)
        return f"{base}_convertido.mp4"

    def start_conversion(self):
        if not self.ffmpeg.check_ffmpeg():
            QMessageBox.critical(self, "Error", "FFmpeg no está disponible.")
            return

        # Check if we have batch items
        if self.batch_items:
            self._start_batch_conversion()
            return

        # Single file conversion
        if not self.input_file:
            QMessageBox.warning(self, "Error", "Selecciona un archivo primero.")
            return

        mode, settings = self._get_settings_from_ui()
        output_file = self._build_output_path(self.input_file)

        output_file, _ = QFileDialog.getSaveFileName(
            self, "Guardar como", output_file,
            "Todos los archivos (*)"
        )
        if not output_file:
            return

        self.output_file = output_file
        trim_start, trim_duration = self._get_trim_params()
        cmd = self.ffmpeg.build_convert_command(
            self.input_file, output_file, mode, settings,
            trim_start=trim_start, trim_duration=trim_duration
        )
        if not cmd:
            QMessageBox.critical(self, "Error", "No se pudo construir el comando.")
            return

        description = f"{os.path.basename(self.input_file)} → {os.path.basename(output_file)}"
        self._run_conversion_thread(cmd, description, output_file)

    def _start_batch_conversion(self):
        """Convert all files in batch queue with same settings."""
        mode, settings = self._get_settings_from_ui()
        trim_start, trim_duration = self._get_trim_params()

        items = []
        for inp, _ in self.batch_items:
            output = self._build_output_path(inp)
            cmd = self.ffmpeg.build_convert_command(
                inp, output, mode, settings,
                trim_start=trim_start, trim_duration=trim_duration
            )
            if cmd:
                desc = f"{os.path.basename(inp)} → {os.path.basename(output)}"
                items.append((inp, output, cmd, desc))

        if not items:
            return

        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.batch_progress.setVisible(True)
        self.batch_progress.setMaximum(len(items))
        self.batch_progress.setValue(0)
        self.log_output.append(f"\n📦 Iniciando lote de {len(items)} archivo(s)...")

        # Connect batch manager
        self.batch_manager.file_finished.connect(self._on_batch_file_finished)
        self.batch_manager.all_finished.connect(self._on_batch_all_finished)
        self.batch_manager.start(self.ffmpeg, items)

    def _on_batch_file_finished(self, index, success, outpath):
        self.batch_progress.setValue(index + 1)
        status = "✅" if success else "❌"
        self.log_output.append(f"  {status} [{index+1}/{self.batch_progress.maximum()}] {os.path.basename(outpath)}")
        # Update list item
        item = self.batch_list.item(index)
        if item:
            item.setText(f"{'✅' if success else '❌'} {item.text()}")

    def _on_batch_all_finished(self):
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.batch_progress.setVisible(False)
        results = self.batch_manager.results
        success_count = sum(1 for s, _ in results if s)
        self.log_output.append(f"\n📊 Lote completado: {success_count}/{len(results)} exitosos")
        self.status_bar.showMessage(f"Lote: {success_count}/{len(results)} completados")
        QMessageBox.information(self, "Lote completado",
            f"Procesados {len(results)} archivo(s).\n"
            f"Exitosos: {success_count}\n"
            f"Fallos: {len(results) - success_count}")

    def _run_conversion_thread(self, cmd, description, output_path):
        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.eta_label.setText("")
        self.speed_label.setText("")
        self.log_output.append(f"\n{'─'*50}")

        self.current_thread = ConversionThread(self.ffmpeg, cmd, description, output_path)
        self.current_thread.progress.connect(self._on_progress)
        self.current_thread.finished.connect(self._on_conversion_finished)
        self.current_thread.log.connect(self.log_output.append)
        self.current_thread.eta_update.connect(self._on_eta_update)
        self.current_thread.start()

    def _on_progress(self, pct, status):
        self.progress_bar.setValue(pct)
        if status:
            self.status_bar.showMessage(status)

    def _on_eta_update(self, eta, speed):
        self.eta_label.setText(f"⏱ Tiempo restante: {eta}")
        self.speed_label.setText(f"⚡ {speed}")

    def _on_conversion_finished(self, success, description, output_path):
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        if success:
            self.status_bar.showMessage(f"✅ Completado: {description}")
            self._update_batch_ui()
            reply = QMessageBox.information(self, "Completado",
                f"Conversión exitosa.\n\n{output_path}",
                QMessageBox.Open | QMessageBox.Ok)
            if reply == QMessageBox.Open:
                os.startfile(os.path.dirname(output_path))
        else:
            self.status_bar.showMessage(f"❌ Falló: {description}")

    def cancel_conversion(self):
        if self.current_thread and self.current_thread.isRunning():
            self.ffmpeg.cancel_conversion()
            self.log_output.append("⏹ Conversión cancelada.")
            self.current_thread.wait()
            self._on_conversion_finished(False, "Cancelado", "")
        # Also cancel batch
        if self.batch_manager.queue:
            self.batch_manager.cancel()
            self.log_output.append("⏹ Lote cancelado.")
            self._on_batch_all_finished()