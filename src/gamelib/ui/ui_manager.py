"""
ImGui UI Manager

Central manager for all UI operations, ImGui integration, and state management.
Handles initialization, event routing, and menu lifecycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import imgui
from imgui.integrations.opengl import ProgrammablePipelineRenderer
import moderngl

from ..input.input_context import InputContext, InputContextManager
from .theme import ThemeManager

if TYPE_CHECKING:
    from ..input.input_manager import InputManager


class UIManager:
    """
    Central UI manager for ImGui integration.

    Responsibilities:
    - Initialize and manage ImGui context
    - Route input events to ImGui
    - Apply themes and styling
    - Manage menu state and visibility
    - Coordinate with input system
    """

    def __init__(
        self,
        ctx: moderngl.Context,
        window_size: tuple[int, int],
        theme_name: str = "sage_green",
    ):
        """
        Initialize UI manager.

        Args:
            ctx: ModernGL context
            window_size: Initial window size (width, height)
            theme_name: Initial theme name
        """
        self.ctx = ctx
        self.window_size = window_size
        self.width, self.height = window_size

        # Initialize ImGui
        imgui.create_context()
        io = imgui.get_io()
        io.display_size = self.window_size
        io.ini_file_name = None  # Disable ini file (use our config)

        # Create OpenGL renderer
        self.renderer = ProgrammablePipelineRenderer()

        # Theme system
        self.theme_manager = ThemeManager(theme_name)

        # UI state
        self.is_paused = False
        self.show_main_menu = False
        self.show_pause_menu = False
        self.show_settings_menu = False
        self.show_scene_picker = False
        self.show_object_inspector = False

        # Selected object for editor
        self.selected_object = None

        # Input manager reference (set later)
        self.input_manager: Optional[InputManager] = None

    def set_input_manager(self, input_manager: InputManager) -> None:
        """Set reference to input manager for context switching."""
        self.input_manager = input_manager

    def handle_mouse_position(self, x: float, y: float) -> None:
        """Update ImGui mouse position."""
        io = imgui.get_io()
        io.mouse_pos = (x, y)

    def handle_mouse_button(self, button: int, pressed: bool) -> None:
        """
        Handle mouse button events.

        Args:
            button: Button code (0=left, 1=right, 2=middle)
            pressed: True if pressed, False if released
        """
        io = imgui.get_io()
        if button < 3:
            io.mouse_down[button] = pressed

    def handle_mouse_scroll(self, x_offset: float, y_offset: float) -> None:
        """Handle mouse scroll."""
        io = imgui.get_io()
        io.mouse_wheel_h = x_offset
        io.mouse_wheel = y_offset

    def handle_keyboard_event(self, key: int, pressed: bool) -> None:
        """
        Handle keyboard events.

        Args:
            key: Key code
            pressed: True if pressed, False if released
        """
        io = imgui.get_io()
        if key < len(io.keys_down):
            io.keys_down[key] = pressed

    def handle_character_input(self, char: str) -> None:
        """Handle text input."""
        io = imgui.get_io()
        io.add_input_character(ord(char))

    def resize(self, width: int, height: int) -> None:
        """
        Handle window resize.

        Args:
            width: New window width
            height: New window height
        """
        self.width = width
        self.height = height
        self.window_size = (width, height)
        io = imgui.get_io()
        io.display_size = (width, height)

    def pause_game(self) -> None:
        """Pause the game and show pause menu."""
        if self.input_manager:
            self.input_manager.context_manager.push_context(InputContext.MENU)
        self.is_paused = True
        self.show_pause_menu = True

    def resume_game(self) -> None:
        """Resume the game and hide pause menu."""
        if self.input_manager:
            self.input_manager.context_manager.pop_context()
        self.is_paused = False
        self.show_pause_menu = False

    def show_main_menu_screen(self) -> None:
        """Show main menu (before game starts)."""
        if self.input_manager:
            self.input_manager.context_manager.set_context(InputContext.MENU)
        self.show_main_menu = True

    def hide_main_menu_screen(self) -> None:
        """Hide main menu and return to gameplay."""
        if self.input_manager:
            self.input_manager.context_manager.set_context(InputContext.GAMEPLAY)
        self.show_main_menu = False

    def toggle_pause_menu(self) -> None:
        """Toggle pause menu on/off."""
        if self.is_paused:
            self.resume_game()
        else:
            self.pause_game()

    def is_input_captured_by_imgui(self) -> bool:
        """
        Check if ImGui has captured input focus.

        Returns True if mouse or keyboard input should be routed to ImGui.
        """
        io = imgui.get_io()
        return io.want_capture_mouse or io.want_capture_keyboard

    def start_frame(self) -> None:
        """
        Called at the start of each frame.

        Sets up ImGui state for the new frame.
        """
        io = imgui.get_io()
        imgui.new_frame()

    def end_frame(self) -> None:
        """
        Called at the end of each frame.

        Renders ImGui drawlist.
        """
        imgui.end_frame()
        imgui.render()

    def render(self) -> None:
        """Render ImGui to screen."""
        imgui.render()
        self.renderer.render(imgui.get_draw_data())

    def shutdown(self) -> None:
        """Clean up ImGui resources."""
        self.renderer.shutdown()

    def switch_theme(self, theme_name: str) -> None:
        """
        Switch to a different theme.

        Args:
            theme_name: Name of theme to switch to
        """
        self.theme_manager.switch_theme(theme_name)
