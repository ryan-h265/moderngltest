"""Skybox data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import moderngl
import numpy as np
from pyrr import Matrix44

from .time_of_day import TimeOfDaySystem
from .skybox_config import SkyboxConfig, WeatherConfig


@dataclass
class Skybox:
    """
    Container for skybox configuration and resources.

    Supports multiple skybox types:
    - Static cubemap textures
    - Procedural atmospheric scattering
    - Dynamic time-of-day systems
    - Weather effects (clouds, fog, precipitation)
    - Star fields
    - Hybrid combinations
    """

    texture: moderngl.TextureCube
    name: str = "Skybox"
    intensity: float = 1.0
    rotation: Matrix44 = field(default_factory=Matrix44.identity)
    shader_variant: str = "cubemap"
    uniforms: Dict[str, Any] = field(default_factory=dict)

    # Advanced features
    config: Optional[SkyboxConfig] = None
    time_of_day: Optional[TimeOfDaySystem] = None
    weather: Optional[WeatherConfig] = None

    def set_rotation_from_euler(self, yaw: float = 0.0, pitch: float = 0.0, roll: float = 0.0) -> None:
        """Update the rotation matrix from Euler angles (degrees)."""
        yaw_rad = np.radians(yaw)
        pitch_rad = np.radians(pitch)
        roll_rad = np.radians(roll)

        rot_yaw = Matrix44.from_y_rotation(yaw_rad)
        rot_pitch = Matrix44.from_x_rotation(pitch_rad)
        rot_roll = Matrix44.from_z_rotation(roll_rad)

        self.rotation = rot_roll * rot_pitch * rot_yaw

    def rotation_matrix(self) -> Matrix44:
        """Return the current rotation matrix as numpy array."""
        return self.rotation

    def set_uniform(self, name: str, value: Any) -> None:
        """Store a custom uniform value."""
        self.uniforms[name] = value

    def get_uniform(self, name: str, default: Any = None) -> Any:
        """Retrieve a previously stored uniform value."""
        return self.uniforms.get(name, default)

    def update(self, delta_time: float) -> None:
        """
        Update skybox animations and time-based effects.

        Args:
            delta_time: Time elapsed since last update (seconds)
        """
        if self.time_of_day is not None:
            self.time_of_day.update(delta_time)

    def get_shader_uniforms(self) -> Dict[str, Any]:
        """
        Get all shader uniforms for this skybox.

        Returns:
            Dictionary of uniform names to values
        """
        uniforms = dict(self.uniforms)

        # Add time-of-day uniforms
        if self.time_of_day is not None:
            sun = self.time_of_day.get_sun_position()
            moon = self.time_of_day.get_moon_position()

            uniforms.update({
                "u_time_of_day": self.time_of_day.time,
                "u_sun_direction": (
                    np.cos(sun.elevation) * np.cos(sun.azimuth),
                    np.sin(sun.elevation),
                    np.cos(sun.elevation) * np.sin(sun.azimuth),
                ),
                "u_sun_color": tuple(sun.color),
                "u_sun_intensity": sun.intensity,
                "u_moon_direction": (
                    np.cos(moon.elevation) * np.cos(moon.azimuth),
                    np.sin(moon.elevation),
                    np.cos(moon.elevation) * np.sin(moon.azimuth),
                ),
                "u_moon_color": tuple(moon.color),
                "u_moon_intensity": moon.intensity,
                "u_star_visibility": self.time_of_day.get_star_visibility(),
                "u_sky_color_zenith": tuple(self.time_of_day.get_sky_color_zenith()),
                "u_sky_color_horizon": tuple(self.time_of_day.get_sky_color_horizon()),
            })

        # Add weather uniforms
        if self.weather is not None:
            uniforms.update({
                "u_cloud_coverage": self.weather.cloud_coverage,
                "u_cloud_speed": self.weather.cloud_speed,
                "u_cloud_density": self.weather.cloud_density,
                "u_precipitation": self.weather.precipitation,
                "u_wind_speed": self.weather.wind_speed,
                "u_wind_direction": self.weather.wind_direction,
            })

        # Add config-based uniforms
        if self.config is not None:
            if self.config.atmospheric.enabled:
                uniforms.update({
                    "u_rayleigh_coefficient": self.config.atmospheric.rayleigh_coefficient,
                    "u_mie_coefficient": self.config.atmospheric.mie_coefficient,
                    "u_sun_brightness": self.config.atmospheric.sun_brightness,
                    "u_turbidity": self.config.atmospheric.turbidity,
                })

            if self.config.stars.enabled:
                uniforms.update({
                    "u_star_density": self.config.stars.density,
                    "u_star_brightness": self.config.stars.brightness,
                    "u_star_size": self.config.stars.size,
                    "u_star_twinkle": 1.0 if self.config.stars.twinkle else 0.0,
                })

            if self.config.fog.enabled:
                uniforms.update({
                    "fogEnabled": 1,
                    "fogColor": self.config.fog.color,
                    "fogDensity": self.config.fog.density,
                    "fogStart": self.config.fog.start,
                    "fogEnd": self.config.fog.end,
                })

            # Add custom uniforms from config
            uniforms.update(self.config.custom_uniforms)

        return uniforms

    @classmethod
    def solid_color(
        cls,
        ctx: moderngl.Context,
        color: Tuple[float, float, float],
        name: str = "Solid Sky",
    ) -> "Skybox":
        """Create a skybox using a solid color for all faces."""
        r = max(0, min(1, color[0]))
        g = max(0, min(1, color[1]))
        b = max(0, min(1, color[2]))
        pixel = bytes([int(r * 255), int(g * 255), int(b * 255)])
        data = pixel * 1  # single pixel

        texture = ctx.texture_cube((1, 1), components=3)
        for face in range(6):
            texture.write(face, data)
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        texture.build_mipmaps()
        return cls(texture=texture, name=name)

    @classmethod
    def aurora(
        cls,
        ctx: moderngl.Context,
        name: str = "Aurora Sky",
        aurora_direction: Tuple[float, float, float] = (-0.5, -0.6, 0.9),
    ) -> "Skybox":
        """Create an aurora procedural skybox configuration."""
        # We still allocate a cubemap to keep the rendering pipeline uniform.
        base = cls.solid_color(ctx, (0.0, 0.0, 0.0), name=name)
        base.shader_variant = "aurora"
        base.uniforms.update(
            {
                "u_transitionAlpha": 1.0,
                "u_auroraDir": aurora_direction,
                "fogEnabled": 1,
                "fogColor": (0.05, 0.1, 0.2),
                "fogStrength": 0.35,
                "fogStart": 0.0,
                "fogEnd": 1.0,
            }
        )
        return base

    @classmethod
    def from_config(
        cls,
        ctx: moderngl.Context,
        config: SkyboxConfig,
        texture: Optional[moderngl.TextureCube] = None,
        name: Optional[str] = None,
    ) -> "Skybox":
        """
        Create a skybox from configuration.

        Args:
            ctx: ModernGL context
            config: Skybox configuration
            texture: Optional pre-loaded cubemap texture (if None, creates a black cubemap)
            name: Optional name override

        Returns:
            Configured Skybox instance
        """
        # Create or use provided texture
        if texture is None:
            # Create a default black cubemap
            texture = cls.solid_color(ctx, (0.0, 0.0, 0.0)).texture

        skybox = cls(
            texture=texture,
            name=name or f"{config.type.capitalize()} Sky",
            intensity=config.intensity,
            shader_variant=config.get_shader_variant(),
            config=config,
        )

        # Set rotation
        skybox.set_rotation_from_euler(*config.rotation)

        # Initialize time-of-day system if enabled
        if config.time_of_day.enabled:
            skybox.time_of_day = TimeOfDaySystem(
                current_time=config.time_of_day.current_time,
                auto_progress=config.time_of_day.auto_progress,
                time_speed=config.time_of_day.speed,
                latitude=config.time_of_day.latitude,
                sun_intensity=config.time_of_day.sun_intensity,
                moon_intensity=config.time_of_day.moon_intensity,
            )

        # Set weather configuration
        skybox.weather = config.weather

        return skybox
