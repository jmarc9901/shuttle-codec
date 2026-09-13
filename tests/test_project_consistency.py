"""Guards that keep the repository internally consistent.

Nothing here tests behaviour: these fail when the version, the translations or
the documented formats drift apart. That is the kind of rot that is invisible
until a user hits it, in a project where several files describe the same thing.
"""

import os
import re
import string
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import __version__
from src.ffmpeg_handler import CONTAINER_AUDIO_CODEC, COPY_SAFE_AUDIO_CODECS, FFmpegHandler
from src.i18n import LANG_EN, LANG_ES, TRANSLATIONS
from src.presets import get_preset, get_preset_ids

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

# Only the literal form: `tr("key")`. Keys passed through a variable (presets)
# are checked separately below.
TR_LITERAL = re.compile(r"""\btr\(\s*["']([a-z0-9_]+)["']""")
MARKDOWN_LINK = re.compile(r"\]\(([^)\s]+)\)")


def read(*parts: str) -> str:
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


def source_files() -> list[str]:
    directory = os.path.join(ROOT, "src")
    return [
        os.path.join(directory, name)
        for name in sorted(os.listdir(directory))
        if name.endswith(".py")
    ]


class TestVersionConsistency(unittest.TestCase):
    def test_changelog_documents_the_current_version(self) -> None:
        first = re.search(r"^## v(\S+)", read("CHANGELOG.md"), re.MULTILINE)
        self.assertIsNotNone(first, "CHANGELOG.md has no `## vX.Y.Z` heading")
        assert first is not None
        self.assertEqual(first.group(1), __version__)

    def test_readme_announces_the_current_version(self) -> None:
        """Each README must carry a heading for the version being shipped."""
        pattern = re.compile(rf"^#{{2,3}} .*{re.escape(__version__)}", re.MULTILINE)
        for name in ("README.md", "README.es.md"):
            with self.subTest(readme=name):
                self.assertRegex(read(name), pattern)

    def test_pyproject_reads_the_version_from_the_package(self) -> None:
        pyproject = read("pyproject.toml")
        self.assertIn('dynamic = ["version"]', pyproject)
        self.assertIn('version = { attr = "src.__version__" }', pyproject)

    def test_the_app_exposes_the_package_version(self) -> None:
        from src.app import VERSION

        self.assertEqual(VERSION, __version__)

    def test_the_installer_fallback_matches_the_version(self) -> None:
        """`iscc` without `/DMyAppVersion` must not ship a mislabelled installer."""
        match = re.search(r'#define MyAppVersion "([^"]+)"', read("installer", "shuttle-codec.iss"))
        self.assertIsNotNone(match, "the .iss has no MyAppVersion fallback")
        assert match is not None
        self.assertEqual(match.group(1), __version__)


class TestTranslations(unittest.TestCase):
    def test_both_languages_define_the_same_keys(self) -> None:
        spanish, english = set(TRANSLATIONS[LANG_ES]), set(TRANSLATIONS[LANG_EN])
        self.assertEqual(spanish - english, set(), "keys missing in English")
        self.assertEqual(english - spanish, set(), "keys missing in Spanish")

    def test_every_translation_call_uses_an_existing_key(self) -> None:
        for path in source_files():
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            for key in TR_LITERAL.findall(content):
                with self.subTest(key=key, file=os.path.basename(path)):
                    for language in (LANG_ES, LANG_EN):
                        self.assertIn(key, TRANSLATIONS[language])

    def test_preset_labels_are_translated(self) -> None:
        for preset_id in get_preset_ids():
            preset = get_preset(preset_id)
            self.assertIsNotNone(preset, f"preset {preset_id} is in the order but not defined")
            assert preset is not None
            for field in ("label_key", "desc_key"):
                with self.subTest(preset=preset_id, field=field):
                    for language in (LANG_ES, LANG_EN):
                        self.assertIn(preset[field], TRANSLATIONS[language])

    def test_placeholders_match_between_languages(self) -> None:
        """A translation that drops a `{}` would raise or print a literal brace."""
        def fields(text: str) -> set[str]:
            return {name for _, name, _, _ in string.Formatter().parse(text) if name is not None}

        for key in TRANSLATIONS[LANG_ES]:
            with self.subTest(key=key):
                self.assertEqual(fields(TRANSLATIONS[LANG_ES][key]), fields(TRANSLATIONS[LANG_EN][key]))


class TestFormatDeclarations(unittest.TestCase):
    def test_every_video_format_declares_its_copy_safe_audio_codecs(self) -> None:
        """A new container must state what it can stream-copy, or nothing will."""
        for name, fmt in FFmpegHandler.VIDEO_FORMATS.items():
            if fmt.get("gif_mode") or name in CONTAINER_AUDIO_CODEC:
                continue  # GIF has no audio; WebM always re-encodes to Opus
            with self.subTest(format=name):
                self.assertIn(name, COPY_SAFE_AUDIO_CODECS)

    def test_copy_safe_codecs_are_lowercase(self) -> None:
        for name, codecs in COPY_SAFE_AUDIO_CODECS.items():
            with self.subTest(format=name):
                for codec in codecs:
                    self.assertEqual(codec, codec.lower())

    def test_documented_formats_exist_in_the_handler(self) -> None:
        video = set(FFmpegHandler.VIDEO_FORMATS)
        audio = set(FFmpegHandler.AUDIO_FORMATS)
        self.assertIn("MP4 (H.264)", video)
        self.assertIn("MP4 (H.265)", video)
        for name in ("MP3", "AAC", "WAV", "FLAC", "OGG (Vorbis)", "M4A", "WMA"):
            with self.subTest(format=name):
                self.assertIn(name, audio)


class TestDocumentationLinks(unittest.TestCase):
    """Every relative markdown link must point at a file that exists."""

    def markdown_files(self) -> list[str]:
        files = ["README.md", "README.es.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md"]
        docs = os.path.join(ROOT, "docs")
        files += [os.path.join("docs", name) for name in sorted(os.listdir(docs)) if name.endswith(".md")]
        return files

    def test_relative_links_resolve(self) -> None:
        for relative in self.markdown_files():
            content = read(relative)
            base = os.path.dirname(os.path.join(ROOT, relative))
            for target in MARKDOWN_LINK.findall(content):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                path = target.split("#", 1)[0]
                if not path:
                    continue
                with self.subTest(file=relative, target=target):
                    self.assertTrue(
                        os.path.exists(os.path.normpath(os.path.join(base, path))),
                        f"{relative} links to a missing file: {target}",
                    )


if __name__ == "__main__":
    unittest.main()
