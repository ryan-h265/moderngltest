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
        self.cube = geometry.cube(size=(2.0, 2.0, 2.0))

    def render(
        self,
        camera: Camera,
        skybox: Optional[Skybox],
        viewport: Tuple[int, int, int, int],
        *,
        time: float | None = None,
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

        # Optional procedural sky uniforms
        time_value = float(time) if time is not None else 0.0
        if "u_time" in self.program:
            self.program["u_time"].value = time_value
        if "u_resolution" in self.program:
            self.program["u_resolution"].value = (float(width), float(height))
        if "u_cameraPos" in self.program:
            pos = tuple(float(v) for v in camera.position)
            self.program["u_cameraPos"].value = pos
        if "u_auroraDir" in self.program:
            aurora_dir = skybox.get_uniform("u_auroraDir", (-0.5, -0.6, 0.9))
            self.program["u_auroraDir"].value = tuple(float(v) for v in aurora_dir)
        if "u_transitionAlpha" in self.program:
            alpha = float(skybox.get_uniform("u_transitionAlpha", 1.0))
            self.program["u_transitionAlpha"].value = alpha
        if "u_useProceduralSky" in self.program:
            self.program["u_useProceduralSky"].value = 1 if skybox.shader_variant == "aurora" else 0

        # Fog configuration (only used by procedural sky)
        if "fogEnabled" in self.program:
            self.program["fogEnabled"].value = int(skybox.get_uniform("fogEnabled", 0))
        if "fogColor" in self.program:
            fog_color = skybox.get_uniform("fogColor", (0.0, 0.0, 0.0))
            self.program["fogColor"].value = tuple(float(v) for v in fog_color)
        if "fogStart" in self.program:
            self.program["fogStart"].value = float(skybox.get_uniform("fogStart", 0.0))
        if "fogEnd" in self.program:
            self.program["fogEnd"].value = float(skybox.get_uniform("fogEnd", 1.0))
        if "fogStrength" in self.program:
            self.program["fogStrength"].value = float(skybox.get_uniform("fogStrength", 0.0))

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
