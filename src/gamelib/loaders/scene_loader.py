"""Scene loader for JSON-defined scenes."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from moderngl_window import geometry
from pyrr import Vector3

from ..config.settings import PROJECT_ROOT
from ..core import geometry_utils
from ..core.light import Light
from ..core.scene import Scene, SceneDefinition, SceneNodeDefinition
from .gltf_loader import GltfLoader


@dataclass
class SceneLoadResult:
    """Result returned from :class:`SceneLoader`."""

    scene: Scene
    lights: List[Light]
    camera_position: Optional[Vector3] = None
    camera_target: Optional[Vector3] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SceneLoader:
    """Load scenes from JSON descriptors."""

    def __init__(self, ctx):
        self.ctx = ctx
        self._gltf_loader: Optional[GltfLoader] = GltfLoader(ctx) if ctx is not None else None

    def load_scene(self, path: Path | str) -> SceneLoadResult:
        """Load a scene from disk."""

        scene_path = Path(path)
        if not scene_path.is_absolute():
            scene_path = PROJECT_ROOT / scene_path
        scene_path = scene_path.resolve()

        if not scene_path.exists():
            raise FileNotFoundError(f"Scene file not found: {scene_path}")

        with scene_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        definition = SceneDefinition.from_dict(payload)
        scene = Scene(ctx=self.ctx)

        base_path = scene_path.parent
        for node in definition.nodes:
            instance = self._instantiate_node(node, base_path)
            if instance is not None:
                scene.add_object(instance)

        lights = [definition_light.instantiate() for definition_light in definition.light_definitions]

        camera_position = Vector3(definition.camera_position) if definition.camera_position else None
        camera_target = Vector3(definition.camera_target) if definition.camera_target else None

        return SceneLoadResult(
            scene=scene,
            lights=lights,
            camera_position=camera_position,
            camera_target=camera_target,
            metadata=definition.metadata,
        )

    def _instantiate_node(self, node: SceneNodeDefinition, base_path: Path):
        node_type = node.node_type.lower()

        if node_type == "primitive":
            return self._create_primitive(node)
        if node_type == "model":
            return self._create_model(node, base_path)

        raise ValueError(f"Unsupported scene node type: {node.node_type}")

    def _create_primitive(self, node: SceneNodeDefinition):
        if node.primitive is None:
            raise ValueError(f"Primitive node '{node.name}' is missing 'primitive' field")

        primitive = node.primitive.lower()
        position = Vector3(node.position)
        color = tuple(node.color) if node.color else (1.0, 1.0, 1.0)

        geometry_obj = None
        bounding_radius = node.bounding_radius

        if primitive == "cube":
            size = tuple(node.extras.get("size", [1.0, 1.0, 1.0]))
            geometry_obj = geometry.cube(size=size)
            if bounding_radius is None:
                bounding_radius = math.sqrt(sum((s * 0.5) ** 2 for s in size))
        elif primitive == "sphere":
            radius = float(node.extras.get("radius", 1.0))
            geometry_obj = geometry.sphere(radius=radius)
            if bounding_radius is None:
                bounding_radius = radius
        elif primitive == "plane":
            size = tuple(node.extras.get("size", [1.0, 1.0]))
            geometry_obj = geometry.plane(size=size)
            if bounding_radius is None:
                bounding_radius = math.sqrt((size[0] * 0.5) ** 2 + (size[1] * 0.5) ** 2)
        elif primitive == "cone":
            radius = float(node.extras.get("radius", 1.0))
            height = float(node.extras.get("height", 2.0))
            geometry_obj = geometry_utils.cone(radius=radius, height=height)
            if bounding_radius is None:
                bounding_radius = math.sqrt(radius ** 2 + (height * 0.5) ** 2)
        elif primitive == "pyramid":
            base_size = float(node.extras.get("base_size", 1.0))
            height = float(node.extras.get("height", 1.0))
            geometry_obj = geometry_utils.pyramid(base_size=base_size, height=height)
            if bounding_radius is None:
                bounding_radius = math.sqrt(2 * (base_size * 0.5) ** 2 + (height * 0.5) ** 2)
        elif primitive == "donut_terrain":
            resolution = int(node.extras.get("resolution", 128))
            outer_radius = float(node.extras.get("outer_radius", 200.0))
            inner_radius = float(node.extras.get("inner_radius", 80.0))
            height = float(node.extras.get("height", 50.0))
            rim_width = float(node.extras.get("rim_width", 40.0))
            seed = int(node.extras.get("seed", 42))
            geometry_obj = geometry_utils.donut_terrain(
                resolution=resolution,
                outer_radius=outer_radius,
                inner_radius=inner_radius,
                height=height,
                rim_width=rim_width,
                seed=seed
            )
            if bounding_radius is None:
                # Bounding sphere needs to encompass the entire terrain mesh
                # The mesh extends to world_size/2 where world_size = outer_radius * 2.2
                # So mesh extends from -offset to +offset in both X and Z
                # Furthest corner is at diagonal distance: sqrt(offset^2 + offset^2)
                world_size = outer_radius * 2.2
                offset = world_size / 2
                diagonal_dist = math.sqrt(offset ** 2 + offset ** 2)
                bounding_radius = math.sqrt(diagonal_dist ** 2 + height ** 2)
        else:
            raise ValueError(f"Unsupported primitive type: {node.primitive}")

        from ..core.scene import SceneObject

        return SceneObject(
            geometry_obj,
            position,
            color,
            bounding_radius=bounding_radius if bounding_radius is not None else 1.0,
            name=node.name,
        )

    def _create_model(self, node: SceneNodeDefinition, base_path: Path):
        if self._gltf_loader is None:
            raise RuntimeError("GLTF loading requested without an active context")

        if not node.mesh_path:
            raise ValueError(f"Model node '{node.name}' is missing 'path'")

        model_path = Path(node.mesh_path)
        if not model_path.is_absolute():
            model_path = (PROJECT_ROOT / model_path).resolve()
        if not model_path.exists():
            # allow relative to the scene file directory
            alt_path = (base_path / node.mesh_path).resolve()
            if alt_path.exists():
                model_path = alt_path
            else:
                raise FileNotFoundError(f"Model not found for node '{node.name}': {node.mesh_path}")

        model = self._gltf_loader.load(str(model_path))
        model.name = node.name or model.name
        model.position = Vector3(node.position)
        model.rotation = Vector3(node.rotation)
        model.scale = Vector3(node.scale)

        if node.bounding_radius is not None:
            model.bounding_radius = float(node.bounding_radius)

        animations = node.extras.get("animations", [])
        played_animation = False
        if isinstance(animations, list):
            for entry in animations:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name")
                if not name:
                    continue
                loop = bool(entry.get("loop", True))
                model.play_animation(name, loop=loop)
                played_animation = True
        if not played_animation and node.extras.get("play_first_animation") and model.animations:
            first = next(iter(model.animations.keys()))
            model.play_animation(first, loop=bool(node.extras.get("animation_loop", True)))

        return model

