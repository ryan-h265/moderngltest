"""
Render Pipeline

Orchestrates the complete rendering pipeline with shadow mapping.
Supports both forward and deferred rendering modes.
"""

from typing import List
import moderngl

from .shader_manager import ShaderManager
from .shadow_renderer import ShadowRenderer
from .main_renderer import MainRenderer
from .gbuffer import GBuffer
from .geometry_renderer import GeometryRenderer
from .lighting_renderer import LightingRenderer
from ..core.camera import Camera
from ..core.light import Light
from ..core.scene import Scene
from ..config.settings import RENDERING_MODE, WINDOW_SIZE


class RenderPipeline:
    """
    Complete rendering pipeline.

    Supports two rendering modes:
    - Forward: Traditional forward rendering (limited lights)
    - Deferred: Deferred rendering (unlimited lights, scalable)

    Coordinates:
    1. Shader loading
    2. Shadow map generation for all lights
    3. Scene rendering (forward or deferred mode)
    """

    def __init__(self, ctx: moderngl.Context, window):
        """
        Initialize rendering pipeline.

        Args:
            ctx: ModernGL context
            window: Window instance (for viewport access)
        """
        self.ctx = ctx
        self.window = window
        self.rendering_mode = RENDERING_MODE

        # Load shaders
        self.shader_manager = ShaderManager(ctx)

        # Shadow shaders (used by both modes)
        self.shader_manager.load_program("shadow", "shadow_depth.vert", "shadow_depth.frag")

        # Forward rendering shaders
        self.shader_manager.load_program("main", "main_lighting.vert", "main_lighting.frag")

        # Deferred rendering shaders
        self.shader_manager.load_program("geometry", "deferred_geometry.vert", "deferred_geometry.frag")
        self.shader_manager.load_program("lighting", "deferred_lighting.vert", "deferred_lighting.frag")
        self.shader_manager.load_program("ambient", "deferred_lighting.vert", "deferred_ambient.frag")

        # Create shadow renderer (used by both modes)
        self.shadow_renderer = ShadowRenderer(
            ctx,
            self.shader_manager.get("shadow")
        )

        # Create forward rendering pipeline
        self.main_renderer = MainRenderer(
            ctx,
            self.shader_manager.get("main")
        )

        # Create deferred rendering pipeline
        self.gbuffer = GBuffer(ctx, WINDOW_SIZE)
        self.geometry_renderer = GeometryRenderer(
            ctx,
            self.shader_manager.get("geometry")
        )
        self.lighting_renderer = LightingRenderer(
            ctx,
            self.shader_manager.get("lighting"),
            self.shader_manager.get("ambient")
        )

    def initialize_lights(self, lights: List[Light]):
        """
        Initialize shadow maps for lights.

        Call this once after creating lights.

        Args:
            lights: List of lights to initialize
        """
        self.shadow_renderer.initialize_light_shadow_maps(lights)

    def render_frame(self, scene: Scene, camera: Camera, lights: List[Light]):
        """
        Render a complete frame.

        Pipeline (Forward):
        1. Shadow passes (one per light)
        2. Main scene pass (with lighting and shadows)

        Pipeline (Deferred):
        1. Shadow passes (one per light)
        2. Geometry pass (write to G-Buffer)
        3. Lighting pass (accumulate all lights)

        Args:
            scene: Scene to render
            camera: Camera for view
            lights: List of lights
        """
        # Pass 1: Render shadow maps for all lights (both modes)
        self.shadow_renderer.render_shadow_maps(lights, scene)

        # Pass 2+: Render scene (mode-dependent)
        if self.rendering_mode == "deferred":
            self._render_deferred(scene, camera, lights)
        else:
            self._render_forward(scene, camera, lights)

    def _render_forward(self, scene: Scene, camera: Camera, lights: List[Light]):
        """
        Render using forward rendering.

        Args:
            scene: Scene to render
            camera: Camera for view
            lights: List of lights
        """
        self.main_renderer.render(scene, camera, lights, self.window.viewport)

    def _render_deferred(self, scene: Scene, camera: Camera, lights: List[Light]):
        """
        Render using deferred rendering.

        Args:
            scene: Scene to render
            camera: Camera for view
            lights: List of lights
        """
        # Pass 2: Geometry pass (write to G-Buffer)
        self.geometry_renderer.render(scene, camera, self.gbuffer)

        # Pass 3: Lighting pass (accumulate all lights from G-Buffer)
        self.lighting_renderer.render(lights, self.gbuffer, camera, self.window.viewport)

    def get_shader(self, name: str) -> moderngl.Program:
        """
        Get a loaded shader program.

        Args:
            name: Shader name ("shadow" or "main")

        Returns:
            Shader program
        """
        return self.shader_manager.get(name)

    def reload_shaders(self):
        """
        Reload all shaders.

        Useful for hot-reloading during development.
        (Not yet fully implemented)
        """
        # Would re-create shader manager and renderers
        raise NotImplementedError("Shader hot-reloading not yet implemented")
