import unittest

from src.presets import (
    PRESET_ORDER,
    PRESETS,
    RESOLUTION_MAP,
    get_preset,
    resolution_to_scale,
)


class TestPresets(unittest.TestCase):
    def test_all_ordered_ids_exist(self):
        for pid in PRESET_ORDER:
            self.assertIn(pid, PRESETS, f"preset '{pid}' missing from PRESETS")

    def test_no_extra_presets_outside_order(self):
        self.assertEqual(set(PRESETS.keys()), set(PRESET_ORDER))

    def test_get_preset(self):
        preset = get_preset("youtube_1080p")
        self.assertIsNotNone(preset)
        self.assertEqual(preset["format"], "MP4 (H.264)")
        self.assertIsNone(get_preset("nonexistent"))

    def test_every_preset_has_translation_keys(self):
        from src.i18n import LANG_EN, LANG_ES, TRANSLATIONS
        for pid, preset in PRESETS.items():
            self.assertIn(preset["label_key"], TRANSLATIONS[LANG_ES], f"{pid}: label_key missing in ES")
            self.assertIn(preset["label_key"], TRANSLATIONS[LANG_EN], f"{pid}: label_key missing in EN")
            self.assertIn(preset["desc_key"], TRANSLATIONS[LANG_ES], f"{pid}: desc_key missing in ES")
            self.assertIn(preset["desc_key"], TRANSLATIONS[LANG_EN], f"{pid}: desc_key missing in EN")

    def test_gif_preset_uses_max_colors(self):
        gif = PRESETS["twitter_gif"]
        self.assertEqual(gif["format"], "GIF")
        self.assertNotIn("crf", gif)
        self.assertIn("max_colors", gif)
        self.assertTrue(2 <= gif["max_colors"] <= 256)

    def test_video_presets_have_crf(self):
        for pid, preset in PRESETS.items():
            if preset["format"] != "GIF":
                self.assertIn("crf", preset, f"{pid} missing crf")

    def test_resolution_map_covers_preset_values(self):
        for pid, preset in PRESETS.items():
            res = preset.get("resolution")
            if res is not None:
                self.assertIn(res, RESOLUTION_MAP, f"{pid}: resolution '{res}' not in RESOLUTION_MAP")

    def test_resolution_to_scale(self):
        self.assertIsNone(resolution_to_scale("Original"))
        self.assertEqual(resolution_to_scale("1920x1080 (1080p)"), "1920:1080")
        self.assertIsNone(resolution_to_scale("not-a-resolution"))
        self.assertIsNone(resolution_to_scale(None))


if __name__ == "__main__":
    unittest.main()
