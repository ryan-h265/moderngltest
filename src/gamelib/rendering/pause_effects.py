"""
Pause Effects Renderer

Renders visual effects when game is paused (dim overlay, optional blur).
"""

from __future__ import annotations

import moderngl
import numpy as np
from pyrr import Matrix44


class PauseEffects:
    """Renders pause menu visual effects (dim overlay, blur, etc.)."""

    OVERLAY_VERTEX_SHADER = """
    #version 410

    in vec2 in_position;

    uniform mat4 projection;

    void main() {
        gl_Position = projection * vec4(in_position, 0.0, 1.0);
    }
    """

    OVERLAY_FRAGMENT_SHADER = """
    #version 410

    out vec4 out_color;

    uniform vec4 overlay_color;

    void main() {
        out_color = overlay_color;
    }
    """

    def __init__(self, ctx: moderngl.Context, window_size: tuple[int, int]):
        """
        Initialize pause effects renderer.

        Args:
            ctx: ModernGL context
            window_size: Window size (width, height)
        """
        self.ctx = ctx
        self.window_size = window_size
        self.width, self.height = window_size

        # Create full-screen quad for overlay (just positions, no texcoords)
        quad_data = np.array([
            # Position
            -1.0, -1.0,
             1.0, -1.0,
             1.0,  1.0,
            -1.0,  1.0,
        ], dtype='f4')

        self.vbo = self.ctx.buffer(quad_data)

        # Compile shader program
        self.program = self.ctx.program(
            vertex_shader=self.OVERLAY_VERTEX_SHADER,
            fragment_shader=self.OVERLAY_FRAGMENT_SHADER,
        )

        # Create VAO
        self.vao = self.ctx.vertex_array(
            self.program,
            [
                (self.vbo, '2f', 'in_position'),
            ],
        )

        # Set up orthographic projection
        self._update_projection()

    def _update_projection(self):
        """Update orthographic projection matrix for current window size."""
        proj = Matrix44.orthogonal_projection(0, self.width, self.height, 0, -1, 1)
        self.program['projection'].write(proj.astype('f4'))

    def resize(self, width: int, height: int):
        """
        Handle window resize.

        Args:
            width: New window width
            height: New window height
        """
        self.width = width
        self.height = height
        self.window_size = (width, height)
        self._update_projection()

    def render_dim_overlay(self, dim_alpha: float = 0.6):
        """
        Render semi-transparent dim overlay.

        Args:
            dim_alpha: Overlay alpha (0.0-1.0). 0.6 = 60% dim
        """
        # Enable blending for semi-transparent overlay
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        # Set overlay color (black with variable alpha)
        self.program['overlay_color'].value = (0.0, 0.0, 0.0, dim_alpha)

        # Render overlay quad (6 vertices = 2 triangles)
        self.vao.render(moderngl.TRIANGLES, vertices=6)

    def shutdown(self):
        """Clean up resources."""
        self.vao.release()
        self.vbo.release()
        self.program.release()
