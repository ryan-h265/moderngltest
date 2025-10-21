#!/usr/bin/env python3
"""
Stress test: 50+ lights with deferred rendering
Demonstrates scalability with shadow map caching and light sorting
"""

import moderngl
import moderngl_window as mglw
from pyrr import Vector3
import math

from src.gamelib import Camera, Light, Scene, RenderPipeline
from src.gamelib.input import InputManager, CameraController


class ManyLightsTest(mglw.WindowConfig):
    """Test scene with many lights"""

    gl_version = (4, 1)
    title = "50 Lights Stress Test"
    window_size = (1280, 720)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.ctx.enable(moderngl.DEPTH_TEST)

        # Camera
        self.camera = Camera(
            position=Vector3([0.0, 8.0, 15.0]),
            target=Vector3([0.0, 0.0, 0.0])
        )

        # Input
        self.input_manager = InputManager(self.wnd.keys)
        self.camera_controller = CameraController(self.camera, self.input_manager)
        self.wnd.mouse_exclusivity = True
        self.wnd.cursor = False

        # Scene
        self.scene = Scene()
        self.scene.create_default_scene()

        # Create MANY lights!
        self.lights = self._create_many_lights()

        # Rendering
        self.render_pipeline = RenderPipeline(self.ctx, self.wnd)
        self.render_pipeline.initialize_lights(self.lights)

        print(f"\n{'='*60}")
        print(f"Stress Test: {len(self.lights)} lights")
        print(f"{'='*60}")
        print(f"Shadow-casting lights: {sum(1 for l in self.lights if l.cast_shadows)}")
        print(f"Non-shadow lights: {sum(1 for l in self.lights if not l.cast_shadows)}")
        print(f"{'='*60}\n")

        self.time = 0

    def _create_many_lights(self):
        """Create 50 lights: mix of shadow-casting and non-shadow"""
        lights = []
        num_lights = 50

        for i in range(num_lights):
            # Arrange in multiple rings
            ring = i // 10  # Ring number (0-4)
            ring_index = i % 10  # Position in ring
            angle = (ring_index / 10) * 2 * math.pi
            radius = 8.0 + ring * 4.0
            height = 6.0 + ring * 2.0

            x = radius * math.cos(angle)
            z = radius * math.sin(angle)

            # Rainbow colors
            hue = i / num_lights
            r = abs(math.sin(hue * math.pi * 2))
            g = abs(math.sin((hue + 0.33) * math.pi * 2))
            b = abs(math.sin((hue + 0.66) * math.pi * 2))

            # First 15 lights cast shadows, rest are cheap fill lights
            cast_shadows = (i < 15)

            light = Light(
                position=Vector3([x, height, z]),
                target=Vector3([0.0, 0.0, 0.0]),
                color=Vector3([r, g, b]),
                intensity=0.5 if cast_shadows else 0.3,
                light_type='directional',
                cast_shadows=cast_shadows
            )

            lights.append(light)

        return lights

    def on_update(self, time, frametime):
        """Update"""
        self.time = time

        # Animate only shadow-casting lights (first 15)
        for i, light in enumerate(self.lights[:15]):
            if i % 3 == 0:  # Every 3rd light rotates
                light.animate_rotation(time * (0.5 + i * 0.05))

        self.input_manager.update(frametime)
        self.camera.update_vectors()

    def on_render(self, time, frametime):
        """Render"""
        self.on_update(time, frametime)
        self.render_pipeline.render_frame(self.scene, self.camera, self.lights)

    def on_mouse_position_event(self, _x, _y, dx, dy):
        """Mouse movement"""
        self.input_manager.on_mouse_move(dx, dy)

    def on_key_event(self, key, action, modifiers):
        """Keyboard"""
        keys = self.wnd.keys
        if action == keys.ACTION_PRESS:
            self.input_manager.on_key_press(key)
            if key == keys.ESCAPE:
                self.wnd.mouse_exclusivity = self.input_manager.mouse_captured
                self.wnd.cursor = not self.input_manager.mouse_captured
        elif action == keys.ACTION_RELEASE:
            self.input_manager.on_key_release(key)


if __name__ == '__main__':
    ManyLightsTest.run()
