# Architecture Documentation

## Overview

This is a modular 3D game engine built with ModernGL, featuring multi-light shadow mapping and a clean, extensible architecture.

## Project Structure

```
3dlibtesting/
├── assets/
│   └── shaders/              # GLSL shader files
│       ├── shadow_depth.{vert,frag}
│       └── main_lighting.{vert,frag}
│
├── src/gamelib/              # Main game library package
│   ├── config/               # Configuration
│   │   └── settings.py       # All constants and settings
│   │
│   ├── core/                 # Core engine components
│   │   ├── camera.py         # Camera with FPS controls
│   │   ├── light.py          # Light sources
│   │   └── scene.py          # Scene management
│   │
│   ├── rendering/            # Rendering subsystem
│   │   ├── shader_manager.py
│   │   ├── shadow_renderer.py
│   │   ├── main_renderer.py
│   │   └── render_pipeline.py
│   │
│   └── input/                # Input handling
│       └── input_handler.py
│
├── tests/                    # Unit tests
├── examples/                 # Example scenes
├── docs/                     # Documentation
└── main.py                   # Entry point
```

## Module Responsibilities

### Config (`src/gamelib/config/`)

**settings.py**: Centralized configuration
- Window settings (size, title, GL version)
- Rendering settings (shadow map size, max lights)
- Camera settings (speed, FOV, sensitivity)
- Lighting defaults (ambient strength, bias)
- Debug and performance flags

### Core (`src/gamelib/core/`)

**camera.py**: Camera management
- Position and orientation
- FPS-style WASD + mouse controls
- View and projection matrix generation
- Pitch constraints to prevent flipping

**light.py**: Light sources
- Position, color, intensity
- Shadow map resources (texture + FBO)
- Light matrix calculation (for shadow mapping)
- Animation helpers (e.g., rotation)

**scene.py**: Scene management
- SceneObject: Individual renderable objects
- Scene: Collection of objects
- Default scene creation (18 cubes)
- Batch rendering

### Rendering (`src/gamelib/rendering/`)

**shader_manager.py**: Shader loading
- Load shaders from `.vert` and `.frag` files
- Compilation error handling
- Shader program registry

**shadow_renderer.py**: Shadow map generation
- Create shadow map textures and FBOs
- Render scene from each light's perspective
- One pass per light

**main_renderer.py**: Main scene rendering
- Bind shadow maps
- Set camera and light uniforms
- Render final scene with lighting and shadows

**render_pipeline.py**: Pipeline orchestration
- Coordinates shadow and main renderers
- Manages frame rendering sequence:
  1. Shadow passes (all lights)
  2. Main pass (with shadows)

### Input (`src/gamelib/input/`)

**input_handler.py**: Input management
- Keyboard state tracking
- Mouse capture toggle
- Integration with camera for movement

## Data Flow

### Initialization

```
main.py
  ├─> Create Camera
  ├─> Create Scene (18 cubes)
  ├─> Create Lights (2 directional)
  ├─> Create RenderPipeline
  │     ├─> ShaderManager loads shaders
  │     ├─> ShadowRenderer created
  │     └─> MainRenderer created
  └─> Initialize shadow maps for lights
```

### Frame Rendering

```
Game.on_render()
  ├─> on_update()
  │     ├─> Animate lights
  │     ├─> Process input (camera movement)
  │     └─> Update camera vectors
  │
  └─> RenderPipeline.render_frame()
        ├─> ShadowRenderer.render_shadow_maps()
        │     ├─> For each light:
        │     │     ├─> Bind light's shadow FBO
        │     │     ├─> Set light matrix
        │     │     └─> Render scene
        │
        └─> MainRenderer.render()
              ├─> Bind all shadow maps
              ├─> Set camera uniforms
              ├─> Set light uniforms
              └─> Render scene
```

### Input Flow

```
User Input
  ├─> Keyboard Press/Release
  │     └─> InputHandler tracks key state
  │           └─> Camera.process_keyboard()
  │
  └─> Mouse Movement
        └─> InputHandler.on_mouse_move()
              └─> Camera.process_mouse_movement()
                    └─> Update yaw/pitch
```

## Design Patterns

### Dependency Injection
- Components receive dependencies via constructors
- Example: `MainRenderer(ctx, shader_program)`
- Makes testing easier (can inject mocks)

### Separation of Concerns
- Each module has single responsibility
- Camera handles view, not rendering
- Renderer handles rendering, not logic
- Pipeline coordinates, doesn't implement

### Configuration Over Code
- Settings in `settings.py`, not hardcoded
- Easy to tweak without editing logic
- Supports different configurations

### Modular Architecture
- Can replace components independently
- Example: Swap MainRenderer without touching Camera
- New features (SSAO, CSM) add new modules

## Extension Points

### Adding New Shader Effects

1. Add shader files to `assets/shaders/`
2. Load in `ShaderManager`
3. Create renderer in `rendering/`
4. Integrate into `RenderPipeline`

Example (SSAO):
```python
# In RenderPipeline.__init__()
self.shader_manager.load_program("ssao", "ssao.vert", "ssao.frag")
self.ssao_renderer = SSAORenderer(ctx, self.shader_manager.get("ssao"))
```

### Adding New Light Types

1. Extend `Light` class in `core/light.py`
2. Add projection calculation in `get_light_matrix()`
3. Update shader if needed

Example (Point Light):
```python
# In Light.get_light_matrix()
elif self.light_type == 'point':
    # Use perspective projection, need 6 faces (cube map)
    ...
```

### Adding Custom Scenes

Create new scene builder:
```python
# In core/scene.py
def create_forest_scene(self):
    """Create forest with trees"""
    for x, z in tree_positions:
        tree = SceneObject(
            geometry.cube(...),
            Vector3([x, 0, z]),
            (0.3, 0.6, 0.2)
        )
        self.add_object(tree)
```

## Testing Strategy

### Unit Tests (`tests/`)
- Test individual classes in isolation
- Mock dependencies (e.g., OpenGL context)
- Focus on logic, not rendering

### Integration Tests
- Test component interactions
- Example: Camera + InputHandler
- May require headless GL context

### Visual Tests
- Manual verification
- Run examples and check output
- Use screenshots for regression testing

## Performance Considerations

### Shadow Map Resolution
- Higher resolution = sharper shadows, lower FPS
- Current: 2048×2048 per light
- Optimization: Use lower res for less important lights

### Light Count
- Linear cost: N lights = N shadow passes
- Current: 2 lights
- Recommendation: Keep shadow-casting lights ≤ 4

### Shader Complexity
- Fragment shader runs per-pixel
- PCF samples 9 points per light
- Total: 18 samples per pixel with 2 lights

## Future Architecture

### Planned Additions (See ROADMAP.md)

**SSAO Module** (`rendering/ssao_renderer.py`):
- G-buffer creation
- Kernel sampling
- Blur pass

**CSM Module** (`rendering/cascade_manager.py`):
- Frustum splitting
- Per-cascade shadow maps
- Cascade selection in shader

**UI System** (`ui/`):
- Debug overlays
- Settings menu
- Performance metrics

## Coding Conventions

### Imports
```python
# Standard library
import sys
from pathlib import Path

# Third-party
import moderngl
from pyrr import Vector3

# Local
from ..config.settings import *
from .camera import Camera
```

### Type Hints
Use type hints for public APIs:
```python
def render(self, scene: Scene, camera: Camera, lights: List[Light]):
    ...
```

### Documentation
- Docstrings for all public classes and methods
- Inline comments for complex logic
- README for high-level overview

### File Organization
- One class per file (generally)
- Related functionality in same module
- Keep files under 300 lines

---

**Last Updated**: 2025-10-20
**Version**: 0.2.0
