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

# ============================================================================
# Anti-Aliasing Settings
# ============================================================================
#
# The engine supports three AA techniques, each with different trade-offs:
#
# 1. MSAA (Multi-Sample Anti-Aliasing)
#    - Hardware-based, excellent geometric edge quality
#    - Higher GPU memory and fill-rate cost
#    - Best for: Clean geometry edges, works with deferred rendering
#
# 2. FXAA (Fast Approximate Anti-Aliasing)
#    - Post-process, very fast, minimal memory
#    - Can blur textures/text slightly
#    - Best for: Maximum performance, shader aliasing
#
# 3. SMAA (Enhanced Subpixel Morphological Anti-Aliasing)
#    - Post-process, better quality than FXAA
#    - Uses official SMAA 1.0 lookup textures for pattern matching
#    - Best for: High quality post-AA, minimal blur
#
# Combined modes (e.g., MSAA 4x + SMAA) provide the best overall quality
# by using MSAA for geometry and SMAA for post-processing.
#
# Runtime Controls:
#   F7: Cycle through AA modes
#   F8: Toggle MSAA on/off
#   F9: Toggle SMAA on/off
# ============================================================================

# Default AA Mode
# Options: "OFF", "FXAA", "SMAA", "MSAA_2X", "MSAA_4X", "MSAA_8X",
#          "MSAA_2X_FXAA", "MSAA_4X_FXAA", "MSAA_2X_SMAA", "MSAA_4X_SMAA"
DEFAULT_AA_MODE = "OFF"

# ----------------------------------------------------------------------------
# MSAA (Multi-Sample Anti-Aliasing) Settings
# ----------------------------------------------------------------------------
# Hardware-accelerated antialiasing using multiple samples per pixel
# Higher quality but more GPU memory and fill-rate intensive

DEFAULT_MSAA_SAMPLES = 4       # Default sample count (2, 4, or 8)
MAX_MSAA_SAMPLES = 8           # Maximum supported samples (GPU dependent)

# MSAA Quality vs Performance:
# 2x: ~15% cost, good edge quality
# 4x: ~25% cost, excellent edge quality (recommended)
# 8x: ~40% cost, outstanding quality (high-end GPUs only)

# ----------------------------------------------------------------------------
# FXAA (Fast Approximate Anti-Aliasing) Settings
# ----------------------------------------------------------------------------
# Post-process AA using edge detection and blur
# Very fast, works on all geometry, minimal memory cost

FXAA_EDGE_THRESHOLD = 0.063    # Edge detection sensitivity (0.063 = default, lower = more blur)
FXAA_EDGE_THRESHOLD_MIN = 0.0312  # Minimum threshold for very dark areas
FXAA_SUBPIX_QUALITY = 0.75     # Sub-pixel aliasing removal (0.0-1.0, higher = more blur)

# FXAA Presets:
# PERFORMANCE: edge_threshold=0.125, subpix=0.50 (faster, less blur)
# BALANCED:    edge_threshold=0.063, subpix=0.75 (default, good quality)
# QUALITY:     edge_threshold=0.031, subpix=1.00 (slower, more blur)

# ----------------------------------------------------------------------------
# SMAA (Enhanced Subpixel Morphological Anti-Aliasing) Settings
# ----------------------------------------------------------------------------
# Advanced post-process AA using pattern detection and lookup tables
# Better quality than FXAA, uses official SMAA 1.0 precomputed textures

SMAA_PRESET = "HIGH"  # Options: "LOW", "MEDIUM", "HIGH", "ULTRA"

# SMAA Quality Settings (auto-set based on preset, can be overridden)
SMAA_THRESHOLD = 0.1           # Edge detection threshold (lower = more edges detected)
SMAA_MAX_SEARCH_STEPS = 16     # Maximum steps when searching for edge patterns
SMAA_MAX_SEARCH_STEPS_DIAG = 8 # Maximum steps for diagonal edges
SMAA_CORNER_ROUNDING = 25      # Corner rounding percentage (0-100)

# SMAA Presets define these values:
# LOW:    threshold=0.15, search_steps=4,  diag_steps=0,  corner_rounding=0   (~2% cost)
# MEDIUM: threshold=0.1,  search_steps=8,  diag_steps=0,  corner_rounding=25  (~3% cost)
# HIGH:   threshold=0.1,  search_steps=16, diag_steps=8,  corner_rounding=25  (~4% cost)
# ULTRA:  threshold=0.05, search_steps=32, diag_steps=16, corner_rounding=100 (~6% cost)

# ----------------------------------------------------------------------------
# Combined AA Modes
# ----------------------------------------------------------------------------
# MSAA + FXAA: MSAA handles geometry edges, FXAA smooths shader aliasing
# MSAA + SMAA: MSAA handles geometry edges, SMAA provides superior post-processing
# Recommended: MSAA 4x + SMAA (best quality, ~29% total cost)

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
AMBIENT_STRENGTH = 0.2         # 0.0 = pitch black, 1.0 = fully lit

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

# Key bindings (using moderngl_window key constants)
# These are checked in InputHandler
KEY_FORWARD = 'W'
KEY_BACKWARD = 'S'
KEY_LEFT = 'A'
KEY_RIGHT = 'D'
KEY_UP = 'E'
KEY_DOWN = 'Q'
KEY_TOGGLE_MOUSE = 'ESCAPE'

# ============================================================================
# Debug Settings
# ============================================================================

DEBUG_MODE = False
SHOW_FPS = True
LOG_LEVEL = "INFO"  # "DEBUG", "INFO", "WARNING", "ERROR"

# ============================================================================
# Performance Settings
# ============================================================================

# Target frame rate (0 = unlimited)
TARGET_FPS = 60

# Enable/disable features for performance
ENABLE_SHADOWS = True
ENABLE_SPECULAR = True
ENABLE_PCF = True

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
