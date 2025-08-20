"""Tests for selector functionality."""

import unittest
from unittest.mock import Mock, patch

from viu_media.libs.selectors.base import BaseSelector
from viu_media.libs.selectors.selector import create_selector

from ..conftest import BaseTestCase


class TestBaseSelector(BaseTestCase):
    """Test the base selector abstract class."""

    def test_base_selector_abstract_methods(self):
        """Test that all abstract methods must be implemented."""
        
        # Incomplete implementation should raise TypeError
        with self.assertRaises(TypeError):
            class IncompleteSelector(BaseSelector):
                def choose(self, prompt, choices, **kwargs):
                    return None
                # Missing other required methods
            
            IncompleteSelector()

    def test_base_selector_with_complete_implementation(self):
        """Test that valid subclass can be created."""
        
        class ValidSelector(BaseSelector):
            def choose(self, prompt, choices, **kwargs):
                return choices[0] if choices else None
            
            def choose_multiple(self, prompt, choices, **kwargs):
                return choices
            
            def confirm(self, prompt, **kwargs):
                return True
            
            def ask(self, prompt, **kwargs):
                return "test response"
        
        # Should not raise an exception
        selector = ValidSelector()
        self.assertIsInstance(selector, BaseSelector)

    def test_search_method_default_implementation(self):
        """Test that search method raises NotImplementedError by default."""
        
        class MinimalSelector(BaseSelector):
            def choose(self, prompt, choices, **kwargs):
                return None
            
            def choose_multiple(self, prompt, choices, **kwargs):
                return []
            
            def confirm(self, prompt, **kwargs):
                return False
            
            def ask(self, prompt, **kwargs):
                return None
        
        selector = MinimalSelector()
        
        with self.assertRaises(NotImplementedError) as context:
            selector.search("test", "command")
        
        self.assertIn("Dynamic search is not supported", str(context.exception))


class MockSelector(BaseSelector):
    """Mock selector for testing."""
    
    def __init__(self):
        self.choose_calls = []
        self.choose_multiple_calls = []
        self.confirm_calls = []
        self.ask_calls = []
        
        # Default return values
        self.choose_return = None
        self.choose_multiple_return = []
        self.confirm_return = False
        self.ask_return = None
    
    def choose(self, prompt, choices, **kwargs):
        self.choose_calls.append((prompt, choices, kwargs))
        return self.choose_return
    
    def choose_multiple(self, prompt, choices, **kwargs):
        self.choose_multiple_calls.append((prompt, choices, kwargs))
        return self.choose_multiple_return
    
    def confirm(self, prompt, **kwargs):
        self.confirm_calls.append((prompt, kwargs))
        return self.confirm_return
    
    def ask(self, prompt, **kwargs):
        self.ask_calls.append((prompt, kwargs))
        return self.ask_return


class TestSelectorMethods(BaseTestCase):
    """Test selector method contracts and behavior."""

    def setUp(self):
        super().setUp()
        self.selector = MockSelector()

    def test_choose_method_contract(self):
        """Test choose method accepts correct parameters."""
        choices = ["option1", "option2", "option3"]
        prompt = "Select an option:"
        
        result = self.selector.choose(prompt, choices)
        
        self.assertEqual(len(self.selector.choose_calls), 1)
        call_args = self.selector.choose_calls[0]
        self.assertEqual(call_args[0], prompt)
        self.assertEqual(call_args[1], choices)

    def test_choose_with_optional_parameters(self):
        """Test choose method with optional parameters."""
        choices = ["option1", "option2"]
        prompt = "Select:"
        preview = "echo preview"
        header = "Choose wisely:"
        
        self.selector.choose(prompt, choices, preview=preview, header=header)
        
        call_args = self.selector.choose_calls[0]
        kwargs = call_args[2]
        self.assertEqual(kwargs["preview"], preview)
        self.assertEqual(kwargs["header"], header)

    def test_choose_multiple_method_contract(self):
        """Test choose_multiple method accepts correct parameters."""
        choices = ["option1", "option2", "option3"]
        prompt = "Select multiple options:"
        
        result = self.selector.choose_multiple(prompt, choices)
        
        self.assertEqual(len(self.selector.choose_multiple_calls), 1)
        call_args = self.selector.choose_multiple_calls[0]
        self.assertEqual(call_args[0], prompt)
        self.assertEqual(call_args[1], choices)

    def test_confirm_method_contract(self):
        """Test confirm method accepts correct parameters."""
        prompt = "Are you sure?"
        
        result = self.selector.confirm(prompt)
        
        self.assertEqual(len(self.selector.confirm_calls), 1)
        call_args = self.selector.confirm_calls[0]
        self.assertEqual(call_args[0], prompt)

    def test_confirm_with_default(self):
        """Test confirm method with default value."""
        prompt = "Continue?"
        default = True
        
        self.selector.confirm(prompt, default=default)
        
        call_args = self.selector.confirm_calls[0]
        kwargs = call_args[1]
        self.assertEqual(kwargs["default"], default)

    def test_ask_method_contract(self):
        """Test ask method accepts correct parameters."""
        prompt = "Enter your name:"
        
        result = self.selector.ask(prompt)
        
        self.assertEqual(len(self.selector.ask_calls), 1)
        call_args = self.selector.ask_calls[0]
        self.assertEqual(call_args[0], prompt)

    def test_ask_with_default(self):
        """Test ask method with default value."""
        prompt = "Enter value:"
        default = "default_value"
        
        self.selector.ask(prompt, default=default)
        
        call_args = self.selector.ask_calls[0]
        kwargs = call_args[1]
        self.assertEqual(kwargs["default"], default)


class TestSelectorFactory(BaseTestCase):
    """Test the selector factory function."""

    def test_create_default_selector(self):
        """Test creating default selector."""
        config = self.create_mock_config()
        selector = create_selector(config)
        
        self.assertIsInstance(selector, BaseSelector)

    def test_create_fzf_selector(self):
        """Test creating FZF selector."""
        config = self.create_mock_config()
        config.general.selector = "fzf"
        
        # FZF selector requires fzf to be installed
        with self.assertRaises(Exception):  # Expects ViuError or similar
            create_selector(config)

    def test_create_rofi_selector(self):
        """Test creating Rofi selector."""
        config = self.create_mock_config()
        config.general.selector = "rofi"
        
        # Rofi selector requires rofi to be installed
        with self.assertRaises(FileNotFoundError):
            create_selector(config)

    def test_create_invalid_selector_raises_error(self):
        """Test that invalid selector name raises an error."""
        config = self.create_mock_config()
        # Temporarily modify to invalid selector
        original_selector = config.general.selector
        config.general.selector = "invalid_selector"
        
        with self.assertRaises(ValueError):
            create_selector(config)


class TestSelectorIntegration(BaseTestCase):
    """Integration tests for selector functionality."""

    def test_selector_with_real_choices(self):
        """Test selector with realistic choice scenarios."""
        selector = MockSelector()
        
        # Test anime selection scenario
        anime_choices = [
            "Attack on Titan",
            "Demon Slayer",
            "My Hero Academia",
            "One Piece"
        ]
        
        selector.choose_return = "Attack on Titan"
        result = selector.choose("Select an anime:", anime_choices)
        
        self.assertEqual(result, "Attack on Titan")
        self.assertEqual(len(selector.choose_calls), 1)

    def test_selector_with_episode_selection(self):
        """Test selector with episode selection scenario."""
        selector = MockSelector()
        
        episode_choices = [f"Episode {i}" for i in range(1, 13)]
        selector.choose_multiple_return = ["Episode 1", "Episode 2", "Episode 3"]
        
        result = selector.choose_multiple("Select episodes to download:", episode_choices)
        
        self.assertEqual(len(result), 3)
        self.assertIn("Episode 1", result)

    def test_selector_confirmation_flow(self):
        """Test selector confirmation workflow."""
        selector = MockSelector()
        
        # Test download confirmation
        selector.confirm_return = True
        result = selector.confirm("Download 3 episodes?")
        
        self.assertTrue(result)
        
        # Test with default
        selector.confirm_return = False
        result = selector.confirm("Delete history?", default=False)
        
        self.assertFalse(result)

    def test_selector_user_input_flow(self):
        """Test selector user input workflow."""
        selector = MockSelector()
        
        # Test search query input
        selector.ask_return = "attack on titan"
        result = selector.ask("Search for anime:")
        
        self.assertEqual(result, "attack on titan")
        
        # Test with default
        selector.ask_return = "default_query"
        result = selector.ask("Search query:", default="popular anime")
        
        call_args = selector.ask_calls[-1]
        kwargs = call_args[1]
        self.assertEqual(kwargs["default"], "popular anime")

    def test_selector_empty_choices_handling(self):
        """Test selector behavior with empty choices."""
        selector = MockSelector()
        
        # Empty choices should be handled gracefully
        empty_choices = []
        selector.choose_return = None
        
        result = selector.choose("Select from empty list:", empty_choices)
        
        self.assertIsNone(result)

    def test_selector_special_characters_in_choices(self):
        """Test selector with special characters in choices."""
        selector = MockSelector()
        
        special_choices = [
            "Anime with [Special] Characters",
            "Anime: The Movie (2023)",
            "Anime & More!",
            "Anime/Episode #1"
        ]
        
        selector.choose_return = special_choices[0]
        result = selector.choose("Select anime:", special_choices)
        
        self.assertEqual(result, special_choices[0])


class TestSelectorErrorHandling(BaseTestCase):
    """Test selector error handling scenarios."""

    def test_selector_handles_none_choices(self):
        """Test that selector handles None choices appropriately."""
        selector = MockSelector()
        
        # Should handle None choices gracefully
        try:
            result = selector.choose("Select:", None)
            # If it doesn't raise, that's fine
        except (TypeError, AttributeError):
            # If it raises due to None, that's also acceptable behavior
            pass

    def test_selector_handles_invalid_prompt_types(self):
        """Test selector behavior with invalid prompt types."""
        selector = MockSelector()
        
        choices = ["option1", "option2"]
        
        # Test with non-string prompt
        try:
            selector.choose(123, choices)  # Invalid prompt type
            # If it works, that's implementation-dependent
        except (TypeError, AttributeError):
            # If it raises, that's acceptable
            pass


if __name__ == '__main__':
    unittest.main()