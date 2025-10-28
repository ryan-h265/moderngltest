"""Camera rig implementations for gameplay and debug views."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import math

from pyrr import Vector3

from ..config.settings import (
    PLAYER_FIRST_PERSON_EYE_HEIGHT,
    PLAYER_THIRD_PERSON_DISTANCE,
    PLAYER_THIRD_PERSON_HEIGHT,
    PLAYER_THIRD_PERSON_SPRING_STIFFNESS,
    PLAYER_THIRD_PERSON_MIN_DISTANCE,
    PLAYER_THIRD_PERSON_MAX_DISTANCE,
)

if TYPE_CHECKING:  # pragma: no cover - import guard for type checking only
    from .camera import Camera
    from ..gameplay.player_character import PlayerCharacter
    from ..physics.physics_world import PhysicsWorld


class CameraRig(ABC):
    """Abstract base class for camera control rigs."""

    def __init__(self, camera: "Camera") -> None:
        self.camera = camera
        self.enabled = True

    def enable(self) -> None:
        """Enable the rig."""

        self.enabled = True

    def disable(self) -> None:
        """Disable the rig."""

        self.enabled = False

    @abstractmethod
    def update(self, delta_time: float) -> None:
        """Update the rig state."""

    @abstractmethod
    def apply_look_input(self, dx: float, dy: float) -> None:
        """Apply mouse look input."""


class FreeFlyRig(CameraRig):
    """Camera rig that emulates the classic free-fly debug camera."""

    def update(self, delta_time: float) -> None:  # pragma: no cover - simple forwarding
        if self.enabled:
            self.camera.update_vectors()

    def apply_look_input(self, dx: float, dy: float) -> None:
        if not self.enabled:
            return

        self.camera.yaw += dx * self.camera.sensitivity
        self.camera.pitch -= dy * self.camera.sensitivity
        self.camera.update_vectors()


class FirstPersonRig(CameraRig):
    """Camera rig that positions the camera at the player character's head."""

    def __init__(self, camera: "Camera", player: "PlayerCharacter", eye_height: float = PLAYER_FIRST_PERSON_EYE_HEIGHT) -> None:
        super().__init__(camera)
        self.player = player
        self.eye_height = eye_height

    def update(self, delta_time: float) -> None:
        if not self.enabled:
            return

        base_position = self.player.get_position()
        self.camera.position = base_position + Vector3([0.0, self.eye_height, 0.0])
        self.camera.update_vectors()

    def apply_look_input(self, dx: float, dy: float) -> None:
        if not self.enabled:
            return

        self.camera.yaw += dx * self.camera.sensitivity
        self.camera.pitch -= dy * self.camera.sensitivity
        self.camera.pitch = max(-89.0, min(89.0, self.camera.pitch))
        self.player.set_yaw(self.camera.yaw)
        self.camera.update_vectors()


class ThirdPersonRig(CameraRig):
    """Orbiting camera rig with collision avoidance for third-person view."""

    def __init__(
        self,
        camera: "Camera",
        player: "PlayerCharacter",
        physics_world: "PhysicsWorld",
        distance: float = PLAYER_THIRD_PERSON_DISTANCE,
        height: float = PLAYER_THIRD_PERSON_HEIGHT,
        spring: float = PLAYER_THIRD_PERSON_SPRING_STIFFNESS,
    ) -> None:
        super().__init__(camera)
        self.player = player
        self.physics_world = physics_world
        self.desired_distance = distance
        self.current_distance = distance
        self.desired_height = height
        self.spring = spring
        self.min_distance = PLAYER_THIRD_PERSON_MIN_DISTANCE
        self.max_distance = PLAYER_THIRD_PERSON_MAX_DISTANCE
        self.collision_margin = 0.2

    def update(self, delta_time: float) -> None:
        if not self.enabled:
            return

        base_position = self.player.get_position()
        target_position = base_position + Vector3([0.0, self.desired_height, 0.0])

        yaw_radians = math.radians(self.camera.yaw)
        forward = Vector3([
            math.cos(yaw_radians),
            0.0,
            math.sin(yaw_radians),
        ])

        desired_camera_pos = target_position - forward * self.desired_distance

        hit = None
        if self.physics_world is not None:
            hit = self.physics_world.ray_test(tuple(target_position), tuple(desired_camera_pos))

        if hit:
            safe_distance = max(self.min_distance, self.desired_distance * hit["hit_fraction"] - self.collision_margin)
            self.current_distance += (safe_distance - self.current_distance) * self.spring
        else:
            self.current_distance += (self.desired_distance - self.current_distance) * self.spring

        self.current_distance = max(self.min_distance, min(self.max_distance, self.current_distance))
        final_position = target_position - forward * self.current_distance
        self.camera.position += (final_position - self.camera.position) * self.spring
        self.camera.update_vectors()

    def apply_look_input(self, dx: float, dy: float) -> None:
        if not self.enabled:
            return

        self.camera.yaw += dx * self.camera.sensitivity
        self.camera.pitch -= dy * self.camera.sensitivity
        self.camera.pitch = max(-89.0, min(89.0, self.camera.pitch))
        self.camera.update_vectors()

    def zoom(self, delta: float) -> None:
        self.desired_distance = max(self.min_distance, min(self.max_distance, self.desired_distance + delta))


__all__ = [
    "CameraRig",
    "FreeFlyRig",
    "FirstPersonRig",
    "ThirdPersonRig",
]
