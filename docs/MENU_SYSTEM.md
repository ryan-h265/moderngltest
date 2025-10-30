# Editor Menu System - Developer Guide

## Overview

The editor attribute menus now use a robust, configuration-driven layout system that supports live editing and debugging. This guide covers the architecture and how to modify or extend the menus.

## Architecture

### Core Components

**1. LayoutManager** (`src/gamelib/ui/layout_manager.py`)
- Manages configuration-driven panel positioning and sizing
- Supports constraint-based layout (anchors, margins, responsive sizing)
- Auto-calculates panel positions to prevent overlaps
- File-watching for hot-reload of configuration changes

**2. LayoutDebugOverlay** (`src/gamelib/ui/layout_debug.py`)
- Live layout editor with keyboard shortcuts
- Visual debug overlays (panel boundaries, margins)
- Interactive panel editor for real-time position/size adjustments
- Keyboard shortcuts:
  - `F12` - Toggle debug overlay
  - `Ctrl+Shift+D` - Toggle debug window
  - `Ctrl+Shift+S` - Save layout config
  - `Ctrl+Shift+R` - Reload config from disk
  - `P` - Toggle panel bounds visualization

**3. Menu Layouts Configuration** (`src/gamelib/ui/config/menu_layouts.json`)
- JSON-based layout definitions
- Panel positioning, sizing, and styling
- Theme colors and property colors
- Debug settings

**4. ThumbnailMenu** (`src/gamelib/ui/menus/thumbnail_menu.py`)
- Asset browser with category tabs
- Tool icons and asset thumbnails
- Now uses LayoutManager for positioning (optional)

**5. ObjectInspector** (`src/gamelib/ui/menus/object_inspector.py`)
- Property editor for selected objects
- Edit transform, color, physics, etc.
- Now uses LayoutManager for positioning (optional)

## Configuration System

### menu_layouts.json Structure

```json
{
  "metadata": {
    "version": "1.0",
    "description": "Editor attribute menu layout configuration",
    "last_modified": "2025-10-30"
  },
  "panels": {
    "panel_name": {
      "name": "Display Name",
      "type": "panel_type",
      "enabled": true,
      "anchor": "bottom_left",  // top_left, top_right, bottom_left, bottom_right
      "position": {
        "x": 0,
        "y": -200,
        "reference": "screen"
      },
      "size": {
        "width": "full",  // pixels or "full"/"fill"
        "height": 200
      },
      "margins": {
        "top": 0,
        "right": 350,
        "bottom": 0,
        "left": 0
      },
      "layout": {
        // Panel-specific settings
      }
    }
  },
  "theme": {
    "colors": {
      // Color definitions
    },
    "property_colors": {
      // Property-specific colors
    }
  },
  "debug": {
    "show_panel_bounds": false,
    "show_margins": false,
    "show_performance": false,
    "file_watch_enabled": true,
    "auto_reload": false
  }
}
```

### Available Anchors

- `top_left` - Top-left corner
- `top_right` - Top-right corner
- `bottom_left` - Bottom-left corner
- `bottom_right` - Bottom-right corner

### Size Values

- **Pixels** (int): Fixed size in pixels
- **"full"**: Take full available space minus margins
- **"fill"**: Fill available space

## Quick Start: Debugging the Menu Layout

### 1. Enable Debug Mode

Press `F12` while the editor is running to toggle the debug overlay.

### 2. View Layout Information

Press `Ctrl+Shift+D` to open the Layout Debug window. This shows:
- All enabled panels with their current positions and sizes
- Interactive editors to adjust panel properties
- Save/reload controls
- Layout statistics

### 3. Visualize Panel Bounds

Press `P` to toggle panel boundary visualization. This draws outlines around all panels and shows their dimensions.

### 4. Make Changes

In the Layout Debug window:
1. Click "Edit" button next to a panel name
2. Adjust X, Y, Width, and Height using the input fields
3. Click "Save Changes" to apply
4. Click "Save Config" button to save to disk

### 5. Live Reload

The system watches `menu_layouts.json` for changes. Press `Ctrl+Shift+R` to manually reload if auto-reload is disabled.

## Modifying the Layout

### Option 1: Using the Debug Interface (Easiest)

1. Run the editor
2. Press `F12` then `Ctrl+Shift+D` to open debug window
3. Adjust panel positions/sizes visually
4. Click "Save Config" to persist changes

### Option 2: Direct JSON Editing

Edit `src/gamelib/ui/config/menu_layouts.json` directly, then press `Ctrl+Shift+R` to reload.

Example: Move inspector to left side
```json
"object_inspector": {
  "anchor": "top_left",  // Changed from top_right
  "position": {
    "x": 0,
    "y": 0
  },
  "size": {
    "width": 350,
    "height": "full"
  },
  "margins": {
    "top": 0,
    "right": 0,
    "bottom": 200,
    "left": 0
  }
}
```

## Adding a New Panel

### Step 1: Create the Panel Component

```python
# src/gamelib/ui/menus/my_panel.py
class MyPanel:
    def __init__(self, layout_manager=None):
        self.layout_manager = layout_manager
        self.show = True

    def draw(self, screen_width, screen_height):
        if not self.show:
            return

        # Get position from layout manager if available
        if self.layout_manager:
            rect = self.layout_manager.get_panel_rect(
                "my_panel", screen_width, screen_height
            )
            if rect:
                x, y, w, h = rect
        else:
            # Fallback positioning
            x, y, w, h = 0, 0, 400, 300

        imgui.set_next_window_position(x, y, imgui.ALWAYS)
        imgui.set_next_window_size(w, h, imgui.ALWAYS)

        if imgui.begin("My Panel##my_panel", self.show):
            # Draw panel content
            imgui.text("Hello World")
            imgui.end()
```

### Step 2: Add Configuration

Add to `menu_layouts.json`:
```json
"my_panel": {
  "name": "My Panel",
  "type": "my_panel",
  "enabled": true,
  "anchor": "top_left",
  "position": {"x": 0, "y": 0, "reference": "screen"},
  "size": {"width": 400, "height": 300},
  "margins": {"top": 0, "right": 0, "bottom": 0, "left": 0},
  "layout": {}
}
```

### Step 3: Initialize in Main Game

```python
# In Game.__init__()
self.my_panel = MyPanel(layout_manager=self.layout_manager)

# In Game.render loop
self.my_panel.draw(int(self.wnd.width), int(self.wnd.height))
```

## LayoutCalculator API

The `LayoutCalculator` class provides position/size calculations:

```python
from src.gamelib.ui.layout_manager import LayoutCalculator

# Calculate panel rectangle
x, y, width, height = LayoutCalculator.calculate_panel_rect(
    panel,          # PanelLayout object
    screen_width,   # Screen width in pixels
    screen_height,  # Screen height in pixels
    other_panels    # Dict of other panels (optional)
)
```

## Keyboard Shortcuts Reference

| Key | Action |
|-----|--------|
| F12 | Toggle debug overlay banner |
| Ctrl+Shift+D | Toggle debug window (inspector, controls) |
| Ctrl+Shift+S | Save current layout to config file |
| Ctrl+Shift+R | Reload config from disk |
| P | Toggle panel bounds visualization |

## Performance Optimization

The debug overlay tracks frame times for performance monitoring:

```python
# Record frame time (in milliseconds)
self.layout_debug.record_frame_time(frame_time_ms)

# Get average frame time
avg_time = self.layout_debug.get_average_frame_time()
```

## Troubleshooting

### Panels Overlapping
1. Press `P` to visualize boundaries
2. Open debug window with `Ctrl+Shift+D`
3. Edit positions to fix overlaps

### Changes Not Applied
- Make sure to click "Save Config" in debug window
- Or press `Ctrl+Shift+S` after manual JSON edits
- Press `Ctrl+Shift+R` to reload

### Config Not Reloading
- Check that `file_watch_enabled` is `true` in debug config
- Or manually press `Ctrl+Shift+R` to force reload

## Future Enhancements

- Grid-based thumbnail layout (currently horizontal scroll)
- 3D preview window with manipulation gizmos
- Enhanced property editor with color-coded labels
- Multiple layout presets (compact, detailed, minimal)
- Layout animations and transitions
- Docking system for custom panel arrangements

## Integration with Other Systems

The LayoutManager integrates with:
- **InputManager**: Debug shortcuts captured in `on_key_event()`
- **UIManager**: ImGui rendering calls in main render loop
- **ThumbnailMenu**: Optional layout manager for positioning
- **ObjectInspector**: Optional layout manager for positioning

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - Overall engine architecture
- [INPUT_SYSTEM.md](INPUT_SYSTEM.md) - Input handling
- [SHADER_GUIDE.md](SHADER_GUIDE.md) - Shader programming
