# Using Fractal Perlin Terrain in main.py

## ✅ What Was Added

### 1. Heightmap Terrain Loading Support
Added `heightmap_terrain()` function to `src/gamelib/core/geometry_utils.py`:
- Loads `.npz` heightmap files
- Builds vertices, normals, and indices
- Returns ModernGL-compatible VAO

### 2. Scene Loader Integration
Updated `src/gamelib/loaders/scene_loader.py`:
- Added `heightmap_terrain` primitive type
- Calculates bounding radius from heightmap data
- Resolves heightmap paths relative to scene file

### 3. Scene JSON Created
Created `assets/scenes/fractal_mountainous_scene.json`:
- References the generated heightmap
- Includes directional lights optimized for terrain
- Camera positioned for good terrain view
- Physics collision support ready

### 4. Main.py Registration
Updated `main.py` to register the new scene:
```python
self.scene_manager.register_scene("fractal_mountainous", 
                                  "assets/scenes/fractal_mountainous_scene.json")
```

## 🚀 How to Use It

### Option 1: Load Fractal Terrain Scene Directly

Change this line in `main.py`:
```python
loaded_scene = self.scene_manager.load("default", camera=self.camera)
```

To:
```python
loaded_scene = self.scene_manager.load("fractal_mountainous", camera=self.camera)
```

### Option 2: Switch Scenes at Runtime (Future)

You can add a key binding to switch scenes:
```python
def switch_to_fractal_terrain(self):
    loaded_scene = self.scene_manager.load("fractal_mountainous", camera=self.camera)
    self.scene = loaded_scene.scene
    self.lights = loaded_scene.lights
    self.render_pipeline.initialize_lights(self.lights, self.camera)
```

### Option 3: Add to Existing Scene

You can also manually add terrain objects to your default scene by updating `assets/scenes/default_scene.json`:

```json
{
  "objects": [
    {
      "name": "Fractal Terrain",
      "type": "heightmap_terrain",
      "heightmap": "../heightmaps/fractal_mountainous_r100_s42.npz",
      "color": [0.4, 0.6, 0.3]
    }
  ]
}
```

## 📋 Scene JSON Format

The fractal terrain scene uses this structure:

```json
{
  "name": "Scene Name",
  "camera": {
    "position": [x, y, z],
    "target": [x, y, z]
  },
  "lights": [...],
  "objects": [
    {
      "name": "Terrain Name",
      "type": "heightmap_terrain",
      "heightmap": "../heightmaps/your_heightmap.npz",
      "color": [r, g, b],
      "extras": {
        "physics": {
          "enabled": true,
          "body_type": "static",
          "collision_shape": "mesh"
        }
      }
    }
  ]
}
```

## 🧪 Quick Test

Run the game with the fractal terrain:

```bash
# 1. Make sure the heightmap exists
ls -lh assets/heightmaps/fractal_mountainous_r100_s42.npz

# 2. Update main.py to load fractal_mountainous scene (see Option 1 above)

# 3. Run the game
python main.py
```

## 🎮 Controls

Once loaded:
- **WASD** - Move camera
- **Q/E** - Move up/down
- **Mouse** - Look around
- **ESC** - Toggle mouse capture
- **F** - Toggle debug camera (if you added the toggle)

## 🔍 What to Expect

When you load the fractal mountainous scene, you should see:
- **Dramatic mountain terrain** with peaks and valleys
- **Green coloring** (adjustable via `color` in scene JSON)
- **Two directional lights** (warm sun + cool fill)
- **Shadows** from the main light (if shadows enabled)
- **Camera** positioned at [0, 80, 150] looking at terrain
- **Physics collision** (if physics enabled and player spawned)

## 🎨 Customization

### Change Terrain Color
Edit `assets/scenes/fractal_mountainous_scene.json`:
```json
"color": [0.5, 0.4, 0.3]  // Brown/desert
"color": [0.8, 0.8, 0.8]  // Snow/white
"color": [0.3, 0.3, 0.4]  // Rocky/gray
```

### Use Different Heightmap
Generate a new one:
```bash
PYTHONPATH=. python3 examples/generate_fractal_scene.py \
  --preset rolling \
  --res 256 \
  --seed 99 \
  --name my_terrain
```

Then update scene JSON:
```json
"heightmap": "../heightmaps/my_terrain.npz"
```

### Adjust Lighting
Edit the `lights` array in scene JSON:
```json
{
  "type": "directional",
  "position": [100, 200, 100],
  "intensity": 1.5,
  "color": [1.0, 0.9, 0.8]  // Warm sunset
}
```

## 🐛 Troubleshooting

### "Heightmap not found"
- Run the generator first: `PYTHONPATH=. python3 examples/generate_fractal_scene.py`
- Check the path in scene JSON is relative to the scene file location

### Terrain Not Visible
- Check camera position in scene JSON
- Increase terrain resolution: `--res 256`
- Adjust lighting intensity

### Low Frame Rate
- Reduce heightmap resolution (use 100 instead of 256+)
- Disable shadows on secondary lights
- Reduce shadow map size

### Physics Not Working
- Ensure `physics_world` is initialized in `main.py`
- Check `extras.physics.enabled` is `true` in scene JSON
- Note: mesh collisions can be expensive for high-res terrain

## 📊 Performance Tips

| Resolution | Vertices | Triangles | Performance |
|-----------|----------|-----------|-------------|
| 50 | 2,500 | 4,802 | Excellent |
| 100 | 10,000 | 19,602 | Very Good |
| 256 | 65,536 | 130,050 | Good |
| 512 | 262,144 | 521,218 | Moderate |

**Recommendation**: Use resolution 100-256 for real-time gameplay.

## 🔮 Next Steps

1. **Try it out**: Load the fractal_mountainous scene in main.py
2. **Generate more terrains**: Create rolling hills, plateaus, different seeds
3. **Add skybox**: The scene looks better with atmospheric effects
4. **Add props**: Place trees, rocks, buildings on the terrain
5. **Implement LOD**: For larger terrains, add level-of-detail system

## ✨ Example Scenes You Can Create

```bash
# Rolling hills
PYTHONPATH=. python3 examples/generate_fractal_scene.py \
  --preset rolling --res 256 --seed 42 --name rolling_hills

# Plateau canyon
PYTHONPATH=. python3 examples/generate_fractal_scene.py \
  --preset plateau --res 256 --seed 123 --name canyon

# Different mountain ranges (same preset, different seeds)
PYTHONPATH=. python3 examples/generate_fractal_scene.py \
  --preset mountainous --res 256 --seed 1 --name mountains_alps
  
PYTHONPATH=. python3 examples/generate_fractal_scene.py \
  --preset mountainous --res 256 --seed 2 --name mountains_rockies
```

Then create scene JSONs for each and switch between them!

---

**Everything is ready to go! Just change the scene name in `main.py` and run it.** 🎉
