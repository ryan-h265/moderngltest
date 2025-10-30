"""
Selection Highlight Renderer

Renders visual highlight/outline around selected objects in editor mode.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import moderngl
import numpy as np
from pyrr import Matrix44, Vector3

if TYPE_CHECKING:
    from ..core.scene import SceneObject


class SelectionHighlight:
    """Renders outline/highlight around selected object."""

    HIGHLIGHT_VERTEX_SHADER = """
    #version 410

    in vec3 in_position;
    in vec3 in_normal;

    uniform mat4 model;
    uniform mat4 view;
    uniform mat4 projection;
    uniform float outline_scale;

    void main() {
        // Scale along normal to create outline effect
        vec3 scaled_pos = in_position + in_normal * outline_scale;
        gl_Position = projection * view * model * vec4(scaled_pos, 1.0);
    }
    """

    HIGHLIGHT_FRAGMENT_SHADER = """
    #version 410

    out vec4 out_color;

    uniform vec4 highlight_color;

    void main() {
        out_color = highlight_color;
    }
    """

    def __init__(self, ctx: moderngl.Context):
        """
        Initialize selection highlight renderer.

        Args:
            ctx: ModernGL context
        """
        self.ctx = ctx
        self.selected_object: Optional[SceneObject] = None
        self.highlight_color = Vector3([1.0, 0.8, 0.0])  # Orange
        self.outline_scale = 0.01  # Slight outline

        # Compile shader program
        try:
            self.program = self.ctx.program(
                vertex_shader=self.HIGHLIGHT_VERTEX_SHADER,
                fragment_shader=self.HIGHLIGHT_FRAGMENT_SHADER
            )
        except Exception as e:
            print(f"Warning: Failed to compile selection highlight shader: {e}")
            self.program = None

    def set_selected_object(self, obj: Optional[SceneObject]) -> None:
        """
        Set the object to highlight.

        Args:
            obj: SceneObject to highlight (or None to clear)
        """
        self.selected_object = obj

    def render(
        self,
        view_matrix: Matrix44,
        projection_matrix: Matrix44,
    ) -> None:
        """
        Render selection highlight around selected object.

        Args:
            view_matrix: Camera view matrix
            projection_matrix: Camera projection matrix
        """
        if not self.selected_object or not self.program:
            return

        obj = self.selected_object

        # Skip if object doesn't have geometry
        if not hasattr(obj, 'geometry') or obj.geometry is None:
            return

        # Skip if object not visible
        if hasattr(obj, 'visible') and not obj.visible:
            return

        # Enable outline rendering (slightly in front)
        self.ctx.enable(moderngl.CULL_FACE)
        self.ctx.front_face = "ccw"

        # Build model matrix from object transform
        model_matrix = self._build_model_matrix(obj)

        # Set uniform values
        self.program['model'].write(model_matrix)
        self.program['view'].write(view_matrix)
        self.program['projection'].write(projection_matrix)
        self.program['highlight_color'].write((*self.highlight_color, 1.0))
        self.program['outline_scale'].write(self.outline_scale)

        # Render geometry
        try:
            geometry = obj.geometry
            if hasattr(geometry, 'render'):
                # Use geometry's render method if available
                geometry.render(self.program)
            elif hasattr(geometry, 'vao') and geometry.vao:
                # Fallback to VAO rendering
                geometry.vao.render(self.program)
        except Exception as e:
            print(f"Warning: Failed to render selection highlight: {e}")

    def render_tint(
        self,
        obj: SceneObject,
        view_matrix: Matrix44,
        projection_matrix: Matrix44,
        tint_color: Vector3 = None,
    ) -> None:
        """
        Render object with tint color overlay (alternative highlight method).

        Uses full object rendering with tint instead of outline.

        Args:
            obj: Object to tint
            view_matrix: Camera view matrix
            projection_matrix: Camera projection matrix
            tint_color: Color to tint with (default orange)
        """
        if not self.program or tint_color is None:
            tint_color = Vector3([1.0, 0.8, 0.0])

        # This would be called after normal rendering to apply tint

    def set_highlight_color(self, color: Vector3) -> None:
        """
        Set highlight color.

        Args:
            color: RGB color as Vector3
        """
        self.highlight_color = color

    def set_outline_scale(self, scale: float) -> None:
        """
        Set outline thickness.

        Args:
            scale: Outline thickness (default 0.01)
        """
        self.outline_scale = scale

    def _build_model_matrix(self, obj: SceneObject) -> Matrix44:
        """
        Build model matrix from object position, rotation, and scale.

        Args:
            obj: SceneObject

        Returns:
            Model matrix
        """
        # Start with identity
        model = Matrix44.identity()

        # Apply translation
        translation = Matrix44.from_translation(obj.position)

        # Apply rotation (from rotation vector in radians)
        rot_x = Matrix44.from_x_rotation(obj.rotation.x)
        rot_y = Matrix44.from_y_rotation(obj.rotation.y)
        rot_z = Matrix44.from_z_rotation(obj.rotation.z)
        rotation = rot_x * rot_y * rot_z

        # Apply scale
        scale = Matrix44.from_scale(obj.scale)

        # Combine: TRS order
        model = translation * rotation * scale

        return model
