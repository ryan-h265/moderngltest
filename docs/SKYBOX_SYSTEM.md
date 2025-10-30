# Skybox System Documentation

## Overview

The ModernGL game engine features an industry-standard skybox system with support for:
- **Static cubemap textures** - Traditional skybox rendering
- **Atmospheric scattering** - Physically-based Preetham model for realistic skies
- **Dynamic time-of-day** - Automated day/night cycles with sun and moon
- **Weather effects** - Procedural clouds, fog, and precipitation
- **Star fields** - Rotating stars with configurable density and brightness
- **Hybrid mode** - Combines all features for maximum realism

## Architecture

### Core Components

```
src/gamelib/
├── core/
│   ├── skybox.py              # Skybox data structure
│   ├── skybox_config.py       # Configuration dataclasses
│   └── time_of_day.py         # Time-of-day system
├── rendering/
│   └── skybox_renderer.py     # Multi-variant skybox renderer
└── loaders/
    └── scene_loader.py        # JSON-based skybox loading

assets/shaders/
├── skybox.vert                # Skybox vertex shader
├── skybox_cubemap.frag        # Static cubemap fragment shader
├── skybox_atmospheric.frag    # Atmospheric scattering shader
├── skybox_hybrid.frag         # Full-featured hybrid shader
└── aurora_skybox.frag         # Legacy procedural aurora shader
```

## Scene JSON Configuration

Skyboxes are defined in scene JSON files under the `"skybox"` key. Each scene can have its own unique skybox configuration.

### Minimal Configuration

```json
{
  "skybox": {
    "type": "cubemap",
    "asset": "assets/skyboxes/my_sky",
    "intensity": 1.0
  }
}
```

### Complete Configuration

```json
{
  "skybox": {
    "type": "hybrid",
    "asset": "assets/skyboxes/my_sky",
    "intensity": 1.0,
    "rotation": [0.0, 45.0, 0.0],
    "time_of_day": {
      "enabled": true,
      "current_time": 0.5,
      "auto_progress": true,
      "speed": 1.0,
      "latitude": 45.0,
      "sun_intensity": 1.0,
      "moon_intensity": 0.3
    },
    "weather": {
      "type": "clear",
      "cloud_coverage": 0.3,
      "cloud_speed": 1.0,
      "cloud_density": 0.5,
      "precipitation": 0.0,
      "wind_speed": 1.0,
      "wind_direction": [1.0, 0.0]
    },
    "atmospheric": {
      "enabled": true,
      "rayleigh_coefficient": [5.8e-6, 13.5e-6, 33.1e-6],
      "mie_coefficient": 2.1e-5,
      "sun_brightness": 20.0,
      "turbidity": 2.0
    },
    "stars": {
      "enabled": true,
      "density": 1000,
      "brightness": 1.0,
      "size": 1.0,
      "rotation_speed": 0.1,
      "twinkle": true,
      "twinkle_speed": 1.0
    },
    "fog": {
      "enabled": false,
      "color": [0.5, 0.6, 0.7],
      "density": 0.02,
      "start": 0.0,
      "end": 100.0
    },
    "transitions": {
      "enabled": true,
      "duration": 2.0,
      "interpolation": "smoothstep"
    }
  }
}
```

## Configuration Reference

### Skybox Types

| Type | Description | Shaders Used |
|------|-------------|--------------|
| `cubemap` | Static cubemap texture | `skybox_cubemap.frag` |
| `atmospheric` | Physically-based atmospheric scattering | `skybox_atmospheric.frag` |
| `procedural` | Procedural aurora/northern lights | `aurora_skybox.frag` |
| `hybrid` | All features combined | `skybox_hybrid.frag` |

### Basic Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | `"cubemap"` | Skybox type (see table above) |
| `asset` | string | `null` | Path to cubemap folder (for cubemap type) |
| `intensity` | float | `1.0` | Brightness multiplier |
| `rotation` | [yaw, pitch, roll] | `[0, 0, 0]` | Rotation in degrees |

### Time of Day Configuration

Controls dynamic day/night cycles, sun/moon positioning, and celestial calculations.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | `true` | Enable time-of-day system |
| `current_time` | float | `0.5` | Current time (0.0=midnight, 0.5=noon, 1.0=midnight) |
| `auto_progress` | bool | `false` | Automatically advance time |
| `speed` | float | `1.0` | Time progression speed multiplier |
| `latitude` | float | `45.0` | Geographic latitude for sun angle calculations |
| `sun_intensity` | float | `1.0` | Sun brightness multiplier |
| `moon_intensity` | float | `0.3` | Moon brightness multiplier |

**Time Ranges:**
- **0.0 - 0.2**: Night
- **0.2 - 0.27**: Dawn
- **0.27 - 0.7**: Day
- **0.7 - 0.77**: Dusk
- **0.77 - 1.0**: Night

### Weather Configuration

Controls cloud coverage, density, wind, and precipitation.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | `"clear"` | Weather type: `clear`, `cloudy`, `overcast`, `stormy`, `rainy`, `snowy` |
| `cloud_coverage` | float | `0.0` | Cloud coverage (0.0-1.0) |
| `cloud_speed` | float | `1.0` | Cloud animation speed |
| `cloud_density` | float | `0.5` | Cloud opacity/thickness |
| `precipitation` | float | `0.0` | Precipitation intensity (0.0-1.0) |
| `wind_speed` | float | `1.0` | Wind speed affecting clouds |
| `wind_direction` | [x, y] | `[1.0, 0.0]` | 2D wind direction vector |

### Atmospheric Configuration

Physically-based atmospheric scattering parameters (Preetham model).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | `true` | Enable atmospheric scattering |
| `rayleigh_coefficient` | [R, G, B] | `[5.8e-6, 13.5e-6, 33.1e-6]` | Rayleigh scattering coefficients (wavelength-dependent) |
| `mie_coefficient` | float | `2.1e-5` | Mie scattering coefficient (aerosols) |
| `sun_brightness` | float | `20.0` | Sun intensity for scattering |
| `turbidity` | float | `2.0` | Atmospheric turbidity (haze/pollution, 1-10) |

**Turbidity Guide:**
- `1.0-2.0`: Clear sky
- `2.0-4.0`: Slightly hazy
- `4.0-7.0`: Hazy/polluted
- `7.0-10.0`: Very hazy

### Star Field Configuration

Procedural star field with rotation and twinkling.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | `true` | Enable star rendering |
| `density` | int | `1000` | Number of stars |
| `brightness` | float | `1.0` | Star brightness multiplier |
| `size` | float | `1.0` | Star size multiplier |
| `rotation_speed` | float | `0.1` | Star rotation speed based on time |
| `twinkle` | bool | `true` | Enable star twinkling |
| `twinkle_speed` | float | `1.0` | Twinkle animation speed |

### Fog Configuration

Atmospheric fog rendered in the skybox.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | `false` | Enable fog |
| `color` | [R, G, B] | `[0.5, 0.6, 0.7]` | Fog color (0.0-1.0) |
| `density` | float | `0.02` | Fog density |
| `start` | float | `0.0` | Fog start distance |
| `end` | float | `100.0` | Fog end distance |

### Transitions Configuration

Smooth transitions between skybox states (future feature).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | `true` | Enable transitions |
| `duration` | float | `2.0` | Transition duration in seconds |
| `interpolation` | string | `"smoothstep"` | Interpolation type: `linear`, `smoothstep`, `cosine` |

## Programming API

### Creating Skyboxes Programmatically

```python
from gamelib.core.skybox import Skybox
from gamelib.core.skybox_config import SkyboxConfig

# From configuration
config = SkyboxConfig(
    type="atmospheric",
    intensity=1.2,
    time_of_day=TimeOfDayConfig(
        current_time=0.6,
        auto_progress=True
    )
)
skybox = Skybox.from_config(ctx, config)

# Or use factory methods
skybox = Skybox.solid_color(ctx, (0.3, 0.5, 0.9))
skybox = Skybox.aurora(ctx, name="Northern Lights")
```

### Updating Skybox at Runtime

```python
# Update time of day
if skybox.time_of_day:
    skybox.time_of_day.time = 0.75  # Sunset
    skybox.time_of_day.auto_progress = True

# Update weather
if skybox.weather:
    skybox.weather.cloud_coverage = 0.8
    skybox.weather.type = "stormy"

# Update rotation
skybox.set_rotation_from_euler(yaw=45.0)

# Update each frame
skybox.update(delta_time)
```

### Accessing Time-of-Day Information

```python
if skybox.time_of_day:
    sun = skybox.time_of_day.get_sun_position()
    print(f"Sun elevation: {sun.elevation}")
    print(f"Sun color: {sun.color}")

    period = skybox.time_of_day.get_time_period()  # "dawn", "day", "dusk", "night"
    time_str = skybox.time_of_day.get_time_of_day_string()  # "14:30"
```

## Example Configurations

### Clear Day Sky

```json
{
  "skybox": {
    "type": "atmospheric",
    "intensity": 1.2,
    "time_of_day": {
      "enabled": true,
      "current_time": 0.5,
      "sun_intensity": 1.2
    },
    "atmospheric": {
      "enabled": true,
      "turbidity": 2.0
    }
  }
}
```

### Sunset with Clouds

```json
{
  "skybox": {
    "type": "hybrid",
    "intensity": 1.0,
    "time_of_day": {
      "enabled": true,
      "current_time": 0.75
    },
    "weather": {
      "cloud_coverage": 0.4,
      "cloud_speed": 0.5
    }
  }
}
```

### Stormy Night

```json
{
  "skybox": {
    "type": "hybrid",
    "intensity": 0.6,
    "time_of_day": {
      "enabled": true,
      "current_time": 0.1
    },
    "weather": {
      "type": "stormy",
      "cloud_coverage": 0.9,
      "cloud_density": 0.8,
      "precipitation": 0.8
    },
    "fog": {
      "enabled": true,
      "color": [0.2, 0.2, 0.3],
      "density": 0.1
    }
  }
}
```

### Animated Day/Night Cycle

```json
{
  "skybox": {
    "type": "hybrid",
    "time_of_day": {
      "enabled": true,
      "current_time": 0.0,
      "auto_progress": true,
      "speed": 10.0
    },
    "stars": {
      "enabled": true,
      "density": 2000,
      "brightness": 1.5
    }
  }
}
```

## Performance Considerations

### Shader Complexity

| Skybox Type | Performance Impact | Use Case |
|-------------|-------------------|----------|
| `cubemap` | Very Low | Static environments, background scenes |
| `atmospheric` | Medium | Dynamic lighting without weather |
| `procedural` | Medium | Special effects (aurora) |
| `hybrid` | High | Full-featured realistic environments |

### Optimization Tips

1. **Use cubemap for static scenes** - Pre-bake atmospheric effects into cubemap textures
2. **Reduce star density** - Lower `density` values for better performance
3. **Disable unused features** - Set `enabled: false` for features you don't need
4. **Lower cloud quality** - Reduce cloud coverage and density for stormy scenes
5. **Disable auto-progression** - Only enable `auto_progress` when needed

## Troubleshooting

### Skybox not appearing
- Check that scene JSON has `"skybox"` key defined
- Verify shader compilation succeeded (check console for errors)
- Ensure `intensity > 0.0`

### Black skybox
- For `cubemap` type, verify `asset` path points to valid cubemap directory
- Check that cubemap folder contains 6 face images (px, nx, py, ny, pz, nz)

### Stars not visible
- Ensure `stars.enabled: true`
- Set `current_time` to night period (< 0.2 or > 0.77)
- Increase `stars.brightness` if too dim

### Clouds not rendering
- Only works with `hybrid` type
- Ensure `cloud_coverage > 0.0`
- Check `weather.enabled` is not blocking rendering

## Implementation Details

### Shader Switching

The `SkyboxRenderer` automatically selects the appropriate shader based on `skybox.shader_variant`:

```python
shader_variant = skybox.shader_variant  # "cubemap", "atmospheric", "hybrid", etc.
program = self.programs.get(shader_variant)
```

### Uniform Updates

All skybox parameters are passed to shaders as uniforms. The `Skybox.get_shader_uniforms()` method collects all relevant uniforms:

- Time-of-day: `u_time_of_day`, `u_sun_direction`, `u_moon_direction`, etc.
- Weather: `u_cloud_coverage`, `u_wind_direction`, etc.
- Atmospheric: `u_rayleigh_coefficient`, `u_turbidity`, etc.
- Stars: `u_star_visibility`, `u_star_density`, etc.

### Depth Testing

Skyboxes are rendered with special depth handling to ensure they always appear behind scene geometry:

```python
gl_Position = vec4(clip_position.xy, clip_position.w, clip_position.w);  // Set z = w for max depth
```

## Future Enhancements

Planned features for future versions:
- ✓ HDR skybox support
- ✓ Atmospheric scattering
- ✓ Dynamic time-of-day
- ✓ Weather transitions
- ✓ Procedural clouds
- ☐ Volumetric clouds with ray marching
- ☐ Lightning effects for storms
- ☐ Aurora customization (colors, intensity patterns)
- ☐ Cloud shadow projection onto terrain
- ☐ Real-time skybox blending/transitions
- ☐ Sky dome mesh support (alternative to cubemap)
- ☐ GPU-based star generation

## References

- **Preetham Model**: "A Practical Analytic Model for Daylight" (SIGGRAPH 1999)
- **Bruneton Model**: "Precomputed Atmospheric Scattering" (EGSR 2008)
- **Industry Standards**: Unreal Engine Sky Atmosphere, Unity Sky System

---

**See Also:**
- `docs/ARCHITECTURE.md` - Overall engine architecture
- `docs/SHADER_GUIDE.md` - Shader programming guide
- `assets/scenes/` - Example scene configurations
