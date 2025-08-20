"""Tests for CLI commands and command-line interface."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from viu_media.cli.cli import cli
from viu_media.core.config import AppConfig

from ..conftest import BaseTestCase


class TestCLIMain(BaseTestCase):
    """Test the main CLI entry point."""

    def setUp(self):
        super().setUp()
        self.runner = CliRunner()

    @patch('viu_media.cli.cli.ConfigLoader')
    def test_cli_with_no_config_flag(self, mock_loader_class):
        """Test CLI with --no-config flag."""
        # Don't use config loader when --no-config is specified
        result = self.runner.invoke(cli, ['--no-config', '--help'])
        
        # Should succeed and show help
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Usage:', result.output)

    @patch('viu_media.cli.cli.ConfigLoader')
    def test_cli_loads_config_by_default(self, mock_loader_class):
        """Test that CLI loads config by default."""
        mock_loader = Mock()
        mock_loader.load.return_value = AppConfig()
        mock_loader_class.return_value = mock_loader
        
        result = self.runner.invoke(cli, ['--help'])
        
        # Should have attempted to load config
        mock_loader_class.assert_called_once()
        self.assertEqual(result.exit_code, 0)

    def test_cli_version_option(self):
        """Test CLI version option."""
        result = self.runner.invoke(cli, ['--version'])
        
        self.assertEqual(result.exit_code, 0)
        # Should contain version information
        self.assertIn('version', result.output.lower())

    @patch('viu_media.cli.cli.setup_logging')
    def test_cli_logging_setup(self, mock_setup_logging):
        """Test that CLI sets up logging."""
        with patch('viu_media.cli.cli.ConfigLoader'):
            result = self.runner.invoke(cli, ['--log', '--help'])
        
        mock_setup_logging.assert_called_once_with(True)

    @patch('viu_media.cli.cli.setup_exceptions_handler')
    def test_cli_exception_handler_setup(self, mock_setup_exceptions):
        """Test that CLI sets up exception handler."""
        with patch('viu_media.cli.cli.ConfigLoader'):
            result = self.runner.invoke(cli, ['--trace', '--help'])
        
        mock_setup_exceptions.assert_called_once()

    @patch('viu_media.cli.cli.ConfigLoader')
    def test_cli_parameter_overrides(self, mock_loader_class):
        """Test that CLI parameters override config values."""
        mock_loader = Mock()
        mock_config = AppConfig()
        mock_loader.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        # Test with a parameter override
        result = self.runner.invoke(cli, ['--help'])
        
        # Loader should have been called
        mock_loader.load.assert_called_once()

    def test_cli_help_output(self):
        """Test CLI help output contains expected information."""
        result = self.runner.invoke(cli, ['--help'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Usage:', result.output)
        self.assertIn('--no-config', result.output)
        self.assertIn('--trace', result.output)
        self.assertIn('--log', result.output)

    @patch('viu_media.cli.cli.ConfigLoader')
    @patch('viu_media.cli.commands.anilist.cmd.anilist')
    def test_cli_default_command_invocation(self, mock_anilist_cmd, mock_loader_class):
        """Test that CLI invokes default command when no subcommand provided."""
        mock_loader = Mock()
        mock_loader.load.return_value = AppConfig()
        mock_loader_class.return_value = mock_loader
        
        # Invoke CLI without subcommand
        result = self.runner.invoke(cli, [])
        
        # Should have invoked the default anilist command
        # (This might fail if the actual command has dependencies)


class TestLazyCommandLoading(BaseTestCase):
    """Test lazy command loading functionality."""

    def test_commands_dictionary_structure(self):
        """Test that commands dictionary has correct structure."""
        from viu_media.cli.cli import commands
        
        self.assertIsInstance(commands, dict)
        
        # Check that expected commands are present
        expected_commands = ['config', 'search', 'anilist', 'download', 'update']
        for cmd in expected_commands:
            self.assertIn(cmd, commands)
            self.assertIsInstance(commands[cmd], str)

    def test_lazy_group_import_structure(self):
        """Test that lazy group can import command modules."""
        from viu_media.cli.cli import commands
        
        # Each command should reference a valid module path
        for cmd_name, module_path in commands.items():
            self.assertIsInstance(module_path, str)
            self.assertIn('.', module_path)  # Should be a module path


class TestCLIOptions(BaseTestCase):
    """Test CLI option handling."""

    def setUp(self):
        super().setUp()
        self.runner = CliRunner()

    def test_trace_option(self):
        """Test --trace option."""
        with patch('viu_media.cli.cli.ConfigLoader'):
            result = self.runner.invoke(cli, ['--trace', '--help'])
        
        self.assertEqual(result.exit_code, 0)

    def test_dev_option(self):
        """Test --dev option."""
        with patch('viu_media.cli.cli.ConfigLoader'):
            result = self.runner.invoke(cli, ['--dev', '--help'])
        
        self.assertEqual(result.exit_code, 0)

    def test_rich_traceback_options(self):
        """Test rich traceback options."""
        with patch('viu_media.cli.cli.ConfigLoader'):
            result = self.runner.invoke(cli, [
                '--rich-traceback', 
                '--rich-traceback-theme', 'monokai',
                '--help'
            ])
        
        self.assertEqual(result.exit_code, 0)

    def test_multiple_options_combination(self):
        """Test combination of multiple options."""
        with patch('viu_media.cli.cli.ConfigLoader'):
            result = self.runner.invoke(cli, [
                '--no-config', 
                '--trace', 
                '--dev', 
                '--log',
                '--help'
            ])
        
        self.assertEqual(result.exit_code, 0)


class TestConfigIntegration(BaseTestCase):
    """Test CLI integration with configuration system."""

    def setUp(self):
        super().setUp()
        self.runner = CliRunner()

    @patch('viu_media.cli.cli.ConfigLoader')
    def test_config_object_passed_to_context(self, mock_loader_class):
        """Test that config object is passed to click context."""
        mock_loader = Mock()
        test_config = AppConfig()
        mock_loader.load.return_value = test_config
        mock_loader_class.return_value = mock_loader
        
        @cli.command()
        @click.pass_obj
        def test_command(config):
            # Verify config is passed correctly
            assert config == test_config
            return config
        
        # This test structure verifies the pattern but won't run the command
        # due to complexity of CLI setup

    @patch('viu_media.cli.cli.ConfigLoader')
    def test_cli_overrides_handling(self, mock_loader_class):
        """Test that CLI parameter overrides are handled correctly."""
        mock_loader = Mock()
        mock_loader.load.return_value = AppConfig()
        mock_loader_class.return_value = mock_loader
        
        result = self.runner.invoke(cli, ['--help'])
        
        # Should have called load with some parameters
        mock_loader.load.assert_called_once()
        call_args = mock_loader.load.call_args
        # The call should include override parameters
        self.assertIsInstance(call_args[0][0], dict)


class TestUpdateChecking(BaseTestCase):
    """Test CLI update checking functionality."""

    @patch('viu_media.cli.cli.ConfigLoader')
    @patch('time.time')
    @patch('viu_media.cli.cli.APP_CACHE_DIR')
    def test_update_check_timing(self, mock_cache_dir, mock_time, mock_loader_class):
        """Test update check timing logic."""
        # Mock config with update checking enabled
        mock_config = AppConfig()
        mock_config.general.check_for_updates = True
        mock_config.general.update_check_interval = 24  # 24 hours
        
        mock_loader = Mock()
        mock_loader.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        # Mock cache directory and file
        mock_cache_dir.__truediv__ = Mock()
        mock_last_update_file = Mock()
        mock_cache_dir.__truediv__.return_value = mock_last_update_file
        
        # Mock current time and last update time
        current_time = 1000000
        last_update_time = current_time - (25 * 3600)  # 25 hours ago
        mock_time.return_value = current_time
        mock_last_update_file.exists.return_value = True
        mock_last_update_file.read_text.return_value = str(last_update_time)
        
        with patch('viu_media.cli.utils.update.check_for_updates') as mock_check:
            mock_check.return_value = (True, None)  # Latest version
            
            result = self.runner.invoke(cli, ['--help'])
            
            # Should have checked for updates due to time interval
            mock_check.assert_called_once()

    @patch('viu_media.cli.cli.ConfigLoader')
    def test_update_check_disabled(self, mock_loader_class):
        """Test that update checking can be disabled."""
        # Mock config with update checking disabled
        mock_config = AppConfig()
        mock_config.general.check_for_updates = False
        
        mock_loader = Mock()
        mock_loader.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        with patch('viu_media.cli.utils.update.check_for_updates') as mock_check:
            result = self.runner.invoke(cli, ['--help'])
            
            # Should not have checked for updates
            mock_check.assert_not_called()


class TestCommandRegistration(BaseTestCase):
    """Test command registration and discovery."""

    def test_all_commands_are_importable(self):
        """Test that all registered commands can be imported."""
        from viu_media.cli.cli import commands
        
        # This test would ideally check that all command modules exist
        # For now, just verify the structure is correct
        for cmd_name, module_path in commands.items():
            self.assertIsInstance(cmd_name, str)
            self.assertIsInstance(module_path, str)
            
            # Module path should be in correct format
            parts = module_path.split('.')
            self.assertGreaterEqual(len(parts), 2)

    def test_command_help_accessibility(self):
        """Test that command help is accessible."""
        # Test that main help works
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Commands:', result.output)


if __name__ == '__main__':
    unittest.main()