"""Skybox rendering utilities."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import moderngl
from moderngl_window import geometry

from ..core.camera import Camera
from ..core.skybox import Skybox


class SkyboxRenderer:
    """
    Render a skybox using multiple shader variants.

    Supports:
    - Static cubemap textures
    - Atmospheric scattering
    - Procedural sky (aurora)
    - Hybrid (atmospheric + clouds + weather)
    """

    def __init__(
        self,
        ctx: moderngl.Context,
        programs: Dict[str, moderngl.Program],
    ):
        """
        Initialize skybox renderer.

        Args:
            ctx: ModernGL context
            programs: Dictionary mapping shader variant names to shader programs
                      e.g., {"cubemap": program1, "atmospheric": program2, ...}
        """
        self.ctx = ctx
        self.programs = programs
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

        # Select appropriate shader program based on skybox variant
        shader_variant = skybox.shader_variant
        program = self.programs.get(shader_variant)

        if program is None:
            # Fallback to first available program
            if not self.programs:
                return
            program = next(iter(self.programs.values()))

        aspect_ratio = width / height
        projection = camera.get_projection_matrix(aspect_ratio)
        view = camera.get_view_matrix().astype("f4")
        view[3, 0:3] = 0.0  # Remove translation component

        rotation = skybox.rotation_matrix().astype("f4")

        # Set standard uniforms
        self._set_uniform(program, "projection", projection.astype("f4").tobytes(), "matrix")
        self._set_uniform(program, "view", view.tobytes(), "matrix")
        self._set_uniform(program, "rotation", rotation.tobytes(), "matrix")
        self._set_uniform(program, "intensity", skybox.intensity, "float")

        # Set time uniform
        time_value = float(time) if time is not None else 0.0
        self._set_uniform(program, "u_time", time_value, "float")
        self._set_uniform(program, "u_resolution", (float(width), float(height)), "vec2")

        # Get all shader uniforms from skybox
        uniforms = skybox.get_shader_uniforms()

        # Set all uniforms from skybox
        for name, value in uniforms.items():
            self._set_uniform_auto(program, name, value)

        # Bind cubemap texture
        skybox.texture.use(location=0)
        if "skybox_texture" in program:
            program["skybox_texture"].value = 0
        elif "skybox" in program:
            program["skybox"].value = 0

        # Set render state
        prev_depth_mask = self.ctx.depth_mask
        prev_depth_func = self.ctx.depth_func

        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.depth_mask = False
        self.ctx.depth_func = "<="
        self.ctx.disable(moderngl.CULL_FACE)

        try:
            self.cube.render(program)
        finally:
            self.ctx.depth_mask = prev_depth_mask
            self.ctx.depth_func = prev_depth_func
            self.ctx.enable(moderngl.CULL_FACE)

    def _set_uniform(
        self,
        program: moderngl.Program,
        name: str,
        value,
        uniform_type: str,
    ) -> None:
        """Set a uniform if it exists in the program."""
        if name not in program:
            return

        try:
            if uniform_type == "matrix":
                program[name].write(value)
            elif uniform_type == "float":
                program[name].value = float(value)
            elif uniform_type == "int":
                program[name].value = int(value)
            elif uniform_type == "vec2":
                program[name].value = tuple(float(v) for v in value)
            elif uniform_type == "vec3":
                program[name].value = tuple(float(v) for v in value)
            elif uniform_type == "vec4":
                program[name].value = tuple(float(v) for v in value)
        except (KeyError, TypeError, ValueError):
            # Silently ignore uniform errors
            pass

    def _set_uniform_auto(
        self,
        program: moderngl.Program,
        name: str,
        value,
    ) -> None:
        """Automatically detect uniform type and set it."""
        if name not in program:
            return

        try:
            if isinstance(value, (int, bool)):
                program[name].value = int(value)
            elif isinstance(value, float):
                program[name].value = float(value)
            elif isinstance(value, (tuple, list)):
                if len(value) == 2:
                    program[name].value = tuple(float(v) for v in value)
                elif len(value) == 3:
                    program[name].value = tuple(float(v) for v in value)
                elif len(value) == 4:
                    program[name].value = tuple(float(v) for v in value)
            elif isinstance(value, bytes):
                program[name].write(value)
        except (KeyError, TypeError, ValueError):
            # Silently ignore uniform errors
            pass
