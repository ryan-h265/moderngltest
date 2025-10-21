#!/usr/bin/env python3
"""
Simple Scene Example

Minimal scene with just 3 cubes and 1 light.
Useful for testing or as a starting point for custom scenes.
"""

import sys
sys.path.insert(0, '..')

import moderngl
import moderngl_window as mglw
from pyrr import Vector3
from moderngl_window import geometry

from src.gamelib import (
    WINDOW_SIZE, ASPECT_RATIO, GL_VERSION,
    Camera, Light, Scene, SceneObject,
    RenderPipeline
)

from src.gamelib.input import InputManager, CameraController


class SimpleSceneDemo(mglw.WindowConfig):
    """Simple 3-cube scene"""

    gl_version = GL_VERSION
    title = "Simple Scene Example"
    window_size = WINDOW_SIZE
    aspect_ratio = ASPECT_RATIO

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctx.enable(moderngl.DEPTH_TEST)

        # Camera
        self.camera = Camera(Vector3([0.0, 3.0, 8.0]))

        # Input system (new Command Pattern architecture)
        self.input_manager = InputManager()
        self.camera_controller = CameraController(self.camera, self.input_manager)

        # Mouse capture
        self.wnd.mouse_exclusivity = True
        self.wnd.cursor = False

        # Rendering
        self.render_pipeline = RenderPipeline(self.ctx, self.wnd)

        # Create simple scene
        self.scene = Scene()
        self._create_simple_scene()

        # Single light
        self.lights = [
            Light(
                position=Vector3([5.0, 8.0, 5.0]),
                target=Vector3([0.0, 0.0, 0.0]),
                color=Vector3([1.0, 1.0, 1.0]),
                intensity=1.0
            )
        ]
        self.render_pipeline.initialize_lights(self.lights)

    def _create_simple_scene(self):
        """Create a simple 3-cube scene"""
        # Ground
        self.scene.add_object(SceneObject(
            geometry.cube(size=(10.0, 0.2, 10.0)),
            Vector3([0.0, -0.1, 0.0]),
            (0.4, 0.4, 0.4)  # Gray
        ))

        # Red cube
        self.scene.add_object(SceneObject(
            geometry.cube(size=(1.5, 1.5, 1.5)),
            Vector3([-2.0, 0.75, 0.0]),
            (0.8, 0.2, 0.2)
        ))

        # Blue cube
        self.scene.add_object(SceneObject(
            geometry.cube(size=(1.0, 2.0, 1.0)),
            Vector3([2.0, 1.0, -1.0]),
            (0.2, 0.2, 0.8)
        ))

        # Green cube
        self.scene.add_object(SceneObject(
            geometry.cube(size=(1.2, 1.2, 1.2)),
            Vector3([0.0, 0.6, 2.5]),
            (0.2, 0.8, 0.2)
        ))

    def on_update(self, time, frametime):
        self.lights[0].animate_rotation(time, radius=8.0, height=6.0)
        self.input_manager.update(frametime)

    def on_render(self, time, frametime):
        self.on_update(time, frametime)
        self.render_pipeline.render_frame(self.scene, self.camera, self.lights)

    def on_mouse_position_event(self, _x, _y, dx, dy):
        self.input_manager.on_mouse_move(dx, dy)

    def on_key_event(self, key, action, modifiers):
        keys = self.wnd.keys

        if action == keys.ACTION_PRESS:
            self.input_manager.on_key_press(key)

            # Check if ESC was pressed (for mouse capture toggle)
            if key == keys.ESCAPE:
                captured = self.input_manager.mouse_captured
                self.wnd.mouse_exclusivity = captured
                self.wnd.cursor = not captured

        elif action == keys.ACTION_RELEASE:
            self.input_manager.on_key_release(key)


if __name__ == '__main__':
    print("Running simple scene example...")
    print("Just 3 cubes and 1 rotating light")
    print()
    SimpleSceneDemo.run()
