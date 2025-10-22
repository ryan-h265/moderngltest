"""
Debug Overlay

Collects and displays engine statistics as on-screen text.
Provides real-time information about FPS, camera, rendering, lights, etc.
"""

from typing import List, Optional
from ..core.camera import Camera
from ..core.light import Light
from ..core.scene import Scene
from ..rendering.text_manager import TextManager
from ..config.settings import (
    DEBUG_POSITION,
    DEBUG_LINE_SPACING,
    DEBUG_TEXT_COLOR,
    DEBUG_TEXT_SCALE,
    RENDERING_MODE,
    SSAO_ENABLED,
    ENABLE_FRUSTUM_CULLING,
    SHADOW_MAP_SIZE
)


class DebugOverlay:
    """
    Manages debug overlay display.

    Collects engine statistics and updates TextManager with formatted output.
    """

    def __init__(self, text_manager: TextManager):
        """
        Initialize debug overlay.

        Args:
            text_manager: TextManager for rendering text
        """
        self.text_manager = text_manager
        self.text_ids = []  # Track text IDs for updates

        # Frame time tracking for averaging
        self.frame_times = []
        self.max_frame_samples = 60  # Average over 60 frames

    def update(self, fps: float, frametime: float, camera: Camera,
               lights: List[Light], scene: Optional[Scene] = None):
        """
        Update debug overlay with current stats.

        Args:
            fps: Current frames per second
            frametime: Frame time in seconds
            camera: Camera instance
            lights: List of lights
            scene: Optional scene for object count
        """
        # Track frame times
        self.frame_times.append(frametime * 1000)  # Convert to ms
        if len(self.frame_times) > self.max_frame_samples:
            self.frame_times.pop(0)

        # Calculate average frame time
        avg_frametime = sum(self.frame_times) / len(self.frame_times)

        # Gather stats
        stats_lines = self._gather_stats(fps, avg_frametime, camera, lights, scene)

        # Update text display
        self._update_display(stats_lines)

    def _gather_stats(self, fps: float, avg_frametime: float, camera: Camera,
                      lights: List[Light], scene: Optional[Scene]) -> List[str]:
        """
        Gather all statistics into formatted lines.

        Args:
            fps: Current FPS
            avg_frametime: Average frame time in ms
            camera: Camera instance
            lights: List of lights
            scene: Optional scene

        Returns:
            List of formatted stat lines
        """
        lines = []

        # Performance stats
        lines.append(f"FPS: {fps:.1f} ({avg_frametime:.2f}ms)")

        # Rendering mode
        from ..config import settings
        render_mode = settings.RENDERING_MODE.capitalize()
        ssao_status = "ON" if settings.SSAO_ENABLED else "OFF"
        lines.append(f"Mode: {render_mode} | SSAO: {ssao_status}")

        # Camera info
        cam_pos = camera.position
        lines.append(f"Cam: [{cam_pos[0]:.1f}, {cam_pos[1]:.1f}, {cam_pos[2]:.1f}]")
        lines.append(f"Pitch: {camera.pitch:.1f}° | Yaw: {camera.yaw:.1f}°")

        # Light info
        shadow_res = SHADOW_MAP_SIZE
        lines.append(f"Lights: {len(lights)} | Shadows: {shadow_res}x{shadow_res}")

        # Scene info
        if scene:
            total_objects = len(scene.objects)
            # Note: We don't have culling stats here, but we could add them
            culling_status = "ON" if ENABLE_FRUSTUM_CULLING else "OFF"
            lines.append(f"Objects: {total_objects} | Culling: {culling_status}")

        # Controls hint
        lines.append("")
        lines.append("ESC: Release mouse | T: Toggle SSAO")

        return lines

    def _update_display(self, lines: List[str]):
        """
        Update text display with stats.

        Args:
            lines: List of text lines to display
        """
        # Remove old text objects
        for text_id in self.text_ids:
            self.text_manager.remove_text(text_id)
        self.text_ids.clear()

        # Add new text objects
        x, y = DEBUG_POSITION
        for i, line in enumerate(lines):
            text_id = self.text_manager.add_text(
                text=line,
                position=(x, y + i * DEBUG_LINE_SPACING),
                color=DEBUG_TEXT_COLOR,
                scale=DEBUG_TEXT_SCALE,
                layer="debug"
            )
            self.text_ids.append(text_id)

    def clear(self):
        """Clear all debug text."""
        for text_id in self.text_ids:
            self.text_manager.remove_text(text_id)
        self.text_ids.clear()
