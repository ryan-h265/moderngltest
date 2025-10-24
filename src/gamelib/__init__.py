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
from .ui.player_hud import PlayerHUD

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
    "Scene",
    "SceneObject",
    # Rendering
    "RenderPipeline",
    "PlayerHUD",
    # Input
    "InputManager",
    "InputCommand",
    "InputType",
    "InputContext",
    "InputContextManager",
    "KeyBindings",
    "CameraController",
]
