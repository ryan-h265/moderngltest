"""
Object Editor Tool

Multi-purpose tool for selecting, moving, rotating, and deleting scene objects.
Supports both continuous drag operations and discrete transformations.
"""

from typing import Optional, Dict, TYPE_CHECKING
from pyrr import Vector3, Quaternion
import math
import numpy as np
from ..tool_base import EditorTool
from ..editor_history import (
    MoveObjectOperation,
    RotateObjectOperation,
    DeleteObjectOperation,
)

if TYPE_CHECKING:
    from ...core.camera import Camera
    from ...core.scene import Scene, SceneObject
    from ..tool_definition import ToolDefinition


class ObjectEditorTool(EditorTool):
    """
    Multi-purpose object manipulation tool.

    Features:
    - Left click: Select object
    - Left click + drag: Move object along surface
    - Right click + drag: Rotate object (continuous)
    - R key: Rotate 45° clockwise (discrete)
    - Delete key: Delete selected object
    - Ctrl+D: Duplicate selected object

    Shows:
    - Highlighted object on hover
    - Selected object indicator
    - Movement preview
    """

    def __init__(self, definition: "ToolDefinition", ctx=None):
        """
        Initialize object editor tool.

        Args:
            definition: Tool definition from JSON
            ctx: ModernGL context
        """
        super().__init__(definition)
        self.ctx = ctx
        self.editor_history = None  # Set by game/editor

        # Selection state
        self.selected_object: Optional["SceneObject"] = None
        self.highlighted_object: Optional["SceneObject"] = None
        self.previous_highlighted_object: Optional["SceneObject"] = None

        # Move operation state
        self.is_moving: bool = False
        self.move_start_position: Optional[Vector3] = None
        self.move_original_position: Optional[Vector3] = None

        # Rotate operation state
        self.is_rotating: bool = False
        self.rotate_start_angle: float = 0.0
        self.rotate_original_rotation: Optional[Quaternion] = None
        self.cumulative_rotation: float = 0.0

        # Highlighting state (store original color and emissive for models)
        self.highlight_color = (1.0, 1.0, 0.0)  # Yellow highlight for primitives
        self.original_color: Optional[tuple] = None
        self.original_emissive_factors: Dict[int, tuple] = {}  # Store original emissive per mesh

    def use(self, camera: "Camera", scene: "Scene", **kwargs) -> bool:
        """
        Primary action: Select object or start move operation.

        Args:
            camera: Active camera
            scene: Current scene
            **kwargs: Additional context (mouse_held, etc.)

        Returns:
            True if action was performed
        """
        if not self.can_use():
            return False

        mouse_held = kwargs.get('mouse_held', False)

        if not mouse_held:
            # Initial click - select object
            hit = self._raycast_objects(camera, scene)
            if hit:
                obj, hit_pos, hit_normal = hit
                self.selected_object = obj
                print(f"Selected: {obj.name}")

                # Start move operation
                self.is_moving = True
                self.move_start_position = Vector3(hit_pos)
                self.move_original_position = Vector3(obj.position)
                return True
            else:
                # Clicked empty space - deselect
                self.selected_object = None
                return False
        else:
            # Mouse held - continue moving selected object
            if self.is_moving and self.selected_object:
                self._update_move(camera, scene)
                return True

        return False

    def use_secondary(self, camera: "Camera", scene: "Scene", **kwargs) -> bool:
        """
        Secondary action: Rotate selected object (continuous drag).

        Args:
            camera: Active camera
            scene: Current scene
            **kwargs: Additional context (mouse_delta_x, mouse_delta_y, mouse_held)

        Returns:
            True if action was performed
        """
        if not self.selected_object:
            return False

        mouse_held = kwargs.get('mouse_held', False)
        mouse_delta_x = kwargs.get('mouse_delta_x', 0.0)

        if not mouse_held:
            # Start rotation
            self.is_rotating = True
            self.rotate_original_rotation = Quaternion(self.selected_object.rotation)
            self.cumulative_rotation = 0.0
            print(f"Rotating: {self.selected_object.name}")
            return True
        else:
            # Continue rotation
            if self.is_rotating:
                # Rotate based on mouse delta
                rotation_speed = self.get_property("rotation_speed", 0.01)
                delta_angle = mouse_delta_x * rotation_speed
                self.cumulative_rotation += delta_angle

                # Apply rotation around Y axis
                rotation_quat = Quaternion.from_y_rotation(self.cumulative_rotation)
                self.selected_object.rotation = self.rotate_original_rotation * rotation_quat
                return True

        return False

    def update(self, delta_time: float, camera: "Camera", scene: "Scene"):
        """
        Update tool state and highlight objects.

        Args:
            delta_time: Time since last update
            camera: Active camera
            scene: Current scene
        """
        super().update(delta_time, camera, scene)

        # Update highlighted object (for visual feedback)
        if not self.is_moving and not self.is_rotating:
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

    def finish_move(self):
        """Finish move operation and record in history."""
        if self.is_moving and self.selected_object and self.move_original_position is not None:
            # Check if object actually moved
            current_pos = np.array(self.selected_object.position)
            original_pos = np.array(self.move_original_position)
            if not np.allclose(current_pos, original_pos, atol=0.001):
                # Record move operation for undo/redo
                if self.editor_history:
                    operation = MoveObjectOperation(
                        self.selected_object,
                        self.move_original_position,
                        Vector3(self.selected_object.position)
                    )
                    self.editor_history.execute(operation, None)
                    print(f"Moved {self.selected_object.name} to {self.selected_object.position}")

        self.is_moving = False
        self.move_start_position = None
        self.move_original_position = None

    def finish_rotate(self):
        """Finish rotate operation and record in history."""
        if self.is_rotating and self.selected_object and self.rotate_original_rotation:
            # Check if object actually rotated
            current_rot = self.selected_object.rotation
            if not (current_rot == self.rotate_original_rotation):
                # Record rotate operation for undo/redo
                if self.editor_history:
                    operation = RotateObjectOperation(
                        self.selected_object,
                        self.rotate_original_rotation,
                        Quaternion(self.selected_object.rotation)
                    )
                    self.editor_history.execute(operation, None)
                    print(f"Rotated {self.selected_object.name}")

        self.is_rotating = False
        self.rotate_original_rotation = None
        self.cumulative_rotation = 0.0

    def rotate_selected(self, angle_degrees: float):
        """
        Rotate selected object by a fixed angle (discrete rotation).

        Args:
            angle_degrees: Angle to rotate in degrees (positive = clockwise)
        """
        if not self.selected_object:
            print("No object selected")
            return

        # Record original rotation
        old_rotation = Quaternion(self.selected_object.rotation)

        # Apply rotation around Y axis
        angle_radians = math.radians(angle_degrees)
        rotation_quat = Quaternion.from_y_rotation(angle_radians)
        self.selected_object.rotation = old_rotation * rotation_quat

        # Record in history
        if self.editor_history:
            operation = RotateObjectOperation(
                self.selected_object,
                old_rotation,
                Quaternion(self.selected_object.rotation)
            )
            self.editor_history.execute(operation, None)

        print(f"Rotated {self.selected_object.name} by {angle_degrees}°")

    def delete_selected(self, scene: "Scene"):
        """Delete the currently selected object."""
        if not self.selected_object:
            print("No object selected")
            return

        # Record and execute delete operation
        if self.editor_history:
            operation = DeleteObjectOperation(self.selected_object)
            self.editor_history.execute(operation, scene)
            print(f"Deleted: {self.selected_object.name}")

        self.selected_object = None

    def duplicate_selected(self):
        """Duplicate the currently selected object."""
        if not self.selected_object:
            print("No object selected")
            return

        # TODO: Implement object duplication
        # Need to create a deep copy of the object
        print("Duplicate not yet implemented")

    def on_equipped(self):
        """Called when tool is equipped."""
        print(f"Equipped: {self.name}")
        self.selected_object = None
        self.highlighted_object = None
        self.is_moving = False
        self.is_rotating = False

    def on_unequipped(self):
        """Called when tool is unequipped."""
        # Finish any in-progress operations
        if self.is_moving:
            self.finish_move()
        if self.is_rotating:
            self.finish_rotate()

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

        self.selected_object = None
        self.highlighted_object = None
        self.previous_highlighted_object = None
        self.original_color = None
        self.original_emissive_factors.clear()

    def _update_move(self, camera: "Camera", scene: "Scene"):
        """
        Update object position during move operation.

        Args:
            camera: Active camera
            scene: Current scene
        """
        if not self.selected_object or not self.move_original_position:
            return

        # Raycast to get new position
        hit = self.raycast_scene(camera, scene)
        if hit:
            obj, hit_pos, hit_normal = hit

            # Snap to grid if enabled
            new_position = self.snap_to_grid(hit_pos)

            # Update object position
            self.selected_object.position = new_position

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
            # Skip if object doesn't have a position
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
                # Approximate hit distance
                hit_distance = projection - obj.bounding_radius

                if hit_distance < closest_distance:
                    closest_distance = hit_distance
                    hit_position = ray_origin + ray_direction * projection
                    hit_normal = Vector3([0.0, 1.0, 0.0])
                    closest_hit = (obj, hit_position, hit_normal)

        return closest_hit

    def get_selected_object(self) -> Optional["SceneObject"]:
        """Get the currently selected object."""
        return self.selected_object

    def get_highlighted_object(self) -> Optional["SceneObject"]:
        """Get the currently highlighted object."""
        return self.highlighted_object
