"""
Object Inspector

Property editor for selected objects in level editor mode.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import imgui
from pyrr import Vector3

from ..widgets import edit_float, edit_vector3, edit_color, edit_text

if TYPE_CHECKING:
    from ...core.scene import SceneObject
    from ...core.light import Light
    from ...tools.editor_history import EditorHistory


class ObjectInspector:
    """Inspector panel for editing selected object properties."""

    def __init__(self):
        """Initialize object inspector."""
        self.selected_object: Optional[SceneObject] = None
        self.editor_history: Optional[EditorHistory] = None
        self.show = True

        # Temporary storage for edits (before applying)
        self.temp_position = Vector3()
        self.temp_rotation = Vector3()
        self.temp_scale = Vector3()
        self.temp_color = (1.0, 1.0, 1.0, 1.0)

    def draw(self, screen_width: int, screen_height: int) -> None:
        """
        Draw object inspector panel (docked on right side).

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
        """
        if not self.show or self.selected_object is None:
            return

        # Dock on right side
        inspector_width = 350
        inspector_height = screen_height
        imgui.set_next_window_position(
            screen_width - inspector_width,
            0,
            imgui.ALWAYS,
        )
        imgui.set_next_window_size(inspector_width, inspector_height, imgui.ALWAYS)

        expanded, self.show = imgui.begin(
            "Inspector##inspector",
            self.show,
            imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE,
        )

        if not expanded:
            imgui.end()
            return

        obj = self.selected_object

        # Title
        imgui.text(f"Object: {obj.name}")
        imgui.separator()

        # Object type info
        obj_type = "Model" if hasattr(obj, 'is_model') and obj.is_model else "Primitive"
        imgui.text(f"Type: {obj_type}")

        if imgui.collapsing_header("Transform", True)[0]:
            self._draw_transform_section()

        if imgui.collapsing_header("Appearance", True)[0]:
            self._draw_appearance_section()

        if imgui.collapsing_header("Physics", True)[0]:
            self._draw_physics_section()

        if imgui.collapsing_header("Advanced", True)[0]:
            self._draw_advanced_section()

        # Action buttons
        imgui.separator()
        button_width = 150

        if imgui.button("Reset Transform", button_width, 30):
            self.selected_object.position = Vector3()
            self.selected_object.rotation = Vector3()
            self.selected_object.scale = Vector3([1.0, 1.0, 1.0])

        imgui.same_line()
        if imgui.button("Delete Object", button_width, 30):
            # Will be handled by main game loop
            pass

        imgui.end()

    def _draw_transform_section(self):
        """Draw transform properties (position, rotation, scale)."""
        obj = self.selected_object
        if obj is None:
            return

        # Position
        changed, pos = edit_vector3(
            "Position",
            obj.position,
            -500.0,
            500.0,
            0.1,
        )
        if changed:
            obj.position = pos

        # Rotation (in degrees for readability)
        rot_degrees = Vector3([
            float(obj.rotation.x) * 180.0 / 3.14159,
            float(obj.rotation.y) * 180.0 / 3.14159,
            float(obj.rotation.z) * 180.0 / 3.14159,
        ])
        changed, rot_deg = edit_vector3(
            "Rotation (°)",
            rot_degrees,
            -360.0,
            360.0,
            1.0,
        )
        if changed:
            obj.rotation = Vector3([
                float(rot_deg.x) * 3.14159 / 180.0,
                float(rot_deg.y) * 3.14159 / 180.0,
                float(rot_deg.z) * 3.14159 / 180.0,
            ])

        # Scale
        changed, scale = edit_vector3(
            "Scale",
            obj.scale,
            0.1,
            10.0,
            0.1,
        )
        if changed:
            obj.scale = scale

    def _draw_appearance_section(self):
        """Draw appearance properties (color, material, etc.)."""
        obj = self.selected_object
        if obj is None:
            return

        # Color (for primitives)
        if hasattr(obj, 'color') and not (hasattr(obj, 'is_model') and obj.is_model):
            current_color = (*obj.color, 1.0) if len(obj.color) == 3 else obj.color
            changed, color = edit_color("Color", current_color)
            if changed:
                obj.color = color[:3]

        # Name
        changed, name = edit_text("Name", obj.name)
        if changed:
            obj.name = name

        # Visibility toggle
        visible = getattr(obj, 'visible', True)
        changed, visible = imgui.checkbox("Visible##visible", visible)
        if changed:
            if hasattr(obj, 'visible'):
                obj.visible = visible

    def _draw_physics_section(self):
        """Draw physics properties."""
        obj = self.selected_object
        if obj is None:
            return

        # Physics body reference
        if hasattr(obj, 'physics_body') and obj.physics_body:
            imgui.text("Physics: Enabled")

            # Mass
            mass = getattr(obj.physics_body, 'mass', 1.0)
            changed, mass = edit_float("Mass", mass, 0.1, 100.0, 0.1)
            if changed:
                if hasattr(obj.physics_body, 'set_mass'):
                    obj.physics_body.set_mass(mass)

        else:
            imgui.text("Physics: Disabled")

        # Bounding radius (for frustum culling)
        if hasattr(obj, 'bounding_radius'):
            changed, radius = edit_float(
                "Bounding Radius",
                obj.bounding_radius,
                0.1,
                100.0,
                0.1,
            )
            if changed:
                obj.bounding_radius = radius

    def _draw_advanced_section(self):
        """Draw advanced properties."""
        obj = self.selected_object
        if obj is None:
            return

        imgui.text("Advanced Properties")

        # Object ID
        obj_id = id(obj)
        imgui.text(f"ID: {obj_id}")

        # Geometry info
        if hasattr(obj, 'geometry'):
            imgui.text(f"Geometry: {type(obj.geometry).__name__}")

        # Position info for debugging
        imgui.separator()
        imgui.text(f"Pos: ({obj.position.x:.2f}, {obj.position.y:.2f}, {obj.position.z:.2f})")

    def set_selected_object(self, obj: Optional[SceneObject]):
        """
        Set the currently selected object.

        Args:
            obj: SceneObject to inspect (or None to deselect)
        """
        self.selected_object = obj
        if obj:
            self.temp_position = Vector3(obj.position)
            self.temp_rotation = Vector3(obj.rotation)
            self.temp_scale = Vector3(obj.scale)
            if hasattr(obj, 'color'):
                self.temp_color = (*obj.color, 1.0) if len(obj.color) == 3 else obj.color
