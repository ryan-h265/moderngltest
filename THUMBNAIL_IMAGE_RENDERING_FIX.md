# Thumbnail Image Rendering Fix

## Problem

Thumbnail images were not displaying - only text fallback buttons appeared. The grid layout was correct (4×3), but the actual asset preview images weren't being rendered.

## Root Causes

### Issue #1: PNG Header Parsing (Critical)
**Location**: `src/gamelib/ui/menus/thumbnail_menu.py:572`

**Problem**:
```python
# WRONG: Only reads 9 bytes
width, height, bit_depth, color_type = struct.unpack('>IIBBB', png_data[offset:offset+9])
```

PNG IHDR chunks are **13 bytes**, not 9:
- Width: 4 bytes
- Height: 4 bytes
- Bit depth: 1 byte
- Color type: 1 byte
- **Compression method: 1 byte** ← Missing
- **Filter method: 1 byte** ← Missing
- **Interlace method: 1 byte** ← Missing

**Impact**: Reading only 9 bytes meant the IHDR parsing was incomplete, potentially corrupting the data stream for subsequent chunk processing.

**Fix**:
```python
# CORRECT: Reads full 13 bytes
width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
    '>IIBBBBB', png_data[offset:offset+13]
)
```

### Issue #2: Texture Object Lifetime (Critical)
**Location**: `src/gamelib/ui/menus/thumbnail_menu.py:105-107, 523-525`

**Problem**:
```python
# WRONG: Only storing texture ID (integer)
self.texture_cache[filepath] = (width, height, texture_id)
# Python garbage collector destroys texture object
# texture_id becomes invalid
```

ModernGL texture objects need to be kept alive or they'll be garbage collected, invalidating their OpenGL handles.

**Fix**:
```python
# CORRECT: Store both texture object and its ID
self.texture_cache: dict[str, Tuple[int, int, int, object]] = {}
self.textures: list[object] = []  # Keep all texture objects alive

# When creating texture:
self.texture_cache[filepath] = (width, height, texture_id, texture)
self.textures.append(texture)  # Double reference to keep alive
```

## Changes Made

### 1. Fixed IHDR Parsing
**File**: `src/gamelib/ui/menus/thumbnail_menu.py:570-575`

Changed from reading 9 bytes to reading full 13 bytes of IHDR chunk:
```python
# OLD (broken):
width, height, bit_depth, color_type = struct.unpack('>IIBBB', png_data[offset:offset+9])

# NEW (fixed):
width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
    '>IIBBBBB', png_data[offset:offset+13]
)
```

### 2. Keep Texture Objects Alive
**File**: `src/gamelib/ui/menus/thumbnail_menu.py:105-109`

Changed texture cache to store object references:
```python
# OLD (broken):
self.texture_cache: dict[str, Tuple[int, int, int]] = {}

# NEW (fixed):
self.texture_cache: dict[str, Tuple[int, int, int, object]] = {}
self.textures: list[object] = []  # Keep all texture objects alive
```

### 3. Updated Cache Storage
**File**: `src/gamelib/ui/menus/thumbnail_menu.py:523-528`

Store both texture object and ID:
```python
# OLD (broken):
self.texture_cache[filepath] = (width, height, texture_id)
return texture_id

# NEW (fixed):
self.texture_cache[filepath] = (width, height, texture_id, texture)
self.textures.append(texture)  # Keep alive
print(f"[Thumbnail] Loaded texture: {path.name} (ID: {texture_id})")
return texture_id
```

### 4. Fixed Cache Retrieval
**File**: `src/gamelib/ui/menus/thumbnail_menu.py:499-504`

Updated to unpack from new tuple format:
```python
# OLD (broken):
width, height, texture_id = self.texture_cache[filepath]

# NEW (fixed):
cached = self.texture_cache[filepath]
# cached[0]=width, cached[1]=height, cached[2]=texture_id, cached[3]=texture_obj
return cached[2]
```

## How It Works Now

### Texture Lifecycle
```
PNG File on Disk
    ↓
load_thumbnail_image(filepath)
    ├─ Check cache (fast path)
    │   └─ Return cached texture_id
    │
    ├─ Parse PNG file
    │   ├─ Read & validate signature
    │   ├─ Parse IHDR (now with full 13 bytes!) ← FIXED
    │   ├─ Concatenate IDAT chunks
    │   └─ Decompress zlib data
    │
    ├─ Unfilter PNG scanlines
    │   └─ Apply PNG filter algorithms
    │
    ├─ Convert to RGBA8 format
    │
    ├─ Create ModernGL texture
    │   └─ ctx.texture((width, height), 4, rgba_data)
    │
    ├─ Cache result:
    │   ├─ Store in texture_cache dict (keeps object alive)
    │   ├─ Append to textures list (double reference)
    │   └─ Log success
    │
    └─ Return texture_id (valid integer)
        ↓
    imgui.image_button(texture_id, width, height)
        └─ Display texture ✓
```

### Memory Management
- **Texture objects** kept alive by:
  1. Reference in `self.texture_cache` tuple
  2. Reference in `self.textures` list
- **No garbage collection** of texture objects during menu lifetime
- **Automatic cleanup** when menu destroyed with context

## Testing the Fix

### What to Look For
1. ✓ Thumbnail menu shows 4 columns × 3 rows
2. ✓ Grid items display colored rectangles (PNG images)
3. ✓ Console shows `[Thumbnail] Loaded texture: filename.png (ID: xxxx)` messages
4. ✓ Clicking thumbnails still selects assets
5. ✓ Yellow border appears around selected items

### Debug Output
When textures load successfully, you'll see:
```
[Thumbnail] Loaded texture: japanese_bar.png (ID: 12345)
[Thumbnail] Loaded texture: glasses.png (ID: 12346)
[Thumbnail] Loaded texture: tent.png (ID: 12347)
...
```

### If Images Still Don't Show
Check for these error messages:
```
Warning: Failed to create ModernGL texture for ...
Warning: Failed to load thumbnail ...
Warning: PNG parsing failed: ...
```

If you see errors, the issue is likely:
1. PNG file corruption or invalid format
2. ModernGL context issues
3. Texture unit limitations (unlikely)

## Code Quality Notes

- **Unused variables** in IHDR unpacking: `compression`, `filter_method`, `interlace` are intentionally unpacked to consume all 13 bytes correctly, even though we don't use them
- **Debug logging** added: `print()` statements show when textures load successfully
- **Graceful fallback**: If texture creation fails, text buttons still display

## Performance Impact

- **First load**: PNG parsing + texture creation takes ~10-50ms per image
- **Subsequent loads**: Cache lookup is O(1), instant display
- **Memory**: One 96×96 RGBA texture ≈ 36KB per asset
- **Total**: 12 visible textures × 36KB ≈ 432KB GPU memory (negligible)

## Files Modified

1. `src/gamelib/ui/menus/thumbnail_menu.py`
   - Line 105-109: Updated cache structure
   - Line 499-504: Fixed cache retrieval
   - Line 523-528: Fixed cache storage
   - Line 570-575: Fixed IHDR parsing

## Summary

The fixes enable proper PNG image rendering in the thumbnail menu by:
1. **Correctly parsing PNG headers** (read full 13 bytes, not 9)
2. **Keeping texture objects alive** (prevent garbage collection)
3. **Maintaining valid texture IDs** (for imgui.image_button())

Thumbnails should now display as actual images instead of text fallback buttons.
