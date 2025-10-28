"""
Inventory System

Manages tool storage and hotbar slots.
"""

from typing import List, Optional, Dict
from collections import defaultdict
from .tool_category import ToolCategory


class Inventory:
    """
    Manages tool inventory with hotbar and storage.

    Features:
    - 9-slot hotbar (1-9 keys)
    - Unlimited storage
    - Category-based organization
    - Tool assignment to hotbar slots
    """

    HOTBAR_SIZE = 9

    def __init__(self):
        """Initialize empty inventory."""
        self.hotbar: List[Optional[str]] = [None] * self.HOTBAR_SIZE  # tool IDs in hotbar slots (0-8)
        self.storage: List[str] = []  # All owned tool IDs
        self.categories: Dict[ToolCategory, List[str]] = defaultdict(list)  # Category -> tool IDs

    def add_tool(self, tool_id: str, category: ToolCategory):
        """
        Add a tool to inventory.

        Args:
            tool_id: Unique tool identifier
            category: Tool category for organization
        """
        if tool_id not in self.storage:
            self.storage.append(tool_id)
            self.categories[category].append(tool_id)

    def remove_tool(self, tool_id: str):
        """
        Remove a tool from inventory.

        Args:
            tool_id: Tool to remove
        """
        if tool_id in self.storage:
            self.storage.remove(tool_id)

            # Remove from hotbar if present
            for i in range(self.HOTBAR_SIZE):
                if self.hotbar[i] == tool_id:
                    self.hotbar[i] = None

            # Remove from categories
            for category_tools in self.categories.values():
                if tool_id in category_tools:
                    category_tools.remove(tool_id)

    def assign_to_hotbar(self, tool_id: str, slot: int) -> bool:
        """
        Assign a tool to a hotbar slot.

        Args:
            tool_id: Tool to assign
            slot: Hotbar slot (0-8, corresponding to keys 1-9)

        Returns:
            True if successful, False if invalid slot or tool not owned
        """
        if not (0 <= slot < self.HOTBAR_SIZE):
            return False

        if tool_id not in self.storage:
            return False

        self.hotbar[slot] = tool_id
        return True

    def clear_hotbar_slot(self, slot: int):
        """
        Clear a hotbar slot.

        Args:
            slot: Slot to clear (0-8)
        """
        if 0 <= slot < self.HOTBAR_SIZE:
            self.hotbar[slot] = None

    def get_hotbar_tool(self, slot: int) -> Optional[str]:
        """
        Get tool ID in a hotbar slot.

        Args:
            slot: Hotbar slot (0-8)

        Returns:
            Tool ID or None if slot is empty or invalid
        """
        if 0 <= slot < self.HOTBAR_SIZE:
            return self.hotbar[slot]
        return None

    def get_tools_by_category(self, category: ToolCategory) -> List[str]:
        """
        Get all tools in a category.

        Args:
            category: Category to filter by

        Returns:
            List of tool IDs
        """
        return self.categories[category].copy()

    def has_tool(self, tool_id: str) -> bool:
        """
        Check if inventory contains a tool.

        Args:
            tool_id: Tool to check

        Returns:
            True if tool is in inventory
        """
        return tool_id in self.storage

    def get_all_tools(self) -> List[str]:
        """
        Get all tool IDs in inventory.

        Returns:
            List of all tool IDs
        """
        return self.storage.copy()

    def find_next_hotbar_slot(self, current_slot: int, direction: int = 1) -> Optional[int]:
        """
        Find the next non-empty hotbar slot.

        Args:
            current_slot: Current slot (0-8)
            direction: 1 for next, -1 for previous

        Returns:
            Next slot index with a tool, or None if no tools in hotbar
        """
        if not any(self.hotbar):  # No tools in hotbar
            return None

        # Search for next non-empty slot
        for i in range(1, self.HOTBAR_SIZE):
            slot = (current_slot + direction * i) % self.HOTBAR_SIZE
            if self.hotbar[slot] is not None:
                return slot

        # If we got here, only current slot has a tool
        return current_slot

    def auto_assign_to_hotbar(self):
        """
        Auto-assign tools to hotbar slots.

        Fills empty hotbar slots with tools from storage.
        Useful for initial setup or after loading tools.
        """
        tool_index = 0
        for slot in range(self.HOTBAR_SIZE):
            if self.hotbar[slot] is None and tool_index < len(self.storage):
                self.hotbar[slot] = self.storage[tool_index]
                tool_index += 1

    def __repr__(self):
        hotbar_str = ", ".join([f"{i+1}:{self.hotbar[i] or 'empty'}" for i in range(self.HOTBAR_SIZE)])
        return f"<Inventory hotbar=[{hotbar_str}] total_tools={len(self.storage)}>"
