"""Skybox data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

import moderngl
import numpy as np
from pyrr import Matrix44


@dataclass
class Skybox:
    """Container for skybox configuration and resources."""

    texture: moderngl.TextureCube
    name: str = "Skybox"
    intensity: float = 1.0
    rotation: Matrix44 = field(default_factory=Matrix44.identity)
    shader_variant: str = "cubemap"
    uniforms: Dict[str, Any] = field(default_factory=dict)

    def set_rotation_from_euler(self, yaw: float = 0.0, pitch: float = 0.0, roll: float = 0.0) -> None:
        """Update the rotation matrix from Euler angles (degrees)."""
        yaw_rad = np.radians(yaw)
        pitch_rad = np.radians(pitch)
        roll_rad = np.radians(roll)

        rot_yaw = Matrix44.from_y_rotation(yaw_rad)
        rot_pitch = Matrix44.from_x_rotation(pitch_rad)
        rot_roll = Matrix44.from_z_rotation(roll_rad)

        self.rotation = rot_roll * rot_pitch * rot_yaw

    def rotation_matrix(self) -> Matrix44:
        """Return the current rotation matrix as numpy array."""
        return self.rotation

    def set_uniform(self, name: str, value: Any) -> None:
        """Store a custom uniform value."""
        self.uniforms[name] = value

    def get_uniform(self, name: str, default: Any = None) -> Any:
        """Retrieve a previously stored uniform value."""
        return self.uniforms.get(name, default)

    @classmethod
    def solid_color(
        cls,
        ctx: moderngl.Context,
        color: Tuple[float, float, float],
        name: str = "Solid Sky",
    ) -> "Skybox":
        """Create a skybox using a solid color for all faces."""
        r = max(0, min(1, color[0]))
        g = max(0, min(1, color[1]))
        b = max(0, min(1, color[2]))
        pixel = bytes([int(r * 255), int(g * 255), int(b * 255)])
        data = pixel * 1  # single pixel

        texture = ctx.texture_cube((1, 1), components=3)
        for face in range(6):
            texture.write(face, data)
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        texture.build_mipmaps()
        return cls(texture=texture, name=name)

    @classmethod
    def aurora(
        cls,
        ctx: moderngl.Context,
        name: str = "Aurora Sky",
        aurora_direction: Tuple[float, float, float] = (-0.5, -0.6, 0.9),
    ) -> "Skybox":
        """Create an aurora procedural skybox configuration."""
        # We still allocate a cubemap to keep the rendering pipeline uniform.
        base = cls.solid_color(ctx, (0.0, 0.0, 0.0), name=name)
        base.shader_variant = "aurora"
        base.uniforms.update(
            {
                "u_transitionAlpha": 1.0,
                "u_auroraDir": aurora_direction,
                "fogEnabled": 1,
                "fogColor": (0.05, 0.1, 0.2),
                "fogStrength": 0.35,
                "fogStart": 0.0,
                "fogEnd": 1.0,
            }
        )
        return base
