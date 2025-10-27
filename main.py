#!/usr/bin/env python3
"""
ModernGL 3D Engine - Main Entry Point

A modular 3D game engine with multi-light shadow mapping.
"""

from __future__ import annotations

import logging

import moderngl
import moderngl_window as mglw
from moderngl_window import geometry
from pyrr import Vector3

from src.gamelib import (
    # Configuration
    WINDOW_SIZE, ASPECT_RATIO, GL_VERSION, WINDOW_TITLE, RESIZABLE,
    # Core
    Camera, SceneManager, SceneObject,
    CameraRig, FreeFlyRig, FirstPersonRig, ThirdPersonRig,
    # Rendering
    RenderPipeline,
    # Gameplay
    PlayerCharacter,
    # Input helpers
    InputContext,
    InputCommand,
)
from src.gamelib.core.skybox import Skybox

# New input system
from src.gamelib.input.input_manager import InputManager
from src.gamelib.input.controllers import CameraController, PlayerController, RenderingController

# Physics
from src.gamelib.physics import PhysicsWorld

# Debug overlay
from src.gamelib.debug import DebugOverlay
from src.gamelib.config.settings import DEBUG_OVERLAY_ENABLED


logger = logging.getLogger(__name__)


class Game(mglw.WindowConfig):
    """Main game class"""

    gl_version = GL_VERSION
    title = WINDOW_TITLE
    window_size = WINDOW_SIZE
    aspect_ratio = ASPECT_RATIO
    resizable = RESIZABLE

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Enable core GL states
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.CULL_FACE)
        self.ctx.front_face = "ccw"

        # Primary camera used by all rigs
        self.camera = Camera(
            position=Vector3([0.0, 5.0, 10.0]),
            target=Vector3([0.0, 0.0, 0.0]),
        )

        # Input system
        self.input_manager = InputManager(self.wnd.keys)

        # Capture mouse by default
        self.wnd.mouse_exclusivity = True
        self.wnd.cursor = False
        self.wnd.exit_key = self.wnd.keys.Q

        # Rendering pipeline and controllers
        self.render_pipeline = RenderPipeline(self.ctx, self.wnd)
        self.rendering_controller = RenderingController(self.render_pipeline, self.input_manager)

        # Physics world (optional if PyBullet missing)
        try:
            self.physics_world = PhysicsWorld()
        except RuntimeError as exc:  # pragma: no cover - environment dependent
            logger.warning("Physics world disabled: %s", exc)
            self.physics_world = None

        # Scene management
        self.scene_manager = SceneManager(
            self.ctx,
            self.render_pipeline,
            physics_world=self.physics_world,
        )
        self.scene_manager.register_scene("default", "assets/scenes/default_scene.json")
        self.scene_manager.register_scene("donut_terrain", "assets/scenes/donut_terrain_scene.json")
        self.scene_manager.register_scene("fractal_mountainous", "assets/scenes/fractal_mountainous_scene.json")

        loaded_scene = self.scene_manager.load("fractal_mountainous", camera=self.camera)
        self.scene = loaded_scene.scene
        self.lights = loaded_scene.lights

        # Skybox
        skybox = Skybox.aurora(self.ctx, name="Aurora Skybox")
        skybox.intensity = 1.0
        self.scene.set_skybox(skybox)

        # Player character and controllers
        self.player = self._spawn_player()
        if self.player is not None:
            self.scene.add_object(self.player.model)

        self.camera_rig: CameraRig = self._create_camera_rig()
        self.camera_controller = CameraController(self.camera, self.input_manager, rig=self.camera_rig)
        self.player_controller = PlayerController(self.player, self.input_manager) if self.player else None

        # Toggle for debug camera context
        self.input_manager.register_handler(InputCommand.SYSTEM_TOGGLE_DEBUG_CAMERA, self.toggle_debug_camera)

        # Debug overlay
        self.debug_overlay = DebugOverlay(self.render_pipeline) if DEBUG_OVERLAY_ENABLED else None

        # Time tracking
        self.time = 0.0

    def _spawn_player(self) -> PlayerCharacter | None:
        if self.physics_world is None:
            return None

        placeholder = SceneObject(
            geometry.cube(size=(0.8, 1.8, 0.8)),
            Vector3([0.0, 20.0, 0.0]),
            (0.2, 0.6, 0.9),
            name="Player",
        )

        player = PlayerCharacter(placeholder, self.physics_world)
        player.set_yaw(self.camera.yaw)
        return player

    def _create_camera_rig(self) -> CameraRig:
        if self.player is None:
            return FreeFlyRig(self.camera)
        return FirstPersonRig(self.camera, self.player)

    def toggle_debug_camera(self):
        context_manager = self.input_manager.context_manager
        if context_manager.current_context == InputContext.DEBUG_CAMERA:
            # Return to gameplay
            context_manager.pop_context()
            new_rig = self._create_camera_rig()
            self.camera_rig = new_rig
            if self.player is not None:
                self.camera.position = self.player.get_eye_position()
            self.camera_controller.disable_free_fly(new_rig)
        else:
            # Enter debug free-fly
            context_manager.push_context(InputContext.DEBUG_CAMERA)
            self.camera_controller.enable_free_fly()
            self.camera_rig = self.camera_controller.rig

    def on_update(self, time, frametime):
        """
        Update game logic.

        Args:
            time: Total elapsed time (seconds)
            frametime: Time since last frame (seconds)
        """
        self.time = time

        # Update input system (processes continuous commands + mouse movement)
        self.input_manager.update(frametime)

        if self.player_controller is not None:
            self.player_controller.update()

        if self.player is not None:
            self.player.update(frametime)

        if self.physics_world is not None:
            self.physics_world.step_simulation(frametime)

        if self.player is not None:
            self.player.update_post_physics(frametime)

        if self.camera_rig is not None:
            self.camera_rig.update(frametime)

        # Update animations for all models in the scene
        animated_this_frame = False
        for obj in self.scene.objects:
            # Check if this is a Model with animations
            if hasattr(obj, 'is_model') and obj.is_model:
                animated_this_frame |= obj.update(frametime)

        if animated_this_frame:
            for light in self.lights:
                if light.cast_shadows:
                    light.mark_shadow_dirty()

        # Update debug overlay
        if self.debug_overlay:
            fps = 1.0 / frametime if frametime > 0 else 0
            self.debug_overlay.update(fps, frametime, self.camera, self.lights, self.scene, self.player)

    def on_render(self, time, frametime):
        """
        Render a frame.

        Args:
            time: Total elapsed time (seconds)
            frametime: Time since last frame (seconds)
        """
        # Update logic
        self.on_update(time, frametime)

        # Render frame
        self.render_pipeline.render_frame(self.scene, self.camera, self.lights, time=time)

    def on_mouse_position_event(self, _x: int, _y: int, dx: int, dy: int):
        """
        Handle mouse movement.

        Args:
            _x, _y: Absolute mouse position (unused)
            dx, dy: Mouse delta
        """
        self.input_manager.on_mouse_move(dx, dy)

    def resize(self, width: int, height: int):
        """Handle window resize events by updating render targets."""
        super().resize(width, height)
        self.render_pipeline.resize((width, height))

    def on_key_event(self, key, action, modifiers):
        """
        Handle keyboard events.

        Args:
            key: Key code
            action: Action (press, release, repeat)
            modifiers: Modifier keys (shift, ctrl, etc.)
        """
        keys = self.wnd.keys

        # Handle key press/release
        if action == keys.ACTION_PRESS:
            # print(f"Key pressed: {key}")
            self.input_manager.on_key_press(key)

            # Check if ESC was pressed (for mouse capture toggle)
            # Update window state if mouse capture changed
            if key == keys.ESCAPE:
                captured = self.input_manager.mouse_captured
                self.wnd.mouse_exclusivity = captured
                self.wnd.cursor = not captured

        elif action == keys.ACTION_RELEASE:
            self.input_manager.on_key_release(key)


if __name__ == '__main__':
    Game.run()
