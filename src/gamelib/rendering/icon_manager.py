"""Icon manager for 2D HUD/UI sprites."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import moderngl
from PIL import Image


@dataclass
class _IconResource:
    """Loaded texture resource for an icon."""

    texture: moderngl.Texture
    size: Tuple[int, int]
    path: Path


@dataclass
class _IconInstance:
    """Instance of an icon placed on screen."""

    resource_key: str
    position: Tuple[float, float]
    size: Tuple[float, float]
    color: Tuple[float, float, float, float]
    layer: str


@dataclass
class IconDrawData:
    """Resolved draw information for a single icon."""

    texture: moderngl.Texture
    position: Tuple[float, float]
    size: Tuple[float, float]
    color: Tuple[float, float, float, float]


class IconManager:
    """Loads and manages HUD/UI icons as textured quads."""

    def __init__(self, ctx: moderngl.Context) -> None:
        self.ctx = ctx
        self._resources: Dict[str, _IconResource] = {}
        self._instances: Dict[int, _IconInstance] = {}
        self._next_id: int = 0

    # ------------------------------------------------------------------
    # Icon resource management
    # ------------------------------------------------------------------
    def _get_or_create_resource(self, image_path: Path) -> _IconResource:
        key = str(image_path.resolve())
        if key in self._resources:
            return self._resources[key]

        if not image_path.exists():
            raise FileNotFoundError(f"HUD icon not found: {image_path}")

        with Image.open(image_path) as image:
            rgba = image.convert("RGBA")
            size = rgba.size
            texture = self.ctx.texture(size, 4, rgba.tobytes())
        texture.repeat_x = False
        texture.repeat_y = False
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)

        resource = _IconResource(texture=texture, size=size, path=image_path)
        self._resources[key] = resource
        return resource

    # ------------------------------------------------------------------
    # Icon instance management
    # ------------------------------------------------------------------
    def add_icon(
        self,
        image_path: Path,
        position: Tuple[float, float],
        size: Optional[Tuple[float, float]] = None,
        color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
        layer: str = "default",
    ) -> int:
        resource = self._get_or_create_resource(image_path)
        icon_size = size if size is not None else resource.size

        icon_id = self._next_id
        self._next_id += 1

        self._instances[icon_id] = _IconInstance(
            resource_key=str(resource.path.resolve()),
            position=position,
            size=(float(icon_size[0]), float(icon_size[1])),
            color=color,
            layer=layer,
        )
        return icon_id

    def remove_icon(self, icon_id: int) -> None:
        self._instances.pop(icon_id, None)

    def clear_layer(self, layer: str) -> None:
        """Remove all icons from a specific layer."""
        icon_ids_to_remove = [
            icon_id for icon_id, instance in self._instances.items()
            if instance.layer == layer
        ]
        for icon_id in icon_ids_to_remove:
            self._instances.pop(icon_id, None)

    def update_position(self, icon_id: int, position: Tuple[float, float]) -> None:
        instance = self._instances.get(icon_id)
        if instance:
            instance.position = (float(position[0]), float(position[1]))

    def update_size(self, icon_id: int, size: Tuple[float, float]) -> None:
        instance = self._instances.get(icon_id)
        if instance:
            instance.size = (float(size[0]), float(size[1]))

    def update_color(self, icon_id: int, color: Tuple[float, float, float, float]) -> None:
        instance = self._instances.get(icon_id)
        if instance:
            instance.color = color

    def update_image(self, icon_id: int, image_path: Path) -> None:
        instance = self._instances.get(icon_id)
        if not instance:
            return

        resource = self._get_or_create_resource(image_path)
        instance.resource_key = str(resource.path.resolve())
        instance.size = (float(resource.size[0]), float(resource.size[1]))

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def get_all_layers(self) -> List[str]:
        layers = {instance.layer for instance in self._instances.values()}
        return sorted(layers)

    def get_draw_data_for_layer(self, layer: str) -> List[IconDrawData]:
        draw_calls: List[IconDrawData] = []
        for instance in self._instances.values():
            if instance.layer != layer:
                continue

            resource = self._resources.get(instance.resource_key)
            if resource is None:
                # Resource may have been released; skip gracefully.
                continue

            draw_calls.append(
                IconDrawData(
                    texture=resource.texture,
                    position=instance.position,
                    size=instance.size,
                    color=instance.color,
                )
            )
        return draw_calls

    def has_icons(self) -> bool:
        return bool(self._instances)

    def release(self) -> None:
        for resource in self._resources.values():
            resource.texture.release()
        self._resources.clear()
        self._instances.clear()
        self._next_id = 0
