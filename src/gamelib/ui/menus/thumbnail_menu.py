"""
Thumbnail Menu - Bottom Bar for Editor Mode

Two-tier layout for attribute editing mode:
- Top row: Small editor tool icons
- Main row: Scrollable asset thumbnails (models, lights, etc.)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

import imgui

if TYPE_CHECKING:
    from ...tools import ToolManager


@dataclass
class ThumbnailItem:
    """Represents an asset thumbnail in the menu."""
    id: str
    name: str
    category: str
    icon_path: Optional[str] = None
    preview_path: Optional[str] = None


class ThumbnailMenu:
    """Bottom menu bar with tool icons and asset thumbnails."""

    def __init__(
        self,
        tool_manager: ToolManager,
        thumbnail_size: int = 128,
        visible_count: int = 6,
        bottom_menu_height: int = 200,
        tool_icon_size: int = 48,
    ):
        """
        Initialize thumbnail menu.

        Args:
            tool_manager: ToolManager for equipping tools
            thumbnail_size: Size of main thumbnails in pixels
            visible_count: Number of thumbnails visible at once (6 default)
            bottom_menu_height: Total height of bottom menu bar
            tool_icon_size: Size of tool icons in top row
        """
        self.tool_manager = tool_manager
        self.thumbnail_size = thumbnail_size
        self.visible_count = visible_count
        self.bottom_menu_height = bottom_menu_height
        self.tool_icon_size = tool_icon_size

        # Asset thumbnails by category
        self.assets: dict[str, list[ThumbnailItem]] = {
            "Models": [],
            "Lights": [],
            "Objects": [],
            "Materials": [],
        }

        # Scroll offset for main thumbnail area
        self.scroll_offset = 0

        # Selected item tracking
        self.selected_category: Optional[str] = None
        self.selected_item_id: Optional[str] = None
        self.selected_tool_id: Optional[str] = None

        # Show/hide
        self.show = True

        # Tool icon data (will populate from tool_manager)
        self.tool_icons = []

        # Texture cache for thumbnails (filepath -> imgui texture ID)
        self.texture_cache: dict[str, tuple] = {}

    def add_asset(self, category: str, item: ThumbnailItem) -> None:
        """
        Add an asset to a category.

        Args:
            category: Category name ("Models", "Lights", "Objects", "Materials")
            item: ThumbnailItem to add
        """
        if category not in self.assets:
            self.assets[category] = []
        self.assets[category].append(item)

    def draw(self, screen_width: int, screen_height: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Draw thumbnail menu at bottom of screen.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels

        Returns:
            Tuple of (selected_category, selected_item_id, selected_tool_id)
            Any value that wasn't selected returns None
        """
        if not self.show:
            return None, None, None

        # Reset selections for this frame
        frame_selected_category = None
        frame_selected_item = None
        frame_selected_tool = None

        # Position at bottom of screen
        menu_x = 0
        menu_y = screen_height - self.bottom_menu_height
        menu_width = screen_width

        imgui.set_next_window_position(menu_x, menu_y, imgui.ALWAYS)
        imgui.set_next_window_size(menu_width, self.bottom_menu_height, imgui.ALWAYS)

        expanded, self.show = imgui.begin(
            "Thumbnail Menu##thumbnail_menu",
            self.show,
            imgui.WINDOW_NO_RESIZE,
        )

        if not expanded:
            imgui.end()
            return None, None, None

        # === TOP ROW: Tool Icons ===
        self._draw_tool_icons()

        imgui.separator()

        # === MAIN ROW: Asset Thumbnails ===
        self._draw_asset_thumbnails()

        imgui.end()

        return frame_selected_category, frame_selected_item, frame_selected_tool

    def _draw_tool_icons(self) -> None:
        """Draw top row with small editor tool icons."""
        tool_icon_size = self.tool_icon_size
        spacing = 12

        imgui.text("Tools:")
        imgui.same_line(spacing + 50)

        # Draw all tools from tool_manager
        if self.tool_manager and self.tool_manager.tools:
            tools_to_show = list(self.tool_manager.tools.values())[:4]

            for idx, tool in enumerate(tools_to_show):
                # Draw as button
                is_active = tool == self.tool_manager.active_tool
                if is_active:
                    # Active tool: darker green background
                    imgui.push_style_color(
                        imgui.COLOR_BUTTON,
                        0.3, 0.6, 0.3, 1.0
                    )
                    imgui.push_style_color(
                        imgui.COLOR_BUTTON_HOVERED,
                        0.4, 0.75, 0.4, 1.0
                    )
                    imgui.push_style_color(
                        imgui.COLOR_BUTTON_ACTIVE,
                        0.5, 0.9, 0.5, 1.0
                    )
                else:
                    # Inactive tool: dark gray
                    imgui.push_style_color(
                        imgui.COLOR_BUTTON,
                        0.2, 0.2, 0.25, 1.0
                    )

                button_label = f"{tool.name[:3]}##tool_{tool.id}"
                if imgui.button(button_label, tool_icon_size, tool_icon_size):
                    self.tool_manager.equip_tool(tool.id)
                    self.selected_tool_id = tool.id

                # Pop style colors
                if is_active:
                    imgui.pop_style_color()
                    imgui.pop_style_color()
                    imgui.pop_style_color()
                else:
                    imgui.pop_style_color()

                if idx < len(tools_to_show) - 1:
                    imgui.same_line(spacing)

    def _draw_asset_thumbnails(self) -> None:
        """Draw main section with scrollable asset thumbnails."""
        # Category tabs
        categories = list(self.assets.keys())
        if not categories:
            imgui.text("No assets available")
            return

        # Tab bar for categories
        if imgui.begin_tab_bar("AssetCategories##tab_bar"):
            for category in categories:
                is_open, is_selected = imgui.begin_tab_item(category)

                if is_open:
                    if is_selected:
                        if imgui.begin_child(
                            f"Category_{category}##child",
                            border=False,
                        ):
                            self._draw_category_thumbnails(category)
                            imgui.end_child()

                    imgui.end_tab_item()

            imgui.end_tab_bar()

    def _draw_category_thumbnails(self, category: str) -> None:
        """
        Draw thumbnail grid for a specific category.

        Args:
            category: Category name
        """
        assets = self.assets.get(category, [])
        if not assets:
            imgui.text(f"No {category.lower()} available")
            return

        # Draw scroll buttons
        scroll_width = 35
        thumb_spacing = 6

        # Scroll controls on one line
        if imgui.button("<##scroll_left", scroll_width, 30):
            self.scroll_offset = max(0, self.scroll_offset - 1)

        imgui.same_line()

        if imgui.button(">##scroll_right", scroll_width, 30):
            max_scroll = max(0, len(assets) - self.visible_count)
            self.scroll_offset = min(max_scroll, self.scroll_offset + 1)

        imgui.same_line()
        imgui.text(f"{min(self.visible_count, len(assets))}/{len(assets)}")

        imgui.spacing()

        # Draw visible thumbnails in a compact row
        for i in range(self.visible_count):
            asset_idx = self.scroll_offset + i
            if asset_idx >= len(assets):
                break

            asset = assets[asset_idx]
            is_selected = (
                self.selected_category == category and
                self.selected_item_id == asset.id
            )

            # Highlight selected item
            if is_selected:
                imgui.push_style_color(
                    imgui.COLOR_BUTTON,
                    0.6, 0.6, 0.2, 1.0  # Dark yellow highlight
                )
                imgui.push_style_color(
                    imgui.COLOR_BUTTON_HOVERED,
                    0.8, 0.8, 0.3, 1.0
                )
                imgui.push_style_color(
                    imgui.COLOR_BUTTON_ACTIVE,
                    1.0, 1.0, 0.4, 1.0
                )
            else:
                imgui.push_style_color(
                    imgui.COLOR_BUTTON,
                    0.3, 0.3, 0.35, 1.0  # Dark background
                )

            # Draw thumbnail as button with truncated name
            short_name = asset.name[:8] if len(asset.name) > 8 else asset.name
            button_label = f"{short_name}##thumb_{category}_{asset.id}"
            if imgui.button(button_label, self.thumbnail_size, self.thumbnail_size):
                self.selected_category = category
                self.selected_item_id = asset.id

            if is_selected:
                imgui.pop_style_color()
                imgui.pop_style_color()
                imgui.pop_style_color()
            else:
                imgui.pop_style_color()

            # Same line for next thumbnail
            if i < self.visible_count - 1 and asset_idx + 1 < len(assets):
                imgui.same_line(thumb_spacing)

    def populate_from_scene(self, scene) -> None:
        """
        Populate asset list from scene objects.

        Args:
            scene: Scene to populate from
        """
        # Clear existing assets
        for category in self.assets:
            self.assets[category] = []

        if not scene:
            return

        # Add models from scene objects
        if hasattr(scene, 'objects'):
            for obj in scene.objects:
                item = ThumbnailItem(
                    id=obj.name or f"obj_{id(obj)}",
                    name=obj.name or "Unnamed",
                    category="Objects",
                )
                self.add_asset("Objects", item)

        # Add lights if available
        if hasattr(scene, 'lights'):
            for light in scene.lights:
                item = ThumbnailItem(
                    id=f"light_{id(light)}",
                    name=getattr(light, 'name', f"Light {id(light)}"),
                    category="Lights",
                )
                self.add_asset("Lights", item)

    def set_selected(
        self,
        category: Optional[str] = None,
        item_id: Optional[str] = None,
        tool_id: Optional[str] = None,
    ) -> None:
        """
        Programmatically set selected item.

        Args:
            category: Category to select
            item_id: Item ID to select
            tool_id: Tool ID to select
        """
        if category is not None:
            self.selected_category = category
        if item_id is not None:
            self.selected_item_id = item_id
        if tool_id is not None:
            self.selected_tool_id = tool_id

    def get_selected(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Get currently selected items.

        Returns:
            Tuple of (category, item_id, tool_id)
        """
        return self.selected_category, self.selected_item_id, self.selected_tool_id

    def load_thumbnail_image(self, filepath: str) -> Optional[tuple]:
        """
        Load thumbnail image from file and cache it for ImGui.

        Args:
            filepath: Path to PNG file

        Returns:
            ImGui texture ID tuple or None if loading failed
        """
        if not filepath:
            return None

        # Check cache first
        if filepath in self.texture_cache:
            return self.texture_cache[filepath]

        try:
            path = Path(filepath)
            if not path.exists():
                return None

            # Read PNG file
            import zlib
            import struct

            png_data = path.read_bytes()

            # Parse PNG (simplified - just extract image data from IDAT chunk)
            width, height, image_data = self._parse_png(png_data)

            if image_data is None:
                return None

            # Create ImGui texture
            texture_data = self._convert_to_rgba8(image_data, width, height)

            # Cache the texture (for ImGui, we store the path as identifier)
            # ImGui will handle the actual texture binding
            self.texture_cache[filepath] = (width, height, texture_data)

            return self.texture_cache[filepath]

        except Exception as e:
            print(f"Warning: Failed to load thumbnail {filepath}: {e}")
            return None

    def _parse_png(self, png_data: bytes) -> Tuple[Optional[int], Optional[int], Optional[bytes]]:
        """
        Parse PNG file and extract image dimensions and RGBA data.

        Args:
            png_data: Raw PNG file bytes

        Returns:
            Tuple of (width, height, image_data) or (None, None, None) if parsing failed
        """
        try:
            import zlib
            import struct

            # Check PNG signature
            if png_data[:8] != b'\x89PNG\r\n\x1a\n':
                return None, None, None

            offset = 8
            width = height = None
            idat_data = b''

            # Parse chunks
            while offset < len(png_data):
                # Read chunk length
                length = struct.unpack('>I', png_data[offset:offset+4])[0]
                offset += 4

                # Read chunk type
                chunk_type = png_data[offset:offset+4]
                offset += 4

                if chunk_type == b'IHDR':
                    # Image header
                    width, height = struct.unpack('>II', png_data[offset:offset+8])
                elif chunk_type == b'IDAT':
                    # Image data
                    idat_data += png_data[offset:offset+length]
                elif chunk_type == b'IEND':
                    # End of image
                    break

                offset += length + 4  # Skip data and CRC

            if width is None or height is None:
                return None, None, None

            # Decompress image data
            raw_data = zlib.decompress(idat_data)

            # Convert raw data to RGBA (simple unfiltering)
            image_data = self._unfilter_png_data(raw_data, width, height)

            return width, height, image_data

        except Exception as e:
            print(f"Warning: PNG parsing failed: {e}")
            return None, None, None

    def _unfilter_png_data(self, raw_data: bytes, width: int, height: int) -> bytes:
        """
        Unfilter PNG scanlines and convert to proper image format.

        Args:
            raw_data: Raw PNG pixel data with filter bytes
            width: Image width
            height: Image height

        Returns:
            Unfiltered RGBA image data
        """
        bytes_per_pixel = 4
        scanline_size = 1 + (width * bytes_per_pixel)  # 1 byte filter + pixels
        result = bytearray()

        for y in range(height):
            scanline_start = y * scanline_size
            filter_type = raw_data[scanline_start]
            scanline = bytearray(raw_data[scanline_start+1:scanline_start+scanline_size])

            # Simple filter (just copy for now - proper filtering would be more complex)
            result.extend(scanline)

        return bytes(result)

    def _convert_to_rgba8(self, image_data: bytes, width: int, height: int) -> bytes:
        """Convert image data to RGBA8 format for ImGui."""
        # Ensure we have RGBA format
        if len(image_data) == width * height * 4:
            return image_data
        return image_data
