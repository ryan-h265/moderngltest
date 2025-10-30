"""
Layout Debug - Live layout editor and debug visualization

Provides:
- Live panel boundary visualization
- Interactive layout editor (adjust sizes/positions in real-time)
- Performance metrics
- Keyboard shortcuts (F12, Ctrl+Shift+S, Ctrl+Shift+R, Ctrl+Shift+D)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import imgui

if TYPE_CHECKING:
    from .layout_manager import LayoutManager


class LayoutDebugOverlay:
    """Debug overlay for live menu layout editing."""

    def __init__(self, layout_manager: LayoutManager):
        """
        Initialize debug overlay.

        Args:
            layout_manager: LayoutManager instance
        """
        self.layout_manager = layout_manager
        self.show_overlay = False
        self.show_debug_window = False
        self.show_panel_bounds = False
        self.show_performance = False

        # Editing state
        self.editing_panel: Optional[str] = None
        self.edit_x = 0
        self.edit_y = 0
        self.edit_width = 0
        self.edit_height = 0

        # Performance tracking
        self.frame_times: list[float] = []
        self.max_frames = 60

    def handle_keyboard(self, key_code: int, mods) -> bool:
        """
        Handle keyboard input for debug shortcuts.

        Shortcuts:
        - F12 (122): Toggle overlay
        - Ctrl+Shift+D: Toggle debug window
        - Ctrl+Shift+S: Save layout config
        - Ctrl+Shift+R: Reload config from disk
        - P: Toggle panel bounds

        Args:
            key_code: Keyboard key code
            mods: KeyModifiers object (from moderngl_window)

        Returns:
            True if key was handled, False otherwise
        """
        ctrl = mods.ctrl if hasattr(mods, 'ctrl') else False
        shift = mods.shift if hasattr(mods, 'shift') else False
        alt = mods.alt if hasattr(mods, 'alt') else False

        # F12 (122) - Toggle overlay
        if key_code == 122:
            self.show_overlay = not self.show_overlay
            return True

        # Ctrl+Shift+D - Toggle debug window
        if ctrl and shift and key_code == ord('D'):
            self.show_debug_window = not self.show_debug_window
            return True

        # Ctrl+Shift+S - Save config
        if ctrl and shift and key_code == ord('S'):
            self.layout_manager.save_config()
            print("✓ Layout config saved")
            return True

        # Ctrl+Shift+R - Reload config
        if ctrl and shift and key_code == ord('R'):
            if self.layout_manager.reload_config():
                print("✓ Layout config reloaded")
            else:
                print("✗ Failed to reload layout config")
            return True

        # P - Toggle panel bounds visualization
        if key_code == ord('P'):
            self.show_panel_bounds = not self.show_panel_bounds
            self.layout_manager.debug_config["show_panel_bounds"] = self.show_panel_bounds
            return True

        return False

    def draw(self, screen_width: int, screen_height: int) -> None:
        """
        Draw debug overlay and windows.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
        """
        if self.show_overlay:
            self._draw_overlay_banner(screen_width, screen_height)

        if self.show_debug_window:
            self._draw_debug_window(screen_width, screen_height)

        if self.show_panel_bounds:
            self._draw_panel_bounds(screen_width, screen_height)

    def _draw_overlay_banner(self, screen_width: int, screen_height: int) -> None:
        """Draw top banner with quick info."""
        # Top banner with stats
        banner_height = 60
        draw_list = imgui.get_window_draw_list()

        # Semi-transparent background
        draw_list.add_rect_filled(
            0, 0, screen_width, banner_height,
            imgui.get_color_u32_rgba(0.1, 0.1, 0.1, 0.8)
        )

        # Border
        draw_list.add_rect(
            0, 0, screen_width, banner_height,
            imgui.get_color_u32_rgba(0.5, 0.5, 0.5, 1.0)
        )

        # Text info
        info_text = (
            f"[DEBUG] F12: Toggle | P: Bounds | Ctrl+Shift+D: Window | "
            f"Ctrl+Shift+S: Save | Ctrl+Shift+R: Reload | Screen: {screen_width}x{screen_height}"
        )

        # Draw text in window space
        imgui.set_next_window_position(10, 10, imgui.ALWAYS)
        imgui.set_next_window_size(screen_width - 20, 40, imgui.ALWAYS)

        if imgui.begin(
            "##debug_banner",
            False,
            imgui.WINDOW_NO_BACKGROUND |
            imgui.WINDOW_NO_MOVE |
            imgui.WINDOW_NO_RESIZE |
            imgui.WINDOW_NO_TITLE_BAR |
            imgui.WINDOW_NO_SCROLLBAR
        ):
            imgui.text(info_text)
            imgui.end()

    def _draw_debug_window(self, screen_width: int, screen_height: int) -> None:
        """Draw debug control window."""
        imgui.set_next_window_position(20, 80, imgui.FIRST_USE_EVER)
        imgui.set_next_window_size(400, 500, imgui.FIRST_USE_EVER)

        expanded, self.show_debug_window = imgui.begin(
            "Layout Debug##debug_window",
            self.show_debug_window,
        )

        if not expanded:
            imgui.end()
            return

        # Panel list
        imgui.text("Enabled Panels:")
        imgui.separator()

        for panel_name, panel in self.layout_manager.get_enabled_panels().items():
            rect = self.layout_manager.get_panel_rect(
                panel_name, screen_width, screen_height
            )

            if rect:
                x, y, w, h = rect
                imgui.text(f"{panel.name} ({panel_name})")
                imgui.text(f"  Position: ({x}, {y})")
                imgui.text(f"  Size: {w}x{h}")

                # Edit button
                if imgui.button(f"Edit##panel_{panel_name}", 80, 20):
                    self.editing_panel = panel_name
                    self.edit_x = x
                    self.edit_y = y
                    self.edit_width = w
                    self.edit_height = h

                imgui.spacing()

        # Edit panel section
        if self.editing_panel:
            imgui.separator()
            imgui.text(f"Editing: {self.editing_panel}")

            # Position editors
            _, self.edit_x = imgui.input_int("X##edit_x", self.edit_x)
            _, self.edit_y = imgui.input_int("Y##edit_y", self.edit_y)
            _, self.edit_width = imgui.input_int("Width##edit_w", self.edit_width)
            _, self.edit_height = imgui.input_int("Height##edit_h", self.edit_height)

            # Buttons
            if imgui.button("Save Changes##save_edit", 100, 20):
                self._apply_panel_edit()

            imgui.same_line()
            if imgui.button("Cancel##cancel_edit", 100, 20):
                self.editing_panel = None

        # Config controls
        imgui.separator()
        imgui.text("Config Controls:")

        if imgui.button("Reload Config##reload", 150, 20):
            if self.layout_manager.reload_config():
                print("✓ Config reloaded")

        imgui.same_line()
        if imgui.button("Save Config##save", 150, 20):
            if self.layout_manager.save_config():
                print("✓ Config saved")

        # Debug settings
        imgui.separator()
        imgui.text("Debug Settings:")

        changed, self.show_panel_bounds = imgui.checkbox(
            "Show Panel Bounds", self.show_panel_bounds
        )
        if changed:
            self.layout_manager.debug_config["show_panel_bounds"] = self.show_panel_bounds

        changed, self.show_performance = imgui.checkbox(
            "Show Performance", self.show_performance
        )
        if changed:
            self.layout_manager.debug_config["show_performance"] = self.show_performance

        # Layout info
        imgui.separator()
        imgui.text("Layout Info:")
        debug_info = self.layout_manager.debug_info(screen_width, screen_height)
        imgui.text_wrapped(debug_info)

        imgui.end()

    def _draw_panel_bounds(self, screen_width: int, screen_height: int) -> None:
        """Draw outlines around all panels."""
        draw_list = imgui.get_window_draw_list()

        for panel_name, panel in self.layout_manager.get_enabled_panels().items():
            rect = self.layout_manager.get_panel_rect(
                panel_name, screen_width, screen_height
            )

            if rect:
                x, y, w, h = rect

                # Draw rectangle outline
                color = imgui.get_color_u32_rgba(0.0, 1.0, 0.0, 1.0)
                draw_list.add_rect(x, y, x + w, y + h, color, 2.0)

                # Draw name label
                draw_list.add_text(x + 5, y + 5, color, panel.name)

                # Draw dimensions
                dim_text = f"{w}x{h}"
                draw_list.add_text(x + 5, y + h - 15, color, dim_text)

    def _apply_panel_edit(self) -> None:
        """Apply panel edits to layout manager."""
        if not self.editing_panel:
            return

        panel = self.layout_manager.get_panel_layout(self.editing_panel)
        if not panel:
            return

        try:
            # Update position and size
            panel.position.x = self.edit_x
            panel.position.y = self.edit_y
            panel.size.width = self.edit_width
            panel.size.height = self.edit_height

            print(f"✓ Updated {self.editing_panel}")
            self.editing_panel = None

        except Exception as e:
            print(f"✗ Error applying edit: {e}")

    def record_frame_time(self, frame_time: float) -> None:
        """
        Record frame render time for performance tracking.

        Args:
            frame_time: Frame time in milliseconds
        """
        self.frame_times.append(frame_time)
        if len(self.frame_times) > self.max_frames:
            self.frame_times.pop(0)

    def get_average_frame_time(self) -> float:
        """Get average frame time in milliseconds."""
        if not self.frame_times:
            return 0.0
        return sum(self.frame_times) / len(self.frame_times)
