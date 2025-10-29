"""
Tool Manager

Central manager for tool registration, switching, and lifecycle.
"""

from typing import Dict, Optional, TYPE_CHECKING
from pathlib import Path
import json
from .tool_base import Tool
from .tool_definition import ToolsetDefinition
from .inventory import Inventory
from .tool_category import ToolCategory

if TYPE_CHECKING:
    from ..core.camera import Camera
    from ..core.scene import Scene


class ToolManager:
    """
    Central manager for all tools in the game.

    Responsibilities:
    - Load tool definitions from JSON
    - Instantiate tool classes
    - Manage active tool
    - Handle tool switching
    - Update active tool each frame
    """

    def __init__(self, ctx=None):
        """
        Initialize tool manager.

        Args:
            ctx: ModernGL context (needed for some editor tools)
        """
        self.ctx = ctx
        self.tools: Dict[str, Tool] = {}  # tool_id -> Tool instance
        self.inventory = Inventory()
        self.active_tool: Optional[Tool] = None
        self.active_slot: int = 0  # Current hotbar slot (0-8)

    def register_tool(self, tool: Tool):
        """
        Register a tool instance.

        Args:
            tool: Tool to register
        """
        self.tools[tool.id] = tool
        self.inventory.add_tool(tool.id, tool.category)

    def load_tools_from_json(self, path: Path | str):
        """
        Load tools from a JSON file.

        Args:
            path: Path to JSON file containing tool definitions

        Example JSON:
            {
                "name": "Editor Tools",
                "tools": [
                    {
                        "id": "model_placer",
                        "name": "Model Placer",
                        "category": "EDITOR",
                        "type": "ModelPlacementTool",
                        ...
                    }
                ]
            }
        """
        path = Path(path)
        if not path.exists():
            print(f"Warning: Tool definition file not found: {path}")
            return

        try:
            with open(path, 'r') as f:
                data = json.load(f)

            toolset = ToolsetDefinition.from_dict(data)
            print(f"Loading toolset: {toolset.name} ({len(toolset.tools)} tools)")

            for tool_def in toolset.tools:
                # Instantiate tool class dynamically
                tool_instance = self._instantiate_tool(tool_def)
                if tool_instance:
                    self.register_tool(tool_instance)
                    print(f"  Registered tool: {tool_def.name} (id={tool_def.id})")

            # Auto-assign tools to hotbar
            self.inventory.auto_assign_to_hotbar()

            print(f"Tool manager initialized with {len(self.tools)} tools")

        except Exception as e:
            print(f"Error loading tools from {path}: {e}")
            import traceback
            traceback.print_exc()

    def _instantiate_tool(self, definition) -> Optional[Tool]:
        """
        Instantiate a tool from its definition.

        Args:
            definition: ToolDefinition

        Returns:
            Tool instance or None if class not found
        """
        # Import tool classes dynamically based on tool_type
        tool_type = definition.tool_type

        try:
            # Try editor tools first
            if definition.category == ToolCategory.EDITOR:
                from .editor import (
                    ModelPlacementTool,
                    ObjectEditorTool,
                    LightEditorTool,
                    DeleteTool,
                )
                tool_classes = {
                    "ModelPlacementTool": ModelPlacementTool,
                    "ObjectEditorTool": ObjectEditorTool,
                    "LightEditorTool": LightEditorTool,
                    "DeleteTool": DeleteTool,
                }
            else:
                # Future: gameplay tools
                tool_classes = {}

            if tool_type in tool_classes:
                return tool_classes[tool_type](definition, self.ctx)
            else:
                print(f"Warning: Unknown tool type '{tool_type}' for tool '{definition.id}'")
                return None

        except ImportError as e:
            print(f"Warning: Could not import tool type '{tool_type}': {e}")
            return None

    def equip_tool(self, tool_id: str) -> bool:
        """
        Equip a tool by its ID.

        Args:
            tool_id: Tool to equip

        Returns:
            True if successful
        """
        if tool_id not in self.tools:
            print(f"Warning: Tool '{tool_id}' not found")
            return False

        # Unequip current tool
        if self.active_tool:
            self.active_tool.on_unequipped()

        # Equip new tool
        self.active_tool = self.tools[tool_id]
        self.active_tool.on_equipped()

        print(f"Equipped tool: {self.active_tool.name}")
        return True

    def equip_hotbar_slot(self, slot: int) -> bool:
        """
        Equip tool from hotbar slot.

        Args:
            slot: Hotbar slot (0-8, corresponding to keys 1-9)

        Returns:
            True if tool was equipped
        """
        tool_id = self.inventory.get_hotbar_tool(slot)
        if tool_id:
            self.active_slot = slot
            return self.equip_tool(tool_id)
        return False

    def next_tool(self):
        """Cycle to next tool in hotbar (scroll wheel up)."""
        next_slot = self.inventory.find_next_hotbar_slot(self.active_slot, direction=1)
        print(next_slot)
        if next_slot is not None:
            self.equip_hotbar_slot(next_slot)
            print(f"Equipped next tool: {self.active_tool.name}")
        else:
            print("No next tool found in hotbar.")

    def previous_tool(self):
        """Cycle to previous tool in hotbar (scroll wheel down)."""
        prev_slot = self.inventory.find_next_hotbar_slot(self.active_slot, direction=-1)
        print(prev_slot)
        if prev_slot is not None:
            self.equip_hotbar_slot(prev_slot)
            print(f"Equipped previous tool: {self.active_tool.name}")
        else:
            print("No previous tool found in hotbar.")

    def use_active_tool(self, camera: "Camera", scene: "Scene", **kwargs) -> bool:
        """
        Use the active tool's primary action.

        Args:
            camera: Active camera
            scene: Current scene
            **kwargs: Additional context

        Returns:
            True if action was successful
        """
        if self.active_tool:
            return self.active_tool.use(camera, scene, **kwargs)
        return False

    def use_active_tool_secondary(self, camera: "Camera", scene: "Scene", **kwargs) -> bool:
        """
        Use the active tool's secondary action.

        Args:
            camera: Active camera
            scene: Current scene
            **kwargs: Additional context

        Returns:
            True if action was successful
        """
        if self.active_tool:
            return self.active_tool.use_secondary(camera, scene, **kwargs)
        return False

    def update(self, delta_time: float, camera: "Camera", scene: "Scene"):
        """
        Update active tool.

        Args:
            delta_time: Time since last update
            camera: Active camera
            scene: Current scene
        """
        if self.active_tool:
            self.active_tool.update(delta_time, camera, scene)

    def get_active_tool(self) -> Optional[Tool]:
        """
        Get the currently active tool.

        Returns:
            Active tool or None
        """
        return self.active_tool

    def get_active_slot(self) -> int:
        """
        Get the currently active hotbar slot.

        Returns:
            Slot index (0-8)
        """
        return self.active_slot

    def __repr__(self):
        active = self.active_tool.name if self.active_tool else "None"
        return f"<ToolManager tools={len(self.tools)} active='{active}' slot={self.active_slot+1}>"
