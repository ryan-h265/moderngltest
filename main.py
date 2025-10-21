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
from src.gamelib.input.controllers import CameraController, RenderingController


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

        # Enable backface culling for ~50% fragment shader performance improvement
        self.ctx.enable(moderngl.CULL_FACE)
        self.ctx.front_face = 'ccw'  # Counter-clockwise winding order

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

        # Setup rendering controller for SSAO toggle, etc.
        self.rendering_controller = RenderingController(self.render_pipeline, self.input_manager)

        # Create scene
        self.scene = Scene()
        self.scene.create_default_scene()

        # Create lights
        self.lights = self._create_lights()

        # Initialize shadow maps for lights (with camera for adaptive resolution)
        self.render_pipeline.initialize_lights(self.lights, self.camera)

        # Time tracking
        self.time = 0

    def _create_lights(self):
        """
        Create the default multi-light setup.

        With deferred rendering, we can have many lights!
        This creates 10 lights arranged in a circle around the scene.

        Returns:
            List of Light objects
        """
        import math

        lights = []

        # Number of lights to create
        num_lights = 6

        for i in range(num_lights):
            # Arrange lights in a circle
            angle = (i / num_lights) * 2 * math.pi
            radius = 12.0
            height = 8.0 + (i % 3) * 2.0  # Vary height slightly

            # Position on circle
            x = radius * math.cos(angle)
            z = radius * math.sin(angle)

            # Create different colored lights
            # Use HSV to RGB conversion for nice color distribution
            hue = i / num_lights
            if hue < 1/3:
                color = Vector3([1.0 - 3*hue*0.5, 0.5 + 3*hue*0.5, 0.3])
            elif hue < 2/3:
                color = Vector3([0.3, 1.0 - 3*(hue-1/3)*0.5, 0.5 + 3*(hue-1/3)*0.5])
            else:
                color = Vector3([0.5 + 3*(hue-2/3)*0.5, 0.3, 1.0 - 3*(hue-2/3)*0.5])

            # Normalize color
            color = color / max(color)

            # Create light
            light = Light(
                position=Vector3([x, height, z]),
                target=Vector3([0.0, 0.0, 0.0]),
                color=color,
                intensity= 0.3 + (i % 3) * 0.2,  # Vary intensity
                light_type='directional'
            )

            lights.append(light)

        return lights

    def on_update(self, time, frametime):
        """
        Update game logic.

        Args:
            time: Total elapsed time (seconds)
            frametime: Time since last frame (seconds)
        """
        self.time = time

        # Animate lights (create a rotating light show!)
        for i, light in enumerate(self.lights):
            # Rotate every other light at different speeds
            if i % 2 == 0:
                light.animate_rotation(time * (1.0 + i * 0.1))

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
