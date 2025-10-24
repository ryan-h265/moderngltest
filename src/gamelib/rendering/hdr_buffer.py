"""
HDR Framebuffer utilities.

Provides a reusable floating-point framebuffer for high dynamic range rendering.
"""

from typing import Tuple
import moderngl


class HDRFramebuffer:
    """Floating-point framebuffer used as the primary lighting target."""

    def __init__(
        self,
        ctx: moderngl.Context,
        size: Tuple[int, int],
        color_format: str = "f2",
    ) -> None:
        self.ctx = ctx
        self.size = size
        self.color_format = color_format

        self.color_texture: moderngl.Texture = None
        self.depth_texture: moderngl.Texture = None
        self.fbo: moderngl.Framebuffer = None

        self._create_resources()

    # ------------------------------------------------------------------
    def _create_resources(self) -> None:
        width, height = self.size

        if self.fbo:
            self.release()

        self.color_texture = self.ctx.texture(
            (width, height),
            components=4,
            dtype=self.color_format,
        )
        self.color_texture.filter = moderngl.LINEAR, moderngl.LINEAR
        self.color_texture.repeat_x = False
        self.color_texture.repeat_y = False

        self.depth_texture = self.ctx.depth_texture(self.size)
        self.depth_texture.filter = moderngl.NEAREST, moderngl.NEAREST

        self.fbo = self.ctx.framebuffer(
            color_attachments=[self.color_texture],
            depth_attachment=self.depth_texture,
        )

    # ------------------------------------------------------------------
    def resize(self, size: Tuple[int, int]) -> None:
        if size == self.size:
            return

        self.size = size
        self._create_resources()

    # ------------------------------------------------------------------
    def release(self) -> None:
        if self.fbo:
            self.fbo.release()
            self.fbo = None
        if self.color_texture:
            self.color_texture.release()
            self.color_texture = None
        if self.depth_texture:
            self.depth_texture.release()
            self.depth_texture = None

