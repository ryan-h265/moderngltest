"""
Debug Overlay

Collects and displays engine statistics as on-screen text.
Provides real-time information about FPS, camera, rendering, lights, etc.
"""

from typing import Dict, List, Optional, TYPE_CHECKING
from ..core.camera import Camera
from ..core.light import Light
from ..core.scene import Scene
from ..config.settings import (
    DEBUG_POSITION,
    DEBUG_LINE_SPACING,
    DEBUG_TEXT_COLOR,
    DEBUG_TEXT_SCALE,
    RENDERING_MODE,
    SSAO_ENABLED,
    ENABLE_FRUSTUM_CULLING,
    SHADOW_MAP_SIZE,
    DEBUG_SHOW_CULLED_OBJECTS,
    DEBUG_SHADOW_RENDERING,
    DEBUG_OVERLAY_BACKGROUND_COLOR,
    DEBUG_OVERLAY_BACKGROUND_PADDING,
)

if TYPE_CHECKING:
    from ..rendering.render_pipeline import RenderPipeline


class DebugOverlay:
    """
    Manages debug overlay display.

    Collects engine statistics and updates TextManager with formatted output.
    """

    def __init__(self, pipeline: "RenderPipeline"):
        """
        Initialize debug overlay.

        Args:
            pipeline: RenderPipeline for accessing text manager and render stats
        """
        self.pipeline = pipeline
        self.text_manager = pipeline.text_manager
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
        lines.append(f"Cam Pos.: [{cam_pos[0]:.1f}, {cam_pos[1]:.1f}, {cam_pos[2]:.1f}]")
        lines.append(f"Pitch: {camera.pitch:.1f}° | Yaw: {camera.yaw:.1f}°")

        # Light info
        shadow_res = SHADOW_MAP_SIZE
        lines.append(f"Lights: {len(lights)} | Shadows: {shadow_res}x{shadow_res}")

        tonemap = getattr(self.pipeline, 'tonemap_renderer', None)
        if tonemap is not None:
            exposure = tonemap.exposure
            auto_state = "ON" if tonemap.auto_enabled else "OFF"
            lines.append(f"HDR: exposure={exposure:.2f} auto={auto_state} operator={tonemap.operator}")

        if lights:
            primary = lights[0]
            mode = getattr(primary, 'intensity_mode', 'multiplier')
            lux = getattr(primary, 'illuminance', None)
            lumens = getattr(primary, 'luminous_flux', None)
            lines.append(
                f"Light0: type={primary.light_type} I={primary.intensity:.2f} mode={mode} "
                f"lux={lux if lux is not None else '-'} lumens={lumens if lumens is not None else '-'}"
            )

        # Scene info
        if scene:
            total_objects = len(scene.objects)
            culling_status = "ON" if ENABLE_FRUSTUM_CULLING else "OFF"
            lines.append(f"Objects: {total_objects} | Culling: {culling_status}")

            culling_lines = self._format_culling_stats(scene.last_render_stats)
            if culling_lines:
                lines.append("")
                lines.extend(culling_lines)

        shadow_lines = self._format_shadow_stats()
        if shadow_lines:
            lines.append("")
            lines.extend(shadow_lines)

        # Controls hint
        lines.append("")
        lines.append("ESC: Release mouse | T: Toggle SSAO")
        lines.append("PgUp/PgDn: Exposure +/- | Home: Reset | End: Auto Exp | F10: Print Light Info")

        return lines

    def _format_culling_stats(self, stats: Dict[str, Dict[str, object]]) -> List[str]:
        if not stats:
            return []

        lines: List[str] = []
        for label, data in stats.items():
            if not data.get('frustum_applied'):
                continue

            rendered = data.get('rendered', 0)
            total = data.get('total', 0)
            culled = data.get('culled', 0)
            lines.append(f"Frustum[{label}]: {rendered}/{total} rendered (culled {culled})")

            if DEBUG_SHOW_CULLED_OBJECTS:
                culled_objects = data.get('culled_objects') or []
                if culled_objects:
                    sample = culled_objects[:3]
                    remainder = len(culled_objects) - len(sample)
                    summary = ', '.join(sample)
                    if remainder > 0:
                        summary = f"{summary}, +{remainder} more"
                    lines.append(f"  Culled: {summary}")

        return lines

    def _format_shadow_stats(self) -> List[str]:
        shadow_renderer = getattr(self.pipeline, 'shadow_renderer', None)
        if shadow_renderer is None or shadow_renderer.last_stats is None:
            return []

        stats = shadow_renderer.last_stats
        rendered = stats.get('rendered', 0)
        total = stats.get('total', 0)
        skipped_intensity = stats.get('skipped_intensity', 0)
        skipped_throttle = stats.get('skipped_throttle', 0)
        skipped_non_casting = stats.get('skipped_non_casting', 0)

        lines = [
            f"Shadows: {rendered}/{total} rendered | skipped I:{skipped_intensity} T:{skipped_throttle} NC:{skipped_non_casting}"
        ]

        if DEBUG_SHADOW_RENDERING:
            lines.append("  (Shadow debug logging enabled)")

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
        line_height = self.text_manager.get_line_height() * DEBUG_TEXT_SCALE
        line_step = max(line_height, float(DEBUG_LINE_SPACING))

        for i, line in enumerate(lines):
            line_y = y + i * line_step
            text_id = self.text_manager.add_text(
                text=line,
                position=(x, line_y),
                color=DEBUG_TEXT_COLOR,
                scale=DEBUG_TEXT_SCALE,
                layer="debug",
                background_color=DEBUG_OVERLAY_BACKGROUND_COLOR,
                background_padding=DEBUG_OVERLAY_BACKGROUND_PADDING,
            )
            self.text_ids.append(text_id)

    def clear(self):
        """Clear all debug text."""
        for text_id in self.text_ids:
            self.text_manager.remove_text(text_id)
        self.text_ids.clear()
