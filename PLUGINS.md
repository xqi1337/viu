# Viu Plugin Development Guide

This guide explains how to create plugins for viu, the terminal-based anime streaming tool.

## Overview

Viu supports four types of plugins:

- **Providers**: Add support for new anime streaming websites
- **Players**: Add support for new media players
- **Selectors**: Add support for new interactive selection tools
- **Commands**: Add new CLI commands to viu

## Plugin Structure

Every plugin must be a Git repository with the following structure:

```
your-plugin-repo/
├── plugin.info.toml        # Plugin metadata (required)
├── your_module.py          # Your plugin implementation
├── config.toml             # Default configuration (optional)
├── requirements.txt        # Dependencies (optional)
├── utils.py                # Additional modules (optional)
├── helpers/                # Subdirectories supported (optional)
│   ├── __init__.py
│   └── parser.py
└── README.md              # Documentation (recommended)
```

### Multi-File Plugins

Viu supports plugins with multiple Python files. You can organize your plugin code across multiple modules and import between them normally:

```python
# In your main plugin file
from utils import helper_function
from helpers.parser import ResponseParser

class MyProvider(BaseAnimeProvider):
    def __init__(self, client, **config):
        self.parser = ResponseParser()
        # ... rest of implementation
```

The plugin system automatically adds your plugin directory to Python's import path during loading, so relative imports work as expected.

### Plugin Manifest (`plugin.info.toml`)

Every plugin repository must contain a `plugin.info.toml` file at its root:

```toml
[plugin]
name = "My Awesome Plugin"
version = "1.0.0"
description = "Adds support for Example Anime Site"
author = "Your Name"
homepage = "https://github.com/yourname/viu-example-plugin"
requires_python = ">=3.11"

[components]
# Specify which components your plugin provides
provider = "example_provider:ExampleProvider"  # format: module:class
# player = "my_player:MyPlayer"               # (if providing a player)
# selector = "my_selector:MySelector"         # (if providing a selector)
# command = "my_command:my_command_func"      # (if providing a command)
```

## Provider Plugins

Provider plugins add support for new anime streaming websites.

### Requirements

Your provider class must inherit from `BaseAnimeProvider` and implement:

- `search(query: str) -> SearchResults`
- `get(anime_id: str) -> Anime`
- `episode_streams(anime_id: str, episode: str) -> List[Server]`

### Example Provider Plugin

**plugin.info.toml:**

```toml
[plugin]
name = "Example Anime Provider"
version = "1.0.0"
description = "Adds support for example.anime.site"

[components]
provider = "example_provider:ExampleProvider"
```

**example_provider.py:**

```python
from typing import List
from httpx import Client

# These imports work because viu adds the plugin path to sys.path
from viu_media.libs.provider.anime.base import BaseAnimeProvider
from viu_media.libs.provider.anime.types import SearchResults, Anime, Server

class ExampleProvider(BaseAnimeProvider):
    HEADERS = {
        "Referer": "https://example.anime.site/",
    }

    def __init__(self, client: Client, **config):
        self.client = client
        # Access plugin configuration
        self.timeout = config.get("timeout", 30)
        self.preferred_quality = config.get("preferred_quality", "720p")

    def search(self, query: str) -> SearchResults:
        # Implement search logic
        response = self.client.get(f"https://example.anime.site/search?q={query}")
        # Parse response and return SearchResults
        return SearchResults(...)

    def get(self, anime_id: str) -> Anime:
        # Implement anime details fetching
        response = self.client.get(f"https://example.anime.site/anime/{anime_id}")
        # Parse response and return Anime
        return Anime(...)

    def episode_streams(self, anime_id: str, episode: str) -> List[Server]:
        # Implement stream URL extraction
        response = self.client.get(f"https://example.anime.site/watch/{anime_id}/{episode}")
        # Parse response and return list of Server objects
        return [Server(...)]
```

## Player Plugins

Player plugins add support for new media players.

### Requirements

Your player class must inherit from `BasePlayer` and implement:

- `play(media_url: str, **kwargs) -> None`

### Example Player Plugin

**plugin.info.toml:**

```toml
[plugin]
name = "Custom Player"
version = "1.0.0"
description = "Adds support for my custom media player"

[components]
player = "custom_player:CustomPlayer"
```

**custom_player.py:**

```python
import subprocess
from viu_media.libs.player.base import BasePlayer

class CustomPlayer(BasePlayer):
    def __init__(self, **config):
        self.executable = config.get("executable", "my-player")
        self.extra_args = config.get("extra_args", [])

    def play(self, media_url: str, **kwargs) -> None:
        cmd = [self.executable] + self.extra_args + [media_url]
        subprocess.run(cmd)
```

## Selector Plugins

Selector plugins add support for new interactive selection tools.

### Requirements

Your selector class must inherit from `BaseSelector` and implement:

- `choose(choices: List[str], **kwargs) -> str`
- `confirm(message: str, **kwargs) -> bool`
- `ask(message: str, **kwargs) -> str`

## Command Plugins

Command plugins add new CLI commands to viu.

### Example Command Plugin

**plugin.info.toml:**

```toml
[plugin]
name = "My Command"
version = "1.0.0"
description = "Adds a custom command to viu"

[components]
command = "my_command:my_command"
```

**my_command.py:**

```python
import click

@click.command()
@click.argument("arg1")
def my_command(arg1: str):
    """My custom command description."""
    click.echo(f"Hello from plugin command with arg: {arg1}")
```

## Plugin Configuration

Plugins can include a default configuration file (`config.toml`) in their repository root. When a plugin is installed, this default configuration is automatically copied to the user's `~/.config/viu/plugins.config.toml` file.

**Example `config.toml` in plugin repository:**

```toml
# Default configuration for My Plugin
[my-plugin-name]
timeout = 30
preferred_quality = "720p"
custom_option = "default_value"
```

**After installation, users can customize by editing `~/.config/viu/plugins.config.toml`:**

```toml
[my-plugin-name]
timeout = 60              # Customized value
preferred_quality = "1080p"  # Customized value
custom_option = "my_value"   # Customized value
```

Access this configuration in your plugin constructor via the `**config` parameter.

## Installation and Usage

### For Plugin Developers

1. Create your plugin repository following the structure above
2. Test your plugin locally
3. Publish your repository on GitHub/GitLab
4. Share the installation command with users

### For Users

Install a plugin:

```bash
viu plugin add --type provider myplugin github:user/viu-myplugin
```

Configure the plugin by editing `~/.config/viu/plugins.config.toml`:

```toml
[myplugin]
option1 = "value1"
option2 = "value2"
```

Use the plugin:

```bash
viu --provider myplugin search "anime name"
```

## Dependencies

If your plugin requires additional Python packages, include a `requirements.txt` file in your repository root. Users will need to install these manually:

```bash
pip install -r requirements.txt
```

## Best Practices

1. **Error Handling**: Implement proper error handling and logging
2. **Configuration**: Make your plugin configurable through the config system
3. **Documentation**: Include a README.md with usage instructions
4. **Testing**: Test your plugin thoroughly before publishing
5. **Versioning**: Use semantic versioning for your plugin releases
6. **Compatibility**: Specify minimum Python version requirements

## Plugin Management Commands

```bash
# Install a plugin
viu plugin add --type provider myplugin github:user/viu-myplugin

# List installed plugins
viu plugin list
viu plugin list --type provider

# Update a plugin
viu plugin update --type provider myplugin

# Remove a plugin
viu plugin remove --type provider myplugin
```

## Example Plugins

Check out these example plugin repositories:

- [Example Provider Plugin](https://github.com/example/viu-example-provider)
- [Example Player Plugin](https://github.com/example/viu-example-player)

## Support

For plugin development support:

- Open an issue in the main viu repository
- Join the Discord server: https://discord.gg/C4rhMA4mmK
