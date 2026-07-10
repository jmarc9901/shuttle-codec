from typing import Any, Dict, List, Optional

PresetDef = Dict[str, Any]

PRESETS: Dict[str, PresetDef] = {
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
        "crf": 0,
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

PRESET_ORDER: List[str] = [
    "youtube_1080p",
    "youtube_4k",
    "whatsapp",
    "telegram",
    "discord",
    "twitter_gif",
    "high_quality",
    "small_size",
]


def get_preset(preset_id: str) -> Optional[PresetDef]:
    return PRESETS.get(preset_id)


def get_preset_ids() -> List[str]:
    return PRESET_ORDER
