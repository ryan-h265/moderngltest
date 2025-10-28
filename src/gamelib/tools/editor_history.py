"""
Editor History

Undo/redo system for level editor operations.
Uses command pattern to track and reverse editor actions.
"""

from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING, Any, Optional
from pyrr import Vector3
import copy

if TYPE_CHECKING:
    from ..core.scene import Scene, SceneObject
    from ..core.light import Light


class EditorOperation(ABC):
    """
    Abstract base class for undoable editor operations.

    Each operation must implement execute() and undo() methods.
    Operations follow the Command pattern.
    """

    @abstractmethod
    def execute(self, scene: "Scene") -> bool:
        """
        Execute the operation.

        Args:
            scene: Scene to operate on

        Returns:
            True if operation succeeded
        """
        pass

    @abstractmethod
    def undo(self, scene: "Scene"):
        """
        Undo the operation.

        Args:
            scene: Scene to operate on
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """
        Get human-readable description of this operation.

        Returns:
            Description string (e.g., "Place Object", "Delete Light")
        """
        pass


class PlaceObjectOperation(EditorOperation):
    """Place a new object in the scene."""

    def __init__(self, obj: "SceneObject"):
        """
        Initialize place operation.

        Args:
            obj: Object to place
        """
        self.obj = obj
        self.was_placed = False

    def execute(self, scene: "Scene") -> bool:
        """Add object to scene."""
        scene.add_object(self.obj)
        self.was_placed = True
        return True

    def undo(self, scene: "Scene"):
        """Remove object from scene."""
        if self.was_placed and self.obj in scene.objects:
            scene.objects.remove(self.obj)

    def get_description(self) -> str:
        return f"Place {self.obj.name}"


class DeleteObjectOperation(EditorOperation):
    """Delete an object from the scene."""

    def __init__(self, obj: "SceneObject"):
        """
        Initialize delete operation.

        Args:
            obj: Object to delete
        """
        self.obj = obj
        self.index: Optional[int] = None  # Index in scene.objects for restoration

    def execute(self, scene: "Scene") -> bool:
        """Remove object from scene."""
        if self.obj in scene.objects:
            self.index = scene.objects.index(self.obj)
            scene.objects.remove(self.obj)
            return True
        return False

    def undo(self, scene: "Scene"):
        """Restore object to scene."""
        if self.index is not None:
            # Try to restore at original index
            if self.index <= len(scene.objects):
                scene.objects.insert(self.index, self.obj)
            else:
                scene.objects.append(self.obj)

    def get_description(self) -> str:
        return f"Delete {self.obj.name}"


class MoveObjectOperation(EditorOperation):
    """Move an object to a new position."""

    def __init__(self, obj: "SceneObject", old_position: Vector3, new_position: Vector3):
        """
        Initialize move operation.

        Args:
            obj: Object to move
            old_position: Original position
            new_position: New position
        """
        self.obj = obj
        self.old_position = Vector3(old_position)
        self.new_position = Vector3(new_position)

    def execute(self, scene: "Scene") -> bool:
        """Move object to new position."""
        self.obj.position = Vector3(self.new_position)
        return True

    def undo(self, scene: "Scene"):
        """Restore object to old position."""
        self.obj.position = Vector3(self.old_position)

    def get_description(self) -> str:
        return f"Move {self.obj.name}"


class RotateObjectOperation(EditorOperation):
    """Rotate an object."""

    def __init__(self, obj: "SceneObject", old_rotation, new_rotation):
        """
        Initialize rotate operation.

        Args:
            obj: Object to rotate
            old_rotation: Original rotation (Quaternion)
            new_rotation: New rotation (Quaternion)
        """
        self.obj = obj
        self.old_rotation = copy.deepcopy(old_rotation)
        self.new_rotation = copy.deepcopy(new_rotation)

    def execute(self, scene: "Scene") -> bool:
        """Rotate object to new orientation."""
        self.obj.rotation = copy.deepcopy(self.new_rotation)
        return True

    def undo(self, scene: "Scene"):
        """Restore object to old orientation."""
        self.obj.rotation = copy.deepcopy(self.old_rotation)

    def get_description(self) -> str:
        return f"Rotate {self.obj.name}"


class ScaleObjectOperation(EditorOperation):
    """Scale an object."""

    def __init__(self, obj: "SceneObject", old_scale: Vector3, new_scale: Vector3):
        """
        Initialize scale operation.

        Args:
            obj: Object to scale
            old_scale: Original scale
            new_scale: New scale
        """
        self.obj = obj
        self.old_scale = Vector3(old_scale)
        self.new_scale = Vector3(new_scale)

    def execute(self, scene: "Scene") -> bool:
        """Scale object to new size."""
        self.obj.scale = Vector3(self.new_scale)
        return True

    def undo(self, scene: "Scene"):
        """Restore object to old size."""
        self.obj.scale = Vector3(self.old_scale)

    def get_description(self) -> str:
        return f"Scale {self.obj.name}"


class PlaceLightOperation(EditorOperation):
    """Place a new light in the scene."""

    def __init__(self, light: "Light", lights_list: List["Light"]):
        """
        Initialize place light operation.

        Args:
            light: Light to place
            lights_list: Reference to scene's lights list
        """
        self.light = light
        self.lights_list = lights_list
        self.was_placed = False

    def execute(self, scene: "Scene") -> bool:
        """Add light to lights list."""
        self.lights_list.append(self.light)
        self.was_placed = True
        return True

    def undo(self, scene: "Scene"):
        """Remove light from lights list."""
        if self.was_placed and self.light in self.lights_list:
            self.lights_list.remove(self.light)

    def get_description(self) -> str:
        return f"Place Light"


class DeleteLightOperation(EditorOperation):
    """Delete a light from the scene."""

    def __init__(self, light: "Light", lights_list: List["Light"]):
        """
        Initialize delete light operation.

        Args:
            light: Light to delete
            lights_list: Reference to scene's lights list
        """
        self.light = light
        self.lights_list = lights_list
        self.index: Optional[int] = None

    def execute(self, scene: "Scene") -> bool:
        """Remove light from lights list."""
        if self.light in self.lights_list:
            self.index = self.lights_list.index(self.light)
            self.lights_list.remove(self.light)
            return True
        return False

    def undo(self, scene: "Scene"):
        """Restore light to lights list."""
        if self.index is not None:
            if self.index <= len(self.lights_list):
                self.lights_list.insert(self.index, self.light)
            else:
                self.lights_list.append(self.light)

    def get_description(self) -> str:
        return f"Delete Light"


class EditorHistory:
    """
    Manages undo/redo history for the level editor.

    Features:
    - Undo/redo stack
    - Maximum history limit
    - Operation descriptions for UI
    """

    def __init__(self, max_history: int = 100):
        """
        Initialize editor history.

        Args:
            max_history: Maximum number of operations to remember
        """
        self.undo_stack: List[EditorOperation] = []
        self.redo_stack: List[EditorOperation] = []
        self.max_history = max_history

    def execute(self, operation: EditorOperation, scene: "Scene"):
        """
        Execute an operation and add it to history.

        Args:
            operation: Operation to execute
            scene: Scene to operate on
        """
        if operation.execute(scene):
            self.undo_stack.append(operation)
            self.redo_stack.clear()  # Clear redo stack on new operation

            # Limit history size
            if len(self.undo_stack) > self.max_history:
                self.undo_stack.pop(0)

            print(f"Executed: {operation.get_description()}")

    def undo(self, scene: "Scene") -> bool:
        """
        Undo the last operation.

        Args:
            scene: Scene to operate on

        Returns:
            True if operation was undone
        """
        if not self.undo_stack:
            print("Nothing to undo")
            return False

        operation = self.undo_stack.pop()
        operation.undo(scene)
        self.redo_stack.append(operation)

        print(f"Undone: {operation.get_description()}")
        return True

    def redo(self, scene: "Scene") -> bool:
        """
        Redo the last undone operation.

        Args:
            scene: Scene to operate on

        Returns:
            True if operation was redone
        """
        if not self.redo_stack:
            print("Nothing to redo")
            return False

        operation = self.redo_stack.pop()
        operation.execute(scene)
        self.undo_stack.append(operation)

        print(f"Redone: {operation.get_description()}")
        return True

    def can_undo(self) -> bool:
        """Check if there are operations to undo."""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if there are operations to redo."""
        return len(self.redo_stack) > 0

    def get_undo_description(self) -> Optional[str]:
        """Get description of next undo operation."""
        if self.undo_stack:
            return self.undo_stack[-1].get_description()
        return None

    def get_redo_description(self) -> Optional[str]:
        """Get description of next redo operation."""
        if self.redo_stack:
            return self.redo_stack[-1].get_description()
        return None

    def clear(self):
        """Clear all history."""
        self.undo_stack.clear()
        self.redo_stack.clear()

    def __repr__(self):
        return f"<EditorHistory undo={len(self.undo_stack)} redo={len(self.redo_stack)}>"
