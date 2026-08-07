# Container Locks Plugin for Endstone

A comprehensive container locking system for Minecraft Bedrock Edition servers running Endstone.

## Features

- **Lock Containers**: Lock chests, barrels, and all shulker box variants
- **Trusted Players**: Add trusted players who can access your locked containers
- **Owner Management**: Full management interface for container owners
- **Admin Override**: Admins can access and unlock any container with master keys
- **Visual Feedback**: Action bar notifications when looking at locked containers
- **Persistent Storage**: All locks saved to JSON database

## Installation

1. Ensure you have Endstone 0.11.8 or higher installed
2. Clone or download this plugin
3. Install using pip:
   ```bash
   pip install -e .
   ```
4. Restart your Endstone server
5. The plugin will create a `locks.json` file in the plugin data folder

## Usage

### Locking a Container

Use a `ninjos:lock` item on any lockable container to lock it. If already locked and you're the owner, it opens the management menu.

### Managing Access

When you use the lock item on your own locked container, you'll see a menu with options to:
- **Add Trusted Player**: Grant access to another player
- **Remove Trusted Player**: Revoke access from a trusted player
- **Unlock Container**: Remove the lock completely

### Admin Features

Players with the `container_locks.admin` permission can:
- Access any locked container
- Break any locked container
- Use the `ninjos:masterlock` item to forcibly unlock containers
- See who owns containers when looking at them

### Lockable Container Types

- Chest
- Barrel
- All Shulker Box colors (including undyed)

## Permissions

- `container_locks.admin` - Allows full access to all locked containers and use of master key

## Configuration

The plugin automatically saves locks to `plugins/endstone_container_locks/locks.json`. No additional configuration is needed.

## Commands

This plugin operates entirely through in-game interactions and does not require any commands.

## Technical Details

- Uses Endstone's event system for block interactions
- Implements cooldown system to prevent message spam
- Action bar updates run every 10 ticks (0.5 seconds)
- Form cooldown prevents multiple simultaneous form openings
- Automatically converts old lock format to new format with trusted player support

## Development

Built for Endstone 0.11.8+ with Python 3.10+

### Project Structure
```
endstone-container-locks/
├── src/
│   └── endstone_container_locks/
│       ├── __init__.py
│       └── container_locks.py
├── pyproject.toml
└── README.md
```

## License

This plugin is provided as-is for use with Endstone servers.

## Credits

Ported from the original Minecraft Bedrock JavaScript implementation to Endstone Python plugin.