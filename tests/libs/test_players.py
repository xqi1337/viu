"""Tests for media player functionality."""

import subprocess
import unittest
from unittest.mock import Mock, patch, MagicMock

from viu_media.libs.player.base import BasePlayer
from viu_media.libs.player.params import PlayerParams
from viu_media.libs.player.types import PlayerResult
from viu_media.libs.player.player import create_player

from ..conftest import BaseTestCase


class TestBasePlayer(BaseTestCase):
    """Test the base player abstract class."""

    def test_base_player_initialization(self):
        """Test base player initialization."""
        
        class TestPlayer(BasePlayer):
            def play(self, params):
                return PlayerResult(success=True)
            def play_with_ipc(self, params, socket_path):
                return Mock(spec=subprocess.Popen)
        
        config = self.create_mock_config()
        player = TestPlayer(config.stream)
        
        self.assertEqual(player.stream_config, config.stream)

    def test_abstract_methods_must_be_implemented(self):
        """Test that all abstract methods must be implemented."""
        
        # Incomplete implementation should raise TypeError
        with self.assertRaises(TypeError):
            class IncompletePlayer(BasePlayer):
                def play(self, params):
                    return PlayerResult(success=True)
                # Missing play_with_ipc method
            
            config = self.create_mock_config()
            IncompletePlayer(config.stream)


class MockPlayer(BasePlayer):
    """Mock player for testing."""
    
    def __init__(self, config):
        super().__init__(config)
        self.play_calls = []
        self.ipc_calls = []
        self.should_succeed = True
        
    def play(self, params):
        self.play_calls.append(params)
        return PlayerResult(success=self.should_succeed)
        
    def play_with_ipc(self, params, socket_path):
        self.ipc_calls.append((params, socket_path))
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.returncode = 0 if self.should_succeed else 1
        return mock_process


class TestPlayerMethods(BaseTestCase):
    """Test player method contracts and behavior."""

    def setUp(self):
        super().setUp()
        config = self.create_mock_config()
        self.player = MockPlayer(config.stream)

    def test_play_method_contract(self):
        """Test play method accepts correct parameters."""
        params = PlayerParams(
            url="http://example.com/video.mp4",
            title="Test Video",
            query="test query"
        )
        
        result = self.player.play(params)
        
        self.assertIsInstance(result, PlayerResult)
        self.assertTrue(result.success)
        self.assertEqual(len(self.player.play_calls), 1)
        self.assertEqual(self.player.play_calls[0], params)

    def test_play_with_failure(self):
        """Test play method when playback fails."""
        self.player.should_succeed = False
        
        params = PlayerParams(
            url="http://example.com/video.mp4",
            title="Test Video",
            query="test query"
        )
        
        result = self.player.play(params)
        
        self.assertIsInstance(result, PlayerResult)
        self.assertFalse(result.success)

    def test_play_with_ipc_method_contract(self):
        """Test play_with_ipc method accepts correct parameters."""
        params = PlayerParams(
            url="http://example.com/video.mp4",
            title="Test Video",
            query="test query"
        )
        socket_path = "/tmp/test_socket"
        
        process = self.player.play_with_ipc(params, socket_path)
        
        self.assertIsInstance(process, subprocess.Popen)
        self.assertEqual(len(self.player.ipc_calls), 1)
        self.assertEqual(self.player.ipc_calls[0][0], params)
        self.assertEqual(self.player.ipc_calls[0][1], socket_path)

    def test_player_params_validation(self):
        """Test that PlayerParams validates required fields."""
        # Valid parameters
        valid_params = PlayerParams(
            url="http://example.com/video.mp4",
            title="Test Video",
            query="test query"
        )
        self.assertIsNotNone(valid_params.url)
        
        # Test with additional optional parameters
        extended_params = PlayerParams(
            url="http://example.com/video.mp4",
            title="Test Video",
            query="test query",
            start_time=30,
            end_time=120
        )
        result = self.player.play(extended_params)
        self.assertTrue(result.success)


class TestPlayerFactory(BaseTestCase):
    """Test the player factory function."""

    def test_create_mpv_player(self):
        """Test creating MPV player."""
        config = self.create_mock_config()
        player = create_player("mpv", config)
        
        self.assertIsInstance(player, BasePlayer)

    def test_create_vlc_player(self):
        """Test creating VLC player."""
        config = self.create_mock_config()
        player = create_player("vlc", config)
        
        self.assertIsInstance(player, BasePlayer)

    def test_create_invalid_player_raises_error(self):
        """Test that invalid player name raises an error."""
        config = self.create_mock_config()
        
        with self.assertRaises(ValueError):
            create_player("invalid_player", config)


class TestPlayerIntegration(BaseTestCase):
    """Integration tests for player functionality."""

    @patch('subprocess.Popen')
    def test_player_subprocess_integration(self, mock_popen):
        """Test player integration with subprocess."""
        mock_process = Mock()
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        config = self.create_mock_config()
        
        # Create a concrete player implementation that uses subprocess
        class ConcretePlayer(BasePlayer):
            def play(self, params):
                try:
                    process = subprocess.Popen([
                        "mpv", 
                        "--no-video" if not params.url.endswith('.mp4') else "",
                        params.url
                    ])
                    process.wait()
                    return PlayerResult(success=process.returncode == 0)
                except Exception:
                    return PlayerResult(success=False)
                    
            def play_with_ipc(self, params, socket_path):
                return subprocess.Popen([
                    "mpv",
                    f"--input-ipc-server={socket_path}",
                    params.url
                ])
        
        player = ConcretePlayer(config.stream)
        
        params = PlayerParams(
            url="http://example.com/video.mp4",
            title="Test Video",
            query="test query"
        )
        
        result = player.play(params)
        self.assertTrue(result.success)
        
        # Test IPC call
        ipc_process = player.play_with_ipc(params, "/tmp/test_socket")
        self.assertIsNotNone(ipc_process)

    def test_player_error_handling(self):
        """Test player error handling scenarios."""
        config = self.create_mock_config()
        
        class ErrorPlayer(BasePlayer):
            def play(self, params):
                # Simulate player executable not found
                raise FileNotFoundError("Player executable not found")
                
            def play_with_ipc(self, params, socket_path):
                raise FileNotFoundError("Player executable not found")
        
        player = ErrorPlayer(config.stream)
        
        params = PlayerParams(
            url="http://example.com/video.mp4",
            title="Test Video",
            query="test query"
        )
        
        # Player should handle errors appropriately
        with self.assertRaises(FileNotFoundError):
            player.play(params)

    @patch('os.path.exists')
    def test_player_executable_validation(self, mock_exists):
        """Test player executable validation."""
        mock_exists.return_value = False  # Simulate executable not found
        
        config = self.create_mock_config()
        
        class ValidatingPlayer(BasePlayer):
            def __init__(self, config):
                super().__init__(config)
                self.executable = "mpv"
                
            def _validate_executable(self):
                import os
                return os.path.exists(self.executable)
                
            def play(self, params):
                if not self._validate_executable():
                    return PlayerResult(success=False, error="Executable not found")
                return PlayerResult(success=True)
                
            def play_with_ipc(self, params, socket_path):
                return Mock(spec=subprocess.Popen)
        
        player = ValidatingPlayer(config.stream)
        
        params = PlayerParams(
            url="http://example.com/video.mp4",
            title="Test Video",
            query="test query"
        )
        
        result = player.play(params)
        self.assertFalse(result.success)
        self.assertIn("Executable not found", result.error or "")


class TestPlayerResult(BaseTestCase):
    """Test PlayerResult type."""

    def test_player_result_success(self):
        """Test successful PlayerResult."""
        result = PlayerResult(success=True)
        self.assertTrue(result.success)
        self.assertIsNone(result.error)

    def test_player_result_failure(self):
        """Test failed PlayerResult with error."""
        error_msg = "Playback failed"
        result = PlayerResult(success=False, error=error_msg)
        self.assertFalse(result.success)
        self.assertEqual(result.error, error_msg)

    def test_player_result_with_additional_data(self):
        """Test PlayerResult with additional data."""
        result = PlayerResult(
            success=True,
            duration=120,
            position=30
        )
        self.assertTrue(result.success)
        self.assertEqual(result.duration, 120)
        self.assertEqual(result.position, 30)


if __name__ == '__main__':
    unittest.main()