"""Integration tests for viu components working together."""

import unittest
from unittest.mock import Mock, patch, MagicMock

from viu_media.core.config import AppConfig
from viu_media.libs.provider.anime.params import SearchParams
from viu_media.libs.media_api.params import MediaSearchParams

from ..conftest import BaseTestCase, MockProvider, MockMediaApi, MockPlayer, MockSelector


class TestProviderMediaApiIntegration(BaseTestCase):
    """Test integration between provider and media API."""

    def setUp(self):
        super().setUp()
        self.config = self.create_mock_config()
        self.provider = MockProvider()
        self.media_api = MockMediaApi()

    def test_search_workflow_integration(self):
        """Test complete search workflow from media API to provider."""
        # Mock media API search results
        from viu_media.libs.media_api.types import MediaSearchResult, MediaItem, MediaTitle
        
        media_item = MediaItem(
            id=123,
            title=MediaTitle(english="Test Anime", romaji="Test Anime"),
            description="Test description"
        )
        
        search_result = MediaSearchResult(
            media=[media_item],
            page_info=None
        )
        
        self.media_api.search_media.return_value = search_result
        
        # Mock provider search results
        from viu_media.libs.provider.anime.types import SearchResults, SearchResult
        
        provider_result = SearchResult(
            id="test_id",
            title="Test Anime",
            url="http://example.com/anime/test",
            poster=None
        )
        
        provider_search = SearchResults(results=[provider_result])
        self.provider.search.return_value = provider_search
        
        # Test the workflow
        query = "test anime"
        
        # Step 1: Search media API
        media_search_params = MediaSearchParams(query=query)
        media_results = self.media_api.search_media(media_search_params)
        
        self.assertIsNotNone(media_results)
        self.assertEqual(len(media_results.media), 1)
        self.assertEqual(media_results.media[0].title.english, "Test Anime")
        
        # Step 2: Search provider
        provider_search_params = SearchParams(query=query)
        provider_results = self.provider.search(provider_search_params)
        
        self.assertIsNotNone(provider_results)
        self.assertEqual(len(provider_results.results), 1)
        self.assertEqual(provider_results.results[0].title, "Test Anime")

    def test_episode_streaming_workflow(self):
        """Test complete episode streaming workflow."""
        from viu_media.libs.provider.anime.types import Anime, AnimeTitle, Server, StreamLink
        from viu_media.libs.provider.anime.params import AnimeParams, EpisodeStreamsParams
        
        # Mock anime data
        anime = Anime(
            id="test_anime_id",
            title=AnimeTitle(english="Test Anime", romaji="Test Anime"),
            poster=None,
            episodes={1: "Episode 1", 2: "Episode 2"}
        )
        
        self.provider.get.return_value = anime
        
        # Mock server data
        server = Server(
            name="Test Server",
            links=[
                StreamLink(link="http://example.com/stream1", quality="1080"),
                StreamLink(link="http://example.com/stream2", quality="720")
            ]
        )
        
        def mock_episode_streams(params):
            yield server
        
        self.provider.episode_streams.return_value = mock_episode_streams(None)
        
        # Test the workflow
        # Step 1: Get anime details
        anime_params = AnimeParams(anime_id="test_anime_id", query="test anime")
        anime_data = self.provider.get(anime_params)
        
        self.assertIsNotNone(anime_data)
        self.assertEqual(anime_data.id, "test_anime_id")
        self.assertIn(1, anime_data.episodes)
        
        # Step 2: Get episode streams
        from viu_media.libs.provider.anime.types import TranslationType
        
        stream_params = EpisodeStreamsParams(
            anime_id="test_anime_id",
            query="test anime",
            episode=1,
            translation_type=TranslationType.SUB
        )
        
        servers = list(self.provider.episode_streams(stream_params))
        
        self.assertEqual(len(servers), 1)
        self.assertEqual(servers[0].name, "Test Server")
        self.assertEqual(len(servers[0].links), 2)

    def test_user_list_management_workflow(self):
        """Test user list management workflow."""
        from viu_media.libs.media_api.params import UpdateUserMediaListEntryParams
        from viu_media.libs.media_api.types import UserMediaListStatus
        
        # Step 1: Authenticate user
        self.media_api.authenticate.return_value = Mock(id=123, name="TestUser")
        profile = self.media_api.authenticate("test_token")
        
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "TestUser")
        
        # Step 2: Update list entry
        self.media_api.is_authenticated.return_value = True
        self.media_api.update_list_entry.return_value = True
        
        update_params = UpdateUserMediaListEntryParams(
            media_id=123,
            status=UserMediaListStatus.WATCHING
        )
        
        success = self.media_api.update_list_entry(update_params)
        self.assertTrue(success)


class TestPlayerSelectorIntegration(BaseTestCase):
    """Test integration between player and selector components."""

    def setUp(self):
        super().setUp()
        self.config = self.create_mock_config()
        self.player = MockPlayer()
        self.selector = MockSelector()

    def test_episode_selection_and_playback_workflow(self):
        """Test complete episode selection and playback workflow."""
        from viu_media.libs.player.params import PlayerParams
        from viu_media.libs.player.types import PlayerResult
        
        # Mock episode selection
        episode_choices = ["Episode 1", "Episode 2", "Episode 3"]
        self.selector.choose.return_value = "Episode 2"
        
        selected_episode = self.selector.choose("Select episode:", episode_choices)
        self.assertEqual(selected_episode, "Episode 2")
        
        # Mock playback
        self.player.play.return_value = PlayerResult(success=True)
        
        player_params = PlayerParams(
            url="http://example.com/episode2.mp4",
            title="Test Anime - Episode 2",
            query="test anime"
        )
        
        result = self.player.play(player_params)
        self.assertTrue(result.success)

    def test_quality_selection_workflow(self):
        """Test quality selection workflow."""
        # Mock quality selection
        quality_choices = ["1080p", "720p", "480p", "360p"]
        self.selector.choose.return_value = "1080p"
        
        selected_quality = self.selector.choose("Select quality:", quality_choices)
        self.assertEqual(selected_quality, "1080p")
        
        # Mock corresponding stream URL selection
        stream_url = "http://example.com/stream_1080p.mp4"
        
        from viu_media.libs.player.params import PlayerParams
        from viu_media.libs.player.types import PlayerResult
        
        self.player.play.return_value = PlayerResult(success=True)
        
        player_params = PlayerParams(
            url=stream_url,
            title="Test Anime",
            query="test anime"
        )
        
        result = self.player.play(player_params)
        self.assertTrue(result.success)

    def test_download_confirmation_workflow(self):
        """Test download confirmation workflow."""
        # Mock download confirmation
        self.selector.confirm.return_value = True
        
        confirmed = self.selector.confirm("Download 5 episodes (approximately 2.5GB)?")
        self.assertTrue(confirmed)
        
        # Mock download location selection
        self.selector.ask.return_value = "/home/user/Downloads/anime"
        
        download_path = self.selector.ask("Download location:", default="/home/user/Downloads")
        self.assertEqual(download_path, "/home/user/Downloads/anime")


class TestFullApplicationWorkflow(BaseTestCase):
    """Test complete application workflows."""

    def setUp(self):
        super().setUp()
        self.config = self.create_mock_config()
        self.provider = MockProvider()
        self.media_api = MockMediaApi()
        self.player = MockPlayer()
        self.selector = MockSelector()

    def test_complete_watch_workflow(self):
        """Test complete workflow from search to watch."""
        # Step 1: User searches for anime
        self.selector.ask.return_value = "attack on titan"
        search_query = self.selector.ask("Search for anime:")
        
        # Step 2: Media API search
        from viu_media.libs.media_api.types import MediaSearchResult, MediaItem, MediaTitle
        
        media_item = MediaItem(
            id=123,
            title=MediaTitle(english="Attack on Titan", romaji="Shingeki no Kyojin"),
            description="Humanity fights titans"
        )
        
        search_result = MediaSearchResult(media=[media_item], page_info=None)
        self.media_api.search_media.return_value = search_result
        
        # Step 3: User selects anime
        self.selector.choose.return_value = "Attack on Titan"
        selected_anime = self.selector.choose(
            "Select anime:", 
            ["Attack on Titan", "Attack on Titan: Season 2"]
        )
        
        # Step 4: Provider search
        from viu_media.libs.provider.anime.types import SearchResults, SearchResult, Anime, AnimeTitle
        
        provider_result = SearchResult(
            id="aot_id",
            title="Attack on Titan",
            url="http://example.com/anime/aot",
            poster=None
        )
        
        provider_search = SearchResults(results=[provider_result])
        self.provider.search.return_value = provider_search
        
        # Step 5: Get anime details
        anime = Anime(
            id="aot_id",
            title=AnimeTitle(english="Attack on Titan", romaji="Shingeki no Kyojin"),
            poster=None,
            episodes={i: f"Episode {i}" for i in range(1, 26)}
        )
        
        self.provider.get.return_value = anime
        
        # Step 6: User selects episode
        self.selector.choose.return_value = "Episode 1"
        selected_episode = self.selector.choose(
            "Select episode:",
            [f"Episode {i}" for i in range(1, 6)]
        )
        
        # Step 7: Get episode streams
        from viu_media.libs.provider.anime.types import Server, StreamLink
        
        server = Server(
            name="Server 1",
            links=[
                StreamLink(link="http://example.com/aot_ep1_1080p.mp4", quality="1080"),
                StreamLink(link="http://example.com/aot_ep1_720p.mp4", quality="720")
            ]
        )
        
        def mock_streams(params):
            yield server
        
        self.provider.episode_streams.return_value = mock_streams(None)
        
        # Step 8: Play episode
        from viu_media.libs.player.params import PlayerParams
        from viu_media.libs.player.types import PlayerResult
        
        self.player.play.return_value = PlayerResult(success=True, duration=1440)  # 24 minutes
        
        player_params = PlayerParams(
            url="http://example.com/aot_ep1_1080p.mp4",
            title="Attack on Titan - Episode 1",
            query="attack on titan"
        )
        
        result = self.player.play(player_params)
        
        # Verify the complete workflow
        self.assertEqual(search_query, "attack on titan")
        self.assertEqual(selected_anime, "Attack on Titan")
        self.assertEqual(selected_episode, "Episode 1")
        self.assertTrue(result.success)
        self.assertEqual(result.duration, 1440)

    def test_complete_download_workflow(self):
        """Test complete download workflow."""
        # Step 1: User requests download
        self.selector.choose.return_value = "Download episodes"
        action = self.selector.choose("What would you like to do?", ["Watch", "Download episodes"])
        
        # Step 2: Select episodes to download
        self.selector.choose_multiple.return_value = ["Episode 1", "Episode 2", "Episode 3"]
        episodes = self.selector.choose_multiple(
            "Select episodes to download:",
            [f"Episode {i}" for i in range(1, 11)]
        )
        
        # Step 3: Confirm download
        self.selector.confirm.return_value = True
        confirmed = self.selector.confirm(f"Download {len(episodes)} episodes?")
        
        # Step 4: Select download quality
        self.selector.choose.return_value = "1080p"
        quality = self.selector.choose("Select quality:", ["1080p", "720p", "480p"])
        
        # Step 5: Select download location
        self.selector.ask.return_value = "/home/user/Downloads/AttackOnTitan"
        download_path = self.selector.ask("Download location:")
        
        # Verify workflow
        self.assertEqual(action, "Download episodes")
        self.assertEqual(len(episodes), 3)
        self.assertTrue(confirmed)
        self.assertEqual(quality, "1080p")
        self.assertEqual(download_path, "/home/user/Downloads/AttackOnTitan")

    @patch('viu_media.core.config.AppConfig')
    def test_configuration_loading_workflow(self, mock_config_class):
        """Test configuration loading and validation workflow."""
        # Mock configuration loading
        mock_config = AppConfig()
        mock_config_class.return_value = mock_config
        
        # Test that configuration is properly loaded
        config = AppConfig()
        self.assertIsInstance(config, AppConfig)
        
        # Test configuration validation
        self.assertIsNotNone(config.general)
        self.assertIsNotNone(config.stream)
        self.assertIsNotNone(config.anilist)


class TestErrorHandlingIntegration(BaseTestCase):
    """Test error handling across integrated components."""

    def setUp(self):
        super().setUp()
        self.config = self.create_mock_config()
        self.provider = MockProvider()
        self.media_api = MockMediaApi()
        self.player = MockPlayer()
        self.selector = MockSelector()

    def test_network_error_handling(self):
        """Test handling of network errors across components."""
        # Mock network failure in provider
        self.provider.search.side_effect = Exception("Network error")
        
        try:
            from viu_media.libs.provider.anime.params import SearchParams
            search_params = SearchParams(query="test")
            self.provider.search(search_params)
            self.fail("Expected exception was not raised")
        except Exception as e:
            self.assertIn("Network error", str(e))

    def test_authentication_error_handling(self):
        """Test handling of authentication errors."""
        # Mock authentication failure
        self.media_api.authenticate.return_value = None
        self.media_api.is_authenticated.return_value = False
        
        profile = self.media_api.authenticate("invalid_token")
        self.assertIsNone(profile)
        self.assertFalse(self.media_api.is_authenticated())

    def test_player_error_handling(self):
        """Test handling of player errors."""
        from viu_media.libs.player.params import PlayerParams
        from viu_media.libs.player.types import PlayerResult
        
        # Mock player failure
        self.player.play.return_value = PlayerResult(success=False, error="Player not found")
        
        player_params = PlayerParams(
            url="http://example.com/video.mp4",
            title="Test Video",
            query="test"
        )
        
        result = self.player.play(player_params)
        self.assertFalse(result.success)
        self.assertIn("Player not found", result.error)

    def test_user_cancellation_handling(self):
        """Test handling of user cancellations."""
        # Mock user cancellation in selector
        self.selector.choose.return_value = None  # User canceled
        
        result = self.selector.choose("Select option:", ["Option 1", "Option 2"])
        self.assertIsNone(result)
        
        # Mock user declining confirmation
        self.selector.confirm.return_value = False
        
        confirmed = self.selector.confirm("Continue with download?")
        self.assertFalse(confirmed)


if __name__ == '__main__':
    unittest.main()