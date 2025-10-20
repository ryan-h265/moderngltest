# Quick Reference Guide

Fast reference for common tasks with the refactored codebase.

---

## Running the Engine

```bash
# Main engine (default scene)
python main.py

# Simple example (3 cubes)
python examples/simple_scene.py

# Basic example (18 cubes)
python examples/basic_scene.py
```

---

## Common Imports

```python
# Configuration
from src.gamelib.config.settings import SHADOW_MAP_SIZE, MAX_LIGHTS

# Core components
from src.gamelib import Camera, Light, Scene, SceneObject

# Rendering
from src.gamelib import RenderPipeline

# Input
from src.gamelib import InputHandler

# Direct imports
from src.gamelib.core.camera import Camera
from src.gamelib.core.light import Light
from src.gamelib.core.scene import Scene
from src.gamelib.rendering.render_pipeline import RenderPipeline
```

---

## Creating a Camera

```python
from pyrr import Vector3
from src.gamelib import Camera

camera = Camera(
    position=Vector3([0.0, 5.0, 10.0]),
    target=Vector3([0.0, 0.0, 0.0]),  # optional
    speed=5.0,                         # units per second
    sensitivity=0.1                    # mouse sensitivity
)

# Get matrices
view_matrix = camera.get_view_matrix()
projection_matrix = camera.get_projection_matrix(aspect_ratio=16/9)

# Update camera
camera.process_mouse_movement(dx, dy)
camera.process_keyboard(keys_pressed, frametime)
camera.update_vectors()  # Call after changing yaw/pitch
```

---

## Creating Lights

```python
from pyrr import Vector3
from src.gamelib import Light

# Directional light (like sun)
light = Light(
    position=Vector3([5.0, 10.0, 5.0]),
    target=Vector3([0.0, 0.0, 0.0]),
    color=Vector3([1.0, 1.0, 1.0]),  # RGB (0-1)
    intensity=1.0,                    # multiplier
    light_type='directional'
)

# Animate rotation
light.animate_rotation(time, radius=12.0, height=10.0, speed=0.5)

# Manual control
light.set_position(x, y, z)
light.set_color(r, g, b)
light.set_intensity(0.8)
```

---

## Creating a Scene

```python
from pyrr import Vector3
from moderngl_window import geometry
from src.gamelib import Scene, SceneObject

scene = Scene()

# Use default scene (18 cubes)
scene.create_default_scene()

# Or create custom objects
obj = SceneObject(
    geom=geometry.cube(size=(2.0, 2.0, 2.0)),
    position=Vector3([0.0, 1.0, 0.0]),
    color=(0.8, 0.3, 0.3)  # RGB tuple
)
scene.add_object(obj)

# Clear scene
scene.clear()
```

---

## Setting Up Rendering

```python
from src.gamelib import RenderPipeline

# Create pipeline
pipeline = RenderPipeline(ctx, window)

# Initialize lights with shadow maps
pipeline.initialize_lights(lights)

# Render frame
pipeline.render_frame(scene, camera, lights)
```

---

## Handling Input

```python
from src.gamelib import InputHandler

input_handler = InputHandler(camera)

# In event handlers
def on_key_event(self, key, action, modifiers):
    if action == self.wnd.keys.ACTION_PRESS:
        input_handler.on_key_press(key)
    elif action == self.wnd.keys.ACTION_RELEASE:
        input_handler.on_key_release(key)

def on_mouse_position_event(self, _x, _y, dx, dy):
    input_handler.on_mouse_move(dx, dy)

# In update loop
def on_update(self, time, frametime):
    input_handler.update(frametime)
    camera.update_vectors()

# Toggle mouse capture
captured = input_handler.toggle_mouse_capture()
```

---

## Modifying Settings

Edit `src/gamelib/config/settings.py`:

```python
# Window
WINDOW_SIZE = (1920, 1080)
WINDOW_TITLE = "My Game"

# Shadows
SHADOW_MAP_SIZE = 4096  # Higher = sharper, slower
MAX_LIGHTS = 4          # More lights supported

# Camera
DEFAULT_CAMERA_SPEED = 10.0
MOUSE_SENSITIVITY = 0.2

# Lighting
AMBIENT_STRENGTH = 0.3  # Brighter ambient
```

---

## Working with Shaders

### Loading Shaders

```python
from src.gamelib.rendering.shader_manager import ShaderManager

shader_mgr = ShaderManager(ctx)
shader_mgr.load_program("myshader", "myshader.vert", "myshader.frag")
program = shader_mgr.get("myshader")
```

### Shader File Location

Place in `assets/shaders/`:
- `myshader.vert` - Vertex shader
- `myshader.frag` - Fragment shader

### Example Shader

```glsl
// assets/shaders/myshader.vert
#version 410

uniform mat4 projection;
uniform mat4 view;
uniform mat4 model;

in vec3 in_position;

void main() {
    gl_Position = projection * view * model * vec4(in_position, 1.0);
}
```

---

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_camera.py

# With coverage
pytest --cov=src/gamelib

# Verbose output
pytest -v
```

---

## File Locations

| What | Where |
|------|-------|
| Main entry point | `main.py` |
| Configuration | `src/gamelib/config/settings.py` |
| Camera | `src/gamelib/core/camera.py` |
| Light | `src/gamelib/core/light.py` |
| Scene | `src/gamelib/core/scene.py` |
| Shaders | `assets/shaders/*.{vert,frag}` |
| Rendering | `src/gamelib/rendering/` |
| Input | `src/gamelib/input/input_handler.py` |
| Tests | `tests/` |
| Examples | `examples/` |
| Docs | `docs/` |

---

## Common Tasks

### Add a New Cube

```python
scene.add_object(SceneObject(
    geometry.cube(size=(1.0, 1.0, 1.0)),
    Vector3([x, y, z]),
    (r, g, b)  # color
))
```

### Add a Third Light

```python
light3 = Light(
    position=Vector3([0.0, 8.0, -10.0]),
    target=Vector3([0.0, 0.0, 0.0]),
    color=Vector3([0.5, 0.5, 1.0]),  # Blue
    intensity=0.6
)
lights.append(light3)

# Don't forget to update settings.py:
MAX_LIGHTS = 3

# And update shader #define:
# In main_lighting.{vert,frag}: #define MAX_LIGHTS 3
```

### Change Shadow Quality

```python
# In settings.py
SHADOW_MAP_SIZE = 4096  # Sharper (slower)
SHADOW_MAP_SIZE = 1024  # Faster (blockier)
```

### Change Camera Speed

```python
# In settings.py
DEFAULT_CAMERA_SPEED = 10.0  # Faster

# Or dynamically:
camera.speed = 10.0
```

---

## Troubleshooting

### Import Errors

Make sure you're in the project root:
```bash
cd /path/to/3dlibtesting
python main.py
```

### Shader Not Found

Check shader path:
```python
# In settings.py
print(SHADERS_DIR)  # Should be: /path/to/assets/shaders
```

### Performance Issues

1. Reduce shadow map size in `settings.py`
2. Reduce number of lights
3. Disable PCF soft shadows (edit shader)

### Black Screen

Check:
- Lights are positioned above scene
- Camera is not inside geometry
- Ambient strength > 0 in settings

---

## Keyboard Controls

| Key | Action |
|-----|--------|
| W | Forward |
| S | Backward |
| A | Left |
| D | Right |
| Q | Down |
| E | Up |
| Mouse | Look around |
| ESC | Toggle mouse capture |

---

## Documentation

- **Architecture**: `docs/ARCHITECTURE.md`
- **Roadmap**: `docs/ROADMAP.md`
- **Shaders**: `docs/SHADER_GUIDE.md`
- **Multi-Light**: `docs/MULTI_LIGHT_IMPLEMENTATION.md`
- **Refactoring**: `REFACTORING_SUMMARY.md`

---

## Getting Help

1. Check `docs/ARCHITECTURE.md` for system overview
2. Look at `examples/` for working code
3. Read module docstrings in code
4. Check `tests/` for usage examples

---

**Quick Reference v0.2.0**
