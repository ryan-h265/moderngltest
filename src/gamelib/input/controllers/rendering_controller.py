"""
Rendering Controller

Handles rendering-related input commands like toggling SSAO, shadows, etc.
"""

from ...rendering.render_pipeline import RenderPipeline
from ..input_commands import InputCommand
from ..input_manager import InputManager


class RenderingController:
    """
    Controller for rendering input commands.

    Registers handlers with InputManager for rendering toggles.

    Usage:
        input_manager = InputManager()
        render_pipeline = RenderPipeline(ctx, window)
        controller = RenderingController(render_pipeline, input_manager)
    """

    def __init__(self, render_pipeline: RenderPipeline, input_manager: InputManager):
        """
        Initialize rendering controller.

        Args:
            render_pipeline: RenderPipeline instance
            input_manager: InputManager to register handlers with
        """
        self.render_pipeline = render_pipeline
        self.input_manager = input_manager

        # State tracking
        self.ssao_enabled = True  # Track current SSAO state

        # Register handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register input handlers with InputManager"""
        self.input_manager.register_handler(
            InputCommand.SYSTEM_TOGGLE_SSAO,
            self.toggle_ssao
        )
        self.input_manager.register_handler(
            InputCommand.SYSTEM_CYCLE_AA_MODE,
            self.cycle_aa_mode
        )
        self.input_manager.register_handler(
            InputCommand.SYSTEM_TOGGLE_MSAA,
            self.toggle_msaa
        )
        self.input_manager.register_handler(
            InputCommand.SYSTEM_TOGGLE_FXAA,
            self.toggle_fxaa
        )
        self.input_manager.register_handler(
            InputCommand.SYSTEM_TOGGLE_SMAA,
            self.toggle_smaa
        )

    def toggle_ssao(self, delta_time: float = 0.0):
        """
        Toggle SSAO on/off.

        Args:
            delta_time: Time since last frame (unused, for handler compatibility)
        """
        # print("Toggling SSAO...")
        self.ssao_enabled = not self.ssao_enabled

        # Update the settings module dynamically
        from ...config import settings
        settings.SSAO_ENABLED = self.ssao_enabled

        # Print status message
        status = "enabled" if self.ssao_enabled else "disabled"
        print(f"SSAO {status}")

    def cycle_aa_mode(self, delta_time: float = 0.0):
        """
        Cycle through anti-aliasing modes.

        Args:
            delta_time: Time since last frame (unused, for handler compatibility)
        """
        self.render_pipeline.cycle_aa_mode()

    def toggle_msaa(self, delta_time: float = 0.0):
        """
        Toggle MSAA on/off.

        Args:
            delta_time: Time since last frame (unused, for handler compatibility)
        """
        self.render_pipeline.toggle_msaa()

    def toggle_fxaa(self, delta_time: float = 0.0):
        """
        Toggle FXAA on/off.

        Args:
            delta_time: Time since last frame (unused, for handler compatibility)
        """
        self.render_pipeline.toggle_fxaa()

    def toggle_smaa(self, delta_time: float = 0.0):
        """
        Toggle SMAA on/off.

        Args:
            delta_time: Time since last frame (unused, for handler compatibility)
        """
        self.render_pipeline.toggle_smaa()
