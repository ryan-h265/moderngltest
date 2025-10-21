# Input System Documentation

## Overview

The input system uses a **Command Pattern architecture** to provide flexible, rebindable input with context management. This design separates input devices (keyboard, mouse) from game actions, making the system extensible and user-friendly.

**Version**: 0.2.0
**Date**: 2025-10-20

---

## Architecture

### Core Components

```
┌──────────────────┐
│  Raw Input       │ ← Keyboard/Mouse events
│  (main.py)       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  InputManager    │ ← Central coordinator
│                  │   - Translates keys → commands
│                  │   - Filters by context
│                  │   - Dispatches to controllers
└────────┬─────────┘
         │
         ├─────────┬──────────┬──────────┐
         ▼         ▼          ▼          ▼
    ┌─────────┬──────────┬──────────┐
    │Camera   │Game      │UI        │  ← Controllers
    │Control  │Control   │Control   │    (handle commands)
    └─────────┴──────────┴──────────┘
         │
         ▼
    ┌─────────┐
    │ Camera  │ ← Pure logic classes
    │ Player  │
    │ UI      │
    └─────────┘
```

### Module Structure

```
src/gamelib/input/
├── input_commands.py      # InputCommand enum (all possible actions)
├── input_context.py       # Context management (gameplay, menu, etc.)
├── key_bindings.py        # Key→Command mappings (rebindable)
├── input_manager.py       # Central coordinator
└── controllers/           # Command handlers
    ├── camera_controller.py
    ├── game_controller.py (placeholder)
    └── ui_controller.py   (placeholder)
```

---

## Key Concepts

### 1. Commands (Actions)

**InputCommand** defines all possible game actions, independent of input devices.

```python
from src.gamelib.input import InputCommand

# Camera commands
InputCommand.CAMERA_MOVE_FORWARD
InputCommand.CAMERA_MOVE_BACKWARD
InputCommand.CAMERA_LOOK

# Future game commands
InputCommand.GAME_JUMP
InputCommand.GAME_INTERACT
InputCommand.GAME_ATTACK

# UI commands
InputCommand.UI_NAVIGATE_UP
InputCommand.UI_CONFIRM
InputCommand.UI_CANCEL
```

**Command Types**:
- **CONTINUOUS**: Held keys (e.g., movement)
- **INSTANT**: Single press (e.g., jump)
- **AXIS**: Mouse/analog input (e.g., look)
- **TOGGLE**: On/off state (e.g., crouch)

### 2. Contexts

**InputContext** determines which commands are allowed in different game states.

```python
from src.gamelib.input import InputContext

# Available contexts
InputContext.GAMEPLAY   # Normal gameplay (camera, movement, actions)
InputContext.MENU       # UI navigation only
InputContext.DIALOGUE   # Limited input during dialogue
InputContext.INVENTORY  # Item management
# ... etc
```

**Context Stack**: Contexts can be pushed/popped (e.g., open menu → push MENU context).

### 3. Key Bindings

**KeyBindings** maps physical keys to commands. Fully rebindable with save/load support.

Default bindings:
```python
W/A/S/D  → Camera movement
Q/E      → Camera up/down
Mouse    → Camera look
ESC      → Toggle mouse capture
F1       → Screenshot
F4       → Toggle debug
```

### 4. Controllers

Controllers translate commands into specific actions. They register handlers with InputManager.

---

## Usage

### Basic Setup

```python
from src.gamelib import Camera, InputManager, CameraController

# Create components
camera = Camera(position)
input_manager = InputManager()
camera_controller = CameraController(camera, input_manager)

# Update every frame
def update(frametime):
    input_manager.update(frametime)
```

### Handling Input Events

```python
# In your window class (e.g., main.py)

def on_key_event(self, key, action, modifiers):
    if action == self.wnd.keys.ACTION_PRESS:
        self.input_manager.on_key_press(key)
    elif action == self.wnd.keys.ACTION_RELEASE:
        self.input_manager.on_key_release(key)

def on_mouse_position_event(self, _x, _y, dx, dy):
    self.input_manager.on_mouse_move(dx, dy)
```

### Registering Custom Handlers

```python
# Register a handler for a command
input_manager.register_handler(InputCommand.GAME_JUMP, player.jump)

# Lambda for simple actions
input_manager.register_handler(
    InputCommand.SYSTEM_SCREENSHOT,
    lambda: save_screenshot()
)

# Handler with parameters (for AXIS commands)
input_manager.register_handler(
    InputCommand.CAMERA_LOOK,
    lambda dx, dy: camera_controller.rotate(dx, dy)
)
```

### Context Management

```python
# Push a new context (e.g., open menu)
input_manager.push_context(InputContext.MENU)

# Pop context (e.g., close menu)
input_manager.pop_context()

# Get current context
current = input_manager.get_current_context()
```

### Rebinding Keys

```python
# Get key bindings
bindings = input_manager.key_bindings

# Rebind a key
bindings.rebind_key(InputCommand.GAME_JUMP, 32)  # Rebind jump to SPACE

# Add additional binding
bindings.add_binding(InputCommand.CAMERA_MOVE_FORWARD, 265)  # Add UP arrow

# Save to JSON
bindings.save_bindings()  # Saves to keybindings.json

# Load from JSON
bindings.load_bindings()  # Loads from keybindings.json

# Reset to defaults
bindings.reset_to_defaults()
```

### Mouse Capture

```python
# Toggle mouse capture (called by ESC key by default)
captured = input_manager.toggle_mouse_capture()

# Set explicitly
input_manager.set_mouse_capture(True)  # Capture
input_manager.set_mouse_capture(False)  # Release
```

---

## Creating Custom Controllers

Controllers handle specific domains (camera, player, UI, etc.).

```python
from src.gamelib.input import InputManager, InputCommand

class PlayerController:
    """Controller for player actions"""

    def __init__(self, player, input_manager: InputManager):
        self.player = player
        self.input_manager = input_manager
        self._register_handlers()

    def _register_handlers(self):
        """Register input handlers"""
        # CONTINUOUS commands (held keys)
        self.input_manager.register_handler(
            InputCommand.GAME_SPRINT,
            self.sprint
        )

        # INSTANT commands (single press)
        self.input_manager.register_handler(
            InputCommand.GAME_JUMP,
            self.jump
        )

    def sprint(self, delta_time: float):
        """Sprint while key is held"""
        self.player.set_sprint(True)

    def jump(self):
        """Single jump"""
        self.player.jump()
```

---

## Default Key Bindings

### Camera Movement (WASD + QE)
| Key | Command | Action |
|-----|---------|--------|
| W | CAMERA_MOVE_FORWARD | Move camera forward |
| S | CAMERA_MOVE_BACKWARD | Move camera backward |
| A | CAMERA_MOVE_LEFT | Move camera left |
| D | CAMERA_MOVE_RIGHT | Move camera right |
| Q | CAMERA_MOVE_DOWN | Move camera down |
| E | CAMERA_MOVE_UP | Move camera up |

### System Commands
| Key | Command | Action |
|-----|---------|--------|
| ESC | SYSTEM_TOGGLE_MOUSE | Toggle mouse capture |
| F1 | SYSTEM_SCREENSHOT | Take screenshot |
| F4 | SYSTEM_TOGGLE_DEBUG | Toggle debug info |

### Mouse
| Button | Command | Action |
|--------|---------|--------|
| Move | CAMERA_LOOK | Rotate camera (when captured) |

---

## Context Filtering

Each context allows specific command categories:

### GAMEPLAY Context
- ✅ All camera commands
- ✅ All game commands
- ✅ System commands
- ❌ UI navigation commands

### MENU Context
- ❌ Camera commands
- ❌ Game commands
- ✅ UI navigation commands
- ✅ System commands

### DIALOGUE Context
- ❌ Camera commands
- ❌ Most game commands
- ✅ UI commands (advance dialogue)
- ✅ System commands

### INVENTORY Context
- ❌ Camera movement
- ❌ Combat commands
- ✅ Item manipulation
- ✅ UI navigation
- ✅ System commands

---

## Command Types in Detail

### CONTINUOUS Commands
Execute every frame while key is held.

```python
# Handler receives delta_time
def move_forward(self, delta_time: float):
    movement = speed * delta_time
    self.camera.position += self.camera._front * movement
```

### INSTANT Commands
Execute once on key press.

```python
# Handler receives no arguments
def jump(self):
    if self.player.on_ground:
        self.player.apply_force(Vector3([0, jump_force, 0]))
```

### AXIS Commands
Execute with accumulated mouse/analog input.

```python
# Handler receives dx, dy
def rotate(self, dx: float, dy: float):
    self.camera.yaw += dx * sensitivity
    self.camera.pitch += dy * sensitivity
```

### TOGGLE Commands
Execute on press, maintain state.

```python
# Handler toggles state
def toggle_crouch(self):
    self.player.crouching = not self.player.crouching
```

---

## Key Bindings File Format

Saved to `keybindings.json`:

```json
{
  "keyboard": {
    "87": "CAMERA_MOVE_FORWARD",
    "83": "CAMERA_MOVE_BACKWARD",
    "65": "CAMERA_MOVE_LEFT",
    "68": "CAMERA_MOVE_RIGHT",
    "32": "GAME_JUMP"
  },
  "mouse": {
    "1": "OBJECT_SELECT",
    "2": "GAME_ATTACK"
  }
}
```

**Key Codes**:
- Keyboard: 65-90 (A-Z), 48-57 (0-9), special keys (256=ESC, 32=SPACE, etc.)
- Mouse: 1=Left, 2=Right, 3=Middle

---

## Advanced Features

### Multiple Keys Per Command

```python
# Multiple keys for same command
bindings.add_binding(InputCommand.CAMERA_MOVE_FORWARD, 87)  # W
bindings.add_binding(InputCommand.CAMERA_MOVE_FORWARD, 265)  # UP arrow
```

### Clear All Input (Context Switch)

```python
# Clear stuck keys when changing contexts
input_manager.clear_all_input()
```

### Get Human-Readable Key Names

```python
# Get key name for display
key_name = bindings.get_key_name(87)  # → "W"
key_name = bindings.get_key_name(256)  # → "ESC"
key_name = bindings.get_key_name(-1)  # → "Left Click"
```

### Export/Import Bindings

```python
# Export to dict (for profiles)
data = bindings.export_bindings()

# Import from dict
bindings.import_bindings(data)
```

---

## Migration from Old InputHandler

### Old System (deprecated)
```python
from src.gamelib import InputHandler

input_handler = InputHandler(camera, keys)
input_handler.on_key_press(key)
input_handler.on_mouse_move(dx, dy)
input_handler.update(frametime)
```

### New System
```python
from src.gamelib import InputManager, CameraController

input_manager = InputManager()
camera_controller = CameraController(camera, input_manager)
input_manager.on_key_press(key)
input_manager.on_mouse_move(dx, dy)
input_manager.update(frametime)
```

**Benefits**:
- ✅ Rebindable keys
- ✅ Context management
- ✅ Extensible for UI, game actions
- ✅ Save/load custom bindings
- ✅ Multiple controllers
- ✅ Pure camera class (no input code)

---

## Best Practices

### 1. Use Controllers for Domains
Create separate controllers for different systems:
- CameraController (camera movement)
- PlayerController (character actions)
- UIController (menu navigation)

### 2. Register Handlers in Constructor
Register all handlers when creating the controller.

### 3. Use Contexts Appropriately
Push contexts when entering special game states (menu, dialogue, inventory).

### 4. Clear Input on Context Change
Call `clear_all_input()` when changing contexts to prevent stuck keys.

### 5. Save Bindings on Change
Call `save_bindings()` after user rebinds keys.

### 6. Load Bindings at Startup
Call `load_bindings()` in InputManager initialization (already done by default).

---

## Future Enhancements

### Planned Features
- **Gamepad support**: Add gamepad input device
- **Input recording**: Record and playback input sequences
- **Input hints**: Display current key bindings in UI
- **Profile system**: Multiple binding profiles per user
- **Dead zones**: Configurable analog dead zones
- **Sensitivity curves**: Non-linear mouse sensitivity

### Extension Points
- Add new commands to `InputCommand` enum
- Create new contexts in `InputContext` enum
- Implement new controllers for custom systems
- Add new input devices (touch, VR controllers)

---

## Troubleshooting

### Keys Not Responding
1. Check if command is allowed in current context
2. Verify key binding exists: `bindings.get_command(key)`
3. Ensure handler is registered: `command in input_manager.handlers`

### Mouse Not Working
1. Check `input_manager.mouse_captured` state
2. Verify ESC key toggles capture correctly
3. Update window cursor state: `wnd.cursor = not captured`

### Rebinding Not Saving
1. Call `bindings.save_bindings()` explicitly
2. Check write permissions for `keybindings.json`
3. Verify JSON is valid after save

### Context Not Filtering
1. Ensure context is pushed: `input_manager.push_context(context)`
2. Check context allows command: `is_command_allowed(command)`
3. Verify context stack: `get_current_context()`

---

## API Reference

### InputManager

**Methods**:
- `register_handler(command, handler)` - Register command handler
- `unregister_handler(command)` - Remove command handler
- `on_key_press(key)` - Handle key press event
- `on_key_release(key)` - Handle key release event
- `on_mouse_move(dx, dy)` - Handle mouse movement
- `on_mouse_button_press(button)` - Handle mouse button press
- `update(delta_time)` - Update continuous commands
- `push_context(context)` - Push new context
- `pop_context()` - Pop current context
- `toggle_mouse_capture()` - Toggle mouse capture
- `clear_all_input()` - Clear all input state

### KeyBindings

**Methods**:
- `get_command(key, is_mouse=False)` - Get command for key
- `get_keys_for_command(command)` - Get all keys for command
- `get_key_name(key)` - Get human-readable key name
- `rebind_key(command, new_key, is_mouse=False)` - Rebind command
- `add_binding(command, key, is_mouse=False)` - Add additional binding
- `remove_binding(key, is_mouse=False)` - Remove binding
- `clear_bindings_for_command(command)` - Clear all bindings for command
- `save_bindings()` - Save to JSON
- `load_bindings()` - Load from JSON
- `reset_to_defaults()` - Reset to default bindings
- `export_bindings()` - Export to dict
- `import_bindings(data)` - Import from dict

### Controllers

**CameraController**:
- `move_forward(delta_time)` - Move camera forward
- `move_backward(delta_time)` - Move camera backward
- `move_left(delta_time)` - Move camera left
- `move_right(delta_time)` - Move camera right
- `move_up(delta_time)` - Move camera up
- `move_down(delta_time)` - Move camera down
- `rotate(dx, dy)` - Rotate camera

---

## Examples

See [examples/input_demo.py](../examples/input_demo.py) for a complete demonstration.

---

**Documentation Version**: 1.0
**Last Updated**: 2025-10-20
**Author**: ModernGL 3D Engine Team
