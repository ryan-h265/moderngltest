"""
Tool Controller

Handles input commands for the tool system.
Connects InputManager to ToolManager for tool usage and switching.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...tools.tool_manager import ToolManager
    from ...core.camera import Camera
    from ...core.scene import Scene
    from ..input_manager import InputManager

from ..input_commands import InputCommand


class ToolController:
    """
    Handles tool-related input commands.

    Responsibilities:
    - Tool usage (primary and secondary actions)
    - Tool switching (hotbar slots, next/previous)
    - Editor commands (undo, redo, save, etc.)
    """

    def __init__(
        self,
        tool_manager: "ToolManager",
        input_manager: "InputManager",
        camera: "Camera",
        scene: "Scene"
    ):
        """
        Initialize tool controller.

        Args:
            tool_manager: ToolManager instance
            input_manager: InputManager instance
            camera: Active camera
            scene: Current scene
        """
        self.tool_manager = tool_manager
        self.input_manager = input_manager
        self.camera = camera
        self.scene = scene

        # Editor history (for undo/redo) - will be set by game/editor
        self.editor_history = None

        # Track continuous tool use (held down)
        self.tool_use_held = False
        self.tool_secondary_held = False

        self._register_handlers()

    def _register_handlers(self):
        """Register input command handlers."""
        # Tool usage
        self.input_manager.register_handler(InputCommand.TOOL_USE, self.use_tool)
        self.input_manager.register_handler(InputCommand.TOOL_USE_SECONDARY, self.use_tool_secondary)
        self.input_manager.register_handler(InputCommand.TOOL_RELOAD, self.reload_tool)
        self.input_manager.register_handler(InputCommand.TOOL_CANCEL, self.cancel_tool)

        # Tool switching
        self.input_manager.register_handler(InputCommand.TOOL_NEXT, self.next_tool)
        self.input_manager.register_handler(InputCommand.TOOL_PREVIOUS, self.previous_tool)

        # Hotbar slots
        self.input_manager.register_handler(InputCommand.TOOL_HOTBAR_1, lambda: self.select_hotbar(1))
        self.input_manager.register_handler(InputCommand.TOOL_HOTBAR_2, lambda: self.select_hotbar(2))
        self.input_manager.register_handler(InputCommand.TOOL_HOTBAR_3, lambda: self.select_hotbar(3))
        self.input_manager.register_handler(InputCommand.TOOL_HOTBAR_4, lambda: self.select_hotbar(4))
        self.input_manager.register_handler(InputCommand.TOOL_HOTBAR_5, lambda: self.select_hotbar(5))
        self.input_manager.register_handler(InputCommand.TOOL_HOTBAR_6, lambda: self.select_hotbar(6))
        self.input_manager.register_handler(InputCommand.TOOL_HOTBAR_7, lambda: self.select_hotbar(7))
        self.input_manager.register_handler(InputCommand.TOOL_HOTBAR_8, lambda: self.select_hotbar(8))
        self.input_manager.register_handler(InputCommand.TOOL_HOTBAR_9, lambda: self.select_hotbar(9))

        # Editor commands
        self.input_manager.register_handler(InputCommand.EDITOR_UNDO, self.undo)
        self.input_manager.register_handler(InputCommand.EDITOR_REDO, self.redo)
        self.input_manager.register_handler(InputCommand.EDITOR_SAVE_SCENE, self.save_scene)
        self.input_manager.register_handler(InputCommand.EDITOR_LOAD_SCENE, self.load_scene)
        self.input_manager.register_handler(InputCommand.EDITOR_TOGGLE_GRID, self.toggle_grid)
        self.input_manager.register_handler(InputCommand.EDITOR_ROTATE_CW, self.rotate_cw)
        self.input_manager.register_handler(InputCommand.EDITOR_ROTATE_CCW, self.rotate_ccw)
        self.input_manager.register_handler(InputCommand.EDITOR_DELETE, self.delete_selected)
        self.input_manager.register_handler(InputCommand.EDITOR_DUPLICATE, self.duplicate_selected)
        self.input_manager.register_handler(InputCommand.EDITOR_OPEN_BROWSER, self.open_browser)

    # ========================================================================
    # Tool Usage
    # ========================================================================

    def use_tool(self, delta_time: float = 0.0):
        """
        Use active tool's primary action.

        Args:
            delta_time: Time since last call (for continuous use)
        """
        if self.tool_manager.active_tool:
            self.tool_use_held = True
            self.tool_manager.use_active_tool(self.camera, self.scene)

    def use_tool_secondary(self, delta_time: float = 0.0):
        """
        Use active tool's secondary action.

        Args:
            delta_time: Time since last call (for continuous use)
        """
        if self.tool_manager.active_tool:
            self.tool_secondary_held = True
            self.tool_manager.use_active_tool_secondary(self.camera, self.scene)

    def reload_tool(self):
        """Reload active tool (for weapons)."""
        if self.tool_manager.active_tool and hasattr(self.tool_manager.active_tool, 'reload'):
            self.tool_manager.active_tool.reload()

    def cancel_tool(self):
        """Cancel active tool action."""
        self.tool_use_held = False
        self.tool_secondary_held = False
        if self.tool_manager.active_tool and hasattr(self.tool_manager.active_tool, 'cancel'):
            self.tool_manager.active_tool.cancel()

    # ========================================================================
    # Tool Switching
    # ========================================================================

    def next_tool(self):
        """Switch to next tool in hotbar."""
        self.tool_manager.next_tool()

    def previous_tool(self):
        """Switch to previous tool in hotbar."""
        self.tool_manager.previous_tool()

    def select_hotbar(self, slot_number: int):
        """
        Select hotbar slot by number (1-9).

        Args:
            slot_number: Slot number (1-9, not 0-8)
        """
        slot_index = slot_number - 1  # Convert 1-9 to 0-8
        self.tool_manager.equip_hotbar_slot(slot_index)

    # ========================================================================
    # Editor Commands
    # ========================================================================

    def undo(self):
        """Undo last editor action."""
        if self.editor_history:
            self.editor_history.undo(self.scene)
            print("Undo")

    def redo(self):
        """Redo last undone action."""
        if self.editor_history:
            self.editor_history.redo(self.scene)
            print("Redo")

    def save_scene(self):
        """Save current scene to JSON."""
        from pathlib import Path
        from datetime import datetime

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = Path("scenes")
        save_dir.mkdir(exist_ok=True)
        filepath = save_dir / f"scene_{timestamp}.json"

        # Get lights from somewhere (need to be passed in or accessible)
        # For now, assume we have access via a lights attribute
        lights = getattr(self, 'lights', None)

        try:
            self.scene.save_to_json(str(filepath), lights=lights)
            print(f"Scene saved to: {filepath}")
        except Exception as e:
            print(f"Error saving scene: {e}")
            import traceback
            traceback.print_exc()

    def load_scene(self):
        """Load scene from JSON."""
        print("Load scene - Not yet implemented (need file picker)")
        # TODO: Implement file picker UI to select scene file
        # For now, user can call scene.load_from_json() directly

    def toggle_grid(self):
        """Toggle grid snapping on/off."""
        active_tool = self.tool_manager.get_active_tool()
        if active_tool and hasattr(active_tool, 'grid_snap_enabled'):
            active_tool.grid_snap_enabled = not active_tool.grid_snap_enabled
            status = "enabled" if active_tool.grid_snap_enabled else "disabled"
            print(f"Grid snap {status}")

    def rotate_cw(self):
        """Rotate selected object clockwise (discrete 45° rotation)."""
        active_tool = self.tool_manager.get_active_tool()
        if active_tool and hasattr(active_tool, 'rotate_selected'):
            active_tool.rotate_selected(45.0)

    def rotate_ccw(self):
        """Rotate selected object counter-clockwise (discrete 45° rotation)."""
        active_tool = self.tool_manager.get_active_tool()
        if active_tool and hasattr(active_tool, 'rotate_selected'):
            active_tool.rotate_selected(-45.0)

    def delete_selected(self):
        """Delete selected object."""
        active_tool = self.tool_manager.get_active_tool()
        if active_tool and hasattr(active_tool, 'delete_selected'):
            active_tool.delete_selected()

    def duplicate_selected(self):
        """Duplicate selected object."""
        active_tool = self.tool_manager.get_active_tool()
        if active_tool and hasattr(active_tool, 'duplicate_selected'):
            active_tool.duplicate_selected()

    def open_browser(self):
        """Open model/asset browser."""
        print("Open browser - TODO: Implement asset browser UI")
        # TODO: Implement asset browser

    # ========================================================================
    # Update
    # ========================================================================

    def update(self, delta_time: float):
        """
        Update tool controller.

        Called every frame to handle continuous tool usage.

        Args:
            delta_time: Time since last update
        """
        # Continuous tool use is handled via the CONTINUOUS input type
        # in InputManager.update(), which calls our use_tool/use_tool_secondary
        # with delta_time
        pass
