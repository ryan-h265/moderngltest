"""Light Debug Renderer

Draws helper gizmos (spheres + rays) visualizing light positions and directions.
"""

from typing import Iterable, Tuple

import moderngl
import numpy as np
from pyrr import Matrix44

from ..core.camera import Camera
from ..core.light import Light
from ..config import settings


class LightDebugRenderer:
    """Renders simple gizmos showing light origins and directions."""

    def __init__(self, ctx: moderngl.Context, program: moderngl.Program) -> None:
        self.ctx = ctx
        self.program = program

        cross_radius = getattr(settings, 'DEBUG_LIGHT_GIZMO_SPHERE_RADIUS', 1.5)
        cross_vertices = np.array([
            -cross_radius, 0.0, 0.0, 0.0, 0.0, 0.0,
             cross_radius, 0.0, 0.0, 0.0, 0.0, 0.0,
             0.0, -cross_radius, 0.0, 0.0, 0.0, 0.0,
             0.0,  cross_radius, 0.0, 0.0, 0.0, 0.0,
             0.0, 0.0, -cross_radius, 0.0, 0.0, 0.0,
             0.0, 0.0,  cross_radius, 0.0, 0.0, 0.0,
        ], dtype='f4')
        self.cross_vbo = ctx.buffer(cross_vertices.tobytes())
        self.cross_vao = ctx.vertex_array(
            self.program,
            [(self.cross_vbo, '3f 3f', 'in_position', 'in_normal')],
        )

        # Line buffer stores two vertices (pos + dummy normal)
        self.line_vbo = ctx.buffer(reserve=2 * 6 * 4)
        self.line_vao = ctx.vertex_array(
            self.program,
            [(self.line_vbo, '3f 3f', 'in_position', 'in_normal')],
        )

        self.identity = Matrix44.identity(dtype='f4')

    def render(
        self,
        lights: Iterable[Light],
        camera: Camera,
        target: moderngl.Framebuffer,
        viewport: Tuple[int, int, int, int],
    ) -> None:
        lights = list(lights)
        if not lights:
            return

        target.use()

        width = max(viewport[2], 1)
        height = max(viewport[3], 1)
        aspect = width / height

        view = camera.get_view_matrix().astype('f4')
        projection = camera.get_projection_matrix(aspect).astype('f4')

        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.BLEND)
        self.ctx.viewport = viewport
        try:
            self.ctx.line_width = getattr(settings, 'DEBUG_LIGHT_GIZMO_LINE_WIDTH', 2.0)
        except AttributeError:
            pass

        self.program['view'].write(view.tobytes())
        self.program['projection'].write(projection.tobytes())

        fallback_range = getattr(settings, 'DEBUG_LIGHT_GIZMO_FALLBACK_RANGE', 15.0)

        for light in lights:
            position = np.array([
                float(light.position.x),
                float(light.position.y),
                float(light.position.z),
            ], dtype=np.float32)
            direction = np.array([
                float(light.get_direction().x),
                float(light.get_direction().y),
                float(light.get_direction().z),
            ], dtype=np.float32)

            if np.linalg.norm(direction) < 1e-5:
                direction = np.array([0.0, -1.0, 0.0], dtype=np.float32)
            else:
                direction = direction / np.linalg.norm(direction)

            if light.light_type == 'directional':
                length = max(settings.LIGHT_ORTHO_FAR, fallback_range)
            else:
                length = light.range if light.range and light.range > 0.0 else fallback_range

            color = np.array([1.0, 0.2, 0.2], dtype=np.float32)

            # Render cross at light position
            model = Matrix44.from_translation(position.tolist()).astype('f4')
            self.program['model'].write(model.tobytes())
            color_tuple = tuple(color.tolist())
            self.program['override_color'].value = color_tuple
            self.cross_vao.render(moderngl.LINES)

            # Render debug ray
            end = position + direction * length
            line_data = np.array([
                position[0], position[1], position[2], 0.0, 0.0, 0.0,
                end[0], end[1], end[2], 0.0, 0.0, 0.0,
            ], dtype='f4')
            self.line_vbo.write(line_data.tobytes())
            self.program['model'].write(self.identity.tobytes())
            self.program['override_color'].value = color_tuple
            self.line_vao.render(moderngl.LINES)

        self.ctx.line_width = 1.0
