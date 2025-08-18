"""Plugin interface definitions for viu.

This module defines the Pydantic models that represent the structure
of plugin.info.toml files and plugin configurations.
"""

from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field


class PluginComponents(BaseModel):
    """Defines the components that a plugin provides.
    
    Each component is defined as a string in the format:
    {module_name_in_repo}:{ClassName_or_factory_function}
    
    For example:
        provider = "gogo_provider:GogoProvider"
        player = "my_player:MyPlayer"
        selector = "my_selector:MySelector"
        command = "my_command:my_command_func"
    """
    
    provider: Optional[str] = Field(
        None, 
        description="Provider component in format 'module:class'"
    )
    player: Optional[str] = Field(
        None, 
        description="Player component in format 'module:class'"
    )
    selector: Optional[str] = Field(
        None, 
        description="Selector component in format 'module:class'"
    )
    command: Optional[str] = Field(
        None, 
        description="Command component in format 'module:function'"
    )


class PluginMetadata(BaseModel):
    """Plugin metadata from the [plugin] section."""
    
    name: str = Field(description="Human-readable plugin name")
    version: str = Field(description="Plugin version")
    description: str = Field(description="Plugin description")
    author: Optional[str] = Field(None, description="Plugin author")
    homepage: Optional[str] = Field(None, description="Plugin homepage URL")
    requires_python: Optional[str] = Field(
        None, 
        description="Minimum Python version required"
    )


class PluginInfo(BaseModel):
    """Complete plugin information from plugin.info.toml."""
    
    plugin: PluginMetadata = Field(description="Plugin metadata")
    components: PluginComponents = Field(description="Plugin components")


class InstalledPlugin(BaseModel):
    """Represents a plugin entry in plugins.toml."""
    
    source: str = Field(description="Git source (e.g., 'github:user/repo')")
    path: Path = Field(description="Local filesystem path to the plugin")
    version: Optional[str] = Field(None, description="Installed version")


class PluginManifest(BaseModel):
    """Complete plugins.toml manifest structure."""
    
    providers: Dict[str, InstalledPlugin] = Field(
        default_factory=dict,
        description="Installed provider plugins"
    )
    players: Dict[str, InstalledPlugin] = Field(
        default_factory=dict,
        description="Installed player plugins"
    )
    selectors: Dict[str, InstalledPlugin] = Field(
        default_factory=dict,
        description="Installed selector plugins"
    )
    commands: Dict[str, InstalledPlugin] = Field(
        default_factory=dict,
        description="Installed command plugins"
    )
