"""UI text renderer for geometry-based quads."""

import moderngl
import numpy as np
from typing import Dict, Tuple

from .text_manager import TextManager


class UIRenderer:
    """Render prebuilt text geometry as the final overlay pass."""

    def __init__(self, ctx: moderngl.Context, shader_program: moderngl.Program):
        self.ctx = ctx
        self.program = shader_program
        self._vao_cache: Dict[str, moderngl.VertexArray] = {}
        self._vbo_cache: Dict[str, Tuple[moderngl.Buffer, moderngl.Buffer, moderngl.Buffer]] = {}

    def render(self, text_manager: TextManager, screen_size: Tuple[int, int]):
        layers = text_manager.get_all_layers()
        if not layers:
            return

        self._setup_ui_state()

        proj_matrix = self._create_ortho_matrix(screen_size)
        self.program['projection'].write(proj_matrix.tobytes())

        for layer in layers:
            geometry = text_manager.get_layer_geometry(layer)
            if not geometry or geometry['vertex_count'] == 0:
                continue

            vao = self._get_or_create_vao(layer, geometry)
            vao.render(moderngl.TRIANGLES)

        self._restore_state()

    def _get_or_create_vao(self, layer: str, geometry: Dict) -> moderngl.VertexArray:
        if layer in self._vao_cache:
            vao = self._vao_cache[layer]
            # Recreate buffers each frame to pick up geometry changes.
            vao.release()
            for buffer in self._vbo_cache[layer]:
                buffer.release()

        vertices_vbo = self.ctx.buffer(geometry['vertices'].tobytes())
        colors_vbo = self.ctx.buffer(geometry['colors'].tobytes())
        indices_vbo = self.ctx.buffer(geometry['indices'].tobytes())

        vao = self.ctx.vertex_array(
            self.program,
            [
                (vertices_vbo, '2f', 'in_position'),
                (colors_vbo, '4f', 'in_color'),
            ],
            index_buffer=indices_vbo,
        )

        self._vao_cache[layer] = vao
        self._vbo_cache[layer] = (vertices_vbo, colors_vbo, indices_vbo)
        return vao

    def _setup_ui_state(self):
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.CULL_FACE)

    def _restore_state(self):
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.CULL_FACE)
        self.ctx.disable(moderngl.BLEND)

    def _create_ortho_matrix(self, screen_size: Tuple[int, int]) -> np.ndarray:
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

    def resize(self, screen_size: Tuple[int, int]):
        pass

    def release(self):
        for vao in self._vao_cache.values():
            vao.release()
        for buffers in self._vbo_cache.values():
            for buffer in buffers:
                buffer.release()

        self._vao_cache.clear()
        self._vbo_cache.clear()
