"""
Transparent Renderer

Handles forward rendering of transparent objects with alpha blending.
Objects are depth-sorted back-to-front to ensure correct transparency.
"""

from typing import List, Optional, Tuple
import numpy as np
import moderngl
from pyrr import Vector3

from ..core.camera import Camera
from ..core.scene import Scene
from ..core.light import Light


class TransparentRenderer:
    """
    Renders transparent objects using forward rendering with alpha blending.

    Transparent objects cannot use deferred rendering because blending requires
    writing color directly to the framebuffer. This renderer:
    1. Sorts transparent objects back-to-front (painter's algorithm)
    2. Enables alpha blending
    3. Renders with forward PBR lighting
    """

    def __init__(self, ctx: moderngl.Context, transparent_program: moderngl.Program):
        """
        Initialize transparent renderer.

        Args:
            ctx: ModernGL context
            transparent_program: Forward rendering shader for transparent materials
        """
        self.ctx = ctx
        self.transparent_program = transparent_program
        self._last_viewport_size: Optional[Tuple[int, int]] = None

    def render(
        self,
        scene: Scene,
        camera: Camera,
        lights: List[Light],
        screen_fbo: moderngl.Framebuffer,
        shadow_maps: List[moderngl.Texture],
        viewport_size: Tuple[int, int],
        time: float = 0.0,
    ):
        """
        Render transparent objects with forward rendering and depth sorting.

        Args:
            scene: Scene containing objects to render
            camera: Camera for view
            lights: List of lights for forward lighting
            screen_fbo: Screen framebuffer to render into (already contains opaque objects)
            shadow_maps: Shadow map textures for shadowing
            viewport_size: Viewport size for aspect ratio
            time: Elapsed time in seconds for animated fog
        """
        # Use screen framebuffer (render on top of deferred results)
        screen_fbo.use()

        # Set viewport
        self.ctx.viewport = (0, 0, *viewport_size)

        # Enable depth testing (read-only - don't write to depth buffer)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.depth_func = '<'  # Standard depth test
        # Disable depth writes so transparent objects don't occlude each other incorrectly
        self.ctx.depth_mask = False

        # Enable alpha blending
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        # Set camera uniforms
        width, height = viewport_size
        aspect_ratio = width / height if height > 0 else 1.0
        self._set_camera_uniforms(camera, aspect_ratio)

        # Set lighting uniforms
        self._set_lighting_uniforms(lights, shadow_maps)

        # Set fog uniforms
        self._set_fog_uniforms(time)

        # Get transparent objects (meshes with alpha_mode == "BLEND")
        transparent_meshes = scene.get_transparent_meshes()

        # Depth sort: back-to-front (painter's algorithm)
        camera_pos = camera.position
        sorted_meshes = self._depth_sort_meshes(transparent_meshes, camera_pos)

        # Render each transparent mesh
        for mesh_data in sorted_meshes:
            mesh, parent_transform = mesh_data
            mesh.render(self.transparent_program, parent_transform=parent_transform, ctx=self.ctx)

        # Restore state
        self.ctx.depth_mask = True  # Re-enable depth writes
        self.ctx.disable(moderngl.BLEND)

    def resize(self, viewport_size: Tuple[int, int]):
        """Hook for future resize-specific logic (currently no cached resources)."""
        self._last_viewport_size = viewport_size

    def _set_camera_uniforms(self, camera: Camera, aspect_ratio: float):
        """
        Set camera-related shader uniforms.

        Args:
            camera: Camera to get matrices from
            aspect_ratio: Viewport aspect ratio
        """
        view = camera.get_view_matrix()
        projection = camera.get_projection_matrix(aspect_ratio)

        self.transparent_program['projection'].write(projection.astype('f4').tobytes())
        self.transparent_program['view'].write(view.astype('f4').tobytes())
        self.transparent_program['cameraPos'].write(camera.position.astype('f4').tobytes())

    def _set_lighting_uniforms(self, lights: List[Light], shadow_maps: List[moderngl.Texture]):
        """
        Set lighting uniforms for forward rendering.

        Args:
            lights: List of lights
            shadow_maps: Shadow map textures (one per light)
        """
        num_lights = min(len(lights), 4)
        self.transparent_program['numLights'].value = num_lights

        # Build arrays for batch uniform upload
        import numpy as np
        light_positions = np.zeros((4, 3), dtype='f4')
        light_colors = np.zeros((4, 3), dtype='f4')
        light_intensities = np.zeros(4, dtype='f4')
        light_matrices = []

        for i in range(num_lights):
            light = lights[i]
            light_positions[i] = light.position
            light_colors[i] = light.color
            light_intensities[i] = light.intensity
            light_matrices.append(light.get_light_matrix())

        # Upload arrays as uniforms (check if uniform exists first)
        if 'lightPositions' in self.transparent_program:
            self.transparent_program['lightPositions'].write(light_positions.tobytes())
        if 'lightColors' in self.transparent_program:
            self.transparent_program['lightColors'].write(light_colors.tobytes())
        if 'lightIntensities' in self.transparent_program:
            self.transparent_program['lightIntensities'].write(light_intensities.tobytes())

        # Upload light matrices and shadow maps individually
        for i in range(num_lights):
            uniform_name = f'lightMatrices[{i}]'
            if uniform_name in self.transparent_program:
                self.transparent_program[uniform_name].write(light_matrices[i].astype('f4').tobytes())

            # Bind shadow map
            if i < len(shadow_maps):
                shadow_maps[i].use(location=10 + i)  # shadowMap0-3 at locations 10-13
                shadow_uniform = f'shadowMap{i}'
                if shadow_uniform in self.transparent_program:
                    self.transparent_program[shadow_uniform].value = 10 + i

        # Shadow parameters
        from ..config.settings import SHADOW_BIAS
        self.transparent_program['shadowBias'].value = SHADOW_BIAS

        # Ambient lighting
        from ..config.settings import AMBIENT_STRENGTH
        self.transparent_program['ambientStrength'].value = AMBIENT_STRENGTH

    def _set_fog_uniforms(self, time: float):
        """Populate fog configuration uniforms for the transparent shader."""

        from ..config import settings

        if 'fog_enabled' in self.transparent_program:
            self.transparent_program['fog_enabled'].value = int(settings.FOG_ENABLED)
        if 'fog_color' in self.transparent_program:
            self.transparent_program['fog_color'].write(np.array(settings.FOG_COLOR, dtype='f4').tobytes())
        if 'fog_density' in self.transparent_program:
            self.transparent_program['fog_density'].value = float(settings.FOG_DENSITY)
        if 'fog_start_distance' in self.transparent_program:
            self.transparent_program['fog_start_distance'].value = float(settings.FOG_START_DISTANCE)
        if 'fog_end_distance' in self.transparent_program:
            self.transparent_program['fog_end_distance'].value = float(settings.FOG_END_DISTANCE)
        if 'fog_base_height' in self.transparent_program:
            self.transparent_program['fog_base_height'].value = float(settings.FOG_BASE_HEIGHT)
        if 'fog_height_falloff' in self.transparent_program:
            self.transparent_program['fog_height_falloff'].value = float(settings.FOG_HEIGHT_FALLOFF)
        if 'fog_noise_scale' in self.transparent_program:
            self.transparent_program['fog_noise_scale'].value = float(settings.FOG_NOISE_SCALE)
        if 'fog_noise_strength' in self.transparent_program:
            self.transparent_program['fog_noise_strength'].value = float(settings.FOG_NOISE_STRENGTH)
        if 'fog_noise_speed' in self.transparent_program:
            self.transparent_program['fog_noise_speed'].value = float(settings.FOG_NOISE_SPEED)
        if 'fog_wind_direction' in self.transparent_program:
            self.transparent_program['fog_wind_direction'].write(np.array(settings.FOG_WIND_DIRECTION, dtype='f4').tobytes())
        if 'fog_time' in self.transparent_program:
            self.transparent_program['fog_time'].value = float(time)

    def _depth_sort_meshes(
        self,
        meshes: List[Tuple],
        camera_pos: Vector3
    ) -> List[Tuple]:
        """
        Sort transparent meshes back-to-front based on distance from camera.

        Args:
            meshes: List of (mesh, parent_transform) tuples
            camera_pos: Camera position in world space

        Returns:
            Sorted list of (mesh, parent_transform) tuples
        """
        def get_distance(mesh_data):
            mesh, parent_transform = mesh_data
            # Calculate mesh world position from parent transform
            # Extract translation from 4x4 matrix (last column)
            mesh_pos = Vector3([parent_transform[3][0], parent_transform[3][1], parent_transform[3][2]])
            # Calculate distance to camera
            return (mesh_pos - camera_pos).length

        # Sort by distance (farthest first)
        return sorted(meshes, key=get_distance, reverse=True)
