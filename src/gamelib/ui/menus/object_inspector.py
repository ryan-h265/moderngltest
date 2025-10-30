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
    from ..layout_manager import LayoutManager


class ObjectInspector:
    """Inspector panel for editing selected object properties."""

    def __init__(self, layout_manager: Optional[LayoutManager] = None, tool_manager=None):
        """
        Initialize object inspector.

        Args:
            layout_manager: LayoutManager for panel positioning (optional)
            tool_manager: Tool manager for updating active tools (optional)
        """
        self.layout_manager = layout_manager
        self.tool_manager = tool_manager
        self.selected_object: Optional[SceneObject] = None
        self.preview_item: Optional[dict] = None  # Preview item from thumbnail menu
        self.editor_history: Optional[EditorHistory] = None
        self.show = True
        self.mode = "edit"  # "edit" for scene objects or "preview" for thumbnail items

        # Temporary storage for edits (before applying)
        self.temp_position = Vector3()
        self.temp_rotation = Vector3()
        self.temp_scale = Vector3()
        self.temp_color = (1.0, 1.0, 1.0, 1.0)
        self.temp_casts_shadow = True
        self.temp_physics_enabled = False

    def draw(self, screen_width: int, screen_height: int, force_show: bool = False) -> None:
        """
        Draw object inspector panel (docked on right side).

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            force_show: If True, show panel even without selection (for attribute mode)
        """
        # Determine if we should show
        has_selection = self.selected_object is not None or self.preview_item is not None
        if not self.show or (not has_selection and not force_show):
            return

        # Use layout manager for positioning if available
        if self.layout_manager:
            rect = self.layout_manager.get_panel_rect(
                "object_inspector", screen_width, screen_height
            )
            if rect:
                inspector_x, inspector_y, inspector_width, inspector_height = rect
            else:
                # Fallback positioning
                inspector_width = 350
                inspector_height = screen_height
                inspector_x = screen_width - inspector_width
                inspector_y = 0
        else:
            # Original fallback positioning
            inspector_width = 350
            inspector_height = screen_height
            inspector_x = screen_width - inspector_width
            inspector_y = 0

        imgui.set_next_window_position(
            inspector_x,
            inspector_y,
            imgui.ONCE,
        )
        imgui.set_next_window_size(inspector_width, inspector_height, imgui.ALWAYS)

        expanded, self.show = imgui.begin(
            "Inspector##inspector",
            self.show,
        )

        if not expanded:
            imgui.end()
            return

        # Handle both edit and preview modes
        if self.mode == "preview" and self.preview_item:
            self._draw_preview_mode()
        elif self.mode == "edit" and self.selected_object:
            self._draw_edit_mode()
        else:
            # No selection - show help text
            imgui.text("Inspector")
            imgui.separator()
            imgui.text_wrapped("Click on an object in the scene to edit it,")
            imgui.text_wrapped("or select an asset from the thumbnail menu below.")

        imgui.end()

    def _draw_preview_mode(self) -> None:
        """Draw preview mode for items from thumbnail menu."""
        item = self.preview_item
        if not item:
            return

        # Title
        item_name = item.get("name", "Preview Item")
        item_category = item.get("category", "Unknown")
        imgui.text(f"Preview: {item_name}")
        imgui.text(f"Category: {item_category}")
        imgui.separator()

        # Transform settings (for preview object)
        if imgui.collapsing_header("Transform", True)[0]:
            self._draw_preview_transform_section()

        # Appearance
        if imgui.collapsing_header("Appearance", True)[0]:
            self._draw_preview_appearance_section()

        # Physics
        if imgui.collapsing_header("Physics", True)[0]:
            self._draw_preview_physics_section()

        # Info
        imgui.separator()
        imgui.text(f"Path: {item.get('path', 'N/A')[:50]}...")

    def _draw_edit_mode(self) -> None:
        """Draw edit mode for scene objects."""
        obj = self.selected_object
        if obj is None:
            return

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

    def _draw_preview_transform_section(self) -> None:
        """Draw transform settings for preview item."""
        item = self.preview_item
        if not item:
            return

        # Position sliders
        pos = item.get("position", [0.0, 0.0, 0.0])
        if not isinstance(pos, list):
            pos = [pos.x, pos.y, pos.z] if hasattr(pos, 'x') else [0.0, 0.0, 0.0]

        changed, x = imgui.slider_float("X##pos_x", float(pos[0]), -500.0, 500.0, "%.2f")
        if changed:
            pos[0] = x
            item["position"] = pos

        changed, y = imgui.slider_float("Y##pos_y", float(pos[1]), -500.0, 500.0, "%.2f")
        if changed:
            pos[1] = y
            item["position"] = pos

        changed, z = imgui.slider_float("Z##pos_z", float(pos[2]), -500.0, 500.0, "%.2f")
        if changed:
            pos[2] = z
            item["position"] = pos

        # Scale slider (uniform)
        scale = item.get("scale", 1.0)
        changed, new_scale = imgui.slider_float("Scale", float(scale), 0.1, 10.0, "%.2f")
        if changed:
            item["scale"] = new_scale

        # Rotation sliders (simplified, Y rotation mainly)
        rotation = item.get("rotation_y", 0.0)
        changed, new_rot = imgui.slider_float("Rotation Y (°)", float(rotation), -360.0, 360.0, "%.1f")
        if changed:
            item["rotation_y"] = new_rot

    def _draw_preview_appearance_section(self) -> None:
        """Draw appearance settings for preview item."""
        item = self.preview_item
        if not item:
            return

        category = item.get("category", "Unknown")

        # Show different controls for lights vs other items
        if category == "Lights":
            self._draw_preview_light_section()
        else:
            # Color picker for models/other items
            color = item.get("color", [1.0, 1.0, 1.0, 1.0])
            if not isinstance(color, (list, tuple)):
                color = [1.0, 1.0, 1.0, 1.0]
            if len(color) == 3:
                color = list(color) + [1.0]

            changed, new_color = imgui.color_edit4("Color##preview_color", *color)
            if changed:
                item["color"] = list(new_color)

            # Tint (same as color for now)
            imgui.text("(Color acts as tint)")

    def _draw_preview_light_section(self) -> None:
        """Draw light-specific controls for light presets."""
        from ..tools.editor.light_editor_tool import LightEditorTool

        item = self.preview_item
        if not item:
            return

        # Color picker
        color = item.get("color", [1.0, 1.0, 1.0])
        if isinstance(color, (tuple, list)) and len(color) >= 3:
            color = list(color[:3])  # Use RGB only for color picker
        else:
            color = [1.0, 1.0, 1.0]

        changed, new_color = imgui.color_edit3("Color##light_color", *color)
        if changed:
            item["color"] = list(new_color)
            # Update tool if available
            if self.tool_manager:
                active_tool = self.tool_manager.get_active_tool()
                if isinstance(active_tool, LightEditorTool):
                    active_tool.set_light_color(Vector3(new_color))

        # Intensity slider
        intensity = item.get("intensity", 1.0)
        changed, new_intensity = imgui.slider_float("Intensity", float(intensity), 0.0, 3.0, "%.2f")
        if changed:
            item["intensity"] = new_intensity
            # Update tool if available
            if self.tool_manager:
                active_tool = self.tool_manager.get_active_tool()
                if isinstance(active_tool, LightEditorTool):
                    active_tool.set_light_intensity(new_intensity)

        # Light type selection
        light_type = item.get("type", "directional")
        if imgui.begin_combo("Type", light_type.title()):
            for label, value in [("Directional", "directional"), ("Point", "point"), ("Spot", "spot")]:
                is_selected = light_type == value
                if imgui.selectable(label, is_selected)[0]:
                    light_type = value
                    item["type"] = value
                    if self.tool_manager:
                        active_tool = self.tool_manager.get_active_tool()
                        if isinstance(active_tool, LightEditorTool):
                            active_tool.set_light_type(value)
                if is_selected:
                    imgui.set_item_default_focus()
            imgui.end_combo()

        # Range and shadow settings for non-directional lights
        if light_type in ("point", "spot"):
            light_range = float(item.get("range", 15.0))
            changed, new_range = imgui.slider_float("Range##light_range", light_range, 0.1, 200.0, "%.1f")
            if changed:
                item["range"] = new_range
                if self.tool_manager:
                    active_tool = self.tool_manager.get_active_tool()
                    if isinstance(active_tool, LightEditorTool):
                        active_tool.set_light_range(new_range)

            shadow_near = float(item.get("shadow_near", 0.1))
            shadow_far = float(item.get("shadow_far", 30.0))
            changed_clip, new_near, new_far = imgui.drag_float_range2(
                "Shadow Clip##light_clip",
                shadow_near,
                shadow_far,
                0.01,
                0.01,
                300.0,
                "Near %.2f",
                "Far %.1f",
            )
            if changed_clip:
                new_far = max(new_far, new_near + 0.1)
                item["shadow_near"] = new_near
                item["shadow_far"] = new_far
                if self.tool_manager:
                    active_tool = self.tool_manager.get_active_tool()
                    if isinstance(active_tool, LightEditorTool):
                        active_tool.set_shadow_planes(new_near, new_far)

        if light_type == "spot":
            inner_angle = float(item.get("inner_cone_angle", 20.0))
            outer_angle = float(item.get("outer_cone_angle", 30.0))
            outer_angle = max(outer_angle, inner_angle)
            changed_inner, new_inner = imgui.slider_float("Inner Angle##spot_inner", inner_angle, 0.0, max(outer_angle, 0.1), "%.1f")
            if changed_inner:
                inner_angle = new_inner
                outer_angle = max(outer_angle, inner_angle)
            changed_outer, new_outer = imgui.slider_float("Outer Angle##spot_outer", outer_angle, inner_angle, 120.0, "%.1f")
            if changed_outer:
                outer_angle = max(new_outer, inner_angle)
            if changed_inner or changed_outer:
                item["inner_cone_angle"] = inner_angle
                item["outer_cone_angle"] = outer_angle
                if self.tool_manager:
                    active_tool = self.tool_manager.get_active_tool()
                    if isinstance(active_tool, LightEditorTool):
                        active_tool.set_spot_angles(inner_angle, outer_angle)

        # Cast shadows checkbox
        cast_shadows = item.get("cast_shadows", True)
        changed, new_cast_shadows = imgui.checkbox("Cast Shadows##light_cast_shadows", cast_shadows)
        if changed:
            item["cast_shadows"] = new_cast_shadows
            # Update tool if available
            if self.tool_manager:
                active_tool = self.tool_manager.get_active_tool()
                if isinstance(active_tool, LightEditorTool):
                    active_tool.set_cast_shadows(new_cast_shadows)

    def _draw_preview_physics_section(self) -> None:
        """Draw physics settings for preview item."""
        item = self.preview_item
        if not item:
            return

        # Casts shadow checkbox
        casts_shadow = item.get("casts_shadow", True)
        changed, new_casts = imgui.checkbox("Casts Shadow##preview_shadow", casts_shadow)
        if changed:
            item["casts_shadow"] = new_casts

        # Physics enabled checkbox
        physics_enabled = item.get("physics_enabled", False)
        changed, new_physics = imgui.checkbox("Physics Enabled##preview_physics", physics_enabled)
        if changed:
            item["physics_enabled"] = new_physics

        # Mass (if physics enabled)
        if physics_enabled:
            mass = item.get("mass", 1.0)
            changed, new_mass = imgui.slider_float("Mass##preview_mass", float(mass), 0.1, 100.0, "%.1f")
            if changed:
                item["mass"] = new_mass

    def set_selected_object(self, obj: Optional[SceneObject]):
        """
        Set the currently selected object.

        Args:
            obj: SceneObject to inspect (or None to deselect)
        """
        self.selected_object = obj
        self.mode = "edit"
        if obj:
            self.temp_position = Vector3(obj.position)
            self.temp_rotation = Vector3(obj.rotation)
            self.temp_scale = Vector3(obj.scale)
            if hasattr(obj, 'color'):
                self.temp_color = (*obj.color, 1.0) if len(obj.color) == 3 else obj.color

    def set_preview_item(self, item: Optional[dict]):
        """
        Set preview item from thumbnail menu.

        Args:
            item: Item dict with name, category, and properties (or None to deselect)
        """
        self.preview_item = item
        if item:
            self.mode = "preview"
            # Initialize default values if not present
            if "position" not in item:
                item["position"] = [0.0, 0.0, 0.0]
            if "scale" not in item:
                item["scale"] = 1.0
            if "rotation_y" not in item:
                item["rotation_y"] = 0.0
            if "color" not in item:
                item["color"] = [1.0, 1.0, 1.0, 1.0]
            if "casts_shadow" not in item:
                item["casts_shadow"] = True
            if "physics_enabled" not in item:
                item["physics_enabled"] = False
            if "mass" not in item:
                item["mass"] = 1.0
