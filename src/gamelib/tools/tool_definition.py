"""
Tool Definition

Data descriptor for tools loaded from JSON configuration files.
Follows the same pattern as SceneDefinition for data-driven design.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from .tool_category import ToolCategory


@dataclass
class ToolDefinition:
    """
    Data descriptor for a tool loaded from JSON.

    Separates tool data (stats, config) from tool behavior (code).
    This allows tools to be configured via JSON while keeping logic in Python.
    """

    id: str                              # Unique identifier (e.g., "model_placer")
    name: str                            # Display name (e.g., "Model Placer")
    category: ToolCategory               # Tool category for organization
    tool_type: str                       # Python class name to instantiate
    icon: Optional[str] = None           # Path to icon image
    cursor: str = "default"              # Cursor type to display
    cooldown: float = 0.0                # Cooldown time in seconds
    use_duration: float = 0.0            # How long the "use" action takes
    properties: Dict[str, Any] = field(default_factory=dict)  # Tool-specific properties

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolDefinition":
        """
        Create a tool definition from JSON data.

        Args:
            data: Dictionary loaded from JSON

        Returns:
            ToolDefinition instance

        Example JSON:
            {
                "id": "model_placer",
                "name": "Model Placer",
                "category": "EDITOR",
                "type": "ModelPlacementTool",
                "icon": "icons/model_placer.png",
                "cursor": "crosshair_place",
                "cooldown": 0.0,
                "properties": {
                    "snap_to_grid": true,
                    "grid_size": 1.0,
                    "model_library_path": "assets/models/props/"
                }
            }
        """
        if "id" not in data:
            raise ValueError("Tool definition is missing required 'id' field")
        if "type" not in data:
            raise ValueError(f"Tool definition '{data['id']}' is missing required 'type' field")

        # Parse category enum
        category_str = data.get("category", "UTILITY")
        try:
            category = ToolCategory[category_str]
        except KeyError:
            raise ValueError(f"Invalid tool category: {category_str}")

        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            category=category,
            tool_type=data["type"],
            icon=data.get("icon"),
            cursor=data.get("cursor", "default"),
            cooldown=float(data.get("cooldown", 0.0)),
            use_duration=float(data.get("use_duration", 0.0)),
            properties=data.get("properties", {})
        )


@dataclass
class ToolsetDefinition:
    """
    Container for multiple tool definitions loaded from a JSON file.
    """

    name: str
    tools: List[ToolDefinition] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolsetDefinition":
        """
        Load a toolset from JSON data.

        Args:
            data: Dictionary with 'tools' array

        Returns:
            ToolsetDefinition instance

        Example JSON:
            {
                "name": "Editor Tools",
                "tools": [
                    { "id": "model_placer", ... },
                    { "id": "delete_tool", ... }
                ]
            }
        """
        tools = [ToolDefinition.from_dict(tool_data) for tool_data in data.get("tools", [])]
        return cls(
            name=data.get("name", "Toolset"),
            tools=tools
        )
