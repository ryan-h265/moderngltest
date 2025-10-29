# Tool System Integration Guide

This guide explains how to integrate the tool system into your main game loop.

## Overview

The tool system consists of:
- **ToolManager**: Manages all tools and active tool selection
- **ToolController**: Handles input for tools
- **EditorHistory**: Undo/redo system
- **Editor Tools**: ModelPlacementTool, ObjectEditorTool, LightEditorTool, DeleteTool
- **GridOverlay**: Visual grid for snapping
- **PlacementPreview**: Ghost rendering for placement validation

## Integration Steps

### 1. Import Required Modules

```python
from gamelib.tools import ToolManager
from gamelib.tools.editor_history import EditorHistory
from gamelib.tools.grid_overlay import GridOverlay
from gamelib.input.controllers import ToolController
from gamelib.input.input_context import InputContext
```

### 2. Initialize Tool System (in Game.__init__)

```python
class Game:
    def __init__(self):
        # ... existing initialization ...

        # Tool system
        self.tool_manager = ToolManager(self.ctx)
        self.editor_history = EditorHistory(max_history=100)
        self.grid_overlay = GridOverlay(self.ctx, grid_size=1.0, grid_extent=50)

        # Load tools from JSON
        from gamelib.config.settings import PROJECT_ROOT
        tools_path = PROJECT_ROOT / "assets/config/tools/editor_tools.json"
        self.tool_manager.load_tools_from_json(tools_path)

        # Set editor history reference for all tools
        for tool in self.tool_manager.tools.values():
            if hasattr(tool, 'editor_history'):
                tool.editor_history = self.editor_history

            # For LightEditorTool, set lights list reference
            if hasattr(tool, 'lights_list'):
                tool.lights_list = self.lights

        # Create tool controller
        self.tool_controller = ToolController(
            self.tool_manager,
            self.input_manager,
            self.camera,
            self.scene
        )
        self.tool_controller.editor_history = self.editor_history
        self.tool_controller.lights = self.lights  # For scene saving

        # Start with first tool equipped
        self.tool_manager.equip_hotbar_slot(0)
```

### 3. Add Key Bindings (in KeyBindings._set_default_bindings)

```python
# Tool usage
self.mouse_bindings[1] = InputCommand.TOOL_USE         # Left click
self.mouse_bindings[2] = InputCommand.TOOL_USE_SECONDARY  # Right click

# Tool switching
self.keyboard_bindings[self.keys.NUMBER_1] = InputCommand.TOOL_HOTBAR_1
self.keyboard_bindings[self.keys.NUMBER_2] = InputCommand.TOOL_HOTBAR_2
self.keyboard_bindings[self.keys.NUMBER_3] = InputCommand.TOOL_HOTBAR_3
self.keyboard_bindings[self.keys.NUMBER_4] = InputCommand.TOOL_HOTBAR_4
self.keyboard_bindings[self.keys.NUMBER_5] = InputCommand.TOOL_HOTBAR_5
self.keyboard_bindings[self.keys.NUMBER_6] = InputCommand.TOOL_HOTBAR_6
self.keyboard_bindings[self.keys.NUMBER_7] = InputCommand.TOOL_HOTBAR_7
self.keyboard_bindings[self.keys.NUMBER_8] = InputCommand.TOOL_HOTBAR_8
self.keyboard_bindings[self.keys.NUMBER_9] = InputCommand.TOOL_HOTBAR_9

# Editor commands
self.keyboard_bindings[self.keys.Z] = InputCommand.EDITOR_UNDO  # With Ctrl modifier
self.keyboard_bindings[self.keys.Y] = InputCommand.EDITOR_REDO  # With Ctrl modifier
self.keyboard_bindings[self.keys.S] = InputCommand.EDITOR_SAVE_SCENE  # With Ctrl modifier
self.keyboard_bindings[self.keys.G] = InputCommand.EDITOR_TOGGLE_GRID
self.keyboard_bindings[self.keys.R] = InputCommand.EDITOR_ROTATE_CW
self.keyboard_bindings[self.keys.TAB] = InputCommand.EDITOR_TOGGLE_MODE
self.keyboard_bindings[self.keys.DELETE] = InputCommand.EDITOR_DELETE
self.keyboard_bindings[self.keys.D] = InputCommand.EDITOR_DUPLICATE  # With Ctrl modifier
self.keyboard_bindings[self.keys.B] = InputCommand.EDITOR_OPEN_BROWSER

# Model cycling (for ModelPlacementTool)
self.keyboard_bindings[self.keys.LEFT_BRACKET] = InputCommand.TOOL_PREVIOUS  # [
self.keyboard_bindings[self.keys.RIGHT_BRACKET] = InputCommand.TOOL_NEXT     # ]
```

### 4. Handle Editor Mode Toggle

```python
def toggle_editor_mode(self):
    """Toggle between GAMEPLAY and LEVEL_EDITOR contexts."""
    current_context = self.input_manager.get_current_context()

    if current_context == InputContext.GAMEPLAY:
        # Enter level editor mode
        self.input_manager.set_context(InputContext.LEVEL_EDITOR)
        self.grid_overlay.set_visible(True)
        print("Entered LEVEL EDITOR mode")

        # Enable free-fly camera
        if hasattr(self, 'camera_controller'):
            self.camera_controller.enable_free_fly()
    else:
        # Return to gameplay mode
        self.input_manager.set_context(InputContext.GAMEPLAY)
        self.grid_overlay.set_visible(False)
        print("Entered GAMEPLAY mode")
```

Register this handler:
```python
self.input_manager.register_handler(
    InputCommand.EDITOR_TOGGLE_MODE,
    self.toggle_editor_mode
)
```

### 5. Update Tools Each Frame

```python
def update(self, time: float, delta_time: float):
    # ... existing update code ...

    # Update tool manager (updates active tool)
    if self.input_manager.get_current_context() == InputContext.LEVEL_EDITOR:
        self.tool_manager.update(delta_time, self.camera, self.scene)
```

### 6. Render Tool Previews and Grid

```python
def render(self):
    # ... existing render code ...

    # After main scene rendering, before UI:
    if self.input_manager.get_current_context() == InputContext.LEVEL_EDITOR:
        # Render grid overlay
        self.grid_overlay.render(
            self.camera.get_view_matrix(),
            self.camera.get_projection_matrix()
        )

        # Render tool previews (e.g., ModelPlacementTool preview)
        active_tool = self.tool_manager.get_active_tool()
        if active_tool and hasattr(active_tool, 'render_preview'):
            active_tool.render_preview(
                self.main_program,  # Primitive shader
                self.textured_program  # Textured shader
            )
```

### 7. Handle Mouse Events for Tools

For continuous operations (drag to move/rotate), you need to track mouse state:

```python
def on_mouse_press(self, x, y, button):
    """Handle mouse button press."""
    # ... existing code ...

    # For tools, mark button as held
    if self.input_manager.get_current_context() == InputContext.LEVEL_EDITOR:
        if button == 1:  # Left button
            self.tool_left_held = True
        elif button == 2:  # Right button
            self.tool_right_held = True

def on_mouse_release(self, x, y, button):
    """Handle mouse button release."""
    # ... existing code ...

    # For tools, mark button as released and finish operations
    if self.input_manager.get_current_context() == InputContext.LEVEL_EDITOR:
        active_tool = self.tool_manager.get_active_tool()

        if button == 1:  # Left button
            self.tool_left_held = False
            if active_tool and hasattr(active_tool, 'finish_move'):
                active_tool.finish_move()
        elif button == 2:  # Right button
            self.tool_right_held = False
            if active_tool and hasattr(active_tool, 'finish_rotate'):
                active_tool.finish_rotate()

def on_mouse_drag(self, x, y, dx, dy):
    """Handle mouse drag (for continuous tool operations)."""
    if self.input_manager.get_current_context() == InputContext.LEVEL_EDITOR:
        # Provide mouse delta to tool controller
        if self.tool_right_held:
            self.tool_manager.use_active_tool_secondary(
                self.camera,
                self.scene,
                mouse_held=True,
                mouse_delta_x=dx
            )
        elif self.tool_left_held:
            self.tool_manager.use_active_tool(
                self.camera,
                self.scene,
                mouse_held=True
            )
```

## Usage Example

Once integrated, the tool system works as follows:

### Level Editor Mode
1. Press **Tab** to enter LEVEL_EDITOR mode
2. Press **1-9** to select tools from hotbar:
   - **1**: Model Placer
   - **2**: Object Editor
   - **3**: Light Editor
   - **4**: Delete Tool
3. Use tool-specific controls:
   - **Left click**: Primary action (place, select, etc.)
   - **Right click + drag**: Rotate preview/object
   - **R**: Rotate 45° (discrete)
   - **G**: Toggle grid snapping
   - **, / .**: Cycle models (ModelPlacementTool)
4. Press **Ctrl+Z/Y** for undo/redo
5. Press **Ctrl+S** to save scene
6. Press **Tab** to return to GAMEPLAY mode

### Tool Descriptions

**Model Placer (Slot 1)**:
- Previews model in green/red based on validity
- Left click to place model
- Right click drag or R key to rotate
- [ / ] to cycle through available models
- Grid snaps to configured size

**Object Editor (Slot 2)**:
- Left click to select object
- Left click drag to move object
- Right click drag to rotate object
- R to rotate 45° (discrete)
- Delete key to remove selected object

**Light Editor (Slot 3)**:
- Left click to place light
- Right click to select/move light
- Delete key to remove selected light
- Lights saved with scene

**Delete Tool (Slot 4)**:
- Left click on object to delete it
- Supports undo

## Model Library Setup

Place models in `assets/models/props/` with this structure:
```
assets/models/props/
├── model_name_1/
│   └── scene.gltf (or scene.glb)
├── model_name_2/
│   └── scene.gltf
└── ...
```

The ModelPlacementTool will automatically discover all models in this directory.

## Saved Scene Format

Scenes are saved to `scenes/scene_YYYYMMDD_HHMMSS.json`:

```json
{
  "name": "Exported Scene",
  "version": "1.0",
  "objects": [
    {
      "name": "ModelName",
      "type": "model",
      "path": "assets/models/props/model_name/scene.gltf",
      "position": [0.0, 0.0, 0.0],
      "rotation": [0.0, 0.0, 0.0],
      "scale": [1.0, 1.0, 1.0],
      "bounding_radius": 2.0
    }
  ],
  "lights": [
    {
      "type": "directional",
      "position": [0.0, 10.0, 0.0],
      "target": [0.0, 0.0, 0.0],
      "color": [1.0, 1.0, 1.0],
      "intensity": 1.0
    }
  ]
}
```

## Troubleshooting

**Tools not responding to input**:
- Check that LEVEL_EDITOR context is active
- Verify key bindings are registered
- Check tool is equipped (slot 1-9)

**Preview not showing**:
- Verify GridOverlay is rendering
- Check PlacementPreview has valid model loaded
- Ensure render order (preview after main scene)

**Undo/redo not working**:
- Verify EditorHistory is set on tools
- Check operations are being executed via history.execute()

**Scene saving fails**:
- Ensure `scenes/` directory exists or is creatable
- Check models have `source_path` attribute set
- Verify lights list is accessible to ToolController

## Next Steps

- Implement proper physics-based raycasting for object selection
- Add asset browser UI for model selection
- Implement object duplication
- Add more editor tools (terrain sculpting, prefab system, etc.)
- Create keyboard shortcuts reference in UI
