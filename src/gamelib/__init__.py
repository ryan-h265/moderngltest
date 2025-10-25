"""
GameLib - ModernGL 3D Game Engine

A modular 3D game engine with shadow mapping, multi-light support,
and extensible rendering pipeline.
"""

# Configuration
from .config.settings import *

# Core Engine
from .core.camera import Camera
from .core.light import Light, LightDefinition
from .core.scene import Scene, SceneObject, SceneDefinition, SceneNodeDefinition
from .core.scene_manager import SceneManager

# Rendering
from .rendering.render_pipeline import RenderPipeline

# Loaders
from .loaders import SceneLoader, SceneLoadResult

# Input (new Command Pattern system)
from .input.input_manager import InputManager
from .input.input_commands import InputCommand, InputType
from .input.input_context import InputContext, InputContextManager
from .input.key_bindings import KeyBindings
from .input.controllers import CameraController

__version__ = "0.2.0"
__all__ = [
    # Config (exported via *)
    # Core
    "Camera",
    "Light",
    "LightDefinition",
    "Scene",
    "SceneObject",
    "SceneDefinition",
    "SceneNodeDefinition",
    "SceneManager",
    "SceneLoader",
    "SceneLoadResult",
    # Rendering
    "RenderPipeline",
    # Input
    "InputManager",
    "InputCommand",
    "InputType",
    "InputContext",
    "InputContextManager",
    "KeyBindings",
    "CameraController",
]
