"""
Shadow Renderer

Handles shadow map generation for all lights.
"""

from typing import List, Tuple
import moderngl

from ..config.settings import SHADOW_MAP_SIZE
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

    def create_shadow_map(self) -> Tuple[moderngl.Texture, moderngl.Framebuffer]:
        """
        Create a shadow map texture and framebuffer.

        Returns:
            Tuple of (depth_texture, framebuffer)
        """
        # Create depth texture for shadow map
        shadow_map = self.ctx.depth_texture((self.shadow_size, self.shadow_size))
        shadow_map.compare_func = ''  # Disable comparison for sampling
        shadow_map.repeat_x = False
        shadow_map.repeat_y = False

        # Create framebuffer with depth attachment
        shadow_fbo = self.ctx.framebuffer(depth_attachment=shadow_map)

        return shadow_map, shadow_fbo

    def initialize_light_shadow_maps(self, lights: List[Light]):
        """
        Create shadow maps for all lights that don't have them.

        Args:
            lights: List of lights to initialize
        """
        for light in lights:
            if light.shadow_map is None or light.shadow_fbo is None:
                light.shadow_map, light.shadow_fbo = self.create_shadow_map()

    def render_shadow_maps(self, lights: List[Light], scene: Scene):
        """
        Render shadow maps for all lights.

        This performs one shadow pass per light.

        Args:
            lights: List of lights to render shadows for
            scene: Scene to render
        """
        for light in lights:
            self.render_single_shadow_map(light, scene)

    def render_single_shadow_map(self, light: Light, scene: Scene):
        """
        Render shadow map for a single light.

        Args:
            light: Light to render shadow for
            scene: Scene to render
        """
        # Bind light's shadow framebuffer
        light.shadow_fbo.use()
        light.shadow_fbo.clear()

        # Set viewport to shadow map size
        self.ctx.viewport = (0, 0, self.shadow_size, self.shadow_size)

        # Get light matrix
        light_matrix = light.get_light_matrix()

        # Set shader uniform
        self.shadow_program['light_matrix'].write(light_matrix.astype('f4').tobytes())

        # Render scene from light's perspective
        scene.render_all(self.shadow_program)
