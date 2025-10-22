"""
Main Renderer

Handles main scene rendering with lighting and shadows.
"""

from typing import List, Tuple
import numpy as np
import moderngl

from ..core.camera import Camera
from ..core.light import Light
from ..core.scene import Scene
from ..config.settings import CLEAR_COLOR


class MainRenderer:
    """
    Renders the main scene with lighting and shadows.

    This is the final rendering pass that composites all lights and shadows.
    """

    def __init__(self, ctx: moderngl.Context, main_program: moderngl.Program):
        """
        Initialize main renderer.

        Args:
            ctx: ModernGL context
            main_program: Shader program for main scene rendering
        """
        self.ctx = ctx
        self.main_program = main_program

    def render(
        self,
        scene: Scene,
        camera: Camera,
        lights: List[Light],
        viewport: Tuple[int, int, int, int]
    ):
        """
        Render the main scene with frustum culling.

        Args:
            scene: Scene to render
            camera: Camera for view
            lights: List of lights (with shadow maps already rendered)
            viewport: Viewport tuple (x, y, width, height)
        """
        self.render_to_target(scene, camera, lights, viewport, self.ctx.screen)

    def render_to_target(
        self,
        scene: Scene,
        camera: Camera,
        lights: List[Light],
        viewport: Tuple[int, int, int, int],
        target: moderngl.Framebuffer
    ):
        """
        Render the main scene to a specific framebuffer.

        Args:
            scene: Scene to render
            camera: Camera for view
            lights: List of lights (with shadow maps already rendered)
            viewport: Viewport tuple (x, y, width, height)
            target: Target framebuffer
        """
        # Use target framebuffer
        target.use()

        # Clear with background color
        self.ctx.clear(*CLEAR_COLOR)

        # Set viewport
        self.ctx.viewport = viewport

        # Bind shadow maps
        self._bind_shadow_maps(lights)

        # Set camera uniforms
        self._set_camera_uniforms(camera, viewport)

        # Set light uniforms
        self._set_light_uniforms(lights)

        # Get frustum for culling
        from ..config.settings import ENABLE_FRUSTUM_CULLING
        frustum = None
        if ENABLE_FRUSTUM_CULLING:
            _, _, width, height = viewport
            aspect_ratio = width / height if height > 0 else 1.0
            frustum = camera.get_frustum(aspect_ratio)

        # Render scene with frustum culling
        scene.render_all(self.main_program, frustum=frustum)

    def _bind_shadow_maps(self, lights: List[Light]):
        """
        Bind all shadow map textures.

        Args:
            lights: List of lights with shadow maps
        """
        for i, light in enumerate(lights):
            if light.shadow_map is not None:
                light.shadow_map.use(location=i)

    def _set_camera_uniforms(self, camera: Camera, viewport: Tuple[int, int, int, int]):
        """
        Set camera-related shader uniforms.

        Args:
            camera: Camera to get matrices from
            viewport: Viewport for aspect ratio calculation
        """
        # Calculate aspect ratio from viewport
        _, _, width, height = viewport
        aspect_ratio = width / height if height > 0 else 1.0

        # Get camera matrices
        view = camera.get_view_matrix()
        projection = camera.get_projection_matrix(aspect_ratio)

        # Set uniforms
        self.main_program['projection'].write(projection.astype('f4').tobytes())
        self.main_program['view'].write(view.astype('f4').tobytes())
        self.main_program['camera_pos'].write(camera.position.astype('f4').tobytes())

    def _set_light_uniforms(self, lights: List[Light]):
        """
        Set light-related shader uniforms.

        Args:
            lights: List of lights
        """
        # Prepare light data arrays
        light_positions = np.array([light.position for light in lights], dtype='f4')
        light_colors = np.array([light.color for light in lights], dtype='f4')
        light_intensities = np.array([light.intensity for light in lights], dtype='f4')
        light_matrices = np.array([light.get_light_matrix() for light in lights], dtype='f4')

        # Set uniforms
        self.main_program['light_positions'].write(light_positions.tobytes())
        self.main_program['light_colors'].write(light_colors.tobytes())
        self.main_program['light_intensities'].write(light_intensities.tobytes())
        self.main_program['light_matrices'].write(light_matrices.tobytes())

        # Bind shadow map samplers
        # OpenGL requires an array of ints for sampler arrays
        shadow_map_locations = np.array([i for i in range(len(lights))], dtype='i4')
        self.main_program['shadow_maps'].write(shadow_map_locations.tobytes())
