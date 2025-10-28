# Fractal Terrain Quick Reference

## Generate Terrain (CLI)

```bash
# Basic - mountainous terrain, resolution 100
PYTHONPATH=. python3 examples/generate_fractal_scene.py

# Custom parameters
PYTHONPATH=. python3 examples/generate_fractal_scene.py \
  --preset mountainous \
  --res 256 \
  --seed 42 \
  --world-size 400 \
  --obj \
  --json
```

## Load Terrain (Python)

```python
# Load heightmap
from examples.load_fractal_terrain import load_heightmap, build_terrain_mesh_data
heights, meta = load_heightmap('assets/heightmaps/fractal_mountainous_r100_s42.npz')
vertices, normals, indices = build_terrain_mesh_data(heights, meta['world_size'])

# Use in ModernGL
vbo_v = ctx.buffer(vertices.tobytes())
vbo_n = ctx.buffer(normals.tobytes())
ibo = ctx.buffer(indices.tobytes())
vao = ctx.vertex_array(program, [
    (vbo_v, '3f', 'in_position'),
    (vbo_n, '3f', 'in_normal'),
], index_buffer=ibo)
vao.render()
```

## Generate Terrain (Python)

```python
# Option 1: New function (Perlin-based)
from src.gamelib.core.terrain_generation import generate_fractal_terrain
heights = generate_fractal_terrain(resolution=256, preset='mountainous', seed=42)

# Option 2: Existing function with Perlin
from src.gamelib.core.terrain_generation import generate_donut_height_data
heights = generate_donut_height_data(resolution=256, use_perlin=True, seed=42)

# Option 3: Direct from fractal_perlin
from src.gamelib.fractal_perlin import generate_noise_grid, save_heightmap
heights, meta = generate_noise_grid(resolution=256, preset='mountainous', seed=42)
save_heightmap('my_terrain.npz', heights, meta)
```

## Presets

- `mountainous` - Dramatic peaks (Mt. Everest style), ±120 units
- `rolling` - Gentle hills, ±30 units  
- `plateau` - Flat-topped mesas, ±60 units

## Test

```bash
# Run all terrain tests
PYTHONPATH=. python3 -m pytest tests/test_fractal_perlin.py tests/test_terrain_integration.py -v
```

## Files

- **Module**: `src/gamelib/fractal_perlin/__init__.py`
- **Integration**: `src/gamelib/core/terrain_generation.py`
- **CLI**: `examples/generate_fractal_scene.py`
- **Loader**: `examples/load_fractal_terrain.py`
- **Docs**: `docs/FRACTAL_TERRAIN_GENERATION.md`
- **Summary**: `FRACTAL_TERRAIN_COMPLETE.md`
