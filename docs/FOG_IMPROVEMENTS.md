# Fog System Improvements

## Summary of Changes

The fog system has been significantly enhanced to create more natural, smokey, and wispy atmospheric effects with reduced tiling artifacts.

## Key Improvements

### 1. **Better Noise Algorithm**
- **Before**: Simple `sin/cos` functions that created obvious repetitive patterns
- **After**: Proper 3D pseudo-Perlin noise with hash-based interpolation
  - Uses quintic interpolation for smoother gradients
  - Trilinear sampling of 8 cube corners for true 3D variation
  - Eliminates visible tiling and repetition

### 2. **Fractional Brownian Motion (FBM)**
- **Before**: 3 octaves with simple amplitude mixing
- **After**: 5 octaves for main fog + 3 octaves for detail layer
  - More natural turbulence and variation
  - Properly normalized amplitude falloff
  - Creates organic cloud-like structures

### 3. **Domain Warping**
- **New Feature**: Uses one noise field to distort another
  - Creates swirling, flowing patterns
  - Breaks up any remaining regularity
  - Adds organic movement to fog drift
  - Controlled by `FOG_WARP_STRENGTH` parameter

### 4. **Dual-Layer Fog System**
- **Base Layer**: Large-scale fog structures (5 octaves)
- **Detail Layer**: Fine wispy details (3 octaves) moving at 1.7x speed
  - Creates depth illusion with parallax-like effect
  - Adds high-frequency tendrils and wisps
  - Controlled by `FOG_DETAIL_SCALE` and `FOG_DETAIL_STRENGTH`

### 5. **Increased Transparency**
- **Before**: `FOG_DENSITY = 0.009`
- **After**: `FOG_DENSITY = 0.0045` (50% reduction)
  - More transparent, atmospheric haze
  - Objects remain more visible through fog
  - Better depth perception

### 6. **Improved Animation**
- **Before**: `FOG_NOISE_SPEED = 1.34` (too fast)
- **After**: `FOG_NOISE_SPEED = 0.8` (slower, more natural drift)
  - More realistic atmospheric movement
  - Dual layers move at different speeds for depth

### 7. **Larger Scale Features**
- **Before**: `FOG_NOISE_SCALE = 0.34`
- **After**: `FOG_NOISE_SCALE = 0.18` (larger features)
  - Reduces tiling perception
  - More atmospheric, less "noisy"
  - Better matches real-world fog behavior

### 8. **Stronger Variation**
- **Before**: `FOG_NOISE_STRENGTH = 0.6`
- **After**: `FOG_NOISE_STRENGTH = 0.75`
  - More pronounced wispy areas and clear gaps
  - Creates "volumetric" appearance
  - Enhanced with 1.5x multiplier for extreme variation

## New Configuration Parameters

Added to `settings.py`:

```python
FOG_DETAIL_SCALE = 0.85        # Scale for high-frequency wispy details
FOG_DETAIL_STRENGTH = 0.35     # Strength of fine detail layer  
FOG_WARP_STRENGTH = 0.4        # Domain warping intensity for organic flow
```

## Technical Implementation

### Shader Functions Added:
1. **`hash3(vec3 p)`**: Hash function for pseudo-random gradients
2. **`noise3d(vec3 p)`**: 3D Perlin-style noise with quintic interpolation
3. **`fbm(vec3 p, int octaves)`**: Fractional Brownian Motion with configurable octaves

### Performance Considerations:
- More complex shader code (5 octaves + 3 octaves + warping)
- Should still be fast on modern GPUs due to parallel execution
- Can reduce octave count if performance becomes an issue

## Fine-Tuning Tips

If you want to adjust the fog further:

**For MORE transparency:**
- Reduce `FOG_DENSITY` further (try 0.003)
- Increase `FOG_START_DISTANCE`

**For MORE wispy variation:**
- Increase `FOG_NOISE_STRENGTH` (try 0.85-0.95)
- Increase `FOG_DETAIL_STRENGTH` (try 0.45)

**For LARGER, less tiled features:**
- Reduce `FOG_NOISE_SCALE` (try 0.12-0.15)
- Reduce `FOG_DETAIL_SCALE` proportionally

**For SLOWER drift:**
- Reduce `FOG_NOISE_SPEED` (try 0.5-0.6)

**For MORE organic flow:**
- Increase `FOG_WARP_STRENGTH` (try 0.5-0.7)
- Be careful: too high creates chaotic patterns

## Before/After Comparison

### Before:
- Obvious tiling patterns from sin/cos
- Too dense/opaque
- Fast, unnatural animation
- Harsh transitions
- Limited depth perception

### After:
- Smooth, organic fog structures
- More transparent and atmospheric
- Slower, natural drift
- Wispy tendrils and variation
- Multi-layer depth illusion
- No visible tiling or repetition
