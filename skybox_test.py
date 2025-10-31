#!/usr/bin/env python3
"""
Skybox Testing Tool

Interactive tool for testing and configuring skybox parameters with real-time preview.
Uses ImGui for the interface.

Usage:
    python skybox_test.py
"""

import json
import math
import sys
from pathlib import Path

import imgui
import moderngl
import moderngl_window as mglw
from moderngl_window.integrations.imgui import ModernglWindowRenderer
from pyrr import Matrix44, Vector3

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from gamelib.config.settings import WINDOW_SIZE, GL_VERSION
from gamelib.core.camera import Camera
from gamelib.core.skybox import Skybox
from gamelib.core.skybox_config import (
    SkyboxConfig,
    TimeOfDayConfig,
    WeatherConfig,
    AtmosphericConfig,
    StarFieldConfig,
    FogConfig,
)
from gamelib.rendering.skybox_renderer import SkyboxRenderer
from gamelib.rendering.shader_manager import ShaderManager


class SkyboxTestWindow(mglw.WindowConfig):
    """Interactive skybox testing window."""

    gl_version = GL_VERSION
    title = "Skybox Testing Tool"
    window_size = WINDOW_SIZE
    resizable = True
    vsync = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize ImGui
        imgui.create_context()
        self.imgui_renderer = ModernglWindowRenderer(self.wnd)

        # Camera setup (simple free look)
        self.camera = Camera(position=Vector3([0.0, 0.0, 0.0]))
        self.camera.yaw = -90.0
        self.camera.pitch = 0.0
        self.camera.update_vectors()
        self.mouse_sensitivity = 0.1
        self.last_mouse_pos = None
        self.mouse_captured = False

        # Shader setup
        self.shader_manager = ShaderManager(self.ctx)
        self._load_shaders()

        # Skybox renderer
        skybox_programs = {
            "cubemap": self.shader_manager.get("skybox_cubemap"),
            "atmospheric": self.shader_manager.get("skybox_atmospheric"),
            "hybrid": self.shader_manager.get("skybox_hybrid"),
            "aurora": self.shader_manager.get("skybox_aurora"),
            "procedural": self.shader_manager.get("skybox_aurora"),
        }
        self.skybox_renderer = SkyboxRenderer(self.ctx, skybox_programs)

        # Current skybox configuration
        self.config = self._create_default_config()
        self.skybox = self._create_skybox_from_config()

        # UI state
        self.show_help = True
        self.time_accumulator = 0.0

        # Preset configurations
        self.presets = {
            "1: Clear Day": self._preset_clear_day,
            "2: Sunset": self._preset_sunset,
            "3: Night with Stars": self._preset_night_stars,
            "4: Cloudy Day": self._preset_cloudy,
            "5: Stormy": self._preset_stormy,
        }

        print("Skybox Testing Tool")
        print("=" * 50)
        print("Press TAB to toggle mouse capture")
        print("Use number keys 1-5 for presets")
        print("Use ImGui interface to adjust parameters")
        print("=" * 50)

    def _load_shaders(self):
        """Load all skybox shader variants."""
        self.shader_manager.load_program("skybox_cubemap", "skybox.vert", "skybox_cubemap.frag")
        self.shader_manager.load_program("skybox_atmospheric", "skybox.vert", "skybox_atmospheric.frag")
        self.shader_manager.load_program("skybox_hybrid", "skybox.vert", "skybox_hybrid.frag")
        self.shader_manager.load_program("skybox_aurora", "skybox.vert", "aurora_skybox.frag")

    def _create_default_config(self) -> SkyboxConfig:
        """Create default skybox configuration."""
        return SkyboxConfig(
            type="hybrid",
            intensity=1.0,
            rotation=(0.0, 0.0, 0.0),
            time_of_day=TimeOfDayConfig(
                enabled=True,
                current_time=0.5,
                auto_progress=False,
                speed=1.0,
                latitude=45.0,
                sun_intensity=1.0,
                moon_intensity=0.3,
            ),
            weather=WeatherConfig(
                type="clear",
                cloud_coverage=0.3,
                cloud_speed=1.0,
                cloud_density=0.5,
                precipitation=0.0,
                wind_speed=1.0,
                wind_direction=(1.0, 0.0),
            ),
            atmospheric=AtmosphericConfig(
                enabled=True,
                turbidity=2.0,
            ),
            stars=StarFieldConfig(
                enabled=True,
                density=1000,
                brightness=1.0,
                size=1.0,
                rotation_speed=0.1,
                twinkle=True,
                twinkle_speed=1.0,
            ),
            fog=FogConfig(
                enabled=False,
                color=(0.5, 0.6, 0.7),
                density=0.02,
                start=0.0,
                end=100.0,
            ),
        )

    def _create_skybox_from_config(self) -> Skybox:
        """Create skybox from current configuration."""
        return Skybox.from_config(self.ctx, self.config)

    def _apply_config(self):
        """Recreate skybox with current configuration."""
        self.skybox = self._create_skybox_from_config()

    # Preset configurations
    def _preset_clear_day(self):
        """Clear day preset."""
        self.config.type = "atmospheric"
        self.config.intensity = 1.2
        self.config.time_of_day.current_time = 0.5
        self.config.time_of_day.auto_progress = False
        self.config.weather.cloud_coverage = 0.0
        self.config.atmospheric.enabled = True
        self.config.atmospheric.turbidity = 2.0
        self.config.stars.enabled = True
        self._apply_config()

    def _preset_sunset(self):
        """Sunset preset."""
        self.config.type = "hybrid"
        self.config.intensity = 1.0
        self.config.time_of_day.current_time = 0.75
        self.config.time_of_day.auto_progress = False
        self.config.weather.cloud_coverage = 0.2
        self.config.atmospheric.enabled = True
        self.config.atmospheric.turbidity = 3.0
        self.config.stars.enabled = True
        self._apply_config()

    def _preset_night_stars(self):
        """Night with stars preset."""
        self.config.type = "hybrid"
        self.config.intensity = 0.8
        self.config.time_of_day.current_time = 0.1
        self.config.time_of_day.auto_progress = False
        self.config.weather.cloud_coverage = 0.1
        self.config.atmospheric.enabled = True
        self.config.stars.enabled = True
        self.config.stars.density = 2000
        self.config.stars.brightness = 1.5
        self._apply_config()

    def _preset_cloudy(self):
        """Cloudy day preset."""
        self.config.type = "hybrid"
        self.config.intensity = 0.9
        self.config.time_of_day.current_time = 0.5
        self.config.time_of_day.auto_progress = False
        self.config.weather.cloud_coverage = 0.6
        self.config.weather.cloud_density = 0.7
        self.config.atmospheric.enabled = True
        self.config.atmospheric.turbidity = 4.0
        self._apply_config()

    def _preset_stormy(self):
        """Stormy preset."""
        self.config.type = "hybrid"
        self.config.intensity = 0.6
        self.config.time_of_day.current_time = 0.4
        self.config.time_of_day.auto_progress = False
        self.config.weather.type = "stormy"
        self.config.weather.cloud_coverage = 0.9
        self.config.weather.cloud_density = 0.8
        self.config.weather.precipitation = 0.7
        self.config.weather.wind_speed = 3.0
        self.config.atmospheric.enabled = True
        self.config.atmospheric.turbidity = 6.0
        self.config.fog.enabled = True
        self.config.fog.color = (0.3, 0.35, 0.4)
        self.config.fog.density = 0.05
        self._apply_config()

    def _save_config_to_file(self):
        """Save current configuration to JSON file."""
        output_path = Path("skybox_export.json")
        config_dict = self.config.to_dict()

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2)

        print(f"Configuration saved to: {output_path.absolute()}")

    def render_imgui(self):
        """Render ImGui interface."""
        imgui.new_frame()

        # Main window
        imgui.set_next_window_size(400, 700, imgui.FIRST_USE_EVER)
        imgui.set_next_window_position(10, 10, imgui.FIRST_USE_EVER)

        imgui.begin("Skybox Configuration", True)

        # Info section
        if imgui.collapsing_header("Info", imgui.TREE_NODE_DEFAULT_OPEN)[0]:
            if self.skybox.time_of_day:
                time_str = self.skybox.time_of_day.get_time_of_day_string()
                period = self.skybox.time_of_day.get_time_period()
                imgui.text(f"Time: {time_str} ({period})")

                sun = self.skybox.time_of_day.get_sun_position()
                imgui.text(f"Sun Elevation: {math.degrees(sun.elevation):.1f}°")
                imgui.text(f"Sun Intensity: {sun.intensity:.2f}")

            imgui.text(f"Shader: {self.skybox.shader_variant}")
            imgui.separator()

        # Presets
        if imgui.collapsing_header("Presets", imgui.TREE_NODE_DEFAULT_OPEN)[0]:
            for preset_name, preset_func in self.presets.items():
                if imgui.button(preset_name, width=-1):
                    preset_func()
            imgui.separator()

        # Basic settings
        if imgui.collapsing_header("Basic Settings", imgui.TREE_NODE_DEFAULT_OPEN)[0]:
            # Skybox type
            current_type = self.config.type
            type_options = ["cubemap", "atmospheric", "procedural", "hybrid"]
            if imgui.begin_combo("Type", current_type):
                for option in type_options:
                    is_selected = (option == current_type)
                    if imgui.selectable(option, is_selected)[0]:
                        self.config.type = option
                        self._apply_config()
                    if is_selected:
                        imgui.set_item_default_focus()
                imgui.end_combo()

            # Intensity
            changed, value = imgui.slider_float("Intensity", self.config.intensity, 0.0, 2.0)
            if changed:
                self.config.intensity = value
                self.skybox.intensity = value

            # Rotation
            changed, yaw = imgui.slider_float("Rotation Yaw", self.config.rotation[0], -180.0, 180.0)
            if changed:
                self.config.rotation = (yaw, self.config.rotation[1], self.config.rotation[2])
                self.skybox.set_rotation_from_euler(*self.config.rotation)

            imgui.separator()

        # Time of Day
        if imgui.collapsing_header("Time of Day")[0]:
            changed, enabled = imgui.checkbox("Enabled##tod", self.config.time_of_day.enabled)
            if changed:
                self.config.time_of_day.enabled = enabled
                self._apply_config()

            if self.config.time_of_day.enabled:
                changed, value = imgui.slider_float(
                    "Current Time", self.config.time_of_day.current_time, 0.0, 1.0
                )
                if changed:
                    self.config.time_of_day.current_time = value
                    if self.skybox.time_of_day:
                        self.skybox.time_of_day.time = value

                changed, auto = imgui.checkbox("Auto Progress", self.config.time_of_day.auto_progress)
                if changed:
                    self.config.time_of_day.auto_progress = auto
                    if self.skybox.time_of_day:
                        self.skybox.time_of_day.auto_progress = auto

                changed, speed = imgui.slider_float("Speed", self.config.time_of_day.speed, 0.0, 10.0)
                if changed:
                    self.config.time_of_day.speed = speed
                    if self.skybox.time_of_day:
                        self.skybox.time_of_day.time_speed = speed

                changed, lat = imgui.slider_float("Latitude", self.config.time_of_day.latitude, -90.0, 90.0)
                if changed:
                    self.config.time_of_day.latitude = lat
                    self._apply_config()

                changed, sun_int = imgui.slider_float("Sun Intensity", self.config.time_of_day.sun_intensity, 0.0, 2.0)
                if changed:
                    self.config.time_of_day.sun_intensity = sun_int
                    self._apply_config()

                changed, moon_int = imgui.slider_float("Moon Intensity", self.config.time_of_day.moon_intensity, 0.0, 1.0)
                if changed:
                    self.config.time_of_day.moon_intensity = moon_int
                    self._apply_config()

            imgui.separator()

        # Weather
        if imgui.collapsing_header("Weather")[0]:
            # Weather type
            current_weather = self.config.weather.type
            weather_options = ["clear", "cloudy", "overcast", "stormy", "rainy", "snowy"]
            if imgui.begin_combo("Weather Type", current_weather):
                for option in weather_options:
                    is_selected = (option == current_weather)
                    if imgui.selectable(option, is_selected)[0]:
                        self.config.weather.type = option
                        self.skybox.weather = self.config.weather
                    if is_selected:
                        imgui.set_item_default_focus()
                imgui.end_combo()

            changed, cov = imgui.slider_float("Cloud Coverage", self.config.weather.cloud_coverage, 0.0, 1.0)
            if changed:
                self.config.weather.cloud_coverage = cov
                if self.skybox.weather:
                    self.skybox.weather.cloud_coverage = cov

            changed, speed = imgui.slider_float("Cloud Speed", self.config.weather.cloud_speed, 0.0, 5.0)
            if changed:
                self.config.weather.cloud_speed = speed
                if self.skybox.weather:
                    self.skybox.weather.cloud_speed = speed

            changed, dens = imgui.slider_float("Cloud Density", self.config.weather.cloud_density, 0.0, 1.0)
            if changed:
                self.config.weather.cloud_density = dens
                if self.skybox.weather:
                    self.skybox.weather.cloud_density = dens

            changed, precip = imgui.slider_float("Precipitation", self.config.weather.precipitation, 0.0, 1.0)
            if changed:
                self.config.weather.precipitation = precip
                if self.skybox.weather:
                    self.skybox.weather.precipitation = precip

            changed, wind = imgui.slider_float("Wind Speed", self.config.weather.wind_speed, 0.0, 5.0)
            if changed:
                self.config.weather.wind_speed = wind
                if self.skybox.weather:
                    self.skybox.weather.wind_speed = wind

            imgui.separator()

        # Atmospheric
        if imgui.collapsing_header("Atmospheric")[0]:
            changed, enabled = imgui.checkbox("Enabled##atm", self.config.atmospheric.enabled)
            if changed:
                self.config.atmospheric.enabled = enabled

            if self.config.atmospheric.enabled:
                changed, turb = imgui.slider_float("Turbidity", self.config.atmospheric.turbidity, 1.0, 10.0)
                if changed:
                    self.config.atmospheric.turbidity = turb

                changed, brightness = imgui.slider_float("Sun Brightness", self.config.atmospheric.sun_brightness, 0.0, 50.0)
                if changed:
                    self.config.atmospheric.sun_brightness = brightness

            imgui.separator()

        # Stars
        if imgui.collapsing_header("Stars")[0]:
            changed, enabled = imgui.checkbox("Enabled##stars", self.config.stars.enabled)
            if changed:
                self.config.stars.enabled = enabled

            if self.config.stars.enabled:
                changed, dens = imgui.slider_int("Density", self.config.stars.density, 100, 5000)
                if changed:
                    self.config.stars.density = dens

                changed, bright = imgui.slider_float("Brightness", self.config.stars.brightness, 0.0, 3.0)
                if changed:
                    self.config.stars.brightness = bright

                changed, size = imgui.slider_float("Size", self.config.stars.size, 0.1, 3.0)
                if changed:
                    self.config.stars.size = size

                changed, twinkle = imgui.checkbox("Twinkle", self.config.stars.twinkle)
                if changed:
                    self.config.stars.twinkle = twinkle

            imgui.separator()

        # Fog
        if imgui.collapsing_header("Fog")[0]:
            changed, enabled = imgui.checkbox("Enabled##fog", self.config.fog.enabled)
            if changed:
                self.config.fog.enabled = enabled

            if self.config.fog.enabled:
                changed, color = imgui.color_edit3("Color", *self.config.fog.color)
                if changed:
                    self.config.fog.color = color

                changed, dens = imgui.slider_float("Density", self.config.fog.density, 0.0, 0.2)
                if changed:
                    self.config.fog.density = dens

            imgui.separator()

        # Save button
        if imgui.button("Save to skybox_export.json", width=-1):
            self._save_config_to_file()

        imgui.end()

        # Help window
        if self.show_help:
            imgui.set_next_window_size(300, 150, imgui.FIRST_USE_EVER)
            imgui.set_next_window_position(self.wnd.width - 310, 10, imgui.FIRST_USE_EVER)
            imgui.begin("Help")
            imgui.text("Controls:")
            imgui.bullet_text("TAB: Toggle mouse capture")
            imgui.bullet_text("Mouse: Look around")
            imgui.bullet_text("ESC: Exit")
            imgui.bullet_text("1-5: Apply presets")
            imgui.end()

        imgui.render()
        self.imgui_renderer.render(imgui.get_draw_data())

    def on_render(self, time: float, frametime: float):
        """Render callback - called every frame."""
        self.render(time, frametime)

    def render(self, time: float, frametime: float):
        """Render the skybox."""
        self.ctx.clear(0.0, 0.0, 0.0)
        self.ctx.enable(moderngl.DEPTH_TEST)

        # Update skybox animations
        if self.skybox:
            self.skybox.update(frametime)
            self.time_accumulator += frametime

        # Render skybox
        viewport = (0, 0, self.wnd.width, self.wnd.height)
        self.skybox_renderer.render(
            self.camera,
            self.skybox,
            viewport,
            time=self.time_accumulator
        )

        # Render ImGui
        self.render_imgui()

    def on_resize(self, width: int, height: int):
        """Handle window resize."""
        self.imgui_renderer.resize(width, height)

    def on_key_event(self, key, action, modifiers):
        """Handle keyboard events."""
        self.imgui_renderer.key_event(key, action, modifiers)

        if action == self.wnd.keys.ACTION_PRESS:
            # Toggle mouse capture
            if key == self.wnd.keys.TAB:
                self.mouse_captured = not self.mouse_captured
                self.wnd.mouse_exclusivity = self.mouse_captured
                self.wnd.cursor = not self.mouse_captured

            # Presets
            elif key == self.wnd.keys.NUMBER_1:
                self._preset_clear_day()
            elif key == self.wnd.keys.NUMBER_2:
                self._preset_sunset()
            elif key == self.wnd.keys.NUMBER_3:
                self._preset_night_stars()
            elif key == self.wnd.keys.NUMBER_4:
                self._preset_cloudy()
            elif key == self.wnd.keys.NUMBER_5:
                self._preset_stormy()

    def on_mouse_position_event(self, x, y, dx, dy):
        """Handle mouse movement."""
        self.imgui_renderer.mouse_position_event(x, y, dx, dy)

        if self.mouse_captured:
            # Update camera rotation
            self.camera.yaw += dx * self.mouse_sensitivity
            self.camera.pitch -= dy * self.mouse_sensitivity

            # Clamp pitch
            self.camera.pitch = max(-89.0, min(89.0, self.camera.pitch))

            self.camera.update_vectors()

    def on_mouse_drag_event(self, x, y, dx, dy):
        """Handle mouse drag."""
        self.imgui_renderer.mouse_drag_event(x, y, dx, dy)

    def on_mouse_scroll_event(self, x_offset, y_offset):
        """Handle mouse scroll."""
        self.imgui_renderer.mouse_scroll_event(x_offset, y_offset)

    def on_mouse_press_event(self, x, y, button):
        """Handle mouse press."""
        self.imgui_renderer.mouse_press_event(x, y, button)

    def on_mouse_release_event(self, x: int, y: int, button: int):
        """Handle mouse release."""
        self.imgui_renderer.mouse_release_event(x, y, button)

    def on_unicode_char_entered(self, char):
        """Handle unicode character input."""
        self.imgui_renderer.unicode_char_entered(char)


if __name__ == "__main__":
    SkyboxTestWindow.run()
