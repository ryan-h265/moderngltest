"""Skybox configuration structures for JSON-based scene definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pyrr import Vector3


@dataclass
class TimeOfDayConfig:
    """Time of day configuration."""

    enabled: bool = True
    current_time: float = 0.5  # 0.0-1.0 (0.5 = noon)
    auto_progress: bool = False
    speed: float = 1.0
    latitude: float = 45.0
    sun_intensity: float = 1.0
    moon_intensity: float = 0.3

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "TimeOfDayConfig":
        """Create configuration from dictionary."""
        if data is None:
            return cls()
        return cls(
            enabled=data.get("enabled", True),
            current_time=data.get("current_time", 0.5),
            auto_progress=data.get("auto_progress", False),
            speed=data.get("speed", 1.0),
            latitude=data.get("latitude", 45.0),
            sun_intensity=data.get("sun_intensity", 1.0),
            moon_intensity=data.get("moon_intensity", 0.3),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "current_time": self.current_time,
            "auto_progress": self.auto_progress,
            "speed": self.speed,
            "latitude": self.latitude,
            "sun_intensity": self.sun_intensity,
            "moon_intensity": self.moon_intensity,
        }


@dataclass
class WeatherConfig:
    """Weather effects configuration."""

    type: str = "clear"  # clear, cloudy, overcast, stormy, rainy, snowy
    cloud_coverage: float = 0.0  # 0.0-1.0
    cloud_speed: float = 1.0
    cloud_density: float = 0.5
    precipitation: float = 0.0  # 0.0-1.0
    wind_speed: float = 1.0
    wind_direction: Tuple[float, float] = (1.0, 0.0)  # 2D vector

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "WeatherConfig":
        """Create configuration from dictionary."""
        if data is None:
            return cls()
        return cls(
            type=data.get("type", "clear"),
            cloud_coverage=data.get("cloud_coverage", 0.0),
            cloud_speed=data.get("cloud_speed", 1.0),
            cloud_density=data.get("cloud_density", 0.5),
            precipitation=data.get("precipitation", 0.0),
            wind_speed=data.get("wind_speed", 1.0),
            wind_direction=tuple(data.get("wind_direction", [1.0, 0.0])),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "cloud_coverage": self.cloud_coverage,
            "cloud_speed": self.cloud_speed,
            "cloud_density": self.cloud_density,
            "precipitation": self.precipitation,
            "wind_speed": self.wind_speed,
            "wind_direction": list(self.wind_direction),
        }


@dataclass
class AtmosphericConfig:
    """Atmospheric scattering configuration (Preetham/Bruneton model)."""

    enabled: bool = True
    # Rayleigh scattering coefficients (wavelength-dependent)
    rayleigh_coefficient: Tuple[float, float, float] = (5.8e-6, 13.5e-6, 33.1e-6)
    # Mie scattering coefficient
    mie_coefficient: float = 21e-6
    # Sun brightness
    sun_brightness: float = 20.0
    # Atmospheric turbidity (haze/pollution)
    turbidity: float = 2.0
    # Rayleigh scale height (atmosphere thickness)
    rayleigh_scale_height: float = 8500.0
    # Mie scale height
    mie_scale_height: float = 1200.0
    # Planet radius
    planet_radius: float = 6371e3
    # Atmosphere radius
    atmosphere_radius: float = 6471e3

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "AtmosphericConfig":
        """Create configuration from dictionary."""
        if data is None:
            return cls()
        return cls(
            enabled=data.get("enabled", True),
            rayleigh_coefficient=tuple(
                data.get("rayleigh_coefficient", [5.8e-6, 13.5e-6, 33.1e-6])
            ),
            mie_coefficient=data.get("mie_coefficient", 21e-6),
            sun_brightness=data.get("sun_brightness", 20.0),
            turbidity=data.get("turbidity", 2.0),
            rayleigh_scale_height=data.get("rayleigh_scale_height", 8500.0),
            mie_scale_height=data.get("mie_scale_height", 1200.0),
            planet_radius=data.get("planet_radius", 6371e3),
            atmosphere_radius=data.get("atmosphere_radius", 6471e3),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "rayleigh_coefficient": list(self.rayleigh_coefficient),
            "mie_coefficient": self.mie_coefficient,
            "sun_brightness": self.sun_brightness,
            "turbidity": self.turbidity,
            "rayleigh_scale_height": self.rayleigh_scale_height,
            "mie_scale_height": self.mie_scale_height,
            "planet_radius": self.planet_radius,
            "atmosphere_radius": self.atmosphere_radius,
        }


@dataclass
class StarFieldConfig:
    """Star field configuration."""

    enabled: bool = True
    density: int = 1000  # Number of stars
    brightness: float = 1.0
    size: float = 1.0
    rotation_speed: float = 0.1
    twinkle: bool = True
    twinkle_speed: float = 1.0

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "StarFieldConfig":
        """Create configuration from dictionary."""
        if data is None:
            return cls()
        return cls(
            enabled=data.get("enabled", True),
            density=data.get("density", 1000),
            brightness=data.get("brightness", 1.0),
            size=data.get("size", 1.0),
            rotation_speed=data.get("rotation_speed", 0.1),
            twinkle=data.get("twinkle", True),
            twinkle_speed=data.get("twinkle_speed", 1.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "density": self.density,
            "brightness": self.brightness,
            "size": self.size,
            "rotation_speed": self.rotation_speed,
            "twinkle": self.twinkle,
            "twinkle_speed": self.twinkle_speed,
        }


@dataclass
class FogConfig:
    """Atmospheric fog configuration."""

    enabled: bool = False
    color: Tuple[float, float, float] = (0.5, 0.6, 0.7)
    density: float = 0.02
    start: float = 0.0
    end: float = 100.0

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "FogConfig":
        """Create configuration from dictionary."""
        if data is None:
            return cls()
        return cls(
            enabled=data.get("enabled", False),
            color=tuple(data.get("color", [0.5, 0.6, 0.7])),
            density=data.get("density", 0.02),
            start=data.get("start", 0.0),
            end=data.get("end", 100.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "color": list(self.color),
            "density": self.density,
            "start": self.start,
            "end": self.end,
        }


@dataclass
class TransitionConfig:
    """Skybox transition configuration."""

    enabled: bool = True
    duration: float = 2.0  # Transition duration in seconds
    interpolation: str = "smoothstep"  # linear, smoothstep, cosine

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "TransitionConfig":
        """Create configuration from dictionary."""
        if data is None:
            return cls()
        return cls(
            enabled=data.get("enabled", True),
            duration=data.get("duration", 2.0),
            interpolation=data.get("interpolation", "smoothstep"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "duration": self.duration,
            "interpolation": self.interpolation,
        }


@dataclass
class SkyboxConfig:
    """
    Complete skybox configuration for JSON-based scene definitions.

    Supports multiple skybox types:
    - "cubemap": Static cubemap texture
    - "atmospheric": Physically-based atmospheric scattering
    - "procedural": Fully procedural sky (aurora, etc.)
    - "hybrid": Combined system with all features
    """

    # Basic configuration
    type: str = "cubemap"  # cubemap, atmospheric, procedural, hybrid
    asset: Optional[str] = None  # Path to cubemap folder (for cubemap type)
    intensity: float = 1.0
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # yaw, pitch, roll in degrees

    # Feature configurations
    time_of_day: TimeOfDayConfig = field(default_factory=TimeOfDayConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    atmospheric: AtmosphericConfig = field(default_factory=AtmosphericConfig)
    stars: StarFieldConfig = field(default_factory=StarFieldConfig)
    fog: FogConfig = field(default_factory=FogConfig)
    transitions: TransitionConfig = field(default_factory=TransitionConfig)

    # Custom uniforms for shader-specific parameters
    custom_uniforms: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["SkyboxConfig"]:
        """
        Create skybox configuration from dictionary.

        Args:
            data: Configuration dictionary from JSON

        Returns:
            SkyboxConfig instance or None if data is None
        """
        if data is None:
            return None

        return cls(
            type=data.get("type", "cubemap"),
            asset=data.get("asset"),
            intensity=data.get("intensity", 1.0),
            rotation=tuple(data.get("rotation", [0.0, 0.0, 0.0])),
            time_of_day=TimeOfDayConfig.from_dict(data.get("time_of_day")),
            weather=WeatherConfig.from_dict(data.get("weather")),
            atmospheric=AtmosphericConfig.from_dict(data.get("atmospheric")),
            stars=StarFieldConfig.from_dict(data.get("stars")),
            fog=FogConfig.from_dict(data.get("fog")),
            transitions=TransitionConfig.from_dict(data.get("transitions")),
            custom_uniforms=data.get("custom_uniforms", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation
        """
        result: Dict[str, Any] = {
            "type": self.type,
            "intensity": self.intensity,
            "rotation": list(self.rotation),
            "time_of_day": self.time_of_day.to_dict(),
            "weather": self.weather.to_dict(),
            "atmospheric": self.atmospheric.to_dict(),
            "stars": self.stars.to_dict(),
            "fog": self.fog.to_dict(),
            "transitions": self.transitions.to_dict(),
        }

        if self.asset is not None:
            result["asset"] = self.asset

        if self.custom_uniforms:
            result["custom_uniforms"] = self.custom_uniforms

        return result

    def get_shader_variant(self) -> str:
        """
        Determine which shader variant to use based on configuration.

        Returns:
            Shader variant name: "cubemap", "atmospheric", "procedural", or "hybrid"
        """
        if self.type == "cubemap":
            # Pure cubemap
            return "cubemap"
        elif self.type == "atmospheric":
            # Atmospheric scattering
            return "atmospheric"
        elif self.type == "procedural":
            # Procedural sky (aurora, etc.)
            return "procedural"
        elif self.type == "hybrid":
            # Combined system
            return "hybrid"
        else:
            # Default to cubemap
            return "cubemap"

    def resolve_asset_path(self, base_path: Path) -> Optional[Path]:
        """
        Resolve asset path relative to base path.

        Args:
            base_path: Base directory for relative paths

        Returns:
            Resolved absolute path or None
        """
        if self.asset is None:
            return None

        asset_path = Path(self.asset)
        if not asset_path.is_absolute():
            asset_path = (base_path / self.asset).resolve()

        return asset_path if asset_path.exists() else None
