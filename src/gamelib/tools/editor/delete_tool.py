"""
Delete Tool

Raycast-based tool for deleting objects and lights from the scene.
"""

from typing import Optional, Dict, TYPE_CHECKING
from pyrr import Vector3
from ..tool_base import EditorTool
from ..editor_history import DeleteObjectOperation, DeleteLightOperation

if TYPE_CHECKING:
    from ...core.camera import Camera
    from ...core.scene import Scene, SceneObject
    from ..tool_definition import ToolDefinition


class DeleteTool(EditorTool):
    """
    Tool for deleting objects and lights via raycast selection.

    Usage:
    - Left click: Delete object under cursor
    - Shows highlight on hover
    """

    def __init__(self, definition: "ToolDefinition", ctx=None):
        """
        Initialize delete tool.

        Args:
            definition: Tool definition from JSON
            ctx: ModernGL context
        """
        super().__init__(definition)
        self.ctx = ctx
        self.highlighted_object: Optional["SceneObject"] = None
        self.previous_highlighted_object: Optional["SceneObject"] = None
        self.editor_history = None  # Set by game/editor

        # Highlighting state (store original color and emissive for models)
        self.highlight_color = (1.0, 1.0, 0.0)  # Yellow highlight for primitives
        self.original_color: Optional[tuple] = None
        self.original_emissive_factors: Dict[int, tuple] = {}  # Store original emissive per mesh

    def use(self, camera: "Camera", scene: "Scene", **kwargs) -> bool:
        """
        Delete object under cursor.

        Args:
            camera: Active camera
            scene: Current scene
            **kwargs: Additional context

        Returns:
            True if an object was deleted
        """
        if not self.can_use():
            return False

        # Raycast to find object under cursor
        hit = self._raycast_objects(camera, scene)

        if hit:
            obj, hit_pos, hit_normal = hit

            # Delete the object
            if self.editor_history:
                # Use undo/redo system
                operation = DeleteObjectOperation(obj)
                self.editor_history.execute(operation, scene)
            else:
                # Direct deletion
                if obj in scene.objects:
                    scene.objects.remove(obj)
                    print(f"Deleted: {obj.name}")

            self._start_use()
            return True

        return False

    def use_secondary(self, camera: "Camera", scene: "Scene", **kwargs) -> bool:
        """
        Secondary action (unused for delete tool).

        Args:
            camera: Active camera
            scene: Current scene
            **kwargs: Additional context

        Returns:
            False (no secondary action)
        """
        return False

    def update(self, delta_time: float, camera: "Camera", scene: "Scene"):
        """
        Update tool state and highlight object under cursor.

        Args:
            delta_time: Time since last update
            camera: Active camera
            scene: Current scene
        """
        super().update(delta_time, camera, scene)

        # Update highlighted object (for visual feedback)
        hit = self._raycast_objects(camera, scene)
        new_highlight = hit[0] if hit else None

        # If highlight changed, update colors/emissive
        if new_highlight != self.highlighted_object:
            # Restore previous object's appearance
            if self.previous_highlighted_object:
                if hasattr(self.previous_highlighted_object, 'is_model') and self.previous_highlighted_object.is_model:
                    # Model: restore emissive values
                    for mesh_idx, original_emissive in self.original_emissive_factors.items():
                        if mesh_idx < len(self.previous_highlighted_object.meshes):
                            self.previous_highlighted_object.meshes[mesh_idx].material.emissive_factor = original_emissive
                    self.original_emissive_factors.clear()
                else:
                    # SceneObject: restore color
                    if self.original_color is not None:
                        self.previous_highlighted_object.color = self.original_color

            # Apply highlight to new object
            if new_highlight:
                if hasattr(new_highlight, 'is_model') and new_highlight.is_model:
                    # Model: boost emissive to yellow glow
                    self.original_emissive_factors.clear()
                    for mesh_idx, mesh in enumerate(new_highlight.meshes):
                        self.original_emissive_factors[mesh_idx] = mesh.material.emissive_factor
                        mesh.material.emissive_factor = (1.0, 1.0, 0.0)  # Yellow glow
                else:
                    # SceneObject: change color to yellow
                    self.original_color = new_highlight.color
                    new_highlight.color = self.highlight_color
                self.previous_highlighted_object = new_highlight
            else:
                self.original_color = None
                self.original_emissive_factors.clear()
                self.previous_highlighted_object = None

            self.highlighted_object = new_highlight

    def on_equipped(self):
        """Called when tool is equipped."""
        print(f"Equipped: {self.name}")
        self.highlighted_object = None

    def on_unequipped(self):
        """Called when tool is unequipped."""
        # Restore appearance of highlighted object
        if self.previous_highlighted_object:
            if hasattr(self.previous_highlighted_object, 'is_model') and self.previous_highlighted_object.is_model:
                # Model: restore emissive values
                for mesh_idx, original_emissive in self.original_emissive_factors.items():
                    if mesh_idx < len(self.previous_highlighted_object.meshes):
                        self.previous_highlighted_object.meshes[mesh_idx].material.emissive_factor = original_emissive
            else:
                # SceneObject: restore color
                if self.original_color is not None:
                    self.previous_highlighted_object.color = self.original_color

        self.highlighted_object = None
        self.previous_highlighted_object = None
        self.original_color = None
        self.original_emissive_factors.clear()

    def _raycast_objects(self, camera: "Camera", scene: "Scene") -> Optional[tuple]:
        """
        Raycast from camera to find object under cursor.

        Args:
            camera: Active camera
            scene: Current scene

        Returns:
            Tuple of (object, hit_position, hit_normal) or None
        """
        # TODO: Implement proper raycast with physics/collision system
        # For now, use simple bounding sphere intersection

        ray_origin = camera.position
        ray_direction = camera._front
        max_distance = self.raycast_range

        closest_hit = None
        closest_distance = max_distance

        for obj in scene.objects:
            # Skip if object doesn't have a position (shouldn't happen)
            if not hasattr(obj, 'position'):
                continue

            # Calculate distance to object center
            to_object = obj.position - ray_origin
            projection = to_object.dot(ray_direction)

            # Object is behind camera
            if projection < 0:
                continue

            # Find closest point on ray to object center
            closest_point = ray_origin + ray_direction * projection
            distance_to_center = (closest_point - obj.position).length

            # Check if ray intersects bounding sphere
            if distance_to_center <= obj.bounding_radius:
                # Approximate hit distance (could be more accurate)
                hit_distance = projection - obj.bounding_radius

                if hit_distance < closest_distance:
                    closest_distance = hit_distance
                    hit_position = ray_origin + ray_direction * projection
                    hit_normal = Vector3([0.0, 1.0, 0.0])  # Approximate
                    closest_hit = (obj, hit_position, hit_normal)

        return closest_hit

    def get_highlighted_object(self) -> Optional["SceneObject"]:
        """
        Get the currently highlighted object.

        Returns:
            Highlighted object or None
        """
        return self.highlighted_object
