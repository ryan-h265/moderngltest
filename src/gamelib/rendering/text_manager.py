"""
Text Manager

Manages text objects and converts them to renderable geometry.
Supports multiple layers, dynamic updates, and flexible positioning.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from .font_loader import FontLoader, GlyphMetrics


class TextObject:
    """Represents a single text object with position, color, and styling."""

    def __init__(self, text: str, position: Tuple[float, float],
                 color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
                 scale: float = 1.0, layer: str = "default"):
        """
        Initialize text object.

        Args:
            text: Text string to display
            position: Screen position (x, y) in pixels
            color: RGBA color (0.0-1.0)
            scale: Scale multiplier
            layer: Layer name for rendering order
        """
        self.text = text
        self.position = position
        self.color = color
        self.scale = scale
        self.layer = layer
        self.dirty = True  # Needs geometry update


class TextManager:
    """
    Manages text objects and generates renderable geometry.

    Responsibilities:
    - Store text objects by ID
    - Convert text strings to quad geometry
    - Organize text by layers
    - Generate vertex/UV/color data for renderer
    """

    def __init__(self, font_loader: FontLoader):
        """
        Initialize text manager.

        Args:
            font_loader: FontLoader instance with loaded font atlas
        """
        self.font_loader = font_loader

        # Text objects by ID
        self._text_objects: Dict[int, TextObject] = {}
        self._next_id = 0

        # Geometry cache by layer
        self._geometry_cache: Dict[str, Dict] = {}
        self._dirty_layers: set = set()

    def add_text(self, text: str, position: Tuple[float, float],
                 color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
                 scale: float = 1.0, layer: str = "default") -> int:
        """
        Add a new text object.

        Args:
            text: Text string to display
            position: Screen position (x, y) in pixels
            color: RGBA color (0.0-1.0)
            scale: Scale multiplier
            layer: Layer name

        Returns:
            Text object ID for later updates/removal
        """
        text_id = self._next_id
        self._next_id += 1

        text_obj = TextObject(text, position, color, scale, layer)
        self._text_objects[text_id] = text_obj
        self._dirty_layers.add(layer)

        return text_id

    def update_text(self, text_id: int, text: str):
        """
        Update text content.

        Args:
            text_id: Text object ID
            text: New text string
        """
        if text_id in self._text_objects:
            obj = self._text_objects[text_id]
            obj.text = text
            obj.dirty = True
            self._dirty_layers.add(obj.layer)

    def update_position(self, text_id: int, position: Tuple[float, float]):
        """
        Update text position.

        Args:
            text_id: Text object ID
            position: New screen position (x, y) in pixels
        """
        if text_id in self._text_objects:
            obj = self._text_objects[text_id]
            obj.position = position
            obj.dirty = True
            self._dirty_layers.add(obj.layer)

    def update_color(self, text_id: int, color: Tuple[float, float, float, float]):
        """
        Update text color.

        Args:
            text_id: Text object ID
            color: New RGBA color (0.0-1.0)
        """
        if text_id in self._text_objects:
            obj = self._text_objects[text_id]
            obj.color = color
            obj.dirty = True
            self._dirty_layers.add(obj.layer)

    def remove_text(self, text_id: int):
        """
        Remove a text object.

        Args:
            text_id: Text object ID to remove
        """
        if text_id in self._text_objects:
            obj = self._text_objects.pop(text_id)
            self._dirty_layers.add(obj.layer)

    def clear_layer(self, layer: str):
        """
        Remove all text objects from a layer.

        Args:
            layer: Layer name to clear
        """
        to_remove = [tid for tid, obj in self._text_objects.items() if obj.layer == layer]
        for tid in to_remove:
            del self._text_objects[tid]
        self._dirty_layers.add(layer)

    def get_layer_geometry(self, layer: str) -> Optional[Dict]:
        """
        Get renderable geometry for a layer.

        Returns geometry dictionary with:
        - vertices: np.array of vertex positions
        - uvs: np.array of texture coordinates
        - colors: np.array of vertex colors
        - indices: np.array of triangle indices
        - vertex_count: Number of vertices

        Args:
            layer: Layer name

        Returns:
            Geometry dict or None if layer is empty
        """
        # Rebuild geometry if layer is dirty
        if layer in self._dirty_layers:
            self._rebuild_layer_geometry(layer)
            self._dirty_layers.discard(layer)

        return self._geometry_cache.get(layer)

    def get_all_layers(self) -> List[str]:
        """
        Get all active layer names.

        Returns:
            List of layer names
        """
        layers = set(obj.layer for obj in self._text_objects.values())
        return sorted(layers)  # Consistent ordering

    def _rebuild_layer_geometry(self, layer: str):
        """
        Rebuild geometry for a specific layer.

        Args:
            layer: Layer name to rebuild
        """
        # Get all text objects in this layer
        layer_objects = [obj for obj in self._text_objects.values() if obj.layer == layer]

        if not layer_objects:
            # Remove empty layer from cache
            if layer in self._geometry_cache:
                del self._geometry_cache[layer]
            return

        # Build geometry for all text in layer
        vertices = []
        uvs = []
        colors = []
        indices = []
        vertex_offset = 0

        for text_obj in layer_objects:
            text_verts, text_uvs, text_colors, text_indices = self._generate_text_geometry(text_obj)

            # Offset indices for this text object
            offset_indices = [idx + vertex_offset for idx in text_indices]

            vertices.extend(text_verts)
            uvs.extend(text_uvs)
            colors.extend(text_colors)
            indices.extend(offset_indices)

            # Each vertex has 2 components (x, y), so divide by 2
            vertex_offset += len(text_verts) // 2

        # Convert to numpy arrays
        vertices_array = np.array(vertices, dtype='f4')
        uvs_array = np.array(uvs, dtype='f4')
        colors_array = np.array(colors, dtype='f4')
        indices_array = np.array(indices, dtype='i4')

        # Store in cache
        self._geometry_cache[layer] = {
            'vertices': vertices_array,
            'uvs': uvs_array,
            'colors': colors_array,
            'indices': indices_array,
            'vertex_count': len(vertices),
            'index_count': len(indices)
        }

    def _generate_text_geometry(self, text_obj: TextObject) -> Tuple[List, List, List, List]:
        """
        Generate geometry for a single text object.

        Args:
            text_obj: Text object to generate geometry for

        Returns:
            Tuple of (vertices, uvs, colors, indices)
        """
        vertices = []
        uvs = []
        colors = []
        indices = []

        x, y = text_obj.position
        scale = text_obj.scale

        # Current cursor position
        cursor_x = x
        cursor_y = y

        vertex_index = 0

        for char in text_obj.text:
            # Handle newlines
            if char == '\n':
                cursor_x = x
                cursor_y += self.font_loader.get_line_height() * scale
                continue

            # Get glyph metrics
            glyph = self.font_loader.get_glyph(char)
            if not glyph:
                continue  # Skip characters not in atlas

            # Calculate quad vertices (screen space)
            x0 = cursor_x + glyph.bearing_x * scale
            y0 = cursor_y + glyph.bearing_y * scale
            x1 = x0 + glyph.width * scale
            y1 = y0 + glyph.height * scale

            # Quad vertices (bottom-left, bottom-right, top-left, top-right)
            vertices.extend([
                x0, y0,  # Bottom-left
                x1, y0,  # Bottom-right
                x0, y1,  # Top-left
                x1, y1   # Top-right
            ])

            # UV coordinates
            uv_min_u, uv_min_v = glyph.uv_min
            uv_max_u, uv_max_v = glyph.uv_max

            uvs.extend([
                uv_min_u, uv_max_v,  # Bottom-left
                uv_max_u, uv_max_v,  # Bottom-right
                uv_min_u, uv_min_v,  # Top-left
                uv_max_u, uv_min_v   # Top-right
            ])

            # Colors (RGBA per vertex)
            for _ in range(4):
                colors.extend(text_obj.color)

            # Indices for two triangles (CCW winding)
            base = vertex_index
            indices.extend([
                base + 0, base + 1, base + 2,  # Triangle 1
                base + 1, base + 3, base + 2   # Triangle 2
            ])

            vertex_index += 4

            # Advance cursor
            cursor_x += glyph.advance * scale

        return vertices, uvs, colors, indices
