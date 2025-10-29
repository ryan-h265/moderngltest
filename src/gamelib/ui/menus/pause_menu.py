"""
Pause Menu

In-game menu shown when game is paused.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import imgui

if TYPE_CHECKING:
    from ...core.scene_manager import SceneManager


class PauseMenu:
    """Pause menu for in-game controls."""

    def __init__(self, scene_manager: SceneManager):
        """
        Initialize pause menu.

        Args:
            scene_manager: SceneManager for scene switching
        """
        self.scene_manager = scene_manager
        self.show = False
        self.show_scene_picker = False
        self.show_settings = False
        self.selected_scene: Optional[str] = None
        self.settings_menu = None  # Will be set by main.py

    def draw(
        self, screen_width: int, screen_height: int
    ) -> tuple[bool, Optional[str]]:
        """
        Draw pause menu.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels

        Returns:
            Tuple of (should_continue_showing_menu, action_or_scene_id)
            - If second element is "resume": Resume game
            - If second element is "main_menu": Return to main menu
            - If second element is a scene ID: Switch to that scene
            - If second element is None: Continue showing menu
        """
        if not self.show:
            return False, None

        # Center window (larger to accommodate scaled text)
        window_width = 700
        window_height = 600
        imgui.set_next_window_position(
            (screen_width - window_width) / 2,
            (screen_height - window_height) / 2,
            imgui.ALWAYS,
        )
        imgui.set_next_window_size(window_width, window_height, imgui.ALWAYS)

        expanded, self.show = imgui.begin(
            "Pause Menu##pausemenu",
            self.show,
            imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE,
        )

        if not expanded:
            imgui.end()
            return self.show, None

        # Title
        imgui.text("PAUSED")
        imgui.separator()

        button_width = 200
        button_height = 40
        available_width = imgui.get_content_region_available_width()
        button_x = (available_width - button_width) / 2

        imgui.spacing()
        if button_x > 0:
            imgui.set_cursor_pos_x(button_x)

        # Resume button
        if imgui.button("Resume Game", button_width, button_height):
            self.show = False
            imgui.end()
            return False, "resume"

        if button_x > 0:
            imgui.set_cursor_pos_x(button_x)

        # Change scene button
        if imgui.button("Change Scene", button_width, button_height):
            self.show_scene_picker = True

        if button_x > 0:
            imgui.set_cursor_pos_x(button_x)

        # Settings button
        if imgui.button("Settings", button_width, button_height):
            if self.settings_menu:
                self.settings_menu.show = True
            self.show_settings = True

        if button_x > 0:
            imgui.set_cursor_pos_x(button_x)

        # Return to main menu button
        if imgui.button("Main Menu", button_width, button_height):
            self.show = False
            imgui.end()
            return False, "main_menu"

        if button_x > 0:
            imgui.set_cursor_pos_x(button_x)

        # Exit button
        if imgui.button("Exit Game", button_width, button_height):
            imgui.end()
            return False, "exit"

        imgui.end()

        # Draw scene picker if shown
        if self.show_scene_picker:
            show_picker, action = self._draw_scene_picker(screen_width, screen_height)
            if not show_picker:
                self.show_scene_picker = False
                if action and action != "cancel":
                    # Scene was selected
                    self.show = False
                    return False, action

        # Draw settings menu if shown
        if self.show_settings and self.settings_menu:
            show_settings, action = self.settings_menu.draw(screen_width, screen_height)
            if not show_settings:
                self.show_settings = False

        return self.show, None

    def _draw_scene_picker(self, screen_width: int, screen_height: int) -> tuple[bool, Optional[str]]:
        """Draw scene picker submenu."""
        window_width = 600
        window_height = 500
        imgui.set_next_window_position(
            (screen_width - window_width) / 2,
            (screen_height - window_height) / 2 - 50,
            imgui.ALWAYS,
        )
        imgui.set_next_window_size(window_width, window_height, imgui.ALWAYS)

        expanded, open_picker = imgui.begin(
            "Select Scene##scenepicker",
            True,
            imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE,
        )

        if not expanded:
            imgui.end()
            return open_picker, "cancel"

        scenes = self.scene_manager.get_all_scenes()

        if scenes:
            imgui.text("Choose a scene to load:")
            imgui.separator()

            action = None
            for scene_id, metadata in scenes.items():
                if imgui.button(
                    f"{metadata.display_name}##scene_{scene_id}",
                    imgui.get_content_region_available_width(),
                    0,
                ):
                    action = scene_id

            imgui.separator()
            button_width = 80
            button_height = 30

            available_width = imgui.get_content_region_available_width()
            button_x = (available_width - button_width) / 2

            if button_x > 0:
                imgui.set_cursor_pos_x(button_x)

            if imgui.button("Cancel", button_width, button_height):
                imgui.end()
                return False, "cancel"

            imgui.end()
            return True, action

        else:
            imgui.text("No scenes available!")
            imgui.end()
            return False, "cancel"
