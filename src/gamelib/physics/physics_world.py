"""PyBullet integration layer for the ModernGL game engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple
from pyrr import Quaternion, Vector3

try:  # pragma: no cover - exercised indirectly when PyBullet is available
    import pybullet as _pb
except ImportError as exc:  # pragma: no cover - handled gracefully at runtime
    _pb = None
    _IMPORT_ERROR = exc
else:  # pragma: no cover - exercised indirectly when PyBullet is available
    _IMPORT_ERROR = None

try:  # pragma: no cover - optional dependency
    import pybullet_data
except ImportError:  # pragma: no cover - optional dependency
    pybullet_data = None


def _vec3(value: Iterable[float] | None) -> Optional[Tuple[float, float, float]]:
    """Convert an iterable to a tuple of three floats."""

    if value is None:
        return None
    data = tuple(float(v) for v in value)
    if len(data) != 3:
        raise ValueError(f"Expected 3 components, got {data}")
    return data


def _quat(value: Iterable[float] | None) -> Optional[Tuple[float, float, float, float]]:
    """Convert an iterable to a quaternion tuple in (x, y, z, w) order."""

    if value is None:
        return None
    data = tuple(float(v) for v in value)
    if len(data) == 4:
        return data
    if len(data) == 3:
        quat = Quaternion.from_eulers(data)
        return tuple(float(v) for v in quat)
    raise ValueError(f"Expected 3 or 4 components for quaternion, got {data}")


@dataclass(slots=True)
class PhysicsWorldSettings:
    """Settings that control global physics simulation behaviour."""

    gravity: Tuple[float, float, float] = (0.0, -9.81, 0.0)
    fixed_time_step: float = 1.0 / 240.0
    max_substeps: int = 4
    enable_sleeping: bool = True
    additional_search_paths: Tuple[str, ...] = ()


@dataclass(slots=True)
class PhysicsBodyConfig:
    """Configuration describing how to construct a rigid body."""

    shape: Optional[str] = None
    body_type: str = "dynamic"
    mass: Optional[float] = None
    half_extents: Optional[Tuple[float, float, float]] = None
    radius: Optional[float] = None
    height: Optional[float] = None
    plane_normal: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    plane_constant: float = 0.0
    mesh_path: Optional[str] = None
    mesh_scale: Optional[Tuple[float, float, float]] = None
    restitution: float = 0.0
    friction: float = 0.5
    rolling_friction: float = 0.0
    spinning_friction: float = 0.0
    linear_damping: float = 0.0
    angular_damping: float = 0.0
    margin: float = 0.04
    linear_velocity: Optional[Tuple[float, float, float]] = None
    angular_velocity: Optional[Tuple[float, float, float]] = None
    collision_group: Optional[int] = None
    collision_mask: Optional[int] = None
    contact_stiffness: Optional[float] = None
    contact_damping: Optional[float] = None
    enable_sleeping: Optional[bool] = None
    orientation: Optional[Tuple[float, float, float, float]] = None
    position: Optional[Tuple[float, float, float]] = None
    user_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "PhysicsBodyConfig":
        """Create a configuration object from a JSON-compatible dictionary."""

        data = dict(payload)
        config = cls()
        config.shape = data.get("shape")
        config.body_type = str(data.get("type", data.get("body_type", config.body_type))).lower()
        if config.body_type not in {"static", "dynamic", "kinematic"}:
            raise ValueError(f"Unsupported physics body type: {config.body_type}")
        config.mass = float(data["mass"]) if "mass" in data else None
        if "half_extents" in data:
            config.half_extents = _vec3(data["half_extents"])
        if "radius" in data:
            config.radius = float(data["radius"])
        if "height" in data:
            config.height = float(data["height"])
        if "plane_normal" in data:
            config.plane_normal = _vec3(data["plane_normal"]) or config.plane_normal
        if "plane_constant" in data:
            config.plane_constant = float(data["plane_constant"])
        if "mesh_path" in data:
            config.mesh_path = str(data["mesh_path"])
        if "mesh_scale" in data:
            config.mesh_scale = _vec3(data["mesh_scale"])
        if "restitution" in data:
            config.restitution = float(data["restitution"])
        if "friction" in data:
            config.friction = float(data["friction"])
        if "rolling_friction" in data:
            config.rolling_friction = float(data["rolling_friction"])
        if "spinning_friction" in data:
            config.spinning_friction = float(data["spinning_friction"])
        if "linear_damping" in data:
            config.linear_damping = float(data["linear_damping"])
        if "angular_damping" in data:
            config.angular_damping = float(data["angular_damping"])
        if "margin" in data:
            config.margin = float(data["margin"])
        if "linear_velocity" in data:
            config.linear_velocity = _vec3(data["linear_velocity"])
        if "angular_velocity" in data:
            config.angular_velocity = _vec3(data["angular_velocity"])
        if "collision_group" in data:
            config.collision_group = int(data["collision_group"])
        if "collision_mask" in data:
            config.collision_mask = int(data["collision_mask"])
        if "contact_stiffness" in data:
            config.contact_stiffness = float(data["contact_stiffness"])
        if "contact_damping" in data:
            config.contact_damping = float(data["contact_damping"])
        if "enable_sleeping" in data:
            config.enable_sleeping = bool(data["enable_sleeping"])
        if "orientation" in data:
            config.orientation = _quat(data["orientation"])
        if "rotation" in data and config.orientation is None:
            config.orientation = _quat(data["rotation"])
        if "position" in data:
            config.position = _vec3(data["position"])
        if "user_data" in data:
            if not isinstance(data["user_data"], dict):
                raise TypeError("physics.user_data must be a dictionary")
            config.user_data = dict(data["user_data"])
        return config

    @property
    def is_dynamic(self) -> bool:
        return self.body_type == "dynamic"

    @property
    def is_static(self) -> bool:
        return self.body_type == "static"

    @property
    def is_kinematic(self) -> bool:
        return self.body_type == "kinematic"

    def resolved_mass(self) -> float:
        """Return the effective mass for the rigid body."""

        if self.is_dynamic:
            return float(self.mass if self.mass is not None else 1.0)
        return 0.0


@dataclass(slots=True)
class PhysicsBodyHandle:
    """Handle returned when a rigid body is created."""

    body_id: int
    scene_object: Any
    config: PhysicsBodyConfig


class PhysicsWorld:
    """Manage a PyBullet physics world and synchronize it with scene objects."""

    def __init__(self, settings: Optional[PhysicsWorldSettings] = None) -> None:
        if _pb is None:  # pragma: no cover - requires PyBullet in test environment
            raise RuntimeError(
                "PyBullet is not available. Install the 'pybullet' package to enable physics."
            ) from _IMPORT_ERROR

        self.settings = settings or PhysicsWorldSettings()
        self._client = _pb.connect(_pb.DIRECT)
        self._bodies: Dict[int, PhysicsBodyHandle] = {}
        self._accumulator = 0.0
        self._configure_world()

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------
    def _configure_world(self) -> None:
        """Apply global settings (gravity, time step, search paths)."""

        _pb.setGravity(*self.settings.gravity, physicsClientId=self._client)
        _pb.setTimeStep(self.settings.fixed_time_step, physicsClientId=self._client)

        if pybullet_data is not None:
            _pb.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self._client)
        for path in self.settings.additional_search_paths:
            _pb.setAdditionalSearchPath(str(path), physicsClientId=self._client)

    def shutdown(self) -> None:
        """Disconnect the physics client."""

        if self._client is not None:
            _pb.disconnect(self._client)
            self._client = None

    def reset(self) -> None:
        """Clear the world of all bodies."""

        if self._client is None:
            return
        self._bodies.clear()
        _pb.resetSimulation(physicsClientId=self._client)
        self._configure_world()
        self._accumulator = 0.0

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    def set_gravity(self, gravity: Tuple[float, float, float]) -> None:
        self.settings.gravity = tuple(float(v) for v in gravity)
        _pb.setGravity(*self.settings.gravity, physicsClientId=self._client)

    def set_time_step(self, fixed_time_step: float, max_substeps: Optional[int] = None) -> None:
        self.settings.fixed_time_step = float(fixed_time_step)
        if max_substeps is not None:
            self.settings.max_substeps = int(max_substeps)
        _pb.setTimeStep(self.settings.fixed_time_step, physicsClientId=self._client)

    def configure_from_metadata(self, metadata: Dict[str, Any]) -> None:
        """Apply optional settings provided in scene metadata."""

        if not metadata:
            return
        gravity = metadata.get("gravity")
        if gravity is not None:
            self.set_gravity(tuple(float(v) for v in gravity))
        time_step = metadata.get("fixed_time_step")
        if time_step is not None:
            max_substeps = metadata.get("max_substeps")
            self.set_time_step(float(time_step), max_substeps=max_substeps)
        if "enable_sleeping" in metadata:
            self.settings.enable_sleeping = bool(metadata["enable_sleeping"])

    # ------------------------------------------------------------------
    # Body creation helpers
    # ------------------------------------------------------------------
    def _populate_config_defaults(
        self,
        config: PhysicsBodyConfig,
        scene_object: Any,
        node_definition: Any,
        resource_base: Optional[Path],
    ) -> None:
        """Fill in missing collider information based on the scene definition."""

        primitive = getattr(node_definition, "primitive", None)

        if config.shape is None and primitive is not None:
            primitive = primitive.lower()
            if primitive in {"cube", "box"}:
                config.shape = "box"
            elif primitive == "sphere":
                config.shape = "sphere"
            elif primitive == "plane":
                config.shape = "plane"
            elif primitive == "cylinder":
                config.shape = "cylinder"
            elif primitive == "cone":
                config.shape = "cone"
        if config.shape is None:
            config.shape = "box"

        if config.shape == "box" and config.half_extents is None and primitive is not None:
            size = node_definition.extras.get("size") if hasattr(node_definition, "extras") else None
            if size is not None:
                config.half_extents = tuple(float(v) * 0.5 for v in size)
        if config.shape == "sphere" and config.radius is None and primitive is not None:
            radius = node_definition.extras.get("radius") if hasattr(node_definition, "extras") else None
            if radius is not None:
                config.radius = float(radius)
        if config.shape in {"cylinder", "cone"}:
            if config.radius is None and hasattr(node_definition, "extras"):
                radius = node_definition.extras.get("radius")
                if radius is not None:
                    config.radius = float(radius)
            if config.height is None and hasattr(node_definition, "extras"):
                height = node_definition.extras.get("height")
                if height is not None:
                    config.height = float(height)

        if config.mesh_path and resource_base is not None:
            mesh_path = Path(config.mesh_path)
            if not mesh_path.is_absolute():
                config.mesh_path = str((resource_base / mesh_path).resolve())

        if config.mesh_scale is None and hasattr(scene_object, "scale"):
            scale = getattr(scene_object, "scale")
            if isinstance(scale, Vector3):
                config.mesh_scale = (float(scale.x), float(scale.y), float(scale.z))

    def _extract_scene_transform(self, scene_object: Any, config: PhysicsBodyConfig) -> Tuple[Tuple[float, float, float], Tuple[float, float, float, float]]:
        """Return the position and orientation of the scene object."""

        position = getattr(scene_object, "position", Vector3([0.0, 0.0, 0.0]))
        if isinstance(position, Vector3):
            base_position = (float(position.x), float(position.y), float(position.z))
        else:
            base_position = _vec3(position) or (0.0, 0.0, 0.0)

        orientation = None
        if hasattr(scene_object, "rotation"):
            rotation = getattr(scene_object, "rotation")
            if isinstance(rotation, Quaternion):
                orientation = tuple(float(v) for v in rotation.normalised)
        if orientation is None and hasattr(scene_object, "orientation"):
            orientation_attr = getattr(scene_object, "orientation")
            if isinstance(orientation_attr, Quaternion):
                orientation = tuple(float(v) for v in orientation_attr.normalised)
        if orientation is None:
            orientation = (0.0, 0.0, 0.0, 1.0)

        if config.position is not None:
            base_position = config.position
        if config.orientation is not None:
            orientation = config.orientation

        return base_position, orientation

    def _create_collision_shape(self, config: PhysicsBodyConfig) -> int:
        """Create a PyBullet collision shape based on the provided config."""

        shape = (config.shape or "box").lower()
        kwargs = {"physicsClientId": self._client}

        if shape == "box":
            if config.half_extents is None:
                raise ValueError("Box collider requires 'half_extents'")
            return _pb.createCollisionShape(_pb.GEOM_BOX, halfExtents=config.half_extents, **kwargs)
        if shape == "sphere":
            if config.radius is None:
                raise ValueError("Sphere collider requires 'radius'")
            return _pb.createCollisionShape(_pb.GEOM_SPHERE, radius=config.radius, **kwargs)
        if shape == "capsule":
            if config.radius is None or config.height is None:
                raise ValueError("Capsule collider requires 'radius' and 'height'")
            return _pb.createCollisionShape(_pb.GEOM_CAPSULE, radius=config.radius, height=config.height, **kwargs)
        if shape == "cylinder":
            if config.radius is None or config.height is None:
                raise ValueError("Cylinder collider requires 'radius' and 'height'")
            return _pb.createCollisionShape(_pb.GEOM_CYLINDER, radius=config.radius, height=config.height, **kwargs)
        if shape == "cone":
            if config.radius is None or config.height is None:
                raise ValueError("Cone collider requires 'radius' and 'height'")
            return _pb.createCollisionShape(_pb.GEOM_CONE, radius=config.radius, height=config.height, **kwargs)
        if shape == "plane":
            return _pb.createCollisionShape(
                _pb.GEOM_PLANE,
                planeNormal=config.plane_normal,
                planeConstant=config.plane_constant,
                physicsClientId=self._client,
            )
        if shape == "mesh":
            if not config.mesh_path:
                raise ValueError("Mesh collider requires 'mesh_path'")
            mesh_scale = config.mesh_scale or (1.0, 1.0, 1.0)
            mesh_kwargs = dict(kwargs)
            if config.margin is not None:
                mesh_kwargs["collisionMargin"] = config.margin
            return _pb.createCollisionShape(
                _pb.GEOM_MESH,
                fileName=str(config.mesh_path),
                meshScale=mesh_scale,
                **mesh_kwargs,
            )
        if shape == "heightfield":
            raise NotImplementedError("Heightfield colliders are not yet supported")
        raise ValueError(f"Unsupported collider shape: {config.shape}")

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def _pre_step(self) -> None:
        """Synchronise kinematic bodies before stepping the world."""

        for handle in self._bodies.values():
            if handle.config.is_kinematic:
                position, orientation = self._extract_scene_transform(handle.scene_object, handle.config)
                _pb.resetBasePositionAndOrientation(
                    handle.body_id,
                    position,
                    orientation,
                    physicsClientId=self._client,
                )

    def step_simulation(self, delta_time: float) -> None:
        """Advance the simulation and push transforms back to the scene."""

        if self._client is None:
            return

        self._accumulator += delta_time
        substeps = 0
        while self._accumulator >= self.settings.fixed_time_step and substeps < self.settings.max_substeps:
            self._pre_step()
            _pb.stepSimulation(physicsClientId=self._client)
            self._accumulator -= self.settings.fixed_time_step
            substeps += 1

        self.sync_to_scene()

    def sync_to_scene(self) -> None:
        """Write simulated transforms back to associated scene objects."""

        for handle in self._bodies.values():
            if handle.config.is_kinematic:
                continue
            position, orientation = _pb.getBasePositionAndOrientation(
                handle.body_id,
                physicsClientId=self._client,
            )
            if hasattr(handle.scene_object, "apply_physics_transform"):
                handle.scene_object.apply_physics_transform(position, orientation)
            else:
                # Fallback for objects without helper method
                if hasattr(handle.scene_object, "position"):
                    handle.scene_object.position = Vector3(position)
                if hasattr(handle.scene_object, "rotation"):
                    handle.scene_object.rotation = Quaternion(orientation)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def create_body(
        self,
        scene_object: Any,
        config: PhysicsBodyConfig,
        node_definition: Any = None,
        resource_base: Optional[Path] = None,
    ) -> PhysicsBodyHandle:
        """Create a rigid body and attach it to a scene object."""

        self._populate_config_defaults(config, scene_object, node_definition, resource_base)

        if config.enable_sleeping is None:
            config.enable_sleeping = self.settings.enable_sleeping

        position, orientation = self._extract_scene_transform(scene_object, config)
        collision_shape = self._create_collision_shape(config)
        body_id = _pb.createMultiBody(
            baseMass=config.resolved_mass(),
            baseCollisionShapeIndex=collision_shape,
            baseVisualShapeIndex=-1,
            basePosition=position,
            baseOrientation=orientation,
            physicsClientId=self._client,
        )

        _pb.changeDynamics(
            body_id,
            -1,
            lateralFriction=config.friction,
            rollingFriction=config.rolling_friction,
            spinningFriction=config.spinning_friction,
            restitution=config.restitution,
            linearDamping=config.linear_damping,
            angularDamping=config.angular_damping,
            contactStiffness=config.contact_stiffness if config.contact_stiffness is not None else 0.0,
            contactDamping=config.contact_damping if config.contact_damping is not None else 0.0,
            physicsClientId=self._client,
        )

        if config.enable_sleeping is not None and not config.enable_sleeping:
            if hasattr(_pb, "ACTIVATION_STATE_DISABLE_SLEEPING"):
                _pb.changeDynamics(
                    body_id,
                    -1,
                    activationState=_pb.ACTIVATION_STATE_DISABLE_SLEEPING,
                    physicsClientId=self._client,
                )

        if config.collision_group is not None or config.collision_mask is not None:
            group = config.collision_group if config.collision_group is not None else 1
            mask = config.collision_mask if config.collision_mask is not None else -1
            _pb.setCollisionFilterGroupMask(
                body_id,
                -1,
                int(group),
                int(mask),
                physicsClientId=self._client,
            )

        if config.linear_velocity is not None or config.angular_velocity is not None:
            _pb.resetBaseVelocity(
                body_id,
                linearVelocity=config.linear_velocity or (0.0, 0.0, 0.0),
                angularVelocity=config.angular_velocity or (0.0, 0.0, 0.0),
                physicsClientId=self._client,
            )

        handle = PhysicsBodyHandle(body_id=body_id, scene_object=scene_object, config=config)
        self._bodies[body_id] = handle

        if hasattr(scene_object, "apply_physics_transform"):
            scene_object.apply_physics_transform(position, orientation)

        return handle

    def remove_body(self, body_id: int) -> None:
        """Remove a body from the simulation."""

        if body_id in self._bodies:
            _pb.removeBody(body_id, physicsClientId=self._client)
            self._bodies.pop(body_id, None)

    def get_body(self, body_id: int) -> Optional[PhysicsBodyHandle]:
        return self._bodies.get(body_id)

