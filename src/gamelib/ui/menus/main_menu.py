"""
Main Menu

Pre-game scene selection interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import imgui

if TYPE_CHECKING:
    from ...core.scene_manager import SceneManager

from ...config.settings import WINDOW_SIZE


class MainMenu:
    """Main menu for scene selection and game start."""

    def __init__(self, scene_manager: SceneManager):
        """
        Initialize main menu.

        Args:
            scene_manager: SceneManager for loading scenes
        """
        self.scene_manager = scene_manager
        self.selected_scene: Optional[str] = None
        self.show = True

        # Set initial selection to first scene
        scenes = scene_manager.get_all_scenes()
        if scenes:
            self.selected_scene = next(iter(scenes.keys()))

    def draw(self, screen_width: int, screen_height: int) -> tuple[bool, Optional[str]]:
        """
        Draw main menu.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels

        Returns:
            Tuple of (should_continue_showing_menu, selected_scene_id_or_none)
            If selected_scene is not None, that scene should be loaded.
        """
        if not self.show:
            return False, None

        # Use game window size for menu
        window_width = int(WINDOW_SIZE[0] * 0.85)  # 85% of screen width
        window_height = int(WINDOW_SIZE[1] * 0.90)  # 90% of screen height
        imgui.set_next_window_position(
            (screen_width - window_width) / 2,
            (screen_height - window_height) / 2,
            imgui.ALWAYS,
        )
        imgui.set_next_window_size(window_width, window_height, imgui.ALWAYS)

        expanded, self.show = imgui.begin(
            "Main Menu##mainmenu",
            self.show,
            imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE,
        )

        if not expanded:
            imgui.end()
            return False, None

        # Title
        imgui.text("SELECT A SCENE")
        imgui.separator()

        scenes = self.scene_manager.get_all_scenes()
        scene_changed = False

        # Scene list with radio buttons
        if scenes:
            for scene_id, metadata in scenes.items():
                clicked = imgui.radio_button(
                    metadata.display_name, self.selected_scene == scene_id
                )
                if clicked:
                    self.selected_scene = scene_id
                    scene_changed = True

                # Show description below each item
                if metadata.description:
                    imgui.text_colored(
                        f"  {metadata.description}", 0.75, 0.75, 0.75, 1.0
                    )

            imgui.separator()

            # Show selected scene details
            if self.selected_scene and self.selected_scene in scenes:
                selected_meta = scenes[self.selected_scene]
                imgui.text("Scene Details:")
                imgui.text(f"  Name: {selected_meta.display_name}")
                if selected_meta.description:
                    imgui.text(f"  Description: {selected_meta.description}")

            imgui.separator()

            # Action buttons - auto-size based on text content
            button_height = 70
            button_padding = 30  # Padding around text
            imgui.spacing()

            # Calculate button widths based on text content
            start_game_text = "Start Game"
            quit_text = "Quit"

            start_game_width = imgui.calc_text_size(start_game_text)[0] + button_padding
            quit_width = imgui.calc_text_size(quit_text)[0] + button_padding
            button_spacing = 15
            total_button_width = start_game_width + quit_width + button_spacing

            # Center buttons horizontally
            available_width = imgui.get_content_region_available_width()
            button_x = (available_width - total_button_width) / 2
            if button_x > 0:
                imgui.set_cursor_pos_x(button_x)

            if imgui.button(start_game_text, start_game_width, button_height):
                if self.selected_scene:
                    self.show = False
                    imgui.end()
                    return False, self.selected_scene

            imgui.same_line(spacing=button_spacing)
            if imgui.button(quit_text, quit_width, button_height):
                imgui.end()
                return False, None  # Special signal to quit

        else:
            imgui.text("No scenes available!")

        imgui.end()
        return True, None
