"""
Tool System

Provides a flexible, data-driven tool system for both gameplay and level editing.

Core Components:
- Tool: Abstract base class for all tools
- EditorTool: Base class for level editor tools
- ToolManager: Central manager for tool registration and switching
- Inventory: Hotbar and storage management
- ToolController: Input handling for tools

Usage:
    # Load tools from JSON
    tool_manager = ToolManager(ctx)
    tool_manager.load_tools_from_json("assets/config/tools/editor_tools.json")

    # Equip a tool
    tool_manager.equip_tool("model_placer")

    # Use the tool
    tool_manager.use_active_tool(camera, scene)
"""

from .tool_state import ToolState
from .tool_category import ToolCategory
from .tool_definition import ToolDefinition, ToolsetDefinition
from .tool_base import Tool, EditorTool
from .inventory import Inventory
from .tool_manager import ToolManager

__all__ = [
    "ToolState",
    "ToolCategory",
    "ToolDefinition",
    "ToolsetDefinition",
    "Tool",
    "EditorTool",
    "Inventory",
    "ToolManager",
]
