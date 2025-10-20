"""
Render Pipeline

Orchestrates the complete rendering pipeline with shadow mapping.
"""

from typing import List
import moderngl

from .shader_manager import ShaderManager
from .shadow_renderer import ShadowRenderer
from .main_renderer import MainRenderer
from ..core.camera import Camera
from ..core.light import Light
from ..core.scene import Scene


class RenderPipeline:
    """
    Complete rendering pipeline.

    Coordinates:
    1. Shader loading
    2. Shadow map generation for all lights
    3. Main scene rendering with lighting and shadows
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

        # Load shaders
        self.shader_manager = ShaderManager(ctx)
        self.shader_manager.load_program("shadow", "shadow_depth.vert", "shadow_depth.frag")
        self.shader_manager.load_program("main", "main_lighting.vert", "main_lighting.frag")

        # Create renderers
        self.shadow_renderer = ShadowRenderer(
            ctx,
            self.shader_manager.get("shadow")
        )

        self.main_renderer = MainRenderer(
            ctx,
            self.shader_manager.get("main")
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

        Pipeline:
        1. Shadow passes (one per light)
        2. Main scene pass (with lighting and shadows)

        Args:
            scene: Scene to render
            camera: Camera for view
            lights: List of lights
        """
        # Pass 1: Render shadow maps for all lights
        self.shadow_renderer.render_shadow_maps(lights, scene)

        # Pass 2: Render main scene
        self.main_renderer.render(scene, camera, lights, self.window.viewport)

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
