"""
Light Editor Tool

Tool for adding, moving, and deleting lights in the scene.
Integrates with existing light system and saves to scene JSON.
"""

from typing import Optional, List, TYPE_CHECKING
from pyrr import Vector3
from ..tool_base import EditorTool
from ..editor_history import PlaceLightOperation, DeleteLightOperation

if TYPE_CHECKING:
    from ...core.camera import Camera
    from ...core.scene import Scene
    from ...core.light import Light
    from ..tool_definition import ToolDefinition


class LightEditorTool(EditorTool):
    """
    Tool for editing lights in the scene.

    Features:
    - Left click: Place new light
    - Right click: Select/move existing light
    - Delete key: Delete selected light
    - Light types: Directional, Point, Spot
    - Adjustable properties: color, intensity, range

    Lights are:
    - Visible as gizmos in editor
    - Integrated with existing light system
    - Saved to scene JSON with other scene data
    """

    def __init__(self, definition: "ToolDefinition", ctx=None):
        """
        Initialize light editor tool.

        Args:
            definition: Tool definition from JSON
            ctx: ModernGL context
        """
        super().__init__(definition)
        self.ctx = ctx
        self.editor_history = None  # Set by game/editor
        self.render_pipeline = None  # Set by game/editor

        # Lights list reference (set by game/editor)
        self.lights_list: Optional[List["Light"]] = None

        # Light placement
        self.placement_position: Vector3 = Vector3([0.0, 5.0, 0.0])
        self.is_valid_placement: bool = True

        # Selected light
        self.selected_light: Optional["Light"] = None
        self.highlighted_light: Optional["Light"] = None

        # Light configuration
        self.light_type: str = self.get_property("default_light_type", "directional")
        self.light_color: Vector3 = Vector3(self.get_property("default_color", [1.0, 1.0, 1.0]))
        self.light_intensity: float = self.get_property("default_intensity", 1.0)
        self.light_height: float = self.get_property("default_height", 5.0)
        self.cast_shadows: bool = self.get_property("default_cast_shadows", True)
        self.light_range: float = float(self.get_property("default_range", 15.0))
        self.shadow_near: float = float(self.get_property("default_shadow_near", 0.1))
        self.shadow_far: float = float(self.get_property("default_shadow_far", 30.0))
        self.inner_cone_angle: float = float(self.get_property("default_inner_angle", 20.0))
        self.outer_cone_angle: float = float(self.get_property("default_outer_angle", 30.0))

        # Move operation
        self.is_moving: bool = False
        self.move_original_position: Optional[Vector3] = None

    def use(self, camera: "Camera", scene: "Scene", **kwargs) -> bool:
        """
        Place a new light at cursor position.

        Args:
            camera: Active camera
            scene: Current scene
            **kwargs: Additional context

        Returns:
            True if light was placed
        """
        if not self.can_use():
            return False

        if not self.lights_list:
            print("Error: Lights list not configured")
            return False

        if not self.is_valid_placement:
            print("Invalid placement")
            return False

        # Create new light
        from ...core.light import Light

        # Position at placement location with configured height
        light_position = Vector3(self.placement_position)
        light_position.y = self.light_height

        # For directional lights, point downward at placement location
        light_target = Vector3(self.placement_position)

        new_light = Light(
            position=light_position,
            target=light_target,
            color=self.light_color,
            intensity=self.light_intensity,
            light_type=self.light_type,
            cast_shadows=self.cast_shadows,
            range=self.light_range,
            inner_cone_angle=self.inner_cone_angle,
            outer_cone_angle=self.outer_cone_angle,
            shadow_near=self.shadow_near,
            shadow_far=self.shadow_far,
        )

        # Record in history
        if self.editor_history:
            operation = PlaceLightOperation(new_light, self.lights_list, self.render_pipeline, camera)
            self.editor_history.execute(operation, scene)
        else:
            # Direct add
            self.lights_list.append(new_light)
            # Initialize shadow map for the new light
            if self.render_pipeline:
                self.render_pipeline.initialize_lights([new_light], camera)

        print(f"Placed {self.light_type} light at {light_position}")
        self._start_use()
        return True

    def use_secondary(self, camera: "Camera", scene: "Scene", **kwargs) -> bool:
        """
        Select or move existing light.

        Args:
            camera: Active camera
            scene: Current scene
            **kwargs: Additional context

        Returns:
            True if action was performed
        """
        if not self.lights_list:
            return False

        mouse_held = kwargs.get('mouse_held', False)

        if not mouse_held:
            # Initial click - select light
            selected = self._select_nearest_light(camera)
            if selected:
                self.selected_light = selected
                self.is_moving = True
                self.move_original_position = Vector3(selected.position)
                print(f"Selected light at {selected.position}")
                return True
            else:
                self.selected_light = None
                return False
        else:
            # Mouse held - move selected light
            if self.is_moving and self.selected_light:
                self._update_light_move(camera, scene)
                return True

        return False

    def update(self, delta_time: float, camera: "Camera", scene: "Scene"):
        """
        Update placement position and light preview.

        Args:
            delta_time: Time since last update
            camera: Active camera
            scene: Current scene
        """
        super().update(delta_time, camera, scene)

        # Update placement position via raycast
        hit = self.raycast_scene(camera, scene)
        if hit:
            obj, hit_pos, hit_normal = hit

            # Snap to grid if enabled
            snapped_pos = self.snap_to_grid(hit_pos)
            self.placement_position = snapped_pos
            self.is_valid_placement = True
        else:
            self.is_valid_placement = False

        # Update highlighted light (for visual feedback)
        if not self.is_moving:
            self.highlighted_light = self._get_light_at_cursor(camera)

    def finish_move(self):
        """Finish moving a light and record in history."""
        if self.is_moving and self.selected_light and self.move_original_position:
            # Check if light actually moved
            if not Vector3(self.selected_light.position).allclose(self.move_original_position, atol=0.001):
                print(f"Moved light to {self.selected_light.position}")
                # TODO: Add MoveLight operation to editor_history
                # For now, just print

        self.is_moving = False
        self.move_original_position = None

    def delete_selected(self):
        """Delete the currently selected light."""
        if not self.selected_light or not self.lights_list:
            print("No light selected")
            return

        # Record delete operation
        if self.editor_history:
            from ...core.scene import Scene
            operation = DeleteLightOperation(self.selected_light, self.lights_list)
            self.editor_history.execute(operation, None)
        else:
            # Direct delete
            if self.selected_light in self.lights_list:
                self.lights_list.remove(self.selected_light)

        print(f"Deleted light at {self.selected_light.position}")
        self.selected_light = None

    def set_light_type(self, light_type: str):
        """
        Set the type of light to place.

        Args:
            light_type: "directional", "point", or "spot"
        """
        if light_type in ["directional", "point", "spot"]:
            self.light_type = light_type
            print(f"Light type: {self.light_type}")
        else:
            print(f"Invalid light type: {light_type}")

    def set_light_color(self, color: Vector3):
        """
        Set the color of lights to place.

        Args:
            color: RGB color (0-1)
        """
        self.light_color = Vector3(color)
        print(f"Light color: {self.light_color}")

    def set_light_intensity(self, intensity: float):
        """
        Set the intensity of lights to place.

        Args:
            intensity: Light intensity
        """
        self.light_intensity = intensity
        print(f"Light intensity: {self.light_intensity}")

    def set_cast_shadows(self, cast_shadows: bool):
        """
        Set whether lights cast shadows.

        Args:
            cast_shadows: True to enable shadows, False to disable
        """
        self.cast_shadows = cast_shadows
        print(f"Cast shadows: {self.cast_shadows}")

    def set_light_range(self, light_range: float):
        """Set effective light range for point and spot lights."""
        self.light_range = max(0.0, float(light_range))
        print(f"Light range: {self.light_range}")

    def set_shadow_planes(self, near_plane: float, far_plane: float):
        """Configure perspective shadow clip planes."""
        near_plane = max(1e-3, float(near_plane))
        far_plane = max(float(far_plane), near_plane + 0.1)
        self.shadow_near = near_plane
        self.shadow_far = far_plane
        print(f"Shadow clip: near={self.shadow_near:.2f}, far={self.shadow_far:.2f}")

    def set_spot_angles(self, inner_angle: float, outer_angle: float):
        """Set spot light cone angles."""
        inner_angle = max(0.0, float(inner_angle))
        outer_angle = max(float(outer_angle), inner_angle)
        self.inner_cone_angle = inner_angle
        self.outer_cone_angle = outer_angle
        print(f"Spot cone: inner={self.inner_cone_angle:.1f}, outer={self.outer_cone_angle:.1f}")

    def on_equipped(self):
        """Called when tool is equipped."""
        print(f"Equipped: {self.name}")
        print(f"Light type: {self.light_type}")
        print(f"Controls:")
        print(f"  - Left click: Place light")
        print(f"  - Right click: Select/move light")
        print(f"  - Delete: Remove selected light")

    def on_unequipped(self):
        """Called when tool is unequipped."""
        if self.is_moving:
            self.finish_move()
        self.selected_light = None
        self.highlighted_light = None

    def _update_light_move(self, camera: "Camera", scene: "Scene"):
        """
        Update light position during move operation.

        Args:
            camera: Active camera
            scene: Current scene
        """
        if not self.selected_light:
            return

        # Raycast to get new position
        hit = self.raycast_scene(camera, scene)
        if hit:
            obj, hit_pos, hit_normal = hit

            # Snap to grid if enabled
            new_position = self.snap_to_grid(hit_pos)
            new_position.y = self.light_height  # Maintain height

            # Update light position
            self.selected_light.position = new_position

            # For directional lights, update target to point at ground
            if self.selected_light.light_type == "directional":
                target = Vector3(new_position)
                target.y = 0.0
                self.selected_light.target = target

    def _select_nearest_light(self, camera: "Camera") -> Optional["Light"]:
        """
        Select the light nearest to the cursor.

        Args:
            camera: Active camera

        Returns:
            Nearest light or None
        """
        if not self.lights_list:
            return None

        ray_origin = camera.position
        ray_direction = camera._front
        selection_radius = 1.0  # Lights have a 1-unit selection radius

        closest_light = None
        closest_distance = float('inf')

        for light in self.lights_list:
            # Calculate distance from ray to light
            to_light = light.position - ray_origin
            projection = to_light.dot(ray_direction)

            if projection < 0:
                continue  # Behind camera

            closest_point = ray_origin + ray_direction * projection
            distance = (closest_point - light.position).length

            if distance < selection_radius and projection < closest_distance:
                closest_distance = projection
                closest_light = light

        return closest_light

    def _get_light_at_cursor(self, camera: "Camera") -> Optional["Light"]:
        """
        Get light under cursor (for highlighting).

        Args:
            camera: Active camera

        Returns:
            Light under cursor or None
        """
        return self._select_nearest_light(camera)

    def get_selected_light(self) -> Optional["Light"]:
        """Get the currently selected light."""
        return self.selected_light

    def get_highlighted_light(self) -> Optional["Light"]:
        """Get the currently highlighted light."""
        return self.highlighted_light
