"""
Geometry Renderer

Renders scene geometry to the G-Buffer (deferred rendering geometry pass).
"""

from typing import Tuple
import moderngl

from ..core.camera import Camera
from ..core.scene import Scene
from .gbuffer import GBuffer


class GeometryRenderer:
    """
    Renders scene geometry to G-Buffer.

    This is the first pass of deferred rendering, where geometric
    properties (position, normal, albedo) are written to textures
    for later use in the lighting pass.
    """

    def __init__(self, ctx: moderngl.Context, geometry_program: moderngl.Program,
                 geometry_textured_program: moderngl.Program = None,
                 unlit_program: moderngl.Program = None,
                 geometry_textured_skinned_program: moderngl.Program = None):
        """
        Initialize geometry renderer.

        Args:
            ctx: ModernGL context
            geometry_program: Shader program for geometry pass (primitives)
            geometry_textured_program: Shader program for textured models
            unlit_program: Shader program for unlit materials (KHR_materials_unlit)
            geometry_textured_skinned_program: Shader program for skinned meshes
        """
        self.ctx = ctx
        self.geometry_program = geometry_program
        self.geometry_textured_program = geometry_textured_program
        self.unlit_program = unlit_program
        self.geometry_textured_skinned_program = geometry_textured_skinned_program

    def render(self, scene: Scene, camera: Camera, gbuffer: GBuffer):
        """
        Render scene geometry to G-Buffer with frustum culling.

        Args:
            scene: Scene to render
            camera: Camera for view
            gbuffer: G-Buffer to render into
        """
        # Use G-Buffer framebuffer
        gbuffer.use()

        # Clear G-Buffer
        gbuffer.clear()

        # Set viewport
        self.ctx.viewport = gbuffer.viewport

        # Enable depth testing
        self.ctx.enable(moderngl.DEPTH_TEST)

        # Set camera uniforms for all programs
        self._set_camera_uniforms(camera, gbuffer.size)
        if self.geometry_textured_program:
            self._set_camera_uniforms_textured(camera, gbuffer.size)
        if self.unlit_program:
            self._set_camera_uniforms_unlit(camera, gbuffer.size)
        if self.geometry_textured_skinned_program:
            self._set_camera_uniforms_textured_skinned(camera, gbuffer.size)

        # Get frustum for culling
        from ..config.settings import ENABLE_FRUSTUM_CULLING
        frustum = None
        if ENABLE_FRUSTUM_CULLING:
            width, height = gbuffer.size
            aspect_ratio = width / height if height > 0 else 1.0
            frustum = camera.get_frustum(aspect_ratio)

        # Render all visible scene objects
        scene.render_all(
            self.geometry_program,
            frustum=frustum,
            debug_label="Geometry Pass",
            textured_program=self.geometry_textured_program,
            unlit_program=self.unlit_program,
            textured_skinned_program=self.geometry_textured_skinned_program
        )

    def _set_camera_uniforms(self, camera: Camera, viewport_size: Tuple[int, int]):
        """
        Set camera-related shader uniforms.

        Args:
            camera: Camera to get matrices from
            viewport_size: Viewport size for aspect ratio
        """
        # Calculate aspect ratio
        width, height = viewport_size
        aspect_ratio = width / height if height > 0 else 1.0

        # Get camera matrices
        view = camera.get_view_matrix()
        projection = camera.get_projection_matrix(aspect_ratio)

        # Set uniforms
        self.geometry_program['projection'].write(projection.astype('f4').tobytes())
        self.geometry_program['view'].write(view.astype('f4').tobytes())

    def _set_camera_uniforms_textured(self, camera: Camera, viewport_size: Tuple[int, int]):
        """
        Set camera-related shader uniforms for textured program.

        Args:
            camera: Camera to get matrices from
            viewport_size: Viewport size for aspect ratio
        """
        # Calculate aspect ratio
        width, height = viewport_size
        aspect_ratio = width / height if height > 0 else 1.0

        # Get camera matrices
        view = camera.get_view_matrix()
        projection = camera.get_projection_matrix(aspect_ratio)

        # Set uniforms for textured program
        self.geometry_textured_program['projection'].write(projection.astype('f4').tobytes())
        self.geometry_textured_program['view'].write(view.astype('f4').tobytes())

    def _set_camera_uniforms_unlit(self, camera: Camera, viewport_size: Tuple[int, int]):
        """
        Set camera-related shader uniforms for unlit program.

        Args:
            camera: Camera to get matrices from
            viewport_size: Viewport size for aspect ratio
        """
        # Calculate aspect ratio
        width, height = viewport_size
        aspect_ratio = width / height if height > 0 else 1.0

        # Get camera matrices
        view = camera.get_view_matrix()
        projection = camera.get_projection_matrix(aspect_ratio)

        # Set uniforms for unlit program
        self.unlit_program['projection'].write(projection.astype('f4').tobytes())
        self.unlit_program['view'].write(view.astype('f4').tobytes())

    def _set_camera_uniforms_textured_skinned(self, camera: Camera, viewport_size: Tuple[int, int]):
        """
        Set camera-related shader uniforms for skinned program.

        Args:
            camera: Camera to get matrices from
            viewport_size: Viewport size for aspect ratio
        """
        # Calculate aspect ratio
        width, height = viewport_size
        aspect_ratio = width / height if height > 0 else 1.0

        # Get camera matrices
        view = camera.get_view_matrix()
        projection = camera.get_projection_matrix(aspect_ratio)

        # Set uniforms for skinned program
        self.geometry_textured_skinned_program['projection'].write(projection.astype('f4').tobytes())
        self.geometry_textured_skinned_program['view'].write(view.astype('f4').tobytes())
