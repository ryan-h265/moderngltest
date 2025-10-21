"""
Game Configuration Settings

All configuration constants for the game engine.
Modify these values to change engine behavior.
"""

from pathlib import Path

# ============================================================================
# Project Paths
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
SHADERS_DIR = ASSETS_DIR / "shaders"

# ============================================================================
# Window Configuration
# ============================================================================

WINDOW_SIZE = (1920, 1080)
ASPECT_RATIO = 16 / 9
WINDOW_TITLE = "ModernGL 3D Engine"
RESIZABLE = True

# OpenGL version (4.1 is max for macOS)
GL_VERSION = (4, 1)

# ============================================================================
# Rendering Settings
# ============================================================================

# Rendering mode
RENDERING_MODE = "deferred"  # "forward" or "deferred"

# Shadow mapping
SHADOW_MAP_SIZE = 2048  # Resolution of shadow maps (2048x2048)
MAX_LIGHTS = 3          # Number of shadow-casting lights (only for forward rendering)
SHADOW_BIAS = 0.005     # Bias to prevent shadow acne

# Deferred rendering optimizations
MAX_LIGHTS_PER_FRAME = None  # Limit lights rendered per frame (None = unlimited)
ENABLE_LIGHT_SORTING = True  # Sort lights by importance (brightness/distance)

# PCF (Percentage Closer Filtering) for soft shadows
PCF_SAMPLES = 3         # 3x3 grid = 9 samples (use 5 for 25 samples, 1 for no PCF)

# Background clear color (R, G, B)
CLEAR_COLOR = (0.1, 0.1, 0.15)  # Dark blue

# V-Sync
ENABLE_VSYNC = True

# ============================================================================
# Camera Settings
# ============================================================================

# Movement
DEFAULT_CAMERA_SPEED = 5.0     # Units per second
CAMERA_ACCELERATION = 1.5      # Not currently used

# Mouse look
MOUSE_SENSITIVITY = 0.1        # Degrees per pixel
INVERT_MOUSE_Y = False        # Set True to invert Y-axis

# Field of view
DEFAULT_FOV = 45.0             # Degrees
MIN_FOV = 20.0
MAX_FOV = 90.0

# Clipping planes
NEAR_PLANE = 0.1
FAR_PLANE = 100.0

# Pitch limits (prevents camera flipping)
MIN_PITCH = -89.0
MAX_PITCH = 89.0

# ============================================================================
# Lighting Defaults
# ============================================================================

# Ambient lighting
AMBIENT_STRENGTH = 0.1         # 0.0 = pitch black, 1.0 = fully lit

# Directional light projection bounds
LIGHT_ORTHO_LEFT = -15.0
LIGHT_ORTHO_RIGHT = 15.0
LIGHT_ORTHO_BOTTOM = -15.0
LIGHT_ORTHO_TOP = 15.0
LIGHT_ORTHO_NEAR = 0.1
LIGHT_ORTHO_FAR = 50.0

# Default light properties
DEFAULT_LIGHT_INTENSITY = 1.0
DEFAULT_LIGHT_COLOR = (1.0, 1.0, 1.0)  # White

# ============================================================================
# Input Settings
# ============================================================================

# ============================================================================
# Debug Settings
# ============================================================================

DEBUG_MODE = False
SHOW_FPS = True
LOG_LEVEL = "INFO"  # "DEBUG", "INFO", "WARNING", "ERROR"

# Frustum culling debug
DEBUG_FRUSTUM_CULLING = False  # Print culling statistics (very spammy - only enable for debugging)
DEBUG_SHOW_CULLED_OBJECTS = False  # Print names of culled objects (requires DEBUG_FRUSTUM_CULLING)

# ============================================================================
# Performance Settings
# ============================================================================

# Frustum culling (skip rendering objects outside camera view)
ENABLE_FRUSTUM_CULLING = True  # Highly recommended for performance

# Target frame rate (0 = unlimited)
# TARGET_FPS = 60

# Enable/disable features for performance
# ENABLE_SHADOWS = True
# ENABLE_SPECULAR = True
# ENABLE_PCF = True

# ============================================================================
# Future Settings (for SSAO, CSM)
# ============================================================================

# SSAO (Screen Space Ambient Occlusion)
SSAO_ENABLED = True
SSAO_KERNEL_SIZE = 64
SSAO_RADIUS = 0.5
SSAO_BIAS = 0.025
SSAO_INTENSITY = 1.5

# CSM (Cascaded Shadow Maps)
CSM_ENABLED = False
CSM_NUM_CASCADES = 3
CSM_LAMBDA = 0.5  # Blend between uniform and logarithmic splits
