"""
Tool Category

Defines categories for organizing tools in inventory and UI.
"""

from enum import Enum, auto


class ToolCategory(Enum):
    """
    Tool categories for organization and filtering.

    Used for:
    - Inventory grouping
    - UI tabs/sections
    - Context filtering (editor tools only available in LEVEL_EDITOR context)
    """

    EDITOR = auto()      # Level editor tools (model placer, delete, lights)
    WEAPON = auto()      # Combat tools (melee, ranged)
    UTILITY = auto()     # Non-combat tools (flashlight, grapple, scanner)
    BUILD = auto()       # Construction tools (future - building mode)
