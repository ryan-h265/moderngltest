# 3D Engine Feature Roadmap

This document outlines the planned features and implementation path for this ModernGL 3D engine.

## Current Status

**Implemented:**
- ✅ Basic shadow mapping with single directional light
- ✅ PCF (Percentage Closer Filtering) for soft shadows
- ✅ FPS camera controls (WASD + mouse look)
- ✅ Dynamic light animation
- ✅ Multi-object scene (18+ cubes)

**Current Limitation:**
- Overlapping shadows from multiple objects don't compound (no darkening in overlap areas)
- Single shadow map = binary shadow test (in shadow OR not in shadow)

---

## Phase 1: Multiple Shadow-Casting Lights ⬅️ CURRENT PHASE

**Goal:** Enable true shadow compounding where overlapping shadows create darker areas.

### Implementation Details

**What we're building:**
- Support for 2+ lights, each casting independent shadows
- Shadow accumulation: areas blocked by multiple lights appear darker
- Foundation for dynamic multi-light scenes

**Technical approach:**
```
Light 1 blocks 50% → shadow value: 0.5
Light 2 blocks 50% → shadow value: 0.5
Combined formula: 1 - (1-0.5) * (1-0.5) = 0.75 (75% dark)
```

### Architecture Changes

**1. Light Management System**
```python
class Light:
    position: Vector3
    color: Vector3
    intensity: float
    shadow_map: Texture (2048x2048)
    shadow_fbo: Framebuffer
    light_type: 'directional' | 'point' | 'spot'
```

**2. Multiple Shadow Maps**
- Array of depth textures (one per light)
- Each light gets its own framebuffer
- Render shadow pass for each light

**3. Shader Updates**
- Fragment shader samples N shadow maps
- Accumulates shadow contributions
- Per-light color and intensity

### Initial Configuration

**Light 1: Rotating Sun (Directional)**
- Position: Rotates around scene at radius 12
- Color: White (1.0, 1.0, 1.0)
- Intensity: 1.0
- Shadow map: 2048x2048

**Light 2: Static Side Light (Directional/Spot)**
- Position: Fixed at (8, 6, 8)
- Color: Warm orange-red (1.0, 0.7, 0.5)
- Intensity: 0.8
- Shadow map: 2048x2048

### Expected Visual Result

**Before:** Area blocked by cube → uniform shadow
**After:**
- Area blocked by cube from Light 1 only → 50% dark
- Area blocked by cube from Light 2 only → 40% dark (due to 0.8 intensity)
- Area blocked by both → ~70% dark (compounding!)

### Performance Impact

- 2x shadow map memory (2 × 2048×2048)
- 2x shadow pass rendering time
- Slightly more expensive fragment shader (2 shadow lookups + accumulation)
- **Estimated FPS impact:** 60fps → 45fps (for 2 lights)

### Scaling to More Lights

Once 2-light system works:
- Add light 3, 4, 5... using same pattern
- Consider light culling (don't render shadows for lights outside frustum)
- May need to reduce shadow map resolution per light (e.g., 1024×1024)

**Recommended light budget:**
- Development/prototyping: 2-4 shadow-casting lights
- Optimized game: 1-2 high-quality + 2-4 lower-res shadow lights
- Non-shadow-casting lights: unlimited (cheap point lights for ambiance)

---

## Phase 2: Screen Space Ambient Occlusion (SSAO)

**Status:** Planned for after Phase 1

### Why SSAO?

SSAO adds ambient darkening in areas where geometry is close together, complementing shadow maps:
- Corners and crevices appear darker
- Areas where multiple objects are near each other get subtle darkening
- Works in conjunction with shadow maps (different effect)

### What SSAO Provides

**Shadows answer:** "Is this point blocked from the light?"
**SSAO answers:** "Is this point in a tight/enclosed space?"

**Visual examples:**
- Corner between two cubes → darker (even if lit)
- Gap underneath a cube → darker
- Open ground plane → no darkening

### Implementation Overview

**Technique:** Screen-space ray marching
1. Render scene to texture (need depth + normals)
2. For each pixel, sample random points in hemisphere around it
3. Check if sample points are occluded (behind other geometry)
4. More occluded samples = darker ambient occlusion

**Rendering pipeline change:**
```
Current: Shadow pass → Main pass → Screen
New:     Shadow pass → Geometry pass (to texture) → SSAO pass → Lighting pass → Screen
```

### Technical Requirements

**New components needed:**
1. G-buffer (geometry buffer) framebuffer
   - Color attachment: RGB color
   - Depth attachment: depth values
   - Normal attachment: world-space normals
2. SSAO framebuffer
   - Output: grayscale occlusion values
3. Random sample kernel (64 samples in hemisphere)
4. Noise texture (4x4 random rotations)
5. SSAO shader (samples depth + normals)
6. Blur pass (smooth noisy SSAO output)

### Shader Additions

**SSAO Fragment Shader:**
- Sample 64 random points around fragment
- Check depth buffer to see if samples are occluded
- Output occlusion factor (0.0 = fully occluded, 1.0 = open)

**Final Lighting Shader:**
- Multiply ambient term by SSAO factor
- Keeps diffuse/specular unaffected
- `ambient = ambient_strength * object_color * ssao_factor`

### Configuration Parameters

```python
SSAO_KERNEL_SIZE = 64        # Number of samples (16-64)
SSAO_RADIUS = 0.5            # Sample radius in world units
SSAO_BIAS = 0.025            # Prevent self-occlusion
SSAO_INTENSITY = 1.5         # How dark occluded areas get
SSAO_BLUR_SIZE = 4           # Blur kernel size for noise reduction
```

### Performance Impact

- Extra render pass (geometry to texture)
- SSAO calculation pass (64 samples per pixel = expensive)
- Blur pass
- **Estimated FPS impact:** 45fps → 30-35fps

**Optimization strategies:**
- Render SSAO at half resolution, upscale
- Reduce kernel size to 32 or 16 samples
- Use interleaved sampling (only compute every Nth pixel)
- Cache SSAO for static geometry

### Learning Value

**Techniques learned:**
- Deferred rendering (G-buffer)
- Screen-space effects
- Post-processing pipeline
- Random sampling in shader
- Blur filters

**Industry relevance:**
- SSAO is in almost every modern 3D game
- Foundation for more screen-space effects (SSR, SSGI)
- Understanding of depth buffer usage

---

## Phase 3: Cascaded Shadow Maps (CSM)

**Status:** Planned for when scene expands to large outdoor environment

### Why CSM?

**Problem CSM solves:**
With a single shadow map covering a large area, distant shadows become blocky/pixelated while nearby shadows waste resolution.

**Current situation (single shadow map):**
```
Orthographic projection: -15 to +15 (30 units wide)
Shadow map: 2048x2048
Resolution: 2048/30 = 68 pixels per world unit

If scene expands to 200 units wide:
Resolution: 2048/200 = 10 pixels per world unit (very blocky!)
```

**CSM solution:**
- Split view frustum into multiple cascades (typically 3-4)
- Each cascade gets its own shadow map
- Close cascade: high detail (e.g., 0-10 units)
- Far cascade: lower detail (e.g., 50-100 units)

### When You Need CSM

**Don't need CSM if:**
- Scene is compact (< 50 units across)
- Camera doesn't move much
- Indoor environments

**Need CSM if:**
- Large outdoor scenes (100+ units)
- Third-person game with distant vistas
- Flying/driving games
- Open world exploration

**Current scene:** 20x20 ground plane, camera range ~30 units → **Don't need CSM yet**

### Implementation Overview

**Cascade configuration (3 cascades example):**
```
Cascade 0 (near):  0-10 units from camera
  Shadow map: 2048x2048, covers 20x20 world space
  Resolution: 102 pixels/unit (very sharp!)

Cascade 1 (mid):   10-30 units from camera
  Shadow map: 2048x2048, covers 60x60 world space
  Resolution: 34 pixels/unit (sharp)

Cascade 2 (far):   30-100 units from camera
  Shadow map: 2048x2048, covers 200x200 world space
  Resolution: 10 pixels/unit (acceptable for distance)
```

### Technical Requirements

**New components:**
1. Calculate frustum splits (near/mid/far boundaries)
2. Compute light matrices for each cascade
3. Render shadow pass 3-4 times (once per cascade)
4. Fragment shader selects correct cascade based on depth
5. Blend between cascades to avoid visible seams

### Architecture Changes

**Shadow map structure:**
```python
# Before (single light, single shadow map):
shadow_map: Texture2D (2048x2048)

# After (single light, 3 cascades):
shadow_cascade_maps: Texture2DArray (2048x2048 × 3)
cascade_splits: [near, split1, split2, far]
cascade_matrices: [Matrix44 × 3]
```

**Shader changes:**
```glsl
// Determine which cascade to use
float depth = length(camera_pos - v_position);
int cascade_index = 0;
if (depth > cascade_splits[1]) cascade_index = 1;
if (depth > cascade_splits[2]) cascade_index = 2;

// Sample appropriate cascade shadow map
float shadow = texture(shadow_cascade_maps[cascade_index], ...);
```

### Combining CSM + Multiple Lights

**Full system (Phase 1 + Phase 3):**
- 2-4 shadow-casting lights
- Each light has 3 CSM cascades
- Total shadow maps: num_lights × 3

**Example (2 lights, 3 cascades each):**
- 6 total shadow map textures
- 6 shadow passes per frame
- Fragment shader samples 2 cascades (one per light)

**Performance consideration:**
Probably want to use CSM only for primary light (sun), not all lights.

### Advanced CSM Techniques

**Cascade stabilization:**
- Fix shadow map "swimming" when camera moves
- Snap cascade bounds to texel grid

**Soft transitions:**
- Blend shadow values between cascades
- Prevents visible "seam" where cascades meet

**Optimal splits:**
- Practical split scheme: `split[i] = near * (far/near)^(i/N)`
- Logarithmic distribution gives better quality

### Configuration Parameters

```python
CSM_NUM_CASCADES = 3
CSM_LAMBDA = 0.5              # Blend between uniform/logarithmic splits
CSM_SHADOW_MAP_SIZE = 2048    # Per cascade
CSM_CASCADE_BLEND = 0.1       # Transition zone between cascades
```

### Performance Impact

**Single light, 3 cascades:**
- 3x shadow map memory (3 × 2048×2048)
- 3x shadow pass time
- Slightly more complex fragment shader (cascade selection)
- **Estimated FPS impact:** 60fps → 25-30fps (for single light with CSM)

**Optimization:**
- Reduce cascade resolution for far cascades (2048, 1024, 512)
- Skip cascades that are fully outside view frustum
- Update far cascades less frequently (e.g., every other frame)

### Learning Value

**Techniques learned:**
- View frustum splitting
- Level-of-detail (LOD) for shadows
- Multi-frustum rendering
- Texture arrays in OpenGL
- Advanced shadow map optimization

**Industry relevance:**
- CSM is standard for large outdoor games
- Used in virtually all AAA open-world games
- Foundation for virtual shadow maps (Unreal Engine 5)

---

## Phase 4: Advanced Features (Future)

Ideas for further expansion after Phases 1-3:

### 4.1 Dynamic Light Management
- Add/remove lights at runtime
- Light culling (frustum + distance)
- Automatic quality adjustment based on performance

### 4.2 Different Light Types
- Point lights (cube map shadows)
- Spotlights (perspective projection shadows)
- Area lights (approximated)

### 4.3 Additional Screen-Space Effects
- Screen-Space Reflections (SSR)
- Screen-Space Global Illumination (SSGI)
- Volumetric lighting (god rays)

### 4.4 Advanced Shadow Techniques
- Exponential Shadow Maps (ESM)
- Variance Shadow Maps (VSM)
- Contact-hardening shadows (PCSS)

### 4.5 Performance Optimization
- Shadow map caching for static objects
- Temporal filtering (reuse previous frame data)
- Instanced rendering for repeated geometry

---

## Implementation Order Rationale

**Why this order?**

1. **Multiple Lights First** (Phase 1)
   - Solves your immediate question (compounding shadows)
   - Builds toward your stated goal (multiple lights in scene)
   - Works great with current scene size
   - Foundation that other features build upon

2. **SSAO Second** (Phase 2)
   - High visual impact
   - Complements multi-light shadows beautifully
   - Different technique (screen-space vs. shadow mapping)
   - Teaches post-processing pipeline

3. **CSM Last** (Phase 3)
   - Only needed when scene gets large
   - Most complex implementation
   - Builds on existing shadow system
   - Optimization technique (doesn't add new visual features)

---

## Estimated Timeline

**Phase 1 (Multiple Lights):** 1-2 sessions
- Session 1: Architecture + 2 lights working
- Session 2: Testing, tuning, adding 3rd-4th light

**Phase 2 (SSAO):** 2-3 sessions
- Session 1: G-buffer setup + basic SSAO
- Session 2: Blur pass + integration with lighting
- Session 3: Tuning parameters, optimization

**Phase 3 (CSM):** 3-4 sessions
- Session 1: Cascade splitting + matrices
- Session 2: Multi-pass rendering + shader updates
- Session 3: Cascade selection + blending
- Session 4: Optimization + cascade stabilization

**Total:** 6-9 development sessions to complete all phases

---

## Testing Strategy

### Phase 1 Testing
- [ ] 2 lights both cast shadows independently
- [ ] Overlapping shadows are darker than single shadows
- [ ] Move lights to verify shadow updates
- [ ] Performance: measure FPS with 1 vs 2 lights

### Phase 2 Testing
- [ ] Corners/crevices are darker with SSAO on
- [ ] SSAO toggleable (compare on/off)
- [ ] No visible noise artifacts
- [ ] Performance: measure FPS with SSAO on/off

### Phase 3 Testing
- [ ] Near shadows are sharp, far shadows acceptable
- [ ] No visible cascade transitions
- [ ] Works at various camera distances
- [ ] Performance: measure FPS with CSM vs single shadow map

---

## Resources & References

### Multiple Lights / Shadow Mapping
- [LearnOpenGL - Multiple Lights](https://learnopengl.com/Lighting/Multiple-lights)
- [LearnOpenGL - Shadow Mapping](https://learnopengl.com/Advanced-Lighting/Shadows/Shadow-Mapping)

### SSAO
- [LearnOpenGL - SSAO](https://learnopengl.com/Advanced-Lighting/SSAO)
- [John Chapman's SSAO Tutorial](http://john-chapman-graphics.blogspot.com/2013/01/ssao-tutorial.html)

### Cascaded Shadow Maps
- [Microsoft CSM Sample](https://learn.microsoft.com/en-us/windows/win32/dxtecharts/cascaded-shadow-maps)
- [NVIDIA CSM](https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-10-parallel-split-shadow-maps-programmable-gpus)
- [CSM Sample Code](https://github.com/TheRealMJP/Shadows)

### General Shadow Techniques
- [GPU Gems - Shadow Techniques](https://developer.nvidia.com/gpugems/gpugems/part-ii-lighting-and-shadows)
- [Advances in Real-Time Rendering (SIGGRAPH)](https://advances.realtimerendering.com/)
