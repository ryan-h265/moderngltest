"""
Tone Mapping Renderer

Applies exposure and tone mapping curves to HDR color buffers.
"""

from typing import Tuple
import moderngl
import numpy as np

from ..config import settings


class ToneMappingRenderer:
    """Applies tone mapping and gamma correction to an HDR texture."""

    def __init__(self, ctx: moderngl.Context, program: moderngl.Program) -> None:
        self.ctx = ctx
        self.program = program

        self.exposure = settings.HDR_DEFAULT_EXPOSURE
        self.min_exposure = settings.HDR_MIN_EXPOSURE
        self.max_exposure = settings.HDR_MAX_EXPOSURE
        self.auto_enabled = settings.HDR_AUTO_EXPOSURE
        self.auto_speed = settings.HDR_AUTO_EXPOSURE_SPEED
        self.auto_key = settings.HDR_AUTO_EXPOSURE_KEY
        self.operator = settings.TONEMAP_OPERATOR

        self._quad_vbo = None
        self._quad_vao = None
        self._create_fullscreen_quad()

    # ------------------------------------------------------------------
    def _create_fullscreen_quad(self) -> None:
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
        self._quad_vao = self.ctx.vertex_array(
            self.program,
            [(self._quad_vbo, "2f", "in_position")],
        )

    # ------------------------------------------------------------------
    def set_exposure(self, exposure: float) -> None:
        self.exposure = float(np.clip(exposure, self.min_exposure, self.max_exposure))

    # ------------------------------------------------------------------
    def update_auto_exposure(self, hdr_texture: moderngl.Texture, dt: float) -> None:
        """
        Very simple auto-exposure: samples mip level 5 of the HDR texture to
        approximate average luminance and moves current exposure toward target.
        """
        if not self.auto_enabled:
            return

        max_levels = getattr(hdr_texture, "levels", 1)
        mip_level = int(max(0, min(5, max_levels - 1)))

        try:
            pixels = hdr_texture.read(level=mip_level, dtype="f4")
        except Exception:
            pixels = hdr_texture.read(dtype="f4")
        if not pixels:
            return

        data = np.frombuffer(pixels, dtype=np.float32)
        if data.size == 0:
            return

        avg_luminance = float(np.mean(data.reshape(-1, 4)[:, :3], axis=0).mean())
        target_exposure = self.auto_key / max(avg_luminance, 1e-4)

        lerp = 1.0 - np.exp(-self.auto_speed * dt)
        self.exposure = float(
            np.clip(
                (1.0 - lerp) * self.exposure + lerp * target_exposure,
                self.min_exposure,
                self.max_exposure,
            )
        )

    # ------------------------------------------------------------------
    def apply(
        self,
        hdr_texture: moderngl.Texture,
        target_fbo: moderngl.Framebuffer,
        viewport: Tuple[int, int, int, int],
        delta_time: float = 0.0,
    ) -> None:
        if self.auto_enabled:
            self.update_auto_exposure(hdr_texture, delta_time)

        target_fbo.use()
        self.ctx.viewport = viewport
        self.ctx.disable(moderngl.DEPTH_TEST)

        hdr_texture.use(location=0)
        if "hdr_texture" in self.program:
            self.program["hdr_texture"].value = 0

        if "exposure" in self.program:
            self.program["exposure"].value = self.exposure

        if "operator_id" in self.program:
            operator_map = {"ACES": 0, "REINHARD": 1, "UNCHARTED2": 2}
            self.program["operator_id"].value = operator_map.get(self.operator.upper(), 0)

        self._quad_vao.render(moderngl.TRIANGLES)
