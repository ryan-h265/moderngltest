"""
Light Debug Renderer

Renders simple debug gizmos for lights consisting of:
- A colored sphere at the light's position
- A line indicating the light's facing direction
"""

from __future__ import annotations

from typing import Iterable, Tuple
import math
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

    def _draw_line(self, start: np.ndarray, end: np.ndarray) -> None:
        """Render a single line segment using the reusable VAO."""
        line_vertices = np.concatenate((start, end)).astype("f4")
        self._line_buffer.write(line_vertices.tobytes())
        self.program["model"].write(self._identity_bytes)
        self._line_vao.render(mode=moderngl.LINES, vertices=2)

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

                position_vec = np.array(
                    [light.position.x, light.position.y, light.position.z], dtype="f4"
                )

                # Optional volume visualization for point lights (shadow radius)
                if light.light_type == "point":
                    _, far_plane = light.get_shadow_clip_planes()
                    if far_plane > 1e-3:
                        volume_scale = Matrix44.from_scale((far_plane, far_plane, far_plane))
                        volume_model = translation * volume_scale
                        self.program["alpha"].value = alpha * 0.35
                        previous_wireframe = getattr(self.ctx, "wireframe", False)
                        self.ctx.wireframe = True
                        self.program["model"].write(volume_model.astype("f4").tobytes())
                        self._sphere_geometry.render(self.program)
                        self.ctx.wireframe = previous_wireframe
                        self.program["alpha"].value = alpha

                # Direction line – start at light, extend along direction
                if line_length > 0.0:
                    direction = light.get_direction()
                    end = position_vec + np.array([
                        direction.x,
                        direction.y,
                        direction.z,
                    ], dtype="f4") * line_length
                    self._draw_line(position_vec, end)

                # Cone preview for spot lights
                if light.light_type == "spot":
                    _, far_plane = light.get_shadow_clip_planes()
                    if far_plane > 1e-3:
                        direction = light.get_direction()
                        dir_vec = np.array([direction.x, direction.y, direction.z], dtype="f4")
                        base_center = position_vec + dir_vec * far_plane
                        up_hint = np.array([0.0, 1.0, 0.0], dtype="f4")
                        if abs(float(np.dot(dir_vec, up_hint))) > 0.95:
                            up_hint = np.array([0.0, 0.0, 1.0], dtype="f4")
                        right_vec = np.cross(dir_vec, up_hint)
                        norm = np.linalg.norm(right_vec)
                        if norm < 1e-4:
                            right_vec = np.array([1.0, 0.0, 0.0], dtype="f4")
                        else:
                            right_vec /= norm
                        up_vec = np.cross(right_vec, dir_vec)
                        up_norm = np.linalg.norm(up_vec)
                        if up_norm < 1e-4:
                            up_vec = np.array([0.0, 0.0, 1.0], dtype="f4")
                        else:
                            up_vec /= up_norm

                        radius = far_plane * math.tan(math.radians(max(light.outer_cone_angle, 1e-3)))
                        right_vec *= radius
                        up_vec *= radius

                        offsets = [
                            right_vec + up_vec,
                            -right_vec + up_vec,
                            -right_vec - up_vec,
                            right_vec - up_vec,
                        ]

                        self.program["alpha"].value = alpha * 0.6
                        for offset in offsets:
                            base_point = base_center + offset
                            self._draw_line(position_vec, base_point)

                        for idx in range(len(offsets)):
                            start_point = base_center + offsets[idx]
                            end_point = base_center + offsets[(idx + 1) % len(offsets)]
                            self._draw_line(start_point, end_point)

                        self.program["alpha"].value = alpha
        finally:
            # Restore default depth/blend state for subsequent passes
            self.ctx.depth_mask = True
            self.ctx.enable(moderngl.DEPTH_TEST)
            self.ctx.disable(moderngl.BLEND)
