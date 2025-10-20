# Multi-Light Shadow Implementation

## Summary

Successfully implemented **multiple shadow-casting lights** with **compounding shadow darkness**. Your scene now has 2 independent lights that each cast shadows, and areas blocked by both lights appear darker.

---

## What Changed

### 1. New Light Class
Added a `Light` dataclass ([game.py:14-39](game.py#L14-L39)) to manage individual light sources:

```python
@dataclass
class Light:
    position: Vector3
    target: Vector3
    color: Vector3
    intensity: float
    shadow_map: Texture
    shadow_fbo: Framebuffer
    light_type: str  # 'directional', 'point', or 'spot'
```

Each light has:
- Its own position, color, and intensity
- Its own 2048×2048 shadow map
- Its own framebuffer for shadow rendering

### 2. Two Lights in Your Scene

**Light 1: Rotating Sun**
- Position: Rotates around scene (radius 12, height 10)
- Color: White (1.0, 1.0, 1.0)
- Intensity: 1.0
- Behavior: Same animated rotation as before

**Light 2: Static Side Light**
- Position: Fixed at (8, 6, 8)
- Color: Warm orange-red (1.0, 0.7, 0.5)
- Intensity: 0.8
- Behavior: Stationary, provides side lighting

### 3. Updated Shader System

**Vertex Shader:**
- Now transforms each vertex into **2 light spaces** (one per light)
- Outputs array: `v_light_space_pos[MAX_LIGHTS]`

**Fragment Shader:**
- Samples **2 shadow maps** (one per light)
- Calculates lighting contribution from each light independently
- **Accumulates shadows**: areas blocked by both lights are darker
- Each light can have different color and intensity

### 4. Shadow Accumulation Formula

The key to compounding shadows:

```glsl
// For each light i:
shadow_i = calculate_shadow(light_i)
light_contribution_i = intensity_i * (1.0 - shadow_i) * (diffuse + specular)

// Total lighting = ambient + sum of all light contributions
final_color = ambient + light_1_contrib + light_2_contrib + ...
```

**Result:**
- Area blocked by Light 1 only: ~50% shadow
- Area blocked by Light 2 only: ~40% shadow (due to 0.8 intensity)
- Area blocked by BOTH: ~70% shadow (compounding!)

---

## Technical Details

### Shadow Map Pipeline

**Before (Single Light):**
```
Pass 1: Render shadow map from light perspective
Pass 2: Render scene, sample 1 shadow map
```

**After (Multi-Light):**
```
Pass 1a: Render shadow map from Light 1 perspective
Pass 1b: Render shadow map from Light 2 perspective
Pass 2:  Render scene, sample both shadow maps and accumulate
```

### Performance Impact

**Memory:**
- Before: 1 × 2048×2048 depth texture = 16 MB
- After: 2 × 2048×2048 depth textures = 32 MB

**Rendering:**
- Shadow passes: 2× cost (render scene twice for shadows)
- Fragment shader: Slightly more expensive (2 shadow lookups + accumulation)

**Estimated FPS impact:** ~60fps → ~45-50fps (depends on scene complexity)

### Code Locations

| Component | Location |
|-----------|----------|
| Light class | [game.py:14-39](game.py#L14-L39) |
| Light setup | [game.py:235-249](game.py#L235-L249) |
| Vertex shader | [game.py:115-144](game.py#L115-L144) |
| Fragment shader | [game.py:145-232](game.py#L145-L232) |
| Shadow rendering | [game.py:473-487](game.py#L473-L487) |
| Main rendering | [game.py:489-520](game.py#L489-L520) |

---

## How to Use

### Running the Game

```bash
python game.py
```

You should see:
- **Two sets of shadows** from different angles
- **Darker areas** where shadows overlap
- **Color tinting** from the orange side light
- Light 1 rotating around the scene
- Light 2 stationary

### Adding More Lights

To add a 3rd light:

1. **Update MAX_LIGHTS constant:**
```python
# In game.py
NUM_LIGHTS = 3
```

2. **Update shader #define:**
```glsl
#define MAX_LIGHTS 3
```

3. **Add light in setup_lights():**
```python
light3 = Light(
    position=Vector3([0.0, 8.0, -10.0]),
    target=Vector3([0.0, 0.0, 0.0]),
    color=Vector3([0.5, 0.5, 1.0]),  # Blue light
    intensity=0.6,
    light_type='directional'
)
# Then add to lights list (same pattern as light1 and light2)
```

### Customizing Lights

**Change light color:**
```python
self.lights[1].color = Vector3([1.0, 0.0, 0.0])  # Pure red
```

**Change light intensity:**
```python
self.lights[0].intensity = 0.5  # Dimmer
self.lights[1].intensity = 1.5  # Brighter
```

**Animate second light:**
```python
# In on_update() method:
angle2 = time * 0.3
self.lights[1].position.x = 10.0 * np.cos(angle2)
self.lights[1].position.z = 10.0 * np.sin(angle2)
```

---

## Comparison: Before vs After

### Before (Single Light)
✓ One shadow per object
✓ Uniform shadow darkness
✗ No overlapping shadow effects
✗ Single light color (white only)

### After (Multi-Light)
✓ Multiple shadows per object (one per light)
✓ **Compounding darkness in overlaps**
✓ **Colored lighting** from different sources
✓ More realistic and dynamic scenes
✓ Foundation for 3+ lights

---

## Visual Explanation

```
         Light 1 (Sun)
              ↓
         ☀️  (rotating)
        /    \
       /      \
   Shadow1  Shadow2
      \      /
       \    /     ← Overlap region is DARKER
        \  /
        [🟦]  ← Cube

    🔶 Light 2 (Side)
    (stationary, orange)
```

Areas receiving:
- **Both lights:** Fully lit (bright, color mix)
- **Light 1 only:** Partially lit (white-ish)
- **Light 2 only:** Partially lit (orange-ish)
- **Shadow from 1 only:** Medium dark
- **Shadow from 2 only:** Medium dark
- **Shadow from BOTH:** Very dark (compounding!)

---

## Next Steps

Now that you have multi-light shadows working, you can:

1. **Add more lights** (3-4 total for rich scenes)
2. **Implement light types:**
   - Point lights (radial shadows)
   - Spotlights (cone-shaped)
3. **Add light management:**
   - Turn lights on/off dynamically
   - Cull lights outside view frustum
4. **Optimize performance:**
   - Lower shadow map resolution for less important lights
   - Skip shadow updates for static lights
5. **Move to Phase 2:** Implement SSAO (see [ROADMAP.md](ROADMAP.md))

---

## Troubleshooting

### Shadows look wrong
- Check light positions with `print(self.lights[i].position)`
- Verify lights are above the scene (positive Y)
- Adjust bias in fragment shader if you see shadow acne

### Performance is slow
- Reduce shadow map size: `SHADOW_SIZE = 1024`
- Reduce number of lights to 1-2
- Reduce PCF samples in shader (3×3 → 1×1)

### Overlaps not darker
- This should work automatically with the new shader
- Verify both lights are casting shadows
- Check light intensities aren't too low

### One light not visible
- Make sure light position and target are different
- Check light color isn't black
- Verify intensity > 0

---

## Answered Your Original Question

**Your question:** "When shadows collide, there's no compounding darkness. Is this possible or do we need multiple depth maps?"

**Answer:** You DO need multiple depth maps (one per light), which we now have!

**How it works:**
- Each light has its own shadow map
- Fragment shader checks each shadow map independently
- Lighting contributions are accumulated
- Areas blocked from multiple lights receive less total light
- **Result: Overlapping shadows ARE darker**

This is exactly how modern games handle multi-light shadows!

---

**Implementation Complete** ✓

See [ROADMAP.md](ROADMAP.md) for the next features (SSAO and CSM).
