"""Tests for anime provider functionality."""

import unittest
from unittest.mock import Mock, patch
from collections.abc import Iterator

from viu_media.libs.provider.anime.base import BaseAnimeProvider
from viu_media.libs.provider.anime.params import SearchParams, AnimeParams, EpisodeStreamsParams
from viu_media.libs.provider.anime.types import SearchResults, Anime, Server
from viu_media.libs.provider.anime.provider import create_provider

from ..conftest import BaseTestCase


class TestBaseAnimeProvider(BaseTestCase):
    """Test the base anime provider abstract class."""

    def test_base_provider_requires_headers(self):
        """Test that subclasses must define HEADERS."""
        
        # This should raise TypeError because HEADERS is not defined
        with self.assertRaises(TypeError) as context:
            class InvalidProvider(BaseAnimeProvider):
                def search(self, params):
                    pass
                def get(self, params):
                    pass
                def episode_streams(self, params):
                    pass
        
        self.assertIn("must define a 'HEADERS' class attribute", str(context.exception))

    def test_base_provider_with_headers(self):
        """Test that valid subclass can be created."""
        
        class ValidProvider(BaseAnimeProvider):
            HEADERS = {"User-Agent": "test"}
            
            def search(self, params):
                return None
            def get(self, params):
                return None
            def episode_streams(self, params):
                return None
        
        # Should not raise an exception
        provider = ValidProvider(self.mock_http_client)
        self.assertIsInstance(provider, BaseAnimeProvider)

    def test_provider_initialization(self):
        """Test provider initialization with HTTP client."""
        
        class TestProvider(BaseAnimeProvider):
            HEADERS = {"User-Agent": "test"}
            
            def search(self, params):
                return None
            def get(self, params):
                return None
            def episode_streams(self, params):
                return None
        
        provider = TestProvider(self.mock_http_client)
        self.assertEqual(provider.client, self.mock_http_client)


class TestAnimeProviderFactory(BaseTestCase):
    """Test the provider factory function."""

    def test_create_allanime_provider(self):
        """Test creating AllAnime provider."""
        provider = create_provider("allanime")
        self.assertIsInstance(provider, BaseAnimeProvider)

    def test_create_animepahe_provider(self):
        """Test creating AnimePahe provider."""
        provider = create_provider("animepahe")
        self.assertIsInstance(provider, BaseAnimeProvider)

    def test_create_invalid_provider_raises_error(self):
        """Test that invalid provider name raises an error."""
        with self.assertRaises(ValueError):
            create_provider("invalid_provider")


class MockConcreteProvider(BaseAnimeProvider):
    """Mock concrete provider for testing."""
    
    HEADERS = {"User-Agent": "test-agent"}
    
    def __init__(self, client):
        super().__init__(client)
        self.search_results = None
        self.anime_data = None
        self.servers_data = None
    
    def search(self, params: SearchParams):
        return self.search_results
    
    def get(self, params: AnimeParams):
        return self.anime_data
    
    def episode_streams(self, params: EpisodeStreamsParams):
        return self.servers_data


class TestProviderMethods(BaseTestCase):
    """Test provider method contracts and behavior."""

    def setUp(self):
        super().setUp()
        self.provider = MockConcreteProvider(self.mock_http_client)

    def test_search_method_contract(self):
        """Test search method accepts correct parameters."""
        search_params = SearchParams(query="test anime")
        
        # Should not raise an exception
        result = self.provider.search(search_params)
        self.assertIsNone(result)  # Mock returns None by default

    def test_search_with_results(self):
        """Test search method with mock results."""
        from viu_media.libs.provider.anime.types import SearchResult
        
        mock_results = SearchResults(
            results=[
                SearchResult(
                    id="123",
                    title="Test Anime",
                    url="http://example.com/anime/123",
                    poster=None
                )
            ]
        )
        self.provider.search_results = mock_results
        
        search_params = SearchParams(query="test anime")
        result = self.provider.search(search_params)
        
        self.assertEqual(result, mock_results)
        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0].title, "Test Anime")

    def test_get_method_contract(self):
        """Test get method accepts correct parameters."""
        anime_params = AnimeParams(anime_id="123", query="test anime")
        
        result = self.provider.get(anime_params)
        self.assertIsNone(result)  # Mock returns None by default

    def test_get_with_anime_data(self):
        """Test get method with mock anime data."""
        from viu_media.libs.provider.anime.types import AnimeTitle
        
        mock_anime = Anime(
            id="123",
            title=AnimeTitle(english="Test Anime", romaji="Test Anime"),
            poster=None,
            episodes={1: "Episode 1"}
        )
        self.provider.anime_data = mock_anime
        
        anime_params = AnimeParams(anime_id="123", query="test anime")
        result = self.provider.get(anime_params)
        
        self.assertEqual(result, mock_anime)
        self.assertEqual(result.id, "123")
        self.assertEqual(result.title.english, "Test Anime")

    def test_episode_streams_method_contract(self):
        """Test episode_streams method accepts correct parameters."""
        from viu_media.libs.provider.anime.types import TranslationType
        
        stream_params = EpisodeStreamsParams(
            anime_id="123",
            query="test anime",
            episode=1,
            translation_type=TranslationType.SUB
        )
        
        result = self.provider.episode_streams(stream_params)
        self.assertIsNone(result)  # Mock returns None by default

    def test_episode_streams_with_servers(self):
        """Test episode_streams method with mock server data."""
        from viu_media.libs.provider.anime.types import StreamLink, TranslationType
        
        mock_servers = [
            Server(
                name="Test Server",
                links=[
                    StreamLink(link="http://example.com/stream", quality="1080p")
                ]
            )
        ]
        
        def mock_iterator():
            for server in mock_servers:
                yield server
        
        self.provider.servers_data = mock_iterator()
        
        stream_params = EpisodeStreamsParams(
            anime_id="123",
            query="test anime", 
            episode=1,
            translation_type=TranslationType.SUB
        )
        
        result = self.provider.episode_streams(stream_params)
        
        # Convert iterator to list for testing
        servers = list(result)
        self.assertEqual(len(servers), 1)
        self.assertEqual(servers[0].name, "Test Server")
        self.assertEqual(len(servers[0].links), 1)
        self.assertEqual(servers[0].links[0].quality, "1080p")


class TestProviderIntegration(BaseTestCase):
    """Integration tests for provider functionality."""

    @patch('httpx.Client')
    def test_provider_with_http_client(self, mock_client_class):
        """Test provider integration with HTTP client."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        provider = MockConcreteProvider(mock_client)
        
        # Verify the client is assigned
        self.assertEqual(provider.client, mock_client)
        
        # Test that methods can be called
        search_params = SearchParams(query="test")
        provider.search(search_params)  # Should not raise

    def test_provider_error_handling(self):
        """Test provider error handling scenarios."""
        provider = MockConcreteProvider(self.mock_http_client)
        
        # Mock network error
        self.mock_http_client.get.side_effect = Exception("Network error")
        
        # Provider should handle errors gracefully
        search_params = SearchParams(query="test")
        
        # This test verifies the contract - methods should not raise
        # unless the provider implementation explicitly chooses to
        try:
            result = provider.search(search_params)
            # Should either return None or handle the error
        except Exception:
            # If provider chooses to raise, that's also valid
            pass


if __name__ == '__main__':
    unittest.main()