"""
Model Placement Tool

Tool for placing models from a library into the scene.
Includes model browser, placement preview, and grid snapping.
"""

from typing import Optional, List, Dict, TYPE_CHECKING
from pathlib import Path
from pyrr import Vector3, Quaternion
import math
from ..tool_base import EditorTool
from ..placement_preview import PlacementPreview
from ..editor_history import PlaceObjectOperation

if TYPE_CHECKING:
    from ...core.camera import Camera
    from ...core.scene import Scene
    from ...loaders.model import Model
    from ..tool_definition import ToolDefinition


class ModelPlacementTool(EditorTool):
    """
    Tool for placing models from a library.

    Features:
    - Browse available models (B key to open browser)
    - Preview placement with green/red validation
    - Left click: Place model
    - Right click + drag: Rotate preview
    - R key: Rotate preview 45° (discrete)
    - Grid snapping (G key to toggle)
    - Surface snapping (always on)

    Model Library:
    - Loads models from configured directory
    - Supports GLTF/GLB formats
    - Hot-swappable model selection
    """

    def __init__(self, definition: "ToolDefinition", ctx=None):
        """
        Initialize model placement tool.

        Args:
            definition: Tool definition from JSON
            ctx: ModernGL context
        """
        super().__init__(definition)
        self.ctx = ctx
        self.editor_history = None  # Set by game/editor

        # Preview system
        self.preview = PlacementPreview(ctx) if ctx else None
        self.preview_position: Vector3 = Vector3([0.0, 0.0, 0.0])
        self.preview_rotation: float = 0.0  # Y-axis rotation in radians

        # Model library
        self.model_library: Dict[str, str] = {}  # name -> path
        self.available_models: List[str] = []  # List of model names
        self.current_model_index: int = 0
        self.selected_model_path: Optional[str] = None
        self.selected_model_name: str = "None"

        # Load model library
        self._load_model_library()

        # Placement validation
        self.is_valid_placement: bool = True

    def _load_model_library(self):
        """Load available models from configured directory."""
        library_path = self.get_property("model_library_path", "assets/models/props/")

        from ...config.settings import PROJECT_ROOT
        library_dir = PROJECT_ROOT / library_path

        if not library_dir.exists():
            print(f"Warning: Model library directory not found: {library_dir}")
            return

        # Find all GLTF/GLB files
        for model_dir in library_dir.iterdir():
            if model_dir.is_dir():
                # Look for scene.gltf or scene.glb
                gltf_path = model_dir / "scene.gltf"
                glb_path = model_dir / "scene.glb"

                if gltf_path.exists():
                    self.model_library[model_dir.name] = str(gltf_path)
                    self.available_models.append(model_dir.name)
                elif glb_path.exists():
                    self.model_library[model_dir.name] = str(glb_path)
                    self.available_models.append(model_dir.name)

        print(f"Model library loaded: {len(self.available_models)} models available")
        for name in self.available_models:
            print(f"  - {name}")

        # Select first model by default
        if self.available_models:
            self.select_model_by_index(0)

    def select_model_by_index(self, index: int):
        """
        Select a model from the library by index.

        Args:
            index: Index in available_models list
        """
        if 0 <= index < len(self.available_models):
            self.current_model_index = index
            self.selected_model_name = self.available_models[index]
            self.selected_model_path = self.model_library[self.selected_model_name]
            print(f"Selected model: {self.selected_model_name}")

            # Load preview model
            self._load_preview_model()

    def select_next_model(self):
        """Select next model in library (cycle)."""
        if not self.available_models:
            return
        next_index = (self.current_model_index + 1) % len(self.available_models)
        self.select_model_by_index(next_index)

    def select_previous_model(self):
        """Select previous model in library (cycle)."""
        if not self.available_models:
            return
        prev_index = (self.current_model_index - 1) % len(self.available_models)
        self.select_model_by_index(prev_index)

    def _load_preview_model(self):
        """Load the selected model for preview."""
        if not self.selected_model_path or not self.preview:
            return

        try:
            from ...loaders import GltfLoader
            loader = GltfLoader(self.ctx)
            model = loader.load(self.selected_model_path)
            self.preview.set_model(model)
            print(f"Loaded preview model: {self.selected_model_name}")
        except Exception as e:
            print(f"Error loading preview model: {e}")

    def use(self, camera: "Camera", scene: "Scene", **kwargs) -> bool:
        """
        Place model at current preview position.

        Args:
            camera: Active camera
            scene: Current scene
            **kwargs: Additional context

        Returns:
            True if model was placed
        """
        if not self.can_use():
            return False

        if not self.selected_model_path:
            print("No model selected")
            return False

        if not self.is_valid_placement:
            print("Invalid placement")
            return False

        # Load and place model
        try:
            from ...loaders import GltfLoader
            loader = GltfLoader(self.ctx)
            model = loader.load(self.selected_model_path)

            # Set transform
            model.position = Vector3(self.preview_position)
            model.rotation = Vector3([0.0, self.preview_rotation, 0.0])
            model.scale = self.get_property("default_scale", Vector3([1.0, 1.0, 1.0]))
            model.name = self.selected_model_name

            # Add to scene
            scene.add_object(model)

            # Record in history
            if self.editor_history:
                operation = PlaceObjectOperation(model)
                self.editor_history.execute(operation, scene)

            print(f"Placed: {self.selected_model_name} at {self.preview_position}")
            self._start_use()
            return True

        except Exception as e:
            print(f"Error placing model: {e}")
            return False

    def use_secondary(self, camera: "Camera", scene: "Scene", **kwargs) -> bool:
        """
        Rotate preview (continuous drag).

        Args:
            camera: Active camera
            scene: Current scene
            **kwargs: Additional context (mouse_delta_x)

        Returns:
            True if action was performed
        """
        mouse_delta_x = kwargs.get('mouse_delta_x', 0.0)

        if abs(mouse_delta_x) > 0.01:
            # Rotate preview based on mouse movement
            rotation_speed = self.get_property("rotation_speed", 0.01)
            self.preview_rotation += mouse_delta_x * rotation_speed

            # Normalize angle to [0, 2π)
            self.preview_rotation = self.preview_rotation % (2 * math.pi)

            return True

        return False

    def update(self, delta_time: float, camera: "Camera", scene: "Scene"):
        """
        Update preview position and validation.

        Args:
            delta_time: Time since last update
            camera: Active camera
            scene: Current scene
        """
        super().update(delta_time, camera, scene)

        # Update preview position via raycast
        hit = self.raycast_scene(camera, scene)
        if hit:
            obj, hit_pos, hit_normal = hit

            # Snap to grid if enabled
            snapped_pos = self.snap_to_grid(hit_pos)
            self.preview_position = snapped_pos

            # Validate placement (simple check for now)
            self.is_valid_placement = self._validate_placement(scene)

            # Update preview
            if self.preview:
                rotation_vec = Vector3([0.0, self.preview_rotation, 0.0])
                self.preview.update_transform(
                    self.preview_position,
                    rotation_vec,
                    self.is_valid_placement
                )
        else:
            # No surface under cursor
            if self.preview:
                self.preview.hide()
            self.is_valid_placement = False

    def _validate_placement(self, scene: "Scene") -> bool:
        """
        Check if current placement is valid.

        Args:
            scene: Current scene

        Returns:
            True if placement is valid
        """
        # TODO: Implement proper collision checking
        # For now, just check if we're on a valid surface (Y >= 0)
        if self.preview_position.y < -1.0:
            return False

        # Could add checks for:
        # - Collision with existing objects
        # - Out of bounds
        # - Overlapping objects
        # - Minimum distance from other objects

        return True

    def rotate_preview(self, angle_degrees: float):
        """
        Rotate preview by fixed angle (discrete rotation).

        Args:
            angle_degrees: Angle to rotate in degrees
        """
        self.preview_rotation += math.radians(angle_degrees)
        self.preview_rotation = self.preview_rotation % (2 * math.pi)
        print(f"Rotated preview by {angle_degrees}°")

    def on_equipped(self):
        """Called when tool is equipped."""
        print(f"Equipped: {self.name}")
        print(f"Current model: {self.selected_model_name}")
        print(f"Available models: {len(self.available_models)}")
        print(f"Controls:")
        print(f"  - Left click: Place model")
        print(f"  - Right click + drag: Rotate")
        print(f"  - R: Rotate 45°")
        print(f"  - [ / ]: Cycle models")
        print(f"  - G: Toggle grid snap")

        if self.preview:
            self.preview.visible = True

    def on_unequipped(self):
        """Called when tool is unequipped."""
        if self.preview:
            self.preview.hide()

    def render_preview(self, program, textured_program=None):
        """
        Render placement preview.

        Args:
            program: Shader program for primitives
            textured_program: Shader program for textured models
        """
        if self.preview:
            self.preview.render(program, textured_program)

    def get_current_model_name(self) -> str:
        """Get the name of the currently selected model."""
        return self.selected_model_name

    def get_model_count(self) -> int:
        """Get the number of available models."""
        return len(self.available_models)
