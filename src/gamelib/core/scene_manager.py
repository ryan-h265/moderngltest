"""Scene management utilities for loading and switching JSON-defined scenes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from pyrr import Vector3, vector

from ..config.settings import PROJECT_ROOT
from .scene import Scene
from .light import Light
from ..rendering.render_pipeline import RenderPipeline
from ..loaders.scene_loader import SceneLoader, SceneLoadResult
from ..physics import PhysicsBodyHandle, PhysicsWorld


@dataclass
class SceneMetadata:
    """Metadata for a registered scene."""

    id: str                          # Unique scene identifier
    display_name: str                # Human-readable name
    path: Path                       # Path to scene JSON
    description: str = ""            # Scene description
    thumbnail_path: Optional[Path] = None  # Path to thumbnail image


@dataclass
class ActiveScene:
    """Container representing the currently loaded scene."""

    name: str
    scene: Scene
    lights: list[Light]
    metadata: Dict[str, object]
    physics_bodies: List[PhysicsBodyHandle]


class SceneManager:
    """Manage scene registration and synchronous loading."""

    def __init__(
        self,
        ctx,
        render_pipeline: RenderPipeline,
        physics_world: Optional[PhysicsWorld] = None,
    ):
        self.ctx = ctx
        self.render_pipeline = render_pipeline
        self.physics_world = physics_world
        self._scene_loader = SceneLoader(ctx, physics_world=physics_world)
        self._registry: Dict[str, Path] = {}
        self._scene_metadata: Dict[str, SceneMetadata] = {}
        self._active: Optional[ActiveScene] = None
        self._camera_position: Optional[Vector3] = None
        self._camera_target: Optional[Vector3] = None
        self._player_spawn_position: Optional[Vector3] = None

    @property
    def scene(self) -> Optional[Scene]:
        return self._active.scene if self._active else None

    @property
    def lights(self) -> list[Light]:
        return self._active.lights if self._active else []

    @property
    def metadata(self) -> Dict[str, object]:
        return self._active.metadata if self._active else {}

    @property
    def active_name(self) -> Optional[str]:
        return self._active.name if self._active else None

    @property
    def physics_bodies(self) -> List[PhysicsBodyHandle]:
        return self._active.physics_bodies if self._active else []

    @property
    def camera_position(self) -> Optional[Vector3]:
        return self._camera_position

    @property
    def camera_target(self) -> Optional[Vector3]:
        return self._camera_target

    @property
    def player_spawn_position(self) -> Optional[Vector3]:
        return self._player_spawn_position

    def register_scene(
        self,
        name: str,
        path: Path | str,
        display_name: Optional[str] = None,
        description: str = "",
        thumbnail_path: Optional[Path | str] = None,
    ):
        """
        Register a scene.

        Args:
            name: Unique scene identifier
            path: Path to scene JSON file
            display_name: Human-readable name (defaults to name if not provided)
            description: Scene description
            thumbnail_path: Path to thumbnail image (optional)
        """
        scene_path = Path(path)
        if not scene_path.is_absolute():
            scene_path = PROJECT_ROOT / scene_path
        scene_path = scene_path.resolve()

        self._registry[name] = scene_path

        # Create metadata
        thumb_path = None
        if thumbnail_path:
            thumb_path = Path(thumbnail_path)
            if not thumb_path.is_absolute():
                thumb_path = PROJECT_ROOT / thumb_path
            thumb_path = thumb_path.resolve()

        self._scene_metadata[name] = SceneMetadata(
            id=name,
            display_name=display_name or name.replace("_", " ").title(),
            path=scene_path,
            description=description,
            thumbnail_path=thumb_path,
        )

    def unregister_scene(self, name: str):
        self._registry.pop(name, None)
        self._scene_metadata.pop(name, None)

    def get_scene_metadata(self, name: str) -> Optional[SceneMetadata]:
        """Get metadata for a registered scene."""
        return self._scene_metadata.get(name)

    def get_all_scenes(self) -> Dict[str, SceneMetadata]:
        """Get all registered scenes with their metadata."""
        return self._scene_metadata.copy()

    def load(self, name: str, camera=None) -> SceneLoadResult:
        if name not in self._registry:
            raise KeyError(f"Scene '{name}' has not been registered")

        if self.physics_world is not None:
            self.physics_world.reset()

        result = self._scene_loader.load_scene(self._registry[name])

        self._active = ActiveScene(
            name=name,
            scene=result.scene,
            lights=result.lights,
            metadata=result.metadata,
            physics_bodies=result.physics_bodies,
        )

        self._camera_position = result.camera_position
        self._camera_target = result.camera_target
        self._player_spawn_position = result.player_spawn_position

        if camera is not None:
            self._apply_camera_defaults(camera)

        self.render_pipeline.initialize_lights(result.lights, camera)

        # Set skybox on the scene if loaded
        if result.skybox is not None:
            result.scene.set_skybox(result.skybox)

        return result

    def _apply_camera_defaults(self, camera):
        if self._camera_position is not None:
            camera.position = Vector3(self._camera_position)
        if self._camera_target is not None:
            direction = vector.normalise(self._camera_target - camera.position)
            camera.pitch = float(np.degrees(np.arcsin(direction[1])))
            camera.yaw = float(np.degrees(np.arctan2(direction[2], direction[0])))
            camera.update_vectors()
            camera.target = Vector3(self._camera_target)

    def clear(self):
        self._active = None
        self._camera_position = None
        self._camera_target = None
        self._player_spawn_position = None
        if self.physics_world is not None:
            self.physics_world.reset()

