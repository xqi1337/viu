"""List plugins command."""

import click
from rich.console import Console
from rich.table import Table
from typing import cast

from viu_media.core.plugins.manager import plugin_manager, ComponentType

console = Console()


@click.command(name="list")
@click.option(
    "--type",
    "plugin_type",
    type=click.Choice(["provider", "player", "selector", "command"]),
    help="Filter by plugin type"
)
def list_plugins(plugin_type: str) -> None:
    """List installed plugins.
    
    Examples:
        viu plugin list
        viu plugin list --type provider
    """
    all_plugins = plugin_manager.list_plugins()
    
    # Filter by type if specified
    if plugin_type:
        plugins_to_show = {cast(ComponentType, plugin_type): all_plugins[cast(ComponentType, plugin_type)]}
    else:
        plugins_to_show = all_plugins
    
    # Count total plugins
    total_count = sum(len(plugins) for plugins in plugins_to_show.values())
    
    if total_count == 0:
        if plugin_type:
            console.print(f"No {plugin_type} plugins installed.", style="yellow")
        else:
            console.print("No plugins installed.", style="yellow")
        console.print("Install plugins with: viu plugin add --type <type> <name> <source>")
        return
    
    # Create table
    table = Table(title="Installed Plugins")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Version", style="yellow")
    table.add_column("Source", style="blue")
    table.add_column("Path", style="magenta")
    
    # Add rows
    for component_type, plugins in plugins_to_show.items():
        for name, plugin_info in plugins.items():
            table.add_row(
                component_type,
                name,
                plugin_info.version or "unknown",
                plugin_info.source,
                str(plugin_info.path)
            )
    
    console.print(table)
    console.print(f"\nTotal: {total_count} plugin(s)")
    
    # Show configuration hint if plugins exist
    if total_count > 0:
        from viu_media.core.constants import PLUGINS_CONFIG
        console.print(
            f"\n💡 Configure plugins by editing: {PLUGINS_CONFIG}",
            style="blue"
        )
