#!/usr/bin/env python3
"""
Quick test to verify shadow rendering is working
"""

import moderngl
import moderngl_window as mglw
from pyrr import Vector3
from src.gamelib import Camera, Light, Scene, RenderPipeline

class ShadowTest(mglw.WindowConfig):
    gl_version = (4, 1)
    window_size = (800, 600)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.ctx.enable(moderngl.DEPTH_TEST)

        # Simple scene
        self.scene = Scene()
        self.scene.create_default_scene()

        # Simple camera
        self.camera = Camera(
            position=Vector3([0.0, 5.0, 10.0]),
            target=Vector3([0.0, 0.0, 0.0])
        )

        # Create just ONE light for testing
        self.lights = [
            Light(
                position=Vector3([5.0, 10.0, 5.0]),
                target=Vector3([0.0, 0.0, 0.0]),
                color=Vector3([1.0, 1.0, 1.0]),
                intensity=1.0,
                light_type='directional'
            )
        ]

        # Create pipeline
        self.render_pipeline = RenderPipeline(self.ctx, self.wnd)
        self.render_pipeline.initialize_lights(self.lights)

        # Debug: Check if shadow map was created
        print(f"Light has shadow_map: {self.lights[0].shadow_map is not None}")
        print(f"Light has shadow_fbo: {self.lights[0].shadow_fbo is not None}")
        if self.lights[0].shadow_map:
            print(f"Shadow map size: {self.lights[0].shadow_map.size}")

    def on_render(self, time, frametime):
        self.camera.update_vectors()
        self.render_pipeline.render_frame(self.scene, self.camera, self.lights)

if __name__ == '__main__':
    ShadowTest.run()
