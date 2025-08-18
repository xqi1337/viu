"""Remove plugin command."""

import click
from rich.console import Console
from typing import cast

from viu_media.core.plugins.manager import PluginError, PluginNotFoundError, plugin_manager, ComponentType

console = Console()


@click.command()
@click.option(
    "--type",
    "plugin_type",
    type=click.Choice(["provider", "player", "selector", "command"]),
    required=True,
    help="Type of plugin to remove"
)
@click.argument("name")
def remove(plugin_type: str, name: str) -> None:
    """Remove an installed plugin.
    
    NAME: Name of the plugin to remove
    
    Examples:
        viu plugin remove --type provider gogoanime
        viu plugin remove --type player custom-mpv
    """
    try:
        console.print(f"Removing {plugin_type} plugin '{name}'...")
        plugin_manager.remove_plugin(cast(ComponentType, plugin_type), name)
        console.print(f"✅ Successfully removed plugin '{name}'", style="green")
        
    except PluginNotFoundError as e:
        console.print(f"❌ Plugin not found: {e}", style="red")
        raise click.ClickException(str(e))
    except PluginError as e:
        console.print(f"❌ Failed to remove plugin: {e}", style="red")
        raise click.ClickException(str(e))
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="red")
        raise click.ClickException(f"Unexpected error: {e}")
