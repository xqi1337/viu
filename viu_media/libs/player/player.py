"""
Player factory and registration logic for Viu media players.

This module provides a factory for instantiating the correct player implementation based on configuration.
"""

from ...core.config import AppConfig
from .base import BasePlayer

PLAYERS = ["mpv", "vlc", "syncplay"]


class PlayerFactory:
    """
    Factory for creating player instances based on configuration.
    """

    @staticmethod
    def create(config: AppConfig) -> BasePlayer:
        """
        Create a player instance based on the configured player name.

        Args:
            config: The full application configuration object.

        Returns:
            BasePlayer: An instance of a class that inherits from BasePlayer.

        Raises:
            ValueError: If the player_name is not supported.
            NotImplementedError: If the player is recognized but not yet implemented.
        """
        from ...core.plugins.manager import plugin_manager
        
        player_name = config.stream.player

        # Check if it's a plugin first
        if plugin_manager.is_plugin("player", player_name):
            try:
                return plugin_manager.load_component("player", player_name)
            except Exception as e:
                raise ValueError(f"Could not load plugin player '{player_name}': {e}") from e

        # Handle built-in players
        if player_name not in PLAYERS:
            raise ValueError(
                f"Unsupported player: '{player_name}'. Supported players are: {PLAYERS}"
            )

        if player_name == "mpv":
            from .mpv.player import MpvPlayer

            return MpvPlayer(config.mpv)
        raise NotImplementedError(
            f"Configuration logic for player '{player_name}' not implemented in factory."
        )


# Alias for convenient player creation
create_player = PlayerFactory.create
