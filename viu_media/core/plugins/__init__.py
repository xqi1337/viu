"""Plugin system for viu."""

from .model import PluginComponents, PluginInfo
from .manager import PluginManager

__all__ = ["PluginInfo", "PluginComponents", "PluginManager"]
