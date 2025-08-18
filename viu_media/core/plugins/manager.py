"""Plugin manager for viu.

This module contains the PluginManager singleton that handles all plugin operations
including loading, discovery, installation, and removal.
"""

import importlib.util
import logging
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Set, Union

import tomli_w
from pydantic import ValidationError

from ..constants import PLUGINS_CONFIG, PLUGINS_DIR, PLUGINS_MANIFEST
from .model import InstalledPlugin, PluginInfo, PluginManifest
from viu_media.core.exceptions import ViuError
logger = logging.getLogger(__name__)

ComponentType = Literal["provider", "player", "selector", "command"]


class PluginError(ViuError):
    """Base exception for plugin-related errors."""
    pass


class PluginNotFoundError(ViuError):
    """Raised when a requested plugin is not found."""
    pass


class PluginLoadError(ViuError):
    """Raised when a plugin fails to load."""
    pass


class PluginManager:
    """Manages the plugin system for viu.
    
    This is a singleton class that handles:
    - Loading and caching plugins
    - Installing and removing plugins from Git repositories
    - Managing plugin configurations
    - Discovering available plugins
    """
    
    _instance: Optional["PluginManager"] = None
    _initialized: bool = False
    
    def __new__(cls) -> "PluginManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
            
        self._loaded_components: Dict[str, Any] = {}
        self._manifest: PluginManifest = PluginManifest()
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}
        
        self._load_manifest()
        self._load_plugin_configs()
        
        self._initialized = True
    
    def load_component(self, component_type: ComponentType, name: str) -> Any:
        """Lazy-load a plugin component by type and name.
        
        Args:
            component_type: Type of component (provider, player, selector, command)
            name: Name of the component to load
            
        Returns:
            The loaded component instance or function
            
        Raises:
            PluginNotFoundError: If the plugin is not installed
            PluginLoadError: If the plugin fails to load
        """
        cache_key = f"{component_type}:{name}"
        
        # Return cached component if already loaded
        if cache_key in self._loaded_components:
            return self._loaded_components[cache_key]
        
        # Find the plugin in the manifest
        plugins_of_type = getattr(self._manifest, f"{component_type}s")
        if name not in plugins_of_type:
            raise PluginNotFoundError(
                f"Plugin '{name}' of type '{component_type}' is not installed"
            )
        
        plugin_entry = plugins_of_type[name]
        plugin_path = plugin_entry.path
        
        if not plugin_path.exists():
            raise PluginLoadError(
                f"Plugin path does not exist: {plugin_path}"
            )
        
        # Load plugin info to get component definition
        try:
            plugin_info = self._get_plugin_info(plugin_path)
        except PluginError as e:
            raise PluginLoadError(f"Failed to load plugin info: {e}") from e
        
        # Get the component definition
        component_def = getattr(plugin_info.components, component_type)
        if not component_def:
            raise PluginLoadError(
                f"Plugin '{name}' does not provide a {component_type} component"
            )
        
        # Parse module:class format
        if ":" not in component_def:
            raise PluginLoadError(
                f"Invalid component definition: {component_def}"
            )
        
        module_name, class_name = component_def.split(":", 1)
        
        # Load the module
        module_path = plugin_path / f"{module_name}.py"
        if not module_path.exists():
            raise PluginLoadError(f"Plugin module not found: {module_path}")
        
        try:
            spec = importlib.util.spec_from_file_location(
                f"plugin_{name}_{module_name}", module_path
            )
            if spec is None or spec.loader is None:
                raise PluginLoadError(f"Could not create module spec for {module_path}")
            
            module = importlib.util.module_from_spec(spec)
            
            # Add plugin path to sys.path temporarily for relative imports
            sys.path.insert(0, str(plugin_path))
            try:
                spec.loader.exec_module(module)
            finally:
                sys.path.remove(str(plugin_path))
            
        except Exception as e:
            raise PluginLoadError(f"Failed to load module {module_path}: {e}") from e
        
        # Get the component class/function
        if not hasattr(module, class_name):
            raise PluginLoadError(
                f"Module {module_name} does not have {class_name}"
            )
        
        component_cls = getattr(module, class_name)
        
        # For providers, players, and selectors, instantiate with config
        if component_type in ("provider", "player", "selector"):
            plugin_config = self._plugin_configs.get(name, {})
            
            # For providers, also inject httpx client like the built-in system
            if component_type == "provider":
                from ...core.utils.networking import random_user_agent
                from httpx import Client
                
                headers = getattr(component_cls, "HEADERS", {})
                client = Client(
                    headers={"User-Agent": random_user_agent(), **headers}
                )
                
                try:
                    component = component_cls(client, **plugin_config)
                except TypeError:
                    # Fallback if constructor doesn't accept config
                    component = component_cls(client)
            else:
                try:
                    component = component_cls(**plugin_config)
                except TypeError:
                    # Fallback if constructor doesn't accept config
                    component = component_cls()
        else:
            # For commands, just return the function
            component = component_cls
        
        # Cache and return
        self._loaded_components[cache_key] = component
        logger.debug(f"Loaded plugin component: {cache_key}")
        return component
    
    def add_plugin(
        self, 
        component_type: ComponentType, 
        name: str, 
        source: str,
        force: bool = False
    ) -> None:
        """Install a plugin from a Git repository.
        
        Args:
            component_type: Type of component the plugin provides
            name: Local name for the plugin
            source: Git source (e.g., "github:user/repo")
            force: Whether to overwrite existing plugin
            
        Raises:
            PluginError: If installation fails
        """
        plugins_of_type = getattr(self._manifest, f"{component_type}s")
        
        # Check if plugin already exists
        if name in plugins_of_type and not force:
            raise PluginError(
                f"Plugin '{name}' already exists. Use --force to overwrite."
            )
        
        # Determine installation path
        plugin_dir = PLUGINS_DIR / f"{component_type}s" / name
        
        # Remove existing if force is True
        if plugin_dir.exists():
            if force:
                shutil.rmtree(plugin_dir)
            else:
                raise PluginError(f"Plugin directory already exists: {plugin_dir}")
        
        # Create parent directory
        plugin_dir.parent.mkdir(parents=True, exist_ok=True)
        
        # Clone the repository
        self._clone_plugin(source, plugin_dir)
        
        # Validate plugin structure
        try:
            plugin_info = self._get_plugin_info(plugin_dir)
        except PluginError:
            # Clean up on validation failure
            shutil.rmtree(plugin_dir)
            raise
        
        # Ensure plugin provides the expected component type
        expected_component = getattr(plugin_info.components, component_type)
        if not expected_component:
            shutil.rmtree(plugin_dir)
            raise PluginError(
                f"Plugin does not provide a {component_type} component"
            )
        
        # Add to manifest
        plugins_of_type[name] = InstalledPlugin(
            source=source,
            path=plugin_dir,
            version=plugin_info.plugin.version
        )
        
        # Save manifest
        self._save_manifest()
        
        # Copy default config if it exists
        self._install_default_config(name, plugin_dir)
        
        logger.info(f"Successfully installed {component_type} plugin '{name}'")
    
    def remove_plugin(self, component_type: ComponentType, name: str) -> None:
        """Remove an installed plugin.
        
        Args:
            component_type: Type of component
            name: Name of the plugin to remove
            
        Raises:
            PluginNotFoundError: If plugin is not installed
            PluginError: If removal fails
        """
        plugins_of_type = getattr(self._manifest, f"{component_type}s")
        
        if name not in plugins_of_type:
            raise PluginNotFoundError(
                f"Plugin '{name}' of type '{component_type}' is not installed"
            )
        
        plugin_entry = plugins_of_type[name]
        plugin_path = plugin_entry.path
        
        # Remove from filesystem
        if plugin_path.exists():
            try:
                shutil.rmtree(plugin_path)
            except OSError as e:
                raise PluginError(f"Failed to remove plugin directory: {e}") from e
        
        # Remove from manifest
        del plugins_of_type[name]
        
        # Remove from loaded components cache
        cache_key = f"{component_type}:{name}"
        self._loaded_components.pop(cache_key, None)
        
        # Save manifest
        self._save_manifest()
        
        logger.info(f"Successfully removed {component_type} plugin '{name}'")
    
    def update_plugin(self, component_type: ComponentType, name: str) -> None:
        """Update an installed plugin by pulling from Git.
        
        Args:
            component_type: Type of component
            name: Name of the plugin to update
            
        Raises:
            PluginNotFoundError: If plugin is not installed
            PluginError: If update fails
        """
        plugins_of_type = getattr(self._manifest, f"{component_type}s")
        
        if name not in plugins_of_type:
            raise PluginNotFoundError(
                f"Plugin '{name}' of type '{component_type}' is not installed"
            )
        
        plugin_entry = plugins_of_type[name]
        plugin_path = plugin_entry.path
        
        if not plugin_path.exists():
            raise PluginError(f"Plugin path does not exist: {plugin_path}")
        
        # Pull latest changes
        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd=plugin_path,
                check=True,
                capture_output=True,
                text=True
            )
            logger.debug(f"Git pull output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            raise PluginError(f"Failed to update plugin: {e.stderr}") from e
        except FileNotFoundError:
            raise PluginError("Git is not installed or not in PATH") from None
        
        # Update version in manifest
        try:
            plugin_info = self._get_plugin_info(plugin_path)
            plugin_entry.version = plugin_info.plugin.version
            self._save_manifest()
        except PluginError as e:
            logger.warning(f"Could not update plugin version: {e}")
        
        # Clear from cache to force reload
        cache_key = f"{component_type}:{name}"
        self._loaded_components.pop(cache_key, None)
        
        logger.info(f"Successfully updated {component_type} plugin '{name}'")
    
    def list_plugins(self) -> Dict[ComponentType, Dict[str, InstalledPlugin]]:
        """List all installed plugins grouped by type.
        
        Returns:
            Dictionary mapping component types to their installed plugins
        """
        return {
            "provider": dict(self._manifest.providers),
            "player": dict(self._manifest.players),
            "selector": dict(self._manifest.selectors),
            "command": dict(self._manifest.commands),
        }
    
    def get_available_components(self, component_type: ComponentType) -> Set[str]:
        """Get names of all available components of a given type.
        
        This includes both built-in components and installed plugins.
        
        Args:
            component_type: Type of component
            
        Returns:
            Set of component names
        """
        # Get plugin names
        plugins_of_type = getattr(self._manifest, f"{component_type}s")
        plugin_names = set(plugins_of_type.keys())
        
        # Add built-in component names
        if component_type == "provider":
            from ...libs.provider.anime.provider import PROVIDERS_AVAILABLE
            builtin_names = set(PROVIDERS_AVAILABLE.keys())
        elif component_type == "player":
            from ...libs.player.player import PLAYERS
            builtin_names = set(PLAYERS)
        elif component_type == "selector":
            from ...libs.selectors.selector import SELECTORS
            builtin_names = set(SELECTORS)
        elif component_type == "command":
            # Commands would need to be handled differently as they're registered in CLI
            builtin_names = set()
        else:
            builtin_names = set()
        
        return plugin_names | builtin_names
    
    def is_plugin(self, component_type: ComponentType, name: str) -> bool:
        """Check if a component is provided by a plugin.
        
        Args:
            component_type: Type of component
            name: Name of the component
            
        Returns:
            True if it's a plugin, False if it's built-in
        """
        plugins_of_type = getattr(self._manifest, f"{component_type}s")
        return name in plugins_of_type
    
    def _load_manifest(self) -> None:
        """Load the plugins.toml manifest file."""
        if not PLUGINS_MANIFEST.exists():
            logger.debug("No plugins manifest found, creating empty one")
            self._save_manifest()
            return
            
        try:
            with open(PLUGINS_MANIFEST, "rb") as f:
                data = tomllib.load(f)
            self._manifest = PluginManifest.model_validate(data)
            logger.debug(f"Loaded plugins manifest with {len(self.list_plugins())} plugins")
        except (OSError, ValidationError, tomllib.TOMLDecodeError) as e:
            logger.error(f"Failed to load plugins manifest: {e}")
            self._manifest = PluginManifest()
    
    def _save_manifest(self) -> None:
        """Save the current manifest to plugins.toml."""
        try:
            # Convert Path objects to strings for TOML serialization
            manifest_dict = self._manifest.model_dump()
            
            # Convert all Path objects to strings
            def convert_paths(obj: Any) -> Any:
                if isinstance(obj, dict):
                    return {k: convert_paths(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_paths(item) for item in obj]
                elif isinstance(obj, Path):
                    return str(obj)
                else:
                    return obj
            
            manifest_dict = convert_paths(manifest_dict)
            
            with open(PLUGINS_MANIFEST, "wb") as f:
                tomli_w.dump(manifest_dict, f)
            logger.debug("Saved plugins manifest")
        except OSError as e:
            logger.error(f"Failed to save plugins manifest: {e}")
            raise PluginError(f"Could not save plugins manifest: {e}") from e
    
    def _load_plugin_configs(self) -> None:
        """Load plugin configurations from plugins.config.toml."""
        if not PLUGINS_CONFIG.exists():
            logger.debug("No plugin configs found")
            return
            
        try:
            with open(PLUGINS_CONFIG, "rb") as f:
                self._plugin_configs = tomllib.load(f)
            logger.debug(f"Loaded configs for {len(self._plugin_configs)} plugins")
        except (OSError, tomllib.TOMLDecodeError) as e:
            logger.error(f"Failed to load plugin configs: {e}")
            self._plugin_configs = {}
    
    def _get_plugin_info(self, plugin_path: Path) -> PluginInfo:
        """Load and validate plugin.info.toml from a plugin directory."""
        info_file = plugin_path / "plugin.info.toml"
        if not info_file.exists():
            raise PluginError(f"Plugin info file not found: {info_file}")
        
        try:
            with open(info_file, "rb") as f:
                data = tomllib.load(f)
            return PluginInfo.model_validate(data)
        except (OSError, ValidationError, tomllib.TOMLDecodeError) as e:
            raise PluginError(f"Invalid plugin info file {info_file}: {e}") from e
    
    def _parse_git_source(self, source: str) -> tuple[str, str]:
        """Parse a git source string into platform and repo.
        
        Examples:
            "github:user/repo" -> ("github.com", "user/repo")
            "gitlab:user/repo" -> ("gitlab.com", "user/repo")
            "https://github.com/user/repo" -> ("github.com", "user/repo")
            "/path/to/local/repo" -> ("local", "/path/to/local/repo")
            "file:///path/to/repo" -> ("local", "/path/to/repo")
        """
        # Handle local file paths
        if source.startswith("file://"):
            return "local", source[7:]  # Remove file:// prefix
        elif source.startswith("/") or source.startswith("./") or source.startswith("../"):
            return "local", source
        
        if source.startswith("http"):
            # Full URL provided
            if "github.com" in source:
                repo = source.split("github.com/")[-1].rstrip(".git")
                return "github.com", repo
            elif "gitlab.com" in source:
                repo = source.split("gitlab.com/")[-1].rstrip(".git")
                return "gitlab.com", repo
            else:
                raise PluginError(f"Unsupported git host in URL: {source}")
        
        # Short format like "github:user/repo"
        if ":" not in source:
            raise PluginError(f"Invalid source format: {source}")
        
        platform, repo = source.split(":", 1)
        platform_map = {
            "github": "github.com",
            "gitlab": "gitlab.com",
        }
        
        if platform not in platform_map:
            raise PluginError(f"Unsupported platform: {platform}")
        
        return platform_map[platform], repo
    
    def _clone_plugin(self, source: str, dest_path: Path) -> None:
        """Clone a plugin repository from Git."""
        platform, repo = self._parse_git_source(source)
        
        if platform == "local":
            # Handle local repository - just copy the directory
            import shutil
            src_path = Path(repo).resolve()
            
            if not src_path.exists():
                raise PluginError(f"Local repository path does not exist: {src_path}")
            
            if not (src_path / ".git").exists():
                raise PluginError(f"Path is not a Git repository: {src_path}")
            
            logger.info(f"Copying local Git repository from {src_path}")
            
            try:
                # Use git clone to properly copy the repository
                subprocess.run(
                    ["git", "clone", str(src_path), str(dest_path)],
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                raise PluginError(f"Failed to clone local repository: {e.stderr}") from e
        else:
            # Handle remote repository
            git_url = f"https://{platform}/{repo}.git"
            
            logger.info(f"Cloning plugin from {git_url}")
            
            try:
                subprocess.run(
                    ["git", "clone", git_url, str(dest_path)],
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                raise PluginError(f"Failed to clone plugin: {e.stderr}") from e
        
        if not dest_path.exists():
            raise PluginError("Plugin cloning failed - destination directory was not created")
        
        # Check for git command availability
        try:
            subprocess.run(["git", "--version"], check=True, capture_output=True)
        except FileNotFoundError:
            raise PluginError("Git is not installed or not in PATH") from None
    
    def _install_default_config(self, plugin_name: str, plugin_dir: Path) -> None:
        """Install default configuration from plugin's config.toml if it exists."""
        default_config_path = plugin_dir / "config.toml"
        
        if not default_config_path.exists():
            logger.debug(f"No default config found for plugin '{plugin_name}'")
            return
        
        # Load the default config
        try:
            with open(default_config_path, "rb") as f:
                default_config = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError) as e:
            logger.warning(f"Failed to load default config for plugin '{plugin_name}': {e}")
            return
        
        # Load existing plugins config or create empty dict
        if PLUGINS_CONFIG.exists():
            try:
                with open(PLUGINS_CONFIG, "rb") as f:
                    existing_config = tomllib.load(f)
            except (OSError, tomllib.TOMLDecodeError) as e:
                logger.warning(f"Failed to load existing plugins config: {e}")
                existing_config = {}
        else:
            existing_config = {}
        
        # Check if plugin config already exists
        if plugin_name in existing_config:
            logger.debug(f"Plugin '{plugin_name}' config already exists, skipping default config installation")
            return
        
        # Merge the default config
        if plugin_name in default_config:
            existing_config[plugin_name] = default_config[plugin_name]
            
            # Write the updated config
            try:
                with open(PLUGINS_CONFIG, "wb") as f:
                    tomli_w.dump(existing_config, f)
                logger.info(f"Installed default configuration for plugin '{plugin_name}'")
            except OSError as e:
                logger.warning(f"Failed to save default config for plugin '{plugin_name}': {e}")
        else:
            logger.debug(f"No config section found for plugin '{plugin_name}' in default config")


# Global instance
plugin_manager = PluginManager()
