"""
Lighting Renderer

Renders lighting in the deferred rendering pipeline.
Each light is rendered as a full-screen quad that reads from the G-Buffer.
"""

from typing import List
import numpy as np
import moderngl

from ..core.camera import Camera
from ..core.light import Light
from .gbuffer import GBuffer
from ..config.settings import AMBIENT_STRENGTH, CLEAR_COLOR


class LightingRenderer:
    """
    Renders lighting using G-Buffer data.

    This is the second pass of deferred rendering. It reads geometric
    properties from the G-Buffer and calculates lighting contributions
    from all lights, accumulating them with additive blending.
    """

    def __init__(
        self,
        ctx: moderngl.Context,
        lighting_program: moderngl.Program,
        ambient_program: moderngl.Program
    ):
        """
        Initialize lighting renderer.

        Args:
            ctx: ModernGL context
            lighting_program: Shader program for per-light lighting
            ambient_program: Shader program for ambient lighting
        """
        self.ctx = ctx
        self.lighting_program = lighting_program
        self.ambient_program = ambient_program

        # Create full-screen quad for rendering
        self._create_fullscreen_quad()

    def _create_fullscreen_quad(self):
        """
        Create a full-screen quad geometry.

        This quad covers the entire screen in NDC coordinates (-1 to 1).
        """
        # Vertex data: positions in NDC space
        # Triangle 1: (-1,-1), (1,-1), (-1,1)
        # Triangle 2: (-1,1), (1,-1), (1,1)
        vertices = np.array([
            -1.0, -1.0,
             1.0, -1.0,
            -1.0,  1.0,
            -1.0,  1.0,
             1.0, -1.0,
             1.0,  1.0,
        ], dtype='f4')

        # Create VBO
        self.quad_vbo = self.ctx.buffer(vertices.tobytes())

        # Create VAO for lighting pass
        self.quad_vao_lighting = self.ctx.vertex_array(
            self.lighting_program,
            [(self.quad_vbo, '2f', 'in_position')]
        )

        # Create VAO for ambient pass
        self.quad_vao_ambient = self.ctx.vertex_array(
            self.ambient_program,
            [(self.quad_vbo, '2f', 'in_position')]
        )

    def render(
        self,
        lights: List[Light],
        gbuffer: GBuffer,
        camera: Camera,
        viewport: tuple
    ):
        """
        Render all lighting to the screen.

        Args:
            lights: List of lights to render
            gbuffer: G-Buffer with geometric data
            camera: Camera for view position
            viewport: Viewport tuple (x, y, width, height)
        """
        # Use screen framebuffer
        self.ctx.screen.use()

        # Set viewport
        self.ctx.viewport = viewport

        # Disable depth testing (we're rendering screen-space quads)
        self.ctx.disable(moderngl.DEPTH_TEST)

        # Bind G-Buffer textures (locations 0-3)
        gbuffer.bind_textures(start_location=0)

        # Step 1: Render ambient lighting (no blending)
        self.ctx.disable(moderngl.BLEND)
        self._render_ambient(gbuffer)

        # Step 2: Accumulate lighting from all lights (additive blending)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.ONE, moderngl.ONE  # Additive blending

        for light_index, light in enumerate(lights):
            self._render_light(light, light_index, camera)

        # Restore blending state
        self.ctx.disable(moderngl.BLEND)

    def _render_ambient(self, gbuffer: GBuffer):
        """
        Render ambient lighting pass.

        Args:
            gbuffer: G-Buffer (for texture binding reference)
        """
        # Set G-Buffer samplers (check if uniforms exist first)
        if 'gPosition' in self.ambient_program:
            self.ambient_program['gPosition'].value = 0
        if 'gNormal' in self.ambient_program:
            self.ambient_program['gNormal'].value = 1
        if 'gAlbedo' in self.ambient_program:
            self.ambient_program['gAlbedo'].value = 2

        # Set ambient strength
        if 'ambient_strength' in self.ambient_program:
            self.ambient_program['ambient_strength'].value = AMBIENT_STRENGTH

        # Render full-screen quad
        self.quad_vao_ambient.render(moderngl.TRIANGLES)

    def _render_light(self, light: Light, light_index: int, camera: Camera):
        """
        Render a single light's contribution.

        Args:
            light: Light to render
            light_index: Index of light (for shadow map binding)
            camera: Camera for view position
        """
        # Set G-Buffer samplers (locations 0-3) - check if uniforms exist
        if 'gPosition' in self.lighting_program:
            self.lighting_program['gPosition'].value = 0
        if 'gNormal' in self.lighting_program:
            self.lighting_program['gNormal'].value = 1
        if 'gAlbedo' in self.lighting_program:
            self.lighting_program['gAlbedo'].value = 2

        # Set light properties
        if 'light_position' in self.lighting_program:
            self.lighting_program['light_position'].write(light.position.astype('f4').tobytes())
        if 'light_color' in self.lighting_program:
            self.lighting_program['light_color'].write(light.color.astype('f4').tobytes())
        if 'light_intensity' in self.lighting_program:
            self.lighting_program['light_intensity'].value = light.intensity

        # Set shadow map (use higher texture units to avoid G-Buffer conflict)
        shadow_texture_unit = 10 + light_index
        if light.shadow_map is not None:
            light.shadow_map.use(location=shadow_texture_unit)
            if 'shadow_map' in self.lighting_program:
                self.lighting_program['shadow_map'].value = shadow_texture_unit

        # Set light matrix for shadow mapping
        if 'light_matrix' in self.lighting_program:
            light_matrix = light.get_light_matrix()
            self.lighting_program['light_matrix'].write(light_matrix.astype('f4').tobytes())

        # Set camera position
        if 'camera_pos' in self.lighting_program:
            self.lighting_program['camera_pos'].write(camera.position.astype('f4').tobytes())

        # Render full-screen quad
        self.quad_vao_lighting.render(moderngl.TRIANGLES)
