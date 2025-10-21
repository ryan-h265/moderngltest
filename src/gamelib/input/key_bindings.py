"""
Key Bindings

Manages rebindable key→command mappings with save/load support.
"""

from typing import Dict, Optional, List, Tuple
import json
from pathlib import Path
from moderngl_window.context.base.keys import BaseKeys
from .input_commands import InputCommand


class KeyBindings:
    """
    Manages key bindings with save/load support.

    Features:
    - Default bindings
    - Rebindable keys
    - Save/load to JSON
    - Multiple keys per command
    - Mouse button support
    """

    def __init__(self, keys: BaseKeys, config_path: Optional[Path] = None):
        """
        Initialize key bindings.

        Args:
            config_path: Path to save bindings JSON (default: ./keybindings.json)
        """
        self.keys = keys
        self.config_path = config_path or Path("keybindings.json")

        # Key code → Command mappings
        self.keyboard_bindings: Dict[int, InputCommand] = {}
        self.mouse_bindings: Dict[int, InputCommand] = {}

        # Reverse lookup: Command → Keys (for UI display)
        self.command_to_keys: Dict[InputCommand, List[int]] = {}

        # Set default bindings
        self._set_default_bindings()

        # Try to load user bindings
        self.load_bindings()

        # Update reverse lookup
        self._update_command_to_keys()

    def _set_default_bindings(self):
        """Set default key bindings"""

        # ====================================================================
        # Camera Movement (WASD + QE)
        # ====================================================================
        self.keyboard_bindings[self.keys.W] = InputCommand.CAMERA_MOVE_FORWARD    # W
        self.keyboard_bindings[self.keys.S] = InputCommand.CAMERA_MOVE_BACKWARD   # S
        self.keyboard_bindings[self.keys.A] = InputCommand.CAMERA_MOVE_LEFT       # A
        self.keyboard_bindings[self.keys.D] = InputCommand.CAMERA_MOVE_RIGHT      # D
        self.keyboard_bindings[self.keys.Q] = InputCommand.CAMERA_MOVE_DOWN       # Q
        self.keyboard_bindings[self.keys.E] = InputCommand.CAMERA_MOVE_UP         # E

        # Alternative arrow keys for camera movement
        # self.keyboard_bindings[265] = InputCommand.CAMERA_MOVE_FORWARD  # UP
        # self.keyboard_bindings[264] = InputCommand.CAMERA_MOVE_BACKWARD # DOWN
        # self.keyboard_bindings[263] = InputCommand.CAMERA_MOVE_LEFT     # LEFT
        # self.keyboard_bindings[262] = InputCommand.CAMERA_MOVE_RIGHT    # RIGHT

        # ====================================================================
        # Game Actions (Future - examples)
        # ====================================================================
        # self.keyboard_bindings[32] = InputCommand.GAME_JUMP           # SPACE
        # self.keyboard_bindings[340] = InputCommand.GAME_CROUCH        # LEFT SHIFT
        # self.keyboard_bindings[341] = InputCommand.GAME_SPRINT        # LEFT CTRL
        # self.keyboard_bindings[70] = InputCommand.GAME_INTERACT       # F
        # self.keyboard_bindings[82] = InputCommand.GAME_RELOAD         # R
        # self.keyboard_bindings[71] = InputCommand.GAME_THROW          # G

        # ====================================================================
        # UI Actions (Future - examples)
        # ====================================================================
        # self.keyboard_bindings[73] = InputCommand.UI_OPEN_INVENTORY  # I
        # self.keyboard_bindings[77] = InputCommand.UI_OPEN_MAP        # M
        # self.keyboard_bindings[256] = InputCommand.UI_CANCEL         # ESC (alternative)
        # self.keyboard_bindings[258] = InputCommand.UI_TAB_NEXT       # TAB
        # self.keyboard_bindings[257] = InputCommand.UI_CONFIRM        # ENTER

        # ====================================================================
        # System Commands
        # ====================================================================
        self.keyboard_bindings[256] = InputCommand.SYSTEM_TOGGLE_MOUSE  # ESC
        self.keyboard_bindings[290] = InputCommand.SYSTEM_SCREENSHOT    # F1
        self.keyboard_bindings[293] = InputCommand.SYSTEM_TOGGLE_DEBUG  # F4
        # self.keyboard_bindings[294] = InputCommand.SYSTEM_QUICK_SAVE  # F5
        # self.keyboard_bindings[295] = InputCommand.SYSTEM_QUICK_LOAD  # F9

        # ====================================================================
        # Mouse Bindings (Future - examples)
        # ====================================================================
        # self.mouse_bindings[1] = InputCommand.OBJECT_SELECT         # Left click
        # self.mouse_bindings[2] = InputCommand.GAME_ATTACK           # Right click
        # self.mouse_bindings[3] = InputCommand.GAME_ATTACK_SECONDARY # Middle click

    def _update_command_to_keys(self):
        """Update reverse lookup (command → keys)"""
        self.command_to_keys.clear()

        # Keyboard
        for key, command in self.keyboard_bindings.items():
            if command not in self.command_to_keys:
                self.command_to_keys[command] = []
            self.command_to_keys[command].append(key)

        # Mouse
        for button, command in self.mouse_bindings.items():
            if command not in self.command_to_keys:
                self.command_to_keys[command] = []
            # Negative to distinguish from keyboard
            self.command_to_keys[command].append(-button)

    def get_command(self, key: int, is_mouse: bool = False) -> Optional[InputCommand]:
        """
        Get command for a key or mouse button.

        Args:
            key: Key code or mouse button
            is_mouse: True if this is a mouse button

        Returns:
            InputCommand if bound, None otherwise
        """
        bindings = self.mouse_bindings if is_mouse else self.keyboard_bindings
        return bindings.get(key)

    def get_keys_for_command(self, command: InputCommand) -> List[int]:
        """
        Get all keys bound to a command.

        Args:
            command: The command

        Returns:
            List of key codes (negative for mouse buttons)
        """
        return self.command_to_keys.get(command, [])

    def get_key_name(self, key: int) -> str:
        """
        Get human-readable name for a key.

        Args:
            key: Key code (negative for mouse buttons)

        Returns:
            Key name string
        """
        if key < 0:
            # Mouse button
            mouse_names = {-1: "Left Click", -2: "Right Click", -3: "Middle Click"}
            return mouse_names.get(key, f"Mouse{abs(key)}")

        # Keyboard keys (moderngl_window codes)
        key_names = {
            32: "Space", 256: "ESC", 257: "Enter", 258: "Tab",
            259: "Backspace", 260: "Insert", 261: "Delete",
            262: "Right", 263: "Left", 264: "Down", 265: "Up",
            290: "F1", 291: "F2", 292: "F3", 293: "F4", 294: "F5",
            295: "F6", 296: "F7", 297: "F8", 298: "F9", 299: "F10",
            300: "F11", 301: "F12",
            340: "Left Shift", 341: "Left Ctrl", 342: "Left Alt",
            344: "Right Shift", 345: "Right Ctrl", 346: "Right Alt",
        }

        if key in key_names:
            return key_names[key]

        # Letter keys (65-90 = A-Z)
        if 65 <= key <= 90:
            return chr(key)

        # Number keys (48-57 = 0-9)
        if 48 <= key <= 57:
            return chr(key)

        return f"Key{key}"

    def rebind_key(self, command: InputCommand, new_key: int, is_mouse: bool = False):
        """
        Rebind a command to a new key.

        This replaces the current binding.

        Args:
            command: Command to rebind
            new_key: New key code
            is_mouse: True if new_key is a mouse button
        """
        # Remove old binding for this command
        bindings = self.mouse_bindings if is_mouse else self.keyboard_bindings

        # Find and remove old keys for this command
        old_keys = [k for k, cmd in bindings.items() if cmd == command]
        for old_key in old_keys:
            del bindings[old_key]

        # Add new binding
        bindings[new_key] = command

        # Update reverse lookup
        self._update_command_to_keys()

    def add_binding(self, command: InputCommand, key: int, is_mouse: bool = False):
        """
        Add an additional key binding for a command.

        Allows multiple keys for same command.

        Args:
            command: Command to bind
            key: Key code to add
            is_mouse: True if key is a mouse button
        """
        bindings = self.mouse_bindings if is_mouse else self.keyboard_bindings
        bindings[key] = command
        self._update_command_to_keys()

    def remove_binding(self, key: int, is_mouse: bool = False):
        """
        Remove a key binding.

        Args:
            key: Key to unbind
            is_mouse: True if key is a mouse button
        """
        bindings = self.mouse_bindings if is_mouse else self.keyboard_bindings
        if key in bindings:
            del bindings[key]
            self._update_command_to_keys()

    def clear_bindings_for_command(self, command: InputCommand):
        """
        Clear all bindings for a command.

        Args:
            command: Command to clear
        """
        # Remove from keyboard
        self.keyboard_bindings = {
            k: cmd for k, cmd in self.keyboard_bindings.items()
            if cmd != command
        }

        # Remove from mouse
        self.mouse_bindings = {
            k: cmd for k, cmd in self.mouse_bindings.items()
            if cmd != command
        }

        self._update_command_to_keys()

    def save_bindings(self):
        """Save bindings to JSON file"""
        data = {
            "keyboard": {str(k): v.name for k, v in self.keyboard_bindings.items()},
            "mouse": {str(k): v.name for k, v in self.mouse_bindings.items()}
        }

        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)

    def load_bindings(self) -> bool:
        """
        Load bindings from JSON file.

        Returns:
            True if loaded successfully, False if file doesn't exist
        """
        if not self.config_path.exists():
            return False

        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)

            # Clear current bindings
            self.keyboard_bindings.clear()
            self.mouse_bindings.clear()

            # Load keyboard bindings
            for key_str, command_name in data.get("keyboard", {}).items():
                try:
                    key = int(key_str)
                    command = InputCommand[command_name]
                    self.keyboard_bindings[key] = command
                except (ValueError, KeyError) as e:
                    print(f"Warning: Invalid binding {key_str}→{command_name}: {e}")

            # Load mouse bindings
            for button_str, command_name in data.get("mouse", {}).items():
                try:
                    button = int(button_str)
                    command = InputCommand[command_name]
                    self.mouse_bindings[button] = command
                except (ValueError, KeyError) as e:
                    print(f"Warning: Invalid binding {button_str}→{command_name}: {e}")

            self._update_command_to_keys()
            return True

        except Exception as e:
            print(f"Error loading key bindings: {e}")
            return False

    def reset_to_defaults(self):
        """Reset all bindings to defaults"""
        self.keyboard_bindings.clear()
        self.mouse_bindings.clear()
        self._set_default_bindings()
        self._update_command_to_keys()

    def export_bindings(self) -> Dict:
        """
        Export bindings as a dictionary.

        Returns:
            Dict with keyboard and mouse bindings
        """
        return {
            "keyboard": {k: v.name for k, v in self.keyboard_bindings.items()},
            "mouse": {k: v.name for k, v in self.mouse_bindings.items()}
        }

    def import_bindings(self, data: Dict):
        """
        Import bindings from a dictionary.

        Args:
            data: Dict with 'keyboard' and 'mouse' keys
        """
        self.keyboard_bindings.clear()
        self.mouse_bindings.clear()

        for key, command_name in data.get("keyboard", {}).items():
            try:
                command = InputCommand[command_name]
                self.keyboard_bindings[int(key)] = command
            except (ValueError, KeyError):
                pass

        for button, command_name in data.get("mouse", {}).items():
            try:
                command = InputCommand[command_name]
                self.mouse_bindings[int(button)] = command
            except (ValueError, KeyError):
                pass

        self._update_command_to_keys()
