"""
Test configuration and utilities.

This module provides common utilities, fixtures, and configuration
for the test suite.
"""

import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock

import httpx

from viu_media.core.config import AppConfig
from viu_media.core.config.model import (
    AnilistConfig,
    GeneralConfig,
    StreamConfig,
    MpvConfig,
)


class BaseTestCase(unittest.TestCase):
    """Base test case with common setup and utilities."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.mock_http_client = Mock(spec=httpx.Client)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_mock_config(self, **overrides) -> AppConfig:
        """Create a mock AppConfig with default values."""
        config_dict = {
            "general": {
                "media_api": "anilist",
                "provider": "allanime",
                "selector": "default",
                "preferred_spinner": "dots",
                "pygment_style": "default",
            },
            "anilist": {
                "per_page": 20,
            },
            "mpv": {
                "args": "",
            },
            "stream": {
                "quality": "1080",
                "translation_type": "sub",
                "server": "TOP",
            },
        }
        
        # Apply overrides
        for key, value in overrides.items():
            if "." in key:
                section, field = key.split(".", 1)
                if section not in config_dict:
                    config_dict[section] = {}
                config_dict[section][field] = value
            else:
                config_dict[key] = value

        return AppConfig.model_validate(config_dict)

    def create_mock_http_response(
        self, 
        status_code: int = 200, 
        json_data: Dict[str, Any] = None,
        text: str = "",
    ) -> Mock:
        """Create a mock HTTP response."""
        response = Mock()
        response.status_code = status_code
        response.json.return_value = json_data or {}
        response.text = text
        response.headers = {}
        return response

    def create_temp_config_file(self, content: str) -> Path:
        """Create a temporary config file."""
        config_file = self.temp_path / "config.toml"
        config_file.write_text(content)
        return config_file


class MockProvider:
    """Mock provider for testing."""
    
    def __init__(self):
        self.search = Mock()
        self.get = Mock()
        self.episode_streams = Mock()


class MockMediaApi:
    """Mock media API client for testing."""
    
    def __init__(self):
        self.authenticate = Mock()
        self.is_authenticated = Mock(return_value=False)
        self.get_viewer_profile = Mock()
        self.search_media = Mock()
        self.search_media_list = Mock()
        self.update_list_entry = Mock()
        self.delete_list_entry = Mock()
        self.get_recommendation_for = Mock()
        self.get_characters_of = Mock()
        self.get_related_anime_for = Mock()
        self.get_airing_schedule_for = Mock()
        self.get_reviews_for = Mock()
        self.get_notifications = Mock()
        self.transform_raw_search_data = Mock()


class MockPlayer:
    """Mock player for testing."""
    
    def __init__(self):
        self.play = Mock()


class MockSelector:
    """Mock selector for testing."""
    
    def __init__(self):
        self.choose = Mock()
        self.confirm = Mock()
        self.ask = Mock()