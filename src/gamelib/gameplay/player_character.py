"""Physics-driven player character controller."""

from __future__ import annotations

import math
from typing import Optional

from pyrr import Quaternion, Vector3

from ..config.settings import (
    PLAYER_AIR_ACCELERATION,
    PLAYER_AIR_CONTROL_FACTOR,
    PLAYER_AIR_DECELERATION,
    PLAYER_CAPSULE_ANGULAR_DAMPING,
    PLAYER_CAPSULE_FRICTION,
    PLAYER_CAPSULE_HEIGHT,
    PLAYER_CAPSULE_LINEAR_DAMPING,
    PLAYER_CAPSULE_MASS,
    PLAYER_CAPSULE_RADIUS,
    PLAYER_COYOTE_TIME,
    PLAYER_CROUCH_SPEED,
    PLAYER_DEBUG_DRAW_CAPSULE,
    PLAYER_FIRST_PERSON_EYE_HEIGHT,
    PLAYER_GROUND_ACCELERATION,
    PLAYER_GROUND_CHECK_DISTANCE,
    PLAYER_GROUND_DECELERATION,
    PLAYER_JUMP_VELOCITY,
    PLAYER_MAX_SLOPE_ANGLE,
    PLAYER_RUN_SPEED,
    PLAYER_SPRINT_SPEED,
    PLAYER_WALK_SPEED,
)
from ..physics import PhysicsBodyConfig, PhysicsBodyHandle, PhysicsWorld


class PlayerCharacter:
    """High-level gameplay representation of the player."""

    def __init__(
        self,
        model,
        physics_world: PhysicsWorld,
        initial_position: Optional[Vector3] = None,
    ) -> None:
        self.model = model
        self.physics_world = physics_world
        if initial_position is not None:
            self.model.position = initial_position

        self.physics_body = self._create_physics_body()

        self.movement_intent = Vector3([0.0, 0.0, 0.0])
        # Start with a tiny downward velocity to ensure we fall to ground on spawn
        # If spawned in the air, this will trigger the falling sequence immediately
        self.velocity = Vector3([0.0, -0.5, 0.0])
        self.yaw = 0.0
        
        # For kinematic bodies, we manually track position since PyBullet doesn't auto-update it
        # Initialize to the spawn position
        initial_pos = initial_position if initial_position is not None else Vector3([0.0, 2.0, 0.0])
        self._position = Vector3(initial_pos)

        self.is_grounded = False
        self.time_since_grounded = 0.0
        self.jump_requested = False
        self.can_jump = True

        # Skip grounding check on first frame to allow initial velocity to establish contact
        self._is_first_frame = True

        self.is_sprinting = False
        self.is_crouching = False
        self.is_walking = False

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _create_physics_body(self) -> PhysicsBodyHandle:
        config = PhysicsBodyConfig(
            shape="capsule",
            body_type="kinematic",  # Kinematic body - we control movement, PyBullet handles collisions
            radius=PLAYER_CAPSULE_RADIUS,
            height=PLAYER_CAPSULE_HEIGHT,
            mass=PLAYER_CAPSULE_MASS,
            friction=PLAYER_CAPSULE_FRICTION,
            linear_damping=PLAYER_CAPSULE_LINEAR_DAMPING,
            angular_damping=PLAYER_CAPSULE_ANGULAR_DAMPING,
            user_data={"name": "player"},
        )

        if hasattr(self.model, "position"):
            config.position = tuple(float(v) for v in getattr(self.model, "position"))

        handle = self.physics_world.create_body(self.model, config)
        self.physics_world.set_angular_factor(handle.body_id, (0.0, 1.0, 0.0))
        return handle

    # ------------------------------------------------------------------
    # Input hooks
    # ------------------------------------------------------------------
    def set_movement_intent(self, forward: float, right: float) -> None:
        forward = max(-1.0, min(1.0, forward))
        right = max(-1.0, min(1.0, right))
        if abs(forward) < 1e-3 and abs(right) < 1e-3:
            self.movement_intent = Vector3([0.0, 0.0, 0.0])
            return

        yaw_rad = math.radians(self.yaw)
        forward_axis = Vector3([math.cos(yaw_rad), 0.0, math.sin(yaw_rad)])
        right_axis = Vector3([-math.sin(yaw_rad), 0.0, math.cos(yaw_rad)])
        desired = forward_axis * forward + right_axis * right
        length = desired.length
        if length > 1e-3:
            self.movement_intent = desired / length
        else:
            self.movement_intent = Vector3([0.0, 0.0, 0.0])

    def request_jump(self) -> None:
        self.jump_requested = True

    def set_sprint(self, active: bool) -> None:
        self.is_sprinting = active

    def set_crouch(self, active: bool) -> None:
        self.is_crouching = active

    def toggle_walk(self) -> None:
        self.is_walking = not self.is_walking

    def set_yaw(self, yaw: float) -> None:
        self.yaw = yaw
        rotation = Quaternion.from_y_rotation(math.radians(self.yaw))
        if hasattr(self.model, "rotation"):
            self.model.rotation = rotation
        self.physics_world.set_body_transform(self.physics_body.body_id, orientation=tuple(rotation))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def get_position(self) -> Vector3:
        # For kinematic bodies, we track position internally
        return Vector3(self._position)

    # ------------------------------------------------------------------
    # Update loop
    # ------------------------------------------------------------------
    def update(self, delta_time: float) -> None:
        self._update_ground_state(delta_time)
        self._process_jump()
        self._update_velocity(delta_time)
        
        # For kinematic bodies, we must manually move the position based on velocity
        new_pos = self._position + self.velocity * delta_time
        self._position = new_pos
        self.physics_world.set_body_transform(
            self.physics_body.body_id,
            position=tuple(new_pos)
        )
        
        # Set velocity for collision detection purposes
        self.physics_world.set_linear_velocity(self.physics_body.body_id, tuple(self.velocity))
        
        if PLAYER_DEBUG_DRAW_CAPSULE:
            self._draw_debug()
        self.jump_requested = False

    def update_post_physics(self, delta_time: float) -> None:
        # For kinematic bodies, we manually handle movement in update()
        # So we don't need to sync from PyBullet - our position is already updated
        # Just ensure the model position stays in sync with our player position
        
        if hasattr(self.model, "position"):
            self.model.position = self.get_position()
        
        # Reinforce upright orientation so we do not accumulate roll/pitch error when
        # angular axes are locked (especially on PyBullet builds lacking native support).
        rotation = Quaternion.from_y_rotation(math.radians(self.yaw))
        self.physics_world.set_body_transform(
            self.physics_body.body_id,
            orientation=tuple(rotation),
        )
        if hasattr(self.model, "rotation"):
            self.model.rotation = rotation

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _update_ground_state(self, delta_time: float) -> None:
        # Skip grounding check on first frame to allow initial downward velocity to establish contact
        if self._is_first_frame:
            self._is_first_frame = False
            # Force is_grounded = False so _update_velocity will apply gravity
            self.is_grounded = False
            return
        
        # Use raycast for ground detection (more reliable than contact points for kinematic bodies)
        # Cast a ray downward from the capsule center to check for ground below
        capsule_center = self._position
        
        # Ray starts from capsule center and goes downward
        ray_start = capsule_center + Vector3([0.0, -0.1, 0.0])  # Slight offset into capsule for robustness
        # Check down to a reasonable distance below
        ray_end = ray_start + Vector3([0.0, -(PLAYER_CAPSULE_HEIGHT/2.0 + PLAYER_CAPSULE_RADIUS + PLAYER_GROUND_CHECK_DISTANCE), 0.0])
        
        # Perform raycast
        hit_info = self.physics_world.ray_test(tuple(ray_start), tuple(ray_end))
        
        grounded = False
        if hit_info:
            body_id = hit_info.get("body_id", -1)
            # Accept hits from any body except ourselves
            # Check if the hit is close to the capsule (within the expected distance)
            hit_distance = hit_info.get("hit_fraction", 1.0)
            expected_distance = (PLAYER_CAPSULE_HEIGHT/2.0 + PLAYER_CAPSULE_RADIUS + PLAYER_GROUND_CHECK_DISTANCE)
            
            if body_id != self.physics_body.body_id and body_id != -1 and hit_distance <= 1.0:
                grounded = True
        
        # Track grounded state changes
        if grounded and not self.is_grounded:
            # Just landed
            pass
        elif not grounded and self.is_grounded:
            # Just left ground (jumped or fell off)
            pass
        
        self.is_grounded = grounded
        if grounded:
            self.time_since_grounded = 0.0
            self.can_jump = True
        else:
            self.time_since_grounded += delta_time
            if self.time_since_grounded > PLAYER_COYOTE_TIME:
                self.can_jump = False

    def _process_jump(self) -> None:
        if not self.jump_requested:
            return
        if not self.can_jump:
            return
        self.velocity.y = PLAYER_JUMP_VELOCITY
        self.can_jump = False
        self.is_grounded = False

    def _update_velocity(self, delta_time: float) -> None:
        horizontal_velocity = Vector3([self.velocity.x, 0.0, self.velocity.z])

        if self.is_crouching:
            target_speed = PLAYER_CROUCH_SPEED
        elif self.is_sprinting and not self.is_walking:
            target_speed = PLAYER_SPRINT_SPEED
        elif self.is_walking:
            target_speed = PLAYER_WALK_SPEED
        else:
            target_speed = PLAYER_RUN_SPEED

        target_velocity = self.movement_intent * target_speed

        if not self.is_grounded:
            target_velocity *= PLAYER_AIR_CONTROL_FACTOR
            acceleration = PLAYER_AIR_ACCELERATION
            deceleration = PLAYER_AIR_DECELERATION
        else:
            acceleration = PLAYER_GROUND_ACCELERATION
            deceleration = PLAYER_GROUND_DECELERATION

        difference = target_velocity - horizontal_velocity
        diff_len = difference.length
        if diff_len > 1e-3:
            accel_amount = acceleration * delta_time
            if diff_len <= accel_amount:
                horizontal_velocity = target_velocity
            else:
                horizontal_velocity += difference.normalized * accel_amount
        else:
            if horizontal_velocity.length > 1e-3:
                decel_amount = deceleration * delta_time
                if horizontal_velocity.length <= decel_amount:
                    horizontal_velocity = Vector3([0.0, 0.0, 0.0])
                else:
                    horizontal_velocity -= horizontal_velocity.normalized * decel_amount

        if not self.is_grounded:
            gravity_y = self.physics_world.settings.gravity[1]
            self.velocity = Vector3([horizontal_velocity.x, self.velocity.y + gravity_y * delta_time, horizontal_velocity.z])
        else:
            self.velocity = Vector3([horizontal_velocity.x, 0.0, horizontal_velocity.z])

    def _draw_debug(self) -> None:  # pragma: no cover - visualization only
        debug_info = {
            "pos": tuple(self.get_position()),
            "vel": tuple(self.velocity),
            "grounded": self.is_grounded,
        }
        print(f"[PlayerDebug] {debug_info}")

    # Convenience hooks used by camera rigs
    def get_eye_position(self) -> Vector3:
        return self.get_position() + Vector3([0.0, PLAYER_FIRST_PERSON_EYE_HEIGHT, 0.0])
