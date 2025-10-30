# Editor Menu System - Debug & Usage Guide

## What You Now Have

A **live, editable menu layout system** with real-time debugging tools. Adjust your editor menus without restarting or touching code!

## Getting Started

### 1. Start the Editor
```bash
python main.py
```

### 2. Load a Scene
From the main menu, select **Default Scene** (or any scene).

### 3. Enter Editor Mode
Press `Enter` to switch to level editor.

### 4. Activate Attribute Mode
Press `Tab` to open the attribute menu (thumbnail browser + inspector).

### 5. Access Debug Tools
- **Press `F12`** - Show/hide debug overlay banner (top of screen)
- **Press `Ctrl+Shift+D`** - Open the Layout Debug window (main editor)
- **Press `P`** - Toggle panel boundary visualization (green outlines)

## Using the Layout Debug Window

Once you press `Ctrl+Shift+D`, a window appears with:

### Panel List
Shows all active panels with their current:
- Position (X, Y coordinates)
- Size (Width × Height)

Example:
```
Thumbnail Menu (thumbnail_menu)
  Position: (0, 780)
  Size: 1280x200
  [Edit] button

Inspector (object_inspector)
  Position: (930, 0)
  Size: 350x980
  [Edit] button
```

### Editing a Panel
1. Click the **[Edit]** button next to any panel
2. The window expands to show editable fields:
   - **X**: Horizontal position in pixels
   - **Y**: Vertical position in pixels
   - **Width**: Panel width in pixels
   - **Height**: Panel height in pixels
3. Change the values (using input fields or direct typing)
4. Click **[Save Changes]** to apply immediately
5. See the changes in real-time! (no reload needed)

### Saving Your Changes
After editing, click **[Save Config]** to write your changes to disk.

This saves to: `src/gamelib/ui/config/menu_layouts.json`

### Loading Saved Config
If you manually edited the JSON file:
- Press **[Reload Config]** button in the debug window
- Or press `Ctrl+Shift+R` keyboard shortcut

## Keyboard Shortcuts Cheat Sheet

| Key | What It Does |
|-----|--------------|
| `F12` | Toggle debug banner visibility |
| `Ctrl+Shift+D` | Open/close Layout Debug window |
| `Ctrl+Shift+S` | Save current layout to file (manual save) |
| `Ctrl+Shift+R` | Reload config from disk |
| `P` | Toggle green panel boundary outlines |

## Visual Debugging

### Boundary Visualization (Press P)
When you press `P`, green outlines appear around all panels showing:
- Exact panel boundaries
- Panel names in top-left corner
- Dimensions in bottom-left corner

This helps you:
- See overlapping panels
- Verify spacing and alignment
- Understand the coordinate system

### Debug Banner (Press F12)
Shows at the very top of screen when enabled:
- Current screen resolution
- All available shortcuts
- Reminder of what each key does

## Common Tasks

### Move the Inspector to the Left Side
1. Open Layout Debug (`Ctrl+Shift+D`)
2. Click [Edit] next to "Inspector"
3. Change `X` from 930 to 0
4. Click [Save Changes]
5. Watch it move in real-time!
6. Click [Save Config] to keep the change

### Make the Thumbnail Menu Taller
1. Open Layout Debug
2. Click [Edit] next to "Thumbnail Menu"
3. Change `Height` from 200 to 300
4. Click [Save Changes]
5. Click [Save Config]

### Reset Everything to Defaults
Delete the config file:
```bash
rm src/gamelib/ui/config/menu_layouts.json
```
Restart the editor - a new default config will be created.

### Find Out Why Panels Overlap
1. Press `P` to see boundaries
2. Press `Ctrl+Shift+D` to open debug window
3. Look at the positions - which panels are overlapping?
4. Edit one to move it out of the way
5. Save and check with visual boundaries again

## Understanding the JSON (Advanced)

The layout is defined in `src/gamelib/ui/config/menu_layouts.json`

Each panel has:
```json
"panel_name": {
  "name": "Display Name",
  "enabled": true,
  "anchor": "bottom_left",
  "position": {"x": 0, "y": -200},
  "size": {"width": "full", "height": 200},
  "margins": {"top": 0, "right": 350, "bottom": 0, "left": 0}
}
```

**Key concepts:**
- **anchor**: Where the position is measured from (top_left, top_right, bottom_left, bottom_right)
- **position**: X, Y offset from the anchor point
- **width/height**: Can be pixels (int) or "full"
- **margins**: Space to leave around this panel

You can edit this file directly if you prefer:
1. Edit the JSON
2. Press `Ctrl+Shift+R` to reload
3. Changes apply immediately!

## Troubleshooting

### "Debug window won't appear"
Make sure you pressed `Ctrl+Shift+D` (hold Ctrl and Shift, then press D).

### "Changes aren't saving"
After editing in the debug window:
1. Click [Save Changes] (applies immediately)
2. Click [Save Config] button (saves to disk)

### "Manually edited JSON but changes didn't appear"
Press `Ctrl+Shift+R` to reload from disk.

### "Want to undo recent changes"
1. Close the debug window
2. Edit the JSON directly back to what you want
3. Press `Ctrl+Shift+R` to reload

### "Panels keep resetting to old positions"
Make sure you clicked [Save Config] after editing. This saves to disk so changes persist.

## Performance Notes

The debug system has minimal overhead:
- Only active when F12/debug window is used
- File watching only checks on demand
- No performance impact when not debugging

## Next Improvements Coming

The menu system is designed to support:
1. **Grid-based thumbnail display** - Instead of left/right scroll buttons
2. **3D preview window** - See objects with rotation gizmos
3. **Color-coded properties** - Labels with colors (X=red, Y=green, Z=blue)

These will integrate seamlessly with the current system!

## Need More Details?

See [docs/MENU_SYSTEM.md](docs/MENU_SYSTEM.md) for:
- Complete API reference
- Adding new custom panels
- Configuration format details
- Architecture explanation
- Code examples

## Quick Reference

```
┌─────────────────────────────────────────────────────┐
│ Editor Keyboard Shortcuts                           │
├─────────────────────────────────────────────────────┤
│ Tab              → Toggle attribute menu             │
│ F12              → Toggle debug banner              │
│ Ctrl+Shift+D     → Open Layout Debug window        │
│ Ctrl+Shift+S     → Save layout config              │
│ Ctrl+Shift+R     → Reload layout config            │
│ P                → Show panel boundaries           │
└─────────────────────────────────────────────────────┘
```

---

**That's it!** You now have full control over your editor menu layout, with live debugging and instant feedback. Happy designing! 🎯
