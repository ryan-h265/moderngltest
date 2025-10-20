"""
Light Module

Shadow-casting light sources with support for directional, point, and spot lights.
"""

import numpy as np
from dataclasses import dataclass, field
from pyrr import Matrix44, Vector3
import moderngl

from ..config.settings import (
    DEFAULT_LIGHT_INTENSITY,
    DEFAULT_LIGHT_COLOR,
    LIGHT_ORTHO_LEFT,
    LIGHT_ORTHO_RIGHT,
    LIGHT_ORTHO_BOTTOM,
    LIGHT_ORTHO_TOP,
    LIGHT_ORTHO_NEAR,
    LIGHT_ORTHO_FAR,
)


@dataclass
class Light:
    """
    Shadow-casting light source.

    Supports multiple light types:
    - 'directional': Parallel rays (like sun), uses orthographic projection
    - 'point': Radiates from a point (requires cube map shadows - not yet implemented)
    - 'spot': Cone of light (requires perspective projection - not yet implemented)

    Each light can have its own shadow map for independent shadow casting.
    """

    position: Vector3
    target: Vector3
    color: Vector3 = field(default_factory=lambda: Vector3(DEFAULT_LIGHT_COLOR))
    intensity: float = DEFAULT_LIGHT_INTENSITY
    light_type: str = 'directional'

    # Shadow map resources (set by ShadowRenderer)
    shadow_map: moderngl.Texture = None
    shadow_fbo: moderngl.Framebuffer = None

    def get_light_matrix(
        self,
        left: float = LIGHT_ORTHO_LEFT,
        right: float = LIGHT_ORTHO_RIGHT,
        bottom: float = LIGHT_ORTHO_BOTTOM,
        top: float = LIGHT_ORTHO_TOP,
        near: float = LIGHT_ORTHO_NEAR,
        far: float = LIGHT_ORTHO_FAR
    ) -> Matrix44:
        """
        Calculate light projection and view matrix.

        For directional lights, uses orthographic projection.
        For point/spot lights, would use perspective projection.

        Args:
            left, right, bottom, top: Orthographic frustum bounds
            near, far: Clipping planes

        Returns:
            Combined projection * view matrix
        """
        if self.light_type == 'directional':
            # Orthographic projection for directional light
            light_projection = Matrix44.orthogonal_projection(
                left, right, bottom, top, near, far
            )
        elif self.light_type == 'point':
            # Point lights need cube map shadows (6 perspectives)
            # Not yet implemented - would use perspective projection
            raise NotImplementedError("Point light shadow maps not yet implemented")
        elif self.light_type == 'spot':
            # Spotlight uses perspective projection
            # Not yet implemented
            raise NotImplementedError("Spot light shadow maps not yet implemented")
        else:
            raise ValueError(f"Unknown light type: {self.light_type}")

        # Light view matrix
        light_view = Matrix44.look_at(
            self.position,
            self.target,
            Vector3([0.0, 1.0, 0.0])  # Up vector
        )

        return light_projection * light_view

    def animate_rotation(
        self,
        time: float,
        radius: float = 12.0,
        height: float = 10.0,
        speed: float = 0.5
    ):
        """
        Animate light rotating around a center point.

        Useful for simulating sun movement or rotating lights.

        Args:
            time: Current time in seconds
            radius: Distance from center
            height: Y position (height above ground)
            speed: Rotation speed in radians per second
        """
        angle = time * speed
        self.position.x = radius * np.cos(angle)
        self.position.z = radius * np.sin(angle)
        self.position.y = height

    def set_position(self, x: float, y: float, z: float):
        """Set light position"""
        self.position.x = x
        self.position.y = y
        self.position.z = z

    def set_target(self, x: float, y: float, z: float):
        """Set light target (look-at point)"""
        self.target.x = x
        self.target.y = y
        self.target.z = z

    def set_color(self, r: float, g: float, b: float):
        """
        Set light color.

        Args:
            r, g, b: Color components (0.0 to 1.0)
        """
        self.color.x = r
        self.color.y = g
        self.color.z = b

    def set_intensity(self, intensity: float):
        """
        Set light intensity.

        Args:
            intensity: Multiplier for light contribution (typically 0.0 to 2.0)
        """
        self.intensity = intensity
