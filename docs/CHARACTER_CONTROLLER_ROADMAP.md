# Character Controller Roadmap

This document tracks future enhancements for the player character controller to reach full AAA game standard.

## Current Status (v1.0 - January 2025)

### ✅ Implemented Features
- ✅ Kinematic body with collision response
- ✅ Depenetration logic (detect-and-resolve)
- ✅ Slope angle detection and filtering
- ✅ Slide-along-wall behavior
- ✅ Velocity projection onto slopes
- ✅ Configurable max slope angle (45°)
- ✅ Collision margin tuning (prevents edge snagging)
- ✅ Air control factor (reduced control while airborne)
- ✅ Coyote time (grace period for jumping after leaving ledge)
- ✅ Step-up height (climb stairs and small obstacles)
- ✅ Ground snapping (stick to ground on slopes/bumps)

### ⚠️ Known Limitations
- No true sweep tests (PyBullet Python API doesn't expose `convexSweepTest`)
- Depenetration is post-facto (detect after moving, then push out)
- Requires multiple iterations per frame (~0.1ms cost)

---

## Future Enhancements

### 🟡 Priority: High

#### 1. Crouch Collision Adjustment
**Status:** Crouch keybind exists but capsule height doesn't change

**Implementation Plan:**
```python
# In PlayerCharacter._create_physics_body()
# Store original capsule height
self._standing_height = PLAYER_CAPSULE_HEIGHT
self._crouching_height = PLAYER_CAPSULE_HEIGHT * 0.5

# In PlayerCharacter.set_crouch()
def set_crouch(self, active: bool) -> None:
    if active == self.is_crouching:
        return

    if active:
        # Try to crouch
        self._set_capsule_height(self._crouching_height)
        self.is_crouching = True
    else:
        # Try to stand - check for ceiling first
        if self._can_stand_up():
            self._set_capsule_height(self._standing_height)
            self.is_crouching = False

def _can_stand_up(self) -> bool:
    """Cast ray upward to check for ceiling."""
    ray_start = self._position
    ray_end = ray_start + Vector3([0.0, self._standing_height, 0.0])
    hit = self.physics_world.ray_test(tuple(ray_start), tuple(ray_end))
    return hit is None  # No ceiling obstruction

def _set_capsule_height(self, new_height: float) -> None:
    """Recreate capsule with new height."""
    # Remove old body
    self.physics_world.remove_body(self.physics_body.body_id)
    # Create new body with new height
    # ... (implementation details)
```

**Settings to add:**
```python
PLAYER_CROUCH_HEIGHT_MULTIPLIER = 0.5  # Crouch to 50% of standing height
PLAYER_CROUCH_TRANSITION_SPEED = 8.0   # Smooth interpolation
```

**Impact:** Makes crouch mechanically meaningful (can fit under obstacles)

**Effort:** Medium (2-3 hours)

---

#### 2. Moving Platform Support
**Status:** Not implemented

**Implementation Plan:**
```python
# In PlayerCharacter
self.standing_on_body_id = None  # Track what we're standing on
self.platform_velocity = Vector3([0.0, 0.0, 0.0])

# In _update_ground_state()
if grounded and hit_info:
    self.standing_on_body_id = hit_info.get("body_id")
    # Get platform velocity
    platform_vel = self.physics_world.get_linear_velocity(self.standing_on_body_id)
    if platform_vel:
        self.platform_velocity = Vector3(platform_vel)
else:
    self.standing_on_body_id = None
    self.platform_velocity = Vector3([0.0, 0.0, 0.0])

# In update()
# Apply platform velocity before movement
self._position += self.platform_velocity * delta_time
```

**Handles:**
- Linear platform movement (elevators, trains)
- Rotating platforms (with angular velocity)
- Moving and rotating platforms combined

**Settings to add:**
```python
PLAYER_PLATFORM_INERTIA = 0.2  # How much platform momentum carries when leaving
```

**Impact:** Essential for platformer mechanics

**Effort:** Medium (3-4 hours)

---

### 🟢 Priority: Medium

#### 3. Improved Slope Sliding Physics
**Status:** Slopes > 45° are rejected but player doesn't slide down

**Implementation Plan:**
```python
# In _update_velocity()
if not self.is_grounded and self.slope_angle > PLAYER_MAX_SLOPE_ANGLE:
    # Too steep - apply slide force
    slide_direction = self._calculate_slide_direction(self.ground_normal)
    slide_force = PLAYER_SLOPE_SLIDE_FORCE * (self.slope_angle / 90.0)
    self.velocity += slide_direction * slide_force * delta_time

def _calculate_slide_direction(self, surface_normal: Vector3) -> Vector3:
    """Calculate downward slide direction on steep slope."""
    world_up = Vector3([0.0, 1.0, 0.0])
    # Project down onto slope plane
    slide_dir = world_up - surface_normal * world_up.dot(surface_normal)
    if slide_dir.length > 1e-3:
        return -slide_dir.normalized  # Negative = downward
    return Vector3([0.0, -1.0, 0.0])
```

**Settings to add:**
```python
PLAYER_SLOPE_SLIDE_FORCE = 15.0  # Force applied when sliding down steep slopes
PLAYER_SLOPE_FRICTION_CURVE = {  # Friction reduction by angle
    0: 1.0,    # Full friction on flat ground
    30: 0.8,   # 80% friction at 30°
    45: 0.5,   # 50% friction at 45°
    60: 0.1,   # Almost no friction at 60°
}
```

**Impact:** More realistic slope behavior (ski down mountains!)

**Effort:** Low (1-2 hours)

---

#### 4. Contact Point Filtering
**Status:** All contacts processed equally

**Implementation Plan:**
```python
# In _resolve_collisions()
def _filter_contacts(self, contacts: List[Dict]) -> List[Dict]:
    """Filter and prioritize contacts for depenetration."""
    filtered = []

    for contact in contacts:
        penetration_depth = -contact["distance"]

        # Ignore shallow penetrations
        if penetration_depth < PLAYER_MIN_DEPENETRATION_DISTANCE:
            continue

        # Ignore contacts too far away (likely phantom contacts)
        if penetration_depth > PLAYER_MAX_DEPENETRATION_DISTANCE:
            continue

        filtered.append(contact)

    # Sort by penetration depth (deepest first)
    filtered.sort(key=lambda c: -c["distance"])

    # Limit to N most important contacts
    return filtered[:PLAYER_MAX_CONTACTS_PER_FRAME]
```

**Settings to add:**
```python
PLAYER_MAX_DEPENETRATION_DISTANCE = 0.5  # Ignore contacts > 0.5m away
PLAYER_MAX_CONTACTS_PER_FRAME = 4        # Process at most 4 contacts
```

**Impact:** Minor performance improvement, more stable depenetration

**Effort:** Low (1 hour)

---

### 🔵 Priority: Low (Polish)

#### 5. Velocity Smoothing on Collision
**Status:** Instant velocity change can feel jarring

**Implementation Plan:**
```python
# In _resolve_collisions()
# Instead of instant velocity removal:
# self.velocity -= contact_normal * velocity_into_surface

# Smooth velocity removal over time:
velocity_removal_factor = min(1.0, delta_time * PLAYER_COLLISION_VELOCITY_DAMPING)
self.velocity -= contact_normal * velocity_into_surface * velocity_removal_factor
```

**Settings to add:**
```python
PLAYER_COLLISION_VELOCITY_DAMPING = 10.0  # How quickly to remove velocity into surfaces
```

**Impact:** Smoother "feel" when bumping into walls

**Effort:** Very Low (30 minutes)

---

#### 6. Jump Buffer
**Status:** Jump only works if pressed exactly when grounded

**Implementation Plan:**
```python
# In PlayerCharacter
self.jump_buffer_time = 0.0

# In request_jump()
def request_jump(self) -> None:
    self.jump_requested = True
    self.jump_buffer_time = PLAYER_JUMP_BUFFER_TIME

# In update()
self.jump_buffer_time = max(0.0, self.jump_buffer_time - delta_time)

# In _process_jump()
if self.jump_buffer_time > 0.0 and self.can_jump:
    # Buffered jump!
    self.velocity.y = PLAYER_JUMP_VELOCITY
    self.can_jump = False
    self.jump_buffer_time = 0.0
```

**Settings to add:**
```python
PLAYER_JUMP_BUFFER_TIME = 0.15  # Remember jump input for 150ms
```

**Impact:** More forgiving jump input (feels responsive)

**Effort:** Very Low (30 minutes)

---

### ⚫ Priority: Not Feasible (API Limitation)

#### 7. True Sweep Tests (Predictive Collision)
**Status:** PyBullet Python doesn't expose `convexSweepTest`

**Alternative Solutions:**
1. **Use C++ PyBullet directly** - Compile custom Python extension
2. **Migrate to different physics engine:**
   - **PhysX** via `pyphysx` - Has Python bindings, sweep tests available
   - **Jolt Physics** - No official Python bindings (C++ only)
   - **Custom solution** - Implement sweep using multiple sphere casts

**Current Workaround:** Multi-iteration depenetration works well enough

**Impact:** Minor quality improvement, major implementation effort

**Effort:** Very High (weeks)

---

## Testing Checklist

When implementing new features, test:
- [ ] Walking on flat ground
- [ ] Walking up 10°, 20°, 30°, 40° slopes
- [ ] Sliding down 50°+ slopes
- [ ] Climbing stairs (step-up)
- [ ] Walking down stairs (ground snap)
- [ ] Running over small bumps (ground snap)
- [ ] Jumping and landing
- [ ] Jumping off ledges (coyote time)
- [ ] Walking into walls (slide-along)
- [ ] Walking into corners (multi-contact depenetration)
- [ ] Crouching and standing (if implemented)
- [ ] Crouching under obstacles (if implemented)
- [ ] Standing on moving platforms (if implemented)

---

## Physics Engine Migration Considerations

If PyBullet limitations become blocking:

### PhysX (via pyphysx)
**Pros:**
- Industry-standard (Unreal Engine uses PhysX)
- Python bindings available (`pyphysx`)
- True character controller with sweep tests
- Better performance on complex scenes

**Cons:**
- NVIDIA proprietary (though free)
- Migration effort (2-3 weeks)
- Less documentation for Python API

### Custom Solution
**Pros:**
- Full control
- Optimized for your specific needs

**Cons:**
- Massive implementation effort (months)
- Hard to beat established engines

### Stick with PyBullet
**Pros:**
- Current implementation works well
- No migration cost
- PyBullet is well-documented

**Cons:**
- Missing sweep tests
- Python API limitations

**Recommendation:** Stick with PyBullet for now. It's sufficient for most games.

---

## Version History

### v1.0 (January 2025)
- Initial kinematic character controller
- Collision detection and depenetration
- Slope handling
- Step-up height detection
- Ground snapping

### Planned v1.1
- Crouch collision adjustment
- Moving platform support

### Planned v2.0
- Physics engine migration evaluation
- Advanced features (predictive collision, etc.)
