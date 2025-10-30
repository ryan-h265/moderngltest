"""
Game Configuration Settings

All configuration constants for the game engine.
Modify these values to change engine behavior.
"""

import json
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

WINDOW_SIZE = (1920, 1080)  # Width, Height
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
SHADOW_MAP_SIZE = 2048  # Resolution of shadow maps (2048x2048) - default/high quality
MAX_LIGHTS = 3          # Number of shadow-casting lights (only for forward rendering)
SHADOW_BIAS = 0.005     # Bias to prevent shadow acne

# Shadow map optimizations
SHADOW_MAP_MIN_INTENSITY = 0.01  # Skip shadow rendering for lights dimmer than this
ENABLE_ADAPTIVE_SHADOW_RES = True  # Use lower resolution for distant/dim lights
SHADOW_MAP_SIZE_LOW = 512   # Resolution for low-importance lights (distant/dim)
SHADOW_MAP_SIZE_MED = 1024  # Resolution for medium-importance lights
SHADOW_MAP_SIZE_HIGH = 2048  # Resolution for high-importance lights (close/bright)
SHADOW_UPDATE_THROTTLE_FRAMES = 0  # Update static light shadows every N frames (0=every frame)
DEBUG_SHADOW_RENDERING = False  # Print shadow map rendering statistics

# Debug visualization for light placements
DEBUG_DRAW_LIGHT_GIZMOS = False  # Render helper gizmos showing light positions and directions
DEBUG_LIGHT_GIZMO_SPHERE_RADIUS = 0.5  # Radius of the debug sphere drawn at each light position
DEBUG_LIGHT_GIZMO_LINE_LENGTH = 5.5  # Length of the direction line extending from each light
DEBUG_LIGHT_GIZMO_ALPHA = 0.75  # Opacity for light gizmo rendering (0-1)

# Deferred rendering optimizations
MAX_LIGHTS_PER_FRAME = None  # Limit lights rendered per frame (None = unlimited)
ENABLE_LIGHT_SORTING = True  # Sort lights by importance (brightness/distance)

# PCF (Percentage Closer Filtering) for soft shadows
PCF_SAMPLES = 3         # 3x3 grid = 9 samples (use 5 for 25 samples, 1 for no PCF)

# Bloom (emissive glow) settings
BLOOM_ENABLED = True
BLOOM_THRESHOLD = 0.7        # Brightness threshold for bloom extraction (in HDR units)
BLOOM_SOFT_KNEE = 0.25       # Soft thresholding transition [0-1]
BLOOM_INTENSITY = 0.65       # Intensity multiplier when compositing bloom
BLOOM_FILTER_RADIUS = 1.1    # Upsample filter radius (higher = softer bloom)
BLOOM_MAX_LEVELS = 5         # Number of downsample/upsample levels (more = softer, slower)
BLOOM_TINT = (1.0, 1.0, 1.0) # Optional bloom tint (RGB)

# Fog (atmospheric scattering) settings
FOG_ENABLED = True
FOG_COLOR = (0.65, 0.70, 0.88)       # Fog color tint (RGB) - Subtle blue-gray haze
FOG_DENSITY = 0.0085                  # Base exponential density (reduced for more transparency)
FOG_START_DISTANCE = 34.0            # Distance from camera where fog begins
FOG_END_DISTANCE = 125.0              # Distance where fog reaches full strength
FOG_BASE_HEIGHT = 0.0                # World-space height where fog is densest
FOG_HEIGHT_FALLOFF = 0.05            # Exponential falloff per unit height above base
FOG_NOISE_SCALE = 0.18                # World-space scale of noise (lower = larger, less tiled features)
FOG_NOISE_STRENGTH = 0.75            # Strength of noise modulation (higher for more variation)
FOG_NOISE_SPEED = 0.8                 # Animation speed multiplier (slower for more natural drift)
FOG_WIND_DIRECTION = (0.3, 0.0, 0.2) # Direction the fog drifts over time
FOG_DETAIL_SCALE = 0.85               # Scale for high-frequency wispy details
FOG_DETAIL_STRENGTH = 0.35           # Strength of fine detail layer
FOG_WARP_STRENGTH = 0.4              # Domain warping intensity for organic flow

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
FAR_PLANE = 1000.0  # Increased for large terrain (donut extends to ~220 units)

# Pitch limits (prevents camera flipping)
MIN_PITCH = -89.0
MAX_PITCH = 89.0

# ============================================================================
# Character Movement Defaults
# ============================================================================

PLAYER_WALK_SPEED = 15.0
PLAYER_RUN_SPEED = 35.0
PLAYER_SPRINT_SPEED = 50.0
PLAYER_CROUCH_SPEED = 10.0

PLAYER_AIR_CONTROL_FACTOR = 0.35

PLAYER_JUMP_VELOCITY = 5.0
PLAYER_COYOTE_TIME = 0.1

PLAYER_GROUND_ACCELERATION = 40.0
PLAYER_AIR_ACCELERATION = 10.0
PLAYER_GROUND_DECELERATION = 55.0
PLAYER_AIR_DECELERATION = 5.0

PLAYER_CAPSULE_RADIUS = 0.4
PLAYER_CAPSULE_HEIGHT = 1.8
PLAYER_CAPSULE_MASS = 75.0
PLAYER_CAPSULE_FRICTION = 0.8
PLAYER_CAPSULE_LINEAR_DAMPING = 0.1
PLAYER_CAPSULE_ANGULAR_DAMPING = 0.0

PLAYER_MAX_SLOPE_ANGLE = 45.0
PLAYER_GROUND_CHECK_DISTANCE = 0.15
PLAYER_STEP_HEIGHT = 0.4  # Maximum height player can step up (stairs, curbs, etc.)

# Collision response settings
PLAYER_DEPENETRATION_ITERATIONS = 5  # Number of iterations to resolve penetration
PLAYER_SLOPE_ACCELERATION_MULTIPLIER = 1.2  # Extra force when climbing slopes
PLAYER_COLLISION_MARGIN = 0.04  # Collision margin to prevent edge snagging (default 0.04, try 0.06-0.08 if snagging occurs)
PLAYER_MIN_DEPENETRATION_DISTANCE = 0.001  # Minimum penetration depth to resolve (meters)
PLAYER_CCD_ENABLED = True  # Enable Continuous Collision Detection to prevent tunneling at high speeds
PLAYER_CCD_SWEEP_STEPS = 5  # Number of steps to subdivide movement for swept collision detection

# Step-up and ground snapping settings
PLAYER_STEP_UP_EXTRA_HEIGHT = 0.05  # Extra height to lift when stepping (prevents edge catching)
PLAYER_GROUND_SNAP_DISTANCE = 0.3  # Maximum distance to snap down to ground when moving downhill
PLAYER_GROUND_SNAP_SPEED_THRESHOLD = 0.5  # Don't snap if moving upward faster than this (m/s)

PLAYER_FIRST_PERSON_EYE_HEIGHT = 1.6
PLAYER_THIRD_PERSON_DISTANCE = 5.0
PLAYER_THIRD_PERSON_HEIGHT = 2.0
PLAYER_THIRD_PERSON_SPRING_STIFFNESS = 0.18
PLAYER_THIRD_PERSON_MIN_DISTANCE = 1.0
PLAYER_THIRD_PERSON_MAX_DISTANCE = 10.0

PLAYER_DEBUG_DRAW_CAPSULE = False

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
SSAO_ENABLED = False
SSAO_KERNEL_SIZE = 64
SSAO_RADIUS = 0.5
SSAO_BIAS = 0.025
SSAO_INTENSITY = 1.5

# CSM (Cascaded Shadow Maps)
CSM_ENABLED = False
CSM_NUM_CASCADES = 3
CSM_LAMBDA = 0.5  # Blend between uniform and logarithmic splits

# ============================================================================
# UI / Text Rendering Settings
# ============================================================================

# Font configuration
# UI_FONT_PATH = "assets/fonts/PixelOperatorMono.ttf"
UI_FONT_PATH = "assets/fonts/TX-02-Regular.otf"
UI_FONT_SIZE = 24  # Font size in pixels
UI_ATLAS_SIZE = 512  # Texture atlas resolution (512x512)

# Debug overlay
DEBUG_OVERLAY_ENABLED = False
DEBUG_TEXT_COLOR = (0.3, 1.0, 0.3, 0.8)  # RGBA (green - original)
DEBUG_TEXT_SCALE = 1.0  # Normal scale
DEBUG_POSITION = (10, 10)  # Top-left
DEBUG_LINE_SPACING = 35  # Pixels between lines
DEBUG_OVERLAY_BACKGROUND_COLOR = (0.1, 0.1, 0.1, 0.6)  # Semi-transparent gray
DEBUG_OVERLAY_BACKGROUND_PADDING = 6.0  # Pixels of padding around text

# Player HUD configuration
HUD_ENABLED = True
HUD_ANCHOR = "bottom_left"
HUD_MARGIN = (32, 32)  # Pixels from anchored corner
HUD_TEXT_SCALE = 0.95
HUD_TEXT_COLOR = (0.94, 0.97, 1.0, 1.0)
HUD_LABEL_COLOR = (0.65, 0.85, 1.0, 0.95)
HUD_VALUE_COLOR = (1.0, 1.0, 1.0, 1.0)
HUD_WARNING_COLOR = (1.0, 0.73, 0.27, 1.0)
HUD_CRITICAL_COLOR = (1.0, 0.33, 0.33, 1.0)
HUD_HEALTH_THRESHOLDS = {
    "warning": 0.6,
    "critical": 0.35,
}
HUD_ICON_SIZE = (48, 48)
HUD_ICON_TINT = (1.0, 1.0, 1.0, 1.0)
HUD_ICON_TEXT_GAP = 12.0
HUD_LINE_SPACING = 8.0
HUD_SECTION_SPACING = 16.0
HUD_BACKGROUND_COLOR = (0.02, 0.02, 0.02, 0.55)
HUD_BACKGROUND_PADDING = 6.0
HUD_HINT_SLOTS = 3
HUD_HINT_LINE_SPACING = 4.0
HUD_VALUE_GAP = 6.0
HUD_HINT_COLOR = (0.85, 0.85, 0.85, 1.0)
HUD_LAYER_TEXT = "hud_text"
HUD_LAYER_ICONS = "hud_icons"
HUD_SECTIONS = {
    "compass": {
        "label": "Compass",
        "icon": "assets/ui/icons/compass.png",
    },
    "health": {
        "label": "Health",
        "icon": "assets/ui/icons/health.png",
    },
    "minimap": {
        "label": "Minimap",
        "icon": "assets/ui/icons/minimap.png",
    },
    "tool": {
        "label": "Tool",
        "icon": "assets/ui/icons/tool.png",
    },
    "hints": {
        "label": "Hints",
        "icon": "assets/ui/icons/hints.png",
    },
}
HUD_SECTION_ORDER = (
    "hints",  # Rendered closest to anchor when anchored bottom
    "tool",
    "minimap",
    "health",
    "compass",  # Furthest from anchor
)

# ============================================================================
# UI Settings (ImGui)
# ============================================================================

# ImGui theme to use
UI_THEME = "sage_green"  # Options: "sage_green", "dark", "light", "cyberpunk"

# UI scaling (auto-scales with resolution)
UI_SCALE_FACTOR = 1.0

# Menu background dimming when paused
UI_PAUSE_DIM_ALPHA = 0.6  # Opacity of dim overlay (0.0-1.0)

# ============================================================================
# Attribute Mode Settings (Editor)
# ============================================================================

# Thumbnail menu configuration
THUMBNAIL_SIZE = 192  # Size of asset thumbnails in pixels
THUMBNAIL_VISIBLE_COUNT = 6  # Number of thumbnails visible at once
BOTTOM_MENU_HEIGHT = 300  # Height of bottom menu bar in pixels
TOOL_ICON_SIZE = 56  # Size of tool icons in top row

# Object selection and highlight
SELECTION_HIGHLIGHT_COLOR = (1.0, 0.8, 0.0, 1.0)  # Orange RGBA
SELECTION_OUTLINE_SCALE = 0.01  # Outline thickness (0.005-0.02 recommended)
OBJECT_RAYCAST_RANGE = 1000.0  # Maximum distance for raycasting

# ============================================================================
# Light Presets (Editor) - Loaded from JSON Config
# ============================================================================

def _load_light_presets() -> dict:
    """
    Load light presets from JSON configuration file.

    Returns:
        Dictionary mapping preset names to preset data
    """
    config_path = PROJECT_ROOT / "assets" / "config" / "lights" / "light_presets.json"

    if not config_path.exists():
        print(f"Warning: Light presets config not found at {config_path}")
        return {}

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        presets = {}
        for preset in config.get("presets", []):
            name = preset.get("name", preset.get("id", "Unknown"))
            presets[name] = {
                "color": tuple(preset.get("color", [1.0, 1.0, 1.0])),
                "intensity": preset.get("intensity", 1.0),
                "cast_shadows": preset.get("cast_shadows", True),
                "icon_color": tuple(preset.get("icon_color", [1.0, 1.0, 1.0])),
            }

        return presets
    except Exception as e:
        print(f"Error loading light presets: {e}")
        return {}

# Load light presets from JSON configuration
LIGHT_PRESETS = _load_light_presets()
