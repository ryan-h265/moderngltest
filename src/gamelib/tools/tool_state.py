"""
Tool State

Defines the various states a tool can be in during its lifecycle.
"""

from enum import Enum, auto


class ToolState(Enum):
    """
    State machine for tool usage.

    Tools transition through these states based on user input and timing:
    IDLE → USING → COOLDOWN → IDLE
    """

    IDLE = auto()        # Ready to use
    USING = auto()       # Currently being used (animation playing, action in progress)
    COOLDOWN = auto()    # Waiting for cooldown to complete
    RELOADING = auto()   # Reloading (for ranged weapons)
    DISABLED = auto()    # Cannot be used (out of ammo, broken, etc.)
