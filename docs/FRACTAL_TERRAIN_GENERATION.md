# Fractal Terrain Generation

Pure-Python implementation of Perlin noise and fractal Brownian motion (fBm) for procedural terrain generation.

## Module: `src/gamelib/fractal_perlin`

### Features
- **Pure Python + NumPy**: No external C dependencies
- **Deterministic**: Same seed produces identical output
- **Multi-resolution**: Sample the same continuous noise field at different resolutions
- **Presets**: Mountainous, rolling hills, plateau configurations
- **Export formats**: `.npz` (compressed NumPy), optional JSON metadata, OBJ mesh

### API

```python
from src.gamelib.fractal_perlin import (
    perlin, fbm, generate_noise_grid, 
    save_heightmap, export_obj, PRESETS
)

# Basic noise functions
noise_value = perlin(x=1.5, y=2.3, seed=42)
fractal_value = fbm(x=1.5, y=2.3, octaves=6, persistence=0.55, lacunarity=2.1, seed=42)

# Generate a complete heightmap grid
heights, metadata = generate_noise_grid(
    resolution=100,
    preset='mountainous',  # or 'rolling', 'plateau'
    seed=42,
    world_size=400.0
)

# Save heightmap
save_heightmap('assets/heightmaps/terrain.npz', heights, metadata)

# Export OBJ mesh (optional)
export_obj('assets/heightmaps/terrain.obj', heights, world_size=400.0)

# Load heightmap
import numpy as np
import json
data = np.load('assets/heightmaps/terrain.npz')
heights = data['heights']
meta = json.loads(str(data['meta']))
```

### Presets

| Preset | Scale | Octaves | Persistence | Lacunarity | Amplitude | Description |
|--------|-------|---------|-------------|------------|-----------|-------------|
| `mountainous` | 0.006 | 6 | 0.55 | 2.1 | 120.0 | Sharp peaks, dramatic terrain like Mt. Everest |
| `rolling` | 0.02 | 4 | 0.5 | 2.0 | 30.0 | Gentle rolling hills |
| `plateau` | 0.01 | 5 | 0.6 | 2.0 | 60.0 | Flat-topped elevated regions |

## CLI Generator: `examples/generate_fractal_scene.py`

Generate heightmaps and scene JSON files from the command line.

### Usage

```bash
# Basic usage (mountainous preset, resolution 100)
PYTHONPATH=. python3 examples/generate_fractal_scene.py

# Custom parameters
PYTHONPATH=. python3 examples/generate_fractal_scene.py \
  --preset mountainous \
  --res 256 \
  --seed 42 \
  --world-size 400 \
  --out assets/heightmaps \
  --obj \
  --json

# Rolling hills at lower resolution
PYTHONPATH=. python3 examples/generate_fractal_scene.py \
  --preset rolling \
  --res 128 \
  --seed 12345
```

### CLI Options

- `--preset`: Choose from `mountainous`, `rolling`, `plateau` (default: `mountainous`)
- `--res`: Resolution per axis (default: `100`)
- `--seed`: Random seed for reproducibility (default: `42`)
- `--world-size`: World size in units (default: `400.0`)
- `--out`: Output directory (default: `assets/heightmaps`)
- `--name`: Custom filename base (defaults to auto-generated)
- `--obj`: Export OBJ mesh alongside .npz
- `--json`: Export JSON metadata file

### Output Files

The generator creates:
1. **Heightmap**: `assets/heightmaps/fractal_<preset>_r<res>_s<seed>.npz`
   - Compressed NumPy array with `heights` (float32) and `meta` (JSON string)
2. **Scene JSON**: `assets/scenes/fractal_terrain_scene.json`
   - References the heightmap file with relative path
   - Contains generation metadata
3. **OBJ mesh** (if `--obj`): `assets/heightmaps/fractal_<preset>_r<res>_s<seed>.obj`
4. **JSON metadata** (if `--json`): `assets/heightmaps/fractal_<preset>_r<res>_s<seed>.json`

## Scene Format

The generated `assets/scenes/fractal_terrain_scene.json`:

```json
{
  "type": "fractal_terrain_scene",
  "heightmap": "../heightmaps/fractal_mountainous_r100_s42.npz",
  "metadata": {
    "resolution": 100,
    "scale": 0.006,
    "world_size": 400.0,
    "preset": "mountainous",
    "seed": 42,
    "octaves": 6,
    "persistence": 0.55,
    "lacunarity": 2.1,
    "amplitude": 120.0
  },
  "objects": []
}
```

## Multi-Resolution Support

Generate the same terrain at different resolutions by using the same seed and parameters:

```bash
# Low-res preview
PYTHONPATH=. python3 examples/generate_fractal_scene.py --res 50 --seed 42 --name preview

# Medium quality
PYTHONPATH=. python3 examples/generate_fractal_scene.py --res 256 --seed 42 --name medium

# High detail
PYTHONPATH=. python3 examples/generate_fractal_scene.py --res 1024 --seed 42 --name high
```

All three will show the same terrain features at different levels of detail.

## Testing

Run the test suite:

```bash
PYTHONPATH=. python3 -m pytest tests/test_fractal_perlin.py -v
```

Tests cover:
- Perlin noise value ranges and determinism
- fBm normalization and octave effects
- Grid generation with all presets
- Save/load roundtrip accuracy
- OBJ export vertex and face counts

## Integration with Existing Code

### Option 1: Use `generate_fractal_terrain()` directly

The easiest way to generate natural terrain from `terrain_generation.py`:

```python
from src.gamelib.core.terrain_generation import generate_fractal_terrain

# Generate mountainous terrain
heights = generate_fractal_terrain(
    resolution=256,
    world_size=400.0,
    preset='mountainous',
    seed=42
)

# Or with custom parameters
heights = generate_fractal_terrain(
    resolution=256,
    world_size=400.0,
    preset=None,  # Disable preset
    octaves=6,
    persistence=0.55,
    lacunarity=2.1,
    amplitude=120.0,
    scale=0.006,
    seed=42
)
```

### Option 2: Use Perlin noise in existing functions

The existing `generate_donut_height_data` and `fractal_noise` functions now support an optional `use_perlin=True` parameter for higher-quality noise:

```python
from src.gamelib.core.terrain_generation import generate_donut_height_data, fractal_noise

# Generate donut terrain with Perlin-based noise
heights = generate_donut_height_data(
    resolution=256,
    outer_radius=200,
    inner_radius=80,
    height=50,
    seed=42,
    use_perlin=True  # Use high-quality Perlin noise
)

# Use Perlin-based fractal noise directly
noise_value = fractal_noise(
    x=1.5,
    y=2.3,
    octaves=4,
    persistence=0.5,
    lacunarity=2.0,
    seed=42,
    use_perlin=True  # Use Perlin instead of sine-based noise
)
```

**Backward Compatibility**: All existing code continues to work without changes. The `use_perlin` parameter defaults to `False`, so the original sine-based noise is used unless explicitly requested.

### Option 3: Load Baked Heightmaps in Game Engine

Use the provided loader example to load pre-generated heightmaps:

```bash
# Run the loader example
PYTHONPATH=. python3 examples/load_fractal_terrain.py
```

The loader provides vertex, normal, and index arrays ready for ModernGL:

```python
from examples.load_fractal_terrain import load_heightmap, build_terrain_mesh_data

# Load heightmap
heights, meta = load_heightmap('assets/heightmaps/fractal_mountainous_r100_s42.npz')

# Build mesh data
vertices, normals, indices = build_terrain_mesh_data(heights, meta['world_size'])

# Create ModernGL buffers and VAO
vbo_vertices = ctx.buffer(vertices.tobytes())
vbo_normals = ctx.buffer(normals.tobytes())
ibo = ctx.buffer(indices.tobytes())

vao = ctx.vertex_array(program, [
    (vbo_vertices, '3f', 'in_position'),
    (vbo_normals, '3f', 'in_normal'),
], index_buffer=ibo)

# Render
vao.render()
```

See `examples/load_fractal_terrain.py` for a complete working example.

## Performance

- **Resolution 100**: ~50-100ms generation time
- **Resolution 256**: ~500ms-1s generation time
- **Resolution 512**: ~3-5s generation time
- **Resolution 1024**: ~15-30s generation time

Generation is single-threaded. For large resolutions, consider running the generator script once and loading the baked `.npz` at runtime (instantaneous).

## Future Enhancements

- Add more presets (canyon, valley, islands)
- Optional erosion simulation
- Biome blending (mix multiple noise layers)
- Normal map generation
- GPU-accelerated noise generation
- glTF export with materials and LODs
