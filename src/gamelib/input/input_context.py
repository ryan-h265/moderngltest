"""
Input Context Management

Manages different input contexts (gameplay, menu, dialogue, etc.)
and determines which commands are available in each context.
"""

from enum import Enum, auto
from typing import Set
from .input_commands import InputCommand


class InputContext(Enum):
    """
    Different input contexts for the game.

    Each context has a different set of available commands.
    Contexts can be stacked (e.g., open menu while in gameplay).
    """

    GAMEPLAY = auto()      # Normal gameplay mode
    MENU = auto()          # Main menu or pause menu
    DIALOGUE = auto()      # Talking to NPC, reading text
    INVENTORY = auto()     # Inventory/equipment screen
    MAP = auto()           # Map view
    BUILDING = auto()      # Building/construction mode
    CRAFTING = auto()      # Crafting interface
    SETTINGS = auto()      # Settings menu
    CINEMATIC = auto()     # Cutscene (very limited input)
    DEAD = auto()          # Player is dead (respawn screen)


class InputContextManager:
    """
    Manages which input commands are available in each context.

    Features:
    - Context stacking (push/pop for menus)
    - Command filtering per context
    - Context-specific command priority
    """

    def __init__(self):
        """Initialize with GAMEPLAY as default context"""
        self.current_context = InputContext.GAMEPLAY
        self.context_stack = [InputContext.GAMEPLAY]

        # Define which commands are available in each context
        self._define_context_commands()

    def _define_context_commands(self):
        """Define command availability for each context"""

        self.context_commands = {
            # ================================================================
            # GAMEPLAY - All gameplay commands
            # ================================================================
            InputContext.GAMEPLAY: {
                # Camera
                InputCommand.CAMERA_MOVE_FORWARD,
                InputCommand.CAMERA_MOVE_BACKWARD,
                InputCommand.CAMERA_MOVE_LEFT,
                InputCommand.CAMERA_MOVE_RIGHT,
                InputCommand.CAMERA_MOVE_UP,
                InputCommand.CAMERA_MOVE_DOWN,
                InputCommand.CAMERA_LOOK,
                InputCommand.CAMERA_ZOOM_IN,
                InputCommand.CAMERA_ZOOM_OUT,

                # Player actions
                InputCommand.GAME_JUMP,
                InputCommand.GAME_CROUCH,
                InputCommand.GAME_SPRINT,
                InputCommand.GAME_INTERACT,
                InputCommand.GAME_USE,
                InputCommand.GAME_PICKUP,
                InputCommand.GAME_DROP,

                # Combat
                InputCommand.GAME_ATTACK,
                InputCommand.GAME_ATTACK_SECONDARY,
                InputCommand.GAME_BLOCK,
                InputCommand.GAME_RELOAD,
                InputCommand.GAME_SWITCH_WEAPON,

                # Objects
                InputCommand.OBJECT_SELECT,
                InputCommand.OBJECT_GRAB,
                InputCommand.OBJECT_THROW,

                # UI (can open menus from gameplay)
                InputCommand.UI_OPEN_MENU,
                InputCommand.UI_OPEN_INVENTORY,
                InputCommand.UI_OPEN_MAP,
                InputCommand.UI_OPEN_SETTINGS,

                # System
                InputCommand.SYSTEM_TOGGLE_MOUSE,
                InputCommand.SYSTEM_SCREENSHOT,
                InputCommand.SYSTEM_TOGGLE_DEBUG,
                InputCommand.SYSTEM_PAUSE,
                InputCommand.SYSTEM_QUICK_SAVE,
                InputCommand.SYSTEM_QUICK_LOAD,
            },

            # ================================================================
            # MENU - UI navigation only
            # ================================================================
            InputContext.MENU: {
                # UI navigation
                InputCommand.UI_NAVIGATE_UP,
                InputCommand.UI_NAVIGATE_DOWN,
                InputCommand.UI_NAVIGATE_LEFT,
                InputCommand.UI_NAVIGATE_RIGHT,
                InputCommand.UI_CONFIRM,
                InputCommand.UI_CANCEL,
                InputCommand.UI_SELECT,
                InputCommand.UI_TAB_NEXT,
                InputCommand.UI_TAB_PREVIOUS,
                InputCommand.UI_CLOSE,

                # System
                InputCommand.SYSTEM_SCREENSHOT,
                InputCommand.SYSTEM_TOGGLE_DEBUG,
            },

            # ================================================================
            # DIALOGUE - Limited interaction
            # ================================================================
            InputContext.DIALOGUE: {
                # UI
                InputCommand.UI_NAVIGATE_UP,
                InputCommand.UI_NAVIGATE_DOWN,
                InputCommand.UI_CONFIRM,
                InputCommand.UI_CANCEL,
                InputCommand.UI_CLOSE,

                # Can skip dialogue
                InputCommand.GAME_INTERACT,

                # Camera look only (not movement)
                InputCommand.CAMERA_LOOK,
            },

            # ================================================================
            # INVENTORY - Menu + some camera
            # ================================================================
            InputContext.INVENTORY: {
                # UI
                InputCommand.UI_NAVIGATE_UP,
                InputCommand.UI_NAVIGATE_DOWN,
                InputCommand.UI_NAVIGATE_LEFT,
                InputCommand.UI_NAVIGATE_RIGHT,
                InputCommand.UI_CONFIRM,
                InputCommand.UI_CANCEL,
                InputCommand.UI_SELECT,
                InputCommand.UI_TAB_NEXT,
                InputCommand.UI_TAB_PREVIOUS,
                InputCommand.UI_CLOSE,

                # Camera (can rotate to view character)
                InputCommand.CAMERA_LOOK,
                InputCommand.CAMERA_ZOOM_IN,
                InputCommand.CAMERA_ZOOM_OUT,

                # Object interaction (for 3D inventory)
                InputCommand.OBJECT_SELECT,
                InputCommand.OBJECT_ROTATE,
            },

            # ================================================================
            # MAP - Navigation with camera control
            # ================================================================
            InputContext.MAP: {
                # Map navigation
                InputCommand.CAMERA_MOVE_FORWARD,
                InputCommand.CAMERA_MOVE_BACKWARD,
                InputCommand.CAMERA_MOVE_LEFT,
                InputCommand.CAMERA_MOVE_RIGHT,
                InputCommand.CAMERA_ZOOM_IN,
                InputCommand.CAMERA_ZOOM_OUT,

                # UI
                InputCommand.UI_SELECT,
                InputCommand.UI_CLOSE,

                # Object (waypoints)
                InputCommand.OBJECT_SELECT,
                InputCommand.OBJECT_PLACE,
            },

            # ================================================================
            # BUILDING - Construction mode
            # ================================================================
            InputContext.BUILDING: {
                # Camera (free look while building)
                InputCommand.CAMERA_MOVE_FORWARD,
                InputCommand.CAMERA_MOVE_BACKWARD,
                InputCommand.CAMERA_MOVE_LEFT,
                InputCommand.CAMERA_MOVE_RIGHT,
                InputCommand.CAMERA_MOVE_UP,
                InputCommand.CAMERA_MOVE_DOWN,
                InputCommand.CAMERA_LOOK,

                # Building
                InputCommand.BUILD_MODE_TOGGLE,
                InputCommand.BUILD_PLACE,
                InputCommand.BUILD_REMOVE,
                InputCommand.BUILD_ROTATE,
                InputCommand.BUILD_COPY,

                # Object
                InputCommand.OBJECT_SELECT,
                InputCommand.OBJECT_ROTATE,
                InputCommand.OBJECT_PLACE,

                # UI
                InputCommand.UI_CANCEL,
                InputCommand.UI_CLOSE,
            },

            # ================================================================
            # CINEMATIC - Very limited (skip only)
            # ================================================================
            InputContext.CINEMATIC: {
                InputCommand.UI_CONFIRM,   # Skip cutscene
                InputCommand.UI_CANCEL,    # Skip cutscene
                InputCommand.SYSTEM_PAUSE,
            },

            # ================================================================
            # DEAD - Respawn screen
            # ================================================================
            InputContext.DEAD: {
                InputCommand.UI_CONFIRM,    # Respawn
                InputCommand.UI_CANCEL,     # Quit to menu
                InputCommand.UI_OPEN_MENU,
            },

            # ================================================================
            # SETTINGS - Menu navigation
            # ================================================================
            InputContext.SETTINGS: {
                InputCommand.UI_NAVIGATE_UP,
                InputCommand.UI_NAVIGATE_DOWN,
                InputCommand.UI_NAVIGATE_LEFT,
                InputCommand.UI_NAVIGATE_RIGHT,
                InputCommand.UI_CONFIRM,
                InputCommand.UI_CANCEL,
                InputCommand.UI_SELECT,
                InputCommand.UI_TAB_NEXT,
                InputCommand.UI_TAB_PREVIOUS,
                InputCommand.UI_CLOSE,
            },
        }

    def push_context(self, context: InputContext):
        """
        Push a new input context onto the stack.

        Use this when opening menus, dialogues, etc.

        Args:
            context: The context to push
        """
        self.context_stack.append(context)
        self.current_context = context

    def pop_context(self) -> InputContext:
        """
        Pop the current context and return to previous.

        Use this when closing menus, dialogues, etc.

        Returns:
            The popped context

        Raises:
            ValueError: If trying to pop the last context
        """
        if len(self.context_stack) <= 1:
            raise ValueError("Cannot pop the last context (GAMEPLAY)")

        popped = self.context_stack.pop()
        self.current_context = self.context_stack[-1]
        return popped

    def set_context(self, context: InputContext):
        """
        Set context directly (clears stack).

        Use this for major state changes (e.g., main menu → gameplay).

        Args:
            context: The context to set
        """
        self.context_stack = [context]
        self.current_context = context

    def is_command_allowed(self, command: InputCommand) -> bool:
        """
        Check if a command is allowed in the current context.

        Args:
            command: The command to check

        Returns:
            True if command is allowed in current context
        """
        allowed_commands = self.context_commands.get(self.current_context, set())
        return command in allowed_commands

    def get_allowed_commands(self) -> Set[InputCommand]:
        """
        Get all commands allowed in current context.

        Returns:
            Set of allowed commands
        """
        return self.context_commands.get(self.current_context, set())

    def get_current_context(self) -> InputContext:
        """Get the current input context"""
        return self.current_context

    def get_context_stack(self) -> list:
        """Get the full context stack (for debugging)"""
        return self.context_stack.copy()

    def clear_stack(self):
        """Clear stack and return to GAMEPLAY"""
        self.context_stack = [InputContext.GAMEPLAY]
        self.current_context = InputContext.GAMEPLAY
