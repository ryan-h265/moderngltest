"""
Tool Base Class

Abstract base class for all tools in the game.
Defines the interface that all tools must implement.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional
from pyrr import Vector3
from .tool_state import ToolState
from .tool_definition import ToolDefinition

if TYPE_CHECKING:
    from ..core.camera import Camera
    from ..core.scene import Scene


class Tool(ABC):
    """
    Abstract base class for all tools.

    Tools follow a state machine pattern:
    - IDLE: Ready to use
    - USING: Action in progress
    - COOLDOWN: Waiting to be ready again
    - RELOADING: Reloading ammo (weapons)
    - DISABLED: Cannot be used

    Subclasses must implement:
    - use(): Primary action (left click)
    - use_secondary(): Secondary action (right click)
    - on_equipped(): Setup when tool becomes active
    - on_unequipped(): Cleanup when tool is switched away
    """

    def __init__(self, definition: ToolDefinition):
        """
        Initialize tool from definition.

        Args:
            definition: ToolDefinition loaded from JSON
        """
        self.definition = definition
        self.id = definition.id
        self.name = definition.name
        self.category = definition.category
        self.cursor_type = definition.cursor

        # State management
        self.state = ToolState.IDLE
        self.cooldown_time = definition.cooldown
        self.cooldown_remaining = 0.0
        self.use_duration = definition.use_duration
        self.use_time_remaining = 0.0

        # Properties from JSON
        self.properties = definition.properties

    @abstractmethod
    def use(self, camera: "Camera", scene: "Scene", **kwargs) -> bool:
        """
        Use the tool (primary action, typically left click).

        Args:
            camera: Active camera for raycasting
            scene: Current scene
            **kwargs: Additional context (mouse position, modifiers, etc.)

        Returns:
            True if action was successful, False if failed or on cooldown
        """
        pass

    @abstractmethod
    def use_secondary(self, camera: "Camera", scene: "Scene", **kwargs) -> bool:
        """
        Use tool's secondary action (typically right click).

        Args:
            camera: Active camera
            scene: Current scene
            **kwargs: Additional context

        Returns:
            True if action was successful
        """
        pass

    def update(self, delta_time: float, camera: "Camera", scene: "Scene"):
        """
        Update tool state (cooldowns, continuous actions, previews).

        Called every frame while tool is equipped.

        Args:
            delta_time: Time since last update
            camera: Active camera
            scene: Current scene
        """
        # Update use duration (for actions that take time)
        if self.state == ToolState.USING:
            self.use_time_remaining -= delta_time
            if self.use_time_remaining <= 0:
                self._finish_use()

        # Update cooldown
        if self.state == ToolState.COOLDOWN:
            self.cooldown_remaining -= delta_time
            if self.cooldown_remaining <= 0:
                self.state = ToolState.IDLE

    def _start_use(self):
        """
        Begin using the tool.

        Transitions state to USING and sets up timing.
        """
        if self.use_duration > 0:
            self.state = ToolState.USING
            self.use_time_remaining = self.use_duration
        else:
            # Instant action, go straight to cooldown
            self._finish_use()

    def _finish_use(self):
        """
        Finish using the tool.

        Transitions to COOLDOWN or IDLE depending on cooldown time.
        """
        if self.cooldown_time > 0:
            self.state = ToolState.COOLDOWN
            self.cooldown_remaining = self.cooldown_time
        else:
            self.state = ToolState.IDLE

    def can_use(self) -> bool:
        """
        Check if tool can be used right now.

        Returns:
            True if tool is in IDLE state
        """
        return self.state == ToolState.IDLE

    @abstractmethod
    def on_equipped(self):
        """
        Called when tool becomes active (equipped by player).

        Setup any state, enable previews, etc.
        """
        pass

    @abstractmethod
    def on_unequipped(self):
        """
        Called when tool is deactivated (switched to another tool).

        Clean up state, disable previews, etc.
        """
        pass

    def get_property(self, key: str, default=None):
        """
        Get a property from the tool's JSON definition.

        Args:
            key: Property key
            default: Default value if key doesn't exist

        Returns:
            Property value or default
        """
        return self.properties.get(key, default)

    def __repr__(self):
        return f"<Tool '{self.name}' (id={self.id}, state={self.state.name})>"


class EditorTool(Tool):
    """
    Base class for level editor tools.

    Editor tools typically have:
    - Placement previews
    - Grid snapping
    - Undo/redo support
    """

    def __init__(self, definition: ToolDefinition):
        super().__init__(definition)

        # Grid snapping
        self.grid_snap_enabled = self.get_property("snap_to_grid", True)
        self.grid_size = self.get_property("grid_size", 1.0)

        # Raycast settings
        self.raycast_range = self.get_property("raycast_range", 1000.0)

    def snap_to_grid(self, position: Vector3) -> Vector3:
        """
        Snap a position to the grid.

        Args:
            position: World position

        Returns:
            Snapped position
        """
        if not self.grid_snap_enabled:
            return position

        snapped = Vector3([
            round(position.x / self.grid_size) * self.grid_size,
            position.y,  # Y is determined by surface raycast, not grid
            round(position.z / self.grid_size) * self.grid_size
        ])
        return snapped

    def raycast_scene(self, camera: "Camera", scene: "Scene") -> Optional[tuple]:
        """
        Raycast from camera into scene.

        Args:
            camera: Active camera
            scene: Current scene

        Returns:
            Tuple of (hit_object, hit_position, hit_normal) or None if no hit
        """
        # TODO: Implement proper raycast with physics system
        # For now, return a simple ground plane intersection
        ray_origin = camera.position
        ray_direction = camera._front

        # Simple ground plane (y=0) intersection
        if abs(ray_direction.y) > 0.001:
            t = -ray_origin.y / ray_direction.y
            if 0 < t < self.raycast_range:
                hit_position = ray_origin + ray_direction * t
                hit_normal = Vector3([0.0, 1.0, 0.0])
                return (None, hit_position, hit_normal)

        return None
