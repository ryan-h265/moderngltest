"""Configurable in-game heads-up display for player-centric data."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from ..config import settings

if TYPE_CHECKING:  # pragma: no cover - for type checking only
    from ..rendering.render_pipeline import RenderPipeline


@dataclass
class _HUDRow:
    """Container for HUD layout primitives."""

    name: str
    label_id: Optional[int] = None
    value_ids: List[int] = field(default_factory=list)
    icon_id: Optional[int] = None
    icon_path: Optional[Path] = None


class PlayerHUD:
    """High-level HUD controller that mirrors the debug overlay system."""

    def __init__(self, pipeline: "RenderPipeline") -> None:
        self.pipeline = pipeline
        self.text_manager = pipeline.text_manager
        self.icon_manager = getattr(pipeline, "icon_manager", None)
        if self.icon_manager is None:
            raise RuntimeError("RenderPipeline must provide an IconManager for the HUD")

        self._anchor = settings.HUD_ANCHOR
        if self._anchor not in {"bottom_left", "top_left"}:
            raise NotImplementedError(
                f"HUD anchor '{self._anchor}' is not supported yet. Use 'bottom_left' or 'top_left'."
            )

        self._margin = settings.HUD_MARGIN
        self._icon_size = tuple(float(v) for v in settings.HUD_ICON_SIZE)
        self._icon_gap = float(settings.HUD_ICON_TEXT_GAP)
        self._line_spacing = float(settings.HUD_LINE_SPACING)
        self._section_spacing = float(settings.HUD_SECTION_SPACING)
        self._hint_line_spacing = float(settings.HUD_HINT_LINE_SPACING)
        self._value_gap = float(settings.HUD_VALUE_GAP)
        self._text_scale = float(settings.HUD_TEXT_SCALE)
        self._label_color = settings.HUD_LABEL_COLOR
        self._value_color = settings.HUD_VALUE_COLOR
        self._hint_color = settings.HUD_HINT_COLOR
        self._warning_color = settings.HUD_WARNING_COLOR
        self._critical_color = settings.HUD_CRITICAL_COLOR
        self._threshold_warning = settings.HUD_HEALTH_THRESHOLDS.get("warning", 0.6)
        self._threshold_critical = settings.HUD_HEALTH_THRESHOLDS.get("critical", 0.35)
        self._background_color = settings.HUD_BACKGROUND_COLOR
        self._background_padding = float(settings.HUD_BACKGROUND_PADDING)
        self._text_layer = settings.HUD_LAYER_TEXT
        self._icon_layer = settings.HUD_LAYER_ICONS
        self._section_order = [name for name in settings.HUD_SECTION_ORDER if name in settings.HUD_SECTIONS]
        self._hint_slots = max(0, int(settings.HUD_HINT_SLOTS))

        self._line_height = self.text_manager.get_line_height() * self._text_scale
        self._rows: Dict[str, _HUDRow] = {}
        self._last_viewport: Optional[Tuple[int, int]] = None

        # HUD state values
        self._health_current = 100.0
        self._health_max = 100.0
        self._minimap_status = "No signal"
        self._equipped_tool = "Hands"
        self._equipped_tool_icon: Optional[Path] = None
        self._icon_tint = settings.HUD_ICON_TINT
        self._hints: List[str] = []

        self._create_rows()
        self._apply_default_layout()

    # ------------------------------------------------------------------
    # Public API for gameplay systems
    # ------------------------------------------------------------------
    def set_health(self, current: float, maximum: float) -> None:
        self._health_current = max(0.0, float(current))
        self._health_max = max(1.0, float(maximum))

    def set_minimap_status(self, status: str) -> None:
        self._minimap_status = status

    def set_equipped_tool(self, tool_name: str, icon_path: Optional[str] = None) -> None:
        self._equipped_tool = tool_name
        if icon_path:
            path = Path(icon_path)
            if not path.is_absolute():
                path = settings.PROJECT_ROOT / path
            if path != self._equipped_tool_icon:
                row = self._rows.get("tool")
                if row and row.icon_id is not None:
                    self.icon_manager.update_image(row.icon_id, path)
                    self._equipped_tool_icon = path

    def set_hints(self, hints: Sequence[str]) -> None:
        self._hints = [hint for hint in hints][: self._hint_slots]

    def clear_hints(self) -> None:
        self._hints.clear()

    def set_section_value_color(self, section: str, color: Tuple[float, float, float, float]) -> None:
        row = self._rows.get(section)
        if not row:
            return
        for text_id in row.value_ids:
            self.text_manager.update_color(text_id, color)

    # ------------------------------------------------------------------
    def update(self, camera, frametime: float = 0.0) -> None:  # noqa: D401 - match DebugOverlay API
        """Refresh HUD content based on current state."""

        self._ensure_layout()
        self._update_compass(camera)
        self._update_health()
        self._update_minimap()
        self._update_tool()
        self._update_hints()

    # ------------------------------------------------------------------
    # Internal setup helpers
    # ------------------------------------------------------------------
    def _create_rows(self) -> None:
        for name in self._section_order:
            config = settings.HUD_SECTIONS[name]
            row = _HUDRow(name=name)

            icon_path = config.get("icon")
            if icon_path:
                absolute = settings.PROJECT_ROOT / icon_path
                row.icon_id = self.icon_manager.add_icon(
                    absolute,
                    position=(0.0, 0.0),
                    size=self._icon_size,
                    color=self._icon_tint,
                    layer=self._icon_layer,
                )
                row.icon_path = absolute

            label_text = config.get("label", name.title())
            row.label_id = self.text_manager.add_text(
                text=label_text,
                position=(0.0, 0.0),
                color=self._label_color,
                scale=self._text_scale,
                layer=self._text_layer,
                background_color=self._background_color,
                background_padding=self._background_padding,
            )

            if name == "hints":
                for _ in range(self._hint_slots):
                    text_id = self.text_manager.add_text(
                        text="",
                        position=(0.0, 0.0),
                        color=self._hint_color,
                        scale=self._text_scale,
                        layer=self._text_layer,
                        background_color=self._background_color,
                        background_padding=self._background_padding,
                    )
                    row.value_ids.append(text_id)
            else:
                value_id = self.text_manager.add_text(
                    text="--",
                    position=(0.0, 0.0),
                    color=self._value_color,
                    scale=self._text_scale,
                    layer=self._text_layer,
                    background_color=self._background_color,
                    background_padding=self._background_padding,
                )
                row.value_ids.append(value_id)

            self._rows[name] = row

    def _apply_default_layout(self) -> None:
        self._last_viewport = None
        self._ensure_layout()

    # ------------------------------------------------------------------
    # Layout computation
    # ------------------------------------------------------------------
    def _ensure_layout(self) -> None:
        viewport = tuple(self.pipeline.viewport_size)
        if viewport == self._last_viewport:
            return
        self._last_viewport = viewport
        self._layout_rows(viewport)

    def _layout_rows(self, viewport: Tuple[int, int]) -> None:
        width, height = viewport
        margin_x, margin_y = self._margin

        if self._anchor == "bottom_left":
            base_x = float(margin_x)
            cursor_y = float(height - margin_y)
            direction = -1
        else:  # top_left
            base_x = float(margin_x)
            cursor_y = float(margin_y)
            direction = 1

        for name in self._section_order:
            row = self._rows[name]
            row_height = self._compute_row_height(name)

            if direction < 0:
                row_top = cursor_y - row_height
                cursor_y = row_top - self._section_spacing
            else:
                row_top = cursor_y
                cursor_y = row_top + row_height + self._section_spacing

            self._position_row(row, base_x, row_top, row_height)

    def _compute_row_height(self, name: str) -> float:
        if name == "hints":
            lines = 1 + self._hint_slots
            text_height = lines * self._line_height + max(0, lines - 1) * self._hint_line_spacing
        else:
            lines = 2  # label + value
            text_height = self._line_height * 2 + self._value_gap
        return max(self._icon_size[1], text_height) + self._line_spacing

    def _position_row(self, row: _HUDRow, base_x: float, row_top: float, row_height: float) -> None:
        text_block_height = self._line_height * 2 + self._value_gap
        if row.name == "hints":
            lines = 1 + self._hint_slots
            text_block_height = lines * self._line_height + max(0, lines - 1) * self._hint_line_spacing

        text_x = base_x + self._icon_size[0] + self._icon_gap
        text_y = row_top + max(0.0, (row_height - text_block_height) / 2.0)

        if row.icon_id is not None:
            icon_y = row_top + max(0.0, (row_height - self._icon_size[1]) / 2.0)
            self.icon_manager.update_position(row.icon_id, (base_x, icon_y))
            self.icon_manager.update_size(row.icon_id, self._icon_size)

        if row.label_id is not None:
            self.text_manager.update_position(row.label_id, (text_x, text_y))

        if row.name == "hints":
            current_y = text_y + self._line_height + self._hint_line_spacing
            for text_id in row.value_ids:
                self.text_manager.update_position(text_id, (text_x, current_y))
                current_y += self._line_height + self._hint_line_spacing
        else:
            value_y = text_y + self._line_height + self._value_gap
            for text_id in row.value_ids:
                self.text_manager.update_position(text_id, (text_x, value_y))
                value_y += self._line_height + self._hint_line_spacing

    # ------------------------------------------------------------------
    # Update helpers
    # ------------------------------------------------------------------
    def _update_compass(self, camera) -> None:
        row = self._rows.get("compass")
        if not row or not row.value_ids:
            return

        forward = camera.get_front()
        heading_rad = math.atan2(forward[0], -forward[2])
        heading_deg = (math.degrees(heading_rad) + 360.0) % 360.0
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        index = int((heading_deg + 22.5) // 45) % len(directions)
        text = f"{directions[index]} ({heading_deg:03.0f}°)"

        self.text_manager.update_text(row.value_ids[0], text)
        self.text_manager.update_color(row.value_ids[0], self._value_color)

    def _update_health(self) -> None:
        row = self._rows.get("health")
        if not row or not row.value_ids:
            return

        text = f"{int(self._health_current)}/{int(self._health_max)}"
        ratio = self._health_current / max(self._health_max, 1.0)
        if ratio <= self._threshold_critical:
            color = self._critical_color
        elif ratio <= self._threshold_warning:
            color = self._warning_color
        else:
            color = self._value_color

        self.text_manager.update_text(row.value_ids[0], text)
        self.text_manager.update_color(row.value_ids[0], color)

    def _update_minimap(self) -> None:
        row = self._rows.get("minimap")
        if not row or not row.value_ids:
            return
        self.text_manager.update_text(row.value_ids[0], self._minimap_status)
        self.text_manager.update_color(row.value_ids[0], self._value_color)

    def _update_tool(self) -> None:
        row = self._rows.get("tool")
        if not row or not row.value_ids:
            return
        self.text_manager.update_text(row.value_ids[0], self._equipped_tool)
        self.text_manager.update_color(row.value_ids[0], self._value_color)

    def _update_hints(self) -> None:
        row = self._rows.get("hints")
        if not row:
            return

        hints = self._hints + [""] * max(0, self._hint_slots - len(self._hints))
        for text_id, hint in zip(row.value_ids, hints):
            self.text_manager.update_text(text_id, hint)
            self.text_manager.update_color(text_id, self._hint_color)
