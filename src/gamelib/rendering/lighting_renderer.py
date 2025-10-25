"""
Lighting Renderer

Renders lighting in the deferred rendering pipeline.
Each light is rendered as a full-screen quad that reads from the G-Buffer.
"""

from typing import List, Optional
import numpy as np
import moderngl

from ..core.camera import Camera
from ..core.light import Light
from ..core.skybox import Skybox
from .gbuffer import GBuffer
from ..config.settings import (
    AMBIENT_STRENGTH,
    MAX_LIGHTS_PER_FRAME,
    ENABLE_LIGHT_SORTING
)
from ..config import settings


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
        ssao_texture: moderngl.Texture = None,
        skybox: Optional[Skybox] = None,
        time: float | None = None,
        apply_post_lighting=None,
    ):
        """
        Render all lighting to the screen.

        Args:
            lights: List of lights to render
            gbuffer: G-Buffer with geometric data
            camera: Camera for view position
            viewport: Viewport tuple (x, y, width, height)
            ssao_texture: Optional SSAO texture
            skybox: Optional skybox for background rendering
            apply_post_lighting: Optional callback executed after emissive pass
                while additive blending is still enabled (used for bloom)
            time: Elapsed time in seconds for animated effects
        """
        self.render_to_target(
            lights,
            gbuffer,
            camera,
            viewport,
            self.ctx.screen,
            ssao_texture,
            skybox=skybox,
            time=time,
            apply_post_lighting=apply_post_lighting,
        )

    def render_to_target(
        self,
        lights: List[Light],
        gbuffer: GBuffer,
        camera: Camera,
        viewport: tuple,
        target: moderngl.Framebuffer,
        ssao_texture: moderngl.Texture = None,
        skybox: Optional[Skybox] = None,
        time: float | None = None,
        apply_post_lighting=None,
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
            skybox: Optional skybox for background rendering
            apply_post_lighting: Optional callback executed after emissive pass
                while additive blending is still enabled (used for bloom)
        """
        # Use target framebuffer
        target.use()

        # Set viewport
        self.ctx.viewport = viewport

        # Disable depth testing (we're rendering screen-space quads)
        self.ctx.disable(moderngl.DEPTH_TEST)

        # Bind G-Buffer textures (locations 0-3)
        gbuffer.bind_textures(start_location=0)

        # Prepare matrices for screen-space reconstruction
        _, _, width, height = viewport
        aspect_ratio = width / height if height > 0 else 1.0
        view_matrix = camera.get_view_matrix()
        projection_matrix = camera.get_projection_matrix(aspect_ratio)
        inverse_view = np.linalg.inv(view_matrix)
        inverse_projection = np.linalg.inv(projection_matrix)

        # Step 1: Render ambient lighting (no blending)
        self.ctx.disable(moderngl.BLEND)
        self._render_ambient(
            gbuffer,
            ssao_texture,
            inverse_view=inverse_view,
            inverse_projection=inverse_projection,
            skybox=skybox,
            camera=camera,
            viewport=viewport,
            time=time,
        )

        # Step 2: Sort and limit lights if enabled
        lights_to_render = self._prepare_lights_for_rendering(lights, camera)

        # Step 3: Accumulate lighting from all lights (additive blending)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.ONE, moderngl.ONE  # Additive blending

        for light_index, light in enumerate(lights_to_render):
            self._render_light(light, light_index, camera, inverse_view, time)

        # Step 4: Add emissive contribution (additive blending still enabled)
        self._render_emissive(gbuffer, camera, inverse_view, time)

        if apply_post_lighting is not None:
            apply_post_lighting()

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

    def _render_ambient(
        self,
        gbuffer: GBuffer,
        ssao_texture: moderngl.Texture = None,
        inverse_view: np.ndarray | None = None,
        inverse_projection: np.ndarray | None = None,
        skybox: Optional[Skybox] = None,
        camera: Camera | None = None,
        viewport: tuple | None = None,
        time: float | None = None,
    ):
        """
        Render ambient lighting pass.

        Args:
            gbuffer: G-Buffer (for texture binding reference)
            ssao_texture: Optional SSAO texture
            inverse_view: Optional inverse view matrix for world reconstruction
            inverse_projection: Optional inverse projection matrix
            skybox: Optional skybox configuration for background rendering
            camera: Camera for world-space position (procedural sky)
            viewport: Current viewport (for resolution uniform)
            time: Current time in seconds
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

        if camera is not None:
            if 'camera_pos' in self.ambient_program:
                self.ambient_program['camera_pos'].write(camera.position.astype('f4').tobytes())
            if inverse_view is not None and 'inverse_view' in self.ambient_program:
                self.ambient_program['inverse_view'].write(inverse_view.astype('f4').tobytes())

        self._set_fog_uniforms(self.ambient_program, time)

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

        if inverse_view is not None and 'inverse_view' in self.ambient_program:
            self.ambient_program['inverse_view'].write(inverse_view.astype('f4').tobytes())
        if inverse_projection is not None and 'inverse_projection' in self.ambient_program:
            self.ambient_program['inverse_projection'].write(inverse_projection.astype('f4').tobytes())

        time_value = float(time) if time is not None else 0.0
        if 'u_time' in self.ambient_program:
            self.ambient_program['u_time'].value = time_value

        if viewport is not None and 'u_resolution' in self.ambient_program:
            _, _, width, height = viewport
            width = max(width, 1)
            height = max(height, 1)
            self.ambient_program['u_resolution'].value = (float(width), float(height))

        if camera is not None and 'u_cameraPos' in self.ambient_program:
            pos = tuple(float(v) for v in camera.position)
            self.ambient_program['u_cameraPos'].value = pos

        procedural_mode = 1 if (skybox is not None and skybox.shader_variant == "aurora") else 0
        if 'u_useProceduralSky' in self.ambient_program:
            self.ambient_program['u_useProceduralSky'].value = procedural_mode

        aurora_dir = (-0.5, -0.6, 0.9)
        transition_alpha = 1.0
        fog_enabled = 0
        fog_color = (0.0, 0.0, 0.0)
        fog_start = 0.0
        fog_end = 1.0
        fog_strength = 0.0

        if skybox is not None:
            aurora_dir = skybox.get_uniform("u_auroraDir", aurora_dir)
            transition_alpha = float(skybox.get_uniform("u_transitionAlpha", transition_alpha))
            if procedural_mode == 1:
                fog_enabled = int(skybox.get_uniform("fogEnabled", 0))
                fog_color = skybox.get_uniform("fogColor", fog_color)
                fog_start = float(skybox.get_uniform("fogStart", fog_start))
                fog_end = float(skybox.get_uniform("fogEnd", fog_end))
                fog_strength = float(skybox.get_uniform("fogStrength", fog_strength))

        if 'u_auroraDir' in self.ambient_program:
            self.ambient_program['u_auroraDir'].value = tuple(float(v) for v in aurora_dir)
        if 'u_transitionAlpha' in self.ambient_program:
            self.ambient_program['u_transitionAlpha'].value = transition_alpha
        if 'fogEnabled' in self.ambient_program:
            self.ambient_program['fogEnabled'].value = fog_enabled
        if 'fogColor' in self.ambient_program:
            self.ambient_program['fogColor'].value = tuple(float(v) for v in fog_color)
        if 'fogStart' in self.ambient_program:
            self.ambient_program['fogStart'].value = fog_start
        if 'fogEnd' in self.ambient_program:
            self.ambient_program['fogEnd'].value = fog_end
        if 'fogStrength' in self.ambient_program:
            self.ambient_program['fogStrength'].value = fog_strength

        if skybox is not None and getattr(skybox, 'texture', None) is not None:
            if 'skybox_enabled' in self.ambient_program:
                self.ambient_program['skybox_enabled'].value = True
            if 'skybox_texture' in self.ambient_program:
                self.ambient_program['skybox_texture'].value = 7
            skybox.texture.use(location=7)
            if 'skybox_intensity' in self.ambient_program:
                self.ambient_program['skybox_intensity'].value = skybox.intensity
            if 'skybox_rotation' in self.ambient_program:
                self.ambient_program['skybox_rotation'].write(skybox.rotation_matrix().astype('f4').tobytes())
        else:
            if 'skybox_enabled' in self.ambient_program:
                self.ambient_program['skybox_enabled'].value = False

        # Render full-screen quad
        self.quad_vao_ambient.render(moderngl.TRIANGLES)

    def _render_light(self, light: Light, light_index: int, camera: Camera, inverse_view: np.ndarray, time: float = 0.0):
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
        if 'light_type' in self.lighting_program:
            self.lighting_program['light_type'].value = light.get_light_type_id()
        if 'light_range' in self.lighting_program:
            self.lighting_program['light_range'].value = light.range
        if 'light_direction' in self.lighting_program:
            direction = light.get_direction()
            self.lighting_program['light_direction'].write(direction.astype('f4').tobytes())
        if 'spot_inner_cos' in self.lighting_program and 'spot_outer_cos' in self.lighting_program:
            inner_cos, outer_cos = light.get_spot_cosines()
            self.lighting_program['spot_inner_cos'].value = inner_cos
            self.lighting_program['spot_outer_cos'].value = outer_cos

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

        self._set_fog_uniforms(self.lighting_program, time)

        # Render full-screen quad
        self.quad_vao_lighting.render(moderngl.TRIANGLES)

    def _render_emissive(self, gbuffer: GBuffer, camera: Camera, inverse_view: np.ndarray, time: float = 0.0):
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
        if 'gPosition' in self.emissive_program:
            self.emissive_program['gPosition'].value = 0

        if 'camera_pos' in self.emissive_program:
            self.emissive_program['camera_pos'].write(camera.position.astype('f4').tobytes())
        if 'inverse_view' in self.emissive_program:
            self.emissive_program['inverse_view'].write(inverse_view.astype('f4').tobytes())

        self._set_fog_uniforms(self.emissive_program, time)

        # Render full-screen quad with emissive shader
        self.quad_vao_emissive.render(moderngl.TRIANGLES)

    def _set_fog_uniforms(self, program: moderngl.Program, time: float):
        """Write fog parameters into the provided shader program if supported."""

        if 'fog_enabled' in program:
            program['fog_enabled'].value = int(settings.FOG_ENABLED)
        if 'fog_color' in program:
            program['fog_color'].write(np.array(settings.FOG_COLOR, dtype='f4').tobytes())
        if 'fog_density' in program:
            program['fog_density'].value = float(settings.FOG_DENSITY)
        if 'fog_start_distance' in program:
            program['fog_start_distance'].value = float(settings.FOG_START_DISTANCE)
        if 'fog_end_distance' in program:
            program['fog_end_distance'].value = float(settings.FOG_END_DISTANCE)
        if 'fog_base_height' in program:
            program['fog_base_height'].value = float(settings.FOG_BASE_HEIGHT)
        if 'fog_height_falloff' in program:
            program['fog_height_falloff'].value = float(settings.FOG_HEIGHT_FALLOFF)
        if 'fog_noise_scale' in program:
            program['fog_noise_scale'].value = float(settings.FOG_NOISE_SCALE)
        if 'fog_noise_strength' in program:
            program['fog_noise_strength'].value = float(settings.FOG_NOISE_STRENGTH)
        if 'fog_noise_speed' in program:
            program['fog_noise_speed'].value = float(settings.FOG_NOISE_SPEED)
        if 'fog_wind_direction' in program:
            program['fog_wind_direction'].write(np.array(settings.FOG_WIND_DIRECTION, dtype='f4').tobytes())
        if 'fog_time' in program:
            program['fog_time'].value = float(time)
        if 'fog_detail_scale' in program:
            program['fog_detail_scale'].value = float(settings.FOG_DETAIL_SCALE)
        if 'fog_detail_strength' in program:
            program['fog_detail_strength'].value = float(settings.FOG_DETAIL_STRENGTH)
        if 'fog_warp_strength' in program:
            program['fog_warp_strength'].value = float(settings.FOG_WARP_STRENGTH)

