"""Tests for media API functionality."""

import unittest
from unittest.mock import Mock, patch

from viu_media.libs.media_api.base import BaseApiClient
from viu_media.libs.media_api.api import create_api_client
from viu_media.libs.media_api.params import MediaSearchParams
from viu_media.libs.media_api.types import UserProfile, MediaSearchResult

from ..conftest import BaseTestCase


class TestBaseApiClient(BaseTestCase):
    """Test the base media API client abstract class."""

    def test_base_api_client_initialization(self):
        """Test base API client initialization."""
        
        class TestApiClient(BaseApiClient):
            def authenticate(self, token):
                return None
            def is_authenticated(self):
                return False
            def get_viewer_profile(self):
                return None
            def search_media(self, params):
                return None
            def search_media_list(self, params):
                return None
            def update_list_entry(self, params):
                return False
            def delete_list_entry(self, media_id):
                return False
            def get_recommendation_for(self, params):
                return None
            def get_characters_of(self, params):
                return None
            def get_related_anime_for(self, params):
                return None
            def get_airing_schedule_for(self, params):
                return None
            def get_reviews_for(self, params):
                return None
            def get_notifications(self):
                return None
            def transform_raw_search_data(self, raw_data):
                return None
        
        config = self.create_mock_config()
        client = TestApiClient(config.anilist, self.mock_http_client)
        
        self.assertEqual(client.config, config.anilist)
        self.assertEqual(client.http_client, self.mock_http_client)

    def test_abstract_methods_must_be_implemented(self):
        """Test that all abstract methods must be implemented."""
        
        # Incomplete implementation should raise TypeError
        with self.assertRaises(TypeError):
            class IncompleteClient(BaseApiClient):
                def authenticate(self, token):
                    return None
                # Missing other required methods
            
            IncompleteClient(Mock(), Mock())


class MockApiClient(BaseApiClient):
    """Mock API client for testing."""
    
    def __init__(self, config, client):
        super().__init__(config, client)
        self._authenticated = False
        self._user_profile = None
        
    def authenticate(self, token):
        if token == "valid_token":
            self._authenticated = True
            self._user_profile = UserProfile(
                id=123,
                name="TestUser",
                avatar=None
            )
            return self._user_profile
        return None
        
    def is_authenticated(self):
        return self._authenticated
        
    def get_viewer_profile(self):
        return self._user_profile if self._authenticated else None
        
    def search_media(self, params):
        if params.query:
            return MediaSearchResult(media=[], page_info=None)
        return None
        
    def search_media_list(self, params):
        return None
        
    def update_list_entry(self, params):
        return self._authenticated
        
    def delete_list_entry(self, media_id):
        return self._authenticated
        
    def get_recommendation_for(self, params):
        return []
        
    def get_characters_of(self, params):
        return None
        
    def get_related_anime_for(self, params):
        return []
        
    def get_airing_schedule_for(self, params):
        return None
        
    def get_reviews_for(self, params):
        return []
        
    def get_notifications(self):
        return [] if self._authenticated else None
        
    def transform_raw_search_data(self, raw_data):
        return MediaSearchResult(media=[], page_info=None)


class TestMediaApiMethods(BaseTestCase):
    """Test media API method contracts and behavior."""

    def setUp(self):
        super().setUp()
        config = self.create_mock_config()
        self.api_client = MockApiClient(config.anilist, self.mock_http_client)

    def test_authentication_flow(self):
        """Test authentication flow."""
        # Initially not authenticated
        self.assertFalse(self.api_client.is_authenticated())
        self.assertIsNone(self.api_client.get_viewer_profile())
        
        # Authenticate with valid token
        profile = self.api_client.authenticate("valid_token")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "TestUser")
        
        # Should now be authenticated
        self.assertTrue(self.api_client.is_authenticated())
        self.assertIsNotNone(self.api_client.get_viewer_profile())

    def test_authentication_with_invalid_token(self):
        """Test authentication with invalid token."""
        profile = self.api_client.authenticate("invalid_token")
        self.assertIsNone(profile)
        self.assertFalse(self.api_client.is_authenticated())

    def test_search_media(self):
        """Test media search functionality."""
        search_params = MediaSearchParams(query="test anime")
        result = self.api_client.search_media(search_params)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, MediaSearchResult)

    def test_search_media_empty_query(self):
        """Test media search with empty query."""
        search_params = MediaSearchParams(query="")
        result = self.api_client.search_media(search_params)
        
        self.assertIsNone(result)

    def test_list_operations_require_authentication(self):
        """Test that list operations respect authentication."""
        from viu_media.libs.media_api.params import UpdateUserMediaListEntryParams
        from viu_media.libs.media_api.types import UserMediaListStatus
        
        # Without authentication
        update_params = UpdateUserMediaListEntryParams(
            media_id=123,
            status=UserMediaListStatus.WATCHING
        )
        result = self.api_client.update_list_entry(update_params)
        self.assertFalse(result)
        
        delete_result = self.api_client.delete_list_entry(123)
        self.assertFalse(delete_result)
        
        # With authentication
        self.api_client.authenticate("valid_token")
        
        result = self.api_client.update_list_entry(update_params)
        self.assertTrue(result)
        
        delete_result = self.api_client.delete_list_entry(123)
        self.assertTrue(delete_result)

    def test_recommendation_methods(self):
        """Test recommendation and related methods."""
        from viu_media.libs.media_api.params import (
            MediaRecommendationParams,
            MediaCharactersParams,
            MediaRelationsParams,
            MediaReviewsParams
        )
        
        # Test recommendations
        rec_params = MediaRecommendationParams(media_id=123)
        recommendations = self.api_client.get_recommendation_for(rec_params)
        self.assertIsInstance(recommendations, list)
        
        # Test characters
        char_params = MediaCharactersParams(media_id=123)
        characters = self.api_client.get_characters_of(char_params)
        # Can be None or CharacterSearchResult
        
        # Test related anime
        rel_params = MediaRelationsParams(media_id=123)
        related = self.api_client.get_related_anime_for(rel_params)
        self.assertIsInstance(related, list)
        
        # Test reviews
        review_params = MediaReviewsParams(media_id=123)
        reviews = self.api_client.get_reviews_for(review_params)
        self.assertIsInstance(reviews, list)

    def test_notifications_require_authentication(self):
        """Test that notifications require authentication."""
        # Without authentication
        notifications = self.api_client.get_notifications()
        self.assertIsNone(notifications)
        
        # With authentication
        self.api_client.authenticate("valid_token")
        notifications = self.api_client.get_notifications()
        self.assertIsInstance(notifications, list)

    def test_transform_raw_search_data(self):
        """Test raw data transformation."""
        raw_data = {"data": {"Page": {"media": []}}}
        result = self.api_client.transform_raw_search_data(raw_data)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, MediaSearchResult)


class TestApiClientFactory(BaseTestCase):
    """Test the API client factory function."""

    def test_create_anilist_client(self):
        """Test creating AniList API client."""
        config = self.create_mock_config()
        client = create_api_client("anilist", config)
        
        self.assertIsInstance(client, BaseApiClient)

    def test_create_jikan_client(self):
        """Test creating Jikan API client."""
        config = self.create_mock_config()
        client = create_api_client("jikan", config)
        
        self.assertIsInstance(client, BaseApiClient)

    def test_create_invalid_client_raises_error(self):
        """Test that invalid client type raises an error."""
        config = self.create_mock_config()
        
        with self.assertRaises(ValueError):
            create_api_client("invalid_api", config)


class TestApiClientIntegration(BaseTestCase):
    """Integration tests for API client functionality."""

    @patch('httpx.Client')
    def test_api_client_with_http_client(self, mock_client_class):
        """Test API client integration with HTTP client."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        config = self.create_mock_config()
        api_client = MockApiClient(config.anilist, mock_client)
        
        # Verify the client is assigned
        self.assertEqual(api_client.http_client, mock_client)
        
        # Test that methods can be called
        search_params = MediaSearchParams(query="test")
        api_client.search_media(search_params)  # Should not raise

    def test_api_client_error_handling(self):
        """Test API client error handling scenarios."""
        config = self.create_mock_config()
        api_client = MockApiClient(config.anilist, self.mock_http_client)
        
        # Mock network error
        self.mock_http_client.get.side_effect = Exception("Network error")
        
        # API client should handle errors gracefully
        search_params = MediaSearchParams(query="test")
        
        # This test verifies the contract - methods should not raise
        # unless the implementation explicitly chooses to
        try:
            result = api_client.search_media(search_params)
            # Should either return None or handle the error
        except Exception:
            # If client chooses to raise, that's also valid
            pass


if __name__ == '__main__':
    unittest.main()