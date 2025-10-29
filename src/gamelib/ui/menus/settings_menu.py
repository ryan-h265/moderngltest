"""
Settings Menu

In-game settings for graphics, controls, gameplay, and UI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import imgui

if TYPE_CHECKING:
    from ...input.key_bindings import KeyBindings
    from ...rendering.render_pipeline import RenderPipeline


class SettingsMenu:
    """Settings menu with tabs for different categories."""

    def __init__(self, render_pipeline: RenderPipeline, key_bindings: KeyBindings, ui_manager):
        """
        Initialize settings menu.

        Args:
            render_pipeline: RenderPipeline for graphics settings
            key_bindings: KeyBindings for controls rebinding
            ui_manager: UIManager for theme changes
        """
        self.render_pipeline = render_pipeline
        self.key_bindings = key_bindings
        self.ui_manager = ui_manager
        self.show = False
        self.selected_tab = 0  # 0=Graphics, 1=Controls, 2=Gameplay, 3=UI

        # Settings state
        self.pending_changes = {}

    def draw(self, screen_width: int, screen_height: int) -> tuple[bool, Optional[str]]:
        """
        Draw settings menu.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels

        Returns:
            Tuple of (should_continue_showing_menu, action)
            - action can be: None (continue showing), "close" (close menu), "restart" (restart needed)
        """
        if not self.show:
            return False, None

        # Center window
        window_width = 1000
        window_height = 700
        imgui.set_next_window_position(
            (screen_width - window_width) / 2,
            (screen_height - window_height) / 2,
            imgui.ALWAYS,
        )
        imgui.set_next_window_size(window_width, window_height, imgui.ALWAYS)

        expanded, self.show = imgui.begin(
            "Settings##settings",
            self.show,
            imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE,
        )

        if not expanded:
            imgui.end()
            return False, None

        # Title
        imgui.text("SETTINGS")
        imgui.separator()

        # Tabs
        tab_width = 150
        if imgui.button("Graphics", tab_width, 40):
            self.selected_tab = 0
        imgui.same_line()
        if imgui.button("Controls", tab_width, 40):
            self.selected_tab = 1
        imgui.same_line()
        if imgui.button("Gameplay", tab_width, 40):
            self.selected_tab = 2
        imgui.same_line()
        if imgui.button("UI", tab_width, 40):
            self.selected_tab = 3

        imgui.separator()

        # Tab content
        if self.selected_tab == 0:
            self._draw_graphics_tab()
        elif self.selected_tab == 1:
            self._draw_controls_tab()
        elif self.selected_tab == 2:
            self._draw_gameplay_tab()
        elif self.selected_tab == 3:
            self._draw_ui_tab()

        imgui.separator()

        # Bottom buttons
        button_width = 120
        available_width = imgui.get_content_region_available_width()
        button_x = (available_width - button_width * 2 - 10) / 2

        imgui.spacing()
        if button_x > 0:
            imgui.set_cursor_pos_x(button_x)

        if imgui.button("Save & Close", button_width, 40):
            self._apply_settings()
            self.show = False
            imgui.end()
            return False, "close"

        imgui.same_line(spacing=10)
        if imgui.button("Cancel", button_width, 40):
            self.pending_changes.clear()
            self.show = False
            imgui.end()
            return False, "close"

        imgui.end()
        return self.show, None

    def _draw_graphics_tab(self):
        """Draw graphics settings tab."""
        imgui.text("Graphics Settings")
        imgui.separator()

        # SSAO Toggle
        ssao_enabled = self.render_pipeline.config.enable_ssao
        changed, enabled = imgui.checkbox("Enable SSAO (Screen Space Ambient Occlusion)", ssao_enabled)
        if changed:
            self.render_pipeline.config.enable_ssao = enabled
            self.pending_changes['ssao'] = enabled

        # MSAA Mode
        imgui.text("Anti-Aliasing Mode:")
        aa_modes = ["None", "MSAA 2x", "MSAA 4x", "MSAA 8x", "FXAA", "SMAA"]
        current_aa = self.render_pipeline.config.aa_mode_index
        for i, mode in enumerate(aa_modes):
            if imgui.radio_button(mode, i == current_aa):
                self.render_pipeline.config.aa_mode_index = i
                self.pending_changes['aa_mode'] = i

        # Shadow Quality
        imgui.text("Shadow Quality:")
        shadow_sizes = [
            ("Low (512x512)", 512),
            ("Medium (1024x1024)", 1024),
            ("High (2048x2048)", 2048),
            ("Ultra (4096x4096)", 4096),
        ]
        current_shadow_size = self.render_pipeline.config.shadow_map_size
        for label, size in shadow_sizes:
            if imgui.radio_button(label, current_shadow_size == size):
                self.render_pipeline.config.shadow_map_size = size
                self.pending_changes['shadow_size'] = size

        # Max Lights
        imgui.text("Max Lights (affects performance):")
        _, max_lights = imgui.slider_int(
            "##max_lights",
            self.render_pipeline.config.max_lights,
            1,
            8,
            1
        )
        if max_lights != self.render_pipeline.config.max_lights:
            self.render_pipeline.config.max_lights = max_lights
            self.pending_changes['max_lights'] = max_lights

    def _draw_controls_tab(self):
        """Draw controls rebinding tab."""
        imgui.text("Key Bindings")
        imgui.text("(Double-click to rebind a key)")
        imgui.separator()

        imgui.text_colored((0.75, 0.75, 0.75, 1.0),
            "Key rebinding UI coming in next version")
        imgui.spacing()
        imgui.text("For now, edit keybindings.json manually and restart the game.")

    def _draw_gameplay_tab(self):
        """Draw gameplay settings tab."""
        imgui.text("Gameplay Settings")
        imgui.separator()

        # Player Speed
        imgui.text("Player Movement Speed:")
        _, speed = imgui.slider_float(
            "##player_speed",
            8.0,  # default
            2.0,
            20.0,
            0.1
        )
        self.pending_changes['player_speed'] = speed

        # Mouse Sensitivity
        imgui.text("Mouse Sensitivity:")
        _, sensitivity = imgui.slider_float(
            "##mouse_sensitivity",
            0.1,  # default
            0.01,
            0.5,
            0.01
        )
        self.pending_changes['mouse_sensitivity'] = sensitivity

        # Camera FOV
        imgui.text("Camera Field of View (degrees):")
        _, fov = imgui.slider_float(
            "##camera_fov",
            45.0,  # default
            30.0,
            110.0,
            1.0
        )
        self.pending_changes['fov'] = fov

    def _draw_ui_tab(self):
        """Draw UI settings tab."""
        imgui.text("User Interface Settings")
        imgui.separator()

        # Theme Selection
        imgui.text("Color Theme:")
        themes = ["sage_green", "dark", "light", "cyberpunk"]
        current_theme = self.ui_manager.theme_manager.current_theme.name
        for theme in themes:
            if imgui.radio_button(theme, theme == current_theme):
                self.ui_manager.switch_theme(theme)
                self.pending_changes['theme'] = theme

        imgui.separator()

        # UI Scale
        imgui.text("UI Scale Factor:")
        _, scale = imgui.slider_float(
            "##ui_scale",
            self.ui_manager.theme_manager.current_theme.scale,
            1.0,
            2.5,
            0.1
        )
        if scale != self.ui_manager.theme_manager.current_theme.scale:
            self.ui_manager.theme_manager.current_theme.scale = scale
            self.ui_manager.theme_manager.apply_theme(self.ui_manager.theme_manager.current_theme)
            self.pending_changes['ui_scale'] = scale

        # Pause Dim Alpha
        imgui.text("Menu Dim Opacity:")
        _, dim_alpha = imgui.slider_float(
            "##dim_alpha",
            self.ui_manager.dim_alpha,
            0.2,
            1.0,
            0.05
        )
        if dim_alpha != self.ui_manager.dim_alpha:
            self.ui_manager.dim_alpha = dim_alpha
            self.pending_changes['dim_alpha'] = dim_alpha

    def _apply_settings(self):
        """Apply all pending settings changes."""
        # Settings are already applied live in the draw methods
        # Just clear the pending changes dict
        self.pending_changes.clear()

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self.ui_manager.switch_theme("sage_green")
        self.render_pipeline.config.enable_ssao = True
        self.render_pipeline.config.aa_mode_index = 2  # MSAA 4x
        self.render_pipeline.config.shadow_map_size = 2048
        self.render_pipeline.config.max_lights = 4
        self.pending_changes.clear()
