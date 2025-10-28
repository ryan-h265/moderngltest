"""
Light Debug Renderer

Renders simple debug gizmos for lights consisting of:
- A colored sphere at the light's position
- A line indicating the light's facing direction
"""

from __future__ import annotations

from typing import Iterable, Tuple
import numpy as np
import moderngl
from pyrr import Matrix44
from moderngl_window import geometry

from ..core.camera import Camera
from ..core.light import Light
from ..config import settings


class LightDebugRenderer:
    """Draw debug gizmos for lights to aid placement and orientation."""

    def __init__(self, ctx: moderngl.Context, program: moderngl.Program):
        self.ctx = ctx
        self.program = program

        # Simple sphere without normals/UVs – rendered as a solid colored blob
        self._sphere_geometry = geometry.sphere(
            radius=1.0,
            sectors=12,
            rings=6,
            normals=False,
            uvs=False,
            name="light_debug_sphere",
        )

        # Reusable buffer/VAO for drawing a 2-point line segment
        self._line_buffer = ctx.buffer(reserve=2 * 3 * 4)  # two vec3 vertices
        self._line_vao = ctx.vertex_array(
            self.program,
            [(self._line_buffer, "3f", "in_position")],
        )

        self._identity_matrix = Matrix44.identity()
        self._identity_bytes = self._identity_matrix.astype("f4").tobytes()

    def render(self, camera: Camera, lights: Iterable[Light], viewport: Tuple[int, int, int, int]):
        """Render gizmos for all provided lights."""
        lights = list(lights)
        if not lights:
            return

        # Fetch per-frame configuration (supports runtime tweaks)
        sphere_radius = float(getattr(settings, "DEBUG_LIGHT_GIZMO_SPHERE_RADIUS", 0.25))
        line_length = float(getattr(settings, "DEBUG_LIGHT_GIZMO_LINE_LENGTH", 2.5))
        alpha = float(getattr(settings, "DEBUG_LIGHT_GIZMO_ALPHA", 0.9))

        # Prepare common matrices
        _, _, width, height = viewport
        aspect_ratio = width / height if height > 0 else 1.0
        view = camera.get_view_matrix().astype("f4")
        projection = camera.get_projection_matrix(aspect_ratio).astype("f4")
        self.program["view"].write(view.tobytes())
        self.program["projection"].write(projection.tobytes())

        # Configure state for overlay rendering
        self.ctx.screen.use()
        self.ctx.viewport = viewport
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.depth_mask = False

        try:
            for light in lights:
                color = np.array(
                    [light.color.x, light.color.y, light.color.z], dtype="f4"
                )
                color = np.clip(color, 0.0, 1.0)
                self.program["color"].value = (float(color[0]), float(color[1]), float(color[2]))
                self.program["alpha"].value = alpha

                # Sphere at light position
                translation = Matrix44.from_translation(light.position)
                if not np.isclose(sphere_radius, 1.0):
                    scale = Matrix44.from_scale((sphere_radius, sphere_radius, sphere_radius))
                    model = translation * scale
                else:
                    model = translation
                self.program["model"].write(model.astype("f4").tobytes())
                self._sphere_geometry.render(self.program)

                # Direction line – start at light, extend along direction
                if line_length > 0.0:
                    direction = light.get_direction()
                    start = np.array(
                        [light.position.x, light.position.y, light.position.z],
                        dtype="f4",
                    )
                    end = start + np.array([direction.x, direction.y, direction.z], dtype="f4") * line_length
                    line_vertices = np.concatenate((start, end)).astype("f4")
                    self._line_buffer.write(line_vertices.tobytes())
                    self.program["model"].write(self._identity_bytes)
                    self._line_vao.render(mode=moderngl.LINES, vertices=2)
        finally:
            # Restore default depth/blend state for subsequent passes
            self.ctx.depth_mask = True
            self.ctx.enable(moderngl.DEPTH_TEST)
            self.ctx.disable(moderngl.BLEND)
