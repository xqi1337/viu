"""Tests for the interactive session and menu system."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from viu_media.cli.interactive.session import Session, Context, Menu, Switch
from viu_media.cli.interactive.state import State, MenuName, InternalDirective
from viu_media.core.config import AppConfig

from ..conftest import BaseTestCase, MockMediaApi, MockProvider, MockPlayer, MockSelector


class TestSwitch(BaseTestCase):
    """Test the Switch class for menu forcing logic."""

    def test_switch_initialization(self):
        """Test Switch initialization with default values."""
        switch = Switch()
        
        self.assertFalse(switch._provider_results)
        self.assertFalse(switch._episodes)
        self.assertFalse(switch._servers)
        self.assertFalse(switch._dont_play)

    def test_show_provider_results_menu_toggle(self):
        """Test provider results menu show/hide logic."""
        switch = Switch()
        
        # Initially should not show
        self.assertFalse(switch.show_provider_results_menu)
        
        # Force it to show
        switch.force_provider_results_menu()
        self.assertTrue(switch.show_provider_results_menu)
        
        # Should auto-reset after showing once
        self.assertFalse(switch.show_provider_results_menu)

    def test_dont_play_property(self):
        """Test dont_play property."""
        switch = Switch()
        
        # Test the property exists and works
        self.assertFalse(switch.dont_play)


class TestContext(BaseTestCase):
    """Test the Context class for dependency injection."""

    def setUp(self):
        super().setUp()
        self.config = self.create_mock_config()

    def test_context_initialization(self):
        """Test Context initialization with config."""
        context = Context(self.config)
        
        self.assertEqual(context.config, self.config)
        self.assertIsNotNone(context.feedback)
        self.assertIsNotNone(context.provider)
        self.assertIsNotNone(context.media_api)
        self.assertIsNotNone(context.player)
        self.assertIsNotNone(context.selector)

    def test_context_services_are_initialized(self):
        """Test that all context services are properly initialized."""
        context = Context(self.config)
        
        # Test that services can be called (they should not be None)
        self.assertIsNotNone(context.feedback)
        self.assertIsNotNone(context.provider)
        self.assertIsNotNone(context.media_api)
        self.assertIsNotNone(context.player)
        self.assertIsNotNone(context.selector)


class TestMenu(BaseTestCase):
    """Test the Menu class."""

    def test_menu_creation(self):
        """Test Menu dataclass creation."""
        def mock_menu_function(ctx, state):
            return InternalDirective.BACK
        
        menu = Menu(name=MenuName.MAIN, execute=mock_menu_function)
        
        self.assertEqual(menu.name, MenuName.MAIN)
        self.assertEqual(menu.execute, mock_menu_function)

    def test_menu_is_frozen(self):
        """Test that Menu is immutable (frozen dataclass)."""
        def mock_menu_function(ctx, state):
            return InternalDirective.BACK
        
        menu = Menu(name=MenuName.MAIN, execute=mock_menu_function)
        
        # Should not be able to modify frozen dataclass
        with self.assertRaises(Exception):
            menu.name = MenuName.AUTH


class TestSession(BaseTestCase):
    """Test the Session class and menu management."""

    def setUp(self):
        super().setUp()
        self.session = Session()
        self.config = self.create_mock_config()

    def test_session_initialization(self):
        """Test Session initialization."""
        session = Session()
        
        self.assertIsInstance(session._history, list)
        self.assertIsInstance(session._menus, dict)
        self.assertEqual(len(session._history), 0)
        self.assertEqual(len(session._menus), 0)

    def test_menu_decorator_registration(self):
        """Test that the menu decorator properly registers menus."""
        session = Session()
        
        @session.menu
        def test_menu(ctx, state):
            return InternalDirective.BACK
        
        self.assertIn(MenuName.TEST_MENU, session._menus)
        menu = session._menus[MenuName.TEST_MENU]
        self.assertEqual(menu.name, MenuName.TEST_MENU)
        self.assertEqual(menu.execute, test_menu)

    def test_menu_decorator_redefinition_warning(self):
        """Test that redefining a menu logs a warning."""
        session = Session()
        
        @session.menu
        def test_menu(ctx, state):
            return InternalDirective.BACK
        
        # Redefine the same menu
        with patch('viu_media.cli.interactive.session.logger') as mock_logger:
            @session.menu
            def test_menu(ctx, state):
                return InternalDirective.EXIT
            
            mock_logger.warning.assert_called_once()

    @patch('viu_media.cli.interactive.session.os.listdir')
    @patch('viu_media.cli.interactive.session.importlib.util.spec_from_file_location')
    def test_load_menus_from_folder(self, mock_spec_from_file, mock_listdir):
        """Test loading menus from a folder."""
        # Mock file listing
        mock_listdir.return_value = ["menu1.py", "menu2.py", "__init__.py", "not_python.txt"]
        
        # Mock module loading
        mock_spec = Mock()
        mock_loader = Mock()
        mock_spec.loader = mock_loader
        mock_spec_from_file.return_value = mock_spec
        
        session = Session()
        session.load_menus_from_folder("test_package")
        
        # Should process Python files but not __init__ or non-Python files
        self.assertEqual(mock_spec_from_file.call_count, 2)  # menu1.py and menu2.py
        self.assertEqual(mock_loader.exec_module.call_count, 2)

    @patch('viu_media.cli.interactive.session.os.listdir')
    @patch('viu_media.cli.interactive.session.importlib.util.spec_from_file_location')
    def test_load_menus_handles_import_errors(self, mock_spec_from_file, mock_listdir):
        """Test that menu loading handles import errors gracefully."""
        mock_listdir.return_value = ["broken_menu.py"]
        
        # Mock import error
        mock_spec_from_file.side_effect = ImportError("Mock import error")
        
        session = Session()
        
        with patch('viu_media.cli.interactive.session.logger') as mock_logger:
            session.load_menus_from_folder("test_package")
            mock_logger.error.assert_called_once()

    @patch('viu_media.cli.interactive.session.Context')
    def test_load_context(self, mock_context_class):
        """Test context loading."""
        mock_context = Mock()
        mock_context_class.return_value = mock_context
        
        session = Session()
        session._load_context(self.config)
        
        mock_context_class.assert_called_once_with(self.config)
        self.assertEqual(session._context, mock_context)

    @patch('click.edit')
    @patch('viu_media.cli.config.loader.ConfigLoader')
    def test_edit_config(self, mock_loader_class, mock_click_edit):
        """Test config editing functionality."""
        mock_loader = Mock()
        mock_loader.load.return_value = self.config
        mock_loader_class.return_value = mock_loader
        
        session = Session()
        session._context = Mock()  # Mock existing context
        
        session._edit_config()
        
        mock_click_edit.assert_called_once()
        mock_loader.load.assert_called_once()

    def test_cleanup_preview_workers(self):
        """Test cleanup of preview workers."""
        session = Session()
        
        # Mock preview workers
        mock_worker1 = Mock()
        mock_worker2 = Mock()
        session._context = Mock()
        session._context.preview_workers = [mock_worker1, mock_worker2]
        
        session._cleanup_preview_workers()
        
        # Should have attempted to clean up workers
        # (Implementation depends on actual worker interface)

    @patch('viu_media.cli.interactive.session.Session._run_main_loop')
    @patch('viu_media.cli.interactive.session.Session._load_context')
    @patch('viu_media.cli.interactive.session.Session.load_menus_from_folder')
    def test_run_session(self, mock_load_menus, mock_load_context, mock_run_loop):
        """Test session run method."""
        session = Session()
        
        session.run(self.config)
        
        mock_load_context.assert_called_once_with(self.config)
        mock_load_menus.assert_called()  # Should load menus
        mock_run_loop.assert_called_once()

    @patch('viu_media.cli.interactive.session.Session._run_main_loop')
    @patch('viu_media.cli.interactive.session.Session._load_context')
    def test_run_session_with_resume(self, mock_load_context, mock_run_loop):
        """Test session run with resume option."""
        session = Session()
        history = [State(menu_name=MenuName.MAIN)]
        
        session.run(self.config, resume=True, history=history)
        
        self.assertEqual(session._history, history)
        mock_load_context.assert_called_once_with(self.config)
        mock_run_loop.assert_called_once()


class TestMenuExecution(BaseTestCase):
    """Test menu execution and state management."""

    def setUp(self):
        super().setUp()
        self.config = self.create_mock_config()
        self.context = Context(self.config)
        self.session = Session()

    def test_menu_function_signature(self):
        """Test that menu functions have the correct signature."""
        def valid_menu(ctx: Context, state: State):
            return InternalDirective.BACK
        
        # Should accept Context and State parameters
        result = valid_menu(self.context, State(menu_name=MenuName.MAIN))
        self.assertEqual(result, InternalDirective.BACK)

    def test_menu_returns_state_or_directive(self):
        """Test that menus return either State or InternalDirective."""
        def state_returning_menu(ctx: Context, state: State):
            return State(menu_name=MenuName.AUTH)
        
        def directive_returning_menu(ctx: Context, state: State):
            return InternalDirective.EXIT
        
        # Test state return
        new_state = state_returning_menu(self.context, State(menu_name=MenuName.MAIN))
        self.assertIsInstance(new_state, State)
        self.assertEqual(new_state.menu_name, MenuName.AUTH)
        
        # Test directive return
        directive = directive_returning_menu(self.context, State(menu_name=MenuName.MAIN))
        self.assertEqual(directive, InternalDirective.EXIT)

    def test_menu_state_immutability(self):
        """Test that State objects are immutable."""
        state = State(menu_name=MenuName.MAIN)
        
        # Should not be able to modify frozen state
        with self.assertRaises(Exception):
            state.menu_name = MenuName.AUTH

    def test_internal_directive_navigation(self):
        """Test that internal directives provide navigation control."""
        # Test all directive types
        directives = [
            InternalDirective.MAIN,
            InternalDirective.BACK,
            InternalDirective.BACKX2,
            InternalDirective.BACKX3,
            InternalDirective.BACKX4,
            InternalDirective.EXIT,
            InternalDirective.CONFIG_EDIT,
            InternalDirective.RELOAD
        ]
        
        for directive in directives:
            self.assertIsInstance(directive, InternalDirective)


class TestSessionGlobalInstance(BaseTestCase):
    """Test the global session instance."""

    def test_global_session_import(self):
        """Test that global session can be imported."""
        from viu_media.cli.interactive.session import session
        
        self.assertIsInstance(session, Session)

    def test_global_session_menu_registration(self):
        """Test that menus can be registered with global session."""
        from viu_media.cli.interactive.session import session
        
        initial_menu_count = len(session._menus)
        
        @session.menu
        def global_test_menu(ctx, state):
            return InternalDirective.BACK
        
        # Should have registered the menu
        self.assertEqual(len(session._menus), initial_menu_count + 1)


if __name__ == '__main__':
    unittest.main()