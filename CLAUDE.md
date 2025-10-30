# CLAUDE.md

## Project Overview

ModernGL 3D game engine with multi-light shadow mapping. Built using ModernGL, featuring a modular architecture with Command Pattern input system and two-pass shadow rendering. Pybullet for physics and collision detection. Semi-procedural terrian generation (Fractal perlin noise saved to json files)

**Stack**: Python 3.12, ModernGL (OpenGL 4.1 for macOS compatibility), pyrr, moderngl-window

## Development Commands

### Running the Engine
```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Run the main engine
python main.py
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_camera.py

# Run with verbose output
python -m pytest -v tests/
```

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install dev dependencies (includes pytest)
pip install -r requirements-dev.txt
```

## Architecture Overview

### Package Structure
```
src/gamelib/
├── config/          # Centralized settings (window, rendering, camera, lighting)
├── core/            # Camera, Light, Scene - fundamental engine components
├── rendering/       # RenderPipeline, ShaderManager, ShadowRenderer, MainRenderer
├── input/           # Command Pattern input system with InputManager and controllers
└── loaders/         # GLTF/GLB model loading with PBR material support
```

### Key Architectural Patterns

**Command Pattern Input System** (`src/gamelib/input/`)
- InputManager translates raw keyboard/mouse events into InputCommands
- Controllers (CameraController, etc.) register handlers for specific commands
- InputContext filters commands based on game state (gameplay, menu, etc.)
- Three command types: CONTINUOUS (held), INSTANT (pressed once), AXIS (mouse delta)
- Key bindings are rebindable via KeyBindings class

**Frustum Culling** (`src/gamelib/core/frustum.py`)
- Automatically skips rendering objects outside the camera's view frustum
- Uses bounding sphere tests for each SceneObject
- Applied in geometry pass, shadow passes, and main rendering
- Enable/disable via `ENABLE_FRUSTUM_CULLING` in settings.py
- Provides 30-70% performance improvement depending on camera angle

**Two-Pass Shadow Rendering**
1. **Shadow Pass**: RenderPipeline → ShadowRenderer renders scene from each light's perspective to generate depth maps
2. **Main Pass**: MainRenderer renders final scene with lighting, using shadow maps to determine shadowing

**Scene Management**
- Scene contains SceneObjects AND Model instances (unified rendering)
- SceneObjects: Primitives (cubes, spheres, pyramids) with flat colors
- Models: GLTF/GLB loaded models with PBR materials and textures
- Scene.create_default_scene() creates mixed scene (primitives + GLTF models)
- Automatic shader switching based on object type (textured vs flat-color)

### Important Implementation Details

**Camera System** (`src/gamelib/core/camera.py`)
- Uses yaw/pitch Euler angles to calculate front/right/up vectors
- `update_vectors()` must be called after position changes to recalculate target
- Movement is relative to camera orientation (forward = camera's front direction)
- Pitch is clamped between MIN_PITCH and MAX_PITCH to prevent gimbal lock

**Light System** (`src/gamelib/core/light.py`)
- Each Light has its own shadow map (depth texture + framebuffer)
- `get_light_matrix()` returns view-projection matrix for shadow mapping
- Shadow maps initialized via `RenderPipeline.initialize_lights(lights)`
- Supports animated lights (e.g., `light.animate_rotation(time)`)

**Shader Management**
- Shaders loaded from `assets/shaders/` as external .vert/.frag files
- ShaderManager compiles and caches shader programs
- Shadow shaders: `shadow_depth.{vert,frag}` - depth-only rendering
- Main shaders: `main_lighting.{vert,frag}` - multi-light with PCF soft shadows

**Input Flow** (see `docs/INPUT_SYSTEM.md` for details)
```
main.py (raw events)
  → InputManager.on_key_press/on_mouse_move
  → InputManager translates to InputCommand via KeyBindings
  → InputManager dispatches to registered controller handlers
  → Controller modifies Camera/Scene/etc.
```

### Configuration (`src/gamelib/config/settings.py`)

All constants are centralized here:
- WINDOW_SIZE, GL_VERSION (4, 1 for macOS compatibility)
- SHADOW_MAP_SIZE (default 2048x2048)
- MAX_LIGHTS (currently supports up to 4)
- CAMERA_SPEED, MOUSE_SENSITIVITY, DEFAULT_FOV
- AMBIENT_STRENGTH, SHADOW_BIAS for lighting tuning

When modifying behavior, check settings.py first before hardcoding values.

## Common Development Patterns

### Adding a Primitive Object to Scene
```python
# In Scene.create_default_scene() or create a new scene method:
cube = SceneObject(
    geometry=geometry.cube(size=(2.0, 2.0, 2.0)),
    position=Vector3([x, y, z]),
    color=(r, g, b),  # RGB 0.0-1.0
    bounding_radius=1.5  # For frustum culling (optional, defaults to 1.0)
)
self.objects.append(cube)
```

### Loading a GLTF/GLB Model
```python
# In Scene.create_default_scene() (requires self.ctx to be set):
from ..loaders import GltfLoader
from ..config.settings import PROJECT_ROOT

loader = GltfLoader(self.ctx)
model = loader.load(str(PROJECT_ROOT / "assets/models/props/japanese_stone_lantern/scene.gltf"))

# Position and scale
model.position = Vector3([0.0, 0.0, 0.0])
model.scale = Vector3([2.0, 2.0, 2.0])  # Scale up 2x
model.rotation = Vector3([0.0, math.radians(45), 0.0])  # Rotate 45° around Y-axis

# Add to scene (works alongside primitives)
self.add_object(model)

# The model will:
# - Use textured shaders automatically during geometry pass
# - Cast shadows in shadow pass
# - Be frustum culled like primitives
# - Receive proper lighting in deferred lighting pass
```

**Available Models:**
- `assets/models/props/japanese_stone_lantern/scene.gltf` - 4 meshes, PBR materials
- `assets/models/props/tent/scene.gltf` - Simple tent model
- `assets/models/props/japanese_bar/scene.gltf` - Large building with hierarchy

**See [docs/MODEL_LOADING.md](docs/MODEL_LOADING.md) for complete GLTF loading guide.**

### Adding a New Input Command
1. Add command to `InputCommand` enum in `input_commands.py`
2. Add key binding in `KeyBindings.__init__()` in `key_bindings.py`
3. Register handler in controller (e.g., `CameraController`)
4. Implement handler method in controller

### Modifying Shaders
- Edit `.vert` or `.frag` files in `assets/shaders/`
- Shader changes are hot-loaded on restart (no recompilation needed)
- Use `#version 410` for macOS compatibility (OpenGL 4.1 max)

### Adding a New Light
```python
# In Game._create_lights():
new_light = Light(
    position=Vector3([x, y, z]),
    target=Vector3([0.0, 0.0, 0.0]),
    color=Vector3([r, g, b]),
    intensity=1.0,
    light_type='directional'
)
return [light1, light2, new_light]

# Then in __init__, call:
self.render_pipeline.initialize_lights(self.lights)
```

## Testing Conventions

- Tests in `tests/` mirror package structure
- Use pytest fixtures for setup/teardown
- Tests focus on core logic (Camera, Light, Scene), not rendering (requires GL context)
- Mock ModernGL context when testing rendering components

## OpenGL Version Constraints

**IMPORTANT**: This project targets OpenGL 4.1 (macOS maximum).
- GLSL shaders must use `#version 410` or lower
- Avoid features from OpenGL 4.2+ (e.g., layout qualifiers for atomic counters)
- Test on macOS M1 if possible, or verify shader compatibility

## Shadow Mapping Tuning

If experiencing shadow artifacts:
- **Shadow acne** (striping): Increase `SHADOW_BIAS` in settings or shader
- **Peter panning** (detached shadows): Decrease `SHADOW_BIAS`
- **Jagged shadows**: Increase `SHADOW_MAP_SIZE` (performance trade-off)
- **Missing shadows**: Check light position, verify objects in light frustum, increase ortho bounds

## Documentation

Comprehensive docs in `docs/`:
- `ARCHITECTURE.md` - Detailed module responsibilities and data flow
- `INPUT_SYSTEM.md` - Command Pattern input architecture
- `MULTI_LIGHT_IMPLEMENTATION.md` - Shadow mapping implementation
- `SHADER_GUIDE.md` - Shader programming guide
- `ROADMAP.md` - Future features and milestones

## Notes

Dont git add and commit after you've not confirmed something as working or further changes required.

ModernGL/OpenGL expects column-major layout where the translation components are in the bottom row, not the right column
