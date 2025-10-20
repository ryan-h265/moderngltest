# Shadow Mapping Shader Reference

This guide explains the shader code in `game.py` to help you understand and modify the shadow mapping implementation.

## Shadow Map Pass (Depth Rendering)

### Vertex Shader
```glsl
uniform mat4 light_matrix;  // Light's projection * view matrix
uniform mat4 model;          // Object's transform

in vec3 in_position;         // Vertex position

void main() {
    // Transform vertex to light's clip space
    gl_Position = light_matrix * model * vec4(in_position, 1.0);
}
```

**Purpose:** Transform all geometry to light's perspective and write depth values.

### Fragment Shader
```glsl
void main() {
    // Depth is automatically written to depth buffer
    // No color output needed
}
```

**Purpose:** Just let OpenGL write depth values automatically.

---

## Main Render Pass (With Shadows)

### Vertex Shader
```glsl
uniform mat4 projection;      // Camera projection
uniform mat4 view;            // Camera view
uniform mat4 model;           // Object transform
uniform mat4 light_matrix;    // Light's projection * view

in vec3 in_position;
in vec3 in_normal;

out vec3 v_position;          // World space position
out vec3 v_normal;            // World space normal
out vec4 v_light_space_pos;   // Position in light's clip space

void main() {
    vec4 world_pos = model * vec4(in_position, 1.0);
    
    v_position = world_pos.xyz;
    v_normal = mat3(model) * in_normal;
    
    // Transform to light space for shadow lookup
    v_light_space_pos = light_matrix * world_pos;
    
    gl_Position = projection * view * world_pos;
}
```

**Key Points:**
- We need both camera transform (for rendering) and light transform (for shadow lookup)
- `v_light_space_pos` will be used to sample the shadow map

### Fragment Shader - Shadow Calculation

```glsl
float calculate_shadow() {
    // 1. Perspective divide to get NDC coordinates
    vec3 proj_coords = v_light_space_pos.xyz / v_light_space_pos.w;
    
    // 2. Transform from [-1,1] to [0,1] (texture coordinates)
    proj_coords = proj_coords * 0.5 + 0.5;
    
    // 3. If outside shadow map bounds, not in shadow
    if (proj_coords.z > 1.0 || proj_coords.x < 0.0 || proj_coords.x > 1.0 
        || proj_coords.y < 0.0 || proj_coords.y > 1.0) {
        return 0.0;
    }
    
    // 4. Get the depth stored in shadow map
    float closest_depth = texture(shadow_map, proj_coords.xy).r;
    float current_depth = proj_coords.z;
    
    // 5. Bias prevents "shadow acne" (false shadows on surfaces)
    float bias = 0.005;
    
    // 6. PCF (Percentage Closer Filtering) for soft shadows
    float shadow = 0.0;
    vec2 texel_size = 1.0 / textureSize(shadow_map, 0);
    for(int x = -1; x <= 1; ++x) {
        for(int y = -1; y <= 1; ++y) {
            float pcf_depth = texture(shadow_map, proj_coords.xy + vec2(x, y) * texel_size).r;
            shadow += current_depth - bias > pcf_depth ? 1.0 : 0.0;
        }
    }
    shadow /= 9.0;  // Average of 9 samples
    
    return shadow;  // 0.0 = no shadow, 1.0 = full shadow
}
```

**Common Issues:**

| Problem | Cause | Solution |
|---------|-------|----------|
| Shadow acne (stripes) | Depth precision issues | Increase `bias` |
| Peter panning (floating shadows) | Bias too high | Decrease `bias` |
| Hard shadow edges | Single sample | Use PCF (already implemented) |
| No shadows visible | Light position wrong | Check `self.light_pos` |

### Fragment Shader - Lighting

```glsl
void main() {
    vec3 normal = normalize(v_normal);
    vec3 light_dir = normalize(light_pos - v_position);
    vec3 view_dir = normalize(camera_pos - v_position);
    
    // Ambient: Always visible, not affected by shadows
    float ambient_strength = 0.3;
    vec3 ambient = ambient_strength * object_color;
    
    // Diffuse: Depends on angle between normal and light
    float diff = max(dot(normal, light_dir), 0.0);
    vec3 diffuse = diff * object_color;
    
    // Specular: Shiny highlights
    vec3 halfway_dir = normalize(light_dir + view_dir);
    float spec = pow(max(dot(normal, halfway_dir), 0.0), 32.0);
    vec3 specular = vec3(0.3) * spec;
    
    // Calculate shadow
    float shadow = calculate_shadow();
    
    // Only diffuse and specular are affected by shadows
    vec3 lighting = ambient + (1.0 - shadow) * (diffuse + specular);
    
    f_color = vec4(lighting, 1.0);
}
```

**Lighting Components:**
- **Ambient** - Base lighting, shadows don't affect it (keeps everything visible)
- **Diffuse** - Main surface color, reduced in shadows
- **Specular** - Shiny highlights, reduced in shadows

---

## Modifying the Shaders

### Make shadows darker
```glsl
// In main():
float ambient_strength = 0.1;  // Lower = darker overall
```

### Adjust shadow softness
```glsl
// In calculate_shadow():
// Increase PCF samples (slower but smoother):
for(int x = -2; x <= 2; ++x) {  // Was -1 to 1
    for(int y = -2; y <= 2; ++y) {
        // ...
    }
}
shadow /= 25.0;  // Was 9.0
```

### Add colored lighting
```glsl
uniform vec3 light_color;

// In main():
vec3 diffuse = diff * object_color * light_color;
```

### Disable soft shadows (hard edges, better performance)
```glsl
// In calculate_shadow():
// Replace PCF loop with single sample:
float shadow = current_depth - bias > closest_depth ? 1.0 : 0.0;
return shadow;
```

---

## Understanding the Math

### Why perspective divide?
```glsl
vec3 proj_coords = v_light_space_pos.xyz / v_light_space_pos.w;
```
After projection, coordinates are in "clip space" where w ≠ 1. Dividing by w converts to "normalized device coordinates" (NDC) where coordinates are in [-1, 1].

### Why transform to [0,1]?
```glsl
proj_coords = proj_coords * 0.5 + 0.5;
```
Texture coordinates use [0, 1] range, but NDC uses [-1, 1]. This converts between them.

### What's the bias for?
```glsl
float bias = 0.005;
current_depth - bias > pcf_depth
```
Due to limited depth precision, a surface might incorrectly shadow itself. The bias shifts the comparison slightly to prevent this "shadow acne."

---

## Performance Considerations

| Modification | FPS Impact | Quality Impact |
|--------------|-----------|----------------|
| Increase `SHADOW_SIZE` | ⬇️ Lower FPS | ⬆️ Sharper shadows |
| Decrease `SHADOW_SIZE` | ⬆️ Higher FPS | ⬇️ Blurrier shadows |
| More PCF samples | ⬇️ Lower FPS | ⬆️ Smoother shadows |
| Remove PCF | ⬆️ Higher FPS | ⬇️ Hard edges |
| Increase bias | Neutral | ⬇️ Peter panning |
| Decrease bias | Neutral | ⬇️ Shadow acne |

---

## Next Steps

1. **Experiment with values** - Change bias, ambient strength, PCF samples
2. **Add point light shadows** - Requires cube map shadows
3. **Cascade shadow maps** - For large open worlds
4. **Variance shadow mapping** - Alternative soft shadow technique

## Quick Debug Checklist

Shadow not working? Check:
- [ ] Light position is above the scene
- [ ] Shadow map is bound: `self.shadow_depth.use(location=0)`
- [ ] Uniform is set: `program['shadow_map'] = 0`
- [ ] Light matrix is correct (check orthographic bounds)
- [ ] Depth texture comparison is disabled
- [ ] Bias value is reasonable (0.001 - 0.01)

---

**Pro Tip:** To visualize the shadow map, render it to the screen in a corner:
```python
# In render() after pass 2:
self.shadow_depth.use(location=0)
# Render quad with shader that displays depth as grayscale
```
