import importlib
import logging
from typing import Union

from httpx import Client

from .base import BaseAnimeProvider
from .types import ProviderName

logger = logging.getLogger(__name__)

PROVIDERS_AVAILABLE = {
    "allanime": "provider.AllAnime",
    "animepahe": "provider.AnimePahe",
    "hianime": "provider.HiAnime",
    "nyaa": "provider.Nyaa",
    "yugen": "provider.Yugen",
}


class AnimeProviderFactory:
    """Factory for creating anime provider instances."""

    @staticmethod
    def create(provider_name: Union[ProviderName, str]) -> BaseAnimeProvider:
        """
        Dynamically creates an instance of the specified anime provider.

        This method imports the necessary provider module, instantiates its main class,
        and injects a pre-configured HTTP client. It now also supports plugin providers.

        Args:
            provider_name: The name of the provider to create (e.g., 'allanime').

        Returns:
            An instance of a class that inherits from BaseProvider.

        Raises:
            ValueError: If the provider_name is not supported.
            ImportError: If the provider module or class cannot be found.
        """
        from ....core.plugins.manager import plugin_manager
        from ....core.utils.networking import random_user_agent

        # Convert to string if it's an enum
        if isinstance(provider_name, ProviderName):
            provider_str = provider_name.value
        else:
            provider_str = str(provider_name)
        
        # Check if it's a plugin first
        if plugin_manager.is_plugin("provider", provider_str):
            try:
                return plugin_manager.load_component("provider", provider_str)
            except Exception as e:
                logger.error(f"Failed to load plugin provider '{provider_str}': {e}")
                raise ImportError(f"Could not load plugin provider '{provider_str}': {e}") from e
        
        # Handle built-in providers
        if provider_str.lower() not in PROVIDERS_AVAILABLE:
            raise ValueError(f"Provider '{provider_str}' is not available")
        
        # Correctly determine module and class name from the map
        import_path = PROVIDERS_AVAILABLE[provider_str.lower()]
        module_name, class_name = import_path.split(".", 1)

        # Construct the full package path for dynamic import
        package_path = f"viu_media.libs.provider.anime.{provider_str.lower()}"

        try:
            provider_module = importlib.import_module(f".{module_name}", package_path)
            provider_class = getattr(provider_module, class_name)
        except (ImportError, AttributeError) as e:
            logger.error(
                f"Failed to load provider '{provider_str}': {e}"
            )
            raise ImportError(
                f"Could not load provider '{provider_str}'. "
                "Check the module path and class name in PROVIDERS_AVAILABLE."
            ) from e

        # Each provider class requires an httpx.Client, which we set up here.
        client = Client(
            headers={"User-Agent": random_user_agent(), **provider_class.HEADERS}
        )

        return provider_class(client)


# Simple alias for ease of use, consistent with other factories in the codebase.
create_provider = AnimeProviderFactory.create
