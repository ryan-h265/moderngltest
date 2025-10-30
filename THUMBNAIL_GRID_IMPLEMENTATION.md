# Thumbnail Menu - Grid Layout & Image Rendering Implementation

## Overview

Completely refactored the thumbnail menu with:
- **Grid-based layout**: 4 columns × 3 rows (12 items visible vs old 6 items)
- **Actual image rendering**: ModernGL textures display real asset thumbnails
- **Improved PNG parsing**: Full PNG filter algorithm support (None, Sub, Up, Average, Paeth)
- **Better selection visual**: Yellow 3px border around selected item
- **Vertical scrolling**: Mouse wheel for efficient navigation
- **Fallback rendering**: Text buttons if image loading fails

## Architecture

### Grid Layout System
```
┌─────────────────────────────────────────────────────────┐
│ Tools                                                    │
├─────────────────────────────────────────────────────────┤
│ [Model] [Light] [Object] [Material]                     │
├─────────────────────────────────────────────────────────┤
│ [Img1]  [Img2]  [Img3]  [Img4]      Items: 0/7         │
│ [Img5]  [Img6]  [Img7]  [Img8]                          │
│ [Img9]  [Img10] [Img11] [Img12]     ← Mouse scroll     │
└─────────────────────────────────────────────────────────┘
     4 columns × 3 rows = 12 items visible
```

### Texture Pipeline
```
PNG File → Parse PNG → Extract RGBA Data → Create ModernGL Texture → Cache ID → Display with imgui.image_button()
```

## Key Changes to thumbnail_menu.py

### 1. Constructor Changes
**Old**:
```python
def __init__(self, tool_manager, layout_manager=None, thumbnail_size=128,
             visible_count=6, ...)
```

**New**:
```python
def __init__(self, tool_manager, ctx, layout_manager=None, thumbnail_size=96,
             grid_cols=4, grid_rows=3, ...)
```

**Changes**:
- Added `ctx: moderngl.Context` parameter for texture creation
- Replaced `visible_count` with `grid_cols` and `grid_rows`
- Changed `grid_max_visible = grid_cols * grid_rows` (12 items)

### 2. Layout Architecture

**Old layout method**: `_draw_category_thumbnails()` with horizontal scroll
- 6 items per row
- Scroll left/right buttons
- Items arranged in single row

**New layout method**: `_draw_category_grid()` with vertical scroll
- 4 items per row, 3 rows per page
- Mouse wheel scrolling
- Items arranged in grid layout
- Automatic row wrapping

### 3. Image Rendering

**Old**: Text buttons with no images
```python
imgui.button(f"{short_name}##...", self.thumbnail_size, self.thumbnail_size)
```

**New**: Image buttons with fallback
```python
if texture_id is not None:
    imgui.image_button(texture_id, width, height, frame_padding=2)
else:
    imgui.button(...)  # Fallback to text
```

### 4. PNG Parsing Improvements

**Complete PNG filter algorithm implementation** (lines 613-672):

| Filter Type | Algorithm | Purpose |
|------------|-----------|---------|
| 0 (None) | X | No filtering |
| 1 (Sub) | X + A | Horizontal prediction |
| 2 (Up) | X + B | Vertical prediction |
| 3 (Average) | X + floor((A+B)/2) | Average prediction |
| 4 (Paeth) | X + Paeth(A,B,C) | Optimal prediction |

**Previous**: Just copied scanlines (broken for filtered PNGs)
**New**: Applies all filter types correctly

### 5. Selection Visual

**Old**: Yellow button background
```python
imgui.push_style_color(imgui.COLOR_BUTTON, 0.6, 0.6, 0.2, 1.0)
```

**New**: Yellow 3px border (visual from mockup)
```python
if is_selected:
    draw_list = imgui.get_window_draw_list()
    pos_min = imgui.get_item_rect_min()
    pos_max = imgui.get_item_rect_max()
    border_color = imgui.get_color_u32_rgba(1.0, 1.0, 0.0, 1.0)
    draw_list.add_rect(pos_min, pos_max, border_color, 3.0)
```

### 6. Texture Caching

**Structure**: `filepath → (width, height, texture_id)`

```python
self.texture_cache: dict[str, Tuple[int, int, int]] = {}
```

**Benefits**:
- Load PNG once, display many times
- Reuse ModernGL texture handles
- Fast subsequent access

### 7. Mouse Wheel Scrolling

```python
io = imgui.get_io()
if io.mouse_wheel != 0:
    scroll_offset = max(0, min(max_offset, scroll_offset - int(io.mouse_wheel)))
    self.scroll_offsets[category] = scroll_offset
```

Supports all ImGui contexts automatically.

## Updated Integration Points

### main.py Changes

**Old**:
```python
self.thumbnail_menu = ThumbnailMenu(
    self.tool_manager,
    layout_manager=self.layout_manager,
    thumbnail_size=THUMBNAIL_SIZE,
    visible_count=THUMBNAIL_VISIBLE_COUNT,
    bottom_menu_height=BOTTOM_MENU_HEIGHT,
    tool_icon_size=TOOL_ICON_SIZE,
)
```

**New**:
```python
self.thumbnail_menu = ThumbnailMenu(
    self.tool_manager,
    self.ctx,  # ← Added ModernGL context
    layout_manager=self.layout_manager,
    thumbnail_size=THUMBNAIL_SIZE,
    grid_cols=4,
    grid_rows=3,
    bottom_menu_height=BOTTOM_MENU_HEIGHT,
    tool_icon_size=TOOL_ICON_SIZE,
)
```

**Why**: ModernGL context needed to create textures on GPU

## Data Flow

```
Scene Load
  ↓
populate_from_scene()
  ├─ _populate_light_presets()
  ├─ _populate_model_library()
  └─ Creates ThumbnailItem with preview_path
      ↓
   draw() called each frame
      ↓
   _draw_category_grid()
      ├─ Iterate through grid (4×3)
      └─ For each item: _draw_thumbnail_item()
           ├─ load_thumbnail_image(preview_path)
           │   ├─ Check cache (fast path)
           │   ├─ Parse PNG (_parse_png)
           │   │   ├─ Validate PNG signature
           │   │   ├─ Extract IHDR (dimensions, color type)
           │   │   ├─ Concatenate IDAT chunks
           │   │   └─ Decompress zlib data
           │   ├─ Unfilter scanlines (_unfilter_png_data)
           │   │   └─ Apply PNG filter algorithm
           │   ├─ Convert to RGBA8 (_convert_to_rgba8)
           │   └─ Create ModernGL texture
           │       ├─ ctx.texture(size, channels, data)
           │       └─ Cache (filepath → texture_id)
           ├─ Use imgui.image_button(texture_id, ...)
           └─ Draw yellow selection border if selected
```

## Performance Characteristics

| Metric | Value |
|--------|-------|
| **Visible items** | 12 (4×3) vs 6 (old) |
| **Texture memory** | Per unique PNG (cached) |
| **CPU load** | PNG parse once per file |
| **GPU load** | Single texture bind per item |
| **Scroll performance** | O(1) - just offset change |
| **Selection border** | Simple rect draw |

## Compatibility

### Supported PNG Formats
- **Color Types**: Grayscale (0), RGB (2), Indexed (3), RGBA (6)
- **Bit Depths**: 8-bit
- **Interlacing**: Not supported (will fail gracefully)
- **Filters**: All 5 PNG filter types (0-4)

### Fallback Behavior
If image loading fails:
- Displays text button with asset name
- Yellow border still shows selection
- No visual regression
- User can still select and use items

## Testing Checklist

- [x] PNG files load correctly
- [x] ModernGL textures created without errors
- [x] Grid shows 4 columns × 3 rows
- [x] Mouse wheel scrolling works
- [x] Selection border highlights items
- [x] Clicking item selects asset
- [x] Category switching works
- [x] All asset categories load (Models, Lights, Objects)
- [x] Image fallback to text works

## Code Statistics

**Lines of Code**:
- Total: ~742 lines
- PNG parsing & filtering: ~160 lines
- Grid layout: ~60 lines
- Image rendering: ~40 lines
- texture caching & management: ~50 lines

**Key Methods**:
- `_draw_category_grid()` - Grid rendering with scrolling
- `_draw_thumbnail_item()` - Individual item with image + border
- `load_thumbnail_image()` - Texture creation pipeline
- `_parse_png()` - PNG file parsing
- `_unfilter_png_data()` - PNG filter algorithm application
- `_convert_to_rgba8()` - Format conversion
- `_paeth_predictor()` - PNG Paeth filter helper

## Error Handling

**Graceful degradation**:
1. PNG file not found → Returns None → Shows text button
2. PNG parsing fails → Logs warning → Shows text button
3. ModernGL texture creation fails → Logs warning → Shows text button
4. Invalid color type → Uses white default → Shows text button

No crashes, always functional UI.

## Future Enhancements

1. **Interlaced PNG support** - Handle Adam7 interlacing
2. **Transparency** - Proper alpha channel handling
3. **Hover effects** - Image zoom/preview on hover
4. **Drag & drop** - Drag thumbnails to scene
5. **Keyboard navigation** - Arrow keys to move selection
6. **Search/filter** - Find assets by name
7. **Custom icons** - Per-category header icons
8. **Thumbnail generation** - Render 3D models directly to thumbnails

## Integration with Menu System

Works seamlessly with:
- **LayoutManager** - Uses layout_manager for positioning
- **ObjectInspector** - Selections visible in inspector
- **ToolManager** - Tool icons in header row
- **Input system** - Mouse capture prevents clicks on scene
- **Debug overlay** - Can debug layout with F12

## Files Modified

1. `src/gamelib/ui/menus/thumbnail_menu.py` - Complete rewrite
2. `main.py` - Updated ThumbnailMenu initialization

## Summary

The thumbnail menu is now a proper grid-based asset browser with:
- ✅ Real image thumbnails (not just text)
- ✅ Efficient 4×3 grid layout
- ✅ Complete PNG support with all filters
- ✅ Proper selection highlighting
- ✅ Smooth mouse wheel scrolling
- ✅ Graceful fallback rendering
- ✅ Full caching for performance

The system is robust, efficient, and visually matches the design mockup.
