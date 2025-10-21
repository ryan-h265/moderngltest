"""
Camera Module

First-person camera with WASD movement and mouse look controls.
"""

import numpy as np
from pyrr import Matrix44, Vector3, vector

from ..config.settings import (
    DEFAULT_CAMERA_SPEED,
    MOUSE_SENSITIVITY,
    DEFAULT_FOV,
    NEAR_PLANE,
    FAR_PLANE,
    MIN_PITCH,
    MAX_PITCH,
    INVERT_MOUSE_Y,
)


class Camera:
    """
    First-person camera with FPS-style controls.

    Features:
    - WASD movement (forward, left, backward, right)
    - QE vertical movement (down, up)
    - Mouse look (yaw and pitch)
    - Configurable speed and sensitivity
    """

    def __init__(
        self,
        position: Vector3,
        target: Vector3 = None,
        speed: float = DEFAULT_CAMERA_SPEED,
        sensitivity: float = MOUSE_SENSITIVITY
    ):
        """
        Initialize camera.

        Args:
            position: Camera position in world space
            target: Initial look-at target (optional, calculated from yaw/pitch if None)
            speed: Movement speed in units per second
            sensitivity: Mouse sensitivity in degrees per pixel
        """
        self.position = position
        self.speed = speed
        self.sensitivity = sensitivity

        # Euler angles
        self.yaw = -90.0  # Look down negative Z axis initially
        self.pitch = -20.0  # Look down slightly

        # Calculate initial target from yaw/pitch
        if target is None:
            self.update_vectors()
            self.target = self.position + self._front
        else:
            self.target = target
            self.update_vectors()

        # Internal vectors
        self._front = Vector3([0.0, 0.0, -1.0])
        self._up = Vector3([0.0, 1.0, 0.0])
        self._right = Vector3([1.0, 0.0, 0.0])

    def update_vectors(self):
        """
        Update camera direction vectors based on yaw and pitch.
        Call this after changing yaw or pitch.
        """
        # Convert to radians
        yaw_rad = np.radians(self.yaw)
        pitch_rad = np.radians(self.pitch)

        # Calculate front vector from yaw and pitch
        front = Vector3([
            np.cos(yaw_rad) * np.cos(pitch_rad),
            np.sin(pitch_rad),
            np.sin(yaw_rad) * np.cos(pitch_rad)
        ])

        self._front = vector.normalise(front)

        # Calculate right and up vectors
        self._right = vector.normalise(np.cross(self._front, Vector3([0.0, 1.0, 0.0])))
        self._up = vector.normalise(np.cross(self._right, self._front))

        # Update target
        self.target = self.position + self._front

    def get_view_matrix(self) -> Matrix44:
        """
        Get the camera view matrix.

        Returns:
            4x4 view matrix for camera transformation
        """
        return Matrix44.look_at(
            self.position,
            self.target,
            Vector3([0.0, 1.0, 0.0])
        )

    def get_projection_matrix(self, aspect_ratio: float, fov: float = DEFAULT_FOV) -> Matrix44:
        """
        Get the camera projection matrix.

        Args:
            aspect_ratio: Viewport width / height
            fov: Field of view in degrees

        Returns:
            4x4 projection matrix
        """
        return Matrix44.perspective_projection(
            fov,
            aspect_ratio,
            NEAR_PLANE,
            FAR_PLANE
        )

    def get_forward(self) -> Vector3:
        """Get camera forward vector"""
        return vector.normalise(self.target - self.position)

    def get_position(self) -> Vector3:
        """Get camera position"""
        return self.position

    def get_front(self) -> Vector3:
        """Get camera front vector"""
        return self._front

    def get_right(self) -> Vector3:
        """Get camera right vector"""
        return self._right

    def get_up(self) -> Vector3:
        """Get camera up vector"""
        return self._up
