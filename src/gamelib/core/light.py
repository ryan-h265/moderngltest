"""
Light Module

Shadow-casting light sources with support for directional, point, and spot lights.
"""

import math
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
    SPOT_LIGHT_NEAR_PLANE,
    SPOT_LIGHT_DEFAULT_FAR,
    POINT_LIGHT_NEAR_PLANE,
    POINT_LIGHT_DEFAULT_FAR,
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
    cast_shadows: bool = True  # If False, light contributes illumination without shadows
    range: float = 0.0  # Effective radius for point/spot lights (0 = infinite)
    inner_cone_angle: float = 20.0  # Degrees (spot lights)
    outer_cone_angle: float = 30.0  # Degrees (spot lights - must be >= inner angle)
    luminous_flux: float = None     # Lumens (point/spot lights)
    illuminance: float = None       # Lux (directional lights)
    intensity_mode: str = 'multiplier'  # 'multiplier', 'lumens', 'lux'

    # Shadow map resources (set by ShadowRenderer)
    shadow_map: moderngl.Texture = None
    shadow_fbo: moderngl.Framebuffer = None
    shadow_resolution: int = None  # Actual resolution of this light's shadow map
    shadow_near_plane: float = field(default=None, init=False, repr=False)
    shadow_far_plane: float = field(default=None, init=False, repr=False)

    # Shadow map caching (optimization)
    _shadow_dirty: bool = field(default=True, init=False, repr=False)
    _last_position: Vector3 = field(default=None, init=False, repr=False)
    _last_target: Vector3 = field(default=None, init=False, repr=False)

    # Shadow map throttling (optimization)
    _frames_since_shadow_update: int = field(default=0, init=False, repr=False)

    def __post_init__(self):
        """Normalize configuration and validate parameters."""
        # Ensure cone angles make sense
        if self.inner_cone_angle < 0.0:
            self.inner_cone_angle = 0.0
        if self.outer_cone_angle < self.inner_cone_angle:
            self.outer_cone_angle = self.inner_cone_angle

        from ..config.settings import (
            PHOTOMETRIC_UNITS_ENABLED,
            LUMINOUS_FLUX_TO_INTENSITY,
            ILLUMINANCE_TO_INTENSITY,
        )

        # Directional lights have infinite range
        if self.light_type == 'directional':
            self.range = 0.0
        elif self.range <= 0.0:
            self.range = 15.0

        if not PHOTOMETRIC_UNITS_ENABLED:
            return

        if self.luminous_flux is not None:
            self.intensity_mode = 'lumens'
            self.intensity = max(self.luminous_flux * LUMINOUS_FLUX_TO_INTENSITY, 0.0)

        if self.illuminance is not None:
            self.intensity_mode = 'lux'
            self.intensity = max(self.illuminance * ILLUMINANCE_TO_INTENSITY, 0.0)

    def get_light_type_id(self) -> int:
        """Return integer identifier for shaders."""
        if self.light_type == 'directional':
            return 0
        if self.light_type == 'point':
            return 1
        if self.light_type == 'spot':
            return 2
        raise ValueError(f"Unknown light type: {self.light_type}")

    def get_direction(self) -> Vector3:
        """
        Calculate a normalized direction vector for directional/spot lights.

        Direction is derived from target - position when available. Falls back to
        global downward vector if the light is co-located with its target.
        """
        direction = self.target - self.position
        length = np.linalg.norm(direction)
        if length < 1e-5:
            # Avoid divide-by-zero; default to downward facing vector
            return Vector3([0.0, -1.0, 0.0])
        return Vector3(direction / length)

    def get_spot_cosines(self) -> tuple:
        """Return cosine of inner/outer cone angles (for shader falloff)."""
        inner_cos = math.cos(math.radians(self.inner_cone_angle))
        outer_cos = math.cos(math.radians(self.outer_cone_angle))
        return inner_cos, outer_cos

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
            self.shadow_near_plane = near
            self.shadow_far_plane = far
        elif self.light_type == 'point':
            raise NotImplementedError("Point light shadow maps not yet implemented")
        elif self.light_type == 'spot':
            fov = max(1.0, min(179.0, self.outer_cone_angle * 2.0))
            aspect = 1.0
            near_plane = max(SPOT_LIGHT_NEAR_PLANE, 0.001)
            far_plane = self.range if self.range > near_plane else SPOT_LIGHT_DEFAULT_FAR
            if far_plane <= near_plane:
                far_plane = near_plane + 0.1

            light_projection = Matrix44.perspective_projection(
                fov,
                aspect,
                near_plane,
                far_plane,
            )
            self.shadow_near_plane = near_plane
            self.shadow_far_plane = far_plane
        else:
            raise ValueError(f"Unknown light type: {self.light_type}")

        # Light view matrix
        light_view = Matrix44.look_at(
            self.position,
            self.target,
            Vector3([0.0, 1.0, 0.0])  # Up vector
        )

        return light_projection * light_view

    def get_point_shadow_matrices(self):
        """Return the 6 view-projection matrices for point light cube shadows."""
        if self.light_type != 'point':
            raise ValueError("Point shadow matrices requested for non-point light")

        near_plane = max(POINT_LIGHT_NEAR_PLANE, 0.001)
        far_plane = self.range if self.range > near_plane else POINT_LIGHT_DEFAULT_FAR
        if far_plane <= near_plane:
            far_plane = near_plane + 0.1

        self.shadow_near_plane = near_plane
        self.shadow_far_plane = far_plane

        projection = Matrix44.perspective_projection(90.0, 1.0, near_plane, far_plane)

        directions = [
            Vector3([1.0, 0.0, 0.0]),
            Vector3([-1.0, 0.0, 0.0]),
            Vector3([0.0, 1.0, 0.0]),
            Vector3([0.0, -1.0, 0.0]),
            Vector3([0.0, 0.0, 1.0]),
            Vector3([0.0, 0.0, -1.0]),
        ]

        up_vectors = [
            Vector3([0.0, -1.0, 0.0]),
            Vector3([0.0, -1.0, 0.0]),
            Vector3([0.0, 0.0, 1.0]),
            Vector3([0.0, 0.0, -1.0]),
            Vector3([0.0, -1.0, 0.0]),
            Vector3([0.0, -1.0, 0.0]),
        ]

        matrices = []
        for direction, up in zip(directions, up_vectors):
            target = Vector3(self.position + direction)
            view = Matrix44.look_at(self.position, target, up)
            matrices.append(projection * view)

        return matrices

    def should_render_shadow(self, intensity_threshold: float = 0.01, throttle_frames: int = 0) -> bool:
        """
        Determine if this light's shadow should be rendered this frame.

        Checks:
        1. Light casts shadows
        2. Intensity is above threshold
        3. Shadow is dirty (light moved) OR throttle interval reached

        Args:
            intensity_threshold: Skip shadows for lights dimmer than this
            throttle_frames: Render shadow every N frames for static lights (0=every frame)

        Returns:
            True if shadow should be rendered this frame
        """
        # Must cast shadows
        if not self.cast_shadows:
            return False

        # Must have sufficient intensity
        if self.intensity < intensity_threshold:
            return False

        # Check if dirty (light moved)
        if self.is_shadow_dirty():
            return True

        # Check throttle interval for static lights
        if throttle_frames > 0:
            return self._frames_since_shadow_update >= throttle_frames

        return False

    def is_shadow_dirty(self) -> bool:
        """
        Check if shadow map needs to be re-rendered.

        Returns True if light position/target changed since last shadow render.
        """
        if not self.cast_shadows:
            return False

        if self._shadow_dirty:
            return True

        # Check if position or target changed
        if self._last_position is None or self._last_target is None:
            return True

        # Convert Vector3 to numpy arrays for comparison
        pos_array = np.array([self.position.x, self.position.y, self.position.z])
        last_pos_array = np.array([self._last_position.x, self._last_position.y, self._last_position.z])
        target_array = np.array([self.target.x, self.target.y, self.target.z])
        last_target_array = np.array([self._last_target.x, self._last_target.y, self._last_target.z])

        position_changed = not np.allclose(pos_array, last_pos_array, atol=1e-5)
        target_changed = not np.allclose(target_array, last_target_array, atol=1e-5)

        return position_changed or target_changed

    def mark_shadow_clean(self):
        """Mark shadow map as up-to-date (called after rendering shadow)."""
        self._shadow_dirty = False
        self._last_position = self.position.copy()
        self._last_target = self.target.copy()
        self._frames_since_shadow_update = 0  # Reset throttle counter

    def increment_shadow_age(self):
        """Increment frames since last shadow update (for throttling)."""
        self._frames_since_shadow_update += 1

    def mark_shadow_dirty(self):
        """Force shadow map to be re-rendered on next frame."""
        self._shadow_dirty = True

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
        Automatically marks shadow as dirty.

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
        self.mark_shadow_dirty()

    def set_position(self, x: float, y: float, z: float):
        """Set light position and mark shadow dirty."""
        self.position.x = x
        self.position.y = y
        self.position.z = z
        self.mark_shadow_dirty()

    def set_target(self, x: float, y: float, z: float):
        """Set light target (look-at point) and mark shadow dirty."""
        self.target.x = x
        self.target.y = y
        self.target.z = z
        self.mark_shadow_dirty()

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
        self.intensity_mode = 'multiplier'
        self.intensity = intensity

    def set_luminous_flux(self, lumens: float):
        """
        Set luminous flux (in lumens) for point/spot lights and derive intensity.
        """
        from ..config.settings import LUMINOUS_FLUX_TO_INTENSITY

        self.luminous_flux = lumens
        self.intensity_mode = 'lumens'
        self.intensity = max(lumens * LUMINOUS_FLUX_TO_INTENSITY, 0.0)

    def set_illuminance(self, lux: float):
        """
        Set illuminance (in lux) for directional lights and derive intensity.
        """
        from ..config.settings import ILLUMINANCE_TO_INTENSITY

        self.illuminance = lux
        self.intensity_mode = 'lux'
        self.intensity = max(lux * ILLUMINANCE_TO_INTENSITY, 0.0)
