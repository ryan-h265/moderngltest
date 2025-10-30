"""
Native ModernGL Thumbnail Menu - Horizontally Scrollable Grid

Uses IconManager + UISpriteRenderer instead of ImGui for maximum control
and to avoid ImGui state machine issues.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import moderngl
from pyrr import matrix44
import numpy as np


@dataclass
class ThumbnailAsset:
    """Represents a single thumbnail asset."""
    asset_id: str
    name: str
    preview_path: Path
    category: str


class NativeThumbnailMenu:
    """Horizontally scrollable thumbnail grid using native ModernGL rendering."""

    def __init__(
        self,
        ctx: moderngl.Context,
        ui_shader: moderngl.Program,
        tool_manager=None,
        text_manager=None,
        thumbnail_size: int = 96,
        grid_cols: int = 4,
        grid_rows: int = 3,
        bottom_menu_height: int = 200,
        padding: int = 8,
        tool_icon_size: int = 48,
    ):
        """
        Initialize native thumbnail menu.

        Args:
            ctx: ModernGL context
            ui_shader: Shader program for rendering UI sprites
            tool_manager: Tool manager for tool operations
            text_manager: Text manager for rendering text labels
            thumbnail_size: Size of each thumbnail in pixels
            grid_cols: Number of columns in grid
            grid_rows: Number of rows in grid
            bottom_menu_height: Total height of bottom menu
            padding: Padding between thumbnails
        """
        self.ctx = ctx
        self.ui_shader = ui_shader
        self.tool_manager = tool_manager
        self.text_manager = text_manager
        self.thumbnail_size = thumbnail_size
        self.grid_cols = grid_cols
        self.grid_rows = grid_rows
        self.bottom_menu_height = bottom_menu_height
        self.padding = padding
        self.tool_icon_size = tool_icon_size
        self.grid_max_visible = grid_cols * grid_rows

        # Asset management
        self.assets: Dict[str, List[ThumbnailAsset]] = {
            "Models": [],
            "Lights": [],
            "Objects": [],
            "Materials": [],
        }

        # Rendering
        self.icon_ids: Dict[str, int] = {}  # asset_id -> icon_id mapping
        self.texture_cache: Dict[str, int] = {}  # preview_path -> icon_id
        self.loaded_textures: set = set()  # Track which assets have been rendered
        self.tool_label_text_ids: Dict[str, int] = {}  # tool_id -> text_id mapping

        # UI state
        self.show = True
        self.scroll_offset: Dict[str, int] = {}  # category -> offset
        for cat in self.assets:
            self.scroll_offset[cat] = 0

        self.selected_category: Optional[str] = None
        self.selected_asset_id: Optional[str] = None
        self.selected_icon_id: Optional[int] = None
        self._frame_selection_handled = False  # Track if selection was reported this frame

        # Track touch bounds for click detection
        self.thumbnail_bounds: Dict[int, Tuple[float, float, float, float]] = {}
        # icon_id -> (x, y, width, height)

        # Tool button bounds for click detection
        self.tool_button_bounds: Dict[str, Tuple[float, float, float, float]] = {}
        # tool_id -> (x, y, width, height)

        # Menu bounds
        self.menu_x = 0.0
        self.menu_y = 0.0
        self.menu_width = 800.0

        print("[NativeThumbnailMenu] Initialized")

    def add_asset(self, category: str, asset: ThumbnailAsset) -> None:
        """Add an asset to a category."""
        if category not in self.assets:
            self.assets[category] = []
        self.assets[category].append(asset)
        # print(f"[NativeThumbnailMenu] Added asset: {asset.name} ({category})")

    def populate_from_scene(self, scene) -> None:
        """Populate from scene objects."""
        # Clear existing
        for cat in self.assets:
            self.assets[cat] = []

        if not scene:
            return

        # print("[NativeThumbnailMenu] Populating from scene...")

        # Add light presets from assets
        self._populate_light_presets()

        # Add model library from assets
        self._populate_model_library()

        # print(f"[NativeThumbnailMenu] Populated with {sum(len(items) for items in self.assets.values())} assets")

    def _populate_light_presets(self) -> None:
        """Load light preset thumbnails."""
        from ...config.settings import PROJECT_ROOT

        lights_dir = PROJECT_ROOT / "assets" / "ui" / "thumbs" / "lights"
        if not lights_dir.exists():
            # print(f"[NativeThumbnailMenu] Lights directory not found: {lights_dir}")
            return

        png_files = list(sorted(lights_dir.glob("*.png")))
        # print(f"[NativeThumbnailMenu] Found {len(png_files)} light presets")

        for png_file in png_files:
            light_name = png_file.stem
            asset = ThumbnailAsset(
                asset_id=f"light_preset_{light_name}",
                name=light_name,
                preview_path=png_file,
                category="Lights",
            )
            self.add_asset("Lights", asset)

    def _populate_model_library(self) -> None:
        """Load model library thumbnails."""
        from ...config.settings import PROJECT_ROOT

        models_dir = PROJECT_ROOT / "assets" / "ui" / "thumbs" / "models"
        if not models_dir.exists():
            # print(f"[NativeThumbnailMenu] Models directory not found: {models_dir}")
            return

        png_files = list(sorted(models_dir.glob("*.png")))
        # print(f"[NativeThumbnailMenu] Found {len(png_files)} models")

        for png_file in png_files:
            model_name = png_file.stem
            asset = ThumbnailAsset(
                asset_id=f"model_{model_name}",
                name=model_name,
                preview_path=png_file,
                category="Models",
            )
            self.add_asset("Models", asset)

    def render(self, icon_manager, screen_width: int, screen_height: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Render the thumbnail menu.

        Args:
            icon_manager: IconManager for rendering icons
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels

        Returns:
            Tuple of (selected_category, selected_asset_id) or (None, None)
        """
        if not self.show:
            return None, None

        # Set menu bounds
        self.menu_x = 0.0
        self.menu_y = float(screen_height - self.bottom_menu_height)
        self.menu_width = float(screen_width)

        # Get default category (first with assets)
        if self.selected_category is None:
            for cat, assets in self.assets.items():
                if assets:
                    self.selected_category = cat
                    break

        if self.selected_category is None or not self.assets[self.selected_category]:
            return None, None

        # Setup render state for entire menu
        self._setup_render_state()

        # Render menu background (optional: could use a colored quad)
        self._render_background(icon_manager)

        # Render tool selection buttons
        self._render_tool_buttons(icon_manager)

        # Render thumbnails for selected category
        self._render_category_grid_internal(icon_manager, self.selected_category)

        # Restore render state
        self._restore_render_state()

        # Return selected asset ONLY if it was just clicked (report once per click)
        frame_selected_category = None
        frame_selected_asset = None

        if self._frame_selection_handled:
            frame_selected_category = self.selected_category
            frame_selected_asset = self.selected_asset_id
            self._frame_selection_handled = False  # Reset for next frame

        return frame_selected_category, frame_selected_asset

    def _render_background(self, icon_manager) -> None:
        """Render semi-transparent background for menu area."""
        # TODO: Could create a quad with alpha = 0.8, color = gray
        # For now, just render the thumbnails
        pass

    def _render_tool_buttons(self, icon_manager) -> None:
        """
        Render tool selection buttons above the thumbnail grid.

        Tool buttons from left to right:
        - Model Placer
        - Light Editor
        - Object Editor
        - Delete Tool
        """
        if not self.tool_manager:
            return

        # Tool button positioning
        button_x = self.menu_x + self.padding
        button_y = self.menu_y + self.padding

        # Tool definitions: (tool_id, label)
        tools = [
            ("model_placer", "Model"),
            ("light_editor", "Light"),
            ("object_editor", "Object"),
            ("delete_tool", "Delete"),
        ]

        # Clear previous bounds
        self.tool_button_bounds.clear()

        # Get active tool
        active_tool = self.tool_manager.get_active_tool()
        active_tool_id = active_tool.definition.id if active_tool else None

        # Render each tool button
        current_x = button_x
        for tool_id, label in tools:
            # Check if this is the active tool
            is_active = tool_id == active_tool_id

            # Render text label with button background (background acts as button)
            if self.text_manager:
                bounds = self._render_tool_label_with_button(current_x, button_y, tool_id, label, is_active)
                # bounds is (x, y, width, height)
                x, y, width, height = bounds
                self.tool_button_bounds[tool_id] = (x, y, width, height)
                current_x = x + width + self.padding
            else:
                # Fallback: render colored quad if text manager not available
                self._render_tool_button_quad(current_x, button_y, (0.6, 0.6, 0.6, 1.0))
                self.tool_button_bounds[tool_id] = (current_x, button_y, self.tool_icon_size, self.tool_icon_size)
                current_x += self.tool_icon_size + self.padding

    def _render_tool_label_with_button(self, x: float, y: float, tool_id: str, label: str, is_active: bool) -> Tuple[float, float, float, float]:
        """
        Render text label with a button background.

        The button background is rendered using the TextManager's background_color feature,
        so the button width automatically scales based on the text length.

        Args:
            x: Button X position
            y: Button Y position
            tool_id: Tool identifier
            label: Text label to display
            is_active: Whether this tool is currently active

        Returns:
            Tuple of (x, y, width, height) representing the button bounds
        """
        if not self.text_manager:
            return (x, y, self.tool_icon_size, self.tool_icon_size)

        # Text color: white
        text_color = (1.0, 1.0, 1.0, 1.0)

        # Button background color based on active state
        if is_active:
            # Bright green for active tool
            button_color = (0.3, 0.8, 0.3, 1.0)
        else:
            # Gray for inactive tools
            button_color = (0.6, 0.6, 0.6, 1.0)

        # Button padding
        button_padding = 6.0

        # Check if text already exists for this tool
        if tool_id in self.tool_label_text_ids:
            # Update existing text
            text_id = self.tool_label_text_ids[tool_id]
            self.text_manager.update_text(text_id, label)
            self.text_manager.update_position(text_id, (x, y))
            self.text_manager.update_color(text_id, text_color)
            self.text_manager.update_background(text_id, background_color=button_color)
        else:
            # Create new text label with button background
            text_id = self.text_manager.add_text(
                text=label,
                position=(x, y),
                color=text_color,
                scale=0.7,  # Scaled font
                layer="tool_labels",
                background_color=button_color,
                background_padding=button_padding,
            )
            self.tool_label_text_ids[tool_id] = text_id

        # Estimate button bounds based on text length
        # Rough estimate: each character is about 12 pixels wide at scale 0.7
        char_width = 12.0
        estimated_width = len(label) * char_width + (button_padding * 2)
        estimated_height = 28.0 + (button_padding * 2)

        return (x, y, estimated_width, estimated_height)

    def _render_tool_button_quad(self, x: float, y: float, color: Tuple[float, float, float, float]) -> None:
        """
        Render a single colored quad for a tool button.

        Args:
            x: X position
            y: Y position
            color: RGBA color tuple
        """
        width = self.tool_icon_size
        height = self.tool_icon_size

        vertices = np.array(
            [
                x, y, 0.0, 0.0, *color,
                x + width, y, 1.0, 0.0, *color,
                x + width, y + height, 1.0, 1.0, *color,
                x, y + height, 0.0, 1.0, *color,
            ],
            dtype="f4",
        )
        indices = np.array([0, 1, 2, 0, 2, 3], dtype="i4")

        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())

        # Create simple white texture for solid color rendering
        white_texture = self.ctx.texture((1, 1), 4, b'\xff\xff\xff\xff')

        vao = self.ctx.vertex_array(
            self.ui_shader,
            [
                (vbo, "2f 2f 4f", "in_position", "in_uv", "in_color"),
            ],
            index_buffer=ibo,
        )

        white_texture.use(location=0)
        self.ui_shader["sprite_texture"].value = 0
        vao.render(moderngl.TRIANGLES)

        vao.release()
        vbo.release()
        ibo.release()
        white_texture.release()

    def _render_category_grid_internal(self, icon_manager, category: str) -> Optional[str]:
        """
        Render grid of thumbnails for a category (called after render state is set up).

        Returns:
            Selected asset_id if one was clicked, None otherwise
        """
        assets = self.assets.get(category, [])
        if not assets:
            return None

        # Calculate grid parameters
        scroll_offset = self.scroll_offset.get(category, 0)
        grid_x = self.menu_x + self.padding
        # Grid starts below tool buttons (which are at menu_y + padding)
        grid_y = self.menu_y + self.padding + self.tool_icon_size + self.padding

        # print(f"[NativeThumbnailMenu] Rendering {len(assets)} assets in {category}")
        # print(f"[NativeThumbnailMenu] Grid position: ({grid_x}, {grid_y}), scroll: {scroll_offset}")

        # Render each visible thumbnail
        visible_index = 0
        for asset_idx, asset in enumerate(assets):
            if asset_idx < scroll_offset:
                continue

            if visible_index >= self.grid_max_visible:
                break

            # Calculate grid position
            col = visible_index % self.grid_cols
            row = visible_index // self.grid_cols

            x = grid_x + col * (self.thumbnail_size + self.padding)
            y = grid_y + row * (self.thumbnail_size + self.padding)

            # Load and render thumbnail
            icon_id = self._load_thumbnail(icon_manager, asset)
            if icon_id is not None:
                # Update position
                icon_manager.update_position(icon_id, (x, y))

                # Update color for selection highlight
                is_selected = self.selected_asset_id == asset.asset_id
                if is_selected:
                    # Brighten selected thumbnail
                    icon_manager.update_color(icon_id, (1.2, 1.2, 1.2, 1.0))
                else:
                    icon_manager.update_color(icon_id, (1.0, 1.0, 1.0, 1.0))

                # Store bounds for click detection
                self.thumbnail_bounds[icon_id] = (x, y, self.thumbnail_size, self.thumbnail_size)

            visible_index += 1

        # Render all icons in the thumbnail layer
        self._render_icons(icon_manager)

        return None

    def _load_thumbnail(self, icon_manager, asset: ThumbnailAsset) -> Optional[int]:
        """Load thumbnail texture for an asset."""
        if asset.asset_id in self.icon_ids:
            return self.icon_ids[asset.asset_id]

        try:
            if not asset.preview_path.exists():
                # print(f"[NativeThumbnailMenu] Preview path not found: {asset.preview_path}")
                return None

            # Add icon to icon manager
            icon_id = icon_manager.add_icon(
                asset.preview_path,
                position=(0.0, 0.0),  # Will be updated per frame
                size=(self.thumbnail_size, self.thumbnail_size),
                color=(1.0, 1.0, 1.0, 1.0),
                layer="thumbnails",
            )

            self.icon_ids[asset.asset_id] = icon_id
            self.loaded_textures.add(asset.asset_id)

            # print(f"[NativeThumbnailMenu] Loaded texture: {asset.name} (icon_id: {icon_id})")
            return icon_id

        except Exception as e:
            # print(f"[NativeThumbnailMenu] Failed to load thumbnail for {asset.name}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _render_icons(self, icon_manager) -> None:
        """Render all thumbnail icons."""
        if not icon_manager.has_icons():
            return

        # Get draw data for thumbnails layer
        draws = icon_manager.get_draw_data_for_layer("thumbnails")

        # Render each icon
        for draw in draws:
            self._render_icon_quad(draw)

    def _render_icon_quad(self, draw) -> None:
        """Render a single textured quad for an icon."""
        x, y = draw.position
        width, height = draw.size

        vertices = np.array(
            [
                x, y, 0.0, 0.0, *draw.color,
                x + width, y, 1.0, 0.0, *draw.color,
                x + width, y + height, 1.0, 1.0, *draw.color,
                x, y + height, 0.0, 1.0, *draw.color,
            ],
            dtype="f4",
        )
        indices = np.array([0, 1, 2, 0, 2, 3], dtype="i4")

        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())

        vao = self.ctx.vertex_array(
            self.ui_shader,
            [
                (vbo, "2f 2f 4f", "in_position", "in_uv", "in_color"),
            ],
            index_buffer=ibo,
        )

        draw.texture.use(location=0)
        self.ui_shader["sprite_texture"].value = 0
        vao.render(moderngl.TRIANGLES)

        vao.release()
        vbo.release()
        ibo.release()

    def _setup_render_state(self) -> None:
        """Setup OpenGL state for rendering."""
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.CULL_FACE)

    def _restore_render_state(self) -> None:
        """Restore OpenGL state after rendering."""
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.CULL_FACE)
        self.ctx.disable(moderngl.BLEND)

    def handle_click(self, x: float, y: float) -> bool:
        """
        Handle mouse click in menu area.

        Args:
            x: Screen X coordinate
            y: Screen Y coordinate

        Returns:
            True if click was handled, False otherwise
        """
        if not self.show:
            return False

        # Check if click is in menu bounds
        if y < self.menu_y or x < self.menu_x or x > self.menu_x + self.menu_width:
            return False

        # Check if click is on a tool button
        for tool_id, (tx, ty, tw, th) in self.tool_button_bounds.items():
            if x >= tx and x <= tx + tw and y >= ty and y <= ty + th:
                # Tool button clicked
                if self.tool_manager:
                    self.tool_manager.equip_tool(tool_id)
                    print(f"[NativeThumbnailMenu] Equipped tool: {tool_id}")
                return True

        # Check if click is on any thumbnail
        for icon_id, (tx, ty, tw, th) in self.thumbnail_bounds.items():
            if x >= tx and x <= tx + tw and y >= ty and y <= ty + th:
                # Find the asset for this icon_id
                for asset in sum(self.assets.values(), []):
                    if self.icon_ids.get(asset.asset_id) == icon_id:
                        self.selected_asset_id = asset.asset_id
                        self.selected_icon_id = icon_id
                        self._frame_selection_handled = True  # Mark selection for this frame
                        # print(f"[NativeThumbnailMenu] Selected: {asset.name}")
                        return True

        return False

    def handle_scroll(self, delta: float) -> bool:
        """
        Handle mouse wheel scroll.

        Args:
            delta: Scroll delta (positive = up, negative = down)

        Returns:
            True if scroll was handled, False otherwise
        """
        if not self.show or self.selected_category is None:
            return False

        # Check if cursor is in menu area
        # TODO: Check actual mouse position from ImGui
        # For now, just handle scroll when menu is visible

        assets = self.assets.get(self.selected_category, [])
        if not assets:
            return False

        max_offset = max(0, len(assets) - self.grid_max_visible)
        old_offset = self.scroll_offset.get(self.selected_category, 0)

        # Scroll (negative delta = scroll down = increase offset)
        new_offset = max(0, min(max_offset, old_offset - int(delta)))

        if new_offset != old_offset:
            self.scroll_offset[self.selected_category] = new_offset
            # print(f"[NativeThumbnailMenu] Scrolled to offset {new_offset}")
            return True

        return False

    def switch_category(self, category: str) -> None:
        """Switch to a different category."""
        if category in self.assets:
            self.selected_category = category
            self.selected_asset_id = None
            # print(f"[NativeThumbnailMenu] Switched to category: {category}")

    def release(self) -> None:
        """Clean up resources."""
        # Remove text labels
        if self.text_manager:
            for text_id in self.tool_label_text_ids.values():
                self.text_manager.remove_text(text_id)
            self.tool_label_text_ids.clear()

        self.icon_ids.clear()
        self.texture_cache.clear()
        self.loaded_textures.clear()
        # print("[NativeThumbnailMenu] Released")
