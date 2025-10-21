#!/usr/bin/env python3
"""
ModernGL 3D Engine - Main Entry Point

A modular 3D game engine with multi-light shadow mapping.
"""

import moderngl
import moderngl_window as mglw
from pyrr import Vector3

from src.gamelib import (
    # Configuration
    WINDOW_SIZE, ASPECT_RATIO, GL_VERSION, WINDOW_TITLE, RESIZABLE,
    # Core
    Camera, Light, Scene,
    # Rendering
    RenderPipeline,
)

# New input system
from src.gamelib.input.input_manager import InputManager
from src.gamelib.input.controllers import CameraController


class Game(mglw.WindowConfig):
    """Main game class"""

    gl_version = GL_VERSION
    title = WINDOW_TITLE
    window_size = WINDOW_SIZE
    aspect_ratio = ASPECT_RATIO
    resizable = RESIZABLE

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Enable depth testing
        self.ctx.enable(moderngl.DEPTH_TEST)

        # Setup camera
        self.camera = Camera(
            position=Vector3([0.0, 5.0, 10.0]),
            target=Vector3([0.0, 0.0, 0.0])
        )

        # Setup input system (new Command Pattern architecture)
        self.input_manager = InputManager(self.wnd.keys)
        self.camera_controller = CameraController(self.camera, self.input_manager)

        # Capture mouse
        self.wnd.mouse_exclusivity = True
        self.wnd.cursor = False

        # Setup rendering pipeline
        self.render_pipeline = RenderPipeline(self.ctx, self.wnd)

        # Create scene
        self.scene = Scene()
        self.scene.create_default_scene()

        # Create lights
        self.lights = self._create_lights()

        # Initialize shadow maps for lights
        self.render_pipeline.initialize_lights(self.lights)

        # Time tracking
        self.time = 0

    def _create_lights(self):
        """
        Create the default multi-light setup.

        Returns:
            List of Light objects
        """
        # Light 1: Rotating sun (white directional light)
        light1 = Light(
            position=Vector3([5.0, 10.0, 5.0]),
            target=Vector3([0.0, 0.0, 0.0]),
            color=Vector3([1.0, 1.0, 1.0]),
            intensity=1.0,
            light_type='directional'
        )

        # Light 2: Static side light (warm orange-red)
        light2 = Light(
            position=Vector3([8.0, 6.0, 8.0]),
            target=Vector3([0.0, 0.0, 0.0]),
            color=Vector3([1.0, 0.7, 0.5]),
            intensity=0.8,
            light_type='directional'
        )

        return [light1, light2]

    def on_update(self, time, frametime):
        """
        Update game logic.

        Args:
            time: Total elapsed time (seconds)
            frametime: Time since last frame (seconds)
        """
        self.time = time

        # Animate first light (rotating sun)
        self.lights[0].animate_rotation(time)
        # Light 2 stays static

        # Update input system (processes continuous commands + mouse movement)
        self.input_manager.update(frametime)

        # Update camera target after position changes
        self.camera.update_vectors()

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
        self.render_pipeline.render_frame(self.scene, self.camera, self.lights)

    def on_mouse_position_event(self, _x: int, _y: int, dx: int, dy: int):
        """
        Handle mouse movement.

        Args:
            _x, _y: Absolute mouse position (unused)
            dx, dy: Mouse delta
        """
        self.input_manager.on_mouse_move(dx, dy)

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
