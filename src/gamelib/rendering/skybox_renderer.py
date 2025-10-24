"""Skybox rendering utilities."""

from __future__ import annotations

from typing import Optional, Tuple

import moderngl
from moderngl_window import geometry

from ..core.camera import Camera
from ..core.skybox import Skybox


class SkyboxRenderer:
    """Render a skybox cube map using a dedicated shader."""

    def __init__(self, ctx: moderngl.Context, program: moderngl.Program):
        self.ctx = ctx
        self.program = program
        self.cube = geometry.cube(size=2.0)

    def render(
        self,
        camera: Camera,
        skybox: Optional[Skybox],
        viewport: Tuple[int, int, int, int],
    ) -> None:
        """Render the provided skybox using the current framebuffer."""
        if skybox is None:
            return

        _, _, width, height = viewport
        if width <= 0 or height <= 0:
            return

        aspect_ratio = width / height
        projection = camera.get_projection_matrix(aspect_ratio)
        view = camera.get_view_matrix().astype("f4")
        view[3, 0:3] = 0.0  # Remove translation component

        rotation = skybox.rotation_matrix().astype("f4")

        self.program["projection"].write(projection.astype("f4").tobytes())
        self.program["view"].write(view.tobytes())
        if "rotation" in self.program:
            self.program["rotation"].write(rotation.tobytes())
        if "intensity" in self.program:
            self.program["intensity"].value = skybox.intensity

        skybox.texture.use(location=0)
        if "skybox_texture" in self.program:
            self.program["skybox_texture"].value = 0
        elif "skybox" in self.program:
            self.program["skybox"].value = 0

        prev_depth_mask = self.ctx.depth_mask
        prev_depth_func = self.ctx.depth_func

        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.depth_mask = False
        self.ctx.depth_func = "<="
        self.ctx.disable(moderngl.CULL_FACE)

        try:
            self.cube.render(self.program)
        finally:
            self.ctx.depth_mask = prev_depth_mask
            self.ctx.depth_func = prev_depth_func
            self.ctx.enable(moderngl.CULL_FACE)
