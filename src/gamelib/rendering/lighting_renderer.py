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
from ..config.settings import (
    AMBIENT_STRENGTH,
    CLEAR_COLOR,
    MAX_LIGHTS_PER_FRAME,
    ENABLE_LIGHT_SORTING
)


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
        ambient_program: moderngl.Program,
        emissive_program: moderngl.Program
    ):
        """
        Initialize lighting renderer.

        Args:
            ctx: ModernGL context
            lighting_program: Shader program for per-light lighting
            ambient_program: Shader program for ambient lighting
            emissive_program: Shader program for emissive pass
        """
        self.ctx = ctx
        self.lighting_program = lighting_program
        self.ambient_program = ambient_program
        self.emissive_program = emissive_program

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

        # Create VAO for emissive pass
        self.quad_vao_emissive = self.ctx.vertex_array(
            self.emissive_program,
            [(self.quad_vbo, '2f', 'in_position')]
        )

    def render(
        self,
        lights: List[Light],
        gbuffer: GBuffer,
        camera: Camera,
        viewport: tuple,
        ssao_texture: moderngl.Texture = None
    ):
        """
        Render all lighting to the screen.

        Args:
            lights: List of lights to render
            gbuffer: G-Buffer with geometric data
            camera: Camera for view position
            viewport: Viewport tuple (x, y, width, height)
            ssao_texture: Optional SSAO texture
        """
        self.render_to_target(lights, gbuffer, camera, viewport, self.ctx.screen, ssao_texture)

    def render_to_target(
        self,
        lights: List[Light],
        gbuffer: GBuffer,
        camera: Camera,
        viewport: tuple,
        target: moderngl.Framebuffer,
        ssao_texture: moderngl.Texture = None
    ):
        """
        Render all lighting to a specific target.

        Args:
            lights: List of lights to render
            gbuffer: G-Buffer with geometric data
            camera: Camera for view position
            viewport: Viewport tuple (x, y, width, height)
            target: Target framebuffer
            ssao_texture: Optional SSAO texture
        """
        # Use target framebuffer
        target.use()

        # Set viewport
        self.ctx.viewport = viewport

        # Disable depth testing (we're rendering screen-space quads)
        self.ctx.disable(moderngl.DEPTH_TEST)

        # Bind G-Buffer textures (locations 0-3)
        gbuffer.bind_textures(start_location=0)

        # Step 1: Render ambient lighting (no blending)
        self.ctx.disable(moderngl.BLEND)
        self._render_ambient(gbuffer, ssao_texture)

        # Step 2: Sort and limit lights if enabled
        lights_to_render = self._prepare_lights_for_rendering(lights, camera)

        # Step 3: Accumulate lighting from all lights (additive blending)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.ONE, moderngl.ONE  # Additive blending

        # Get inverse view matrix for world-space reconstruction
        inverse_view = np.linalg.inv(camera.get_view_matrix())

        for light_index, light in enumerate(lights_to_render):
            self._render_light(light, light_index, camera, inverse_view)

        # Step 4: Add emissive contribution (additive blending still enabled)
        self._render_emissive(gbuffer)

        # Restore blending state
        self.ctx.disable(moderngl.BLEND)

    def _prepare_lights_for_rendering(self, lights: List[Light], camera: Camera) -> List[Light]:
        """
        Sort lights by importance and apply budget limit.

        Importance = intensity / distance_to_camera²

        Args:
            lights: All lights in the scene
            camera: Camera for distance calculation

        Returns:
            List of lights to render (sorted and limited)
        """
        if not ENABLE_LIGHT_SORTING and MAX_LIGHTS_PER_FRAME is None:
            return lights  # No optimization needed

        # Calculate importance for each light
        lights_with_importance = []
        for light in lights:
            # Distance from camera to light
            distance = np.linalg.norm(light.position - camera.position)
            # Prevent division by zero
            distance = max(distance, 0.1)

            # Importance = intensity / distance²  (inverse square law)
            importance = light.intensity / (distance * distance)

            lights_with_importance.append((light, importance))

        # Sort by importance (descending - most important first)
        if ENABLE_LIGHT_SORTING:
            lights_with_importance.sort(key=lambda x: x[1], reverse=True)

        # Apply light budget limit
        if MAX_LIGHTS_PER_FRAME is not None:
            lights_with_importance = lights_with_importance[:MAX_LIGHTS_PER_FRAME]

        # Return just the lights (drop importance scores)
        return [light for light, _ in lights_with_importance]

    def _render_ambient(self, gbuffer: GBuffer, ssao_texture: moderngl.Texture = None):
        """
        Render ambient lighting pass.

        Args:
            gbuffer: G-Buffer (for texture binding reference)
            ssao_texture: Optional SSAO texture
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

        # Set SSAO texture and parameters (use location 6 to avoid conflict with gEmissive at location 4)
        if ssao_texture is not None:
            ssao_texture.use(location=6)
            if 'ssaoTexture' in self.ambient_program:
                self.ambient_program['ssaoTexture'].value = 6
            if 'ssaoEnabled' in self.ambient_program:
                self.ambient_program['ssaoEnabled'].value = True
            if 'ssaoIntensity' in self.ambient_program:
                from ..config.settings import SSAO_INTENSITY
                self.ambient_program['ssaoIntensity'].value = SSAO_INTENSITY
        else:
            if 'ssaoEnabled' in self.ambient_program:
                self.ambient_program['ssaoEnabled'].value = False

        # Render full-screen quad
        self.quad_vao_ambient.render(moderngl.TRIANGLES)

    def _render_light(self, light: Light, light_index: int, camera: Camera, inverse_view: np.ndarray):
        """
        Render a single light's contribution.

        Args:
            light: Light to render
            light_index: Index of light (for shadow map binding)
            camera: Camera for view position
            inverse_view: Inverse view matrix for world-space reconstruction
        """
        # Set G-Buffer samplers (locations 0-4) - check if uniforms exist
        if 'gPosition' in self.lighting_program:
            self.lighting_program['gPosition'].value = 0
        if 'gNormal' in self.lighting_program:
            self.lighting_program['gNormal'].value = 1
        if 'gAlbedo' in self.lighting_program:
            self.lighting_program['gAlbedo'].value = 2
        if 'gMaterial' in self.lighting_program:
            self.lighting_program['gMaterial'].value = 3

        # Set inverse view matrix for world-space reconstruction
        if 'inverse_view' in self.lighting_program:
            self.lighting_program['inverse_view'].write(inverse_view.astype('f4').tobytes())

        # Set light properties
        if 'light_position' in self.lighting_program:
            self.lighting_program['light_position'].write(light.position.astype('f4').tobytes())
        if 'light_color' in self.lighting_program:
            self.lighting_program['light_color'].write(light.color.astype('f4').tobytes())
        if 'light_intensity' in self.lighting_program:
            self.lighting_program['light_intensity'].value = light.intensity

        # Set shadow map (use higher texture units to avoid G-Buffer conflict)
        # For non-shadow-casting lights, we still need to bind something to avoid shader errors
        if light.cast_shadows and light.shadow_map is not None:
            shadow_texture_unit = 10 + light_index
            light.shadow_map.use(location=shadow_texture_unit)
            if 'shadow_map' in self.lighting_program:
                self.lighting_program['shadow_map'].value = shadow_texture_unit

            # Set light matrix for shadow mapping
            if 'light_matrix' in self.lighting_program:
                light_matrix = light.get_light_matrix()
                self.lighting_program['light_matrix'].write(light_matrix.astype('f4').tobytes())
        else:
            # Non-shadow-casting light: bind a dummy texture or use a zero matrix
            # The shader will see shadow factor = 0 (no shadow)
            if 'shadow_map' in self.lighting_program:
                # Bind first shadow map or create dummy (shader won't use it effectively)
                shadow_texture_unit = 10
                if 'light_matrix' in self.lighting_program:
                    import numpy as np
                    # Identity matrix will cause all shadow tests to fail gracefully
                    identity = np.eye(4, dtype='f4')
                    self.lighting_program['light_matrix'].write(identity.tobytes())

        # Set camera position
        if 'camera_pos' in self.lighting_program:
            self.lighting_program['camera_pos'].write(camera.position.astype('f4').tobytes())

        # Render full-screen quad
        self.quad_vao_lighting.render(moderngl.TRIANGLES)

    def _render_emissive(self, gbuffer: GBuffer):
        """
        Render emissive contribution pass.

        This pass reads the emissive texture from the G-Buffer and additively blends
        it onto the accumulated lighting. Emissive materials glow independently of lighting.

        Args:
            gbuffer: G-Buffer containing emissive texture
        """
        # Set gEmissive sampler (location 4)
        if 'gEmissive' in self.emissive_program:
            self.emissive_program['gEmissive'].value = 4

        # Render full-screen quad with emissive shader
        self.quad_vao_emissive.render(moderngl.TRIANGLES)
