"""Main plugin command group."""

import click

from ...utils.lazyloader import LazyGroup

lazy_subcommands = {
    "add": "add.add",
    "remove": "remove.remove", 
    "list": "list_plugins.list_plugins",
    "update": "update.update",
}


@click.group(
    name="plugin",
    cls=LazyGroup,
    root="viu_media.cli.commands.plugin.commands",
    lazy_subcommands=lazy_subcommands,
    help="Manage viu plugins (providers, players, selectors, commands)"
)
def plugin() -> None:
    """Manage viu plugins."""
    pass
