"""Add plugin command."""

import click
from rich.console import Console
from typing import cast

from viu_media.core.plugins.manager import PluginError, plugin_manager, ComponentType

console = Console()


@click.command()
@click.option(
    "--type",
    "plugin_type", 
    type=click.Choice(["provider", "player", "selector", "command"]),
    required=True,
    help="Type of plugin to install"
)
@click.option(
    "--force", 
    is_flag=True,
    help="Force installation, overwriting existing plugin"
)
@click.argument("name")
@click.argument("source")
def add(plugin_type: str, name: str, source: str, force: bool) -> None:
    """Install a plugin from a Git repository.
    
    NAME: Local name for the plugin
    SOURCE: Git source (e.g., 'github:user/repo' or full URL)
    
    Examples:
        viu plugin add --type provider gogoanime github:user/viu-gogoanime
        viu plugin add --type player custom-mpv https://github.com/user/viu-mpv-plugin
    """
    try:
        console.print(f"Installing {plugin_type} plugin '{name}' from {source}...")
        plugin_manager.add_plugin(cast(ComponentType, plugin_type), name, source, force=force)
        console.print(f"✅ Successfully installed plugin '{name}'", style="green")
        
        # Show configuration hint
        from viu_media.core.constants import PLUGINS_CONFIG
        console.print(
            f"\n💡 Configure the plugin by editing: {PLUGINS_CONFIG}",
            style="blue"
        )
        
    except PluginError as e:
        console.print(f"❌ Failed to install plugin: {e}", style="red")
        raise click.ClickException(str(e))
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="red")
        raise click.ClickException(f"Unexpected error: {e}")
