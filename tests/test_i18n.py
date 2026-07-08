import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.i18n import tr, set_language, get_language, get_available_languages, LANG_ES, LANG_EN


class TestI18n(unittest.TestCase):
    def setUp(self):
        set_language(LANG_ES)

    def test_default_language_is_spanish(self):
        self.assertEqual(get_language(), LANG_ES)

    def test_switch_to_english(self):
        set_language(LANG_EN)
        self.assertEqual(get_language(), LANG_EN)

    def test_available_languages(self):
        langs = get_available_languages()
        self.assertIn(LANG_ES, langs)
        self.assertIn(LANG_EN, langs)

    def test_tr_spanish(self):
        set_language(LANG_ES)
        self.assertEqual(tr("app_name"), "Shuttle Codec")
        self.assertEqual(tr("btn_convert"), "▶ Iniciar conversión")

    def test_tr_english(self):
        set_language(LANG_EN)
        self.assertEqual(tr("app_name"), "Shuttle Codec")
        self.assertEqual(tr("btn_convert"), "▶ Start conversion")

    def test_tr_with_args(self):
        set_language(LANG_ES)
        result = tr("btn_convert_batch", 5)
        self.assertEqual(result, "▶ Convertir 5 archivo(s)")

    def test_tr_missing_key(self):
        result = tr("nonexistent_key_xyz")
        self.assertEqual(result, "nonexistent_key_xyz")

    def test_tr_invalid_language_falls_back(self):
        set_language("invalid_lang")
        result = tr("app_name")
        self.assertEqual(result, "Shuttle Codec")

    def test_all_keys_have_english_translation(self):
        from src.i18n import TRANSLATIONS
        es_keys = set(TRANSLATIONS[LANG_ES].keys())
        en_keys = set(TRANSLATIONS[LANG_EN].keys())
        missing_in_en = es_keys - en_keys
        self.assertEqual(
            missing_in_en, set(),
            f"Keys missing in English translations: {missing_in_en}"
        )


if __name__ == "__main__":
    unittest.main()
