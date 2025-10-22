# GLTF/GLB Model Loading

Complete guide to loading and rendering GLTF/GLB 3D models in the ModernGL 3D engine.

## Overview

The engine supports loading GLTF 2.0 and GLB (binary GLTF) models with PBR materials, textures, and multi-mesh support. Models integrate seamlessly with the existing deferred rendering pipeline and coexist with primitive objects (cubes, spheres, etc.) in the same scene.

## Current Implementation Status

### ✅ Fully Implemented

**Core Loading:**
- GLTF 2.0 and GLB file format support
- Mesh loading with positions, normals, and UV coordinates
- Indexed geometry (automatically expanded for ModernGL)
- Multiple meshes per model
- Automatic bounding sphere calculation for frustum culling

**Material System:**
- PBR material properties (baseColorFactor, metallicFactor, roughnessFactor)
- Texture loading (base color, metallic/roughness, normal maps, emissive)
- External texture files (PNG, JPG)
- Embedded textures (in GLB files)
- Material binding to shaders

**Rendering Integration:**
- Deferred rendering pipeline support
- Shadow casting for GLTF models
- Frustum culling
- Coexistence with primitive objects
- Automatic shader switching (textured vs. flat-color)

**Normal Mapping:** ✅
- Lengyel's tangent generation algorithm
- Gram-Schmidt orthogonalization
- TBN matrix calculation in view space
- Full normal mapping support in textured shader

**PBR Lighting:** ✅
- Cook-Torrance BRDF implementation
- Fresnel-Schlick approximation
- GGX (Trowbridge-Reitz) normal distribution
- Smith geometry function
- Energy conservation (diffuse + specular = 1.0)
- Proper metallic/dielectric workflow

**Node Hierarchy & Transforms:** ✅
- Full GLTF scene graph traversal
- Recursive node processing with parent transforms
- TRS (Translation, Rotation, Scale) decomposition
- Direct matrix support (column-major)
- Per-mesh local transforms
- Transform-aware bounding sphere calculation

### ⚠️ Partial Implementation

None currently - all core features are implemented!

### ❌ Not Yet Implemented

**Missing GLTF Features:**
- Skeletal animations and skinning (static models only)
- Morph targets (blend shapes)
- Vertex colors
- Multiple UV sets (only TEXCOORD_0 supported)
- Emissive texture rendering (loaded but unused)
- Ambient occlusion maps
- KHR extensions (draco compression, lights, etc.)

**Performance Features:**
- Model caching (same model loaded multiple times wastes memory)
- Texture compression (DXT/BC formats)
- Instancing for repeated models
- Mipmapping optimization

## Architecture

### Package Structure

```
src/gamelib/loaders/
├── __init__.py           # Exports GltfLoader, Model, Material
├── gltf_loader.py        # Main loader (handles .gltf/.glb parsing)
├── model.py              # Model class with multi-mesh support
└── material.py           # PBR material with texture binding
```

### Key Classes

**GltfLoader:**
- Parses GLTF/GLB files using `pygltflib`
- Extracts vertex data (positions, normals, UVs, tangents)
- Loads textures with Pillow, uploads to GPU
- Creates ModernGL VAOs for each mesh
- Returns fully initialized Model object

**Model:**
- Container for multiple Mesh objects
- Position, rotation, scale transforms
- Bounding sphere for frustum culling
- Compatible with SceneObject interface
- Renders all meshes with correct materials

**Material:**
- Holds PBR texture references (ModernGL Texture objects)
- Stores material factors (color, metallic, roughness)
- Binds textures to shader uniforms (texture units 0-3)
- Manages GPU resource lifecycle

**Mesh:**
- Single mesh with VAO and material
- Encapsulates geometry rendering
- Material binding before draw

## Usage Guide

### Basic Model Loading

```python
from src.gamelib.loaders import GltfLoader
from pyrr import Vector3

# Create loader (needs ModernGL context)
loader = GltfLoader(ctx)

# Load a model
model = loader.load("assets/models/props/japanese_stone_lantern/scene.gltf")

# Position and scale
model.position = Vector3([0.0, 0.0, 0.0])
model.scale = Vector3([2.0, 2.0, 2.0])  # Scale up 2x

# Add to scene (works alongside primitives)
scene.add_object(model)
```

### Loading Multiple Models

```python
# Load multiple models
lantern = loader.load("assets/models/props/japanese_stone_lantern/scene.gltf")
tent = loader.load("assets/models/props/tent/scene.gltf")
bar = loader.load("assets/models/props/japanese_bar/scene.gltf")

# Position them
lantern.position = Vector3([0.0, 0.0, 0.0])
tent.position = Vector3([5.0, 0.0, 3.0])
bar.position = Vector3([-6.0, 0.0, -2.0])

# Scale as needed
lantern.scale = Vector3([2.0, 2.0, 2.0])
tent.scale = Vector3([1.5, 1.5, 1.5])

# Add all to scene
scene.add_object(lantern)
scene.add_object(tent)
scene.add_object(bar)
```

### Model Properties

```python
# Access model information
print(f"Model: {model.name}")
print(f"Meshes: {len(model.meshes)}")
print(f"Bounding radius: {model.bounding_radius}")

# Iterate through meshes
for mesh in model.meshes:
    print(f"  Mesh: {mesh.name}, vertices: {mesh.vertex_count}")
    print(f"  Material: {mesh.material.name}")
    print(f"    Has base color: {mesh.material.has_base_color()}")
    print(f"    Has normal map: {mesh.material.has_normal_map()}")
```

### Rotation (Current Limitation)

```python
# Rotation using Euler angles (yaw, pitch, roll)
model.rotation = Vector3([
    math.radians(45),   # Yaw (Y-axis rotation)
    math.radians(0),    # Pitch (X-axis rotation)
    math.radians(0)     # Roll (Z-axis rotation)
])

# Note: Model.rotation applies rotations in order: yaw → pitch → roll
# For more complex rotations, this will need quaternion support
```

## Technical Details

### GLTF Data Flow

```
1. pygltflib.GLTF2.load()
   ↓
2. Parse materials → Load textures → Create Material objects
   ↓
3. Parse meshes → Extract vertex data → Create VAOs
   ↓
4. Calculate bounding sphere from vertex positions
   ↓
5. Create Model with meshes, materials, transforms
```

### Vertex Data Extraction

**Supported Attributes:**
- `POSITION` (required, float32 × 3)
- `NORMAL` (required, float32 × 3, auto-generated if missing)
- `TEXCOORD_0` (optional, float32 × 2)
- `TANGENT` (optional, float32 × 4, **currently unused**)

**Index Buffer Handling:**
- GLTF often uses indexed geometry
- ModernGL VAO doesn't support index buffers directly
- Solution: Expand indices to create non-indexed vertex buffer
- Trade-off: Higher memory usage for simpler rendering

### Texture Loading

**Texture Types Loaded:**
```
Base Color:         texture unit 0  (RGB + alpha)
Normal Map:         texture unit 1  (RGB, tangent space)
Metallic/Roughness: texture unit 2  (B=metallic, G=roughness)
Emissive:           texture unit 3  (RGB, **not yet used in lighting**)
```

**Texture Processing:**
1. Read image from file or embedded buffer
2. Convert to RGBA using Pillow
3. Upload to GPU as ModernGL Texture
4. Generate mipmaps for better quality
5. Set trilinear filtering (LINEAR_MIPMAP_LINEAR)

### Shader Integration

**Geometry Pass (Deferred Rendering):**
- Primitive objects → `deferred_geometry.{vert,frag}` (flat colors)
- GLTF models → `deferred_geometry_textured.{vert,frag}` (PBR textures)

**Shadow Pass:**
- Both primitives and models → `shadow_depth.{vert,frag}` (depth only)
- Models render each mesh VAO without textures

**Shader Uniforms:**
```glsl
// Camera (set by GeometryRenderer)
uniform mat4 projection;
uniform mat4 view;

// Per-object (set by Scene.render_all or Model.render)
uniform mat4 model;

// Material (set by Material.bind_textures)
uniform sampler2D baseColorTexture;
uniform sampler2D normalTexture;
uniform sampler2D metallicRoughnessTexture;
uniform bool hasBaseColorTexture;
uniform bool hasNormalTexture;
uniform bool hasMetallicRoughnessTexture;
uniform vec4 baseColorFactor;
```

## Rendering Pipeline Integration

### Scene Rendering Flow

```python
# In Scene.render_all():
for obj in scene.objects:
    if obj.is_model:
        # GLTF model
        if textured_program:
            # Geometry pass: use textured shader
            obj.render(textured_program)  # Model.render() handles materials
        else:
            # Shadow pass: use simple shader
            for mesh in obj.meshes:
                mesh.vao.render(program)  # Just geometry, no materials
    else:
        # Primitive object (cube, sphere, etc.)
        obj.geometry.render(program)
```

### Frustum Culling

- Models use bounding sphere (calculated from all meshes)
- Same culling logic as primitives
- `Model.is_visible(frustum)` tests sphere vs. frustum planes
- Entire model culled if outside view (all meshes)

### Shadow Casting

- Models participate in shadow passes automatically
- Each mesh rendered from light's perspective
- Shadow maps generated normally
- Models receive shadows from lights correctly

## Available Test Models

### japanese_stone_lantern
- **File:** `assets/models/props/japanese_stone_lantern/scene.gltf`
- **Meshes:** 4 (stone base, wood frame, wood lantern, paper lamp)
- **Materials:** 4 with full PBR textures
- **Textures:** Base color, normal maps, metallic/roughness for all materials
- **Size:** Medium (bounding radius ~1.2)
- **Complexity:** Good test for multi-material rendering

### tent
- **File:** `assets/models/props/tent/scene.gltf`
- **Meshes:** TBD (needs testing)
- **Materials:** TBD
- **Size:** TBD
- **Complexity:** Simpler model, good for edge case testing

### japanese_bar
- **File:** `assets/models/props/japanese_bar/scene.gltf`
- **Meshes:** TBD (needs testing)
- **Materials:** TBD
- **Node Hierarchy:** Has node children (more complex structure)
- **Size:** Large
- **Complexity:** Best test for hierarchy support (Phase 4)

## Known Limitations & Issues

### 1. Normal Maps Not Applied ⚠️ HIGH PRIORITY
**Problem:** Normal maps load but don't affect rendering
**Cause:** Missing tangent-space transformation
**Fix:** Phase 2 (Tangent-Space Normal Mapping)
**File:** [deferred_geometry_textured.frag:42](../assets/shaders/deferred_geometry_textured.frag#L42)

### 2. Non-Photorealistic Lighting ⚠️ MEDIUM PRIORITY
**Problem:** Materials use Blinn-Phong, not PBR
**Cause:** Lighting pass doesn't implement Cook-Torrance BRDF
**Fix:** Phase 3 (Full PBR Lighting)
**File:** [deferred_lighting.frag](../assets/shaders/deferred_lighting.frag)

### 3. Flat Model Hierarchy ⚠️ MEDIUM PRIORITY
**Problem:** All meshes positioned at model origin
**Cause:** Node transforms not parsed or applied
**Fix:** Phase 4 (Model Transforms & Hierarchy)
**Impact:** Complex multi-part models may look wrong

### 4. No Animation Support ℹ️ FUTURE
**Problem:** Animated models load but don't move
**Cause:** Animation keyframes not parsed
**Fix:** Phase 6A (Animation Support)
**Impact:** Static poses only

### 5. Memory Duplication ℹ️ FUTURE
**Problem:** Same model loaded multiple times uses N× memory
**Cause:** No model caching system
**Fix:** Phase 6C (Performance Optimizations)
**Impact:** Higher memory usage for repeated models

## Troubleshooting

### Model Doesn't Load
**Check:**
1. File path correct? (use absolute path or relative to project root)
2. GLTF file valid? (test with [gltf-validator](https://github.com/KhronosGroup/glTF-Validator))
3. Textures exist? (check console for texture loading warnings)
4. Buffer files present? (scene.bin must be in same directory)

**Debug:**
```python
try:
    model = loader.load("path/to/model.gltf")
except Exception as e:
    print(f"Load failed: {e}")
    import traceback
    traceback.print_exc()
```

### Model Renders Black
**Possible causes:**
1. No textures → Check if baseColorFactor is black (0,0,0)
2. Normals inverted → Check normal generation
3. Outside view frustum → Increase bounding_radius
4. No lighting → Ensure lights are positioned correctly

**Test:**
```python
# Override bounding radius
model.bounding_radius = 10.0  # Disable culling

# Check materials
for mesh in model.meshes:
    print(f"Material: {mesh.material.base_color_factor}")
```

### Model Renders Wrong Scale
**Fix:**
```python
# GLTF uses meters, you may need to scale
model.scale = Vector3([2.0, 2.0, 2.0])  # 2x larger

# Or adjust based on bounding radius
desired_size = 3.0
scale_factor = desired_size / model.bounding_radius
model.scale = Vector3([scale_factor] * 3)
```

### Performance Issues
**Optimizations:**
1. Reduce shadow map resolution per light
2. Lower SSAO quality settings
3. Disable anti-aliasing temporarily
4. Check model poly count (very high-poly models slow)

## Future Roadmap

### Phase 2: Tangent-Space Normal Mapping (Next Up)
- Extract tangents from GLTF TANGENT attribute
- Generate tangents for models without them (Lengyel's method)
- Calculate TBN matrix in shaders
- Transform normal map samples to view space
- **Expected result:** Surface details visible on all materials

### Phase 3: Full PBR Lighting
- Implement Cook-Torrance BRDF
- Add Fresnel-Schlick, GGX distribution, Smith geometry
- Separate metallic/dielectric workflows
- Energy conservation
- **Expected result:** Photorealistic materials

### Phase 4: Model Transforms & Hierarchy
- Parse GLTF node tree
- Apply node transforms (translation, rotation, scale)
- Calculate world matrices from parent chain
- Support multi-part models
- **Expected result:** Complex models render correctly

### Phase 5: Multiple Models in Scene
- Load tent, bar, lantern together
- Compose interesting scene
- Test performance and rendering
- **Expected result:** Rich demo scene

### Phase 6: Advanced Features (Future)
- 6A: Animation support (keyframes, skinning)
- 6B: Additional materials (emissive, AO, vertex colors)
- 6C: Performance (caching, compression, instancing)

## References

### GLTF Specification
- [GLTF 2.0 Spec](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)
- [GLTF Tutorial](https://github.khronos.org/glTF-Tutorials/)
- [GLTF Sample Models](https://github.com/KhronosGroup/glTF-Sample-Models)

### PBR Theory
- [LearnOpenGL - PBR Theory](https://learnopengl.com/PBR/Theory)
- [Real Shading in Unreal Engine 4](https://blog.selfshadow.com/publications/s2013-shading-course/karis/s2013_pbl_epic_notes_v2.pdf)

### Normal Mapping
- [LearnOpenGL - Normal Mapping](https://learnopengl.com/Advanced-Lighting/Normal-Mapping)
- [Computing Tangent Space Basis Vectors](http://www.terathon.com/code/tangent.html)

### Dependencies
- [pygltflib](https://pypi.org/project/pygltflib/) - GLTF parser
- [Pillow](https://pillow.readthedocs.io/) - Image loading
- [ModernGL](https://moderngl.readthedocs.io/) - OpenGL wrapper
- [pyrr](https://pyrr.readthedocs.io/) - Math library

## Example: Loading Model in create_default_scene()

```python
# In src/gamelib/core/scene.py:

def create_default_scene(self):
    """Create scene with primitives and GLTF models"""

    # Load GLTF model
    if self.ctx is not None:
        try:
            from ..loaders import GltfLoader
            from ..config.settings import PROJECT_ROOT

            loader = GltfLoader(self.ctx)
            model_path = PROJECT_ROOT / "assets/models/props/japanese_stone_lantern/scene.gltf"

            if model_path.exists():
                lantern = loader.load(str(model_path))
                lantern.position = Vector3([0.0, 0.0, 0.0])
                lantern.scale = Vector3([2.0, 2.0, 2.0])
                self.add_object(lantern)
                print(f"Loaded {lantern.name} with {len(lantern.meshes)} meshes")
        except Exception as e:
            print(f"Failed to load model: {e}")

    # Add primitives as usual
    ground = SceneObject(
        geometry.cube(size=(20.0, 0.5, 20.0)),
        Vector3([0.0, -0.25, 0.0]),
        (0.3, 0.6, 0.3),
        name="Ground"
    )
    self.add_object(ground)
    # ... more primitives ...
```

---

**Last Updated:** 2025-10-22
**Status:** Phase 1 Complete, Phase 2 Next
