# Donut Terrain Generation - Usage Guide

This guide explains how to use the donut terrain generation feature in your ModernGL engine.

## Overview

The donut terrain feature creates a procedurally generated ring-shaped terrain with:
- **Flat walkable surface** on the top rim
- **Smooth slopes** on inner and outer edges
- **Procedural noise** for natural variation
- **Proper lighting** with calculated normals
- **Angular variation** for visual interest

## Quick Start

### Option 1: Use the Pre-made Scene

Switch to the donut terrain scene in [main.py](main.py:79):

```python
# Change this line:
loaded_scene = self.scene_manager.load("default", camera=self.camera)

# To this:
loaded_scene = self.scene_manager.load("donut_terrain", camera=self.camera)
```

Then run:
```bash
python main.py
```

### Option 2: Create Your Own Scene

Create a JSON scene file with the donut terrain primitive:

```json
{
  "name": "my_terrain_scene",
  "camera": {
    "position": [0.0, 150.0, 300.0],
    "target": [0.0, 0.0, 0.0]
  },
  "objects": [
    {
      "name": "MyDonutTerrain",
      "type": "primitive",
      "primitive": "donut_terrain",
      "position": [0.0, 0.0, 0.0],
      "color": [0.4, 0.6, 0.3],
      "resolution": 128,
      "outer_radius": 200.0,
      "inner_radius": 80.0,
      "height": 50.0,
      "rim_width": 40.0,
      "seed": 42
    }
  ],
  "lights": [
    {
      "type": "directional",
      "position": [100.0, 200.0, 100.0],
      "target": [0.0, 0.0, 0.0],
      "color": [1.0, 1.0, 1.0],
      "intensity": 3.5,
      "cast_shadows": true
    }
  ]
}
```

## Configuration Parameters

### Required Parameters
- **`primitive`**: Must be `"donut_terrain"`
- **`type`**: Must be `"primitive"`

### Optional Parameters (with defaults)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `resolution` | 128 | Grid resolution (vertices per edge). Higher = more detail but slower. Recommended: 64-256 |
| `outer_radius` | 200.0 | Outer radius of the donut in world units |
| `inner_radius` | 80.0 | Inner radius (size of the hole) in world units |
| `height` | 50.0 | Maximum height of the rim above ground level |
| `rim_width` | 40.0 | Width parameter for the flat top surface |
| `seed` | 42 | Random seed for procedural noise (change for different terrain) |
| `color` | [1.0, 1.0, 1.0] | RGB color for the terrain (0.0-1.0 range) |
| `position` | [0.0, 0.0, 0.0] | World position of the terrain center |

### Bounding Radius
The `bounding_radius` is auto-calculated if not provided. For custom values:
```
bounding_radius ≈ sqrt(outer_radius² + height²)
```

## Examples

### Small, Detailed Donut
```json
{
  "primitive": "donut_terrain",
  "resolution": 256,
  "outer_radius": 100.0,
  "inner_radius": 40.0,
  "height": 30.0,
  "seed": 12345
}
```

### Large, Low-Detail Donut (Performance)
```json
{
  "primitive": "donut_terrain",
  "resolution": 64,
  "outer_radius": 500.0,
  "inner_radius": 200.0,
  "height": 100.0
}
```

### Different Terrain Variations (Seeds)
```json
// Variation 1
{"primitive": "donut_terrain", "seed": 42}

// Variation 2
{"primitive": "donut_terrain", "seed": 1337}

// Variation 3
{"primitive": "donut_terrain", "seed": 9999}
```

## Camera Positioning

For best viewing, position the camera to see the entire donut:

```json
"camera": {
  "position": [0.0, height * 3, outer_radius * 1.5],
  "target": [0.0, 0.0, 0.0]
}
```

Example for default parameters (height=50, outer_radius=200):
```json
"camera": {
  "position": [0.0, 150.0, 300.0],
  "target": [0.0, 0.0, 0.0]
}
```

## Performance Considerations

**Resolution vs Performance:**
- `resolution: 64` - Fast, suitable for background terrain (~4K vertices)
- `resolution: 128` - Good balance (~16K vertices) **[Recommended]**
- `resolution: 256` - High detail, slower (~65K vertices)
- `resolution: 512` - Very high detail, may be slow (~262K vertices)

**Optimization Tips:**
1. Use lower resolution for distant/background terrain
2. Frustum culling is enabled by default (objects outside view are skipped)
3. The terrain uses indexed rendering for efficiency

## Technical Details

### Terrain Generation Algorithm

The donut terrain is generated using:
1. **Height Field Generation**: 2D grid of height values based on distance from center
2. **Rim Profile**: Flat top surface with smooth slopes
3. **Fractal Noise**: Multi-octave noise for natural variation
4. **Angular Variation**: Sine wave modulation creates lobed shapes

### Mesh Generation
- **Vertices**: `resolution² vertices` with position + normal attributes
- **Triangles**: `2 × (resolution-1)² triangles` forming the terrain surface
- **Normals**: Calculated using finite differences for proper lighting
- **Rendering**: Indexed triangle list for efficiency

## Files Modified/Created

### Created Files
- `src/gamelib/core/terrain_generation.py` - Noise functions and height generation
- `assets/scenes/donut_terrain_scene.json` - Example donut terrain scene

### Modified Files
- `src/gamelib/core/geometry_utils.py` - Added `donut_terrain()` function
- `src/gamelib/loaders/scene_loader.py` - Added donut_terrain primitive support
- `main.py` - Registered donut_terrain scene

## Integration with Other Features

The donut terrain works seamlessly with:
- ✅ **Lighting**: Full support for directional/point lights
- ✅ **Shadows**: Can cast and receive shadows
- ✅ **Frustum Culling**: Automatically culled when outside view
- ✅ **Scene JSON**: Define via JSON like other primitives
- ✅ **PBR Materials**: Uses flat color shading (can be extended)

## Troubleshooting

**Issue: Terrain appears flat or incorrect**
- Check that `outer_radius > inner_radius`
- Ensure `height > 0`
- Verify the camera is positioned to see the terrain

**Issue: Performance is slow**
- Reduce `resolution` parameter (try 64 or 96)
- Check that frustum culling is enabled
- Ensure SSAO and other post-processing effects are optimized

**Issue: Lighting looks wrong**
- Normals are auto-calculated - check that lights are positioned correctly
- Try adjusting light `intensity` values
- Ensure at least one light has `cast_shadows: true`

## Advanced Usage

### Combining Multiple Terrains

You can create multiple donut terrains with different seeds:

```json
"objects": [
  {
    "name": "Terrain1",
    "primitive": "donut_terrain",
    "outer_radius": 150.0,
    "seed": 42
  },
  {
    "name": "Terrain2",
    "primitive": "donut_terrain",
    "position": [500.0, 0.0, 0.0],
    "outer_radius": 120.0,
    "seed": 9999
  }
]
```

### Custom Colors

Use the `color` parameter for varied terrain:

```json
{
  "primitive": "donut_terrain",
  "color": [0.6, 0.4, 0.3]  // Sandy/desert color
}
```

## Future Enhancements

Possible improvements (not yet implemented):
- Texture mapping support
- Multiple biomes with color blending
- Real-time terrain modification
- Chunk-based infinite terrain
- Collision mesh generation
- Water/lava in the center hole

## References

- Original terrain code: `pandas_terrain_generation.py`
- ModernGL docs: https://moderngl.readthedocs.io/
- pyrr (math library): https://pyrr.readthedocs.io/
