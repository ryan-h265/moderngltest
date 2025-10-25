"""
Render Pipeline

Orchestrates the complete rendering pipeline with shadow mapping.
Supports both forward and deferred rendering modes.
"""

from typing import List, Tuple
import moderngl

from .shader_manager import ShaderManager
from .shadow_renderer import ShadowRenderer
from .main_renderer import MainRenderer
from .gbuffer import GBuffer
from .geometry_renderer import GeometryRenderer
from .lighting_renderer import LightingRenderer
from .ssao_renderer import SSAORenderer
from .transparent_renderer import TransparentRenderer
from .text_manager import TextManager
from .ui_renderer import UIRenderer
from .antialiasing_renderer import AntiAliasingRenderer, AAMode
from .bloom_renderer import BloomRenderer
from ..core.camera import Camera
from ..core.light import Light
from ..core.scene import Scene
from ..config.settings import (
    RENDERING_MODE,
    WINDOW_SIZE,
    SSAO_ENABLED,
    SSAO_KERNEL_SIZE,
    UI_FONT_PATH,
    UI_FONT_SIZE,
    DEBUG_OVERLAY_ENABLED,
    PROJECT_ROOT,
    BLOOM_ENABLED,
)


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
        self.shader_manager.load_program("geometry_textured", "deferred_geometry_textured.vert", "deferred_geometry_textured.frag")
        self.shader_manager.load_program("geometry_textured_skinned", "deferred_geometry_textured_skinned.vert", "deferred_geometry_textured.frag")  # Skinned meshes
        self.shader_manager.load_program("unlit", "unlit.vert", "unlit.frag")  # KHR_materials_unlit
        self.shader_manager.load_program("lighting", "deferred_lighting.vert", "deferred_lighting.frag")
        self.shader_manager.load_program("ambient", "deferred_lighting.vert", "deferred_ambient.frag")
        self.shader_manager.load_program("emissive", "deferred_lighting.vert", "deferred_emissive.frag")

        # Forward transparent shader (for alpha BLEND mode)
        self.shader_manager.load_program("transparent", "forward_transparent.vert", "forward_transparent.frag")

        # SSAO shaders
        self.shader_manager.load_program("ssao", "ssao.vert", "ssao.frag")
        self.shader_manager.load_program("ssao_blur", "ssao_blur.vert", "ssao_blur.frag")

        # Anti-aliasing shaders
        self.shader_manager.load_program("fxaa", "fxaa.vert", "fxaa.frag")
        
        # SMAA shaders (optional - handle gracefully if they don't exist)
        try:
            self.shader_manager.load_program("smaa_edge", "smaa_edge.vert", "smaa_edge.frag")
            self.shader_manager.load_program("smaa_blend", "smaa_blend.vert", "smaa_blend.frag")
            self.shader_manager.load_program("smaa_neighborhood", "smaa_neighborhood.vert", "smaa_neighborhood.frag")
        except Exception as e:
            print(f"Warning: SMAA shaders not found, SMAA will be disabled: {e}")

        # Create shadow renderer (used by both modes)
        self.shadow_renderer = ShadowRenderer(
            ctx,
            self.shader_manager.get("shadow")
        )
        self.shadow_renderer.set_screen_viewport((0, 0, WINDOW_SIZE[0], WINDOW_SIZE[1]))

        # Create forward rendering pipeline
        self.main_renderer = MainRenderer(
            ctx,
            self.shader_manager.get("main")
        )

        # Create deferred rendering pipeline
        self.gbuffer = GBuffer(ctx, WINDOW_SIZE)
        self.geometry_renderer = GeometryRenderer(
            ctx,
            self.shader_manager.get("geometry"),
            self.shader_manager.get("geometry_textured"),
            self.shader_manager.get("unlit"),
            self.shader_manager.get("geometry_textured_skinned")
        )
        self.lighting_renderer = LightingRenderer(
            ctx,
            self.shader_manager.get("lighting"),
            self.shader_manager.get("ambient"),
            self.shader_manager.get("emissive")
        )

        # Create SSAO renderer (only used in deferred mode)
        self.ssao_renderer = SSAORenderer(
            ctx,
            WINDOW_SIZE,
            self.shader_manager.get("ssao"),
            self.shader_manager.get("ssao_blur")
        ) if SSAO_ENABLED else None

        # Bloom (emissive glow) post-process
        if BLOOM_ENABLED:
            self.shader_manager.load_program("bloom_downsample", "deferred_lighting.vert", "bloom_downsample.frag")
            self.shader_manager.load_program("bloom_upsample", "deferred_lighting.vert", "bloom_upsample.frag")
            self.shader_manager.load_program("bloom_composite", "deferred_lighting.vert", "bloom_composite.frag")
            self.bloom_renderer = BloomRenderer(
                ctx,
                WINDOW_SIZE,
                self.shader_manager.get("bloom_downsample"),
                self.shader_manager.get("bloom_upsample"),
                self.shader_manager.get("bloom_composite"),
            )
        else:
            self.bloom_renderer = None

        # Create transparent renderer (for alpha BLEND mode)
        self.transparent_renderer = TransparentRenderer(
            ctx,
            self.shader_manager.get("transparent")
        )

        # Create anti-aliasing renderer with optional SMAA support
        smaa_edge = None
        smaa_blend = None
        smaa_neighborhood = None
        
        try:
            smaa_edge = self.shader_manager.get("smaa_edge")
            smaa_blend = self.shader_manager.get("smaa_blend")
            smaa_neighborhood = self.shader_manager.get("smaa_neighborhood")
        except Exception:
            pass  # SMAA shaders not available
        
        self.aa_renderer = AntiAliasingRenderer(
            ctx,
            WINDOW_SIZE,
            self.shader_manager.get("fxaa"),
            smaa_edge,
            smaa_blend,
            smaa_neighborhood
        )

        # Create UI rendering system
        self.shader_manager.load_program("ui_text", "ui_text.vert", "ui_text.frag")
        font_path = str(PROJECT_ROOT / UI_FONT_PATH)
        self.text_manager = TextManager(font_path, UI_FONT_SIZE)
        self.ui_renderer = UIRenderer(
            ctx,
            self.shader_manager.get("ui_text"),
        )
        self.viewport_size: Tuple[int, int] = tuple(self.window.size)

    def initialize_lights(self, lights: List[Light], camera: Camera = None):
        """
        Initialize shadow maps for lights with adaptive resolution.

        Call this once after creating lights.

        Args:
            lights: List of lights to initialize
            camera: Optional camera for adaptive shadow resolution calculation
        """
        camera_pos = camera.position if camera else None
        self.shadow_renderer.initialize_light_shadow_maps(lights, camera_pos)

    def render_frame(self, scene: Scene, camera: Camera, lights: List[Light], time: float = 0.0):
        """
        Render a complete frame.

        Pipeline (Forward):
        1. Shadow passes (one per light)
        2. Main scene pass (with lighting and shadows)
        3. UI overlay pass

        Pipeline (Deferred):
        1. Shadow passes (one per light)
        2. Geometry pass (write to G-Buffer)
        3. Lighting pass (accumulate all lights)
        4. UI overlay pass

        Args:
            scene: Scene to render
            camera: Camera for view
            lights: List of lights
            time: Elapsed time in seconds (used for animated effects)
        """
        # Pass 1: Render shadow maps for all lights (both modes)
        self.shadow_renderer.render_shadow_maps(lights, scene)

        # Pass 2+: Render scene (mode-dependent)
        if self.rendering_mode == "deferred":
            self._render_deferred(scene, camera, lights, time=time)
        else:
            self._render_forward(scene, camera, lights, time=time)

        # Final pass: Render UI overlay
        if DEBUG_OVERLAY_ENABLED or len(self.text_manager.get_all_layers()) > 0:
            self.ui_renderer.render(self.text_manager, self.window.size)

    def resize(self, size: Tuple[int, int]):
        """Resize internal render targets and update cached viewport size."""
        if not size or size == self.viewport_size:
            return

        width, height = size
        if width <= 0 or height <= 0:
            return

        self.viewport_size = (width, height)
        screen_viewport = (0, 0, width, height)
        self.window.viewport = screen_viewport
        self.ctx.viewport = screen_viewport
        self.shadow_renderer.set_screen_viewport(screen_viewport)

        self.gbuffer.resize(self.viewport_size)

        if self.ssao_renderer is not None:
            self.ssao_renderer.resize(self.viewport_size)

        self.aa_renderer.resize(self.viewport_size)

        if hasattr(self.transparent_renderer, "resize"):
            self.transparent_renderer.resize(self.viewport_size)

        if hasattr(self.ui_renderer, "resize"):
            self.ui_renderer.resize(self.viewport_size)

        if hasattr(self.text_manager, "refresh_layout_metrics"):
            self.text_manager.refresh_layout_metrics()

    def _render_forward(self, scene: Scene, camera: Camera, lights: List[Light], time: float = 0.0):
        """
        Render using forward rendering.

        Args:
            scene: Scene to render
            camera: Camera for view
            lights: List of lights
        """
        # Get AA render target
        render_target = self.aa_renderer.get_render_target()
        
        # Check if AA is enabled
        if render_target == self.ctx.screen:
            # No AA - render directly to screen (original behavior)
            self.main_renderer.render(scene, camera, lights, self.window.viewport, time=time)
        else:
            # AA enabled - render to AA framebuffer then resolve
            self.main_renderer.render_to_target(scene, camera, lights, self.window.viewport, render_target, time=time)
            self.aa_renderer.resolve_and_present()

    def _render_deferred(self, scene: Scene, camera: Camera, lights: List[Light], time: float = 0.0):
        """
        Render using deferred rendering.

        Args:
            scene: Scene to render
            camera: Camera for view
            lights: List of lights
        """
        # Pass 2: Geometry pass (write to G-Buffer)
        self.geometry_renderer.render(scene, camera, self.gbuffer)

        # Pass 2.5: SSAO pass (optional, if enabled)
        ssao_texture = None
        # Import settings dynamically to get current runtime value
        from ..config import settings
        if self.ssao_renderer is not None and settings.SSAO_ENABLED:
            aspect_ratio = self.window.size[0] / self.window.size[1]
            self.ssao_renderer.render(
                self.gbuffer.position_texture,
                self.gbuffer.normal_texture,
                camera.get_projection_matrix(aspect_ratio),
                radius=settings.SSAO_RADIUS,
                bias=settings.SSAO_BIAS,
                intensity=settings.SSAO_INTENSITY
            )
            ssao_texture = self.ssao_renderer.get_ssao_texture()

        # Get AA render target
        render_target = self.aa_renderer.get_render_target()

        # Pass 3: Lighting pass (accumulate all lights from G-Buffer)
        if render_target == self.ctx.screen:
            # No AA - render directly to screen (original behavior)
            apply_post_lighting = None
            if self.bloom_renderer:
                target_fbo = self.ctx.screen

                def _apply_post_lighting():
                    self.bloom_renderer.apply(
                        self.gbuffer.emissive_texture,
                        self.window.viewport,
                        target_fbo,
                    )

                apply_post_lighting = _apply_post_lighting

            self.lighting_renderer.render(
                lights,
                self.gbuffer,
                camera,
                self.window.viewport,
                ssao_texture=ssao_texture,
                apply_post_lighting=apply_post_lighting,
                time=time,
            )

            # Pass 4: Transparent pass (forward rendering for alpha BLEND objects)
            if scene.has_transparent_objects():
                shadow_maps = [light.shadow_map for light in lights]
                self.transparent_renderer.render(
                    scene,
                    camera,
                    lights,
                    self.ctx.screen,
                    shadow_maps,
                    self.window.size,
                    time=time,
                )
        else:
            # AA enabled - render to AA framebuffer then resolve
            apply_post_lighting = None
            if self.bloom_renderer:
                target_fbo = render_target

                def _apply_post_lighting():
                    self.bloom_renderer.apply(
                        self.gbuffer.emissive_texture,
                        self.window.viewport,
                        target_fbo,
                    )

                apply_post_lighting = _apply_post_lighting

            self.lighting_renderer.render_to_target(
                lights,
                self.gbuffer,
                camera,
                self.window.viewport,
                render_target,
                ssao_texture=ssao_texture,
                apply_post_lighting=apply_post_lighting,
                time=time,
            )

            # Pass 4: Transparent pass (forward rendering for alpha BLEND objects)
            # Render into AA buffer before resolving
            if scene.has_transparent_objects():
                shadow_maps = [light.shadow_map for light in lights]
                self.transparent_renderer.render(
                    scene,
                    camera,
                    lights,
                    render_target,
                    shadow_maps,
                    self.window.size,
                    time=time,
                )

            self.aa_renderer.resolve_and_present()

    def get_shader(self, name: str) -> moderngl.Program:
        """
        Get a loaded shader program.

        Args:
            name: Shader name ("shadow" or "main")

        Returns:
            Shader program
        """
        return self.shader_manager.get(name)

    def cycle_aa_mode(self):
        """Cycle to the next anti-aliasing mode"""
        if hasattr(self, 'aa_renderer'):
            mode = self.aa_renderer.cycle_aa_mode()
            print(f"Anti-aliasing mode: {self.aa_renderer.get_aa_mode_name()}")
            return mode

    def toggle_msaa(self):
        """Toggle MSAA on/off"""
        if hasattr(self, 'aa_renderer'):
            enabled = self.aa_renderer.toggle_msaa()
            mode_name = self.aa_renderer.get_aa_mode_name()
            print(f"MSAA {'enabled' if enabled else 'disabled'} - AA mode: {mode_name}")
            return enabled

    def toggle_fxaa(self):
        """Toggle FXAA on/off"""
        if hasattr(self, 'aa_renderer'):
            enabled = self.aa_renderer.toggle_fxaa()
            mode_name = self.aa_renderer.get_aa_mode_name()
            print(f"FXAA {'enabled' if enabled else 'disabled'} - AA mode: {mode_name}")
            return enabled

    def toggle_smaa(self):
        """Toggle SMAA on/off"""
        if hasattr(self, 'aa_renderer'):
            enabled = self.aa_renderer.toggle_smaa()
            mode_name = self.aa_renderer.get_aa_mode_name()
            if self.aa_renderer.smaa_renderer:
                print(f"SMAA {'enabled' if enabled else 'disabled'} - AA mode: {mode_name}")
            else:
                print("SMAA not available (shaders not loaded)")
            return enabled

    def get_aa_mode_name(self) -> str:
        """Get current anti-aliasing mode name"""
        if hasattr(self, 'aa_renderer'):
            return self.aa_renderer.get_aa_mode_name()
        return "Not Available"

    def reload_shaders(self):
        """
        Reload all shaders.

        Useful for hot-reloading during development.
        (Not yet fully implemented)
        """
        # Would re-create shader manager and renderers
        raise NotImplementedError("Shader hot-reloading not yet implemented")
