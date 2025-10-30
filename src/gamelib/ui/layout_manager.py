"""
Layout Manager - Unified panel positioning and sizing system

Provides configuration-driven layout management for editor UI panels.
Supports constraint-based positioning with anchors, margins, and responsive sizing.
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
import time

from ..config.settings import PROJECT_ROOT


@dataclass
class PanelSize:
    """Panel size definition."""
    width: int | str  # Pixels or "full"/"fill"
    height: int | str  # Pixels or "full"/"fill"


@dataclass
class PanelPosition:
    """Panel position definition."""
    x: int
    y: int
    reference: str = "screen"  # "screen" or "parent"


@dataclass
class PanelMargins:
    """Panel margins (spacing from edges)."""
    top: int = 0
    right: int = 0
    bottom: int = 0
    left: int = 0


@dataclass
class PanelLayout:
    """Complete layout definition for a panel."""
    name: str
    panel_type: str
    enabled: bool
    anchor: str  # "top_left", "top_right", "bottom_left", "bottom_right", etc.
    position: PanelPosition
    size: PanelSize
    margins: PanelMargins
    layout_config: Dict[str, Any] = field(default_factory=dict)


class LayoutCalculator:
    """Calculate actual panel positions and sizes based on constraints."""

    @staticmethod
    def calculate_panel_rect(
        panel: PanelLayout,
        screen_width: int,
        screen_height: int,
        other_panels: Dict[str, PanelLayout] | None = None,
    ) -> Tuple[int, int, int, int]:
        """
        Calculate the actual rectangle (x, y, width, height) for a panel.

        Args:
            panel: Panel layout definition
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            other_panels: Dict of other panels for margin calculations

        Returns:
            Tuple of (x, y, width, height)
        """
        if other_panels is None:
            other_panels = {}

        # Calculate size first (depends on screen dimensions)
        panel_width = LayoutCalculator._resolve_width(
            panel.size.width, screen_width, panel.margins, other_panels
        )
        panel_height = LayoutCalculator._resolve_height(
            panel.size.height, screen_height, panel.margins, other_panels
        )

        # Calculate position based on anchor
        panel_x, panel_y = LayoutCalculator._resolve_position(
            panel, screen_width, screen_height, panel_width, panel_height
        )

        return panel_x, panel_y, panel_width, panel_height

    @staticmethod
    def _resolve_width(
        width: int | str,
        screen_width: int,
        margins: PanelMargins,
        other_panels: Dict[str, PanelLayout],
    ) -> int:
        """Resolve width: handle 'full'/'fill' and pixel values."""
        if isinstance(width, int):
            return width
        elif width == "full":
            return screen_width - margins.left - margins.right
        elif width == "fill":
            # Fill available space after accounting for margined panels
            return screen_width - margins.left - margins.right
        return 350  # Default fallback

    @staticmethod
    def _resolve_height(
        height: int | str,
        screen_height: int,
        margins: PanelMargins,
        other_panels: Dict[str, PanelLayout],
    ) -> int:
        """Resolve height: handle 'full'/'fill' and pixel values."""
        if isinstance(height, int):
            return height
        elif height == "full":
            return screen_height - margins.top - margins.bottom
        elif height == "fill":
            return screen_height - margins.top - margins.bottom
        return 200  # Default fallback

    @staticmethod
    def _resolve_position(
        panel: PanelLayout,
        screen_width: int,
        screen_height: int,
        panel_width: int,
        panel_height: int,
    ) -> Tuple[int, int]:
        """Resolve position based on anchor and offset."""
        pos = panel.position
        margins = panel.margins

        # Start with anchor position
        anchor = panel.anchor.lower()

        if anchor == "top_left":
            x = margins.left + pos.x
            y = margins.top + pos.y
        elif anchor == "top_right":
            x = screen_width - margins.right - panel_width + pos.x
            y = margins.top + pos.y
        elif anchor == "bottom_left":
            x = margins.left + pos.x
            y = screen_height - margins.bottom - panel_height + pos.y
        elif anchor == "bottom_right":
            x = screen_width - margins.right - panel_width + pos.x
            y = screen_height - margins.bottom - panel_height + pos.y
        else:
            # Default to top-left
            x = margins.left + pos.x
            y = margins.top + pos.y

        return x, y


class LayoutManager:
    """Manages layout configuration and panel positioning."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize layout manager.

        Args:
            config_path: Path to menu_layouts.json config file
        """
        if config_path is None:
            config_path = (
                PROJECT_ROOT / "src" / "gamelib" / "ui" / "config" / "menu_layouts.json"
            )

        self.config_path = Path(config_path)
        self.panels: Dict[str, PanelLayout] = {}
        self.debug_config: Dict[str, Any] = {}
        self.theme_colors: Dict[str, str] = {}
        self.property_colors: Dict[str, str] = {}

        # File watching
        self._last_modified = 0.0
        self._watch_enabled = False

        # Load configuration
        self.reload_config()

        # Enable file watching
        self._watch_enabled = self.debug_config.get("file_watch_enabled", True)

    def reload_config(self) -> bool:
        """
        Load or reload configuration from disk.

        Returns:
            True if config was successfully loaded, False otherwise
        """
        if not self.config_path.exists():
            print(f"Warning: Layout config not found at {self.config_path}")
            return False

        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)

            # Parse panels
            self.panels.clear()
            for panel_name, panel_data in config.get("panels", {}).items():
                panel = self._parse_panel_config(panel_name, panel_data)
                if panel:
                    self.panels[panel_name] = panel

            # Parse theme
            theme = config.get("theme", {})
            self.theme_colors = theme.get("colors", {})
            self.property_colors = theme.get("property_colors", {})

            # Parse debug config
            self.debug_config = config.get("debug", {})

            # Update file modification time
            self._last_modified = self.config_path.stat().st_mtime

            return True

        except Exception as e:
            print(f"Error loading layout config: {e}")
            return False

    def check_reload(self) -> bool:
        """
        Check if config file has been modified and reload if needed.

        Returns:
            True if config was reloaded, False otherwise
        """
        if not self._watch_enabled or not self.config_path.exists():
            return False

        try:
            current_mtime = self.config_path.stat().st_mtime
            if current_mtime > self._last_modified:
                print("Layout config changed, reloading...")
                return self.reload_config()
        except Exception as e:
            print(f"Error checking config file: {e}")

        return False

    def get_panel_layout(self, panel_name: str) -> Optional[PanelLayout]:
        """
        Get layout configuration for a panel.

        Args:
            panel_name: Name of panel (e.g., "thumbnail_menu")

        Returns:
            PanelLayout or None if not found
        """
        return self.panels.get(panel_name)

    def get_panel_rect(
        self, panel_name: str, screen_width: int, screen_height: int
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Get calculated rectangle for a panel.

        Args:
            panel_name: Name of panel
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels

        Returns:
            Tuple of (x, y, width, height) or None if panel not found
        """
        panel = self.get_panel_layout(panel_name)
        if not panel or not panel.enabled:
            return None

        return LayoutCalculator.calculate_panel_rect(
            panel, screen_width, screen_height, self.panels
        )

    def get_enabled_panels(self) -> Dict[str, PanelLayout]:
        """
        Get all enabled panels.

        Returns:
            Dict of enabled panels
        """
        return {name: panel for name, panel in self.panels.items() if panel.enabled}

    def set_panel_enabled(self, panel_name: str, enabled: bool) -> bool:
        """
        Enable or disable a panel.

        Args:
            panel_name: Name of panel
            enabled: True to enable, False to disable

        Returns:
            True if successful, False if panel not found
        """
        if panel_name in self.panels:
            self.panels[panel_name].enabled = enabled
            return True
        return False

    def save_config(self) -> bool:
        """
        Save current configuration to disk.

        Returns:
            True if successful, False otherwise
        """
        try:
            config = {
                "metadata": {
                    "version": "1.0",
                    "description": "Editor attribute menu layout configuration",
                    "last_modified": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
                "panels": {},
                "theme": {
                    "colors": self.theme_colors,
                    "property_colors": self.property_colors,
                },
                "debug": self.debug_config,
            }

            # Convert panels back to dict format
            for panel_name, panel in self.panels.items():
                config["panels"][panel_name] = self._panel_to_dict(panel)

            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=2)

            self._last_modified = self.config_path.stat().st_mtime
            print(f"Saved layout config to {self.config_path}")
            return True

        except Exception as e:
            print(f"Error saving layout config: {e}")
            return False

    def _parse_panel_config(self, panel_name: str, data: Dict[str, Any]) -> Optional[PanelLayout]:
        """Parse panel configuration from dict."""
        try:
            pos_data = data.get("position", {})
            position = PanelPosition(
                x=pos_data.get("x", 0),
                y=pos_data.get("y", 0),
                reference=pos_data.get("reference", "screen"),
            )

            size_data = data.get("size", {})
            size = PanelSize(
                width=size_data.get("width", 350),
                height=size_data.get("height", 200),
            )

            margins_data = data.get("margins", {})
            margins = PanelMargins(
                top=margins_data.get("top", 0),
                right=margins_data.get("right", 0),
                bottom=margins_data.get("bottom", 0),
                left=margins_data.get("left", 0),
            )

            return PanelLayout(
                name=data.get("name", panel_name),
                panel_type=data.get("type", panel_name),
                enabled=data.get("enabled", True),
                anchor=data.get("anchor", "top_left"),
                position=position,
                size=size,
                margins=margins,
                layout_config=data.get("layout", {}),
            )
        except Exception as e:
            print(f"Error parsing panel config '{panel_name}': {e}")
            return None

    def _panel_to_dict(self, panel: PanelLayout) -> Dict[str, Any]:
        """Convert panel layout back to dict format."""
        return {
            "name": panel.name,
            "type": panel.panel_type,
            "enabled": panel.enabled,
            "anchor": panel.anchor,
            "position": {
                "x": panel.position.x,
                "y": panel.position.y,
                "reference": panel.position.reference,
            },
            "size": {
                "width": panel.size.width,
                "height": panel.size.height,
            },
            "margins": {
                "top": panel.margins.top,
                "right": panel.margins.right,
                "bottom": panel.margins.bottom,
                "left": panel.margins.left,
            },
            "layout": panel.layout_config,
        }

    def debug_info(self, screen_width: int, screen_height: int) -> str:
        """
        Get debug information about current layout.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels

        Returns:
            Formatted debug string
        """
        info = f"Layout Debug Info (Screen: {screen_width}x{screen_height})\n"
        info += "=" * 60 + "\n"

        for panel_name, panel in self.get_enabled_panels().items():
            rect = self.get_panel_rect(panel_name, screen_width, screen_height)
            if rect:
                x, y, w, h = rect
                info += f"{panel.name:20} | Pos: ({x:4}, {y:4}) | Size: {w:4}x{h:4}\n"

        return info
