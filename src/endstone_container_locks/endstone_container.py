import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from endstone import Player, ColorFormat
from endstone.plugin import Plugin
from endstone.event import (
    event_handler,
    PlayerInteractEvent,
    BlockBreakEvent,
    BlockPlaceEvent,
    PlayerQuitEvent,
)
from endstone.command import Command, CommandSender
from endstone.form import ActionForm, ModalForm, TextInput


class ContainerLocksPlugin(Plugin):
    """
    Container locking system for Minecraft Bedrock servers.
    Allows players to lock chests, barrels, and shulker boxes.
    """

    api_version = "0.11"

    # --- Command & permission declarations (Endstone-style) ---
    commands = {
        "trust": {
            "description": "Manage trusted players for your containers and doors.",
            "usages": ["/trust <add|remove|list|globaladd|globalremove|globallist> [playername]"],
            "permissions": ["container_locks.command.trust"],
        }
    }
    permissions = {
        "container_locks.command.trust": {
            "description": "Allow players to use /trust to manage container access.",
            "default": True,  # everyone can use by default; adjust as needed
        },
        "container_locks.admin": {
            "description": "Admin permission to bypass and master unlock.",
            "default": "op",
        },
    }

    LOCKABLE_TYPES = [
        "minecraft:chest",
        "minecraft:trapped_chest",
        "minecraft:barrel",
        "minecraft:undyed_shulker_box",
        "minecraft:black_shulker_box",
        "minecraft:blue_shulker_box",
        "minecraft:brown_shulker_box",
        "minecraft:cyan_shulker_box",
        "minecraft:gray_shulker_box",
        "minecraft:green_shulker_box",
        "minecraft:light_blue_shulker_box",
        "minecraft:light_gray_shulker_box",
        "minecraft:lime_shulker_box",
        "minecraft:magenta_shulker_box",
        "minecraft:orange_shulker_box",
        "minecraft:pink_shulker_box",
        "minecraft:purple_shulker_box",
        "minecraft:red_shulker_box",
        "minecraft:white_shulker_box",
        "minecraft:yellow_shulker_box",
        "minecraft:copper_chest",
        "minecraft:exposed_copper_chest",
        "minecraft:weathered_copper_chest",
        "minecraft:oxidized_copper_chest",
        "minecraft:waxed_copper_chest",
        "minecraft:waxed_exposed_copper_chest",
        "minecraft:waxed_weathered_copper_chest",
        "minecraft:waxed_oxidized_copper_chest",
    ]

    LOCKABLE_DOOR_TYPES = [
        "minecraft:wooden_door",
        "minecraft:spruce_door",
        "minecraft:birch_door",
        "minecraft:jungle_door",
        "minecraft:acacia_door",
        "minecraft:dark_oak_door",
        "minecraft:mangrove_door",
        "minecraft:cherry_door",
        "minecraft:bamboo_door",
        "minecraft:crimson_door",
        "minecraft:warped_door",
        "minecraft:iron_door",
        "minecraft:copper_door",
        "minecraft:exposed_copper_door",
        "minecraft:weathered_copper_door",
        "minecraft:oxidized_copper_door",
        "minecraft:waxed_copper_door",
        "minecraft:waxed_exposed_copper_door",
        "minecraft:waxed_weathered_copper_door",
        "minecraft:waxed_oxidized_copper_door",
        "minecraft:trapdoor",
        "minecraft:spruce_trapdoor",
        "minecraft:birch_trapdoor",
        "minecraft:jungle_trapdoor",
        "minecraft:acacia_trapdoor",
        "minecraft:dark_oak_trapdoor",
        "minecraft:mangrove_trapdoor",
        "minecraft:cherry_trapdoor",
        "minecraft:bamboo_trapdoor",
        "minecraft:crimson_trapdoor",
        "minecraft:warped_trapdoor",
        "minecraft:iron_trapdoor",
        "minecraft:copper_trapdoor",
        "minecraft:exposed_copper_trapdoor",
        "minecraft:weathered_copper_trapdoor",
        "minecraft:oxidized_copper_trapdoor",
        "minecraft:waxed_copper_trapdoor",
        "minecraft:waxed_exposed_copper_trapdoor",
        "minecraft:waxed_weathered_copper_trapdoor",
        "minecraft:waxed_oxidized_copper_trapdoor",
    ]

    # Full-height door types (2-block-tall, lock both halves)
    FULL_DOOR_TYPES = [
        "minecraft:wooden_door",
        "minecraft:spruce_door",
        "minecraft:birch_door",
        "minecraft:jungle_door",
        "minecraft:acacia_door",
        "minecraft:dark_oak_door",
        "minecraft:mangrove_door",
        "minecraft:cherry_door",
        "minecraft:bamboo_door",
        "minecraft:crimson_door",
        "minecraft:warped_door",
        "minecraft:iron_door",
        "minecraft:copper_door",
        "minecraft:exposed_copper_door",
        "minecraft:weathered_copper_door",
        "minecraft:oxidized_copper_door",
        "minecraft:waxed_copper_door",
        "minecraft:waxed_exposed_copper_door",
        "minecraft:waxed_weathered_copper_door",
        "minecraft:waxed_oxidized_copper_door",
    ]

    REDSTONE_ACTIVATORS = [
        "minecraft:lever",
        "minecraft:stone_button",
        "minecraft:wooden_button",
        "minecraft:spruce_button",
        "minecraft:birch_button",
        "minecraft:jungle_button",
        "minecraft:acacia_button",
        "minecraft:dark_oak_button",
        "minecraft:mangrove_button",
        "minecraft:cherry_button",
        "minecraft:bamboo_button",
        "minecraft:crimson_button",
        "minecraft:warped_button",
        "minecraft:polished_blackstone_button",
        "minecraft:stone_pressure_plate",
        "minecraft:wooden_pressure_plate",
        "minecraft:spruce_pressure_plate",
        "minecraft:birch_pressure_plate",
        "minecraft:jungle_pressure_plate",
        "minecraft:acacia_pressure_plate",
        "minecraft:dark_oak_pressure_plate",
        "minecraft:mangrove_pressure_plate",
        "minecraft:cherry_pressure_plate",
        "minecraft:bamboo_pressure_plate",
        "minecraft:crimson_pressure_plate",
        "minecraft:warped_pressure_plate",
        "minecraft:polished_blackstone_pressure_plate",
        "minecraft:light_weighted_pressure_plate",
        "minecraft:heavy_weighted_pressure_plate",
    ]

    # Redstone components that should not be placed near locked doors
    REDSTONE_PLACEABLE_BLOCKS = [
        "minecraft:redstone_block",
        "minecraft:redstone_wire",
        "minecraft:redstone_torch",
        "minecraft:unlit_redstone_torch",
        "minecraft:unpowered_repeater",
        "minecraft:powered_repeater",
        "minecraft:unpowered_comparator",
        "minecraft:powered_comparator",
        "minecraft:observer",
        "minecraft:daylight_detector",
        "minecraft:daylight_detector_inverted",
        "minecraft:tripwire_hook",
        "minecraft:piston",
        "minecraft:sticky_piston",
        "minecraft:dropper",
        "minecraft:dispenser",
        "minecraft:hopper",
        "minecraft:tnt",
        "minecraft:sculk_sensor",
        "minecraft:calibrated_sculk_sensor",
        "minecraft:target",
        "minecraft:lever",
        "minecraft:stone_button",
        "minecraft:wooden_button",
        "minecraft:spruce_button",
        "minecraft:birch_button",
        "minecraft:jungle_button",
        "minecraft:acacia_button",
        "minecraft:dark_oak_button",
        "minecraft:mangrove_button",
        "minecraft:cherry_button",
        "minecraft:bamboo_button",
        "minecraft:crimson_button",
        "minecraft:warped_button",
        "minecraft:polished_blackstone_button",
        "minecraft:stone_pressure_plate",
        "minecraft:wooden_pressure_plate",
        "minecraft:spruce_pressure_plate",
        "minecraft:birch_pressure_plate",
        "minecraft:jungle_pressure_plate",
        "minecraft:acacia_pressure_plate",
        "minecraft:dark_oak_pressure_plate",
        "minecraft:mangrove_pressure_plate",
        "minecraft:cherry_pressure_plate",
        "minecraft:bamboo_pressure_plate",
        "minecraft:crimson_pressure_plate",
        "minecraft:warped_pressure_plate",
        "minecraft:polished_blackstone_pressure_plate",
        "minecraft:light_weighted_pressure_plate",
        "minecraft:heavy_weighted_pressure_plate",
    ]

    REDSTONE_CHECK_RADIUS = 3

    COOLDOWN_MS = 1000

    def __init__(self):
        super().__init__()
        self.locks_db: Dict[str, dict] = {}
        self.door_locks_db: Dict[str, dict] = {}
        self.global_trusted_db: Dict[str, List[str]] = {}
        self.message_cooldowns: Dict[str, float] = {}
        self.form_open_cooldown: Set[str] = set()
        self.action_bar_cooldowns: Dict[str, float] = {}
        self.db_file: Optional[Path] = None
        self.door_db_file: Optional[Path] = None
        self.global_trusted_file: Optional[Path] = None
        # map of player.name -> "x,y,z" the container they are managing
        self.pending_trust_blocks: Dict[str, str] = {}
        # map of player.name -> "x,y,z" the door they are managing
        self.pending_door_blocks: Dict[str, str] = {}
        # Tracks doors that an authorized player has intentionally opened
        # Maps "x,y,z" -> timestamp so we don't fight with legitimate opens
        self.allowed_opens: Dict[str, float] = {}
        # How long (seconds) an allowed open stays valid before auto-expiring
        self.ALLOWED_OPEN_TIMEOUT = 60.0
        # Track the door monitor task so we can cancel it on reload/disable
        self._door_monitor_task = None

    def on_enable(self) -> None:
        """Called when the plugin is enabled."""
        self.logger.info("Container Locks plugin enabled!")

        # Initialize database file paths
        self.db_file = self.data_folder / "locks.json"
        self.door_db_file = self.data_folder / "door_locks.json"
        self.global_trusted_file = self.data_folder / "global_trusted.json"
        self.data_folder.mkdir(parents=True, exist_ok=True)

        # Load existing locks
        self.load_locks()
        self.load_door_locks()
        self.load_global_trusted()

        # Register event listeners
        self.register_events(self)

        # Start the door state monitor (catches redstone-opened locked doors)
        self._start_door_monitor()

        # NOTE: Commands are registered via `commands` + `on_command`.

    def on_disable(self) -> None:
        """Called when the plugin is disabled."""
        # Cancel the door monitor task to prevent stale references after reload
        if self._door_monitor_task:
            try:
                self._door_monitor_task.cancel()
            except Exception:
                pass
            self._door_monitor_task = None

        self.save_locks()
        self.save_door_locks()
        self.save_global_trusted()

        # Clear transient in-memory state so a stale instance can't interfere
        self.form_open_cooldown.clear()
        self.message_cooldowns.clear()
        self.action_bar_cooldowns.clear()
        self.pending_trust_blocks.clear()
        self.pending_door_blocks.clear()
        self.allowed_opens.clear()

        self.logger.info("Container Locks plugin disabled!")

    # ======== Redstone protection: tick-based door state monitor ========

    def _start_door_monitor(self) -> None:
        """Start a repeating task that checks locked doors every 5 ticks."""
        self._door_monitor_task = self.server.scheduler.run_task(
            self, self._check_locked_doors, delay=20, period=5
        )
        self.logger.info("Door state monitor started (every 5 ticks)")

    def _check_locked_doors(self) -> None:
        """
        Periodic check: for every locked door, if its open_bit is true
        and it is NOT in our allowed_opens set, force it closed via /setblock.
        """
        now = time.time()

        # Expire old allowed_opens entries
        expired = [
            pos for pos, ts in self.allowed_opens.items()
            if now - ts > self.ALLOWED_OPEN_TIMEOUT
        ]
        for pos in expired:
            del self.allowed_opens[pos]

        if not self.door_locks_db:
            return

        for pos in list(self.door_locks_db.keys()):
            # Skip doors that an authorized player intentionally opened
            if pos in self.allowed_opens:
                continue

            self._force_close_door(pos)

    def _force_close_door(self, pos: str) -> None:
        """
        Force a door at the given position to closed state.
        Reads the full block data to preserve direction/hinge/upper states,
        then only flips open_bit to false via /setblock.
        """
        try:
            x, y, z = map(int, pos.split(","))
            dimension = self.server.level.get_dimension("overworld")
            block = dimension.get_block_at(x, y, z)
            if not block or block.type not in self.LOCKABLE_DOOR_TYPES:
                return

            # Get the block data string representation
            # Typical format: minecraft:wooden_door ["direction"=0, "door_hinge_bit"=0b, "open_bit"=1b, "upper_block_bit"=0b]
            data_str = str(block.data) if hasattr(block, 'data') and block.data else ""

            # Quick check: is the door actually open?
            # Look for open_bit with value 1, true, or 1b
            if not data_str:
                return

            data_lower = data_str.lower()
            is_open = (
                '"open_bit"=1b' in data_lower
                or '"open_bit"=true' in data_lower
                or '"open_bit"=1' in data_lower
                or "'open_bit'=1b" in data_lower
                or "'open_bit'=true" in data_lower
                or "'open_bit'=1" in data_lower
            )

            if not is_open:
                return  # Already closed, nothing to do

            # Build setblock command preserving all states
            # Extract the block states portion from data_str
            # The string typically looks like: type_name [states]
            # We need to reconstruct with open_bit=false
            # Replace open_bit value to false/0 in the data string
            # Handle formats: "open_bit"=1b, "open_bit"=true, "open_bit"=1
            modified = re.sub(
                r'(["\']open_bit["\'])\s*=\s*(?:1b?|true)',
                r'\1=false',
                data_str,
                flags=re.IGNORECASE
            )

            # Now issue setblock with the full modified block data
            self.server.dispatch_command(
                self.server.command_sender,
                f'setblock {x} {y} {z} {modified} replace'
            )
        except Exception:
            pass

    def load_locks(self) -> None:
        """Load locks from JSON file."""
        if self.db_file and self.db_file.exists():
            try:
                with open(self.db_file, "r") as f:
                    self.locks_db = json.load(f)
                self.logger.info(f"Loaded {len(self.locks_db)} container locks")
            except Exception as e:
                self.logger.error(f"Failed to load locks: {e}")
                self.locks_db = {}
        else:
            self.locks_db = {}

    def save_locks(self) -> None:
        """Save locks to JSON file."""
        try:
            if not self.db_file:
                self.logger.error("DB file path not initialized")
                return
            with open(self.db_file, "w") as f:
                json.dump(self.locks_db, f, indent=2)
            self.logger.info(f"Saved {len(self.locks_db)} container locks")
        except Exception as e:
            self.logger.error(f"Failed to save locks: {e}")

    def load_door_locks(self) -> None:
        """Load door locks from JSON file."""
        if self.door_db_file and self.door_db_file.exists():
            try:
                with open(self.door_db_file, "r") as f:
                    self.door_locks_db = json.load(f)
                self.logger.info(f"Loaded {len(self.door_locks_db)} door locks")
            except Exception as e:
                self.logger.error(f"Failed to load door locks: {e}")
                self.door_locks_db = {}
        else:
            self.door_locks_db = {}

    def save_door_locks(self) -> None:
        """Save door locks to JSON file."""
        try:
            if not self.door_db_file:
                self.logger.error("Door DB file path not initialized")
                return
            with open(self.door_db_file, "w") as f:
                json.dump(self.door_locks_db, f, indent=2)
            self.logger.info(f"Saved {len(self.door_locks_db)} door locks")
        except Exception as e:
            self.logger.error(f"Failed to save door locks: {e}")

    def load_global_trusted(self) -> None:
        """Load global trusted lists from JSON file."""
        if self.global_trusted_file and self.global_trusted_file.exists():
            try:
                with open(self.global_trusted_file, "r") as f:
                    self.global_trusted_db = json.load(f)
                self.logger.info(f"Loaded global trusted lists for {len(self.global_trusted_db)} owners")
            except Exception as e:
                self.logger.error(f"Failed to load global trusted: {e}")
                self.global_trusted_db = {}
        else:
            self.global_trusted_db = {}

    def save_global_trusted(self) -> None:
        """Save global trusted lists to JSON file."""
        try:
            if not self.global_trusted_file:
                self.logger.error("Global trusted file path not initialized")
                return
            with open(self.global_trusted_file, "w") as f:
                json.dump(self.global_trusted_db, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save global trusted: {e}")

    @staticmethod
    def get_block_position(block) -> str:
        """Get a string representation of block position."""
        loc = block.location
        return f"{loc.x},{loc.y},{loc.z}"

    def get_normalized_lock_info(self, block_position: str) -> Optional[dict]:
        """Get normalized lock info, converting old string format to new dict format."""
        lock_data = self.locks_db.get(block_position)
        if not lock_data:
            return None

        # Convert old format (string) to new format (dict)
        if isinstance(lock_data, str):
            owner_name = lock_data
            new_lock_info = {"owner": owner_name, "trusted": []}
            self.locks_db[block_position] = new_lock_info
            self.save_locks()
            return new_lock_info

        # Ensure 'trusted' exists and is a list
        if "trusted" not in lock_data or not isinstance(lock_data["trusted"], list):
            lock_data["trusted"] = []
        return lock_data

    def send_cooldown_message(self, player: Player, message: str) -> None:
        """Send a message to player with cooldown to prevent spam."""
        now = time.time() * 1000  # milliseconds
        pid = str(player.unique_id)
        last_message_time = self.message_cooldowns.get(pid, 0)

        if now - last_message_time > self.COOLDOWN_MS:
            player.send_message(message)
            self.message_cooldowns[pid] = now

    # ======== Trust helpers (case-insensitive) ========

    @staticmethod
    def _clean_name(name: str) -> str:
        return (name or "").strip()

    @staticmethod
    def _lower(name: str) -> str:
        return (name or "").lower()

    def _trusted_index(self, trusted: List[str], name: str) -> int:
        """Return index in trusted list matching name (case-insensitive), or -1."""
        name_l = self._lower(name)
        for i, n in enumerate(trusted or []):
            if self._lower(n) == name_l:
                return i
        return -1

    def _is_trusted(self, trusted: List[str], name: str) -> bool:
        return self._trusted_index(trusted, name) != -1

    def _is_globally_trusted(self, owner: str, player_name: str) -> bool:
        """Check if player_name is in the owner's global trusted list."""
        owner_key = self._lower(owner)
        player_key = self._lower(player_name)
        trusted = self.global_trusted_db.get(owner_key, [])
        return any(self._lower(t) == player_key for t in trusted)

    def _add_global_trusted(self, owner: str, name: str) -> bool:
        """Add name to owner's global trusted list. Returns True if added."""
        name = self._clean_name(name)
        if not name:
            return False
        owner_key = self._lower(owner)
        trusted = self.global_trusted_db.setdefault(owner_key, [])
        if not any(self._lower(t) == self._lower(name) for t in trusted):
            trusted.append(name)
            return True
        return False

    def _remove_global_trusted(self, owner: str, name: str) -> bool:
        """Remove name from owner's global trusted list. Returns True if removed."""
        name = self._clean_name(name)
        owner_key = self._lower(owner)
        trusted = self.global_trusted_db.get(owner_key, [])
        name_l = self._lower(name)
        for i, t in enumerate(trusted):
            if self._lower(t) == name_l:
                trusted.pop(i)
                # Clean up empty lists
                if not trusted:
                    self.global_trusted_db.pop(owner_key, None)
                return True
        return False

    def _get_global_trusted(self, owner: str) -> List[str]:
        """Return the owner's global trusted list."""
        return self.global_trusted_db.get(self._lower(owner), [])

    def _has_admin_tag(self, player: Player) -> bool:
        """Check if player has the Admin scoreboard tag (via /tag playerName add Admin)."""
        try:
            return "Admin" in player.scoreboard_tags
        except Exception:
            return False

    def _add_trusted_name(self, lock_info: dict, name: str) -> bool:
        """Add name to trusted (case-insensitive uniqueness). Returns True if added."""
        name = self._clean_name(name)
        if not name:
            return False
        trusted = lock_info.setdefault("trusted", [])
        if not self._is_trusted(trusted, name):
            trusted.append(name)
            return True
        return False

    def _remove_trusted_name(self, lock_info: dict, name: str) -> bool:
        """Remove name from trusted (case-insensitive). Returns True if removed."""
        name = self._clean_name(name)
        trusted = lock_info.get("trusted", [])
        idx = self._trusted_index(trusted, name)
        if idx != -1:
            trusted.pop(idx)
            return True
        return False

    def can_access_container(self, player: Player, block) -> bool:
        """Check if player can access a locked container."""
        block_position = self.get_block_position(block)
        lock_info = self.get_normalized_lock_info(block_position)

        if not lock_info:
            return True

        # Owner (case-insensitive)
        if self._lower(lock_info.get("owner", "")) == self._lower(player.name):
            return True

        # Trusted (case-insensitive)
        if self._is_trusted(lock_info.get("trusted", []), player.name):
            return True

        # Global trusted (owner trusts this player for all their containers)
        if self._is_globally_trusted(lock_info.get("owner", ""), player.name):
            return True

        # Admin bypass (permission or Admin tag)
        if player.has_permission("container_locks.admin"):
            return True
        if self._has_admin_tag(player):
            return True

        return False

    def can_access_door(self, player: Player, block_position: str) -> bool:
        """Check if player can access a locked door."""
        lock_info = self.get_normalized_door_lock_info(block_position)

        if not lock_info:
            return True

        # Owner (case-insensitive)
        if self._lower(lock_info.get("owner", "")) == self._lower(player.name):
            return True

        # Trusted (case-insensitive)
        if self._is_trusted(lock_info.get("trusted", []), player.name):
            return True

        # Global trusted (owner trusts this player for all their doors)
        if self._is_globally_trusted(lock_info.get("owner", ""), player.name):
            return True

        # Admin bypass (permission only — Admin tag does NOT grant door access)
        if player.has_permission("container_locks.admin"):
            return True

        return False

    def get_normalized_door_lock_info(self, block_position: str) -> Optional[dict]:
        """Get normalized door lock info, converting old string format to new dict format."""
        lock_data = self.door_locks_db.get(block_position)
        if not lock_data:
            return None

        if isinstance(lock_data, str):
            owner_name = lock_data
            new_lock_info = {"owner": owner_name, "trusted": []}
            self.door_locks_db[block_position] = new_lock_info
            self.save_door_locks()
            return new_lock_info

        if "trusted" not in lock_data or not isinstance(lock_data["trusted"], list):
            lock_data["trusted"] = []
        return lock_data

    def _get_door_positions(self, block) -> List[str]:
        """
        For a full-height door (2-block-tall), return positions for both halves.
        For trapdoors, return just the single position.
        """
        pos = self.get_block_position(block)
        positions = [pos]

        if block.type in self.FULL_DOOR_TYPES:
            loc = block.location
            # Check block above and below for matching door type
            for dy in [1, -1]:
                try:
                    other = block.dimension.get_block_at(loc.x, loc.y + dy, loc.z)
                    if other and other.type == block.type:
                        other_pos = self.get_block_position(other)
                        if other_pos not in positions:
                            positions.append(other_pos)
                except Exception:
                    pass
        return positions

    def _find_door_lock(self, block) -> Optional[str]:
        """
        Check if any position of this door (including partner half) is locked.
        Returns the locked position key, or None.
        """
        for pos in self._get_door_positions(block):
            if pos in self.door_locks_db:
                return pos
        return None

    def _find_nearby_locked_door(self, block, player: Player) -> bool:
        """
        Check if there is a locked door within REDSTONE_CHECK_RADIUS of the given block
        that the player does NOT have access to.
        """
        loc = block.location
        r = self.REDSTONE_CHECK_RADIUS
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    try:
                        nearby = block.dimension.get_block_at(
                            loc.x + dx, loc.y + dy, loc.z + dz
                        )
                        if nearby and nearby.type in self.LOCKABLE_DOOR_TYPES:
                            door_pos = self.get_block_position(nearby)
                            lock_info = self.get_normalized_door_lock_info(door_pos)
                            if lock_info and not self.can_access_door(player, door_pos):
                                return True
                    except Exception:
                        pass
        return False

    # ======== Form payload normalizer ========

    def _extract_text_input(self, data, index: int = 0) -> str:
        """
        Normalize Endstone ModalForm on_submit payloads into a single string value.
        Handles: list/tuple, dict, JSON string (["value"]), plain string, or scalar.
        """
        # List/tuple
        if isinstance(data, (list, tuple)):
            return (data[index] if len(data) > index else "") or ""

        # Dict (fallback to positional values order)
        if isinstance(data, dict):
            try:
                return list(data.values())[index] or ""
            except Exception:
                return next(iter(data.values()), "") or ""

        # String (may be JSON-encoded)
        if isinstance(data, str):
            s = data.strip()
            try:
                parsed = json.loads(s)
                if isinstance(parsed, (list, tuple)):
                    return (parsed[index] if len(parsed) > index else "") or ""
                if isinstance(parsed, dict):
                    return list(parsed.values())[index] or ""
                return str(parsed) or ""
            except Exception:
                return s

        # Unknown type: stringify
        return str(data or "")

    # ======== UI (safe: only pass strings/values into callbacks) ========

    def show_manage_access_form(self, player: Player, block) -> None:
        """Show the container management form to the owner."""
        block_position = self.get_block_position(block)
        lock_info = self.get_normalized_lock_info(block_position)

        if not lock_info or self._lower(lock_info["owner"]) != self._lower(player.name):
            return

        trusted_list = ", ".join(lock_info.get("trusted", [])) or "None"
        global_trusted = self._get_global_trusted(player.name)
        global_trusted_list = ", ".join(global_trusted) or "None"

        form = ActionForm(
            title="Manage Container Access",
            content=(
                "Manage access for this container.\n"
                f"Owner: {lock_info['owner']}\n"
                f"Trusted (this container): {trusted_list}\n"
                f"Globally Trusted (all your locks): {global_trusted_list}"
            ),
        )

        # Pass only the position string into callbacks
        form.add_button(
            "Add Trusted Player",
            on_click=lambda p, pos=block_position: self.show_add_trusted_form(p, pos),
        )
        form.add_button(
            "Remove Trusted Player",
            on_click=lambda p, pos=block_position: self.show_remove_trusted_form(p, pos),
        )
        form.add_button(
            f"{ColorFormat.AQUA}Add Global Trusted Player",
            on_click=lambda p, pos=block_position: self.show_add_global_trusted_form(p, pos),
        )
        form.add_button(
            f"{ColorFormat.AQUA}Manage Global Trusted",
            on_click=lambda p, pos=block_position: self.show_manage_global_trusted_form(p, pos),
        )
        form.add_button(
            f"{ColorFormat.RED}Unlock Container",
            on_click=lambda p, pos=block_position: self.unlock_container(p, pos),
        )
        form.add_button("Close")

        player.send_form(form)

    # ======== Door management UI ========

    def show_door_manage_form(self, player: Player, block_position: str) -> None:
        """Show the door management form to the owner."""
        lock_info = self.get_normalized_door_lock_info(block_position)

        if not lock_info or self._lower(lock_info["owner"]) != self._lower(player.name):
            return

        trusted_list = ", ".join(lock_info.get("trusted", [])) or "None"
        global_trusted = self._get_global_trusted(player.name)
        global_trusted_list = ", ".join(global_trusted) or "None"

        form = ActionForm(
            title="Manage Door Access",
            content=(
                "Manage access for this door.\n"
                f"Owner: {lock_info['owner']}\n"
                f"Trusted (this door): {trusted_list}\n"
                f"Globally Trusted (all your locks): {global_trusted_list}"
            ),
        )

        form.add_button(
            "Add Trusted Player",
            on_click=lambda p, pos=block_position: self.show_door_add_trusted_form(p, pos),
        )
        form.add_button(
            "Remove Trusted Player",
            on_click=lambda p, pos=block_position: self.show_door_remove_trusted_form(p, pos),
        )
        form.add_button(
            f"{ColorFormat.AQUA}Add Global Trusted Player",
            on_click=lambda p, pos=block_position: self.show_add_global_trusted_form(p, pos, door=True),
        )
        form.add_button(
            f"{ColorFormat.AQUA}Manage Global Trusted",
            on_click=lambda p, pos=block_position: self.show_manage_global_trusted_form(p, pos, door=True),
        )
        form.add_button(
            f"{ColorFormat.RED}Unlock Door",
            on_click=lambda p, pos=block_position: self.unlock_door(p, pos),
        )
        form.add_button("Close")

        player.send_form(form)

    def show_door_add_trusted_form(self, player: Player, block_position: str) -> None:
        """Open a modal to add a trusted player for a door."""
        self.pending_door_blocks[player.name] = block_position

        form = ModalForm(
            title="Add Trusted Player",
            controls=[
                TextInput(label="Player name", placeholder="Steve"),
            ],
            on_submit=lambda p, data, pos=block_position: self._on_door_add_trusted_submit(
                p, data, pos
            ),
            on_close=lambda p, pos=block_position: self.show_door_manage_form(p, pos),
        )
        player.send_form(form)

    def _on_door_add_trusted_submit(self, player: Player, data, block_position: str) -> None:
        """Handle the modal submit for adding a trusted player to a door."""
        target_name = self._clean_name(self._extract_text_input(data, 0))

        if not target_name:
            self.send_cooldown_message(
                player, f"{ColorFormat.RED}Please enter a player name."
            )
            return self.show_door_manage_form(player, block_position)

        lock_info = self.get_normalized_door_lock_info(block_position)
        if not lock_info or self._lower(lock_info.get("owner", "")) != self._lower(player.name):
            self.send_cooldown_message(
                player,
                f"{ColorFormat.RED}You don't own this door or it's not locked.",
            )
            return

        if self._lower(target_name) == self._lower(player.name):
            self.send_cooldown_message(
                player,
                f"{ColorFormat.YELLOW}You are the owner; you don't need to trust yourself.",
            )
            return self.show_door_manage_form(player, block_position)

        if self._add_trusted_name(lock_info, target_name):
            self.door_locks_db[block_position] = lock_info
            # Also update partner half if exists
            self._sync_door_trust(block_position, lock_info)
            self.save_door_locks()
            self.send_cooldown_message(
                player,
                f"{ColorFormat.GREEN}{target_name} has been added to the trusted list.",
            )
        else:
            self.send_cooldown_message(
                player,
                f"{ColorFormat.YELLOW}{target_name} is already on the trusted list.",
            )

        self.show_door_manage_form(player, block_position)

    def show_door_remove_trusted_form(self, player: Player, block_position: str) -> None:
        """Show a list of trusted players to remove from a door."""
        lock_info = self.get_normalized_door_lock_info(block_position)

        if not lock_info or not lock_info.get("trusted"):
            self.send_cooldown_message(
                player, f"{ColorFormat.YELLOW}There are no trusted players to remove."
            )
            return self.show_door_manage_form(player, block_position)

        form = ActionForm(
            title="Remove Trusted Player",
            content="Select a player to remove from the trust list.",
        )

        for trusted_player in lock_info["trusted"]:
            form.add_button(
                trusted_player,
                on_click=lambda p, tp=trusted_player, pos=block_position: self.remove_door_trusted_player(
                    p, pos, tp
                ),
            )

        form.on_close = (
            lambda p, pos=block_position: self.show_door_manage_form(p, pos)
        )
        player.send_form(form)

    def remove_door_trusted_player(
        self, player: Player, block_position: str, target_name: str
    ) -> None:
        """Remove a player from a door's trusted list."""
        lock_info = self.get_normalized_door_lock_info(block_position)

        if lock_info and self._remove_trusted_name(lock_info, target_name):
            self.door_locks_db[block_position] = lock_info
            self._sync_door_trust(block_position, lock_info)
            self.save_door_locks()
            self.send_cooldown_message(
                player,
                f"{ColorFormat.GREEN}{target_name} has been removed from the trusted list.",
            )
        else:
            self.send_cooldown_message(
                player,
                f"{ColorFormat.YELLOW}{target_name} is not on the trusted list.",
            )

        self.show_door_manage_form(player, block_position)

    def unlock_door(self, player: Player, block_position: str) -> None:
        """Unlock a door and remove both halves from DB."""
        if block_position in self.door_locks_db:
            # Also remove partner half
            self._remove_door_lock_all(block_position)
            self.save_door_locks()
            self.send_cooldown_message(player, f"{ColorFormat.GREEN}Door unlocked!")

    def _sync_door_trust(self, block_position: str, lock_info: dict) -> None:
        """Sync trust list to the partner half of a double door."""
        for pos, data in list(self.door_locks_db.items()):
            if pos != block_position and isinstance(data, dict) and data.get("owner") == lock_info.get("owner"):
                # Check if this is a partner (same owner, within 1 y distance)
                try:
                    ax, ay, az = map(int, block_position.split(","))
                    bx, by, bz = map(int, pos.split(","))
                    if ax == bx and az == bz and abs(ay - by) == 1:
                        data["trusted"] = list(lock_info.get("trusted", []))
                        self.door_locks_db[pos] = data
                except Exception:
                    pass

    def _remove_door_lock_all(self, block_position: str) -> None:
        """Remove lock for a door position and its partner half."""
        lock_info = self.door_locks_db.get(block_position)
        if not lock_info:
            return
        owner = lock_info.get("owner", "") if isinstance(lock_info, dict) else lock_info
        del self.door_locks_db[block_position]
        # Remove partner half
        try:
            ax, ay, az = map(int, block_position.split(","))
            for dy in [1, -1]:
                partner_pos = f"{ax},{ay + dy},{az}"
                partner = self.door_locks_db.get(partner_pos)
                if partner:
                    partner_owner = partner.get("owner", "") if isinstance(partner, dict) else partner
                    if self._lower(partner_owner) == self._lower(owner):
                        del self.door_locks_db[partner_pos]
        except Exception:
            pass

    def show_add_trusted_form(self, player: Player, block_position: str) -> None:
        """Open a modal with a text input to add a trusted player (safe: no native objects captured)."""

        # Remember which container this player is editing
        self.pending_trust_blocks[player.name] = block_position

        form = ModalForm(
            title="Add Trusted Player",
            controls=[
                TextInput(label="Player name", placeholder="Steve"),
            ],
            on_submit=lambda p, data, pos=block_position: self._on_add_trusted_submit(
                p, data, pos
            ),
            on_close=lambda p, pos=block_position: self._return_to_manage_form(p, pos),
        )
        player.send_form(form)

    def _return_to_manage_form(self, player: Player, block_position: str) -> None:
        """Re-open manage form by reconstructing the Block from coordinates at callback time."""
        try:
            x, y, z = map(int, block_position.split(","))
            block = player.dimension.get_block_at(x, y, z)
            self.show_manage_access_form(player, block)
        except Exception:
            self.send_cooldown_message(
                player,
                f"{ColorFormat.YELLOW}That container is no longer available.",
            )

    def _on_add_trusted_submit(self, player: Player, data, block_position: str) -> None:
        """Handle the modal submit for adding a trusted player."""
        target_name = self._clean_name(self._extract_text_input(data, 0))

        if not target_name:
            self.send_cooldown_message(
                player, f"{ColorFormat.RED}Please enter a player name."
            )
            return self._return_to_manage_form(player, block_position)

        lock_info = self.get_normalized_lock_info(block_position)
        if not lock_info or self._lower(lock_info.get("owner", "")) != self._lower(player.name):
            self.send_cooldown_message(
                player,
                f"{ColorFormat.RED}You don't own this container or it's not locked.",
            )
            return

        if self._lower(target_name) == self._lower(player.name):
            self.send_cooldown_message(
                player,
                f"{ColorFormat.YELLOW}You are the owner; you don't need to trust yourself.",
            )
            return self._return_to_manage_form(player, block_position)

        if self._add_trusted_name(lock_info, target_name):
            self.locks_db[block_position] = lock_info
            self.save_locks()
            self.send_cooldown_message(
                player,
                f"{ColorFormat.GREEN}{target_name} has been added to the trusted list.",
            )
        else:
            self.send_cooldown_message(
                player,
                f"{ColorFormat.YELLOW}{target_name} is already on the trusted list.",
            )

        self._return_to_manage_form(player, block_position)

    def show_remove_trusted_form(self, player: Player, block_position: str) -> None:
        """Show a list of trusted players to remove (safe: only position string captured)."""
        lock_info = self.get_normalized_lock_info(block_position)

        if not lock_info or not lock_info.get("trusted"):
            self.send_cooldown_message(
                player, f"{ColorFormat.YELLOW}There are no trusted players to remove."
            )
            return self._return_to_manage_form(player, block_position)

        form = ActionForm(
            title="Remove Trusted Player",
            content="Select a player to remove from the trust list.",
        )

        for trusted_player in lock_info["trusted"]:
            form.add_button(
                trusted_player,
                on_click=lambda p, tp=trusted_player, pos=block_position: self.remove_trusted_player(
                    p, pos, tp
                ),
            )

        form.on_close = (
            lambda p, pos=block_position: self._return_to_manage_form(p, pos)
        )
        player.send_form(form)

    def remove_trusted_player(
        self, player: Player, block_position: str, target_name: str
    ) -> None:
        """Remove a player from the trusted list."""
        lock_info = self.get_normalized_lock_info(block_position)

        if lock_info and self._remove_trusted_name(lock_info, target_name):
            self.locks_db[block_position] = lock_info
            self.save_locks()
            self.send_cooldown_message(
                player,
                f"{ColorFormat.GREEN}{target_name} has been removed from the trusted list.",
            )
        else:
            self.send_cooldown_message(
                player,
                f"{ColorFormat.YELLOW}{target_name} is not on the trusted list.",
            )

        # Re-open manage form safely
        self._return_to_manage_form(player, block_position)

    # ======== Global trust UI ========

    def show_add_global_trusted_form(self, player: Player, block_position: str, door: bool = False) -> None:
        """Open a modal to add a globally trusted player."""
        form = ModalForm(
            title="Add Global Trusted Player",
            controls=[
                TextInput(
                    label="This player will have access to ALL your locked containers and doors.",
                    placeholder="Player name",
                ),
            ],
            on_submit=lambda p, data, pos=block_position, d=door: self._on_add_global_trusted_submit(
                p, data, pos, d
            ),
            on_close=lambda p, pos=block_position, d=door: (
                self.show_door_manage_form(p, pos) if d else self._return_to_manage_form(p, pos)
            ),
        )
        player.send_form(form)

    def _on_add_global_trusted_submit(
        self, player: Player, data, block_position: str, door: bool = False
    ) -> None:
        """Handle the modal submit for adding a global trusted player."""
        target_name = self._clean_name(self._extract_text_input(data, 0))

        if not target_name:
            self.send_cooldown_message(
                player, f"{ColorFormat.RED}Please enter a player name."
            )
            if door:
                return self.show_door_manage_form(player, block_position)
            return self._return_to_manage_form(player, block_position)

        if self._lower(target_name) == self._lower(player.name):
            self.send_cooldown_message(
                player,
                f"{ColorFormat.YELLOW}You don't need to globally trust yourself.",
            )
            if door:
                return self.show_door_manage_form(player, block_position)
            return self._return_to_manage_form(player, block_position)

        if self._add_global_trusted(player.name, target_name):
            self.save_global_trusted()
            self.send_cooldown_message(
                player,
                f"{ColorFormat.GREEN}{target_name} now has access to ALL your locked containers and doors.",
            )
        else:
            self.send_cooldown_message(
                player,
                f"{ColorFormat.YELLOW}{target_name} is already globally trusted.",
            )

        if door:
            self.show_door_manage_form(player, block_position)
        else:
            self._return_to_manage_form(player, block_position)

    def show_manage_global_trusted_form(
        self, player: Player, block_position: str, door: bool = False
    ) -> None:
        """Show a list of globally trusted players with remove buttons."""
        global_list = self._get_global_trusted(player.name)

        if not global_list:
            self.send_cooldown_message(
                player, f"{ColorFormat.YELLOW}You have no globally trusted players."
            )
            if door:
                return self.show_door_manage_form(player, block_position)
            return self._return_to_manage_form(player, block_position)

        form = ActionForm(
            title="Manage Global Trusted",
            content="Select a player to remove from your global trusted list.\nThis will revoke their access to ALL your locks.",
        )

        for trusted_player in global_list:
            form.add_button(
                f"{ColorFormat.RED}✕ {ColorFormat.RESET}{trusted_player}",
                on_click=lambda p, tp=trusted_player, pos=block_position, d=door: self.remove_global_trusted_player(
                    p, pos, tp, d
                ),
            )

        form.on_close = lambda p, pos=block_position, d=door: (
            self.show_door_manage_form(p, pos) if d else self._return_to_manage_form(p, pos)
        )
        player.send_form(form)

    def remove_global_trusted_player(
        self, player: Player, block_position: str, target_name: str, door: bool = False
    ) -> None:
        """Remove a player from the global trusted list."""
        if self._remove_global_trusted(player.name, target_name):
            self.save_global_trusted()
            self.send_cooldown_message(
                player,
                f"{ColorFormat.GREEN}{target_name} has been removed from your global trusted list.",
            )
        else:
            self.send_cooldown_message(
                player,
                f"{ColorFormat.YELLOW}{target_name} is not on your global trusted list.",
            )

        if door:
            self.show_door_manage_form(player, block_position)
        else:
            self._return_to_manage_form(player, block_position)

    def unlock_container(self, player: Player, block_position: str) -> None:
        """Unlock a container."""
        if block_position in self.locks_db:
            del self.locks_db[block_position]
            self.save_locks()
            self.send_cooldown_message(player, "Container unlocked!")

    # ======== Events ========

    @event_handler
    def on_player_interact(self, event: PlayerInteractEvent) -> None:
        """Handle player interaction with blocks."""
        player = event.player
        block = event.block
        item = player.inventory.item_in_main_hand

        if not block:
            return

        # --- Door / Trapdoor interactions ---
        if block.type in self.LOCKABLE_DOOR_TYPES:
            self._handle_door_interact(event, player, block, item)
            return

        # --- Redstone activator near a locked door ---
        if block.type in self.REDSTONE_ACTIVATORS:
            if self._find_nearby_locked_door(block, player):
                event.is_cancelled = True
                self.send_cooldown_message(
                    player,
                    f"{ColorFormat.RED}This is near a locked door. You cannot use it.",
                )
            return

        # --- Container interactions (existing logic) ---
        if block.type not in self.LOCKABLE_TYPES:
            return

        block_position = self.get_block_position(block)
        lock_info = self.get_normalized_lock_info(block_position)

        # Lock item flow
        if item and item.type == "ninjos:lock":
            event.is_cancelled = True

            if lock_info:
                # Owner managing access
                if self._lower(lock_info["owner"]) == self._lower(player.name):
                    pid = str(player.unique_id)
                    if pid not in self.form_open_cooldown:
                        self.form_open_cooldown.add(pid)
                        self.show_manage_access_form(player, block)

                        # Clear cooldown after ~2s (40 ticks)
                        def remove_cooldown():
                            self.form_open_cooldown.discard(pid)

                        self.server.scheduler.run_task(self, remove_cooldown, delay=40)
                else:
                    self.send_cooldown_message(
                        player,
                        f"{ColorFormat.RED}You are not the owner of this container. It belongs to {lock_info['owner']}.",
                    )
            else:
                self.locks_db[block_position] = {"owner": player.name, "trusted": []}
                self.save_locks()
                self.send_cooldown_message(player, "Container locked!")

        # Master lock (admin) flow
        elif item and item.type == "ninjos:masterlock":
            event.is_cancelled = True

            if not player.has_permission("container_locks.admin") and not self._has_admin_tag(player):
                self.send_cooldown_message(
                    player, "You do not have permission to use the master key."
                )
                return

            if lock_info:
                del self.locks_db[block_position]
                self.save_locks()
                self.send_cooldown_message(
                    player,
                    f"Container owned by {lock_info['owner']} unlocked with the master key!",
                )
            else:
                self.send_cooldown_message(player, "This container is already unlocked!")

        # Access checks for normal interaction
        elif not self.can_access_container(player, block):
            event.is_cancelled = True
            if lock_info:
                self.send_cooldown_message(
                    player,
                    f"You are not allowed to open this container. It belongs to {lock_info['owner']}.",
                )
        else:
            # Show ownership info when accessing any locked container
            if lock_info:
                if self._lower(lock_info["owner"]) == self._lower(player.name):
                    self.send_cooldown_message(
                        player, f"{ColorFormat.GREEN}Your locked container."
                    )
                elif self._is_trusted(lock_info.get("trusted", []), player.name):
                    self.send_cooldown_message(
                        player,
                        f"{ColorFormat.YELLOW}Locked By: {lock_info['owner']} (You have access)",
                    )
                elif self._is_globally_trusted(lock_info.get("owner", ""), player.name):
                    self.send_cooldown_message(
                        player,
                        f"{ColorFormat.AQUA}Locked By: {lock_info['owner']} (Globally trusted)",
                    )
                elif player.has_permission("container_locks.admin") or self._has_admin_tag(player):
                    self.send_cooldown_message(
                        player,
                        f"{ColorFormat.BLUE}Locked By: {lock_info['owner']} (Admin access)",
                    )
                else:
                    self.send_cooldown_message(
                        player, f"{ColorFormat.GREEN}Locked By: {lock_info['owner']}"
                    )

    def _handle_door_interact(
        self, event: PlayerInteractEvent, player: Player, block, item
    ) -> None:
        """Handle all door/trapdoor interactions."""
        block_position = self.get_block_position(block)
        locked_pos = self._find_door_lock(block)
        lock_info = self.get_normalized_door_lock_info(locked_pos) if locked_pos else None

        # --- ninjos:owner item flow (operator-only locking + management) ---
        if item and item.type == "ninjos:owner":
            event.is_cancelled = True

            if lock_info:
                # Already locked — owner opens management UI
                if self._lower(lock_info["owner"]) == self._lower(player.name):
                    pid = str(player.unique_id)
                    if pid not in self.form_open_cooldown:
                        self.form_open_cooldown.add(pid)
                        self.show_door_manage_form(player, locked_pos)

                        def remove_cd():
                            self.form_open_cooldown.discard(pid)

                        self.server.scheduler.run_task(self, remove_cd, delay=40)
                else:
                    self.send_cooldown_message(
                        player,
                        f"{ColorFormat.RED}This door is locked by {lock_info['owner']}.",
                    )
            else:
                # Not locked yet — only operators can lock (Admin tag NOT sufficient)
                if not player.has_permission("container_locks.admin"):
                    self.send_cooldown_message(
                        player,
                        f"{ColorFormat.RED}Only operators can lock doors.",
                    )
                    return

                # Lock all positions for this door (both halves for full doors)
                new_lock = {"owner": player.name, "trusted": []}
                for pos in self._get_door_positions(block):
                    self.door_locks_db[pos] = {
                        "owner": player.name,
                        "trusted": [],
                    }
                self.save_door_locks()
                self.send_cooldown_message(
                    player, f"{ColorFormat.GREEN}Door locked!"
                )
            return

        # --- Master lock for doors ---
        if item and item.type == "ninjos:masterlock":
            event.is_cancelled = True

            # Admin tag does NOT grant master key access for doors
            if not player.has_permission("container_locks.admin"):
                self.send_cooldown_message(
                    player, "You do not have permission to use the master key on doors."
                )
                return

            if lock_info and locked_pos:
                self._remove_door_lock_all(locked_pos)
                self.save_door_locks()
                self.send_cooldown_message(
                    player,
                    f"Door owned by {lock_info['owner']} unlocked with the master key!",
                )
            else:
                self.send_cooldown_message(player, "This door is already unlocked!")
            return

        # --- Normal interaction: block if locked and no access ---
        if lock_info and locked_pos:
            if not self.can_access_door(player, locked_pos):
                event.is_cancelled = True
                self.send_cooldown_message(
                    player,
                    f"{ColorFormat.RED}This door is locked by {lock_info['owner']}.",
                )
            else:
                # Toggle allowed_opens for authorized players so the monitor
                # doesn't fight with their legitimate open/close actions.
                all_positions = self._get_door_positions(block)
                if locked_pos in self.allowed_opens:
                    # Player is closing the door — remove from allowed
                    for p in all_positions:
                        self.allowed_opens.pop(p, None)
                else:
                    # Player is opening the door — mark as allowed
                    now = time.time()
                    for p in all_positions:
                        self.allowed_opens[p] = now

                # Show ownership info
                if self._lower(lock_info["owner"]) == self._lower(player.name):
                    self.send_cooldown_message(
                        player, f"{ColorFormat.GREEN}Your locked door."
                    )
                elif self._is_trusted(lock_info.get("trusted", []), player.name):
                    self.send_cooldown_message(
                        player,
                        f"{ColorFormat.YELLOW}Locked By: {lock_info['owner']} (You have access)",
                    )
                elif self._is_globally_trusted(lock_info.get("owner", ""), player.name):
                    self.send_cooldown_message(
                        player,
                        f"{ColorFormat.AQUA}Locked By: {lock_info['owner']} (Globally trusted)",
                    )
                elif player.has_permission("container_locks.admin"):
                    self.send_cooldown_message(
                        player,
                        f"{ColorFormat.BLUE}Locked By: {lock_info['owner']} (Admin access)",
                    )

    @event_handler
    def on_block_break(self, event: BlockBreakEvent) -> None:
        """Handle block breaking."""
        player = event.player
        block = event.block

        # --- Container break protection ---
        if block.type in self.LOCKABLE_TYPES:
            block_position = self.get_block_position(block)
            lock_info = self.get_normalized_lock_info(block_position)

            if lock_info:
                if self._lower(lock_info["owner"]) == self._lower(player.name):
                    del self.locks_db[block_position]
                    self.save_locks()
                elif player.has_permission("container_locks.admin") or self._has_admin_tag(player):
                    del self.locks_db[block_position]
                    self.save_locks()
                    self.send_cooldown_message(
                        player,
                        f"You have broken a container owned by {lock_info['owner']}.",
                    )
                else:
                    event.is_cancelled = True
                    self.send_cooldown_message(
                        player,
                        f"You are not allowed to break this container. It belongs to {lock_info['owner']}.",
                    )
            return

        # --- Door / Trapdoor break protection ---
        if block.type in self.LOCKABLE_DOOR_TYPES:
            locked_pos = self._find_door_lock(block)
            if locked_pos:
                lock_info = self.get_normalized_door_lock_info(locked_pos)
                if lock_info:
                    if self._lower(lock_info["owner"]) == self._lower(player.name):
                        self._remove_door_lock_all(locked_pos)
                        self.save_door_locks()
                    elif player.has_permission("container_locks.admin"):
                        owner_name = lock_info["owner"]
                        self._remove_door_lock_all(locked_pos)
                        self.save_door_locks()
                        self.send_cooldown_message(
                            player,
                            f"You have broken a door owned by {owner_name}.",
                        )
                    else:
                        event.is_cancelled = True
                        self.send_cooldown_message(
                            player,
                            f"{ColorFormat.RED}You are not allowed to break this door. It belongs to {lock_info['owner']}.",
                        )
            return

    @event_handler
    def on_block_place(self, event: BlockPlaceEvent) -> None:
        """Prevent placing redstone components near locked doors."""
        player = event.player
        block = event.block

        if not block or block.type not in self.REDSTONE_PLACEABLE_BLOCKS:
            return

        if self._find_nearby_locked_door(block, player):
            event.is_cancelled = True
            self.send_cooldown_message(
                player,
                f"{ColorFormat.RED}You cannot place redstone components near a locked door.",
            )
    # ======== Command handling ========

    def on_command(self, sender: CommandSender, command: Command, args: List[str]) -> bool:
        """Endstone-style command handler. Routes to our trust logic."""
        if command.name == "trust":
            return self.trust_command(sender, command, args)
        return False

    def trust_command(
        self, sender: CommandSender, command: Command, args: List[str]
    ) -> bool:
        """Handle /trust command for managing trusted players."""
        if not isinstance(sender, Player):
            sender.send_message(f"{ColorFormat.RED}This command can only be used by players.")
            return True

        player = sender

        if len(args) < 1:
            player.send_message(
                f"{ColorFormat.YELLOW}Usage: /trust <add|remove|list|globaladd|globalremove|globallist> [playername]"
            )
            return True

        action = args[0].lower()

        # --- Global trust subcommands (no container needed) ---
        if action == "globaladd":
            if len(args) < 2:
                player.send_message(f"{ColorFormat.RED}Usage: /trust globaladd <playername>")
                return True
            target_name = self._clean_name(args[1])
            if self._lower(target_name) == self._lower(player.name):
                player.send_message(
                    f"{ColorFormat.YELLOW}You don't need to globally trust yourself."
                )
                return True
            if self._add_global_trusted(player.name, target_name):
                self.save_global_trusted()
                player.send_message(
                    f"{ColorFormat.GREEN}{target_name} now has access to ALL your locked containers and doors."
                )
            else:
                player.send_message(
                    f"{ColorFormat.YELLOW}{target_name} is already globally trusted."
                )
            return True

        elif action == "globalremove":
            if len(args) < 2:
                player.send_message(f"{ColorFormat.RED}Usage: /trust globalremove <playername>")
                return True
            target_name = self._clean_name(args[1])
            if self._remove_global_trusted(player.name, target_name):
                self.save_global_trusted()
                player.send_message(
                    f"{ColorFormat.GREEN}{target_name} has been removed from your global trusted list."
                )
            else:
                player.send_message(
                    f"{ColorFormat.YELLOW}{target_name} is not on your global trusted list."
                )
            return True

        elif action == "globallist":
            global_list = self._get_global_trusted(player.name)
            if global_list:
                player.send_message(
                    f"{ColorFormat.GREEN}Globally trusted players: {', '.join(global_list)}"
                )
            else:
                player.send_message(f"{ColorFormat.YELLOW}No globally trusted players.")
            return True

        # --- Per-container trust subcommands (require a pending container) ---
        block_position = self.pending_trust_blocks.get(player.name)
        if not block_position:
            player.send_message(
                f"{ColorFormat.RED}You need to use the lock item on a container first."
            )
            return True

        lock_info = self.get_normalized_lock_info(block_position)
        if not lock_info or self._lower(lock_info["owner"]) != self._lower(player.name):
            player.send_message(
                f"{ColorFormat.RED}You don't own this container or it's not locked."
            )
            return True

        if action == "add":
            if len(args) < 2:
                player.send_message(f"{ColorFormat.RED}Usage: /trust add <playername>")
                return True

            target_name = self._clean_name(args[1])
            if self._lower(target_name) == self._lower(player.name):
                player.send_message(
                    f"{ColorFormat.YELLOW}You are the owner; you don't need to trust yourself."
                )
                return True

            if self._add_trusted_name(lock_info, target_name):
                self.locks_db[block_position] = lock_info
                self.save_locks()
                player.send_message(
                    f"{ColorFormat.GREEN}{target_name} has been added to the trusted list."
                )
            else:
                player.send_message(
                    f"{ColorFormat.YELLOW}{target_name} is already on the trusted list."
                )

        elif action == "remove":
            if len(args) < 2:
                player.send_message(
                    f"{ColorFormat.RED}Usage: /trust remove <playername>"
                )
                return True

            target_name = self._clean_name(args[1])
            if self._remove_trusted_name(lock_info, target_name):
                self.locks_db[block_position] = lock_info
                self.save_locks()
                player.send_message(
                    f"{ColorFormat.GREEN}{target_name} has been removed from the trusted list."
                )
            else:
                player.send_message(
                    f"{ColorFormat.YELLOW}{target_name} is not on the trusted list."
                )

        elif action == "list":
            trusted_list = lock_info.get("trusted", [])
            if trusted_list:
                player.send_message(
                    f"{ColorFormat.GREEN}Trusted players: {', '.join(trusted_list)}"
                )
            else:
                player.send_message(f"{ColorFormat.YELLOW}No trusted players.")
        else:
            player.send_message(
                f"{ColorFormat.YELLOW}Usage: /trust <add|remove|list|globaladd|globalremove|globallist> [playername]"
            )

        return True

    @event_handler
    def on_player_quit(self, event: PlayerQuitEvent) -> None:
        """Clean up cooldowns when player leaves."""
        player_id = str(event.player.unique_id)
        player_name = event.player.name
        self.message_cooldowns.pop(player_id, None)
        self.form_open_cooldown.discard(player_id)
        self.action_bar_cooldowns.pop(player_id, None)
        self.pending_trust_blocks.pop(player_name, None)
        self.pending_door_blocks.pop(player_name, None)
