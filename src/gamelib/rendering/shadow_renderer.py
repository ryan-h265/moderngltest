"""
Shadow Renderer

Handles shadow map generation for all lights.
"""

from typing import Dict, List, Optional, Sequence, Tuple

import moderngl
import numpy as np

from ..config.settings import (
    SHADOW_MAP_SIZE,
    SHADOW_MAP_SIZE_LOW,
    SHADOW_MAP_SIZE_MED,
    SHADOW_MAP_SIZE_HIGH,
    ENABLE_ADAPTIVE_SHADOW_RES,
)
from ..core.light import Light
from ..core.scene import Scene


class ShadowRenderer:
    """
    Renders shadow maps for shadow-casting lights.

    Each light gets its own shadow map (depth texture + framebuffer).
    """

    def __init__(
        self,
        ctx: moderngl.Context,
        shadow_program: moderngl.Program,
        shadow_size: int = SHADOW_MAP_SIZE
    ):
        """
        Initialize shadow renderer.

        Args:
            ctx: ModernGL context
            shadow_program: Shader program for shadow depth rendering
            shadow_size: Resolution of shadow maps (width and height)
        """
        self.ctx = ctx
        self.shadow_program = shadow_program
        self.shadow_size = shadow_size
        self._screen_viewport: Optional[Tuple[int, int, int, int]] = None
        self.last_stats: Optional[Dict[str, int]] = None

    def set_screen_viewport(self, viewport: Tuple[int, int, int, int]) -> None:
        """Persist the default screen viewport to restore after shadow passes."""
        self._screen_viewport = viewport

    def create_shadow_map(self, resolution: Optional[int] = None) -> Tuple[moderngl.Texture, moderngl.Framebuffer]:
        """
        Create a shadow map texture and framebuffer.

        Args:
            resolution: Shadow map resolution (defaults to self.shadow_size)

        Returns:
            Tuple of (depth_texture, framebuffer)
        """
        if resolution is None:
            resolution = self.shadow_size

        # Create depth texture for shadow map
        shadow_map = self.ctx.depth_texture((resolution, resolution))
        shadow_map.compare_func = ''  # Disable comparison for sampling
        shadow_map.repeat_x = False
        shadow_map.repeat_y = False

        # Create framebuffer with depth attachment
        shadow_fbo = self.ctx.framebuffer(depth_attachment=shadow_map)

        return shadow_map, shadow_fbo

    def create_shadow_cube_map(
        self, resolution: Optional[int] = None
    ) -> Tuple[moderngl.Texture, List[moderngl.Framebuffer]]:
        """Create a cube depth texture and framebuffer per face."""

        if resolution is None:
            resolution = self.shadow_size

        cube_map = self.ctx.depth_texture_cube((resolution, resolution))
        cube_map.compare_func = ''
        cube_map.repeat_x = False
        cube_map.repeat_y = False

        fbos = [
            self.ctx.framebuffer(depth_attachment=(cube_map, face))
            for face in range(6)
        ]

        return cube_map, fbos

    def _calculate_shadow_resolution(self, light: Light, camera_position=None) -> int:
        """
        Calculate appropriate shadow map resolution for a light based on importance.

        Importance = intensity / distance² (if camera position provided)

        Args:
            light: Light to calculate resolution for
            camera_position: Optional camera position for distance calculation

        Returns:
            Shadow map resolution (LOW/MED/HIGH)
        """
        if not ENABLE_ADAPTIVE_SHADOW_RES:
            return SHADOW_MAP_SIZE_HIGH

        # Calculate importance score
        if camera_position is not None:
            distance = np.linalg.norm(light.position - camera_position)
            distance = max(distance, 0.1)  # Prevent division by zero
            importance = light.intensity / (distance * distance)
        else:
            # No camera position - use intensity only
            importance = light.intensity

        # Map importance to resolution tiers
        # High: importance > 0.01 (close bright lights)
        # Med:  importance > 0.001 (medium distance/brightness)
        # Low:  everything else
        if importance > 0.01:
            return SHADOW_MAP_SIZE_HIGH
        elif importance > 0.001:
            return SHADOW_MAP_SIZE_MED
        else:
            return SHADOW_MAP_SIZE_LOW

    def initialize_light_shadow_maps(self, lights: List[Light], camera_position=None):
        """
        Create shadow maps for shadow-casting lights that don't have them.

        Uses adaptive resolution based on light importance if enabled.
        Non-shadow-casting lights are skipped to save memory.

        Args:
            lights: List of lights to initialize
            camera_position: Optional camera position for adaptive resolution
        """
        for light in lights:
            # Only create shadow maps for shadow-casting lights
            if not light.cast_shadows:
                continue

            needs_rebuild = False
            if light.light_type == 'point':
                needs_rebuild = (
                    light.shadow_map is None
                    or not light.shadow_face_fbos
                    or light.shadow_map_type != 'cube'
                )
            else:
                needs_rebuild = (
                    light.shadow_map is None
                    or light.shadow_fbo is None
                    or light.shadow_map_type not in (None, '2d')
                )

            if needs_rebuild:
                resolution = self._calculate_shadow_resolution(light, camera_position)
                light.shadow_resolution = resolution

                if light.light_type == 'point':
                    light.shadow_map, light.shadow_face_fbos = self.create_shadow_cube_map(resolution)
                    light.shadow_fbo = None
                    light.shadow_map_type = 'cube'
                else:
                    light.shadow_map, light.shadow_fbo = self.create_shadow_map(resolution)
                    light.shadow_face_fbos = []
                    light.shadow_map_type = '2d'

    def render_shadow_maps(self, lights: List[Light], scene: Scene):
        """
        Render shadow maps for all lights with optimizations.

        Optimizations:
        - Intensity culling: Skip lights below minimum intensity
        - Shadow map caching: Only re-render shadows for lights that moved
        - Throttling: Update static light shadows less frequently
        - Non-shadow-casting lights are skipped entirely

        Args:
            lights: List of lights to render shadows for
            scene: Scene to render
        """
        from ..config.settings import (
            SHADOW_MAP_MIN_INTENSITY,
            SHADOW_UPDATE_THROTTLE_FRAMES,
            DEBUG_SHADOW_RENDERING
        )

        # Track statistics for debugging
        rendered = 0
        skipped_intensity = 0
        skipped_throttle = 0
        skipped_non_casting = 0

        for light in lights:
            # Skip non-shadow-casting lights
            if not light.cast_shadows:
                skipped_non_casting += 1
                continue

            # Check if shadow should be rendered (intensity + throttling)
            if light.should_render_shadow(SHADOW_MAP_MIN_INTENSITY, SHADOW_UPDATE_THROTTLE_FRAMES):
                self.render_single_shadow_map(light, scene)
                light.mark_shadow_clean()
                rendered += 1
            else:
                # Determine skip reason for statistics
                if light.intensity < SHADOW_MAP_MIN_INTENSITY:
                    skipped_intensity += 1
                else:
                    skipped_throttle += 1

                # Increment age for throttling
                light.increment_shadow_age()

        # Persist stats for overlay/debug consumers
        self.last_stats = {
            'rendered': rendered,
            'total': len(lights),
            'skipped_intensity': skipped_intensity,
            'skipped_throttle': skipped_throttle,
            'skipped_non_casting': skipped_non_casting,
        }

        # Debug output
        if DEBUG_SHADOW_RENDERING:
            total = len(lights)
            print(f"Shadow Maps: Rendered {rendered}/{total}, "
                  f"Skipped (intensity={skipped_intensity}, throttle={skipped_throttle}, "
                  f"non-casting={skipped_non_casting})")

        if self._screen_viewport is not None:
            self.ctx.viewport = self._screen_viewport

    def render_single_shadow_map(self, light: Light, scene: Scene):
        """
        Render shadow map for a single light with frustum culling.

        Args:
            light: Light to render shadow for
            scene: Scene to render
        """
        resolution = light.shadow_resolution if light.shadow_resolution else self.shadow_size

        self.ctx.enable(moderngl.DEPTH_TEST)

        def _render_with_matrix(matrix: np.ndarray, target_fbo: moderngl.Framebuffer, face_index: int | None = None):
            target_fbo.use()
            target_fbo.clear()
            self.ctx.viewport = (0, 0, resolution, resolution)

            self.shadow_program['light_matrix'].write(matrix.astype('f4').tobytes())
            if 'light_type' in self.shadow_program:
                self.shadow_program['light_type'].value = light.get_light_type_id()
            if 'shadow_face' in self.shadow_program and face_index is not None:
                self.shadow_program['shadow_face'].value = face_index

            from ..config.settings import ENABLE_FRUSTUM_CULLING
            frustum = None
            if ENABLE_FRUSTUM_CULLING:
                from ..core.frustum import Frustum
                frustum = Frustum(matrix)

            scene.render_all(self.shadow_program, frustum=frustum, debug_label="Shadow Pass")

        if light.light_type == 'point':
            matrices: Sequence[np.ndarray] = light.get_shadow_matrices()
            for face_index, matrix in enumerate(matrices):
                target_fbo = light.shadow_face_fbos[face_index]
                _render_with_matrix(matrix, target_fbo, face_index)
        else:
            matrix = light.get_shadow_matrices()[0]
            target_fbo = light.shadow_fbo
            _render_with_matrix(matrix, target_fbo, None)
