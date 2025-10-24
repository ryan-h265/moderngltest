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
        self.keyboard_bindings[self.keys.LEFT_SHIFT] = InputCommand.CAMERA_MOVE_DOWN       # SHIFT
        self.keyboard_bindings[self.keys.SPACE] = InputCommand.CAMERA_MOVE_UP         # SPACE

        # Alternative arrow keys for camera movement
        # self.keyboard_bindings[self.keys.UP] = InputCommand.CAMERA_MOVE_FORWARD  # UP
        # self.keyboard_bindings[self.keys.DOWN] = InputCommand.CAMERA_MOVE_BACKWARD # DOWN
        # self.keyboard_bindings[self.keys.LEFT] = InputCommand.CAMERA_MOVE_LEFT     # LEFT
        # self.keyboard_bindings[self.keys.RIGHT] = InputCommand.CAMERA_MOVE_RIGHT    # RIGHT

        # ====================================================================
        # Game Actions (Future - examples)
        # ====================================================================
        # self.keyboard_bindings[self.keys.SPACE] = InputCommand.GAME_JUMP           # SPACE
        # self.keyboard_bindings[self.keys.LEFT_SHIFT] = InputCommand.GAME_CROUCH        # LEFT SHIFT
        # self.keyboard_bindings[self.keys.LEFT_CTRL] = InputCommand.GAME_SPRINT        # LEFT CTRL
        # self.keyboard_bindings[self.keys.F] = InputCommand.GAME_INTERACT       # F
        # self.keyboard_bindings[self.keys.R] = InputCommand.GAME_RELOAD         # R
        # self.keyboard_bindings[self.keys.G] = InputCommand.GAME_THROW          # G

        # ====================================================================
        # UI Actions (Future - examples)
        # ====================================================================
        # self.keyboard_bindings[self.keys.I] = InputCommand.UI_OPEN_INVENTORY  # I
        # self.keyboard_bindings[self.keys.M] = InputCommand.UI_OPEN_MAP        # M
        # self.keyboard_bindings[self.keys.ESCAPE] = InputCommand.UI_CANCEL         # ESC (alternative)
        # self.keyboard_bindings[self.keys.TAB] = InputCommand.UI_TAB_NEXT       # TAB
        # self.keyboard_bindings[self.keys.ENTER] = InputCommand.UI_CONFIRM        # ENTER

        # ====================================================================
        # System Commands
        # ====================================================================
        self.keyboard_bindings[self.keys.ESCAPE] = InputCommand.SYSTEM_TOGGLE_MOUSE  # ESC
        self.keyboard_bindings[self.keys.F1] = InputCommand.SYSTEM_SCREENSHOT    # F1
        self.keyboard_bindings[self.keys.F4] = InputCommand.SYSTEM_TOGGLE_DEBUG  # F4
        # self.keyboard_bindings[self.keys.F5] = InputCommand.SYSTEM_QUICK_SAVE  # F5
        self.keyboard_bindings[self.keys.F6] = InputCommand.SYSTEM_TOGGLE_SSAO   # F6
        self.keyboard_bindings[self.keys.F7] = InputCommand.SYSTEM_CYCLE_AA_MODE # F7
        self.keyboard_bindings[self.keys.F8] = InputCommand.SYSTEM_TOGGLE_MSAA   # F8
        self.keyboard_bindings[self.keys.F9] = InputCommand.SYSTEM_TOGGLE_SMAA   # F9
        self.keyboard_bindings[self.keys.PAGE_UP] = InputCommand.SYSTEM_EXPOSURE_INCREASE
        self.keyboard_bindings[self.keys.PAGE_DOWN] = InputCommand.SYSTEM_EXPOSURE_DECREASE
        self.keyboard_bindings[self.keys.HOME] = InputCommand.SYSTEM_EXPOSURE_RESET
        self.keyboard_bindings[self.keys.END] = InputCommand.SYSTEM_TOGGLE_AUTO_EXPOSURE
        self.keyboard_bindings[self.keys.F10] = InputCommand.SYSTEM_PRINT_LIGHT_INFO

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
