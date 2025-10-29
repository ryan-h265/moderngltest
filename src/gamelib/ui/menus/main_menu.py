"""
Main Menu

Pre-game scene selection interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import imgui

if TYPE_CHECKING:
    from ...core.scene_manager import SceneManager


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

        # Center window (larger to accommodate scaled text)
        window_width = 1200
        window_height = 800
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
                    imgui.same_line(150)
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

            # Action buttons
            button_width = 150
            button_height = 40
            imgui.spacing()

            # Center buttons horizontally
            available_width = imgui.get_content_region_available_width()
            button_x = (available_width - button_width * 2 - 10) / 2
            if button_x > 0:
                imgui.set_cursor_pos_x(button_x)

            if imgui.button("Start Game", button_width, button_height):
                if self.selected_scene:
                    self.show = False
                    imgui.end()
                    return False, self.selected_scene

            imgui.same_line(spacing=10)
            if imgui.button("Quit", button_width, button_height):
                imgui.end()
                return False, None  # Special signal to quit

        else:
            imgui.text("No scenes available!")

        imgui.end()
        return True, None
