# Asset Caching System

## Overview

The asset caching system provides automatic model caching with reference counting and memory management, following industry-standard patterns used by Unity, Unreal, and Godot.

**Performance Impact**: 5-20x faster model placement (5ms vs 50-200ms per placement for identical models)

## How It Works

### 1. Automatic Model Caching

When you load a GLTF/GLB model using `GltfLoader.load()`:

```python
loader = GltfLoader(ctx)

# First load: reads from disk (~100ms)
model1 = loader.load("assets/models/lantern.glb")

# Subsequent loads: return clones instantly (~5ms) ✓ Fast!
model2 = loader.load("assets/models/lantern.glb")
model3 = loader.load("assets/models/lantern.glb")
```

**What happens behind the scenes:**
1. **First load**: GltfLoader parses the GLTF file, creates GPU resources (VAOs, textures), and caches the model
2. **Subsequent loads**: Cache hit! Returns a cloned instance that shares GPU resources but has independent transforms
3. **Cloning is instant** because it only copies lightweight state (position, rotation, scale)

### 2. Shared GPU Resources

Cloned models share:
- **Vertex Array Objects (VAOs)** - Same geometry data on GPU
- **Textures** - Same image data on GPU (PBR materials: albedo, normal, metallic-roughness)
- **Materials** - Same material properties
- **Skeleton & Animations** - Same rigged data and animation definitions

Each clone has independent:
- **Position, Rotation, Scale** - Unique transforms
- **Animation Playback State** - Each instance animates separately
- **Animation Controller** - Separate playback control per instance

### 3. Reference Counting

Models in cache have reference counts:

```python
asset_mgr = AssetManager.get_instance()

# Load model (ref_count = 1)
model1 = loader.load("model.glb")

# Clone (ref_count = 1 in cache, instance doesn't increase it)
model2 = loader.load("model.glb")  # Still ref_count = 1

# Original stays in cache as long as either model exists
```

### 4. Memory Management

The asset manager enforces a memory budget (default 500 MB):

```python
asset_mgr = AssetManager.get_instance(ctx, memory_budget_mb=500)

# Monitors memory usage
stats = asset_mgr.get_cache_stats()
print(f"Using {stats['total_memory_mb']:.1f} MB of {stats['memory_budget_mb']:.0f} MB")
# Output: Using 45.2 MB of 500 MB

# LRU eviction: Removes least-recently-used models when budget exceeded
# (only if they have no active references)
```

## API Reference

### GltfLoader.load()

```python
model = loader.load(
    filepath: str,      # Path to .gltf or .glb file
    use_cache: bool = True  # Enable caching (default True)
)
```

**With caching enabled (default)**:
- First load: Full parsing + GPU upload
- Subsequent loads: Cache hit → instant clone

**With `use_cache=False`**:
- Every call does full load (for testing/uncached scenarios)

### Model.clone()

```python
original = loader.load("model.glb")
instance = original.clone()

# Independent transforms
instance.position = Vector3([10, 0, 0])
instance.rotation = Vector3([0, math.radians(45), 0])
instance.scale = Vector3([2, 2, 2])
```

### AssetManager

```python
asset_mgr = AssetManager.get_instance(ctx, memory_budget_mb=500)

# Check cache status
stats = asset_mgr.get_cache_stats()
print(asset_mgr.get_formatted_status(verbose=True))

# Manual cache control
is_cached = asset_mgr.is_cached("path/to/model.glb")
asset_mgr.clear_cache()  # Nuclear option (for testing)
```

## Performance Benchmarks

### Loading the same model multiple times:

| Scenario | Time | Improvement |
|----------|------|-------------|
| Load fresh (no cache) | ~100-200ms | baseline |
| Load with cache (2nd+) | ~5-10ms | **10-20x faster** |
| Placing 10 identical models | 1-2s | 0.05-0.1s |
| Placing 100 identical models | 10-20s | 0.5-1s |

### Memory usage (typical model):

```
japanese_stone_lantern (4 meshes):
  - Textures: ~10 MB (base color, normal, metallic)
  - VAOs: ~0.5 MB (geometry)
  - Total: ~10.5 MB per unique model

100 clones share the same GPU memory:
  - 1 original cached: 10.5 MB
  - 99 clones: ~10 KB each (just transforms) = ~990 KB
  - Total: ~11.5 MB (vs ~1 GB without caching)
```

## Under the Hood

### System Components

1. **AssetManager** (`src/gamelib/core/asset_manager.py`)
   - Singleton cache manager
   - Reference counting
   - Memory budget enforcement
   - LRU eviction

2. **TexturePool** (`src/gamelib/core/texture_pool.py`)
   - Reference-counted texture management
   - Prevents duplicate texture loads
   - Automatic GPU cleanup

3. **Model.clone()** (`src/gamelib/loaders/model.py`)
   - Creates instances with shared GPU data
   - Independent transform state per clone
   - Proper animation controller creation

4. **GltfLoader Integration** (`src/gamelib/loaders/gltf_loader.py`)
   - Transparent caching layer
   - Automatic cache hit detection
   - Clone-on-hit optimization

### Data Flow

```
User calls loader.load("model.glb")
    ↓
GltfLoader.load() [with use_cache=True]
    ↓
AssetManager.is_cached("model.glb")?
    ↓YES↓                          ↓NO
  Cache hit!              Full load from disk
  Return clone()          Parse GLTF
                          Create GPU resources
                          ↓
                    AssetManager.cache_model()
                          ↓
                    Return to user
```

## Common Patterns

### Pattern 1: Browse and Place Models

```python
# In model placement tool:
def select_model(name):
    # Caching is automatic - no code changes needed!
    preview_model = loader.load(self.model_paths[name])
    self.preview.set_model(preview_model)

def place_model():
    # Second load of same model → instant clone
    model = loader.load(self.selected_path)
    model.position = placement_pos
    scene.add_object(model)
```

### Pattern 2: Batch Placement

```python
# Place 100 trees efficiently
template = loader.load("tree.glb")  # Load once
for i in range(100):
    tree = template.clone()  # Instant clone
    tree.position = forest_positions[i]
    scene.add_object(tree)
```

### Pattern 3: Preload at Startup

```python
def init_game():
    # Preload commonly used models
    preload_paths = [
        "assets/models/player.glb",
        "assets/models/enemy.glb",
        "assets/models/item.glb",
    ]
    for path in preload_paths:
        loader.load(path)  # Cache during initialization

    # Later placements are instant
```

### Pattern 4: Cache Statistics (Debug)

```python
# Print cache status
asset_mgr = AssetManager.get_instance()
print(asset_mgr.get_formatted_status(verbose=True))

# Output:
# ═══════════════════════════════════════
#         Asset Manager Cache Status
# ═══════════════════════════════════════
# Cached Models: 3
# Memory: 32.5 MB / 500 MB (6.5%)
# Hit Rate: 73.3% (11 hits, 4 misses)
# Evictions: 0 | Total Loads: 7
# ───────────────────────────────────────
# Cached Assets:
#   japanese_stone_lantern   10.5 MB (refs: 1)
#   japanese_bar            15.2 MB (refs: 2)
#   tent                     7.3 MB (refs: 0)
# ═══════════════════════════════════════
```

## Advanced: Texture Reference Counting

The TexturePool provides automatic texture lifetime management:

```python
from src.gamelib.core.texture_pool import TexturePool

pool = TexturePool.get_instance(ctx)

# Materials automatically register/unregister textures
# (This happens internally during model loading/cloning)

# Check texture usage
refs = pool.get_texture_ref_count("texture_path.png")
print(f"Texture used by {refs} materials")
```

## Limitations and Notes

1. **First load is still slow**: Caching doesn't help the first load (parsing + GPU upload is necessary)
2. **Memory budget**: Default 500 MB may need adjustment based on target platform
3. **LRU eviction**: Only evicts models with `ref_count == 0`
4. **Animations**: Each clone gets independent animation state (required for multiplayer/multiple instances)
5. **Texture sharing**: Textures are shared unless modified (immutable after loading)

## Troubleshooting

**Q: Models are still loading slowly**
A: First load is always slow. If subsequent loads are slow:
- Check `print()` output: Should show "Loading from cache (cloned instance)"
- Verify `use_cache=True` (default)

**Q: Cache hitting memory limit**
A: Increase budget: `AssetManager.get_instance(ctx, memory_budget_mb=1000)`

**Q: Need to force reload a model**
A: `loader.load("path.glb", use_cache=False)`

**Q: Cloned models look different**
A: Clones share GPU data but should look identical. Check:
- Model transforms (position, rotation, scale)
- Material assignments in GLTF

## See Also

- [MODEL_LOADING.md](MODEL_LOADING.md) - GLTF loading guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview
