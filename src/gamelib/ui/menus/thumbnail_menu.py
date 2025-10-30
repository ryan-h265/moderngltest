"""
Thumbnail Menu - Bottom Bar for Editor Mode

Enhanced layout with:
- 4-column × 3-row grid layout (12 items visible)
- ModernGL texture rendering for actual thumbnail images
- Vertical mouse wheel scrolling
- Yellow border selection indicator
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import struct
import zlib

import imgui
import moderngl

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

    def to_dict(self) -> dict:
        """Convert to dictionary for preview display."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "icon_path": self.icon_path,
            "preview_path": self.preview_path,
        }


class ThumbnailMenu:
    """Bottom menu bar with tool icons and grid of asset thumbnails."""

    def __init__(
        self,
        tool_manager: ToolManager,
        ctx: moderngl.Context,
        layout_manager: Optional[object] = None,
        thumbnail_size: int = 96,
        grid_cols: int = 4,
        grid_rows: int = 3,
        bottom_menu_height: int = 200,
        tool_icon_size: int = 48,
    ):
        """
        Initialize thumbnail menu.

        Args:
            tool_manager: ToolManager for equipping tools
            ctx: ModernGL context for texture creation
            layout_manager: LayoutManager for panel positioning (optional)
            thumbnail_size: Size of main thumbnails in pixels
            grid_cols: Number of columns in grid (default 4)
            grid_rows: Number of rows in grid (default 3)
            bottom_menu_height: Total height of bottom menu bar
            tool_icon_size: Size of tool icons in top row
        """
        self.tool_manager = tool_manager
        self.ctx = ctx
        self.layout_manager = layout_manager
        self.thumbnail_size = thumbnail_size
        self.grid_cols = grid_cols
        self.grid_rows = grid_rows
        self.bottom_menu_height = bottom_menu_height
        self.tool_icon_size = tool_icon_size
        self.grid_max_visible = grid_cols * grid_rows

        # Asset thumbnails by category
        self.assets: dict[str, list[ThumbnailItem]] = {
            "Models": [],
            "Lights": [],
            "Objects": [],
            "Materials": [],
        }

        # Scroll offsets for each category
        self.scroll_offsets: dict[str, int] = {cat: 0 for cat in self.assets}

        # Selected item tracking
        self.selected_category: Optional[str] = None
        self.selected_item_id: Optional[str] = None
        self.selected_tool_id: Optional[str] = None

        # Selected tab (for ImGui tab bar)
        self.selected_tab_index: int = 0  # Default to first tab

        # Show/hide
        self.show = True

        # Tool icon data
        self.tool_icons = []

        # Texture cache: filepath -> (width, height, texture_id, texture_obj)
        # Keeps references to both the OpenGL ID and ModernGL object
        # (Must keep the texture object alive to prevent garbage collection)
        self.texture_cache: dict[str, Tuple[int, int, int, object]] = {}
        self.textures: list[object] = []  # Keep all texture objects alive

    def add_asset(self, category: str, item: ThumbnailItem) -> None:
        """
        Add an asset to a category.

        Args:
            category: Category name ("Models", "Lights", "Objects", "Materials")
            item: ThumbnailItem to add
        """
        if category not in self.assets:
            self.assets[category] = []

        print(f"[Thumbnail] add_asset({category}, {item.name}): preview_path={item.preview_path}")
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
            print(f"[Thumbnail] draw() NOT drawing because show=False")
            return None, None, None

        # Debug: Check if assets are loaded
        total_assets = sum(len(items) for items in self.assets.values())
        print(f"[Thumbnail] draw() called. Total assets: {total_assets}")
        if total_assets > 0:
            print(f"[Thumbnail]   ✓ Assets loaded")

        # Reset selections for this frame
        frame_selected_category = None
        frame_selected_item = None
        frame_selected_tool = None

        # Use layout manager for positioning if available
        if self.layout_manager:
            rect = self.layout_manager.get_panel_rect(
                "thumbnail_menu", screen_width, screen_height
            )
            if rect:
                menu_x, menu_y, menu_width, menu_height = rect
                self.bottom_menu_height = menu_height
            else:
                # Fallback if panel not configured
                menu_x = 0
                menu_y = screen_height - self.bottom_menu_height
                menu_width = screen_width
        else:
            # Original fallback positioning
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

        # === MAIN ROW: Asset Thumbnails Grid ===
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
        """Draw main section with grid of asset thumbnails."""
        print(f"[Thumbnail] _draw_asset_thumbnails() called")

        # Category tabs
        categories = list(self.assets.keys())
        print(f"[Thumbnail] Categories: {categories}")

        # Debug: Show content of each category
        for cat in categories:
            assets_in_cat = self.assets.get(cat, [])
            print(f"[Thumbnail]   Category '{cat}': {len(assets_in_cat)} items")
            for asset in assets_in_cat:
                print(f"[Thumbnail]     - {asset.name} (preview_path: {asset.preview_path})")

        if not categories:
            imgui.text("No assets available")
            return

        # Tab bar for categories
        try:
            if imgui.begin_tab_bar("AssetCategories##tab_bar"):
                print(f"[Thumbnail] Tab bar created with {len(categories)} categories")

                # Track if any tab was explicitly selected by ImGui this frame
                any_tab_selected_by_imgui = False

                for tab_idx, category in enumerate(categories):
                    try:
                        is_open, is_selected = imgui.begin_tab_item(category)
                        print(f"[Thumbnail] Tab {tab_idx} '{category}': is_open={is_open}, is_selected={is_selected}")

                        try:
                            # IMPORTANT: Only draw content if this tab is open
                            if is_open:
                                # Track if ImGui selected this tab
                                if is_selected:
                                    any_tab_selected_by_imgui = True
                                    self.selected_tab_index = tab_idx
                                    print(f"[Thumbnail] ImGui selected tab {tab_idx}")

                                # Render if:
                                # 1. ImGui selected this tab, OR
                                # 2. This is the first tab AND nothing else was selected (fallback for first frame)
                                should_render = is_selected or (tab_idx == 0 and not any_tab_selected_by_imgui)

                                if should_render:
                                    if tab_idx == 0 and not is_selected:
                                        print(f"[Thumbnail] Fallback rendering first tab (ImGui not selecting any)")

                                    print(f"[Thumbnail] Drawing grid for tab: {category}")

                                    if imgui.begin_child(
                                        f"ThumbnailGrid_{category}##child",
                                        border=False,
                                    ):
                                        try:
                                            self._draw_category_grid(category)
                                        finally:
                                            imgui.end_child()
                                    else:
                                        print(f"[Thumbnail] Failed to create child window for tab: {category}")
                                else:
                                    print(f"[Thumbnail] Tab {tab_idx} '{category}' not selected, skipping render")
                            else:
                                print(f"[Thumbnail] Tab {tab_idx} '{category}' is NOT open")

                        finally:
                            # CRITICAL: Always call end_tab_item() regardless of is_open
                            imgui.end_tab_item()

                    except Exception as e:
                        print(f"[Thumbnail] Error processing tab {tab_idx}: {e}")
                        import traceback
                        traceback.print_exc()

                imgui.end_tab_bar()
            else:
                print(f"[Thumbnail] ERROR: Failed to create tab bar!")

        except Exception as e:
            print(f"[Thumbnail] Error in tab bar rendering: {e}")
            import traceback
            traceback.print_exc()

    def _draw_category_grid(self, category: str) -> None:
        """
        Draw thumbnail grid for a specific category (4 cols × 3 rows).

        Args:
            category: Category name
        """
        print(f"[Thumbnail] _draw_category_grid({category}) called")

        assets = self.assets.get(category, [])
        print(f"[Thumbnail] Category '{category}' has {len(assets)} assets")

        if not assets:
            imgui.text(f"No {category.lower()} available")
            return

        scroll_offset = self.scroll_offsets.get(category, 0)
        spacing = 8
        total_items = len(assets)
        max_offset = max(0, total_items - self.grid_max_visible)

        # Info text
        visible_count = min(self.grid_max_visible, total_items - scroll_offset)
        imgui.text(f"Items: {visible_count + scroll_offset}/{total_items}")

        imgui.spacing()

        # Draw grid
        col_index = 0
        for display_idx in range(self.grid_max_visible):
            asset_idx = scroll_offset + display_idx
            if asset_idx >= total_items:
                break

            asset = assets[asset_idx]
            self._draw_thumbnail_item(asset, category)

            # Move to next column or row
            col_index += 1
            if col_index < self.grid_cols and asset_idx + 1 < total_items:
                imgui.same_line(spacing)
            else:
                col_index = 0

        # Mouse wheel scrolling
        io = imgui.get_io()
        if io.mouse_wheel != 0:
            scroll_offset = max(0, min(max_offset, scroll_offset - int(io.mouse_wheel)))
            self.scroll_offsets[category] = scroll_offset

    def _draw_thumbnail_item(self, asset: ThumbnailItem, category: str) -> None:
        """
        Draw a single thumbnail item with image and border.

        Args:
            asset: ThumbnailItem to draw
            category: Category name
        """
        is_selected = (
            self.selected_category == category and
            self.selected_item_id == asset.id
        )

        # Try to load and use thumbnail image
        texture_id = None
        if asset.preview_path:
            # Debug: Log what we're trying to load
            texture_id = self.load_thumbnail_image(asset.preview_path)
            if texture_id is None:
                print(f"[Thumbnail] Failed to load image for {asset.name}: preview_path={asset.preview_path}")
        else:
            print(f"[Thumbnail] No preview_path for {asset.name}")

        # Style the button
        if is_selected:
            imgui.push_style_color(
                imgui.COLOR_BUTTON,
                0.2, 0.2, 0.22, 1.0  # Slightly lighter background for selected
            )
        else:
            imgui.push_style_color(
                imgui.COLOR_BUTTON,
                0.15, 0.15, 0.17, 1.0  # Dark background
            )

        button_id = f"##thumb_{category}_{asset.id}"

        # Draw button or image
        clicked = False
        if texture_id is not None:
            # Draw image button with texture
            size = (self.thumbnail_size, self.thumbnail_size)
            clicked = imgui.image_button(
                texture_id,
                *size,
                frame_padding=2,
            )
        else:
            # Fallback: colored button with text
            clicked = imgui.button(
                f"{asset.name[:8]}{button_id}",
                self.thumbnail_size,
                self.thumbnail_size
            )

        imgui.pop_style_color()

        # Draw selection border if selected
        if is_selected:
            draw_list = imgui.get_window_draw_list()
            pos_min = imgui.get_item_rect_min()
            pos_max = imgui.get_item_rect_max()
            border_color = imgui.get_color_u32_rgba(1.0, 1.0, 0.0, 1.0)  # Yellow
            draw_list.add_rect(pos_min, pos_max, border_color, 3.0)  # 3px border

        # Handle click
        if clicked:
            self.selected_category = category
            self.selected_item_id = asset.id

    def populate_from_scene(self, scene) -> None:
        """
        Populate asset list from scene objects and generated thumbnails.

        Args:
            scene: Scene to populate from
        """
        # Clear existing assets
        for category in self.assets:
            self.assets[category] = []

        if not scene:
            return

        # Add light presets with thumbnails
        self._populate_light_presets()

        # Add model library with thumbnails
        self._populate_model_library()

        # Add objects from scene
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

    def _populate_light_presets(self) -> None:
        """Load and add light preset thumbnails from generated assets."""
        from pathlib import Path
        from ...config.settings import PROJECT_ROOT

        lights_dir = PROJECT_ROOT / "assets" / "ui" / "thumbs" / "lights"
        if not lights_dir.exists():
            print(f"[Thumbnail] Lights directory not found: {lights_dir}")
            return

        # Add each light preset thumbnail
        png_files = list(sorted(lights_dir.glob("*.png")))
        print(f"[Thumbnail] Found {len(png_files)} light presets in {lights_dir}")

        for png_file in png_files:
            light_name = png_file.stem
            item = ThumbnailItem(
                id=f"light_preset_{light_name}",
                name=light_name,
                category="Lights",
                preview_path=str(png_file),
            )
            self.add_asset("Lights", item)
            print(f"[Thumbnail] Added light preset: {light_name} -> {png_file}")

    def _populate_model_library(self) -> None:
        """Load and add model library thumbnails from generated assets."""
        from pathlib import Path
        from ...config.settings import PROJECT_ROOT

        models_dir = PROJECT_ROOT / "assets" / "ui" / "thumbs" / "models"
        if not models_dir.exists():
            print(f"[Thumbnail] Models directory not found: {models_dir}")
            return

        # Add each model thumbnail
        png_files = list(sorted(models_dir.glob("*.png")))
        print(f"[Thumbnail] Found {len(png_files)} models in {models_dir}")

        for png_file in png_files:
            model_name = png_file.stem
            item = ThumbnailItem(
                id=f"model_{model_name}",
                name=model_name,
                category="Models",
                preview_path=str(png_file),
            )
            self.add_asset("Models", item)
            print(f"[Thumbnail] Added model: {model_name} -> {png_file}")

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

    def load_thumbnail_image(self, filepath: str) -> Optional[int]:
        """
        Load thumbnail image from PNG file and create ModernGL texture.

        Args:
            filepath: Path to PNG file

        Returns:
            OpenGL texture ID (int) or None if loading failed
        """
        if not filepath:
            print(f"[Thumbnail] Empty filepath")
            return None

        # Check cache first
        if filepath in self.texture_cache:
            cached = self.texture_cache[filepath]
            # cached[0]=width, cached[1]=height, cached[2]=texture_id, cached[3]=texture_obj
            # texture_obj is kept in cache to prevent garbage collection
            print(f"[Thumbnail] Using cached texture for {Path(filepath).name}")
            return cached[2]

        print(f"[Thumbnail] Loading texture from: {filepath}")

        try:
            path = Path(filepath)
            if not path.exists():
                print(f"[Thumbnail] File not found: {path}")
                return None

            print(f"[Thumbnail] File exists, reading {path.stat().st_size} bytes")

            # Parse PNG file
            png_data = path.read_bytes()
            print(f"[Thumbnail] Parsing PNG...")
            width, height, rgba_data = self._parse_png(png_data)

            if rgba_data is None or width is None or height is None:
                print(f"[Thumbnail] PNG parsing failed: width={width}, height={height}, data={rgba_data is not None}")
                return None

            print(f"[Thumbnail] PNG parsed: {width}x{height}, data size={len(rgba_data)}")

            # Create ModernGL texture from RGBA data
            try:
                print(f"[Thumbnail] Creating ModernGL texture...")
                texture = self.ctx.texture((width, height), 4, rgba_data)
                texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
                texture_id = texture.glo  # Get OpenGL object ID

                # Cache: (width, height, texture_id, texture_obj)
                # Must keep texture_obj reference to prevent garbage collection!
                self.texture_cache[filepath] = (width, height, texture_id, texture)
                self.textures.append(texture)  # Keep alive in list too

                print(f"[Thumbnail] ✓ Successfully loaded texture: {path.name} (ID: {texture_id})")
                return texture_id
            except Exception as e:
                print(f"[Thumbnail] ✗ Failed to create ModernGL texture: {e}")
                import traceback
                traceback.print_exc()
                return None

        except Exception as e:
            print(f"[Thumbnail] ✗ Failed to load thumbnail: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_png(self, png_data: bytes) -> Tuple[Optional[int], Optional[int], Optional[bytes]]:
        """
        Parse PNG file and extract image dimensions and RGBA data.

        Args:
            png_data: Raw PNG file bytes

        Returns:
            Tuple of (width, height, rgba_data) or (None, None, None) if parsing failed
        """
        try:
            # Check PNG signature
            if png_data[:8] != b'\x89PNG\r\n\x1a\n':
                return None, None, None

            offset = 8
            width = height = None
            idat_data = b''
            bit_depth = 8
            color_type = 6  # RGBA

            # Parse chunks
            while offset < len(png_data):
                # Read chunk length
                length = struct.unpack('>I', png_data[offset:offset+4])[0]
                offset += 4

                # Read chunk type
                chunk_type = png_data[offset:offset+4]
                offset += 4

                if chunk_type == b'IHDR':
                    # Image header (13 bytes total)
                    # Format: width(4) height(4) bit_depth(1) color_type(1) compression(1) filter(1) interlace(1)
                    width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                        '>IIBBBBB', png_data[offset:offset+13]
                    )
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
            try:
                raw_data = zlib.decompress(idat_data)
            except Exception as e:
                print(f"Warning: Failed to decompress PNG data: {e}")
                return None, None, None

            # Convert to RGBA if needed
            if color_type == 6:  # Already RGBA
                bytes_per_pixel = 4
            elif color_type == 2:  # RGB
                bytes_per_pixel = 3
            elif color_type == 0:  # Grayscale
                bytes_per_pixel = 1
            elif color_type == 3:  # Indexed
                bytes_per_pixel = 1
            else:
                return None, None, None

            # Unfilter scanlines
            try:
                image_data = self._unfilter_png_data(raw_data, width, height, bytes_per_pixel)
            except Exception as e:
                print(f"Warning: Failed to unfilter PNG data: {e}")
                return None, None, None

            # Convert to RGBA8 if needed
            rgba_data = self._convert_to_rgba8(image_data, width, height, color_type, bytes_per_pixel)

            return width, height, rgba_data

        except Exception as e:
            print(f"Warning: PNG parsing failed: {e}")
            return None, None, None

    def _unfilter_png_data(self, raw_data: bytes, width: int, height: int, bytes_per_pixel: int) -> bytes:
        """
        Unfilter PNG scanlines using proper PNG filter algorithms.

        Implements PNG filter types:
        - 0: None
        - 1: Sub (X + A)
        - 2: Up (X + B)
        - 3: Average (X + floor((A+B)/2))
        - 4: Paeth (X + Paeth(A,B,C))

        Args:
            raw_data: Raw PNG pixel data with filter bytes
            width: Image width
            height: Image height
            bytes_per_pixel: Bytes per pixel (1, 3, or 4)

        Returns:
            Unfiltered image data as bytes
        """
        scanline_size = 1 + (width * bytes_per_pixel)  # 1 byte filter + pixels
        result = bytearray()
        prev_scanline = bytearray(width * bytes_per_pixel)

        for y in range(height):
            scanline_start = y * scanline_size
            if scanline_start + scanline_size > len(raw_data):
                # Incomplete scanline
                break

            filter_type = raw_data[scanline_start]
            scanline_data = bytearray(raw_data[scanline_start+1:scanline_start+scanline_size])

            # Apply filter based on type
            if filter_type == 0:  # None
                pass
            elif filter_type == 1:  # Sub
                for x in range(bytes_per_pixel, len(scanline_data)):
                    scanline_data[x] = (scanline_data[x] + scanline_data[x-bytes_per_pixel]) & 0xFF
            elif filter_type == 2:  # Up
                for x in range(len(scanline_data)):
                    scanline_data[x] = (scanline_data[x] + prev_scanline[x]) & 0xFF
            elif filter_type == 3:  # Average
                for x in range(len(scanline_data)):
                    left = scanline_data[x-bytes_per_pixel] if x >= bytes_per_pixel else 0
                    up = prev_scanline[x]
                    avg = (left + up) // 2
                    scanline_data[x] = (scanline_data[x] + avg) & 0xFF
            elif filter_type == 4:  # Paeth
                for x in range(len(scanline_data)):
                    left = scanline_data[x-bytes_per_pixel] if x >= bytes_per_pixel else 0
                    up = prev_scanline[x]
                    up_left = prev_scanline[x-bytes_per_pixel] if x >= bytes_per_pixel else 0
                    paeth = self._paeth_predictor(left, up, up_left)
                    scanline_data[x] = (scanline_data[x] + paeth) & 0xFF

            result.extend(scanline_data)
            prev_scanline = bytearray(scanline_data)

        return bytes(result)

    @staticmethod
    def _paeth_predictor(a: int, b: int, c: int) -> int:
        """
        Paeth predictor function for PNG filter type 4.

        Args:
            a: Left pixel value
            b: Up pixel value
            c: Up-left pixel value

        Returns:
            Predicted value
        """
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)

        if pa <= pb and pa <= pc:
            return a
        elif pb <= pc:
            return b
        else:
            return c

    def _convert_to_rgba8(
        self, image_data: bytes, width: int, height: int, color_type: int, bytes_per_pixel: int
    ) -> bytes:
        """
        Convert image data to RGBA8 format for ImGui/OpenGL.

        Args:
            image_data: Unfiltered image data
            width: Image width
            height: Image height
            color_type: PNG color type (0=gray, 2=RGB, 3=indexed, 6=RGBA)
            bytes_per_pixel: Original bytes per pixel

        Returns:
            RGBA8 formatted data
        """
        result = bytearray()

        if color_type == 6 and bytes_per_pixel == 4:
            # Already RGBA
            return image_data

        for i in range(0, len(image_data), bytes_per_pixel):
            if color_type == 6:  # RGBA
                r, g, b, a = image_data[i:i+4]
                result.extend([r, g, b, a])
            elif color_type == 2:  # RGB
                r, g, b = image_data[i:i+3]
                result.extend([r, g, b, 255])
            elif color_type == 0:  # Grayscale
                gray = image_data[i]
                result.extend([gray, gray, gray, 255])
            else:
                # Default: white with full alpha
                result.extend([255, 255, 255, 255])

        return bytes(result)

    def cleanup(self) -> None:
        """Clean up GPU resources (textures)."""
        # ModernGL textures are automatically cleaned up when the context is destroyed
        # But we can explicitly release if needed
        self.texture_cache.clear()
