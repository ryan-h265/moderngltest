"""
Shadow Renderer

Handles shadow map generation for all lights.
"""

from typing import List, Tuple
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

    def create_shadow_map(self, resolution: int = None) -> Tuple[moderngl.Texture, moderngl.Framebuffer]:
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
            if light.cast_shadows and (light.shadow_map is None or light.shadow_fbo is None):
                # Calculate appropriate resolution
                resolution = self._calculate_shadow_resolution(light, camera_position)
                light.shadow_resolution = resolution

                # Create shadow map with calculated resolution
                light.shadow_map, light.shadow_fbo = self.create_shadow_map(resolution)

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

        # Debug output
        if DEBUG_SHADOW_RENDERING:
            total = len(lights)
            print(f"Shadow Maps: Rendered {rendered}/{total}, "
                  f"Skipped (intensity={skipped_intensity}, throttle={skipped_throttle}, "
                  f"non-casting={skipped_non_casting})")

    def render_single_shadow_map(self, light: Light, scene: Scene):
        """
        Render shadow map for a single light with frustum culling.

        Args:
            light: Light to render shadow for
            scene: Scene to render
        """
        # Bind light's shadow framebuffer
        light.shadow_fbo.use()
        light.shadow_fbo.clear()

        # Set viewport to light's shadow map resolution (supports adaptive sizing)
        resolution = light.shadow_resolution if light.shadow_resolution else self.shadow_size
        self.ctx.viewport = (0, 0, resolution, resolution)

        # IMPORTANT: Enable depth testing for shadow map generation
        self.ctx.enable(moderngl.DEPTH_TEST)

        # Get light matrix
        light_matrix = light.get_light_matrix()

        # Set shader uniform
        self.shadow_program['light_matrix'].write(light_matrix.astype('f4').tobytes())

        # Get frustum for light's view (for culling objects outside light's view)
        from ..config.settings import ENABLE_FRUSTUM_CULLING
        frustum = None
        if ENABLE_FRUSTUM_CULLING:
            from ..core.frustum import Frustum
            frustum = Frustum(light_matrix)

        # Render scene from light's perspective with frustum culling
        scene.render_all(self.shadow_program, frustum=frustum)
