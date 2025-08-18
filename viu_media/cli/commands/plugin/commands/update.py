"""Update plugin command."""

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
    help="Type of plugin to update"
)
@click.argument("name")
def update(plugin_type: str, name: str) -> None:
    """Update an installed plugin by pulling from Git.
    
    NAME: Name of the plugin to update
    
    Examples:
        viu plugin update --type provider gogoanime
        viu plugin update --type player custom-mpv
    """
    try:
        console.print(f"Updating {plugin_type} plugin '{name}'...")
        plugin_manager.update_plugin(cast(ComponentType, plugin_type), name)
        console.print(f"✅ Successfully updated plugin '{name}'", style="green")
        
    except PluginNotFoundError as e:
        console.print(f"❌ Plugin not found: {e}", style="red")
        raise click.ClickException(str(e))
    except PluginError as e:
        console.print(f"❌ Failed to update plugin: {e}", style="red")
        raise click.ClickException(str(e))
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="red")
        raise click.ClickException(f"Unexpected error: {e}")
