"""Renderer for textured HUD/UI sprites."""

from __future__ import annotations

from typing import Tuple

import moderngl
import numpy as np

from .icon_manager import IconManager


class UISpriteRenderer:
    """Render icon quads in screen space as part of the UI pass."""

    def __init__(self, ctx: moderngl.Context, shader_program: moderngl.Program):
        self.ctx = ctx
        self.program = shader_program

    def render(self, icon_manager: IconManager, screen_size: Tuple[int, int]):
        if not icon_manager.has_icons():
            return

        self._setup_state()
        projection = self._create_ortho_matrix(screen_size)
        self.program["projection"].write(projection.tobytes())

        for layer in icon_manager.get_all_layers():
            draws = icon_manager.get_draw_data_for_layer(layer)
            for draw in draws:
                self._render_icon(draw)

        self._restore_state()

    def _render_icon(self, draw):
        # Create quad geometry (two triangles)
        x, y = draw.position
        width, height = draw.size

        vertices = np.array(
            [
                x, y, 0.0, 0.0, *draw.color,
                x + width, y, 1.0, 0.0, *draw.color,
                x + width, y + height, 1.0, 1.0, *draw.color,
                x, y + height, 0.0, 1.0, *draw.color,
            ],
            dtype="f4",
        )
        indices = np.array([0, 1, 2, 0, 2, 3], dtype="i4")

        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())

        vao = self.ctx.vertex_array(
            self.program,
            [
                (vbo, "2f 2f 4f", "in_position", "in_uv", "in_color"),
            ],
            index_buffer=ibo,
        )

        draw.texture.use(location=0)
        self.program["sprite_texture"].value = 0
        vao.render(moderngl.TRIANGLES)

        vao.release()
        vbo.release()
        ibo.release()

    def _setup_state(self):
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.CULL_FACE)

    def _restore_state(self):
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.CULL_FACE)
        self.ctx.disable(moderngl.BLEND)

    def _create_ortho_matrix(self, screen_size: Tuple[int, int]):
        width, height = screen_size
        from pyrr import matrix44

        return matrix44.create_orthogonal_projection_matrix(
            0.0,
            float(width),
            float(height),
            0.0,
            -1.0,
            1.0,
            dtype=np.float32,
        )

    def resize(self, _screen_size: Tuple[int, int]):
        # Stateless renderer; nothing to do other than maintain API symmetry.
        return

    def release(self):
        # No persistent buffers to release; method kept for parity with other renderers.
        return
