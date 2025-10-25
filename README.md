# ModernGL 3D Game Engine

A modular 3D game engine with multi-light shadow mapping using ModernGL. Features clean architecture, comprehensive documentation, and extensible design.

## Features

✅ **Multi-Light Shadows** - Multiple shadow-casting lights with compounding darkness
✅ **Modular Architecture** - Clean separation: core, rendering, input
✅ **Shadow Mapping** - PCF soft shadows with configurable quality
✅ **FPS Camera** - WASD movement + mouse look
✅ **Shader Files** - External .vert/.frag files with syntax highlighting
✅ **Well Documented** - Comprehensive docs and examples
✅ **Tested** - Unit tests for core components
✅ **M1 Compatible** - Uses OpenGL 4.1 (max for macOS)

## Quick Start

### Installation

```bash
# Make sure you're using native ARM Python (not Rosetta)
python3 --version  # Should show arm64 architecture

# Install dependencies
pip install -r requirements.txt

# Run the engine
python main.py
```

### Controls

**Camera Movement:**
- `W/A/S/D` - Move forward/left/backward/right
- `Q/E` - Move down/up
- Mouse - Look around (if implemented)

**Light Movement:**
- `Arrow Keys` - Move light horizontally
- `Z/X` - Move light down/up

**Exit:**
- `ESC` - Close window

## Project Structure

```
3dlibtesting/
├── assets/
│   └── shaders/            # GLSL shader files
├── src/gamelib/            # Main engine package
│   ├── config/             # Configuration
│   ├── core/               # Camera, Light, Scene
│   ├── rendering/          # Rendering pipeline
│   └── input/              # Input handling
├── tests/                  # Unit tests
├── examples/               # Example scenes
├── docs/                   # Documentation
└── main.py                 # Entry point
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## How It Works

### Shadow Mapping Overview

The project uses **two-pass rendering**:

1. **Pass 1 - Shadow Map Generation:**
   - Render scene from light's perspective
   - Store depth values in a texture (shadow map)
   - Uses orthographic projection for directional light

2. **Pass 2 - Main Render:**
   - Render scene from camera's perspective
   - For each fragment, check if it's in shadow by comparing with shadow map
   - Apply lighting calculations with shadow factor

### Key Components

**Shadow Map Setup (`setup_shadow_map`):**
```python
# Creates 2048x2048 depth texture
self.shadow_depth = self.ctx.depth_texture((2048, 2048))
self.shadow_fbo = self.ctx.framebuffer(depth_attachment=self.shadow_depth)
```

**Shader Programs:**
- `shadow_program` - Renders depth from light's POV
- `main_program` - Main render with lighting and shadows

**PCF (Percentage Closer Filtering):**
- Samples 9 points around each shadow map pixel
- Creates soft shadow edges instead of hard shadows

## Extending the Project

### Adding New Objects

```python
# In create_scene() method:
self.my_object = geometry.cube(size=(2.0, 2.0, 2.0))
self.my_object_pos = Vector3([x, y, z])
self.my_object_color = (r, g, b)

# Add to objects list:
self.objects.append(
    (self.my_object, self.my_object_pos, self.my_object_color)
)
```

### Changing Shadow Quality

```python
# In class definition:
SHADOW_SIZE = 4096  # Higher = sharper shadows, lower performance
```

### Modifying Lighting

```python
# In shader fragment shader:
ambient_strength = 0.3  # Increase for brighter ambient
bias = 0.005            # Adjust to fix shadow artifacts
```

### Loading Custom Models

Replace `geometry.cube()` with custom mesh loading:
```python
# Using wavefront obj loader (install: pip install moderngl-window[pywavefront])
self.model = self.load_scene('models/mymodel.obj')
```

## Common Issues & Fixes

### Shadows not appearing
- Check light position with arrow keys
- Verify objects are within light's view frustum
- Increase orthographic projection bounds in `get_light_matrix()`

### Shadow acne (striped patterns)
```python
# Increase bias in fragment shader:
float bias = 0.01;  # Was 0.005
```

### Peter panning (shadows detached from objects)
```python
# Decrease bias:
float bias = 0.001;  # Was 0.005
```

### Performance issues
- Reduce shadow map size: `SHADOW_SIZE = 1024`
- Disable PCF soft shadows (use single sample)
- Reduce number of objects

## Next Steps

### Recommended Additions:

1. **Mouse Look Camera**
   ```python
   def mouse_position_event(self, x, y, dx, dy):
       self.camera_yaw += dx * self.mouse_sensitivity
       self.camera_pitch -= dy * self.mouse_sensitivity
       # Update camera target based on yaw/pitch
   ```

2. **Load Custom 3D Models**
   - Use `moderngl-window`'s scene loaders
   - Support for .obj, .gltf formats

3. **Texture Mapping**
   - Load textures with `self.load_texture_2d('texture.png')`
   - Add texture coordinates to geometry
   - Sample textures in fragment shader

4. **Point Lights & Spotlights**
   - Modify lighting calculations
   - Use perspective projection for shadows (not orthographic)

5. **Skybox**
   - Cube map texture
   - Render after clearing depth

6. **Post-processing**
   - Render to texture
   - Apply effects (bloom, SSAO, etc.)

## Performance Tips

- ModernGL performs well for Minecraft-level complexity
- Keep draw calls reasonable (<10K per frame)
- Use instancing for repeated objects
- Profile with `self.wnd.print_context_info()`

## Collision Mesh Pipeline

- Author physics-enabled objects with a `collision_mesh` block (e.g. `{"type": "gltf", "source": "assets/models/…/scene.gltf"}`).
- For procedural geometry, point at any callable that writes an OBJ: `{"type": "generator", "generator": "tools.export_collision_meshes:export_donut_collision", "params": {...}}`.
- Generate or refresh OBJ collision meshes by running `python tools/export_collision_meshes.py`.
- The tool scans every scene in `assets/scenes`, builds missing meshes under `assets/collision`, and skips files that are already up to date.
- At runtime the physics system resolves those definitions automatically, so no hard-coded OBJ paths are required.

## Troubleshooting

### Installation fails on M1
```bash
# Force ARM architecture
arch -arm64 pip install -r requirements.txt

# If still issues, try creating a venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### OpenGL version errors
macOS caps at OpenGL 4.1. The project is configured for this, but if you copied shaders from elsewhere, ensure they use `#version 410` or lower.

### Window doesn't open
```bash
# Check if dependencies installed correctly
python -c "import moderngl; print(moderngl.__version__)"
python -c "import moderngl_window; print('OK')"
```

## Resources

- [ModernGL Documentation](https://moderngl.readthedocs.io/)
- [ModernGL Examples](https://github.com/moderngl/moderngl/tree/master/examples)
- [LearnOpenGL Shadow Mapping](https://learnopengl.com/Advanced-Lighting/Shadows/Shadow-Mapping)
- [Pyrr Documentation](https://pyrr.readthedocs.io/)
