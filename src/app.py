"""
Main window for Shuttle Codec.

UI construction, user interaction, and conversion orchestration.
Threading lives in `workers.py`, styling in `theme.py`, shared
helpers in `utils.py`, and the FFmpeg logic in `ffmpeg_handler.py`.
"""

import contextlib
import os
import subprocess
from typing import Any, cast

from PyQt5.QtCore import QT_VERSION_STR, QSettings, Qt, QTime, QTimer, QUrl
from PyQt5.QtGui import (
    QCloseEvent,
    QColor,
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
    QIcon,
    QKeySequence,
    QPalette,
)
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QShortcut,
    QSlider,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .diagnostics import build_diagnostics, build_issue_url
from .ffmpeg_handler import FFmpegHandler
from .i18n import get_available_languages, get_language, set_language, tr
from .presets import RESOLUTION_MAP, get_preset, get_preset_ids
from .theme import (
    ACCENT,
    BASE,
    BLUE,
    CRUST,
    DANGER,
    MAUVE,
    OVERLAY0,
    PANEL_BG,
    PEACH,
    SECONDARY_TEXT,
    SUCCESS,
    SURFACE0,
    SURFACE1,
    TEXT,
    WARNING,
    build_stylesheet,
)
from .utils import (
    filter_existing_files,
    get_icon_path,
    is_image_file,
    open_folder,
    qtime_to_seconds,
    shutdown_command,
)
from .workers import BatchConversionManager, BatchItem, ConversionThread

VERSION = __version__


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ffmpeg = FFmpegHandler()
        self.current_thread: ConversionThread | None = None
        self.batch_manager = BatchConversionManager(parent=self)
        self.batch_items: list[tuple[str, str | None]] = []
        self.input_file: str | None = None
        self.output_file: str | None = None
        self.media_info: dict[str, Any] | None = None
        self.settings = QSettings("ShuttleCodec", "ShuttleCodec")
        self.simple_mode = True
        self._preset_settings: dict[str, Any] = {}
        self._batch_signals_connected: bool = False
        # True when the loaded file has no video stream (audio-only)
        self._audio_mode: bool = False
        # True when the loaded file is a still image (image conversion mode)
        self._image_mode: bool = False
        # ffprobe summary of the loaded file, reused for the size estimate
        self._current_summary: dict[str, Any] | None = None
        # Runtime status tracked so language switches can re-render correctly
        self._ffmpeg_ok: bool = True
        self._hw_info: str = ""

        self.init_ui()
        self._load_settings()
        QTimer.singleShot(200, self._check_ffmpeg)

    # ─── UI INIT ────────────────────────────────────────────────────────────────
    def _apply_dark_palette(self) -> None:
        """
        Give Qt's palette-driven widgets the dark theme.

        The stylesheet only covers the widgets it names; anything Qt paints
        from the palette (message boxes, non-native file dialogs, menus,
        tooltips) would otherwise keep the system's *light* background while
        inheriting our light text color, producing unreadable dialogs.
        """
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            return
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(BASE))
        pal.setColor(QPalette.WindowText, QColor(TEXT))
        pal.setColor(QPalette.Base, QColor(CRUST))
        pal.setColor(QPalette.AlternateBase, QColor(SURFACE0))
        pal.setColor(QPalette.Text, QColor(TEXT))
        pal.setColor(QPalette.Button, QColor(SURFACE1))
        pal.setColor(QPalette.ButtonText, QColor(TEXT))
        pal.setColor(QPalette.ToolTipBase, QColor(SURFACE0))
        pal.setColor(QPalette.ToolTipText, QColor(TEXT))
        pal.setColor(QPalette.Highlight, QColor(ACCENT))
        pal.setColor(QPalette.HighlightedText, QColor(BASE))
        for role in (QPalette.Text, QPalette.ButtonText, QPalette.WindowText):
            pal.setColor(QPalette.Disabled, role, QColor(OVERLAY0))
        app.setPalette(pal)

    def init_ui(self) -> None:
        self.setWindowTitle(tr("app_name"))
        self.setMinimumSize(900, 600)
        self.setAcceptDrops(True)
        self.setWindowIcon(QIcon(get_icon_path()))

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        self._apply_dark_palette()
        self.setStyleSheet(build_stylesheet())
        self._create_header(main_layout)

        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        self._create_file_section(top_layout)
        main_layout.addWidget(top_widget)

        self._create_info_panel(main_layout)
        self._create_mode_toggle(main_layout)
        self._create_preset_section(main_layout)
        self._create_image_section(main_layout)

        self.content_splitter = QSplitter(Qt.Horizontal)  # type: ignore[attr-defined]

        left_widget = QWidget()
        left_widget.setAutoFillBackground(True)
        pal = left_widget.palette()
        pal.setColor(left_widget.backgroundRole(), QColor(PANEL_BG))
        left_widget.setPalette(pal)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._create_video_section(left_layout)
        self._create_audio_section(left_layout)
        self._create_trim_section(left_layout)
        left_scroll = QScrollArea()
        left_scroll.setWidget(left_widget)
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        viewport = left_scroll.viewport()
        if viewport is not None:
            viewport.setAutoFillBackground(True)
            pal2 = viewport.palette()
            pal2.setColor(viewport.backgroundRole(), QColor(PANEL_BG))
            viewport.setPalette(pal2)
        self.content_splitter.addWidget(left_scroll)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self._create_batch_section(right_layout)
        self.content_splitter.addWidget(right_widget)

        self.content_splitter.setSizes([650, 350])
        main_layout.addWidget(self.content_splitter, 1)

        self._create_progress_section(main_layout)
        self._create_log_section(main_layout)
        self._create_status_bar()
        self._setup_shortcuts()

        self.preset_section.setVisible(self.simple_mode)
        self.content_splitter.setVisible(not self.simple_mode)
        self._update_mode_visibility()
        self._apply_accessibility()

    def _create_header(self, layout: QVBoxLayout) -> None:
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 0, 4, 0)

        self.header_title = QLabel(tr("app_name"))
        self.header_title.setStyleSheet(f"color: {MAUVE}; font-size: 20px; font-weight: bold;")

        self.subtitle = QLabel(tr("app_subtitle"))
        self.subtitle.setStyleSheet(f"color: {SECONDARY_TEXT}; font-size: 11px;")
        self.subtitle.setTextFormat(Qt.RichText)  # type: ignore[attr-defined]
        self.subtitle.setOpenExternalLinks(True)

        self.ffmpeg_status = QLabel(tr("ffmpeg_ok"))
        self.ffmpeg_status.setStyleSheet(f"color: {SUCCESS}; font-weight: bold; font-size: 13px;")

        self.hw_status = QLabel("")
        self.hw_status.setStyleSheet(f"color: {WARNING}; font-size: 12px;")

        self.mode_label = QLabel(tr("mode_simple"))
        self.mode_label.setStyleSheet(f"color: {PEACH}; font-size: 12px;")
        self.mode_label.setToolTip(tr("tip_expert_mode"))

        self.lang_combo = QComboBox()
        for code, name in get_available_languages().items():
            self.lang_combo.addItem(name, code)
        idx = self.lang_combo.findData(get_language())
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.setToolTip(tr("tip_language"))
        self.lang_combo.currentIndexChanged.connect(self._on_language_change)
        self.lang_combo.setFixedWidth(100)

        header_layout.addWidget(self.header_title)
        header_layout.addSpacing(8)
        self.report_btn = QPushButton(tr("btn_report"))
        self.report_btn.setToolTip(tr("tip_report"))
        self.report_btn.clicked.connect(self.report_problem)

        header_layout.addWidget(self.subtitle)
        header_layout.addStretch()
        header_layout.addWidget(self.report_btn)
        header_layout.addSpacing(8)
        header_layout.addWidget(self.lang_combo)
        header_layout.addSpacing(8)
        header_layout.addWidget(self.hw_status)
        header_layout.addSpacing(8)
        header_layout.addWidget(self.mode_label)
        header_layout.addSpacing(8)
        header_layout.addWidget(self.ffmpeg_status)

        layout.addWidget(header)

    def _on_language_change(self, index: int) -> None:
        lang = self.lang_combo.itemData(index)
        if lang and isinstance(lang, str):
            set_language(lang)
            self._save_settings()
            self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("app_name"))
        self.header_title.setText(tr("app_name"))
        self.subtitle.setText(tr("app_subtitle"))
        self._update_ffmpeg_status()
        self.mode_label.setText(tr("mode_simple") if self.simple_mode else tr("mode_expert"))
        self.mode_label.setToolTip(tr("tip_expert_mode"))
        self.file_path.setPlaceholderText(tr("file_placeholder"))
        self.browse_btn.setText(tr("btn_browse"))
        self.browse_btn.setToolTip(tr("tip_browse"))
        self.clear_btn.setText(tr("btn_clear"))
        self.clear_btn.setToolTip(tr("tip_cancel_sel"))

        self.video_group.setTitle(tr("group_video"))
        self.audio_group.setTitle(tr("group_audio"))
        self.video_format_label.setText(tr("label_format"))
        self.video_preset_label.setText(tr("label_preset"))
        self.video_quality_label.setText(tr("label_quality"))
        self.video_resolution_label.setText(tr("label_resolution"))
        self.video_fps_label.setText(tr("label_fps"))
        self.audio_format_label.setText(tr("label_format"))
        self.audio_bitrate_label.setText(tr("label_bitrate"))

        self.image_group.setTitle(tr("group_image"))
        self.frame_check.setText(tr("chk_frame_export"))
        self.frame_check.setToolTip(tr("tip_frame_export"))
        self.frame_time_label.setText(tr("label_frame_time"))
        self.image_format_label.setText(tr("label_format"))
        self.image_quality_label.setText(tr("label_quality"))
        self.image_quality.setToolTip(tr("tip_image_quality"))
        self.image_resolution_label.setText(tr("label_resolution"))
        self.trim_start_label.setText(tr("label_trim_start"))
        self.trim_end_label.setText(tr("label_trim_end"))
        self.trim_duration_label.setText(tr("label_trim_duration"))
        self.trim_max_label.setText(tr("trim_max_duration"))
        self.video_keep_audio.setText(tr("chk_keep_audio"))
        self.video_keep_audio.setToolTip(tr("tip_keep_audio"))
        self._update_hw_label()
        self.hw_check.setToolTip(tr("tip_hw_accel"))
        self.trim_group.setTitle(tr("group_trim"))
        self.trim_enable.setText(tr("chk_trim_enable"))

        self.batch_group.setTitle(tr("group_batch"))
        self.add_batch_btn.setText(tr("btn_add_batch"))
        self.remove_batch_btn.setText(tr("btn_remove_batch"))
        self.clear_batch_btn.setText(tr("btn_clear_batch"))
        self.shutdown_check.setText(tr("chk_shutdown"))
        self.shutdown_check.setToolTip(tr("tip_shutdown"))
        self.extract_audio_check.setText(tr("chk_extract_audio"))
        self.extract_audio_check.setToolTip(tr("tip_extract_audio"))
        self.report_btn.setText(tr("btn_report"))
        self.report_btn.setToolTip(tr("tip_report"))
        self.target_check.setText(tr("chk_target_size"))
        self.target_size.setSuffix(f" {tr('label_target_size')}")

        self.progress_group.setTitle(tr("group_progress"))
        self.convert_btn.setToolTip(tr("tip_convert"))
        self._update_batch_ui()
        self.cancel_btn.setText(tr("btn_cancel"))
        self.cancel_btn.setToolTip(tr("tip_cancel"))
        self.log_group.setTitle(tr("group_log"))
        self.status_bar.showMessage(tr("status_ready"))
        self.expert_btn.setText(
            tr("btn_expert_hide") if not self.simple_mode else tr("btn_expert_show")
        )

        # Resolution / FPS combos (labels translatable, data stable)
        res_dict = dict(self._resolution_data)
        for combo in (self.video_resolution, self.image_resolution):
            for i in range(combo.count()):
                data = combo.itemData(i)
                if data and str(data) in res_dict:
                    combo.setItemText(i, res_dict[str(data)])
        fps_dict = dict(self._fps_data)
        for i in range(self.video_fps.count()):
            data = self.video_fps.itemData(i)
            if data and str(data) in fps_dict:
                self.video_fps.setItemText(i, fps_dict[str(data)])

        # Rebuild preset combo labels
        current_preset_id = self.preset_combo.currentData()
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        for pid in get_preset_ids():
            preset = get_preset(pid)
            if preset:
                self.preset_combo.addItem(tr(preset["label_key"]), pid)
        if current_preset_id:
            idx = self.preset_combo.findData(current_preset_id)
            if idx >= 0:
                self.preset_combo.setCurrentIndex(idx)
        self.preset_combo.blockSignals(False)

        self.preset_title.setText(tr("preset_quick_title"))
        if self._preset_settings:
            desc_key = self._preset_settings.get("desc_key", "")
            self.preset_desc.setText(tr(desc_key) if desc_key else "")

        self._update_estimate()
        self._update_mode_visibility()
        self.lang_combo.setToolTip(tr("tip_language"))
        self._apply_accessibility()

    def _create_file_section(self, layout: QHBoxLayout) -> None:
        file_frame = QFrame()
        file_frame.setObjectName("infoPanel")
        file_layout = QHBoxLayout(file_frame)
        file_layout.setContentsMargins(8, 4, 8, 4)

        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText(tr("file_placeholder"))
        self.file_path.setReadOnly(True)
        file_layout.addWidget(self.file_path, 1)

        self.browse_btn = QPushButton(tr("btn_browse"))
        self.browse_btn.setToolTip(tr("tip_browse"))
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)

        self.clear_btn = QPushButton(tr("btn_clear"))
        self.clear_btn.setToolTip(tr("tip_cancel_sel"))
        self.clear_btn.clicked.connect(self.clear_file)
        self.clear_btn.setFixedWidth(36)
        file_layout.addWidget(self.clear_btn)

        layout.addWidget(file_frame)

    def _create_info_panel(self, layout: QVBoxLayout) -> None:
        self.info_frame = QFrame()
        self.info_frame.setObjectName("infoPanel")
        self.info_frame.setVisible(False)
        info_layout = QHBoxLayout(self.info_frame)
        info_layout.setContentsMargins(8, 4, 8, 4)

        self.info_name = QLabel("")
        self.info_name.setStyleSheet(f"color: {TEXT}; font-size: 12px; font-weight: bold;")
        info_layout.addWidget(self.info_name)
        info_layout.addSpacing(16)

        self.info_size = QLabel("")
        self.info_size.setStyleSheet(f"color: {SECONDARY_TEXT}; font-size: 12px;")
        info_layout.addWidget(self.info_size)
        info_layout.addSpacing(16)

        self.info_video = QLabel("")
        self.info_video.setStyleSheet(f"color: {BLUE}; font-size: 12px;")
        info_layout.addWidget(self.info_video)
        info_layout.addSpacing(16)

        self.info_audio = QLabel("")
        self.info_audio.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
        info_layout.addWidget(self.info_audio)
        info_layout.addSpacing(16)

        self.info_duration = QLabel("")
        self.info_duration.setStyleSheet(f"color: {WARNING}; font-size: 12px;")
        info_layout.addWidget(self.info_duration)
        info_layout.addSpacing(16)

        # Output-size hint: refreshed whenever a setting that affects it changes.
        self.info_estimate = QLabel("")
        self.info_estimate.setStyleSheet(f"color: {MAUVE}; font-size: 12px;")
        info_layout.addWidget(self.info_estimate)
        info_layout.addStretch()

        layout.addWidget(self.info_frame)

    def _create_mode_toggle(self, layout: QVBoxLayout) -> None:
        toggle_layout = QHBoxLayout()
        toggle_layout.setContentsMargins(0, 0, 0, 0)

        self.expert_btn = QPushButton(tr("btn_expert_show"))
        self.expert_btn.setObjectName("btnExpert")
        self.expert_btn.setCheckable(True)
        self.expert_btn.clicked.connect(self._toggle_mode)
        toggle_layout.addWidget(self.expert_btn)
        toggle_layout.addStretch()

        layout.addLayout(toggle_layout)

    def _create_video_section(self, layout: QVBoxLayout) -> None:
        self.video_group = QGroupBox(tr("group_video"))
        video_layout = QVBoxLayout(self.video_group)

        row1 = QHBoxLayout()
        self.video_format_label = QLabel(tr("label_format"))
        row1.addWidget(self.video_format_label)
        self.video_format = QComboBox()
        self.video_format.setToolTip(tr("tip_format"))
        self.video_format.addItems(self.ffmpeg.get_supported_video_formats())
        self.video_format.currentIndexChanged.connect(self._on_video_format_change)
        row1.addWidget(self.video_format)
        row1.addStretch()
        video_layout.addLayout(row1)

        self.advanced_video = QWidget()
        adv = QVBoxLayout(self.advanced_video)
        adv.setContentsMargins(0, 0, 0, 0)

        row2 = QHBoxLayout()
        self.video_preset_label = QLabel(tr("label_preset"))
        row2.addWidget(self.video_preset_label)
        self.video_preset = QComboBox()
        self.video_preset.setToolTip(tr("tip_preset"))
        self.video_preset.addItems(self.ffmpeg.VIDEO_FORMATS["MP4 (H.264)"]["presets"])
        self.video_preset.setCurrentText("medium")
        row2.addWidget(self.video_preset)
        row2.addStretch()
        adv.addLayout(row2)

        row3 = QHBoxLayout()
        self.video_quality_label = QLabel(tr("label_quality"))
        row3.addWidget(self.video_quality_label)
        self.video_crf = QSlider(Qt.Horizontal)  # type: ignore[attr-defined]
        self.video_crf.setToolTip(tr("tip_crf"))
        self.video_crf.setRange(0, 51)
        self.video_crf.setValue(23)
        row3.addWidget(self.video_crf, 1)
        self.video_crf_label = QLabel("23")
        self.video_crf_label.setStyleSheet("min-width: 30px;")
        self.video_crf.valueChanged.connect(lambda v: self.video_crf_label.setText(str(v)))
        row3.addWidget(self.video_crf_label)

        self.crf_info = QLabel(tr("crf_high"))
        self.crf_info.setStyleSheet(f"color: {SECONDARY_TEXT}; font-size: 11px;")
        self.video_crf.valueChanged.connect(self._update_crf_info)
        row3.addWidget(self.crf_info)
        row3.addStretch()
        adv.addLayout(row3)

        row4 = QHBoxLayout()
        self.video_resolution_label = QLabel(tr("label_resolution"))
        row4.addWidget(self.video_resolution_label)
        self.video_resolution = QComboBox()
        self.video_resolution.setToolTip(tr("tip_resolution"))
        self._resolution_data = list(RESOLUTION_MAP.items())
        for data_val, display in self._resolution_data:
            self.video_resolution.addItem(display, data_val)
        row4.addWidget(self.video_resolution)
        row4.addStretch()
        adv.addLayout(row4)

        row5 = QHBoxLayout()
        self.video_fps_label = QLabel(tr("label_fps"))
        row5.addWidget(self.video_fps_label)
        self.video_fps = QComboBox()
        self.video_fps.setToolTip(tr("tip_fps"))
        self._fps_data = [
            ("Original", tr("resolution_original")),
            ("60", "60"), ("30", "30"), ("24", "24"), ("15", "15"),
        ]
        for data_val, display in self._fps_data:
            self.video_fps.addItem(display, data_val)
        row5.addWidget(self.video_fps)
        row5.addStretch()
        adv.addLayout(row5)

        row6 = QHBoxLayout()
        self.video_keep_audio = QCheckBox(tr("chk_keep_audio"))
        self.video_keep_audio.setToolTip(tr("tip_keep_audio"))
        self.video_keep_audio.setChecked(True)
        row6.addWidget(self.video_keep_audio)
        row6.addStretch()
        adv.addLayout(row6)

        row7 = QHBoxLayout()
        self.hw_check = QCheckBox(tr("chk_hw_accel"))
        self.hw_check.setToolTip(tr("tip_hw_accel"))
        self.hw_check.setVisible(False)
        row7.addWidget(self.hw_check)
        row7.addStretch()
        adv.addLayout(row7)

        row9 = QHBoxLayout()
        self.extract_audio_check = QCheckBox(tr("chk_extract_audio"))
        self.extract_audio_check.setToolTip(tr("tip_extract_audio"))
        self.extract_audio_check.toggled.connect(self._update_mode_visibility)
        row9.addWidget(self.extract_audio_check)
        row9.addStretch()
        adv.addLayout(row9)

        row8 = QHBoxLayout()
        self.target_check = QCheckBox(tr("chk_target_size"))
        self.target_check.setToolTip(tr("tip_target_size"))
        self.target_check.toggled.connect(self._on_target_size_toggle)
        row8.addWidget(self.target_check)
        self.target_size = QSpinBox()
        self.target_size.setRange(1, 20000)
        self.target_size.setValue(25)
        self.target_size.setSuffix(f" {tr('label_target_size')}")
        self.target_size.valueChanged.connect(self._update_estimate)
        row8.addWidget(self.target_size)
        row8.addStretch()
        adv.addLayout(row8)

        # Any of these changes the estimated output size.
        self.video_format.currentIndexChanged.connect(self._update_estimate)
        self.video_crf.valueChanged.connect(self._update_estimate)
        self.video_resolution.currentIndexChanged.connect(self._update_estimate)
        self.video_fps.currentIndexChanged.connect(self._update_estimate)
        self.video_keep_audio.toggled.connect(self._update_estimate)

        self.advanced_video.setVisible(False)
        video_layout.addWidget(self.advanced_video)
        video_layout.addStretch()
        layout.addWidget(self.video_group)

    def _create_image_section(self, layout: QVBoxLayout) -> None:
        """
        Image output.

        Used in two situations: a still image was loaded (convert it), or the
        user asked for a single frame of a video ("export frame").
        """
        self.image_group = QGroupBox(tr("group_image"))
        image_layout = QVBoxLayout(self.image_group)

        row0 = QHBoxLayout()
        self.frame_check = QCheckBox(tr("chk_frame_export"))
        self.frame_check.setToolTip(tr("tip_frame_export"))
        self.frame_check.toggled.connect(self._update_mode_visibility)
        row0.addWidget(self.frame_check)

        self.frame_time_label = QLabel(tr("label_frame_time"))
        row0.addWidget(self.frame_time_label)
        self.frame_time = QTimeEdit(QTime(0, 0, 0))
        self.frame_time.setDisplayFormat("HH:mm:ss")
        self.frame_time.timeChanged.connect(self._update_estimate)
        row0.addWidget(self.frame_time)
        row0.addStretch()
        image_layout.addLayout(row0)

        row1 = QHBoxLayout()
        self.image_format_label = QLabel(tr("label_format"))
        row1.addWidget(self.image_format_label)
        self.image_format = QComboBox()
        self.image_format.setToolTip(tr("tip_format"))
        self.image_format.addItems(self.ffmpeg.get_supported_image_formats())
        self.image_format.currentIndexChanged.connect(self._on_image_format_change)
        row1.addWidget(self.image_format)
        row1.addStretch()
        image_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.image_quality_label = QLabel(tr("label_quality"))
        row2.addWidget(self.image_quality_label)
        self.image_quality = QSlider(Qt.Horizontal)  # type: ignore[attr-defined]
        self.image_quality.setToolTip(tr("tip_image_quality"))
        self.image_quality.setRange(1, 100)
        self.image_quality.setValue(92)
        row2.addWidget(self.image_quality, 1)
        self.image_quality_value = QLabel("92")
        self.image_quality_value.setStyleSheet("min-width: 30px;")
        self.image_quality.valueChanged.connect(lambda v: self.image_quality_value.setText(str(v)))
        row2.addWidget(self.image_quality_value)
        row2.addStretch()
        image_layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.image_resolution_label = QLabel(tr("label_resolution"))
        row3.addWidget(self.image_resolution_label)
        self.image_resolution = QComboBox()
        self.image_resolution.setToolTip(tr("tip_resolution"))
        for data_val, display in RESOLUTION_MAP.items():
            self.image_resolution.addItem(display, data_val)
        self.image_resolution.currentIndexChanged.connect(self._update_estimate)
        row3.addWidget(self.image_resolution)
        row3.addStretch()
        image_layout.addLayout(row3)

        self._on_image_format_change(0)
        layout.addWidget(self.image_group)

    def _on_image_format_change(self, index: int) -> None:
        """Only JPG/WebP have a meaningful quality knob."""
        fmt = self.ffmpeg.IMAGE_FORMATS.get(self.image_format.currentText())
        adjustable = fmt is not None and fmt.get("quality") in ("mjpeg", "webp")
        self.image_quality.setEnabled(adjustable)
        self.image_quality_value.setEnabled(adjustable)
        self._update_estimate()

    def _on_target_size_toggle(self, checked: bool) -> None:
        """A target size replaces the CRF knob, so disable it to be explicit."""
        self.video_crf.setEnabled(not checked)
        self.crf_info.setEnabled(not checked)
        self._update_estimate()

    def _create_audio_section(self, layout: QVBoxLayout) -> None:
        """Audio-only conversion (MP3, FLAC, ...) from any media file."""
        self.audio_group = QGroupBox(tr("group_audio"))
        audio_layout = QVBoxLayout(self.audio_group)

        row1 = QHBoxLayout()
        self.audio_format_label = QLabel(tr("label_format"))
        row1.addWidget(self.audio_format_label)
        self.audio_format = QComboBox()
        self.audio_format.setToolTip(tr("tip_format"))
        self.audio_format.addItems(self.ffmpeg.get_supported_audio_formats())
        self.audio_format.currentIndexChanged.connect(self._update_estimate)
        row1.addWidget(self.audio_format)
        row1.addStretch()
        audio_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.audio_bitrate_label = QLabel(tr("label_bitrate"))
        row2.addWidget(self.audio_bitrate_label)
        self.audio_bitrate = QComboBox()
        self.audio_bitrate.addItems(["192k", "128k", "256k", "320k", "auto"])
        self.audio_bitrate.currentIndexChanged.connect(self._update_estimate)
        row2.addWidget(self.audio_bitrate)
        row2.addStretch()
        audio_layout.addLayout(row2)

        layout.addWidget(self.audio_group)

    def _update_crf_info(self, val: int) -> None:
        if val <= 18:
            self.crf_info.setText(tr("crf_best"))
            self.crf_info.setStyleSheet(f"color: {SUCCESS}; font-size: 11px;")
        elif val <= 23:
            self.crf_info.setText(tr("crf_high"))
            self.crf_info.setStyleSheet(f"color: {SUCCESS}; font-size: 11px;")
        elif val <= 28:
            self.crf_info.setText(tr("crf_balanced"))
            self.crf_info.setStyleSheet(f"color: {WARNING}; font-size: 11px;")
        elif val <= 35:
            self.crf_info.setText(tr("crf_compressed"))
            self.crf_info.setStyleSheet(f"color: {PEACH}; font-size: 11px;")
        else:
            self.crf_info.setText(tr("crf_overcompressed"))
            self.crf_info.setStyleSheet(f"color: {DANGER}; font-size: 11px;")

    def _on_video_format_change(self, index: int) -> None:
        fmt_name = self.video_format.currentText()
        fmt = self.ffmpeg.VIDEO_FORMATS.get(fmt_name)
        if not fmt:
            return
        is_gif = fmt.get("gif_mode", False)
        self.video_preset.clear()
        if fmt["presets"]:
            self.video_preset.addItems(fmt["presets"])
            self.video_preset.setCurrentText("medium")
        self.video_preset.setVisible(not is_gif)
        self.video_preset_label.setVisible(not is_gif)
        if is_gif:
            # CRF is meaningless for GIF; the slider controls palette colors instead.
            self.video_crf.setRange(2, 256)
            self.video_crf.setValue(256)
            self.video_crf_label.setText("256")
            self.crf_info.setText(tr("label_colors"))
            self.crf_info.setStyleSheet(f"color: {SECONDARY_TEXT}; font-size: 11px;")
        else:
            self.video_crf.setRange(fmt["quality_range"][0], fmt["quality_range"][1])
            self.video_crf.setValue(fmt["default_crf"])
            self.video_crf_label.setText(str(fmt["default_crf"]))
            self._update_crf_info(fmt["default_crf"])
        self.video_keep_audio.setVisible(not is_gif)
        self.hw_check.setVisible(False)

    def _create_trim_section(self, layout: QVBoxLayout) -> None:
        self.trim_group = QGroupBox(tr("group_trim"))
        trim_layout = QHBoxLayout(self.trim_group)

        self.trim_start_label = QLabel(tr("label_trim_start"))
        trim_layout.addWidget(self.trim_start_label)
        self.trim_start = QTimeEdit(QTime(0, 0, 0))
        self.trim_start.setDisplayFormat("HH:mm:ss")
        self.trim_start.timeChanged.connect(self._update_trim_duration)
        trim_layout.addWidget(self.trim_start)

        self.trim_end_label = QLabel(tr("label_trim_end"))
        trim_layout.addWidget(self.trim_end_label)
        self.trim_end = QTimeEdit(QTime(0, 0, 0))
        self.trim_end.setDisplayFormat("HH:mm:ss")
        self.trim_end.timeChanged.connect(self._update_trim_duration)
        trim_layout.addWidget(self.trim_end)

        self.trim_duration_label = QLabel(tr("label_trim_duration"))
        trim_layout.addWidget(self.trim_duration_label)
        self.trim_duration = QLabel("00:00:00")
        self.trim_duration.setStyleSheet(f"color: {SUCCESS}; font-weight: bold; font-size: 13px;")
        trim_layout.addWidget(self.trim_duration)

        self.trim_enable = QCheckBox(tr("chk_trim_enable"))
        trim_layout.addWidget(self.trim_enable)

        self.trim_max_label = QLabel(tr("trim_max_duration"))
        self.trim_max_label.setStyleSheet(f"color: {OVERLAY0}; font-size: 10px;")
        trim_layout.addWidget(self.trim_max_label)

        trim_layout.addStretch()
        layout.addWidget(self.trim_group)

    def _update_trim_duration(self) -> None:
        start_s = qtime_to_seconds(self.trim_start.time())
        end_s = qtime_to_seconds(self.trim_end.time())
        if end_s > start_s:
            diff = end_s - start_s
            h, m, s = diff // 3600, (diff % 3600) // 60, diff % 60
            self.trim_duration.setText(f"{h:02d}:{m:02d}:{s:02d}")
            self.trim_duration.setStyleSheet(f"color: {SUCCESS}; font-weight: bold; font-size: 13px;")
            self.trim_duration.setToolTip("")
            self.trim_duration.setAccessibleDescription(tr("label_trim_duration"))
        else:
            # Colour alone cannot convey this (colour blindness, screen reader),
            # so the invalid range is stated in words as well.
            self.trim_duration.setText("00:00:00")
            self.trim_duration.setStyleSheet(f"color: {DANGER}; font-weight: bold; font-size: 13px;")
            self.trim_duration.setToolTip(tr("trim_invalid"))
            self.trim_duration.setAccessibleDescription(tr("trim_invalid"))

    def _create_batch_section(self, layout: QVBoxLayout) -> None:
        self.batch_group = QGroupBox(tr("group_batch"))
        batch_layout = QVBoxLayout(self.batch_group)

        self.batch_list = QListWidget()
        self.batch_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.batch_list.setAlternatingRowColors(False)
        batch_layout.addWidget(self.batch_list, 1)

        btn_row = QHBoxLayout()
        self.add_batch_btn = QPushButton(tr("btn_add_batch"))
        self.add_batch_btn.clicked.connect(self._add_to_batch)
        btn_row.addWidget(self.add_batch_btn)

        self.remove_batch_btn = QPushButton(tr("btn_remove_batch"))
        self.remove_batch_btn.clicked.connect(self._remove_from_batch)
        btn_row.addWidget(self.remove_batch_btn)

        self.clear_batch_btn = QPushButton(tr("btn_clear_batch"))
        self.clear_batch_btn.clicked.connect(self._clear_batch)
        btn_row.addWidget(self.clear_batch_btn)

        batch_layout.addLayout(btn_row)

        self.batch_progress = QProgressBar()
        self.batch_progress.setVisible(False)
        self.batch_progress.setTextVisible(True)
        self.batch_progress.setFormat("%v / %m")
        batch_layout.addWidget(self.batch_progress)

        # Off by default: only an explicit opt-in may power the machine off.
        self.shutdown_check = QCheckBox(tr("chk_shutdown"))
        self.shutdown_check.setToolTip(tr("tip_shutdown"))
        batch_layout.addWidget(self.shutdown_check)

        layout.addWidget(self.batch_group)

    def _create_progress_section(self, layout: QVBoxLayout) -> None:
        self.progress_group = QGroupBox(tr("group_progress"))
        progress_layout = QVBoxLayout(self.progress_group)

        eta_row = QHBoxLayout()
        self.eta_label = QLabel("")
        self.eta_label.setStyleSheet(f"color: {WARNING}; font-size: 12px;")
        eta_row.addWidget(self.eta_label)
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet(f"color: {SECONDARY_TEXT}; font-size: 12px;")
        eta_row.addWidget(self.speed_label)
        eta_row.addStretch()
        progress_layout.addLayout(eta_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        self.convert_btn = QPushButton(tr("btn_convert"))
        self.convert_btn.setObjectName("btnConvert")
        self.convert_btn.setToolTip(tr("tip_convert"))
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setMinimumHeight(48)
        # Enabled once a file is loaded or the batch queue has items.
        self.convert_btn.setEnabled(False)
        btn_layout.addWidget(self.convert_btn)

        self.cancel_btn = QPushButton(tr("btn_cancel"))
        self.cancel_btn.setObjectName("btnCancel")
        self.cancel_btn.setToolTip(tr("tip_cancel"))
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setMinimumHeight(48)
        btn_layout.addWidget(self.cancel_btn)

        progress_layout.addLayout(btn_layout)
        layout.addWidget(self.progress_group)

    def _create_log_section(self, layout: QVBoxLayout) -> None:
        self.log_group = QGroupBox(tr("group_log"))
        log_layout = QVBoxLayout(self.log_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)

        layout.addWidget(self.log_group)

    def _append_log(self, text: str) -> None:
        """
        Append one line to the log panel, prefixed with its timestamp.

        Indented lines are continuations of the previous entry (batch results,
        command arguments) and keep their alignment instead of getting their own
        timestamp. A bug report is much easier to read with times in it.
        """
        stamp = ""
        if text.strip() and text[:1] not in (" ", "\t"):
            stamp = f"[{QTime.currentTime().toString('HH:mm:ss')}] "
        self.log_output.append(f"{stamp}{text}")

    def _apply_accessibility(self) -> None:
        """
        Name and describe every interactive control for assistive technology.

        Qt's accessibility bridge (screen readers on Windows, macOS and Linux)
        reads `accessibleName`/`accessibleDescription`; without them a widget is
        announced as an unlabelled "button", "combo box" or "slider", so the app
        stays unusable without sight even though every control has a visible
        label. Re-run on each language switch, since these strings are tr().
        """
        controls: list[tuple[QWidget, str, str | None]] = [
            (self.file_path, "file_placeholder", "tip_browse"),
            (self.browse_btn, "btn_browse", "tip_browse"),
            (self.clear_btn, "tip_cancel_sel", "tip_clear"),
            (self.report_btn, "btn_report", "tip_report"),
            (self.lang_combo, "label_language", "tip_language"),
            (self.expert_btn, "btn_expert_show", "tip_expert_mode"),
            (self.video_format, "label_format", "tip_format"),
            (self.video_preset, "label_preset", "tip_preset"),
            (self.video_crf, "label_quality", "tip_crf"),
            (self.video_resolution, "label_resolution", "tip_resolution"),
            (self.video_fps, "label_fps", "tip_fps"),
            (self.video_keep_audio, "chk_keep_audio", "tip_keep_audio"),
            (self.hw_check, "chk_hw_accel", "tip_hw_accel"),
            (self.extract_audio_check, "chk_extract_audio", "tip_extract_audio"),
            (self.target_check, "chk_target_size", "tip_target_size"),
            (self.target_size, "label_target_size", "tip_target_size"),
            (self.frame_check, "chk_frame_export", "tip_frame_export"),
            (self.frame_time, "label_frame_time", None),
            (self.image_format, "label_format", "tip_format"),
            (self.image_quality, "label_quality", "tip_image_quality"),
            (self.image_resolution, "label_resolution", "tip_resolution"),
            (self.audio_format, "label_format", "tip_format"),
            (self.audio_bitrate, "label_bitrate", None),
            (self.trim_enable, "chk_trim_enable", None),
            (self.trim_start, "label_trim_start", None),
            (self.trim_end, "label_trim_end", None),
            (self.batch_list, "group_batch", None),
            (self.add_batch_btn, "btn_add_batch", None),
            (self.remove_batch_btn, "btn_remove_batch", None),
            (self.clear_batch_btn, "btn_clear_batch", None),
            (self.shutdown_check, "chk_shutdown", "tip_shutdown"),
            (self.progress_bar, "group_progress", None),
            (self.convert_btn, "btn_convert", "tip_convert"),
            (self.cancel_btn, "btn_cancel", "tip_cancel"),
            (self.log_output, "group_log", None),
        ]
        for widget, name_key, description_key in controls:
            widget.setAccessibleName(tr(name_key))
            if description_key:
                widget.setAccessibleDescription(tr(description_key))
        self._update_trim_duration()

    def _quit(self) -> None:
        """Quit shortcut handler (QWidget.close returns bool, which Qt's
        `activated` signal rejects at type-check time)."""
        self.close()

    def _create_status_bar(self) -> None:
        # QMainWindow.statusBar() lazily creates one; the stub types it Optional.
        self.status_bar = cast(QStatusBar, self.statusBar())
        self.status_bar.showMessage(tr("status_ready"))

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.browse_file)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.start_conversion)
        QShortcut(QKeySequence("Delete"), self).activated.connect(self._remove_from_batch)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self._quit)

    def _create_preset_section(self, layout: QVBoxLayout) -> None:
        self.preset_section = QFrame()
        self.preset_section.setObjectName("infoPanel")
        ps_layout = QVBoxLayout(self.preset_section)
        ps_layout.setContentsMargins(8, 4, 8, 4)
        ps_layout.setSpacing(6)

        header_row = QHBoxLayout()
        quick_icon = QLabel("⚡")
        quick_icon.setStyleSheet("font-size: 16px;")
        header_row.addWidget(quick_icon)
        self.preset_title = QLabel(tr("preset_quick_title"))
        self.preset_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {TEXT};")
        header_row.addWidget(self.preset_title)
        header_row.addStretch()
        ps_layout.addLayout(header_row)

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumHeight(36)
        self.preset_combo.setStyleSheet("font-size: 14px; padding: 4px 8px;")
        for pid in get_preset_ids():
            preset = get_preset(pid)
            if preset:
                self.preset_combo.addItem(tr(preset["label_key"]), pid)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_change)
        ps_layout.addWidget(self.preset_combo)

        self.preset_desc = QLabel("")
        self.preset_desc.setStyleSheet(f"color: {SECONDARY_TEXT}; font-size: 12px; padding-left: 4px;")
        self.preset_desc.setWordWrap(True)
        ps_layout.addWidget(self.preset_desc)

        if self.preset_combo.count() > 0:
            self.preset_combo.setCurrentIndex(0)

        layout.addWidget(self.preset_section)

    # ─── SETTINGS PERSISTENCE ──────────────────────────────────────────────────
    def _save_settings(self) -> None:
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/state", self.saveState())
        self.settings.setValue("window/language", get_language())
        self.settings.setValue("window/splitter", self.content_splitter.saveState())
        self.settings.setValue("last_dir", os.path.dirname(self.input_file) if self.input_file else "")
        self.settings.setValue("simple_mode", self.simple_mode)
        self.settings.setValue("video/format", self.video_format.currentText())
        self.settings.setValue("video/crf", self.video_crf.value())
        self.settings.setValue("video/preset", self.video_preset.currentText())
        res_data = self.video_resolution.currentData()
        self.settings.setValue("video/resolution", str(res_data) if res_data else "")
        fps_data = self.video_fps.currentData()
        self.settings.setValue("video/fps", str(fps_data) if fps_data else "")
        self.settings.setValue("video/keep_audio", self.video_keep_audio.isChecked())
        self.settings.setValue("audio/format", self.audio_format.currentText())
        self.settings.setValue("audio/bitrate", self.audio_bitrate.currentText())
        self.settings.setValue("video/target_size", self.target_size.value())
        self.settings.setValue("video/target_enabled", self.target_check.isChecked())
        self.settings.setValue("image/format", self.image_format.currentText())
        self.settings.setValue("image/quality", self.image_quality.value())
        image_res = self.image_resolution.currentData()
        self.settings.setValue("image/resolution", str(image_res) if image_res else "")
        self.settings.setValue("batch/shutdown", self.shutdown_check.isChecked())
        preset_id = self.preset_combo.currentData()
        if preset_id and isinstance(preset_id, str):
            self.settings.setValue("preset/id", preset_id)

    def _load_settings(self) -> None:
        geo = self.settings.value("window/geometry")
        if geo:
            self.restoreGeometry(geo)
        state = self.settings.value("window/state")
        if state:
            self.restoreState(state)

        lang = self.settings.value("window/language")
        if lang and isinstance(lang, str):
            set_language(lang)
            idx = self.lang_combo.findData(lang)
            if idx >= 0:
                self.lang_combo.setCurrentIndex(idx)
            self.retranslate_ui()

        s = self.settings.value("window/splitter")
        if s:
            self.content_splitter.restoreState(s)

        simple = self.settings.value("simple_mode")
        if simple is not None:
            self._set_simple_mode(str(simple).lower() in ("true", "1", "yes"))

        vf = self.settings.value("video/format")
        if vf and isinstance(vf, str) and self.video_format.findText(vf) >= 0:
            self.video_format.setCurrentText(vf)
        crf = self.settings.value("video/crf")
        if crf is not None:
            with contextlib.suppress(TypeError, ValueError):
                self.video_crf.setValue(int(crf))
        pres = self.settings.value("video/preset")
        if pres and isinstance(pres, str) and self.video_preset.findText(pres) >= 0:
            self.video_preset.setCurrentText(pres)
        res = self.settings.value("video/resolution")
        if res and isinstance(res, str):
            idx = self.video_resolution.findData(res)
            if idx >= 0:
                self.video_resolution.setCurrentIndex(idx)
        fps = self.settings.value("video/fps")
        if fps and isinstance(fps, str):
            idx = self.video_fps.findData(fps)
            if idx >= 0:
                self.video_fps.setCurrentIndex(idx)
        keep_audio = self.settings.value("video/keep_audio")
        if keep_audio is not None:
            self.video_keep_audio.setChecked(str(keep_audio).lower() in ("true", "1", "yes"))
        af = self.settings.value("audio/format")
        if af and isinstance(af, str) and self.audio_format.findText(af) >= 0:
            self.audio_format.setCurrentText(af)
        ab = self.settings.value("audio/bitrate")
        if ab and isinstance(ab, str) and self.audio_bitrate.findText(ab) >= 0:
            self.audio_bitrate.setCurrentText(ab)

        preset_id = self.settings.value("preset/id")
        if preset_id and isinstance(preset_id, str) and self.preset_combo.findData(preset_id) >= 0:
            self.preset_combo.setCurrentIndex(self.preset_combo.findData(preset_id))

        target_enabled = self.settings.value("video/target_enabled")
        if target_enabled is not None:
            self.target_check.setChecked(str(target_enabled).lower() in ("true", "1", "yes"))
        target_size = self.settings.value("video/target_size")
        if target_size is not None:
            with contextlib.suppress(TypeError, ValueError):
                self.target_size.setValue(int(target_size))

        image_format = self.settings.value("image/format")
        if image_format and isinstance(image_format, str) and self.image_format.findText(image_format) >= 0:
            self.image_format.setCurrentText(image_format)
        image_quality = self.settings.value("image/quality")
        if image_quality is not None:
            with contextlib.suppress(TypeError, ValueError):
                self.image_quality.setValue(int(image_quality))
        image_res = self.settings.value("image/resolution")
        if image_res and isinstance(image_res, str):
            idx = self.image_resolution.findData(image_res)
            if idx >= 0:
                self.image_resolution.setCurrentIndex(idx)

        shutdown = self.settings.value("batch/shutdown")
        if shutdown is not None:
            self.shutdown_check.setChecked(str(shutdown).lower() in ("true", "1", "yes"))

        self._restore_batch()

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        self._save_settings()
        if (self.current_thread and self.current_thread.isRunning()) or self.batch_manager.is_running():
            reply = QMessageBox.question(
                self, tr("title_exit"),
                tr("error_conversion_in_progress"),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.ffmpeg.cancel_conversion()
                if self.batch_manager.is_running():
                    self.batch_manager.cancel()
                    self.batch_manager.wait()
                if self.current_thread:
                    self.current_thread.wait(5000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def _update_ffmpeg_status(self) -> None:
        """Render the FFmpeg availability label for the current language."""
        if self._ffmpeg_ok:
            self.ffmpeg_status.setText(tr("ffmpeg_ok"))
            self.ffmpeg_status.setStyleSheet(f"color: {SUCCESS}; font-weight: bold; font-size: 13px;")
        else:
            self.ffmpeg_status.setText(tr("ffmpeg_missing"))
            self.ffmpeg_status.setStyleSheet(f"color: {DANGER}; font-weight: bold; font-size: 13px;")

    def _update_hw_label(self) -> None:
        """Render the hardware acceleration checkbox label with its backend."""
        backend = self._hw_info.split()[0] if self._hw_info else ""
        label = tr("chk_hw_accel")
        self.hw_check.setText(f"{label} · {backend}" if backend else label)

    def _check_ffmpeg(self) -> None:
        if self.ffmpeg.check_ffmpeg():
            self._ffmpeg_ok = True
            self._update_ffmpeg_status()
            self.status_bar.showMessage(tr("ffmpeg_ready"))
            self._detect_hardware()
        else:
            self._ffmpeg_ok = False
            self._update_ffmpeg_status()
            QMessageBox.critical(self, tr("title_error"), tr("ffmpeg_not_found"))

    def _detect_hardware(self) -> None:
        self._hw_info = self.ffmpeg.detect_hardware_acceleration()
        if self._hw_info:
            self.hw_status.setText(self._hw_info)
            self.hw_status.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
            if "NVENC" in self._hw_info or "AMF" in self._hw_info or "QSV" in self._hw_info:
                self._update_hw_label()
                self.hw_check.setVisible(True)

    def _toggle_mode(self) -> None:
        self._set_simple_mode(not self.expert_btn.isChecked())

    def _set_simple_mode(self, simple: bool) -> None:
        self.simple_mode = simple
        if simple:
            # These live inside expert-only groups: leaving them set would keep
            # changing the output type with no visible way to undo it.
            self.frame_check.setChecked(False)
            self.extract_audio_check.setChecked(False)
        self.preset_section.setVisible(simple)
        self.content_splitter.setVisible(not simple)
        self.advanced_video.setVisible(not simple)
        if simple:
            self.expert_btn.setText(tr("btn_expert_show"))
            self.mode_label.setText(tr("mode_simple"))
        else:
            self.expert_btn.setText(tr("btn_expert_hide"))
            self.mode_label.setText(tr("mode_expert"))
            if self._preset_settings:
                self._apply_preset_to_controls(self._preset_settings)
        # The batch list (and therefore the convert button) is mode-dependent.
        self._update_batch_ui()

    def _on_preset_change(self, index: int) -> None:
        preset_id = self.preset_combo.itemData(index)
        if preset_id and isinstance(preset_id, str):
            preset = get_preset(preset_id)
            if preset:
                self._preset_settings = dict(preset)
                desc_key = preset.get("desc_key", "")
                self.preset_desc.setText(tr(desc_key) if desc_key else "")

    def _apply_preset_to_controls(self, preset: dict[str, Any]) -> None:
        fmt_idx = self.video_format.findText(preset.get("format", ""))
        if fmt_idx >= 0:
            self.video_format.setCurrentIndex(fmt_idx)

        if preset.get("format") == "GIF":
            self.video_crf.setValue(int(preset.get("max_colors", 256)))
        else:
            self.video_crf.setValue(int(preset.get("crf", 23)))

        enc_preset = preset.get("enc_preset", "")
        if enc_preset:
            p_idx = self.video_preset.findText(enc_preset)
            if p_idx >= 0:
                self.video_preset.setCurrentIndex(p_idx)

        res = preset.get("resolution", "Original")
        for i in range(self.video_resolution.count()):
            if self.video_resolution.itemData(i) == res:
                self.video_resolution.setCurrentIndex(i)
                break

        fps = preset.get("framerate", "Original")
        for i in range(self.video_fps.count()):
            if self.video_fps.itemData(i) == fps:
                self.video_fps.setCurrentIndex(i)
                break

        self.video_keep_audio.setChecked(preset.get("keep_audio", True))

    # ─── FILE HANDLING ──────────────────────────────────────────────────────────
    @staticmethod
    def _is_valid_media_file(file_path: str) -> bool:
        try:
            resolved = os.path.realpath(file_path)
            if not os.path.isfile(resolved):
                return False
            size = os.path.getsize(resolved)
            return 0 < size <= 10 * 1024 * 1024 * 1024
        except (OSError, ValueError):
            return False

    def browse_file(self) -> None:
        last_dir = self.settings.value("last_dir", "")
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("select_media_title"),
            str(last_dir) if last_dir else "",
            tr("media_filter")
        )
        if file_path:
            if self._is_valid_media_file(file_path):
                self.load_file(file_path)
                self.settings.setValue("last_dir", os.path.dirname(file_path))
            else:
                QMessageBox.warning(self, tr("title_warning"), tr("error_invalid_file"))

    def clear_file(self) -> None:
        self.input_file = None
        self.output_file = None
        self.media_info = None
        self._audio_mode = False
        self._image_mode = False
        self._current_summary = None
        self.extract_audio_check.setChecked(False)
        self.file_path.clear()
        self._update_batch_ui()
        self.log_output.clear()
        self.progress_bar.setValue(0)
        self.eta_label.setText("")
        self.speed_label.setText("")
        self.info_frame.setVisible(False)
        self.frame_check.setChecked(False)
        self._update_mode_visibility()
        self.status_bar.showMessage(tr("status_ready"))

    def load_file(self, file_path: str) -> None:
        if not self._is_valid_media_file(file_path):
            QMessageBox.warning(self, tr("title_warning"), tr("error_invalid_file"))
            return

        self.input_file = file_path
        self.file_path.setText(file_path)
        self.media_info = self.ffmpeg.get_media_info(file_path)
        self.convert_btn.setEnabled(True)
        self.log_output.clear()
        self.progress_bar.setValue(0)

        summary = self.ffmpeg.get_file_summary(file_path)
        self._current_summary = summary
        self._image_mode = is_image_file(file_path)
        self._audio_mode = summary is not None and not summary.get("video_codec") and not self._image_mode
        if summary:
            self.info_name.setText(tr("log_file_info", summary['filename']))
            self.info_size.setText(tr("log_file_size", summary['size_mb']))
            vcodec = summary.get('video_codec')
            if vcodec:
                res = f"{summary['width']}x{summary['height']}" if summary.get('width') else ""
                self.info_video.setText(f"🎬 {vcodec.upper()} {res}")
            else:
                self.info_video.setText("🎬 -")
            acodec = summary.get('audio_codec') or "-"
            self.info_audio.setText(f"🎵 {acodec.upper() if acodec != '-' else '-'}")
            bitrate_str = f" · {summary['bitrate']} kbps" if summary.get('bitrate') else ""
            # Still images have no duration; don't claim 00:00:00.
            duration_str = summary['duration_str'] if summary.get('duration') else "—"
            self.info_duration.setText(f"⏱ {duration_str}{bitrate_str}")
            self.info_frame.setVisible(True)

        codecs = self.ffmpeg.get_codecs(file_path)
        width, height = self.ffmpeg.get_resolution(file_path)
        duration: float | None = None
        bitrate: str | None = None
        if self.media_info and "format" in self.media_info:
            dur_str = self.media_info["format"].get("duration")
            if dur_str:
                duration = float(dur_str)
            bitrate = self.media_info["format"].get("bit_rate")

        info_lines: list[str] = [
            tr("log_file_info", os.path.basename(file_path)),
            tr("log_file_size", os.path.getsize(file_path) / 1024 / 1024),
        ]
        if codecs.get("video"):
            info_lines.append(tr("log_file_video", codecs['video']))
            if width and height:
                info_lines.append(tr("log_file_resolution", width, height))
        if codecs.get("audio"):
            info_lines.append(tr("log_file_audio", codecs['audio']))
        if bitrate:
            info_lines.append(tr("log_file_bitrate", int(bitrate) // 1000))
        if duration:
            info_lines.append(tr("log_file_duration", self.ffmpeg.get_duration_string(duration)))
        self._append_log(" | ".join(info_lines))

        self._auto_detect_best(codecs, width, height)
        self._update_mode_visibility()

    def _frame_export_enabled(self) -> bool:
        """True when the user asked for a single frame instead of a video."""
        return bool(
            self.frame_check.isChecked() and not self._image_mode and not self._audio_mode
        )

    def _update_mode_visibility(self) -> None:
        """
        Show only the option groups that apply.

        Video, audio-only and image inputs each get their own group; the video
        and trim groups are hidden when a single frame is being exported.
        """
        if not hasattr(self, "video_group"):
            return
        frame_export = self._frame_export_enabled()
        self.audio_group.setVisible(self._audio_mode or self._extract_audio_enabled())
        # Exporting one frame makes every video/trim control irrelevant.
        self.video_group.setVisible(not self._audio_mode and not self._image_mode and not frame_export)
        self.trim_group.setVisible(not self._audio_mode and not self._image_mode and not frame_export)
        self.image_group.setVisible((self._image_mode or not self.simple_mode) and not self._audio_mode)
        self.frame_check.setVisible(not self._image_mode)
        self.frame_time_label.setVisible(frame_export)
        self.frame_time.setVisible(frame_export)
        self._update_estimate()

    def _extract_audio_enabled(self) -> bool:
        """True when the user wants the audio track of a video, without video."""
        return bool(
            self.extract_audio_check.isChecked() and not self._audio_mode and not self._image_mode
        )

    def _conversion_plan(self, mode: str) -> tuple[float | None, float | None]:
        """Trim parameters for `mode`; exporting a frame reuses the start time."""
        if mode == "image":
            if self._image_mode:
                return None, None
            return float(qtime_to_seconds(self.frame_time.time())), None
        return self._get_trim_params()

    def _update_estimate(self, *_args: object) -> None:
        """Refresh the estimated output size shown in the info panel."""
        if not hasattr(self, "video_format") or not hasattr(self, "info_estimate"):
            return
        try:
            mode, settings = self._get_settings_from_ui()
        except (AttributeError, KeyError, TypeError):
            return

        summary = dict(self._current_summary) if self._current_summary else None
        _, trim_duration = self._conversion_plan(mode)
        if summary and trim_duration:
            duration = float(summary.get("duration") or trim_duration)
            summary["duration"] = min(duration, float(trim_duration))

        estimate = self.ffmpeg.estimate_output_size_mb(summary, settings)
        if estimate and estimate > 0:
            self.info_estimate.setText(tr("estimate_size", f"{estimate:.1f}"))
        else:
            self.info_estimate.setText(tr("estimate_unknown"))

    def _auto_detect_best(self, codecs: dict[str, str | None], width: int | None, height: int | None) -> None:
        if width and height:
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

            idx = self.video_resolution.findData(res)
            if idx >= 0:
                self.video_resolution.setCurrentIndex(idx)

        # Suggest format based on codec
        vcodec = codecs.get("video", "")
        if vcodec and ("265" in vcodec or "hevc" in vcodec.lower()) and self.video_format.findText("MP4 (H.265)") >= 0:
            self.video_format.setCurrentText("MP4 (H.265)")
        elif vcodec and "264" in vcodec and self.video_format.findText("MP4 (H.264)") >= 0:
            self.video_format.setCurrentText("MP4 (H.264)")

    def dragEnterEvent(self, event: QDragEnterEvent | None) -> None:
        if event is None:
            return
        mime = event.mimeData()
        if mime is not None and mime.hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent | None) -> None:
        if event is None:
            return
        mime = event.mimeData()
        if not mime or not mime.hasUrls():
            return
        urls = mime.urls()
        if not urls:
            return
        file_paths = [u.toLocalFile() for u in urls if u and os.path.isfile(u.toLocalFile())]
        valid_paths = [p for p in file_paths if self._is_valid_media_file(p)]
        if not valid_paths:
            return
        if len(valid_paths) == 1:
            self.load_file(valid_paths[0])
        else:
            self.load_file(valid_paths[0])
            for fp in valid_paths:
                self._add_single_to_batch(fp)

    # ─── BATCH ──────────────────────────────────────────────────────────────────
    def _add_to_batch(self) -> None:
        last_dir = self.settings.value("last_dir", "")
        files, _ = QFileDialog.getOpenFileNames(
            self, tr("batch_add_title"),
            str(last_dir) if last_dir else "",
            tr("batch_filter")
        )
        for fp in files:
            if self._is_valid_media_file(fp):
                self._add_single_to_batch(fp)

    def _add_single_to_batch(self, file_path: str) -> None:
        self.batch_items.append((file_path, None))
        item = QListWidgetItem(os.path.basename(file_path))
        item.setToolTip(file_path)
        item.setData(Qt.UserRole, os.path.basename(file_path))  # type: ignore[attr-defined]
        self.batch_list.addItem(item)
        self._update_batch_ui()
        self._save_batch()

    def _remove_from_batch(self) -> None:
        rows = sorted([self.batch_list.row(item) for item in self.batch_list.selectedItems()], reverse=True)
        for row in rows:
            if row < len(self.batch_items):
                self.batch_items.pop(row)
            self.batch_list.takeItem(row)
        self._update_batch_ui()
        self._save_batch()

    def _clear_batch(self) -> None:
        self.batch_items.clear()
        self.batch_list.clear()
        self._update_batch_ui()
        self._save_batch()

    def _save_batch(self) -> None:
        """Persist the queue so it survives a restart (paths only)."""
        self.settings.setValue("batch/items", [path for path, _ in self.batch_items])

    def _restore_batch(self) -> None:
        """Reload the queue from the last session, skipping files that vanished."""
        stored = self.settings.value("batch/items")
        if not stored:
            return
        if isinstance(stored, str):
            stored = [stored]
        paths = filter_existing_files(list(stored))
        for path in paths:
            self._add_single_to_batch(path)
        if paths:
            self._append_log(tr("log_batch_restored", len(paths)))

    def _update_batch_ui(self) -> None:
        """Refresh the convert button for the current queue and mode.

        Deliberately does *not* persist the queue: this runs while settings are
        being restored (before `_restore_batch`), and saving an empty queue
        there would wipe the batch the user left behind. Persistence belongs to
        the queue mutations (`_add_single_to_batch`, `_remove_from_batch`,
        `_clear_batch`).
        """
        if not hasattr(self, "batch_list"):
            return
        count = self.batch_list.count()
        # In simple mode the batch list is hidden, so the queue must not take
        # over the convert button: the user would be told "convert N files"
        # while looking at a window that cannot show, edit or run that batch.
        batching = count > 0 and not self.simple_mode
        if batching:
            self.convert_btn.setText(tr("btn_convert_batch", count))
        else:
            self.convert_btn.setText(tr("btn_convert"))
        # Never re-enable the button while a conversion is already running.
        running = (self.current_thread is not None and self.current_thread.isRunning()) or (
            self.batch_manager.is_running()
        )
        if not running:
            self.convert_btn.setEnabled(self.input_file is not None or batching)

    # ─── CONVERSION ─────────────────────────────────────────────────────────────
    def _get_trim_params(self) -> tuple[float | None, float | None]:
        if not self.trim_enable.isChecked():
            return None, None
        start_s = qtime_to_seconds(self.trim_start.time())
        end_s = qtime_to_seconds(self.trim_end.time())
        if end_s <= start_s:
            return None, None
        return float(start_s), float(end_s - start_s)

    def _collect_video_settings(self, preset: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build the video settings dict from either a preset or the expert controls."""
        if preset is not None:
            fmt_name = preset.get("format", "MP4 (H.264)")
            fmt = self.ffmpeg.VIDEO_FORMATS.get(fmt_name)
            is_gif = fmt.get("gif_mode", False) if fmt else False
            fps_raw = preset.get("framerate", "Original")
            return {
                "format": fmt_name,
                "crf": preset.get("crf", 23),
                "max_colors": preset.get("max_colors", 256),
                "preset": preset.get("enc_preset", ""),
                "resolution": RESOLUTION_MAP.get(str(preset.get("resolution", "Original"))),
                "framerate": None if str(fps_raw) == "Original" else str(fps_raw),
                "keep_audio": preset.get("keep_audio", True) if not is_gif else False,
                "copy_audio": False,
                "audio_codec": "aac",
                "audio_bitrate": "192k",
                "hw_accel": False,
                "extension": fmt["extension"] if fmt else ".mp4",
                # Presets always keep constant quality; no target size.
                "target_size_mb": None,
            }

        fmt_name = self.video_format.currentText()
        fmt = self.ffmpeg.VIDEO_FORMATS.get(fmt_name)
        is_gif = fmt.get("gif_mode", False) if fmt else False
        res_data = self.video_resolution.currentData()
        fps_raw = self.video_fps.currentData()
        crf_value = self.video_crf.value()
        return {
            "format": fmt_name,
            "crf": None if is_gif else crf_value,
            "max_colors": crf_value if is_gif else 256,
            "preset": self.video_preset.currentText() if fmt and fmt["presets"] else "",
            "resolution": RESOLUTION_MAP.get(str(res_data)) if res_data else None,
            "framerate": None if str(fps_raw) == "Original" else str(fps_raw),
            "keep_audio": self.video_keep_audio.isChecked() if not is_gif else False,
            "copy_audio": self.video_keep_audio.isChecked() and not is_gif,
            "audio_codec": "aac",
            "audio_bitrate": "192k",
            # isVisibleTo: the checkbox counts as active even when the window is
            # not shown yet (headless runs, tests).
            "hw_accel": self.hw_check.isChecked() if self.hw_check.isVisibleTo(self) else False,
            "extension": fmt["extension"] if fmt else ".mp4",
            "target_size_mb": self.target_size.value() if self.target_check.isChecked() else None,
        }

    def _collect_image_settings(self) -> dict[str, Any]:
        """Build the image settings dict (still image or exported frame)."""
        fmt_name = self.image_format.currentText()
        fmt = self.ffmpeg.IMAGE_FORMATS.get(fmt_name)
        res_data = self.image_resolution.currentData()
        return {
            "format": fmt_name,
            "quality": self.image_quality.value(),
            "resolution": RESOLUTION_MAP.get(str(res_data)) if res_data else None,
            "extension": fmt["extension"] if fmt else ".png",
            "keep_audio": False,
            "target_size_mb": None,
        }

    def _get_settings_from_ui(self) -> tuple[str, dict[str, Any]]:
        """Return (mode, settings). Audio-only files convert with mode='audio'."""
        if self._audio_mode:
            fmt_name = self.audio_format.currentText()
            return "audio", {
                "format": fmt_name,
                "bitrate": self.audio_bitrate.currentText(),
                "extension": self.ffmpeg.AUDIO_FORMATS.get(fmt_name, {}).get("extension", ".mp3"),
            }
        if self._image_mode or self._frame_export_enabled():
            return "image", self._collect_image_settings()
        if self._extract_audio_enabled():
            fmt_name = self.audio_format.currentText()
            fmt = self.ffmpeg.AUDIO_FORMATS.get(fmt_name, {})
            return "extract_audio", {
                "format": fmt_name,
                "audio_codec": fmt.get("audio_codec", "libmp3lame"),
                "bitrate": self.audio_bitrate.currentText(),
                "extension": fmt.get("extension", ".mp3"),
                "target_size_mb": None,
            }
        if self.simple_mode and self._preset_settings:
            return "video", self._collect_video_settings(self._preset_settings)
        return "video", self._collect_video_settings()

    def _build_output_path(self, input_path: str) -> str:
        mode, settings = self._get_settings_from_ui()
        if mode in ("audio", "extract_audio"):
            ext = settings.get("extension", ".mp3")
        elif mode == "image":
            ext = settings.get("extension", ".png")
        else:
            fmt = self.ffmpeg.VIDEO_FORMATS.get(settings["format"])
            ext = fmt["extension"] if fmt else ".mp4"
        base, _ = os.path.splitext(input_path)
        return f"{base}_shuttle{ext}"

    def _warn_if_target_size_unusable(
        self, mode: str, settings: dict[str, Any], input_file: str, trim_duration: float | None
    ) -> None:
        """
        Log the documented warning when a target size silently falls back to CRF.

        Target size is derived from the duration, so a file whose duration
        ffprobe cannot read would otherwise be converted at constant quality
        without telling the user anything.
        """
        if mode != "video" or not settings.get("target_size_mb"):
            return
        if self.ffmpeg.video_target_bitrate(settings, input_file, trim_duration) <= 0:
            self._append_log(tr("log_target_size_fallback", os.path.basename(input_file)))

    def start_conversion(self) -> None:
        if not self.ffmpeg.check_ffmpeg():
            QMessageBox.critical(self, tr("title_error"), tr("error_ffmpeg_unavailable"))
            return

        if not self.simple_mode and self.batch_items:
            self._start_batch_conversion()
            return

        if not self.input_file:
            QMessageBox.warning(self, tr("title_error"), tr("error_select_file"))
            return

        mode, settings = self._get_settings_from_ui()
        output_file = self._build_output_path(self.input_file)

        output_file, _ = QFileDialog.getSaveFileName(
            self,
            tr("title_image_save") if mode == "image" else tr("save_as_title"),
            output_file,
            tr("image_filter") if mode == "image" else tr("all_files_filter")
        )
        if not output_file:
            return

        self.output_file = output_file
        trim_start, trim_duration = self._conversion_plan(mode)
        self._warn_if_target_size_unusable(mode, settings, self.input_file, trim_duration)
        cmd = self.ffmpeg.build_convert_command(
            self.input_file, output_file, mode, settings,
            trim_start=trim_start, trim_duration=trim_duration
        )
        if not cmd:
            QMessageBox.critical(self, tr("title_error"), tr("error_cmd_failed"))
            return

        description = f"{os.path.basename(self.input_file)} → {os.path.basename(output_file)}"
        self._run_conversion_thread(cmd, description, output_file)

    def _start_batch_conversion(self) -> None:
        mode, settings = self._get_settings_from_ui()
        trim_start, trim_duration = self._conversion_plan(mode)

        items: list[BatchItem] = []
        for inp, _ in self.batch_items:
            output = self._build_output_path(inp)
            cmd = self.ffmpeg.build_convert_command(
                inp, output, mode, settings,
                trim_start=trim_start, trim_duration=trim_duration
            )
            if cmd:
                self._warn_if_target_size_unusable(mode, settings, inp, trim_duration)
                desc = f"{os.path.basename(inp)} → {os.path.basename(output)}"
                items.append(BatchItem(inp, output, cmd, desc, self.ffmpeg.build_software_fallback(cmd)))

        if not items:
            return

        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.batch_progress.setVisible(True)
        self.batch_progress.setMaximum(len(items))
        self.batch_progress.setValue(0)
        self._append_log(tr("msg_batch_started", len(items)))

        # Connect once — signals stay connected for the window's lifetime.
        if not self._batch_signals_connected:
            self.batch_manager.file_finished.connect(self._on_batch_file_finished)
            self.batch_manager.all_finished.connect(self._on_batch_all_finished)
            self._batch_signals_connected = True

        self.batch_manager.start(self.ffmpeg, items)

    def _on_batch_file_finished(self, index: int, success: bool, outpath: str) -> None:
        self.batch_progress.setValue(index + 1)
        status = "✅" if success else "❌"
        self._append_log(
            f"  {status} [{index + 1}/{self.batch_progress.maximum()}] {os.path.basename(outpath)}"
        )
        item = self.batch_list.item(index)
        if item:
            name = item.data(Qt.UserRole) or os.path.basename(outpath)  # type: ignore[attr-defined]
            item.setText(f"{status} {name}")

    def _on_batch_all_finished(self, success_count: int, total: int) -> None:
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.batch_progress.setVisible(False)
        self._append_log(tr("msg_batch_done", success_count, total))
        self.status_bar.showMessage(tr("msg_batch_status", success_count, total))
        if self.batch_manager.cancelled:
            # A cancelled batch also reaches this slot: reporting "completed"
            # and offering to shut the machine down would be misleading.
            self._update_batch_ui()
            return
        QMessageBox.information(
            self, tr("title_batch_completed"),
            tr("msg_batch_completed", total, success_count, total - success_count)
        )
        self._maybe_shutdown()

    def _run_conversion_thread(self, cmd: list[str], description: str, output_path: str) -> None:
        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.eta_label.setText("")
        self.speed_label.setText("")
        self._append_log(f"\n{'─' * 50}")

        # When the job uses a GPU encoder, keep a CPU-only equivalent ready: it
        # is used automatically if the hardware encoder fails at runtime.
        fallback_cmd = self.ffmpeg.build_software_fallback(cmd)

        self.current_thread = ConversionThread(
            self.ffmpeg, cmd, description, output_path, fallback_cmd=fallback_cmd
        )
        self.current_thread.progress.connect(self._on_progress)
        self.current_thread.conversion_done.connect(self._on_conversion_finished)
        self.current_thread.log.connect(self._append_log)
        self.current_thread.eta_update.connect(self._on_eta_update)
        self.current_thread.start()

    def _on_progress(self, pct: int, status: str) -> None:
        self.progress_bar.setValue(pct)
        if status:
            self.status_bar.showMessage(status)

    def _on_eta_update(self, eta: str, speed: str) -> None:
        self.eta_label.setText(tr("eta_label", eta))
        self.speed_label.setText(tr("speed_label", speed))

    def _on_conversion_finished(self, success: bool, description: str, output_path: str) -> None:
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        if success:
            self.status_bar.showMessage(f"✅ {tr('msg_conversion_success')} {description}")
            reply = QMessageBox.information(
                self, tr("title_completed"),
                tr("msg_conversion_completed", output_path),
                QMessageBox.Open | QMessageBox.Ok
            )
            if reply == QMessageBox.Open and not open_folder(os.path.dirname(output_path) or output_path):
                QMessageBox.warning(self, tr("title_warning"), output_path)
        else:
            self.status_bar.showMessage(f"❌ {tr('msg_conversion_failed')}: {description}")

    # ─── SHUTDOWN / DIAGNOSTICS ─────────────────────────────────────────────────
    def _maybe_shutdown(self) -> None:
        """Power the machine off after a finished batch, when the user opted in."""
        if not self.shutdown_check.isChecked() or self.batch_manager.cancelled:
            return
        command = shutdown_command()
        if command is None:
            self._append_log(tr("msg_shutdown_unavailable"))
            return
        self._show_shutdown_dialog(command)

    def _show_shutdown_dialog(self, command: list[str]) -> None:
        """Countdown with 60 seconds to abort; blocks until the user decides."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(tr("title_shutdown"))
        box.setText(tr("msg_shutdown_countdown", 60))
        cancel_button = box.addButton(tr("btn_cancel_shutdown"), QMessageBox.RejectRole)
        box.setStandardButtons(QMessageBox.NoButton)

        remaining = 60
        timer = QTimer(box)

        def tick() -> None:
            nonlocal remaining
            remaining -= 1
            if remaining <= 0:
                timer.stop()
                box.done(0)
                return
            box.setText(tr("msg_shutdown_countdown", remaining))

        timer.timeout.connect(tick)
        timer.start(1000)
        box.exec_()
        timer.stop()

        if box.clickedButton() is cancel_button:
            self._append_log(tr("msg_shutdown_cancelled"))
            return
        try:
            subprocess.Popen(command)  # noqa: S603
        except OSError:
            self._append_log(tr("msg_shutdown_unavailable"))

    def report_problem(self) -> None:
        """Open a GitHub bug report pre-filled with diagnostics and the log tail."""
        diagnostics = build_diagnostics(
            version=VERSION,
            language=get_language(),
            ffmpeg_version=self.ffmpeg.get_ffmpeg_version(),
            qt_version=QT_VERSION_STR,
            log_text=self.log_output.toPlainText(),
        )
        if QDesktopServices.openUrl(QUrl(build_issue_url(diagnostics, title="[Bug] "))):
            self._append_log(tr("msg_report_done"))
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(diagnostics)
        QMessageBox.information(self, tr("title_warning"), tr("msg_report_copied"))

    def cancel_conversion(self) -> None:
        if self.ffmpeg:
            self.ffmpeg.cancel_conversion()
        self._append_log(tr("msg_cancelled"))
        if self.batch_manager.is_running():
            self.batch_manager.cancel()
            self._append_log(tr("msg_batch_cancelled"))
            return
        self._on_conversion_finished(False, tr("msg_cancelled"), "")
