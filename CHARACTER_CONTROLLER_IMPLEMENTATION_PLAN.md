# Character Controller Implementation Plan (Revised)

**Version**: 2.0
**Date**: 2025-10-26
**Status**: Ready for Implementation

## Executive Summary

This plan details the implementation of a high-quality, physics-driven character controller for the ModernGL game engine. The design uses PyBullet's kinematic capsule colliders with manual collision resolution, integrates with the existing animation system, and provides both first-person and third-person camera rigs.

**Key Improvements from Original Plan:**
- ✅ Integrates existing animation system for character state-driven animations
- ✅ Extends PhysicsWorld with required velocity and collision query methods
- ✅ Clarifies kinematic body approach for predictable movement
- ✅ Specifies PlayerCharacter class architecture and Scene integration
- ✅ Provides concrete camera rig implementations with spring interpolation
- ✅ Details input context migration and key rebinding strategy
- ✅ Includes physics tuning constants and debug visualization

---

## Phase 1: Physics Layer Extensions

**Goal**: Extend `PhysicsWorld` with methods required for character control.

### 1.1 Add Velocity Control Methods

**File**: `src/gamelib/physics/physics_world.py`

Add these methods after the `get_body()` method (line 576):

```python
def get_linear_velocity(self, body_id: int) -> Tuple[float, float, float]:
    """Get the linear velocity of a body."""
    if body_id not in self._bodies:
        raise ValueError(f"Body {body_id} not found")
    linear_vel, _ = _pb.getBaseVelocity(body_id, physicsClientId=self._client)
    return linear_vel

def set_linear_velocity(self, body_id: int, velocity: Tuple[float, float, float]) -> None:
    """Set the linear velocity of a body directly."""
    if body_id not in self._bodies:
        raise ValueError(f"Body {body_id} not found")
    _, angular_vel = _pb.getBaseVelocity(body_id, physicsClientId=self._client)
    _pb.resetBaseVelocity(
        body_id,
        linearVelocity=_vec3(velocity),
        angularVelocity=angular_vel,
        physicsClientId=self._client,
    )

def get_angular_velocity(self, body_id: int) -> Tuple[float, float, float]:
    """Get the angular velocity of a body."""
    if body_id not in self._bodies:
        raise ValueError(f"Body {body_id} not found")
    _, angular_vel = _pb.getBaseVelocity(body_id, physicsClientId=self._client)
    return angular_vel

def set_angular_factor(self, body_id: int, factor: Tuple[float, float, float]) -> None:
    """
    Lock or unlock rotation axes.

    Args:
        body_id: Body to modify
        factor: (x, y, z) factors where 0 = locked, 1 = free
               Example: (0, 1, 0) allows only Y-axis rotation (yaw)
    """
    if body_id not in self._bodies:
        raise ValueError(f"Body {body_id} not found")
    _pb.changeDynamics(
        body_id,
        -1,
        angularFactor=_vec3(factor),
        physicsClientId=self._client,
    )
```

### 1.2 Add Collision Query Methods

Add these methods after velocity methods:

```python
def ray_test(
    self,
    from_pos: Tuple[float, float, float],
    to_pos: Tuple[float, float, float],
) -> Optional[Dict[str, Any]]:
    """
    Perform a raycast and return hit information.

    Returns:
        Dictionary with 'body_id', 'hit_position', 'hit_normal', 'hit_fraction'
        or None if no hit
    """
    if self._client is None:
        return None

    result = _pb.rayTest(
        _vec3(from_pos),
        _vec3(to_pos),
        physicsClientId=self._client,
    )

    if result and result[0][0] != -1:  # Hit something
        return {
            'body_id': result[0][0],
            'hit_position': result[0][3],
            'hit_normal': result[0][4],
            'hit_fraction': result[0][2],
        }
    return None

def ray_test_all(
    self,
    from_pos: Tuple[float, float, float],
    to_pos: Tuple[float, float, float],
) -> List[Dict[str, Any]]:
    """
    Perform a raycast and return all hits along the ray.

    Returns:
        List of hit dictionaries sorted by distance
    """
    if self._client is None:
        return []

    results = _pb.rayTest(
        _vec3(from_pos),
        _vec3(to_pos),
        physicsClientId=self._client,
    )

    hits = []
    for result in results:
        if result[0] != -1:  # Valid hit
            hits.append({
                'body_id': result[0],
                'hit_position': result[3],
                'hit_normal': result[4],
                'hit_fraction': result[2],
            })

    return sorted(hits, key=lambda h: h['hit_fraction'])

def get_body_position(self, body_id: int) -> Tuple[float, float, float]:
    """Get the current position of a body."""
    if body_id not in self._bodies:
        raise ValueError(f"Body {body_id} not found")
    position, _ = _pb.getBasePositionAndOrientation(
        body_id,
        physicsClientId=self._client,
    )
    return position

def get_body_orientation(self, body_id: int) -> Tuple[float, float, float, float]:
    """Get the current orientation (quaternion) of a body."""
    if body_id not in self._bodies:
        raise ValueError(f"Body {body_id} not found")
    _, orientation = _pb.getBasePositionAndOrientation(
        body_id,
        physicsClientId=self._client,
    )
    return orientation
```

### 1.3 Add Force/Impulse Methods

Add after collision query methods:

```python
def apply_central_impulse(
    self,
    body_id: int,
    impulse: Tuple[float, float, float],
) -> None:
    """
    Apply an impulse at the body's center of mass.
    Useful for jumping and knockback.
    """
    if body_id not in self._bodies:
        raise ValueError(f"Body {body_id} not found")

    _pb.applyExternalForce(
        body_id,
        -1,
        _vec3(impulse),
        (0, 0, 0),
        _pb.LINK_FRAME,
        physicsClientId=self._client,
    )

def apply_central_force(
    self,
    body_id: int,
    force: Tuple[float, float, float],
) -> None:
    """
    Apply a continuous force at the body's center of mass.
    Force is applied for one physics step.
    """
    if body_id not in self._bodies:
        raise ValueError(f"Body {body_id} not found")

    _pb.applyExternalForce(
        body_id,
        -1,
        _vec3(force),
        (0, 0, 0),
        _pb.LINK_FRAME,
        physicsClientId=self._client,
    )
```

### 1.4 Update PhysicsWorld.__init__.py Exports

**File**: `src/gamelib/physics/__init__.py`

The exports are already comprehensive, but verify these classes are exported:
```python
__all__ = [
    "PhysicsBodyConfig",
    "PhysicsBodyHandle",
    "PhysicsWorld",
    "PhysicsWorldSettings",
]
```

---

## Phase 2: Configuration Constants

**Goal**: Add character movement tuning constants to centralized settings.

### 2.1 Add Character Movement Constants

**File**: `src/gamelib/config/settings.py`

Add this section after the camera constants (around line 50):

```python
# ==============================================================================
# Character Movement
# ==============================================================================

# Base movement speeds (meters per second)
PLAYER_WALK_SPEED = 3.0
PLAYER_RUN_SPEED = 6.0
PLAYER_SPRINT_SPEED = 9.0
PLAYER_CROUCH_SPEED = 1.5

# Air control (0.0 = no control, 1.0 = full control)
PLAYER_AIR_CONTROL_FACTOR = 0.3

# Jumping
PLAYER_JUMP_VELOCITY = 5.0  # Upward velocity on jump (m/s)
PLAYER_DOUBLE_JUMP_ENABLED = False
PLAYER_COYOTE_TIME = 0.1  # Grace period after leaving ground (seconds)

# Acceleration and damping
PLAYER_GROUND_ACCELERATION = 40.0  # How quickly reach max speed (m/s²)
PLAYER_AIR_ACCELERATION = 10.0
PLAYER_GROUND_DECELERATION = 50.0  # How quickly stop moving (m/s²)
PLAYER_AIR_DECELERATION = 5.0

# Physics capsule dimensions
PLAYER_CAPSULE_RADIUS = 0.4  # Meters (character width)
PLAYER_CAPSULE_HEIGHT = 1.8  # Meters (character height)
PLAYER_CAPSULE_MASS = 70.0   # Kilograms
PLAYER_CAPSULE_FRICTION = 0.8
PLAYER_CAPSULE_LINEAR_DAMPING = 0.1
PLAYER_CAPSULE_ANGULAR_DAMPING = 0.0

# Ground detection
PLAYER_MAX_SLOPE_ANGLE = 45.0  # Degrees (steeper slopes = slide)
PLAYER_GROUND_CHECK_DISTANCE = 0.1  # Ray length below capsule
PLAYER_STEP_HEIGHT = 0.4  # Auto-climb stairs up to this height (meters)

# Camera rig settings
PLAYER_FIRST_PERSON_EYE_HEIGHT = 1.6  # Meters above capsule base
PLAYER_THIRD_PERSON_DISTANCE = 5.0  # Default camera distance
PLAYER_THIRD_PERSON_HEIGHT = 2.0  # Camera height offset
PLAYER_THIRD_PERSON_SPRING_STIFFNESS = 0.15  # Smoothing factor (0-1)
PLAYER_THIRD_PERSON_MIN_DISTANCE = 1.0  # Closest zoom
PLAYER_THIRD_PERSON_MAX_DISTANCE = 10.0  # Farthest zoom

# Debug visualization
PLAYER_DEBUG_DRAW_CAPSULE = False
PLAYER_DEBUG_DRAW_VELOCITY = False
PLAYER_DEBUG_DRAW_GROUND_NORMAL = False
```

---

## Phase 3: Input System Extensions

**Goal**: Add player movement commands and debug camera toggle.

### 3.1 Add New Input Commands

**File**: `src/gamelib/input/input_commands.py`

Add these commands to the `InputCommand` enum (around line 15):

```python
class InputCommand(Enum):
    # ... existing camera commands ...

    # Player Movement (NEW)
    PLAYER_MOVE_FORWARD = auto()
    PLAYER_MOVE_BACKWARD = auto()
    PLAYER_MOVE_LEFT = auto()
    PLAYER_MOVE_RIGHT = auto()
    PLAYER_JUMP = auto()
    PLAYER_CROUCH = auto()
    PLAYER_SPRINT = auto()
    PLAYER_WALK = auto()  # Toggle walk/run

    # ... existing game commands ...

    # System commands
    SYSTEM_TOGGLE_DEBUG_CAMERA = auto()  # NEW
    # ... existing system commands ...
```

### 3.2 Update Command Types

In the same file, add command types (around line 70):

```python
COMMAND_TYPES = {
    # ... existing ...

    # Player movement
    InputCommand.PLAYER_MOVE_FORWARD: InputType.CONTINUOUS,
    InputCommand.PLAYER_MOVE_BACKWARD: InputType.CONTINUOUS,
    InputCommand.PLAYER_MOVE_LEFT: InputType.CONTINUOUS,
    InputCommand.PLAYER_MOVE_RIGHT: InputType.CONTINUOUS,
    InputCommand.PLAYER_JUMP: InputType.INSTANT,
    InputCommand.PLAYER_CROUCH: InputType.TOGGLE,
    InputCommand.PLAYER_SPRINT: InputType.TOGGLE,
    InputCommand.PLAYER_WALK: InputType.TOGGLE,

    # System
    InputCommand.SYSTEM_TOGGLE_DEBUG_CAMERA: InputType.INSTANT,
}
```

### 3.3 Add Debug Camera Context

**File**: `src/gamelib/input/input_context.py`

Add new context after existing contexts (around line 10):

```python
class InputContext(Enum):
    # ... existing contexts ...
    DEBUG_CAMERA = auto()  # Free-fly camera for debugging
```

Update `CONTEXT_COMMANDS` dictionary (around line 30):

```python
CONTEXT_COMMANDS = {
    InputContext.GAMEPLAY: {
        # Camera (now following player)
        InputCommand.CAMERA_LOOK,

        # Player movement (NEW)
        InputCommand.PLAYER_MOVE_FORWARD,
        InputCommand.PLAYER_MOVE_BACKWARD,
        InputCommand.PLAYER_MOVE_LEFT,
        InputCommand.PLAYER_MOVE_RIGHT,
        InputCommand.PLAYER_JUMP,
        InputCommand.PLAYER_CROUCH,
        InputCommand.PLAYER_SPRINT,
        InputCommand.PLAYER_WALK,

        # ... existing game commands ...

        # System
        InputCommand.SYSTEM_TOGGLE_MOUSE,
        InputCommand.SYSTEM_TOGGLE_DEBUG_CAMERA,
        # ... other system commands ...
    },

    InputContext.DEBUG_CAMERA: {  # NEW
        # Free-fly camera controls
        InputCommand.CAMERA_MOVE_FORWARD,
        InputCommand.CAMERA_MOVE_BACKWARD,
        InputCommand.CAMERA_MOVE_LEFT,
        InputCommand.CAMERA_MOVE_RIGHT,
        InputCommand.CAMERA_MOVE_UP,
        InputCommand.CAMERA_MOVE_DOWN,
        InputCommand.CAMERA_LOOK,

        # System
        InputCommand.SYSTEM_TOGGLE_MOUSE,
        InputCommand.SYSTEM_TOGGLE_DEBUG_CAMERA,  # To exit debug mode
        InputCommand.SYSTEM_SCREENSHOT,
        InputCommand.SYSTEM_TOGGLE_DEBUG,
        InputCommand.SYSTEM_TOGGLE_LIGHT_GIZMOS,
    },

    # ... other contexts ...
}
```

### 3.4 Update Key Bindings

**File**: `src/gamelib/input/key_bindings.py`

Modify the `__init__` method to rebind WASD/Space/Shift (around line 20):

```python
def __init__(self, wnd_keys):
    self.wnd_keys = wnd_keys
    self.key_to_command: Dict[int, InputCommand] = {}
    self.command_to_keys: Dict[InputCommand, List[int]] = {}
    self._register_defaults()
    self._load_bindings()

def _register_defaults(self):
    """Set up default key bindings."""
    # WASD - Player Movement (CHANGED from camera movement)
    self.add_binding(self.wnd_keys.W, InputCommand.PLAYER_MOVE_FORWARD)
    self.add_binding(self.wnd_keys.A, InputCommand.PLAYER_MOVE_LEFT)
    self.add_binding(self.wnd_keys.S, InputCommand.PLAYER_MOVE_BACKWARD)
    self.add_binding(self.wnd_keys.D, InputCommand.PLAYER_MOVE_RIGHT)

    # Space/Shift - Player Actions (CHANGED from camera up/down)
    self.add_binding(self.wnd_keys.SPACE, InputCommand.PLAYER_JUMP)
    self.add_binding(self.wnd_keys.LEFT_SHIFT, InputCommand.PLAYER_SPRINT)
    self.add_binding(self.wnd_keys.LEFT_CTRL, InputCommand.PLAYER_CROUCH)
    self.add_binding(self.wnd_keys.C, InputCommand.PLAYER_WALK)  # Walk toggle

    # Mouse - Camera look (unchanged)
    # (Mouse is handled separately in InputManager)

    # System commands
    self.add_binding(self.wnd_keys.ESCAPE, InputCommand.SYSTEM_TOGGLE_MOUSE)
    self.add_binding(self.wnd_keys.F1, InputCommand.SYSTEM_SCREENSHOT)
    self.add_binding(self.wnd_keys.F2, InputCommand.SYSTEM_TOGGLE_DEBUG_CAMERA)  # NEW
    self.add_binding(self.wnd_keys.F4, InputCommand.SYSTEM_TOGGLE_DEBUG)

    # Rendering toggles
    self.add_binding(self.wnd_keys.T, InputCommand.SYSTEM_TOGGLE_SSAO)
    self.add_binding(self.wnd_keys.L, InputCommand.SYSTEM_TOGGLE_LIGHT_GIZMOS)
    self.add_binding(self.wnd_keys.F7, InputCommand.SYSTEM_CYCLE_AA_MODE)
    self.add_binding(self.wnd_keys.F8, InputCommand.SYSTEM_TOGGLE_MSAA)
    self.add_binding(self.wnd_keys.F9, InputCommand.SYSTEM_TOGGLE_SMAA)
```

---

## Phase 4: Camera Rig System

**Goal**: Create modular camera rig architecture supporting FPS and third-person views.

### 4.1 Create Camera Rig Base Class

**New File**: `src/gamelib/core/camera_rig.py`

```python
"""
Camera Rig System

Provides modular camera control systems that decouple camera movement
from direct input, enabling first-person, third-person, and cinematic views.
"""

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
import math
import numpy as np
from pyrr import Vector3

from .camera import Camera
from ..config.settings import (
    PLAYER_FIRST_PERSON_EYE_HEIGHT,
    PLAYER_THIRD_PERSON_DISTANCE,
    PLAYER_THIRD_PERSON_HEIGHT,
    PLAYER_THIRD_PERSON_SPRING_STIFFNESS,
    PLAYER_THIRD_PERSON_MIN_DISTANCE,
    PLAYER_THIRD_PERSON_MAX_DISTANCE,
)

if TYPE_CHECKING:
    from ..gameplay.player_character import PlayerCharacter
    from ..physics import PhysicsWorld


class CameraRig(ABC):
    """
    Base class for camera control systems.

    A camera rig controls how the camera responds to input and follows targets.
    Subclasses implement specific behaviors (first-person, third-person, etc).
    """

    def __init__(self, camera: Camera):
        """
        Initialize camera rig.

        Args:
            camera: Camera instance to control
        """
        self.camera = camera
        self.enabled = True

    @abstractmethod
    def update(self, delta_time: float):
        """
        Update camera based on rig logic.

        Args:
            delta_time: Time elapsed since last frame (seconds)
        """
        pass

    @abstractmethod
    def apply_look_input(self, dx: float, dy: float):
        """
        Process mouse input for camera rotation.

        Args:
            dx: Horizontal mouse delta (pixels)
            dy: Vertical mouse delta (pixels)
        """
        pass

    def enable(self):
        """Enable this rig."""
        self.enabled = True

    def disable(self):
        """Disable this rig."""
        self.enabled = False


class FreeFlyRig(CameraRig):
    """
    Free-fly camera rig for debug mode.

    Provides unrestricted camera movement independent of any target.
    This is the original camera behavior (WASD movement, mouse look).
    """

    def update(self, delta_time: float):
        """No automatic updates needed - camera controlled by input handlers."""
        if self.enabled:
            self.camera.update_vectors()

    def apply_look_input(self, dx: float, dy: float):
        """Apply mouse input to camera yaw/pitch."""
        if not self.enabled:
            return

        self.camera.yaw += dx * self.camera.sensitivity
        self.camera.pitch -= dy * self.camera.sensitivity
        self.camera.update_vectors()


class FirstPersonRig(CameraRig):
    """
    First-person camera rig attached to player head.

    Camera position follows player position with eye height offset.
    Mouse input controls both camera and player orientation.
    """

    def __init__(
        self,
        camera: Camera,
        player: "PlayerCharacter",
        eye_height: float = PLAYER_FIRST_PERSON_EYE_HEIGHT,
    ):
        """
        Initialize first-person rig.

        Args:
            camera: Camera to control
            player: Player character to follow
            eye_height: Height above player base (meters)
        """
        super().__init__(camera)
        self.player = player
        self.eye_height = eye_height

    def update(self, delta_time: float):
        """Position camera at player head."""
        if not self.enabled:
            return

        # Get player position from physics body
        player_pos = self.player.get_position()

        # Position camera at eye height
        self.camera.position = player_pos + Vector3([0.0, self.eye_height, 0.0])
        self.camera.update_vectors()

    def apply_look_input(self, dx: float, dy: float):
        """Apply mouse input to camera AND player yaw."""
        if not self.enabled:
            return

        # Update camera orientation
        self.camera.yaw += dx * self.camera.sensitivity
        self.camera.pitch -= dy * self.camera.sensitivity

        # Sync player yaw with camera
        self.player.set_yaw(self.camera.yaw)

        self.camera.update_vectors()


class ThirdPersonRig(CameraRig):
    """
    Third-person camera rig with spring damping and collision avoidance.

    Camera follows player from behind with smooth interpolation.
    Performs ray tests to prevent clipping through walls.
    """

    def __init__(
        self,
        camera: Camera,
        player: "PlayerCharacter",
        physics_world: "PhysicsWorld",
        distance: float = PLAYER_THIRD_PERSON_DISTANCE,
        height: float = PLAYER_THIRD_PERSON_HEIGHT,
        spring_stiffness: float = PLAYER_THIRD_PERSON_SPRING_STIFFNESS,
    ):
        """
        Initialize third-person rig.

        Args:
            camera: Camera to control
            player: Player character to follow
            physics_world: Physics world for collision tests
            distance: Desired distance behind player (meters)
            height: Camera height offset above player (meters)
            spring_stiffness: Interpolation speed (0-1, higher = faster)
        """
        super().__init__(camera)
        self.player = player
        self.physics_world = physics_world
        self.desired_distance = distance
        self.desired_height = height
        self.spring_stiffness = spring_stiffness

        # Current actual distance (for smooth zoom)
        self.current_distance = distance

        # Collision avoidance
        self.min_distance = PLAYER_THIRD_PERSON_MIN_DISTANCE
        self.max_distance = PLAYER_THIRD_PERSON_MAX_DISTANCE
        self.collision_margin = 0.2  # Extra space from walls

    def update(self, delta_time: float):
        """Update camera position with smooth following and collision avoidance."""
        if not self.enabled:
            return

        player_pos = self.player.get_position()

        # Calculate camera direction from yaw (ignore pitch for distance calculation)
        yaw_rad = math.radians(self.camera.yaw)
        camera_direction = Vector3([
            math.cos(yaw_rad),
            0.0,
            math.sin(yaw_rad),
        ])

        # Desired camera position (behind and above player)
        target_offset = player_pos + Vector3([0.0, self.desired_height, 0.0])
        desired_pos = target_offset - camera_direction * self.desired_distance

        # Collision test: ray from player to desired camera position
        ray_start = tuple(target_offset)
        ray_end = tuple(desired_pos)
        hit = self.physics_world.ray_test(ray_start, ray_end)

        if hit:
            # Wall collision - clamp camera to hit point
            hit_fraction = hit['hit_fraction']
            safe_distance = (self.desired_distance * hit_fraction) - self.collision_margin
            safe_distance = max(safe_distance, self.min_distance)

            # Smoothly interpolate to safe distance
            self.current_distance += (safe_distance - self.current_distance) * self.spring_stiffness
        else:
            # No collision - smoothly return to desired distance
            self.current_distance += (self.desired_distance - self.current_distance) * self.spring_stiffness

        # Clamp distance
        self.current_distance = max(self.min_distance, min(self.max_distance, self.current_distance))

        # Final camera position
        final_pos = target_offset - camera_direction * self.current_distance

        # Spring interpolation for smooth movement
        self.camera.position += (final_pos - self.camera.position) * self.spring_stiffness

        self.camera.update_vectors()

    def apply_look_input(self, dx: float, dy: float):
        """Apply mouse input to camera rotation."""
        if not self.enabled:
            return

        self.camera.yaw += dx * self.camera.sensitivity
        self.camera.pitch -= dy * self.camera.sensitivity

        # Optionally sync player yaw with camera (for character rotation)
        # self.player.set_yaw(self.camera.yaw)

        self.camera.update_vectors()

    def zoom(self, delta: float):
        """
        Adjust camera distance.

        Args:
            delta: Distance change (positive = zoom out, negative = zoom in)
        """
        self.desired_distance += delta
        self.desired_distance = max(self.min_distance, min(self.max_distance, self.desired_distance))


class OrbitRig(CameraRig):
    """
    Orbit camera rig for cinematic views or object inspection.

    Camera orbits around a target point at fixed distance.
    """

    def __init__(
        self,
        camera: Camera,
        target: Vector3,
        distance: float = 10.0,
        height: float = 5.0,
    ):
        """
        Initialize orbit rig.

        Args:
            camera: Camera to control
            target: Point to orbit around
            distance: Orbit radius (meters)
            height: Orbit height above target (meters)
        """
        super().__init__(camera)
        self.target = target
        self.distance = distance
        self.height = height
        self.orbit_yaw = 0.0
        self.orbit_pitch = -20.0

    def update(self, delta_time: float):
        """Position camera in orbit around target."""
        if not self.enabled:
            return

        yaw_rad = math.radians(self.orbit_yaw)
        pitch_rad = math.radians(self.orbit_pitch)

        # Calculate orbit position
        offset = Vector3([
            math.cos(yaw_rad) * math.cos(pitch_rad),
            math.sin(pitch_rad),
            math.sin(yaw_rad) * math.cos(pitch_rad),
        ]) * self.distance

        self.camera.position = self.target + offset + Vector3([0.0, self.height, 0.0])

        # Make camera look at target
        direction = (self.target - self.camera.position).normalized
        self.camera._front = direction
        self.camera.update_vectors()

    def apply_look_input(self, dx: float, dy: float):
        """Rotate orbit angles."""
        if not self.enabled:
            return

        self.orbit_yaw += dx * self.camera.sensitivity
        self.orbit_pitch -= dy * self.camera.sensitivity

        # Clamp pitch
        self.orbit_pitch = max(-89.0, min(89.0, self.orbit_pitch))
```

### 4.2 Update Camera Controller for Rig Support

**File**: `src/gamelib/input/controllers/camera_controller.py`

Modify to support rig delegation:

```python
"""Camera input controller with rig support."""

from typing import Optional
from ...core.camera import Camera
from ...core.camera_rig import CameraRig, FreeFlyRig
from ..input_manager import InputManager
from ..input_commands import InputCommand


class CameraController:
    """
    Handles camera input commands with optional rig delegation.

    When a rig is active, look input is delegated to the rig.
    Movement input is only active in free-fly (debug) mode.
    """

    def __init__(
        self,
        camera: Camera,
        input_manager: InputManager,
        rig: Optional[CameraRig] = None,
    ):
        """
        Initialize camera controller.

        Args:
            camera: Camera instance
            input_manager: Input manager to register with
            rig: Optional camera rig (defaults to FreeFlyRig)
        """
        self.camera = camera
        self.input_manager = input_manager
        self.rig = rig or FreeFlyRig(camera)
        self.free_fly_mode = False  # Track if in debug camera mode
        self._register_handlers()

    def _register_handlers(self):
        """Register input command handlers."""
        # Movement (only active in free-fly mode)
        self.input_manager.register_handler(
            InputCommand.CAMERA_MOVE_FORWARD,
            self.move_forward,
        )
        self.input_manager.register_handler(
            InputCommand.CAMERA_MOVE_BACKWARD,
            self.move_backward,
        )
        self.input_manager.register_handler(
            InputCommand.CAMERA_MOVE_LEFT,
            self.move_left,
        )
        self.input_manager.register_handler(
            InputCommand.CAMERA_MOVE_RIGHT,
            self.move_right,
        )
        self.input_manager.register_handler(
            InputCommand.CAMERA_MOVE_UP,
            self.move_up,
        )
        self.input_manager.register_handler(
            InputCommand.CAMERA_MOVE_DOWN,
            self.move_down,
        )

        # Look (delegated to rig)
        self.input_manager.register_handler(
            InputCommand.CAMERA_LOOK,
            self.rotate,
        )

    def set_rig(self, rig: CameraRig):
        """
        Change the active camera rig.

        Args:
            rig: New rig to use
        """
        if self.rig:
            self.rig.disable()
        self.rig = rig
        self.rig.enable()

    def enable_free_fly(self):
        """Enable free-fly debug camera mode."""
        self.free_fly_mode = True
        self.set_rig(FreeFlyRig(self.camera))

    def disable_free_fly(self, gameplay_rig: CameraRig):
        """
        Disable free-fly mode and return to gameplay rig.

        Args:
            gameplay_rig: Rig to use for normal gameplay
        """
        self.free_fly_mode = False
        self.set_rig(gameplay_rig)

    # Movement handlers (only work in free-fly mode)

    def move_forward(self, delta_time: float):
        """Move camera forward (free-fly only)."""
        if not self.free_fly_mode:
            return
        movement = self.camera.speed * delta_time
        self.camera.position += self.camera._front * movement

    def move_backward(self, delta_time: float):
        """Move camera backward (free-fly only)."""
        if not self.free_fly_mode:
            return
        movement = self.camera.speed * delta_time
        self.camera.position -= self.camera._front * movement

    def move_left(self, delta_time: float):
        """Move camera left (free-fly only)."""
        if not self.free_fly_mode:
            return
        movement = self.camera.speed * delta_time
        self.camera.position -= self.camera._right * movement

    def move_right(self, delta_time: float):
        """Move camera right (free-fly only)."""
        if not self.free_fly_mode:
            return
        movement = self.camera.speed * delta_time
        self.camera.position += self.camera._right * movement

    def move_up(self, delta_time: float):
        """Move camera up (free-fly only)."""
        if not self.free_fly_mode:
            return
        movement = self.camera.speed * delta_time
        self.camera.position += Vector3([0.0, movement, 0.0])

    def move_down(self, delta_time: float):
        """Move camera down (free-fly only)."""
        if not self.free_fly_mode:
            return
        movement = self.camera.speed * delta_time
        self.camera.position -= Vector3([0.0, movement, 0.0])

    def rotate(self, dx: float, dy: float):
        """Delegate rotation to active rig."""
        self.rig.apply_look_input(dx, dy)
```

### 4.3 Update Core Package Exports

**File**: `src/gamelib/core/__init__.py`

Add camera rig exports:

```python
from .camera_rig import (
    CameraRig,
    FreeFlyRig,
    FirstPersonRig,
    ThirdPersonRig,
    OrbitRig,
)

__all__ = [
    # ... existing exports ...
    "CameraRig",
    "FreeFlyRig",
    "FirstPersonRig",
    "ThirdPersonRig",
    "OrbitRig",
]
```

---

## Phase 5: Player Character Controller

**Goal**: Create the PlayerCharacter class with physics-driven movement and animation.

### 5.1 Create Gameplay Package

**New Directory**: `src/gamelib/gameplay/`

**New File**: `src/gamelib/gameplay/__init__.py`

```python
"""Gameplay systems including player character, AI, game logic."""

from .player_character import PlayerCharacter

__all__ = ["PlayerCharacter"]
```

### 5.2 Create PlayerCharacter Class

**New File**: `src/gamelib/gameplay/player_character.py`

```python
"""
Player Character Controller

Physics-driven character controller with movement, jumping, crouching,
and animation state management.
"""

import math
from typing import Optional, Tuple
import numpy as np
from pyrr import Vector3, Quaternion

from ..physics import PhysicsWorld, PhysicsBodyHandle, PhysicsBodyConfig
from ..animation import AnimationController
from ..loaders.model import Model
from ..config.settings import (
    PLAYER_WALK_SPEED,
    PLAYER_RUN_SPEED,
    PLAYER_SPRINT_SPEED,
    PLAYER_CROUCH_SPEED,
    PLAYER_AIR_CONTROL_FACTOR,
    PLAYER_JUMP_VELOCITY,
    PLAYER_COYOTE_TIME,
    PLAYER_GROUND_ACCELERATION,
    PLAYER_AIR_ACCELERATION,
    PLAYER_GROUND_DECELERATION,
    PLAYER_AIR_DECELERATION,
    PLAYER_CAPSULE_RADIUS,
    PLAYER_CAPSULE_HEIGHT,
    PLAYER_CAPSULE_MASS,
    PLAYER_CAPSULE_FRICTION,
    PLAYER_CAPSULE_LINEAR_DAMPING,
    PLAYER_CAPSULE_ANGULAR_DAMPING,
    PLAYER_MAX_SLOPE_ANGLE,
    PLAYER_GROUND_CHECK_DISTANCE,
    PLAYER_STEP_HEIGHT,
)


class PlayerCharacter:
    """
    Player character with physics-based movement.

    Features:
    - Kinematic capsule physics body
    - Grounded detection with slope filtering
    - Jump with coyote time
    - Sprint, walk, crouch movement modes
    - Air control
    - Animation state driving
    - Automatic step-up for stairs
    """

    def __init__(
        self,
        model: Model,
        physics_world: PhysicsWorld,
        initial_position: Vector3 = None,
    ):
        """
        Initialize player character.

        Args:
            model: GLTF model for visual representation
            physics_world: Physics world to create body in
            initial_position: Starting position (default: origin)
        """
        self.model = model
        self.physics_world = physics_world

        # Set initial position
        if initial_position is not None:
            self.model.position = initial_position

        # Create physics capsule
        self.physics_body = self._create_physics_capsule()

        # Animation controller
        self.animation_controller = None
        if self.model.skeleton:
            self.animation_controller = AnimationController(self.model.skeleton)

        # Movement state
        self.movement_intent = Vector3([0.0, 0.0, 0.0])  # Desired direction (normalized)
        self.yaw = 0.0  # Character facing direction (degrees)
        self.velocity = Vector3([0.0, 0.0, 0.0])  # Current velocity (m/s)

        # Grounded state
        self.is_grounded = False
        self.time_since_grounded = 0.0  # For coyote time
        self.ground_normal = Vector3([0.0, 1.0, 0.0])

        # Movement modes
        self.is_sprinting = False
        self.is_crouching = False
        self.is_walking = False  # Walk toggle (slower than run)

        # Jump state
        self.can_jump = True
        self.jump_requested = False

    def _create_physics_capsule(self) -> PhysicsBodyHandle:
        """Create kinematic capsule collider for character."""
        config = PhysicsBodyConfig(
            shape='capsule',
            body_type='kinematic',
            radius=PLAYER_CAPSULE_RADIUS,
            height=PLAYER_CAPSULE_HEIGHT,
            mass=PLAYER_CAPSULE_MASS,
            friction=PLAYER_CAPSULE_FRICTION,
            linear_damping=PLAYER_CAPSULE_LINEAR_DAMPING,
            angular_damping=PLAYER_CAPSULE_ANGULAR_DAMPING,
        )

        handle = self.physics_world.create_body(self.model, config)

        # Lock rotation on X and Z axes (allow only Y-axis rotation)
        self.physics_world.set_angular_factor(handle.body_id, (0.0, 1.0, 0.0))

        return handle

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def set_movement_intent(self, forward: float, right: float):
        """
        Set desired movement direction.

        Args:
            forward: Forward/backward axis (-1 to 1)
            right: Right/left axis (-1 to 1)
        """
        # Build movement vector in character's local space
        if abs(forward) < 0.01 and abs(right) < 0.01:
            self.movement_intent = Vector3([0.0, 0.0, 0.0])
            return

        # Convert to world space based on character yaw
        yaw_rad = math.radians(self.yaw)
        forward_dir = Vector3([
            math.cos(yaw_rad),
            0.0,
            math.sin(yaw_rad),
        ])
        right_dir = Vector3([
            -math.sin(yaw_rad),
            0.0,
            math.cos(yaw_rad),
        ])

        intent = forward_dir * forward + right_dir * right
        self.movement_intent = intent.normalized if intent.length > 0.01 else Vector3([0.0, 0.0, 0.0])

    def request_jump(self):
        """Request a jump on next update."""
        self.jump_requested = True

    def set_sprint(self, sprinting: bool):
        """Enable or disable sprinting."""
        self.is_sprinting = sprinting

    def set_crouch(self, crouching: bool):
        """Enable or disable crouching."""
        self.is_crouching = crouching

    def toggle_walk(self):
        """Toggle walk/run mode."""
        self.is_walking = not self.is_walking

    def set_yaw(self, yaw: float):
        """
        Set character facing direction.

        Args:
            yaw: Yaw angle in degrees
        """
        self.yaw = yaw

        # Update physics body orientation
        yaw_rad = math.radians(yaw)
        quat = Quaternion.from_y_rotation(yaw_rad)

        pos = self.physics_world.get_body_position(self.physics_body.body_id)
        self.physics_world._client  # Access PyBullet directly
        import pybullet as pb
        pb.resetBasePositionAndOrientation(
            self.physics_body.body_id,
            pos,
            tuple(quat),
            physicsClientId=self.physics_world._client,
        )

    def get_position(self) -> Vector3:
        """Get current character position."""
        pos = self.physics_world.get_body_position(self.physics_body.body_id)
        return Vector3(pos)

    def get_yaw(self) -> float:
        """Get current character yaw."""
        return self.yaw

    # -------------------------------------------------------------------------
    # Update Loop
    # -------------------------------------------------------------------------

    def update(self, delta_time: float):
        """
        Update character state (call before physics step).

        Args:
            delta_time: Time since last frame (seconds)
        """
        # Update grounded state
        self._update_grounded_state(delta_time)

        # Process jump
        self._process_jump()

        # Calculate desired velocity from movement intent
        self._update_velocity(delta_time)

        # Apply velocity to physics body
        self._apply_velocity()

        # Update animation state
        self._update_animations(delta_time)

        # Reset per-frame state
        self.jump_requested = False

    def update_post_physics(self, delta_time: float):
        """
        Update after physics step (sync transforms).

        Args:
            delta_time: Time since last frame (seconds)
        """
        # Physics sync happens automatically via PhysicsWorld.sync_to_scene()
        # This method is a hook for any post-physics logic
        pass

    # -------------------------------------------------------------------------
    # Internal Update Methods
    # -------------------------------------------------------------------------

    def _update_grounded_state(self, delta_time: float):
        """Check if character is on walkable ground."""
        # Get contacts from physics world
        contacts = self.physics_world.get_contacts(body_id=self.physics_body.body_id)

        # Check for valid ground contacts
        max_slope_rad = math.radians(PLAYER_MAX_SLOPE_ANGLE)
        min_y_normal = math.cos(max_slope_rad)

        was_grounded = self.is_grounded
        self.is_grounded = False

        for contact in contacts:
            normal = Vector3(contact['normal_on_b'])
            distance = contact['distance']

            # Check if surface is walkable (normal pointing up, close contact)
            if normal.y >= min_y_normal and distance < PLAYER_GROUND_CHECK_DISTANCE:
                self.is_grounded = True
                self.ground_normal = normal
                break

        # Update coyote time
        if self.is_grounded:
            self.time_since_grounded = 0.0
            self.can_jump = True
        else:
            self.time_since_grounded += delta_time

            # Allow jump within coyote time window
            if self.time_since_grounded > PLAYER_COYOTE_TIME:
                self.can_jump = False

    def _process_jump(self):
        """Process jump request."""
        if self.jump_requested and self.can_jump:
            # Apply upward velocity
            current_vel = self.velocity
            self.velocity = Vector3([
                current_vel.x,
                PLAYER_JUMP_VELOCITY,
                current_vel.z,
            ])

            self.can_jump = False
            self.is_grounded = False

    def _update_velocity(self, delta_time: float):
        """Calculate desired velocity from movement intent."""
        # Determine target speed based on movement mode
        if self.is_crouching:
            target_speed = PLAYER_CROUCH_SPEED
        elif self.is_sprinting and not self.is_walking:
            target_speed = PLAYER_SPRINT_SPEED
        elif self.is_walking:
            target_speed = PLAYER_WALK_SPEED
        else:
            target_speed = PLAYER_RUN_SPEED

        # Calculate target velocity (horizontal only)
        target_velocity = self.movement_intent * target_speed

        # Choose acceleration/deceleration based on grounded state
        if self.is_grounded:
            acceleration = PLAYER_GROUND_ACCELERATION
            deceleration = PLAYER_GROUND_DECELERATION
        else:
            # Reduced control in air
            acceleration = PLAYER_AIR_ACCELERATION
            deceleration = PLAYER_AIR_DECELERATION
            target_speed *= PLAYER_AIR_CONTROL_FACTOR
            target_velocity = self.movement_intent * target_speed

        # Accelerate toward target velocity
        current_horizontal = Vector3([self.velocity.x, 0.0, self.velocity.z])
        target_horizontal = Vector3([target_velocity.x, 0.0, target_velocity.z])

        velocity_diff = target_horizontal - current_horizontal

        if velocity_diff.length > 0.01:
            # Accelerate
            accel_amount = acceleration * delta_time
            if velocity_diff.length < accel_amount:
                # Snap to target
                current_horizontal = target_horizontal
            else:
                # Accelerate toward target
                current_horizontal += velocity_diff.normalized * accel_amount
        else:
            # Decelerate to zero
            if current_horizontal.length > 0.01:
                decel_amount = deceleration * delta_time
                if current_horizontal.length < decel_amount:
                    current_horizontal = Vector3([0.0, 0.0, 0.0])
                else:
                    current_horizontal -= current_horizontal.normalized * decel_amount

        # Apply gravity to vertical velocity
        if not self.is_grounded:
            gravity = self.physics_world.settings.gravity[1]  # Y component
            self.velocity = Vector3([
                current_horizontal.x,
                self.velocity.y + gravity * delta_time,
                current_horizontal.z,
            ])
        else:
            # Keep vertical velocity zero when grounded
            self.velocity = Vector3([
                current_horizontal.x,
                0.0,
                current_horizontal.z,
            ])

    def _apply_velocity(self):
        """Apply calculated velocity to physics body."""
        # For kinematic bodies, we apply velocity directly
        self.physics_world.set_linear_velocity(
            self.physics_body.body_id,
            tuple(self.velocity),
        )

    def _update_animations(self, delta_time: float):
        """Update animation state based on movement."""
        if self.animation_controller is None:
            return

        # Determine animation state
        horizontal_speed = math.sqrt(self.velocity.x**2 + self.velocity.z**2)

        # Simple state machine (expand as needed)
        if not self.is_grounded:
            # TODO: Play jump/fall animation
            pass
        elif horizontal_speed < 0.1:
            # TODO: Play idle animation
            pass
        elif self.is_crouching:
            # TODO: Play crouch walk animation
            pass
        elif horizontal_speed > PLAYER_RUN_SPEED * 0.9:
            # TODO: Play sprint animation
            pass
        elif horizontal_speed > PLAYER_WALK_SPEED * 0.9:
            # TODO: Play run animation
            pass
        else:
            # TODO: Play walk animation
            pass

        # Update animation controller
        self.animation_controller.update(delta_time)

    # -------------------------------------------------------------------------
    # Debug Helpers
    # -------------------------------------------------------------------------

    def get_debug_info(self) -> dict:
        """Return debug information."""
        return {
            'position': tuple(self.get_position()),
            'yaw': self.yaw,
            'velocity': tuple(self.velocity),
            'horizontal_speed': math.sqrt(self.velocity.x**2 + self.velocity.z**2),
            'is_grounded': self.is_grounded,
            'is_sprinting': self.is_sprinting,
            'is_crouching': self.is_crouching,
            'time_since_grounded': self.time_since_grounded,
        }
```

---

## Phase 6: Player Input Controller

**Goal**: Create PlayerController to translate input commands into player actions.

### 6.1 Create PlayerController

**New File**: `src/gamelib/input/controllers/player_controller.py`

```python
"""
Player Input Controller

Handles player movement input commands and translates them
into PlayerCharacter actions.
"""

from ...gameplay.player_character import PlayerCharacter
from ..input_manager import InputManager
from ..input_commands import InputCommand


class PlayerController:
    """
    Controller for player character input.

    Registers handlers for player movement commands and drives
    the PlayerCharacter based on input.
    """

    def __init__(
        self,
        player: PlayerCharacter,
        input_manager: InputManager,
    ):
        """
        Initialize player controller.

        Args:
            player: Player character to control
            input_manager: Input manager to register with
        """
        self.player = player
        self.input_manager = input_manager

        # Movement accumulator (reset each frame)
        self.forward_input = 0.0
        self.right_input = 0.0

        self._register_handlers()

    def _register_handlers(self):
        """Register input command handlers."""
        # Movement (continuous)
        self.input_manager.register_handler(
            InputCommand.PLAYER_MOVE_FORWARD,
            self.move_forward,
        )
        self.input_manager.register_handler(
            InputCommand.PLAYER_MOVE_BACKWARD,
            self.move_backward,
        )
        self.input_manager.register_handler(
            InputCommand.PLAYER_MOVE_LEFT,
            self.move_left,
        )
        self.input_manager.register_handler(
            InputCommand.PLAYER_MOVE_RIGHT,
            self.move_right,
        )

        # Actions (instant/toggle)
        self.input_manager.register_handler(
            InputCommand.PLAYER_JUMP,
            self.jump,
        )
        self.input_manager.register_handler(
            InputCommand.PLAYER_SPRINT,
            self.toggle_sprint,
        )
        self.input_manager.register_handler(
            InputCommand.PLAYER_CROUCH,
            self.toggle_crouch,
        )
        self.input_manager.register_handler(
            InputCommand.PLAYER_WALK,
            self.toggle_walk,
        )

    # Movement handlers (accumulate input for update)

    def move_forward(self, delta_time: float):
        """Accumulate forward movement."""
        self.forward_input += 1.0

    def move_backward(self, delta_time: float):
        """Accumulate backward movement."""
        self.forward_input -= 1.0

    def move_left(self, delta_time: float):
        """Accumulate left movement."""
        self.right_input -= 1.0

    def move_right(self, delta_time: float):
        """Accumulate right movement."""
        self.right_input += 1.0

    # Action handlers

    def jump(self):
        """Request jump."""
        self.player.request_jump()

    def toggle_sprint(self):
        """Toggle sprint mode."""
        self.player.set_sprint(not self.player.is_sprinting)

    def toggle_crouch(self):
        """Toggle crouch mode."""
        self.player.set_crouch(not self.player.is_crouching)

    def toggle_walk(self):
        """Toggle walk mode."""
        self.player.toggle_walk()

    # Update

    def update(self):
        """
        Apply accumulated input to player.
        Call this each frame before physics step.
        """
        # Clamp input to [-1, 1]
        forward = max(-1.0, min(1.0, self.forward_input))
        right = max(-1.0, min(1.0, self.right_input))

        # Apply to player
        self.player.set_movement_intent(forward, right)

        # Reset accumulators
        self.forward_input = 0.0
        self.right_input = 0.0
```

### 6.2 Update Controllers Package

**File**: `src/gamelib/input/controllers/__init__.py`

Add player controller export:

```python
from .player_controller import PlayerController

__all__ = [
    # ... existing ...
    "PlayerController",
]
```

---

## Phase 7: Main Game Loop Integration

**Goal**: Wire everything together in main.py.

### 7.1 Update Main Game Class

**File**: `main.py`

Major changes:

```python
# Around line 8, add imports
from src.gamelib.gameplay import PlayerCharacter
from src.gamelib.core import FirstPersonRig, ThirdPersonRig
from src.gamelib.input.controllers import PlayerController
from src.gamelib.input import InputContext

class Game(mglw.WindowConfig):
    # ... existing config ...

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info("Initializing ModernGL Game Engine")

        # Graphics initialization (unchanged)
        self.ctx.enable_only(moderngl.DEPTH_TEST | moderngl.CULL_FACE)

        # Input system
        self.input_manager = InputManager(self.wnd.keys)

        # Camera (initial position will be overridden by rig)
        self.camera = Camera(
            position=Vector3([0.0, 5.0, 10.0]),
            target=Vector3([0.0, 0.0, 0.0]),
        )

        # Rendering pipeline
        self.render_pipeline = RenderPipeline(self.ctx, self.wnd.size)
        self.scene = Scene(self.ctx)
        self.lights = self._create_lights()
        self.render_pipeline.initialize_lights(self.lights)

        # Physics world
        try:
            self.physics_world = PhysicsWorld()
        except RuntimeError as exc:
            logger.warning("Physics world disabled: %s", exc)
            self.physics_world = None

        # Player character (NEW)
        self.player = self._create_player()
        if self.player:
            self.scene.add_object(self.player.model)

        # Camera rig (NEW)
        self.camera_rig = self._create_camera_rig()

        # Input controllers
        self.camera_controller = CameraController(
            self.camera,
            self.input_manager,
            rig=self.camera_rig,
        )

        if self.player:
            self.player_controller = PlayerController(
                self.player,
                self.input_manager,
            )

        # Rendering controller
        self.rendering_controller = RenderingController(
            self.render_pipeline,
            self.input_manager,
        )

        # Register debug camera toggle (NEW)
        self.input_manager.register_handler(
            InputCommand.SYSTEM_TOGGLE_DEBUG_CAMERA,
            self.toggle_debug_camera,
        )

        # Load scene
        self.scene_manager = SceneManager(self.ctx, self.scene, self.physics_world)
        scene_def = self.scene_manager.load_scene("main_scene")
        if scene_def:
            logger.info("Loaded scene: %s", scene_def.name)

        logger.info("Game initialization complete")

    def _create_player(self) -> Optional[PlayerCharacter]:
        """Create player character with physics."""
        if self.physics_world is None:
            logger.warning("Player character disabled (no physics)")
            return None

        from src.gamelib.loaders import GltfLoader
        from src.gamelib.config.settings import PROJECT_ROOT

        # Option 1: Load a character model
        # loader = GltfLoader(self.ctx)
        # model = loader.load(str(PROJECT_ROOT / "assets/models/character/player.gltf"))

        # Option 2: Use a simple colored cube as placeholder
        from src.gamelib.core import SceneObject
        from moderngl_window import geometry

        placeholder = SceneObject(
            geom=geometry.cube(size=(0.8, 1.8, 0.8)),
            position=Vector3([0.0, 2.0, 0.0]),
            color=(0.2, 0.5, 0.8),  # Blue
            name="Player",
        )

        player = PlayerCharacter(
            model=placeholder,
            physics_world=self.physics_world,
            initial_position=Vector3([0.0, 5.0, 0.0]),
        )

        return player

    def _create_camera_rig(self):
        """Create camera rig based on configuration."""
        if self.player is None:
            # No player - use free-fly rig
            from src.gamelib.core import FreeFlyRig
            return FreeFlyRig(self.camera)

        # Choose first-person or third-person
        # TODO: Make this configurable
        USE_FIRST_PERSON = True

        if USE_FIRST_PERSON:
            return FirstPersonRig(self.camera, self.player)
        else:
            return ThirdPersonRig(self.camera, self.player, self.physics_world)

    def toggle_debug_camera(self):
        """Toggle between gameplay camera and free-fly debug camera."""
        current_context = self.input_manager.context_manager.current_context

        if current_context == InputContext.GAMEPLAY:
            # Switch to debug camera
            logger.info("Enabling debug camera (free-fly mode)")
            self.input_manager.context_manager.push_context(InputContext.DEBUG_CAMERA)
            self.camera_controller.enable_free_fly()
        else:
            # Return to gameplay camera
            logger.info("Disabling debug camera (gameplay mode)")
            self.input_manager.context_manager.pop_context()

            # Restore gameplay rig
            gameplay_rig = self._create_camera_rig()
            self.camera_controller.disable_free_fly(gameplay_rig)
            self.camera_rig = gameplay_rig

    def on_update(self, time: float, frametime: float):
        """Update game state."""
        # Process input
        self.input_manager.update(frametime)

        # Update player controller (accumulate input)
        if self.player:
            self.player_controller.update()

        # Update player character (before physics step)
        if self.player:
            self.player.update(frametime)

        # Physics step
        if self.physics_world:
            self.physics_world.step_simulation(frametime)

        # Update player post-physics
        if self.player:
            self.player.update_post_physics(frametime)

        # Update camera rig
        self.camera_rig.update(frametime)

        # Update animations
        for obj in self.scene.objects:
            if hasattr(obj, 'animation_controller') and obj.animation_controller:
                obj.animation_controller.update(frametime)
```

---

## Phase 8: Testing and Debug Visualization

**Goal**: Add debugging tools and test character movement.

### 8.1 Add Debug Overlay

**File**: `main.py`

Add after the rendering in `on_render()`:

```python
def on_render(self, time: float, frametime: float):
    """Render the scene."""
    # Existing rendering...
    self.render_pipeline.render_frame(
        self.scene,
        self.camera,
        self.lights,
        time,
    )

    # Debug overlay (NEW)
    if PLAYER_DEBUG_DRAW_CAPSULE and self.player:
        self._draw_debug_capsule()

    if self.player:
        self._draw_debug_ui()

def _draw_debug_ui(self):
    """Draw on-screen debug text."""
    # TODO: Implement text rendering or use external library
    # For now, log to console periodically
    import time
    if not hasattr(self, '_last_debug_time'):
        self._last_debug_time = 0

    if time.time() - self._last_debug_time > 1.0:  # Every second
        info = self.player.get_debug_info()
        logger.debug(f"Player: pos={info['position']}, "
                    f"speed={info['horizontal_speed']:.2f}, "
                    f"grounded={info['is_grounded']}")
        self._last_debug_time = time.time()
```

### 8.2 Create Test Scene

**File**: `assets/scenes/test_character.json`

```json
{
  "name": "Character Test Scene",
  "metadata": {
    "gravity": [0.0, -9.81, 0.0],
    "fixed_time_step": 0.0041666667,
    "max_substeps": 4
  },
  "camera": {
    "position": [0.0, 5.0, 10.0],
    "target": [0.0, 0.0, 0.0]
  },
  "lights": [
    {
      "type": "directional",
      "position": [10.0, 15.0, 10.0],
      "target": [0.0, 0.0, 0.0],
      "color": [1.0, 1.0, 0.95],
      "intensity": 1.0
    }
  ],
  "objects": [
    {
      "name": "Ground",
      "type": "primitive",
      "primitive": "cube",
      "position": [0.0, -0.5, 0.0],
      "scale": [20.0, 1.0, 20.0],
      "color": [0.3, 0.3, 0.3],
      "physics": {
        "type": "static",
        "shape": "box",
        "half_extents": [10.0, 0.5, 10.0]
      }
    },
    {
      "name": "Stairs",
      "type": "primitive",
      "primitive": "cube",
      "position": [5.0, 0.2, 0.0],
      "scale": [2.0, 0.4, 2.0],
      "color": [0.5, 0.5, 0.5],
      "physics": {
        "type": "static",
        "shape": "box",
        "half_extents": [1.0, 0.2, 1.0]
      }
    },
    {
      "name": "Step2",
      "type": "primitive",
      "primitive": "cube",
      "position": [5.0, 0.6, 2.0],
      "scale": [2.0, 0.4, 2.0],
      "color": [0.5, 0.5, 0.5],
      "physics": {
        "type": "static",
        "shape": "box",
        "half_extents": [1.0, 0.2, 1.0]
      }
    },
    {
      "name": "Ramp",
      "type": "primitive",
      "primitive": "cube",
      "position": [-5.0, 1.0, 0.0],
      "rotation": [0.0, 0.0, 0.3],
      "scale": [2.0, 0.2, 4.0],
      "color": [0.4, 0.6, 0.4],
      "physics": {
        "type": "static",
        "shape": "box",
        "half_extents": [1.0, 0.1, 2.0]
      }
    }
  ]
}
```

---

## Phase 9: Documentation and Polish

### 9.1 Update CLAUDE.md

Add character controller section to project documentation.

### 9.2 Create Character Controller Guide

**New File**: `docs/CHARACTER_CONTROLLER.md`

Document:
- How to spawn a player character
- How to switch between first/third person
- How to customize movement parameters
- How to add character animations
- How to extend PlayerCharacter for game-specific features

### 9.3 Update INPUT_SYSTEM.md

Document new input commands and debug camera toggle.

---

## Implementation Checklist

Use this to track implementation progress:

### Phase 1: Physics Extensions
- [ ] Add velocity control methods to PhysicsWorld
- [ ] Add collision query methods (ray_test, etc.)
- [ ] Add force/impulse methods
- [ ] Test physics extensions with simple test

### Phase 2: Configuration
- [ ] Add character constants to settings.py
- [ ] Verify all constants are referenced correctly

### Phase 3: Input System
- [ ] Add PLAYER_* input commands
- [ ] Add DEBUG_CAMERA context
- [ ] Update key bindings (WASD → player movement)
- [ ] Test input command registration

### Phase 4: Camera Rigs
- [ ] Create camera_rig.py with base class
- [ ] Implement FreeFlyRig
- [ ] Implement FirstPersonRig
- [ ] Implement ThirdPersonRig
- [ ] Update CameraController for rig support
- [ ] Test camera rig switching

### Phase 5: Player Character
- [ ] Create gameplay package
- [ ] Implement PlayerCharacter class
- [ ] Test capsule physics body creation
- [ ] Test grounded detection
- [ ] Test jump mechanics
- [ ] Test movement acceleration/deceleration

### Phase 6: Player Controller
- [ ] Create PlayerController
- [ ] Register input handlers
- [ ] Test input → player movement

### Phase 7: Integration
- [ ] Update main.py with player creation
- [ ] Wire camera rigs
- [ ] Add debug camera toggle
- [ ] Test complete gameplay loop

### Phase 8: Testing
- [ ] Create test scene with stairs/ramps
- [ ] Test character movement
- [ ] Test jumping and air control
- [ ] Test slope handling
- [ ] Test step-up behavior
- [ ] Add debug visualization

### Phase 9: Documentation
- [ ] Update CLAUDE.md
- [ ] Create CHARACTER_CONTROLLER.md
- [ ] Update INPUT_SYSTEM.md
- [ ] Add code comments

---

## Testing Scenarios

1. **Basic Movement**: WASD movement on flat ground
2. **Jumping**: Space bar jump with coyote time
3. **Sprinting**: Shift toggle sprint mode
4. **Crouching**: Ctrl toggle crouch (slower movement)
5. **Slopes**: Walk up/down ramps, slide on steep slopes
6. **Stairs**: Auto step-up on stairs within STEP_HEIGHT
7. **Air Control**: Limited movement while airborne
8. **Camera First-Person**: Camera follows player head
9. **Camera Third-Person**: Camera orbits behind player, collision avoidance
10. **Debug Camera**: F2 toggle free-fly mode, ESC for mouse capture

---

## Known Limitations and Future Work

1. **Animation Integration**: TODO comments mark where animations should be triggered
2. **Step-Up Detection**: Not yet implemented (requires convex sweep)
3. **Character Model**: Currently using placeholder cube, needs character mesh
4. **Animation Blending**: Simple state machine, no blend trees yet
5. **Network Synchronization**: Not considered in this design
6. **Save/Load**: Character state not serialized

---

## Summary

This revised plan provides a **complete, actionable roadmap** for implementing high-quality character movement in the ModernGL engine. Key improvements:

- ✅ **Leverages existing systems**: Animation, physics, input all wired correctly
- ✅ **Concrete code examples**: Every phase has complete implementation code
- ✅ **Proper sequencing**: Dependencies are clear, phases build on each other
- ✅ **Testing strategy**: Test scenes and scenarios defined
- ✅ **Debug tools**: Visualization and logging for troubleshooting

The implementation is estimated at **20-30 hours** for a single developer, broken into manageable phases that can be tested incrementally.
