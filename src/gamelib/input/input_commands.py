"""
Input Commands

Defines all possible input commands in the game using Command Pattern.
Commands are abstract actions that can be triggered by any input device.
"""

from enum import Enum, auto


class InputCommand(Enum):
    """
    All possible input commands in the game.

    Commands represent actions, not keys. This allows rebindable controls
    and multiple input sources (keyboard, gamepad, AI, replay system).
    """

    # ========================================================================
    # Camera Movement
    # ========================================================================
    CAMERA_MOVE_FORWARD = auto()
    CAMERA_MOVE_BACKWARD = auto()
    CAMERA_MOVE_LEFT = auto()
    CAMERA_MOVE_RIGHT = auto()
    CAMERA_MOVE_UP = auto()
    CAMERA_MOVE_DOWN = auto()

    # Camera Look (mouse/analog stick)
    CAMERA_LOOK = auto()

    # Camera Zoom
    CAMERA_ZOOM_IN = auto()
    CAMERA_ZOOM_OUT = auto()

    # ========================================================================
    # Game Actions (Future)
    # ========================================================================

    # Player Movement
    GAME_JUMP = auto()
    GAME_CROUCH = auto()
    GAME_SPRINT = auto()
    GAME_WALK = auto()

    # Combat
    GAME_ATTACK = auto()
    GAME_ATTACK_SECONDARY = auto()
    GAME_BLOCK = auto()
    GAME_RELOAD = auto()
    GAME_SWITCH_WEAPON = auto()

    # Interaction
    GAME_INTERACT = auto()
    GAME_USE = auto()
    GAME_PICKUP = auto()
    GAME_DROP = auto()

    # ========================================================================
    # UI Actions (Future)
    # ========================================================================

    # Navigation
    UI_NAVIGATE_UP = auto()
    UI_NAVIGATE_DOWN = auto()
    UI_NAVIGATE_LEFT = auto()
    UI_NAVIGATE_RIGHT = auto()

    # Selection
    UI_CONFIRM = auto()
    UI_CANCEL = auto()
    UI_SELECT = auto()

    # Menus
    UI_OPEN_MENU = auto()
    UI_OPEN_INVENTORY = auto()
    UI_OPEN_MAP = auto()
    UI_OPEN_SETTINGS = auto()
    UI_CLOSE = auto()

    # Tabs
    UI_TAB_NEXT = auto()
    UI_TAB_PREVIOUS = auto()

    # ========================================================================
    # Object Interaction (Future)
    # ========================================================================
    OBJECT_SELECT = auto()           # Click/point at object
    OBJECT_GRAB = auto()             # Grab/hold object
    OBJECT_THROW = auto()            # Throw held object
    OBJECT_ROTATE = auto()           # Rotate object
    OBJECT_PLACE = auto()            # Place object

    # ========================================================================
    # Building/Crafting (Future)
    # ========================================================================
    BUILD_MODE_TOGGLE = auto()
    BUILD_PLACE = auto()
    BUILD_REMOVE = auto()
    BUILD_ROTATE = auto()
    BUILD_COPY = auto()

    # ========================================================================
    # System Commands
    # ========================================================================
    SYSTEM_TOGGLE_MOUSE = auto()     # Capture/release mouse
    SYSTEM_SCREENSHOT = auto()
    SYSTEM_TOGGLE_DEBUG = auto()
    SYSTEM_TOGGLE_FULLSCREEN = auto()
    SYSTEM_TOGGLE_SSAO = auto()      # Toggle SSAO on/off
    SYSTEM_TOGGLE_MSAA = auto()      # Toggle MSAA on/off
    SYSTEM_TOGGLE_FXAA = auto()      # Toggle FXAA on/off
    SYSTEM_TOGGLE_SMAA = auto()      # Toggle SMAA on/off
    SYSTEM_CYCLE_AA_MODE = auto()    # Cycle through AA modes
    SYSTEM_QUICK_SAVE = auto()
    SYSTEM_QUICK_LOAD = auto()
    SYSTEM_PAUSE = auto()
    SYSTEM_QUIT = auto()

    # ========================================================================
    # Social (Future - multiplayer)
    # ========================================================================
    SOCIAL_CHAT = auto()
    SOCIAL_VOICE = auto()
    SOCIAL_EMOTE = auto()


class InputType(Enum):
    """
    Type of input command.

    Determines how the command should be processed.
    """

    CONTINUOUS = auto()   # Held down continuously (movement, aiming)
    INSTANT = auto()      # Single press/release (jump, fire, click)
    AXIS = auto()         # Analog input (mouse, joystick)
    TOGGLE = auto()       # On/off state (crouch, sprint)


# Map commands to their types
COMMAND_TYPES = {
    # Continuous (held)
    InputCommand.CAMERA_MOVE_FORWARD: InputType.CONTINUOUS,
    InputCommand.CAMERA_MOVE_BACKWARD: InputType.CONTINUOUS,
    InputCommand.CAMERA_MOVE_LEFT: InputType.CONTINUOUS,
    InputCommand.CAMERA_MOVE_RIGHT: InputType.CONTINUOUS,
    InputCommand.CAMERA_MOVE_UP: InputType.CONTINUOUS,
    InputCommand.CAMERA_MOVE_DOWN: InputType.CONTINUOUS,

    # Axis (mouse/analog)
    InputCommand.CAMERA_LOOK: InputType.AXIS,
    InputCommand.CAMERA_ZOOM_IN: InputType.CONTINUOUS,
    InputCommand.CAMERA_ZOOM_OUT: InputType.CONTINUOUS,

    # Instant (press once)
    InputCommand.GAME_JUMP: InputType.INSTANT,
    InputCommand.GAME_INTERACT: InputType.INSTANT,
    InputCommand.GAME_ATTACK: InputType.INSTANT,
    InputCommand.UI_CONFIRM: InputType.INSTANT,
    InputCommand.UI_CANCEL: InputType.INSTANT,
    InputCommand.SYSTEM_TOGGLE_MOUSE: InputType.INSTANT,
    InputCommand.SYSTEM_SCREENSHOT: InputType.INSTANT,
    InputCommand.SYSTEM_TOGGLE_DEBUG: InputType.INSTANT,
    InputCommand.SYSTEM_TOGGLE_SSAO: InputType.INSTANT,
    InputCommand.SYSTEM_TOGGLE_MSAA: InputType.INSTANT,
    InputCommand.SYSTEM_TOGGLE_FXAA: InputType.INSTANT,
    InputCommand.SYSTEM_TOGGLE_SMAA: InputType.INSTANT,
    InputCommand.SYSTEM_CYCLE_AA_MODE: InputType.INSTANT,

    # Toggle (on/off state)
    InputCommand.GAME_CROUCH: InputType.TOGGLE,
    InputCommand.GAME_SPRINT: InputType.TOGGLE,
    InputCommand.BUILD_MODE_TOGGLE: InputType.TOGGLE,
}


def get_command_type(command: InputCommand) -> InputType:
    """
    Get the input type for a command.

    Args:
        command: The input command

    Returns:
        InputType for this command, defaults to INSTANT if not defined
    """
    return COMMAND_TYPES.get(command, InputType.INSTANT)
