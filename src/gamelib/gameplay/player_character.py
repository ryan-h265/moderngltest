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
    PLAYER_COLLISION_MARGIN,
    PLAYER_COYOTE_TIME,
    PLAYER_CROUCH_SPEED,
    PLAYER_DEBUG_DRAW_CAPSULE,
    PLAYER_DEPENETRATION_ITERATIONS,
    PLAYER_FIRST_PERSON_EYE_HEIGHT,
    PLAYER_GROUND_ACCELERATION,
    PLAYER_GROUND_CHECK_DISTANCE,
    PLAYER_GROUND_DECELERATION,
    PLAYER_GROUND_SNAP_DISTANCE,
    PLAYER_GROUND_SNAP_SPEED_THRESHOLD,
    PLAYER_JUMP_VELOCITY,
    PLAYER_MAX_SLOPE_ANGLE,
    PLAYER_MIN_DEPENETRATION_DISTANCE,
    PLAYER_RUN_SPEED,
    PLAYER_SLOPE_ACCELERATION_MULTIPLIER,
    PLAYER_SPRINT_SPEED,
    PLAYER_STEP_HEIGHT,
    PLAYER_STEP_UP_EXTRA_HEIGHT,
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
        initial_pos = initial_position if initial_position is not None else Vector3([0.0, 5.0, 0.0])
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

        # Slope and collision tracking
        self.ground_normal = Vector3([0.0, 1.0, 0.0])  # World up by default
        self.slope_angle = 0.0  # Current ground slope in degrees

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
            margin=PLAYER_COLLISION_MARGIN,  # Collision margin to prevent edge snagging
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

        # Resolve any collisions/penetrations after movement
        self._resolve_collisions()

        # Apply ground snapping to stick to slopes when moving downhill
        self._apply_ground_snapping()

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
            self.ground_normal = Vector3([0.0, 1.0, 0.0])
            self.slope_angle = 0.0
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
        ground_normal = Vector3([0.0, 1.0, 0.0])  # Default to flat ground
        slope_angle_deg = 0.0

        if hit_info:
            body_id = hit_info.get("body_id", -1)
            # Accept hits from any body except ourselves
            hit_distance = hit_info.get("hit_fraction", 1.0)

            if body_id != self.physics_body.body_id and body_id != -1 and hit_distance <= 1.0:
                # We hit ground, now check the slope angle
                hit_normal = hit_info.get("hit_normal", (0.0, 1.0, 0.0))
                ground_normal = Vector3(hit_normal)

                # Calculate slope angle: angle between surface normal and world up
                world_up = Vector3([0.0, 1.0, 0.0])
                dot_product = max(-1.0, min(1.0, ground_normal.dot(world_up)))  # Clamp for acos safety
                slope_angle_rad = math.acos(dot_product)
                slope_angle_deg = math.degrees(slope_angle_rad)

                # Only consider grounded if slope is walkable
                if slope_angle_deg <= PLAYER_MAX_SLOPE_ANGLE:
                    grounded = True

        # Track grounded state changes
        if grounded and not self.is_grounded:
            # Just landed
            pass
        elif not grounded and self.is_grounded:
            # Just left ground (jumped or fell off)
            pass

        self.is_grounded = grounded
        self.ground_normal = ground_normal
        self.slope_angle = slope_angle_deg

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

        # Apply slope acceleration multiplier when climbing
        if self.is_grounded and self.slope_angle > 5.0:  # Only on noticeable slopes
            target_speed *= PLAYER_SLOPE_ACCELERATION_MULTIPLIER

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
            # In air: apply gravity
            gravity_y = self.physics_world.settings.gravity[1]
            self.velocity = Vector3([horizontal_velocity.x, self.velocity.y + gravity_y * delta_time, horizontal_velocity.z])
        else:
            # On ground: project movement onto slope
            if self.slope_angle > 1.0:  # On a slope
                # Project horizontal velocity onto the slope plane
                # This allows smooth movement up and down slopes

                # Create a 3D velocity by projecting onto slope
                horizontal_3d = Vector3([horizontal_velocity.x, 0.0, horizontal_velocity.z])

                # Project onto slope plane (perpendicular to ground normal)
                # velocity_on_slope = velocity - (velocity · normal) * normal
                velocity_along_normal = horizontal_3d.dot(self.ground_normal)
                velocity_on_slope = horizontal_3d - self.ground_normal * velocity_along_normal

                self.velocity = velocity_on_slope
            else:
                # Flat ground: zero Y velocity
                self.velocity = Vector3([horizontal_velocity.x, 0.0, horizontal_velocity.z])

    def _draw_debug(self) -> None:  # pragma: no cover - visualization only
        debug_info = {
            "pos": tuple(self.get_position()),
            "vel": tuple(self.velocity),
            "grounded": self.is_grounded,
            "slope": f"{self.slope_angle:.1f}°",
        }
        print(f"[PlayerDebug] {debug_info}")

    def _resolve_collisions(self) -> None:
        """
        Resolve penetrations by pushing player out of colliding geometry.
        This implements depenetration and slide-along-wall behavior.
        """
        for _ in range(PLAYER_DEPENETRATION_ITERATIONS):
            # Get all contacts for the player body
            contacts = self.physics_world.get_contacts(body_id=self.physics_body.body_id)

            if not contacts:
                break  # No collisions, we're done

            # Track if any penetration was resolved this iteration
            resolved_any = False

            for contact in contacts:
                penetration_depth = contact["distance"]

                # Negative distance means penetration
                if penetration_depth >= -PLAYER_MIN_DEPENETRATION_DISTANCE:
                    continue  # Not penetrating (or penetration too small to care)

                resolved_any = True

                # Determine which body is us and which is the other
                if contact["body_a"] == self.physics_body.body_id:
                    # We are body_a, contact normal points from b to a
                    contact_normal = Vector3(contact["normal_on_b"])
                else:
                    # We are body_b, need to flip the normal
                    contact_normal = -Vector3(contact["normal_on_b"])

                # Check if this is a step-up situation (hitting a low wall while grounded)
                if self._try_step_up(contact_normal, -penetration_depth):
                    # Successfully stepped up, no need to depenetrate
                    continue

                # Push player out along the contact normal
                # Penetration depth is negative, so we need to move in positive normal direction
                depenetration_vector = contact_normal * (-penetration_depth)
                self._position += depenetration_vector

                # Project velocity to slide along the surface (remove component into surface)
                velocity_into_surface = self.velocity.dot(contact_normal)
                if velocity_into_surface < 0:
                    # Remove the component of velocity pushing into the surface
                    self.velocity -= contact_normal * velocity_into_surface

            if not resolved_any:
                break  # No penetrations resolved, we're done

        # Update physics body position after depenetration
        self.physics_world.set_body_transform(
            self.physics_body.body_id,
            position=tuple(self._position)
        )

    def _try_step_up(self, contact_normal: Vector3, penetration_depth: float) -> bool:
        """
        Try to step up over a small obstacle (stairs, curbs, etc.).

        Args:
            contact_normal: Normal of the surface we're colliding with
            penetration_depth: How far we've penetrated (positive value)

        Returns:
            True if successfully stepped up, False otherwise
        """
        # Only try stepping up if we're grounded or recently grounded
        if not self.is_grounded and self.time_since_grounded > PLAYER_COYOTE_TIME:
            return False

        # Only step up if the contact is mostly horizontal (hitting a wall, not floor/ceiling)
        # Normal should be pointing mostly horizontally (Y component near zero)
        if abs(contact_normal.y) > 0.7:  # More than 45° from horizontal
            return False

        # Only step up if penetration is small (we're just barely hitting the obstacle)
        if penetration_depth > PLAYER_CAPSULE_RADIUS:
            return False

        # Calculate how high we need to step up
        # Start from slightly above our current position
        step_start_height = self._position.y + PLAYER_STEP_UP_EXTRA_HEIGHT
        max_step_height = step_start_height + PLAYER_STEP_HEIGHT

        # Cast a ray upward to check for a ceiling
        ray_start = self._position
        ray_end = Vector3([self._position.x, max_step_height + PLAYER_CAPSULE_RADIUS, self._position.z])
        ceiling_hit = self.physics_world.ray_test(tuple(ray_start), tuple(ray_end))

        if ceiling_hit:
            ceiling_body_id = ceiling_hit.get("body_id", -1)
            if ceiling_body_id != self.physics_body.body_id and ceiling_body_id != -1:
                # There's a ceiling, can't step up
                return False

        # Try stepping up: move position upward and check if we're clear of obstacles
        original_position = Vector3(self._position)

        # Move up by step height
        test_position = Vector3([
            self._position.x,
            self._position.y + PLAYER_STEP_HEIGHT + PLAYER_STEP_UP_EXTRA_HEIGHT,
            self._position.z
        ])

        # Temporarily move to the stepped-up position
        self._position = test_position
        self.physics_world.set_body_transform(
            self.physics_body.body_id,
            position=tuple(test_position)
        )

        # Check if we still have collisions at this height
        contacts_after_step = self.physics_world.get_contacts(body_id=self.physics_body.body_id)

        # Filter for horizontal penetrations
        has_horizontal_collision = False
        for contact in contacts_after_step:
            if contact["distance"] < -PLAYER_MIN_DEPENETRATION_DISTANCE:
                # Check if it's a horizontal collision
                if contact["body_a"] == self.physics_body.body_id:
                    normal = Vector3(contact["normal_on_b"])
                else:
                    normal = -Vector3(contact["normal_on_b"])

                if abs(normal.y) < 0.7:  # Horizontal collision
                    has_horizontal_collision = True
                    break

        if has_horizontal_collision:
            # Still colliding horizontally after stepping up, revert
            self._position = original_position
            self.physics_world.set_body_transform(
                self.physics_body.body_id,
                position=tuple(original_position)
            )
            return False

        # Success! Now find the ground at this new height
        # Cast a ray downward to find where to land
        ray_start = Vector3([test_position.x, test_position.y, test_position.z])
        ray_end = Vector3([test_position.x, original_position.y - PLAYER_GROUND_CHECK_DISTANCE, test_position.z])
        ground_hit = self.physics_world.ray_test(tuple(ray_start), tuple(ray_end))

        if ground_hit:
            ground_body_id = ground_hit.get("body_id", -1)
            if ground_body_id != self.physics_body.body_id and ground_body_id != -1:
                # Found ground, land on it
                hit_position = Vector3(ground_hit.get("hit_position", (test_position.x, test_position.y, test_position.z)))
                # Position capsule bottom at hit point
                landed_position = Vector3([
                    hit_position.x,
                    hit_position.y + PLAYER_CAPSULE_HEIGHT / 2.0 + PLAYER_CAPSULE_RADIUS,
                    hit_position.z
                ])
                self._position = landed_position
                self.physics_world.set_body_transform(
                    self.physics_body.body_id,
                    position=tuple(landed_position)
                )
                return True

        # Keep the stepped-up position even if we didn't find ground immediately
        # (we'll fall naturally next frame)
        return True

    def _apply_ground_snapping(self) -> None:
        """
        Snap player down to ground when moving downhill.
        Prevents "bouncing" when running down slopes or over small bumps.
        """
        # Only snap when:
        # 1. We were grounded last frame (or recently)
        # 2. We're not moving upward too fast (not jumping)
        # 3. We have some horizontal movement

        if not self.is_grounded and self.time_since_grounded > PLAYER_COYOTE_TIME:
            return  # Not grounded, don't snap

        # Don't snap if we're intentionally moving upward (jumping)
        if self.velocity.y > PLAYER_GROUND_SNAP_SPEED_THRESHOLD:
            return

        # Don't snap if we're not moving horizontally (standing still)
        horizontal_speed = Vector3([self.velocity.x, 0.0, self.velocity.z]).length
        if horizontal_speed < 0.1:
            return  # Not moving, no need to snap

        # Cast a ray downward from current position
        ray_start = self._position
        ray_end = self._position + Vector3([0.0, -PLAYER_GROUND_SNAP_DISTANCE, 0.0])

        ground_hit = self.physics_world.ray_test(tuple(ray_start), tuple(ray_end))

        if not ground_hit:
            return  # No ground below us

        ground_body_id = ground_hit.get("body_id", -1)
        if ground_body_id == self.physics_body.body_id or ground_body_id == -1:
            return  # Hit ourselves or nothing

        # Check if the ground is walkable (not too steep)
        hit_normal = Vector3(ground_hit.get("hit_normal", (0.0, 1.0, 0.0)))
        world_up = Vector3([0.0, 1.0, 0.0])
        dot_product = max(-1.0, min(1.0, hit_normal.dot(world_up)))
        slope_angle_rad = math.acos(dot_product)
        slope_angle_deg = math.degrees(slope_angle_rad)

        if slope_angle_deg > PLAYER_MAX_SLOPE_ANGLE:
            return  # Too steep, don't snap

        # Snap down to the ground
        hit_position = Vector3(ground_hit.get("hit_position", self._position))

        # Calculate the distance we need to move down
        snap_distance = self._position.y - hit_position.y

        # Only snap if we're actually above the ground (not already on it)
        if snap_distance > PLAYER_GROUND_CHECK_DISTANCE:
            # Position capsule bottom at hit point
            snapped_position = Vector3([
                hit_position.x,
                hit_position.y + PLAYER_CAPSULE_HEIGHT / 2.0 + PLAYER_CAPSULE_RADIUS,
                hit_position.z
            ])

            self._position = snapped_position
            self.physics_world.set_body_transform(
                self.physics_body.body_id,
                position=tuple(snapped_position)
            )

            # Zero out downward velocity when snapping
            if self.velocity.y < 0:
                self.velocity = Vector3([self.velocity.x, 0.0, self.velocity.z])

    # Convenience hooks used by camera rigs
    def get_eye_position(self) -> Vector3:
        return self.get_position() + Vector3([0.0, PLAYER_FIRST_PERSON_EYE_HEIGHT, 0.0])
