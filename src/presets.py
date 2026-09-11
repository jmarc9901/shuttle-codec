"""Conversion presets and shared resolution mapping for Shuttle Codec."""

from typing import Any

PresetDef = dict[str, Any]

# Shared mapping: UI display label -> FFmpeg scale argument.
# Single source of truth used by presets and the main window.
RESOLUTION_MAP: dict[str, str | None] = {
    "Original": None,
    "3840x2160 (4K)": "3840:2160",
    "2560x1440 (1440p)": "2560:1440",
    "1920x1080 (1080p)": "1920:1080",
    "1280x720 (720p)": "1280:720",
    "854x480 (480p)": "854:480",
    "640x360 (360p)": "640:360",
}

PRESETS: dict[str, PresetDef] = {
    "youtube_1080p": {
        "label_key": "preset_youtube_1080p",
        "desc_key": "preset_youtube_1080p_desc",
        "format": "MP4 (H.264)",
        "crf": 23,
        "enc_preset": "medium",
        "resolution": "1920x1080 (1080p)",
        "framerate": "30",
        "keep_audio": True,
    },
    "youtube_4k": {
        "label_key": "preset_youtube_4k",
        "desc_key": "preset_youtube_4k_desc",
        "format": "MP4 (H.265)",
        "crf": 23,
        "enc_preset": "medium",
        "resolution": "3840x2160 (4K)",
        "framerate": "30",
        "keep_audio": True,
    },
    "whatsapp": {
        "label_key": "preset_whatsapp",
        "desc_key": "preset_whatsapp_desc",
        "format": "MP4 (H.264)",
        "crf": 28,
        "enc_preset": "fast",
        "resolution": "854x480 (480p)",
        "framerate": "30",
        "keep_audio": True,
    },
    "telegram": {
        "label_key": "preset_telegram",
        "desc_key": "preset_telegram_desc",
        "format": "MP4 (H.264)",
        "crf": 26,
        "enc_preset": "fast",
        "resolution": "1280x720 (720p)",
        "framerate": "30",
        "keep_audio": True,
    },
    "discord": {
        "label_key": "preset_discord",
        "desc_key": "preset_discord_desc",
        "format": "MP4 (H.264)",
        "crf": 26,
        "enc_preset": "fast",
        "resolution": "1280x720 (720p)",
        "framerate": "30",
        "keep_audio": True,
    },
    "twitter_gif": {
        "label_key": "preset_twitter_gif",
        "desc_key": "preset_twitter_gif_desc",
        "format": "GIF",
        "max_colors": 128,
        "enc_preset": "",
        "resolution": "Original",
        "framerate": "15",
        "keep_audio": False,
    },
    "high_quality": {
        "label_key": "preset_high_quality",
        "desc_key": "preset_high_quality_desc",
        "format": "MP4 (H.265)",
        "crf": 18,
        "enc_preset": "slow",
        "resolution": "Original",
        "framerate": "Original",
        "keep_audio": True,
    },
    "small_size": {
        "label_key": "preset_small_size",
        "desc_key": "preset_small_size_desc",
        "format": "MP4 (H.265)",
        "crf": 32,
        "enc_preset": "fast",
        "resolution": "640x360 (360p)",
        "framerate": "24",
        "keep_audio": True,
    },
}

PRESET_ORDER: list[str] = [
    "youtube_1080p",
    "youtube_4k",
    "whatsapp",
    "telegram",
    "discord",
    "twitter_gif",
    "high_quality",
    "small_size",
]


def get_preset(preset_id: str) -> PresetDef | None:
    return PRESETS.get(preset_id)


def get_preset_ids() -> list[str]:
    return PRESET_ORDER


def resolution_to_scale(display_label: str | None) -> str | None:
    """Translate a UI resolution label into an FFmpeg scale value (None = keep original)."""
    if display_label is None:
        return None
    return RESOLUTION_MAP.get(str(display_label))
