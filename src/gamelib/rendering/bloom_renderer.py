"""Bloom Renderer

Implements a multi-pass bloom post-process using emissive textures as the
bright source. The renderer extracts bright regions, downsamples them across
multiple mip levels, performs separable-like filtering during upsampling, and
finally composites the blurred result additively onto the lighting buffer.

The implementation follows a common industry approach based on a dual-filter
downsample/upsample chain. Quality and performance can be tuned through the
runtime configuration values exposed in :mod:`src.gamelib.config.settings`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import moderngl
import numpy as np

from ..config import settings


@dataclass
class _BloomLevel:
    """Container storing textures and framebuffers for a bloom mip level."""

    size: Tuple[int, int]
    downsample_tex: moderngl.Texture
    downsample_fbo: moderngl.Framebuffer
    upsample_tex: moderngl.Texture
    upsample_fbo: moderngl.Framebuffer


class BloomRenderer:
    """Bloom post-processing pipeline.

    Parameters are driven via the global configuration module so they can be
    tweaked without modifying the renderer code. The renderer expects the input
    emissive texture to contain HDR values (e.g., from the deferred G-Buffer).
    """

    def __init__(
        self,
        ctx: moderngl.Context,
        size: Tuple[int, int],
        downsample_program: moderngl.Program,
        upsample_program: moderngl.Program,
        composite_program: moderngl.Program,
    ) -> None:
        self.ctx = ctx
        self.size = size
        self.downsample_program = downsample_program
        self.upsample_program = upsample_program
        self.composite_program = composite_program

        self.threshold = settings.BLOOM_THRESHOLD
        self.soft_knee = settings.BLOOM_SOFT_KNEE
        self.intensity = settings.BLOOM_INTENSITY
        self.filter_radius = settings.BLOOM_FILTER_RADIUS
        self.tint = settings.BLOOM_TINT
        self.max_levels = settings.BLOOM_MAX_LEVELS

        self.levels: List[_BloomLevel] = []

        self._quad_vbo = None
        self._downsample_vao = None
        self._upsample_vao = None
        self._composite_vao = None

        self._create_fullscreen_quad()
        self._allocate_levels(size)

    # ------------------------------------------------------------------
    # Resource management
    # ------------------------------------------------------------------
    def _create_fullscreen_quad(self) -> None:
        """Create VAOs shared by all bloom passes."""

        vertices = np.array(
            [
                -1.0, -1.0,
                1.0, -1.0,
                -1.0, 1.0,
                -1.0, 1.0,
                1.0, -1.0,
                1.0, 1.0,
            ],
            dtype="f4",
        )

        self._quad_vbo = self.ctx.buffer(vertices.tobytes())
        self._downsample_vao = self.ctx.vertex_array(
            self.downsample_program,
            [(self._quad_vbo, "2f", "in_position")],
        )
        self._upsample_vao = self.ctx.vertex_array(
            self.upsample_program,
            [(self._quad_vbo, "2f", "in_position")],
        )
        self._composite_vao = self.ctx.vertex_array(
            self.composite_program,
            [(self._quad_vbo, "2f", "in_position")],
        )

    def _allocate_levels(self, size: Tuple[int, int]) -> None:
        """Allocate bloom mip-chain resources for the current viewport size."""

        self._release_levels()

        width, height = size
        width = max(width, 1)
        height = max(height, 1)

        self.levels = []

        for _ in range(self.max_levels):
            width = max(1, width // 2)
            height = max(1, height // 2)

            down_tex = self.ctx.texture((width, height), components=3, dtype="f2")
            down_tex.filter = moderngl.LINEAR, moderngl.LINEAR
            down_tex.repeat_x = False
            down_tex.repeat_y = False
            down_fbo = self.ctx.framebuffer(color_attachments=[down_tex])

            up_tex = self.ctx.texture((width, height), components=3, dtype="f2")
            up_tex.filter = moderngl.LINEAR, moderngl.LINEAR
            up_tex.repeat_x = False
            up_tex.repeat_y = False
            up_fbo = self.ctx.framebuffer(color_attachments=[up_tex])

            self.levels.append(
                _BloomLevel(
                    size=(width, height),
                    downsample_tex=down_tex,
                    downsample_fbo=down_fbo,
                    upsample_tex=up_tex,
                    upsample_fbo=up_fbo,
                )
            )

    def _release_levels(self) -> None:
        """Release GPU resources for all mip levels."""

        for level in self.levels:
            level.downsample_fbo.release()
            level.downsample_tex.release()
            level.upsample_fbo.release()
            level.upsample_tex.release()
        self.levels = []

    def resize(self, size: Tuple[int, int]) -> None:
        """Resize bloom render targets when the viewport changes."""

        if size != self.size:
            self.size = size
            self._allocate_levels(size)

    # ------------------------------------------------------------------
    # Bloom passes
    # ------------------------------------------------------------------
    def apply(
        self,
        emissive_texture: moderngl.Texture,
        viewport: Tuple[int, int, int, int],
        target: moderngl.Framebuffer,
    ) -> None:
        """Run the bloom pipeline and composite the blurred glow.

        Args:
            emissive_texture: HDR emissive texture sourced from the G-Buffer.
            viewport: Target viewport (x, y, width, height).
            target: Framebuffer to composite the bloom result onto.
        """

        if not self.levels:
            return

        _, _, width, height = viewport
        if width <= 0 or height <= 0:
            return

        self.resize((width, height))

        self.ctx.disable(moderngl.DEPTH_TEST)

        # ------------------------------------------------------------------
        # Downsample chain: progressively shrink emissive texture while
        # applying a brightness threshold on the first level.
        # ------------------------------------------------------------------
        current_source = emissive_texture
        for index, level in enumerate(self.levels):
            level.downsample_fbo.use()
            self.ctx.viewport = (0, 0, *level.size)

            current_source.use(location=0)
            self.downsample_program["sourceTexture"].value = 0
            self.downsample_program["threshold"].value = self.threshold
            self.downsample_program["softKnee"].value = self.soft_knee
            self.downsample_program["useThreshold"].value = int(index == 0)

            self._downsample_vao.render(moderngl.TRIANGLES)
            current_source = level.downsample_tex

        # ------------------------------------------------------------------
        # Upsample chain: reconstruct blur from smallest mip back to the
        # largest, combining each level with its parent.
        # ------------------------------------------------------------------
        next_texture = None
        for index in reversed(range(len(self.levels))):
            level = self.levels[index]
            level.upsample_fbo.use()
            self.ctx.viewport = (0, 0, *level.size)

            level.downsample_tex.use(location=0)
            self.upsample_program["baseTexture"].value = 0
            self.upsample_program["filterRadius"].value = self.filter_radius

            has_previous = next_texture is not None
            self.upsample_program["hasBloomTexture"].value = int(has_previous)
            if has_previous:
                next_texture.use(location=1)
                self.upsample_program["bloomTexture"].value = 1

            self._upsample_vao.render(moderngl.TRIANGLES)
            next_texture = level.upsample_tex

        # ------------------------------------------------------------------
        # Composite: add bloom texture back onto lighting buffer.
        # ------------------------------------------------------------------
        target.use()
        self.ctx.viewport = viewport

        if next_texture is None:
            return

        next_texture.use(location=0)
        self.composite_program["bloomTexture"].value = 0
        self.composite_program["intensity"].value = self.intensity
        self.composite_program["tint"].value = self.tint

        self._composite_vao.render(moderngl.TRIANGLES)

