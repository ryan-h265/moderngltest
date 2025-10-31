"""Time of day system for dynamic sky and lighting."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

import numpy as np
from pyrr import Vector3


@dataclass
class CelestialBody:
    """Represents a celestial body (sun or moon) with position and properties."""

    azimuth: float  # Horizontal angle (radians)
    elevation: float  # Vertical angle (radians)
    intensity: float  # Brightness multiplier
    color: Vector3  # RGB color


class TimeOfDaySystem:
    """
    Manages time-of-day progression and celestial calculations.

    Time is represented as a normalized value from 0.0 to 1.0:
    - 0.0 = Midnight
    - 0.25 = Sunrise (6 AM)
    - 0.5 = Noon
    - 0.75 = Sunset (6 PM)
    - 1.0 = Midnight

    Provides sun/moon positions, sky colors, and time-based transitions
    for industry-standard dynamic skybox rendering.
    """

    # Time period boundaries
    NIGHT_END = 0.20  # 4:48 AM
    DAWN_END = 0.27  # 6:28 AM
    DAY_END = 0.70  # 4:48 PM
    DUSK_END = 0.77  # 6:28 PM

    def __init__(
        self,
        current_time: float = 0.5,
        auto_progress: bool = False,
        time_speed: float = 1.0,
        latitude: float = 45.0,
        sun_intensity: float = 1.0,
        moon_intensity: float = 0.3,
    ):
        """
        Initialize the time of day system.

        Args:
            current_time: Initial time (0.0-1.0, where 0.5 is noon)
            auto_progress: If True, time progresses automatically
            time_speed: Speed multiplier for time progression
            latitude: Latitude for celestial calculations (degrees)
            sun_intensity: Base intensity multiplier for the sun
            moon_intensity: Base intensity multiplier for the moon
        """
        self._time = self._normalize_time(current_time)
        self._auto_progress = auto_progress
        self._time_speed = time_speed
        self._latitude = math.radians(latitude)
        self._sun_intensity = sun_intensity
        self._moon_intensity = moon_intensity

    @property
    def time(self) -> float:
        """Get current time of day (0.0-1.0)."""
        return self._time

    @time.setter
    def time(self, value: float):
        """Set current time of day (0.0-1.0)."""
        self._time = self._normalize_time(value)

    @property
    def auto_progress(self) -> bool:
        """Check if time progresses automatically."""
        return self._auto_progress

    @auto_progress.setter
    def auto_progress(self, value: bool):
        """Enable or disable automatic time progression."""
        self._auto_progress = value

    @property
    def time_speed(self) -> float:
        """Get time progression speed multiplier."""
        return self._time_speed

    @time_speed.setter
    def time_speed(self, value: float):
        """Set time progression speed multiplier."""
        self._time_speed = max(0.0, value)

    def update(self, delta_time: float) -> None:
        """
        Update the time of day system.

        Args:
            delta_time: Time elapsed since last update (seconds)
        """
        if self._auto_progress:
            # Progress time based on delta and speed
            # Full day cycle in 24 real minutes at speed=1.0
            time_increment = (delta_time / (24.0 * 60.0)) * self._time_speed
            self._time = self._normalize_time(self._time + time_increment)

    def get_sun_position(self) -> CelestialBody:
        """
        Calculate the sun's position and properties.

        Returns:
            CelestialBody with sun's azimuth, elevation, intensity, and color
        """
        # Sun elevation: -90° at midnight, +90° at noon
        sun_elevation = math.sin((self._time - 0.25) * 2.0 * math.pi) * (math.pi / 2.0)

        # Sun azimuth: rises in east (90°), sets in west (270°)
        sun_azimuth = (self._time * 2.0 * math.pi) - math.pi

        # Sun intensity based on elevation
        sun_intensity = max(0.0, math.sin(sun_elevation)) * self._sun_intensity

        # Sun color transitions (warm at horizon, white at zenith)
        if sun_elevation < 0:
            # Sun below horizon
            sun_color = Vector3([0.0, 0.0, 0.0])
        elif sun_elevation < math.radians(5):
            # Sunrise/sunset - warm orange/red
            t = sun_elevation / math.radians(5)
            sun_color = Vector3([
                1.0,
                0.4 + 0.4 * t,
                0.1 + 0.3 * t,
            ])
        elif sun_elevation < math.radians(30):
            # Early morning/evening - warm yellow
            t = (sun_elevation - math.radians(5)) / math.radians(25)
            sun_color = Vector3([
                1.0,
                0.8 + 0.2 * t,
                0.4 + 0.6 * t,
            ])
        else:
            # Day - white/slightly warm
            sun_color = Vector3([1.0, 1.0, 0.95])

        return CelestialBody(
            azimuth=sun_azimuth,
            elevation=sun_elevation,
            intensity=sun_intensity,
            color=sun_color,
        )

    def get_moon_position(self) -> CelestialBody:
        """
        Calculate the moon's position and properties.

        Returns:
            CelestialBody with moon's azimuth, elevation, intensity, and color
        """
        # Moon is opposite the sun (offset by 0.5 in time)
        moon_time = self._normalize_time(self._time + 0.5)
        moon_elevation = math.sin((moon_time - 0.25) * 2.0 * math.pi) * (math.pi / 2.0)
        moon_azimuth = (moon_time * 2.0 * math.pi) - math.pi

        # Moon intensity based on elevation
        moon_intensity = max(0.0, math.sin(moon_elevation)) * self._moon_intensity

        # Moon is cool blue-white
        moon_color = Vector3([0.8, 0.8, 1.0])

        return CelestialBody(
            azimuth=moon_azimuth,
            elevation=moon_elevation,
            intensity=moon_intensity,
            color=moon_color,
        )

    def get_ambient_color(self) -> Vector3:
        """
        Calculate ambient light color based on time of day.

        Returns:
            RGB color for ambient lighting
        """
        sun = self.get_sun_position()
        moon = self.get_moon_position()

        if sun.elevation > 0:
            # Daytime ambient
            t = min(1.0, sun.elevation / math.radians(30))
            return Vector3([
                0.4 + 0.3 * t,
                0.5 + 0.3 * t,
                0.6 + 0.3 * t,
            ])
        elif moon.elevation > 0:
            # Nighttime ambient (cool blue)
            t = min(1.0, moon.elevation / math.radians(30))
            return Vector3([
                0.05 + 0.1 * t,
                0.05 + 0.15 * t,
                0.1 + 0.2 * t,
            ])
        else:
            # Deep night (very dark)
            return Vector3([0.02, 0.02, 0.05])

    def get_sky_color_zenith(self) -> Vector3:
        """
        Calculate sky color at zenith (top of sky dome).

        Returns:
            RGB color for zenith
        """
        sun = self.get_sun_position()

        if sun.elevation > math.radians(10):
            # Clear day sky - deep blue
            t = min(1.0, (sun.elevation - math.radians(10)) / math.radians(70))
            return Vector3([
                0.2 + 0.1 * t,
                0.4 + 0.2 * t,
                0.7 + 0.3 * t,
            ])
        elif sun.elevation > math.radians(-5):
            # Twilight - purple/orange gradient
            t = (sun.elevation + math.radians(5)) / math.radians(15)
            return Vector3([
                0.3 + 0.2 * t,
                0.1 + 0.3 * t,
                0.4 + 0.3 * t,
            ])
        else:
            # Night sky - very dark blue
            return Vector3([0.01, 0.01, 0.05])

    def get_sky_color_horizon(self) -> Vector3:
        """
        Calculate sky color at horizon.

        Returns:
            RGB color for horizon
        """
        sun = self.get_sun_position()

        if sun.elevation > math.radians(10):
            # Day - lighter blue at horizon
            t = min(1.0, (sun.elevation - math.radians(10)) / math.radians(70))
            return Vector3([
                0.6 + 0.2 * t,
                0.7 + 0.2 * t,
                0.9 + 0.1 * t,
            ])
        elif sun.elevation > math.radians(-5):
            # Sunrise/sunset - warm colors
            t = (sun.elevation + math.radians(5)) / math.radians(15)
            return Vector3([
                1.0,
                0.4 + 0.4 * t,
                0.2 + 0.3 * t,
            ])
        else:
            # Night horizon - slightly lighter than zenith
            return Vector3([0.05, 0.05, 0.1])

    def get_fog_color(self) -> Vector3:
        """
        Calculate fog color based on time of day.

        Returns:
            RGB color for atmospheric fog
        """
        # Fog color similar to horizon but slightly desaturated
        horizon = self.get_sky_color_horizon()
        return horizon * 0.9

    def get_star_visibility(self) -> float:
        """
        Calculate star visibility factor (0.0 = invisible, 1.0 = fully visible).

        Returns:
            Star visibility multiplier
        """
        sun = self.get_sun_position()

        # Stars fade out as sun rises
        if sun.elevation > math.radians(0):
            return 0.0
        elif sun.elevation > math.radians(-15):
            # Twilight - stars fading
            t = 1.0 - (sun.elevation + math.radians(15)) / math.radians(15)
            return t
        else:
            # Full night
            return 1.0

    def get_time_period(self) -> str:
        """
        Get the current time period name.

        Returns:
            One of: "night", "dawn", "day", "dusk"
        """
        if self._time < self.NIGHT_END or self._time >= self.DUSK_END:
            return "night"
        elif self._time < self.DAWN_END:
            return "dawn"
        elif self._time < self.DAY_END:
            return "day"
        else:
            return "dusk"

    def get_time_of_day_string(self) -> str:
        """
        Get a human-readable time string.

        Returns:
            Time in 24-hour format (e.g., "14:30")
        """
        hours = int(self._time * 24)
        minutes = int((self._time * 24 - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    @staticmethod
    def _normalize_time(time: float) -> float:
        """Normalize time to 0.0-1.0 range."""
        return time % 1.0

    def to_dict(self) -> dict:
        """
        Serialize time of day configuration to dictionary.

        Returns:
            Configuration dictionary
        """
        return {
            "current_time": self._time,
            "auto_progress": self._auto_progress,
            "speed": self._time_speed,
            "latitude": math.degrees(self._latitude),
            "sun_intensity": self._sun_intensity,
            "moon_intensity": self._moon_intensity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimeOfDaySystem":
        """
        Create TimeOfDaySystem from configuration dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            TimeOfDaySystem instance
        """
        return cls(
            current_time=data.get("current_time", 0.5),
            auto_progress=data.get("auto_progress", False),
            time_speed=data.get("speed", 1.0),
            latitude=data.get("latitude", 45.0),
            sun_intensity=data.get("sun_intensity", 1.0),
            moon_intensity=data.get("moon_intensity", 0.3),
        )
