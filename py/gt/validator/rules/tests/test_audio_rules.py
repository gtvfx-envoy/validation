"""Tests for audio validation rules."""

import os
import tempfile
import unittest
from unittest.mock import patch

from gt.runtime import HostType
from gt.validator.config import Config
from gt.validator.rules.audio import (
    AudioFilenameLengthRule,
    AudioFileSizeRule,
    AudioValidExtensionRule,
    _is_audio_file,
)


class TestIsAudioFile(unittest.TestCase):
    """Test the _is_audio_file helper."""

    def test_wav_is_audio(self) -> None:
        self.assertTrue(_is_audio_file("/Game/Sounds/Explosion.wav"))

    def test_mp3_is_audio(self) -> None:
        self.assertTrue(_is_audio_file("/Game/Sounds/BGM.mp3"))

    def test_ogg_is_audio(self) -> None:
        self.assertTrue(_is_audio_file("/Game/Sounds/footstep.ogg"))

    def test_png_is_not_audio(self) -> None:
        self.assertFalse(_is_audio_file("/Game/Textures/T_Wall.png"))

    def test_uasset_is_not_audio(self) -> None:
        self.assertFalse(_is_audio_file("/Game/Meshes/SM_Player.uasset"))


class TestAudioFileSizeRule(unittest.TestCase):
    """Test AudioFileSizeRule."""

    def setUp(self) -> None:
        self.config = Config()

    @patch("gt.runtime.RuntimeDetector.getCurrentHost", return_value=HostType.STANDALONE)
    def test_passes_within_limit(self, mock_host) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(b"0" * (1024 * 1024))  # 1 MB
            path = f.name
        f.close()

        try:
            rule = AudioFileSizeRule(self.config)
            result = rule.validate(path)
            self.assertTrue(result.passed)
            self.assertIn("within limit", result.message.lower())
        finally:
            os.unlink(path)

    @patch("gt.runtime.RuntimeDetector.getCurrentHost", return_value=HostType.STANDALONE)
    def test_fails_exceeds_limit(self, mock_host) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            f.write(b"0" * (60 * 1024 * 1024))  # 60 MB, exceeds 50 MB limit
            path = f.name
        f.close()

        try:
            rule = AudioFileSizeRule(self.config)
            result = rule.validate(path)
            self.assertFalse(result.passed)
            self.assertIn("exceeds", result.message.lower())
        finally:
            os.unlink(path)

    @patch("gt.runtime.RuntimeDetector.getCurrentHost", return_value=HostType.STANDALONE)
    def test_skips_non_audio(self, mock_host) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(b"0" * 1024)
            path = f.name
        f.close()

        try:
            rule = AudioFileSizeRule(self.config)
            result = rule.validate(path)
            self.assertTrue(result.skipped)
        finally:
            os.unlink(path)


class TestAudioValidExtensionRule(unittest.TestCase):
    """Test AudioValidExtensionRule."""

    def setUp(self) -> None:
        self.config = Config()

    @patch("gt.runtime.RuntimeDetector.getCurrentHost", return_value=HostType.STANDALONE)
    def test_passes_valid_extension(self, mock_host) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(b"0" * 1024)
            path = f.name
        f.close()

        try:
            rule = AudioValidExtensionRule(self.config)
            result = rule.validate(path)
            self.assertTrue(result.passed)
        finally:
            os.unlink(path)

    @patch("gt.runtime.RuntimeDetector.getCurrentHost", return_value=HostType.STANDALONE)
    def test_skips_non_audio(self, mock_host) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"0" * 1024)
            path = f.name
        f.close()

        try:
            rule = AudioValidExtensionRule(self.config)
            result = rule.validate(path)
            self.assertTrue(result.skipped)
        finally:
            os.unlink(path)


class TestAudioFilenameLengthRule(unittest.TestCase):
    """Test AudioFilenameLengthRule."""

    def setUp(self) -> None:
        self.config = Config()

    @patch("gt.runtime.RuntimeDetector.getCurrentHost", return_value=HostType.STANDALONE)
    def test_passes_short_name(self, mock_host) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(b"0" * 1024)
            path = f.name
        f.close()

        try:
            rule = AudioFilenameLengthRule(self.config)
            result = rule.validate(path)
            self.assertTrue(result.passed)
        finally:
            os.unlink(path)

    @patch("gt.runtime.RuntimeDetector.getCurrentHost", return_value=HostType.STANDALONE)
    def test_skips_non_audio(self, mock_host) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"0" * 1024)
            path = f.name
        f.close()

        try:
            rule = AudioFilenameLengthRule(self.config)
            result = rule.validate(path)
            self.assertTrue(result.skipped)
        finally:
            os.unlink(path)


if __name__ == "__main__":  # pragma: no cover - manual execution
    unittest.main()
