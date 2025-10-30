# Thumbnail Rendering Debug Guide

## Current Status

The PNG parsing and file infrastructure is **working perfectly**:
- ✓ All 8 light preset PNG files exist and are valid (96x96 RGBA)
- ✓ All 7 model preview PNG files exist and are valid (96x96 RGBA)
- ✓ PNG signature validation works
- ✓ IHDR parsing correctly reads 13 bytes
- ✓ IDAT chunks decompress successfully

However, **thumbnails are not displaying** in the menu, despite assets being loaded.

## Debugging Steps

### Step 1: Run PNG Parsing Test (Optional)
To verify PNG files are valid:
```bash
python test_png_parsing.py
```

Expected output: All files parse successfully with "✓ Successfully decompressed" messages.

### Step 2: Run Editor with Debug Output
```bash
python main.py
```

1. Select a scene from the main menu
2. Press `Enter` to enter LEVEL_EDITOR mode
3. Press `Tab` to toggle ATTRIBUTE_MODE
4. **Watch the console for debug output**

### Step 3: Analyze Console Output

#### Expected Output Sequence (if working correctly):

```
[Game] Populating thumbnail menu from scene...
[Thumbnail] Found 8 light presets in /path/to/lights
[Thumbnail] Added light preset: Purple -> /path/to/Purple.png
[Thumbnail] Added light preset: Blue -> /path/to/Blue.png
... (6 more light presets)
[Thumbnail] Found 7 models in /path/to/models
[Thumbnail] Added model: japanese_bar -> /path/to/japanese_bar.png
... (6 more models)

[When you press Tab to toggle attribute mode:]
Entered ATTRIBUTE MODE
Controls:
  - Click objects in scene to select and edit
  - Use thumbnail menu to select assets
  - WASD: Move camera (mouse look disabled)
  - Adjust properties in right panel

[During rendering - should see repeatedly:]
[Thumbnail] draw() called. Total assets: 15
[Thumbnail]   ✓ Assets loaded
[Thumbnail] _draw_asset_thumbnails() called
[Thumbnail] Categories: ['Models', 'Lights']
[Thumbnail]   Category 'Models': 7 items
[Thumbnail]     - japanese_bar (preview_path: /path/to/japanese_bar.png)
... (etc for other assets)
[Thumbnail]   Category 'Lights': 8 items
[Thumbnail]     - Purple (preview_path: /path/to/Purple.png)
... (etc)

[Thumbnail] Tab bar created with 2 categories
[Thumbnail] Tab 'Models': is_open=True, is_selected=True
[Thumbnail] Drawing grid for selected tab: Models
[Thumbnail] _draw_category_grid(Models) called
[Thumbnail] Category 'Models' has 7 assets

[For each visible item in grid:]
[Thumbnail] Loading texture from: /path/to/japanese_bar.png
[Thumbnail] File exists, reading 837 bytes
[Thumbnail] Parsing PNG...
[Thumbnail] PNG parsed: 96x96, data size=36960
[Thumbnail] Creating ModernGL texture...
[Thumbnail] ✓ Successfully loaded texture: japanese_bar.png (ID: 12345)
```

### Step 4: Identify Where Output Stops

Paste the **complete console output** here, and note which of these messages DO and DON'T appear:

#### Critical Decision Points:

1. **Does `[Thumbnail] draw() called` appear?**
   - If NO → draw() method not being called
   - If YES → continue to next check

2. **Does `[Thumbnail] _draw_asset_thumbnails() called` appear?**
   - If NO → draw() returns early
   - If YES → continue to next check

3. **Does `[Thumbnail] Tab bar created with X categories` appear?**
   - If NO → Tab bar creation failing
   - If YES → continue to next check

4. **Does `[Thumbnail] Tab 'Models': is_open=True, is_selected=True` appear?**
   - If NO → Tab not selected by default
   - If `is_selected=False` → This is likely the problem!
   - If YES → continue to next check

5. **Does `[Thumbnail] _draw_category_grid(Models) called` appear?**
   - If NO → Grid drawing code not reached
   - If YES → continue to next check

6. **Does `[Thumbnail] Loading texture from:` appear?**
   - If NO → Items not being drawn or preview_path is None
   - If YES → PNG loading code is running, check next messages

7. **Does `[Thumbnail] ✓ Successfully loaded texture:` appear?**
   - If NO → ModernGL texture creation failed
   - If YES → Check if images appear in menu

## Common Issues and Fixes

### Issue: No output at all
- **Likely cause**: draw() method not being called
- **Check**: Verify `attribute_mode_active` is True (press Tab)
- **Check**: Verify `input_manager.get_current_context() == InputContext.LEVEL_EDITOR` (press Enter first)

### Issue: Output stops after "Categories: ['Models', 'Lights']"
- **Likely cause**: Tab bar creation failing
- **Error message expected**: `[Thumbnail] ERROR: Failed to create tab bar!`

### Issue: Tab shows `is_selected=False`
- **Likely cause**: ImGui not selecting first tab by default
- **Fix needed**: Set initial selected tab explicitly

### Issue: Texture loading fails
- **Look for error message**: `[Thumbnail] ✗ Failed to create ModernGL texture: ...`
- **Likely causes**:
  - Invalid GL context
  - Texture format mismatch
  - GPU memory issue

## Debug Output Files

The following additions have been made to `thumbnail_menu.py`:

1. **Line 136-143**: Added debug to detect if `self.show=False`
2. **Line 141-143**: Added debug to show total asset count in draw()
3. **Lines 252-257**: Added debug to show content of each category
4. **Lines 265-286**: Added debug for tab bar creation and selection state
5. **Lines 272-280**: Added debug showing which tab is drawn
6. **Line 122**: Added debug to track when assets are added
7. **Lines 554-599**: Comprehensive debug in load_thumbnail_image() with step-by-step logging

## What to Paste

When running the editor, please run and capture output until you press Tab to toggle attribute mode. Then wait a few seconds and stop the program. Paste all output lines starting with `[Thumbnail]` or `[Game]`.

## Next Steps

Based on the output, we'll know exactly where to look for the problem:

1. If draw() not called → Check main.py render loop condition
2. If tab not selected → Add code to set default tab
3. If texture loading fails → Debug ModernGL context issue
4. If textures load but don't show → Check imgui.image_button() usage

## Quick Restart

To remove all debug output and go back to clean code:
```bash
git checkout src/gamelib/ui/menus/thumbnail_menu.py
```

To save debug output to file for easier analysis:
```bash
python main.py 2>&1 | tee thumbnail_debug.log
```

Then examine `thumbnail_debug.log` with:
```bash
grep "\[Thumbnail\]" thumbnail_debug.log
```

