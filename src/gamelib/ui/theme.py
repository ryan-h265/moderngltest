"""
ImGui Theme System

Manages visual styling for UI elements with support for multiple themes
and JSON-based customization.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Optional, Tuple

import imgui

from ..config.settings import PROJECT_ROOT


Color4 = Tuple[float, float, float, float]
Color3 = Tuple[float, float, float]


@dataclass
class ColorPalette:
    """Color palette for a theme."""

    # Primary colors
    primary: Color3 = (0.57, 0.77, 0.55)      # Sage green
    primary_dark: Color3 = (0.47, 0.67, 0.45)
    primary_light: Color3 = (0.67, 0.87, 0.65)

    # Accent colors
    accent: Color3 = (0.85, 0.65, 0.35)       # Warm accent
    accent_dark: Color3 = (0.75, 0.55, 0.25)

    # Background colors
    bg_primary: Color3 = (0.15, 0.15, 0.15)   # Dark background
    bg_secondary: Color3 = (0.20, 0.20, 0.20)
    bg_tertiary: Color3 = (0.25, 0.25, 0.25)

    # Text colors
    text_primary: Color3 = (0.95, 0.95, 0.95)    # Light text
    text_secondary: Color3 = (0.75, 0.75, 0.75)
    text_disabled: Color3 = (0.50, 0.50, 0.50)

    # Status colors
    success: Color3 = (0.35, 0.75, 0.35)
    warning: Color3 = (0.85, 0.65, 0.35)
    error: Color3 = (0.85, 0.35, 0.35)

    # UI element colors
    border: Color3 = (0.40, 0.40, 0.40)
    button_hover: Color3 = (0.30, 0.30, 0.30)
    button_active: Color3 = (0.25, 0.25, 0.25)


@dataclass
class ThemeConfig:
    """Complete theme configuration."""

    name: str = "sage_green"
    colors: ColorPalette = field(default_factory=ColorPalette)

    # Typography
    font_size: int = 16
    font_size_small: int = 12
    font_size_large: int = 20

    # Spacing and sizing
    frame_padding: float = 8.0
    item_spacing: float = 8.0
    item_inner_spacing: float = 4.0
    frame_rounding: float = 4.0
    button_rounding: float = 4.0

    # Window styling
    window_padding: float = 12.0
    window_rounding: float = 8.0
    window_border_size: float = 1.0

    # Transparency
    alpha: float = 1.0
    popup_alpha: float = 0.95

    # Scale factor (multiplier for all sizes)
    scale: float = 1.5  # 1.5x larger by default for better readability

    @classmethod
    def from_dict(cls, data: Dict) -> ThemeConfig:
        """Load theme from dictionary (JSON compatible)."""
        colors_data = data.get("colors", {})
        # Convert lists back to tuples for color values
        if colors_data:
            for key, val in colors_data.items():
                if isinstance(val, list):
                    colors_data[key] = tuple(val)
        colors = ColorPalette(**colors_data) if colors_data else ColorPalette()

        config = cls(
            name=data.get("name", "sage_green"),
            colors=colors,
            font_size=data.get("font_size", 16),
            font_size_small=data.get("font_size_small", 12),
            font_size_large=data.get("font_size_large", 20),
            frame_padding=data.get("frame_padding", 8.0),
            item_spacing=data.get("item_spacing", 8.0),
            item_inner_spacing=data.get("item_inner_spacing", 4.0),
            frame_rounding=data.get("frame_rounding", 4.0),
            button_rounding=data.get("button_rounding", 4.0),
            window_padding=data.get("window_padding", 12.0),
            window_rounding=data.get("window_rounding", 8.0),
            window_border_size=data.get("window_border_size", 1.0),
            alpha=data.get("alpha", 1.0),
            popup_alpha=data.get("popup_alpha", 0.95),
            scale=data.get("scale", 1.5),
        )
        return config

    def to_dict(self) -> Dict:
        """Convert theme to dictionary (JSON serializable)."""
        data = asdict(self)
        # Convert Color3 tuples to lists for JSON serialization
        if isinstance(data.get("colors"), dict):
            colors_dict = data["colors"]
            for key, val in colors_dict.items():
                if isinstance(val, tuple):
                    colors_dict[key] = list(val)
        return data


class ThemeManager:
    """Manages ImGui themes and styling."""

    # Built-in themes
    BUILTIN_THEMES = {
        "sage_green": ColorPalette(
            primary=(0.57, 0.77, 0.55),
            primary_dark=(0.47, 0.67, 0.45),
            primary_light=(0.67, 0.87, 0.65),
        ),
        "dark": ColorPalette(
            primary=(0.40, 0.40, 0.40),
            primary_dark=(0.30, 0.30, 0.30),
            primary_light=(0.50, 0.50, 0.50),
            accent=(0.60, 0.60, 0.60),
        ),
        "light": ColorPalette(
            primary=(0.60, 0.60, 0.60),
            primary_dark=(0.50, 0.50, 0.50),
            primary_light=(0.70, 0.70, 0.70),
            bg_primary=(0.95, 0.95, 0.95),
            bg_secondary=(0.90, 0.90, 0.90),
            bg_tertiary=(0.85, 0.85, 0.85),
            text_primary=(0.05, 0.05, 0.05),
            text_secondary=(0.25, 0.25, 0.25),
        ),
        "cyberpunk": ColorPalette(
            primary=(0.00, 0.95, 0.85),
            primary_dark=(0.00, 0.75, 0.65),
            primary_light=(0.20, 1.00, 0.95),
            accent=(0.95, 0.00, 0.85),
            bg_primary=(0.05, 0.05, 0.15),
            bg_secondary=(0.10, 0.10, 0.20),
            text_primary=(0.00, 0.95, 0.85),
        ),
    }

    def __init__(self, theme_name: str = "sage_green"):
        """
        Initialize theme manager.

        Args:
            theme_name: Name of theme to load ("sage_green", "dark", "light", "cyberpunk")
        """
        self.current_theme = self._load_theme(theme_name)
        self.apply_theme(self.current_theme)

    def _load_theme(self, theme_name: str) -> ThemeConfig:
        """
        Load theme from JSON or built-in.

        Args:
            theme_name: Theme name or path

        Returns:
            ThemeConfig instance
        """
        # Check for JSON file first
        json_path = PROJECT_ROOT / "assets" / "config" / "themes" / f"{theme_name}.json"
        if json_path.exists():
            with open(json_path, "r") as f:
                data = json.load(f)
            return ThemeConfig.from_dict(data)

        # Check built-in themes
        if theme_name in self.BUILTIN_THEMES:
            return ThemeConfig(name=theme_name, colors=self.BUILTIN_THEMES[theme_name])

        # Fallback to sage_green
        print(f"Theme '{theme_name}' not found, using 'sage_green'")
        return ThemeConfig(name="sage_green", colors=self.BUILTIN_THEMES["sage_green"])

    def apply_theme(self, theme: ThemeConfig) -> None:
        """
        Apply theme colors and styling to ImGui.

        Args:
            theme: ThemeConfig to apply
        """
        self.current_theme = theme
        style = imgui.get_style()
        io = imgui.get_io()

        # Set colors
        colors = theme.colors
        style.colors[imgui.COLOR_WINDOW_BACKGROUND] = colors.bg_primary + (theme.alpha,)
        style.colors[imgui.COLOR_CHILD_BACKGROUND] = colors.bg_secondary + (theme.alpha,)
        style.colors[imgui.COLOR_POPUP_BACKGROUND] = colors.bg_secondary + (theme.popup_alpha,)
        style.colors[imgui.COLOR_BORDER] = colors.border + (1.0,)
        style.colors[imgui.COLOR_BORDER_SHADOW] = (0.0, 0.0, 0.0, 0.0)

        # Buttons
        style.colors[imgui.COLOR_BUTTON] = colors.primary + (1.0,)
        style.colors[imgui.COLOR_BUTTON_HOVERED] = colors.primary_light + (1.0,)
        style.colors[imgui.COLOR_BUTTON_ACTIVE] = colors.primary_dark + (1.0,)

        # Headers
        style.colors[imgui.COLOR_HEADER] = colors.primary_dark + (0.8,)
        style.colors[imgui.COLOR_HEADER_HOVERED] = colors.primary + (0.9,)
        style.colors[imgui.COLOR_HEADER_ACTIVE] = colors.primary_light + (1.0,)

        # Text
        style.colors[imgui.COLOR_TEXT] = colors.text_primary + (1.0,)
        style.colors[imgui.COLOR_TEXT_DISABLED] = colors.text_disabled + (1.0,)

        # Sliders and inputs
        style.colors[imgui.COLOR_SLIDER_GRAB] = colors.accent + (1.0,)
        style.colors[imgui.COLOR_SLIDER_GRAB_ACTIVE] = colors.accent_dark + (1.0,)
        style.colors[imgui.COLOR_FRAME_BACKGROUND] = colors.bg_tertiary + (0.9,)
        style.colors[imgui.COLOR_FRAME_BACKGROUND_HOVERED] = colors.bg_primary + (1.0,)
        style.colors[imgui.COLOR_FRAME_BACKGROUND_ACTIVE] = colors.bg_tertiary + (1.0,)

        # Checkmarks and selections
        style.colors[imgui.COLOR_CHECK_MARK] = colors.primary_light + (1.0,)
        style.colors[imgui.COLOR_SCROLLBAR_BACKGROUND] = colors.bg_tertiary + (0.5,)
        style.colors[imgui.COLOR_SCROLLBAR_GRAB] = colors.primary_dark + (0.8,)
        style.colors[imgui.COLOR_SCROLLBAR_GRAB_HOVERED] = colors.primary + (0.9,)
        style.colors[imgui.COLOR_SCROLLBAR_GRAB_ACTIVE] = colors.primary_light + (1.0,)

        # Tabs
        style.colors[imgui.COLOR_TAB] = colors.bg_secondary + (0.8,)
        style.colors[imgui.COLOR_TAB_HOVERED] = colors.primary + (0.9,)
        style.colors[imgui.COLOR_TAB_ACTIVE] = colors.primary_dark + (1.0,)
        style.colors[imgui.COLOR_TAB_UNFOCUSED] = colors.bg_tertiary + (0.7,)
        style.colors[imgui.COLOR_TAB_UNFOCUSED_ACTIVE] = colors.primary_dark + (0.9,)

        # Apply scale factor to all dimensions
        scale = theme.scale

        # Spacing and sizing (scaled)
        style.frame_padding = (theme.frame_padding * scale, theme.frame_padding * scale)
        style.item_spacing = (theme.item_spacing * scale, theme.item_spacing * scale)
        style.item_inner_spacing = (theme.item_inner_spacing * scale, theme.item_inner_spacing * scale)
        style.frame_rounding = theme.frame_rounding * scale
        style.button_text_align = (0.5, 0.5)  # Center button text
        style.window_padding = (theme.window_padding * scale, theme.window_padding * scale)
        style.window_rounding = theme.window_rounding * scale
        style.window_border_size = theme.window_border_size

        # Apply global scale to ImGui
        io.font_global_scale = scale

    def switch_theme(self, theme_name: str) -> None:
        """
        Switch to a different theme.

        Args:
            theme_name: Name of theme to switch to
        """
        theme = self._load_theme(theme_name)
        self.apply_theme(theme)

    def get_color(self, color_name: str) -> Color3:
        """
        Get a color from the current theme palette.

        Args:
            color_name: Name of color ("primary", "accent", "success", etc.)

        Returns:
            RGB color tuple
        """
        colors = self.current_theme.colors
        return getattr(colors, color_name, colors.primary)
