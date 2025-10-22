"""Text manager that converts raster glyphs into geometry strips."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


@dataclass
class _TextObject:
    text: str
    position: Tuple[float, float]
    color: Tuple[float, float, float, float]
    scale: float
    layer: str
    background_color: Optional[Tuple[float, float, float, float]] = None
    background_padding: float = 0.0


@dataclass
class _CachedGeometry:
    vertices: np.ndarray  # shape (N*2,), float32
    indices: np.ndarray   # shape (M,), int32
    vertex_float_count: int
    index_count: int


@dataclass
class _LayerGeometry:
    vertices: np.ndarray  # shape (N*2,), float32
    colors: np.ndarray    # shape (N*4,), float32
    indices: np.ndarray   # shape (M,), int32
    vertex_count: int     # number of vertices (not floats)
    index_count: int


class TextManager:
    """Manages text objects and generates geometry from alpha masks."""

    def __init__(
        self,
        font_path: str,
        font_size: int,
        line_spacing: Optional[int] = None,
    ) -> None:
        self.font_path = Path(font_path)
        self.font_size = font_size
        self.font = ImageFont.truetype(str(self.font_path), font_size)

        ascent, descent = self.font.getmetrics()
        self._line_height = ascent + descent
        self._line_spacing = line_spacing if line_spacing is not None else int(self._line_height * 1.1)

        self._text_objects: Dict[int, _TextObject] = {}
        self._next_id = 0

        self._geometry_cache: Dict[str, _CachedGeometry] = {}
        self._layer_geometry: Dict[str, _LayerGeometry] = {}
        self._dirty_layers: set[str] = set()

    def add_text(
        self,
        text: str,
        position: Tuple[float, float],
        color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
        scale: float = 1.0,
        layer: str = "default",
        background_color: Optional[Tuple[float, float, float, float]] = None,
        background_padding: float = 0.0,
    ) -> int:
        text_id = self._next_id
        self._next_id += 1

        self._text_objects[text_id] = _TextObject(
            text=text,
            position=position,
            color=color,
            scale=scale,
            layer=layer,
            background_color=background_color,
            background_padding=background_padding,
        )

        self._dirty_layers.add(layer)
        return text_id

    def update_text(self, text_id: int, text: str) -> None:
        obj = self._text_objects.get(text_id)
        if not obj or obj.text == text:
            return

        obj.text = text
        self._dirty_layers.add(obj.layer)

    def update_position(self, text_id: int, position: Tuple[float, float]) -> None:
        obj = self._text_objects.get(text_id)
        if obj:
            obj.position = position
            self._dirty_layers.add(obj.layer)

    def update_color(self, text_id: int, color: Tuple[float, float, float, float]) -> None:
        obj = self._text_objects.get(text_id)
        if obj:
            obj.color = color
            self._dirty_layers.add(obj.layer)

    def update_background(
        self,
        text_id: int,
        background_color: Optional[Tuple[float, float, float, float]] = None,
        background_padding: Optional[float] = None,
    ) -> None:
        obj = self._text_objects.get(text_id)
        if obj:
            obj.background_color = background_color
            if background_padding is not None:
                obj.background_padding = background_padding
            self._dirty_layers.add(obj.layer)

    def update_scale(self, text_id: int, scale: float) -> None:
        obj = self._text_objects.get(text_id)
        if obj:
            obj.scale = scale
            self._dirty_layers.add(obj.layer)

    def remove_text(self, text_id: int) -> None:
        obj = self._text_objects.pop(text_id, None)
        if obj:
            self._dirty_layers.add(obj.layer)

    def clear_layer(self, layer: str) -> None:
        to_remove = [tid for tid, obj in self._text_objects.items() if obj.layer == layer]
        for text_id in to_remove:
            del self._text_objects[text_id]
        self._layer_geometry.pop(layer, None)
        self._dirty_layers.discard(layer)

    def get_all_layers(self) -> List[str]:
        layers = {obj.layer for obj in self._text_objects.values()}
        return sorted(layers)

    def get_layer_geometry(self, layer: str) -> Optional[Dict[str, np.ndarray]]:
        if layer in self._dirty_layers:
            self._rebuild_layer_geometry(layer)
            self._dirty_layers.discard(layer)

        geometry = self._layer_geometry.get(layer)
        if geometry is None:
            return None

        return {
            'vertices': geometry.vertices,
            'colors': geometry.colors,
            'indices': geometry.indices,
            'vertex_count': geometry.vertex_count,
            'index_count': geometry.index_count,
        }

    def get_line_height(self) -> int:
        return self._line_height

    def release(self) -> None:
        self._geometry_cache.clear()
        self._layer_geometry.clear()
        self._dirty_layers.clear()

    def _rebuild_layer_geometry(self, layer: str) -> None:
        objects = [obj for obj in self._text_objects.values() if obj.layer == layer]
        if not objects:
            self._layer_geometry.pop(layer, None)
            return

        vertices: List[float] = []
        colors: List[float] = []
        indices: List[int] = []
        vertex_offset = 0

        for obj in objects:
            geom = self._get_text_geometry(obj.text)
            if geom.vertex_float_count == 0:
                continue

            base_vertices = geom.vertices.reshape(-1, 2)

            # Optional background quad (add before text to ensure it renders behind)
            if obj.background_color and obj.background_color[3] > 0.0:
                min_x = float(base_vertices[:, 0].min()) * obj.scale + obj.position[0]
                max_x = float(base_vertices[:, 0].max()) * obj.scale + obj.position[0]
                min_y = float(base_vertices[:, 1].min()) * obj.scale + obj.position[1]
                max_y = float(base_vertices[:, 1].max()) * obj.scale + obj.position[1]

                padding = obj.background_padding
                min_x -= padding
                max_x += padding
                min_y -= padding
                max_y += padding

                background_vertices = [
                    min_x, min_y,
                    max_x, min_y,
                    min_x, max_y,
                    max_x, max_y,
                ]
                vertices.extend(background_vertices)
                colors.extend(np.tile(obj.background_color, 4))

                indices.extend([
                    vertex_offset + 0,
                    vertex_offset + 1,
                    vertex_offset + 2,
                    vertex_offset + 1,
                    vertex_offset + 3,
                    vertex_offset + 2,
                ])
                vertex_offset += 4

            transformed_vertices = geom.vertices.copy()
            transformed_vertices[0::2] *= obj.scale
            transformed_vertices[1::2] *= obj.scale
            transformed_vertices[0::2] += obj.position[0]
            transformed_vertices[1::2] += obj.position[1]

            vertices.extend(transformed_vertices.tolist())

            vertex_total = geom.vertex_float_count // 2
            colors.extend(np.tile(obj.color, vertex_total))

            offset_indices = geom.indices + vertex_offset
            indices.extend(offset_indices.tolist())

            vertex_offset += vertex_total

        if not vertices:
            self._layer_geometry.pop(layer, None)
            return

        vertex_array = np.array(vertices, dtype='f4')
        color_array = np.array(colors, dtype='f4')
        index_array = np.array(indices, dtype='i4')

        self._layer_geometry[layer] = _LayerGeometry(
            vertices=vertex_array,
            colors=color_array,
            indices=index_array,
            vertex_count=len(vertex_array) // 2,
            index_count=len(index_array),
        )

    def _get_text_geometry(self, text: str) -> _CachedGeometry:
        key = text
        cached = self._geometry_cache.get(key)
        if cached:
            return cached

        geometry = self._rasterize_text(text)
        self._geometry_cache[key] = geometry
        return geometry

    def _rasterize_text(self, text: str) -> _CachedGeometry:
        if not text:
            return _CachedGeometry(
                vertices=np.array([], dtype='f4'),
                indices=np.array([], dtype='i4'),
                vertex_float_count=0,
                index_count=0,
            )

        dummy = Image.new('L', (1, 1), 0)
        draw = ImageDraw.Draw(dummy)
        bbox = draw.multiline_textbbox((0, 0), text, font=self.font, spacing=self._line_spacing)

        width = max(1, bbox[2] - bbox[0])
        height = max(1, bbox[3] - bbox[1])

        offset_x = -bbox[0]
        offset_y = -bbox[1]

        image = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(image)
        draw.multiline_text((offset_x, offset_y), text, font=self.font, fill=255, spacing=self._line_spacing)

        alpha = np.array(image, dtype=np.uint8)

        vertices: List[float] = []
        indices: List[int] = []
        vertex_index = 0

        for y in range(height):
            row = alpha[y]
            x = 0
            while x < width:
                if row[x] == 0:
                    x += 1
                    continue

                start = x
                while x < width and row[x] != 0:
                    x += 1
                end = x

                x0 = float(start)
                x1 = float(end)
                y0 = float(y)
                y1 = float(y + 1)

                vertices.extend([
                    x0, y0,
                    x1, y0,
                    x0, y1,
                    x1, y1,
                ])

                indices.extend([
                    vertex_index + 0,
                    vertex_index + 1,
                    vertex_index + 2,
                    vertex_index + 1,
                    vertex_index + 3,
                    vertex_index + 2,
                ])

                vertex_index += 4

        if vertex_index == 0:
            return _CachedGeometry(
                vertices=np.array([], dtype='f4'),
                indices=np.array([], dtype='i4'),
                vertex_float_count=0,
                index_count=0,
            )

        vertices_array = np.array(vertices, dtype='f4')
        vertices_array[0::2] -= offset_x
        vertices_array[1::2] -= offset_y

        return _CachedGeometry(
            vertices=vertices_array,
            indices=np.array(indices, dtype='i4'),
            vertex_float_count=len(vertices_array),
            index_count=len(indices),
        )
