"""Asset preview — image thumbnail + audio player."""
import logging
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QFrame,
)

import gui_qt.theme as theme

log = logging.getLogger(__name__)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".gif", ".ico"}
AUDIO_EXTS = {".ogg", ".wav", ".mp3", ".m4a"}


class AssetPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = None
        self._audio_output = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._preview_label = QLabel("PREVIEW")
        self._preview_label.setObjectName("sectionTitle")
        layout.addWidget(self._preview_label)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setMinimumHeight(120)
        self._image_label.setMaximumHeight(300)
        self._image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._image_label.setStyleSheet(f"background-color: {theme.BG_ELEVATED}; border-radius: 8px;")
        layout.addWidget(self._image_label)

        self._info_label = QLabel("")
        self._info_label.setObjectName("mutedText")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._info_label)

        audio_row = QHBoxLayout()
        audio_row.setSpacing(6)

        self._play_btn = QPushButton("Play")
        self._play_btn.setObjectName("toolBtn")
        self._play_btn.setFixedHeight(28)
        self._play_btn.setEnabled(False)
        self._play_btn.clicked.connect(self._toggle_play)
        audio_row.addWidget(self._play_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setObjectName("toolBtn")
        self._stop_btn.setFixedHeight(28)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop)
        audio_row.addWidget(self._stop_btn)

        audio_row.addStretch()
        layout.addLayout(audio_row)

    def preview_file(self, path: Path):
        self._stop()
        if not path.exists():
            return
        ext = path.suffix.lower()
        if ext in IMAGE_EXTS:
            self._preview_image(path)
        elif ext in AUDIO_EXTS:
            self._preview_audio(path)
        else:
            self._image_label.clear()
            self._image_label.setText(f"Preview not available\n{path.name}")
            self._info_label.setText(f"{ext} — {path.stat().st_size / 1024:.1f} KB")
            self._play_btn.setEnabled(False)
            self._stop_btn.setEnabled(False)

    def _preview_image(self, path: Path):
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._image_label.setText("Failed to load image")
            self._info_label.setText("")
            return
        scaled = pixmap.scaled(
            self._image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_label.setPixmap(scaled)
        size_kb = path.stat().st_size / 1024
        if size_kb >= 1024:
            size_str = f"{size_kb / 1024:.1f} MB"
        else:
            size_str = f"{size_kb:.1f} KB"
        dims = f"{pixmap.width()}x{pixmap.height()}" if pixmap.width() > 0 else "?"
        self._info_label.setText(f"{dims} — {size_str}")
        self._play_btn.setEnabled(False)
        self._stop_btn.setEnabled(False)

    def _preview_audio(self, path: Path):
        self._image_label.clear()
        self._image_label.setText(f"Audio: {path.name}")
        self._info_label.setText(f"{path.stat().st_size / 1024:.1f} KB")
        self._play_btn.setEnabled(True)
        self._stop_btn.setEnabled(True)
        try:
            self._audio_output = QAudioOutput()
            self._player = QMediaPlayer()
            self._player.setAudioOutput(self._audio_output)
            self._player.setSource(QUrl.fromLocalFile(str(path)))
        except Exception as e:
            log.error(f"Failed to setup audio: {e}")
            self._play_btn.setEnabled(False)
            self._stop_btn.setEnabled(False)

    def _toggle_play(self):
        if not self._player:
            return
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
            self._play_btn.setText("Play")
        else:
            self._player.play()
            self._play_btn.setText("Pause")

    def _stop(self):
        if self._player:
            self._player.stop()
            self._play_btn.setText("Play")
        self._play_btn.setEnabled(False)
        self._stop_btn.setEnabled(False)

    def clear(self):
        self._stop()
        self._image_label.clear()
        self._info_label.clear()
