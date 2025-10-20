"""
GameLib - ModernGL 3D Game Engine

A modular 3D game engine with shadow mapping, multi-light support,
and extensible rendering pipeline.
"""

# Configuration
from .config.settings import *

# Core Engine
from .core.camera import Camera
from .core.light import Light
from .core.scene import Scene, SceneObject

# Rendering
from .rendering.render_pipeline import RenderPipeline

# Input
from .input.input_handler import InputHandler

__version__ = "0.2.0"
__all__ = [
    # Config (exported via *)
    # Core
    "Camera",
    "Light",
    "Scene",
    "SceneObject",
    # Rendering
    "RenderPipeline",
    # Input
    "InputHandler",
]
