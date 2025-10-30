# Menu System Quick Start

## What's New

You now have a **robust, configuration-driven menu system** with live debugging capabilities. The editor attribute menus (thumbnail browser and object inspector) can be modified without code changes, and there's a built-in debug overlay to visualize and adjust layouts in real-time.

## Key Features

✓ **Configuration-Driven**: All panel positions and sizes defined in JSON (`src/gamelib/ui/config/menu_layouts.json`)
✓ **Live Editing**: Adjust menu layouts while the game runs
✓ **Hot Reload**: Config changes reload automatically or on-demand
✓ **Debug Visualization**: See panel boundaries and information overlays
✓ **Keyboard Shortcuts**: F12, Ctrl+Shift+D, Ctrl+Shift+S, Ctrl+Shift+R
✓ **Extensible**: Easy to add new panels and customize existing ones

## Quick Start

### 1. Launch the Editor
```bash
python main.py
```

### 2. Open a Scene
Select **Default Scene** or another scene from the main menu.

### 3. Enter Editor Mode
Press `Enter` to switch to level editor mode.

### 4. Open Attribute Menu
Press `Tab` to open the attribute mode (thumbnail menu + inspector).

### 5. Debug the Layout
- Press `F12` to toggle the debug overlay banner
- Press `Ctrl+Shift+D` to open the Layout Debug window
- Press `P` to visualize panel boundaries
- Use the debug window to adjust panel positions/sizes

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `F12` | Toggle debug overlay visibility |
| `Ctrl+Shift+D` | Open Layout Debug window |
| `Ctrl+Shift+S` | Save layout to config file |
| `Ctrl+Shift+R` | Reload config from disk |
| `P` | Toggle panel boundary visualization |

## Modifying the Layout

### Option 1: Visual Debugging (Recommended)
1. Press `F12` then `Ctrl+Shift+D` in the editor
2. In the Layout Debug window, find a panel and click "Edit"
3. Adjust X, Y, Width, Height values
4. Click "Save Changes"
5. Click "Save Config" to persist to disk

### Option 2: Direct JSON Editing
Edit `src/gamelib/ui/config/menu_layouts.json` directly, then press `Ctrl+Shift+R` to reload.

Example: Move the inspector to the left
```json
"object_inspector": {
  "anchor": "top_left",
  "position": {"x": 0, "y": 0},
  "size": {"width": 350, "height": "full"},
  "margins": {"top": 0, "right": 0, "bottom": 200, "left": 0}
}
```

## Files

**Core System**:
- `src/gamelib/ui/layout_manager.py` - Configuration parser and layout calculator
- `src/gamelib/ui/layout_debug.py` - Debug overlay and editor
- `src/gamelib/ui/config/menu_layouts.json` - Layout definitions

**Updated Menus**:
- `src/gamelib/ui/menus/thumbnail_menu.py` - Now uses LayoutManager
- `src/gamelib/ui/menus/object_inspector.py` - Now uses LayoutManager

**Integration**:
- `main.py` - Keyboard handler and render loop integration

## Adding a New Panel

1. Create your panel class (see `src/gamelib/ui/menus/object_inspector.py` for example)
2. Accept optional `layout_manager` parameter in `__init__`
3. Get panel position from layout manager in `draw()`:
   ```python
   if self.layout_manager:
       rect = self.layout_manager.get_panel_rect("panel_name", w, h)
       if rect:
           x, y, w, h = rect
   ```
4. Add configuration to `menu_layouts.json`
5. Initialize in `main.py` Game class
6. Call `draw()` in render loop

## Troubleshooting

**Panel positions wrong?**
- Press `P` to see panel boundaries
- Open debug window (`Ctrl+Shift+D`) to see exact positions
- Adjust in debug window or JSON

**Config not reloading?**
- Press `Ctrl+Shift+R` to force reload
- Check `file_watch_enabled` in debug config section

**Want to reset to defaults?**
- Delete `src/gamelib/ui/config/menu_layouts.json`
- The system will create a new default config on next run

## Next Steps

The following enhancements are planned:
- Grid-based thumbnail layout
- 3D preview window with gizmos
- Color-coded property inspector
- Multiple layout presets

For detailed information, see [docs/MENU_SYSTEM.md](docs/MENU_SYSTEM.md)
