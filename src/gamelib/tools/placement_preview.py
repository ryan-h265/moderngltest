"""
Placement Preview

Provides ghost rendering for object placement with visual feedback.
Shows green when placement is valid, red when invalid.
"""

from typing import Optional, TYPE_CHECKING
from pyrr import Vector3, Matrix44
import moderngl

if TYPE_CHECKING:
    from ..loaders.model import Model
    from ..core.scene import SceneObject


class PlacementPreview:
    """
    Renders a transparent preview of an object being placed.

    Shows visual feedback:
    - Green tint: Valid placement
    - Red tint: Invalid placement (collision, out of bounds, etc.)
    - Transparent: Always semi-transparent for ghost effect
    """

    def __init__(self, ctx: moderngl.Context):
        """
        Initialize placement preview.

        Args:
            ctx: ModernGL context
        """
        self.ctx = ctx
        self.model: Optional["Model"] = None
        self.scene_object: Optional["SceneObject"] = None
        self.position: Vector3 = Vector3([0.0, 0.0, 0.0])
        self.rotation: Vector3 = Vector3([0.0, 0.0, 0.0])
        self.scale: Vector3 = Vector3([1.0, 1.0, 1.0])
        self.is_valid: bool = True  # Green if True, Red if False
        self.visible: bool = False
        self.alpha: float = 0.5  # Transparency level

    def set_model(self, model: "Model"):
        """
        Set a Model to preview.

        Args:
            model: Model instance to preview
        """
        self.model = model
        self.scene_object = None
        self.visible = True

    def set_scene_object(self, scene_object: "SceneObject"):
        """
        Set a SceneObject to preview.

        Args:
            scene_object: SceneObject instance to preview
        """
        self.scene_object = scene_object
        self.model = None
        self.visible = True

    def update_transform(self, position: Vector3, rotation: Vector3, is_valid: bool):
        """
        Update preview position, rotation, and validity.

        Args:
            position: World position
            rotation: Rotation in radians (yaw, pitch, roll)
            is_valid: True if placement is valid (green), False if invalid (red)
        """
        self.position = position
        self.rotation = rotation
        self.is_valid = is_valid
        self.visible = True

    def hide(self):
        """Hide the preview."""
        self.visible = False

    def render(self, program, textured_program=None):
        """
        Render the preview with color tint and transparency.

        Args:
            program: Shader program for primitives
            textured_program: Optional shader program for textured models
        """
        if not self.visible:
            return

        if self.model is None and self.scene_object is None:
            return

        # Enable blending for transparency
        self.ctx.enable(moderngl.BLEND)
        old_blend_func = self.ctx.blend_func
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        # Disable depth writing (but keep depth testing)
        self.ctx.depth_mask = False

        # Set color tint (green if valid, red if invalid)
        if self.is_valid:
            tint_color = Vector3([0.2, 1.0, 0.2])  # Green
        else:
            tint_color = Vector3([1.0, 0.2, 0.2])  # Red

        # Render model or scene object
        if self.model:
            self._render_model(program, textured_program, tint_color)
        elif self.scene_object:
            self._render_scene_object(program, tint_color)

        # Restore render state
        self.ctx.depth_mask = True
        self.ctx.blend_func = old_blend_func

    def _render_model(self, program, textured_program, tint_color: Vector3):
        """
        Render a Model with preview tint.

        Args:
            program: Primitive shader program
            textured_program: Textured shader program
            tint_color: RGB tint color
        """
        # Create transform matrix
        transform = Matrix44.from_translation(self.position)

        # Apply rotation (yaw, pitch, roll)
        if self.rotation is not None:
            from pyrr import Quaternion
            quat = Quaternion.from_eulers(self.rotation)
            transform = transform * Matrix44.from_quaternion(quat)

        # Apply scale
        if self.scale is not None:
            transform = transform * Matrix44.from_scale(self.scale)

        # Render each mesh
        for mesh in self.model.meshes:
            # Use textured program if available and mesh has textures
            if textured_program and mesh.material.base_color_texture:
                active_program = textured_program
            else:
                active_program = program

            # Set tint uniform if shader supports it
            if 'previewTint' in active_program:
                active_program['previewTint'].value = tuple(tint_color) + (self.alpha,)

            # Render mesh
            mesh.render(active_program, parent_transform=transform, ctx=self.ctx)

    def _render_scene_object(self, program, tint_color: Vector3):
        """
        Render a SceneObject with preview tint.

        Args:
            program: Shader program
            tint_color: RGB tint color
        """
        # Create transform matrix
        transform = Matrix44.from_translation(self.position)

        # Apply rotation
        if self.rotation is not None:
            from pyrr import Quaternion
            quat = Quaternion.from_eulers(self.rotation)
            transform = transform * Matrix44.from_quaternion(quat)

        # Apply scale
        if self.scale is not None:
            transform = transform * Matrix44.from_scale(self.scale)

        # Set uniforms
        if 'model' in program:
            program['model'].write(transform.astype('f4').tobytes())

        # Set color with tint and transparency
        if 'object_color' in program:
            color = Vector3(self.scene_object.color) * tint_color
            # Note: Shader would need to support alpha for full transparency
            program['object_color'].write(color.astype('f4').tobytes())

        # Render geometry
        self.scene_object.geometry.render(program)

    def get_transform_matrix(self) -> Matrix44:
        """
        Get the current transform matrix.

        Returns:
            4x4 transformation matrix
        """
        transform = Matrix44.from_translation(self.position)

        if self.rotation is not None:
            from pyrr import Quaternion
            quat = Quaternion.from_eulers(self.rotation)
            transform = transform * Matrix44.from_quaternion(quat)

        if self.scale is not None:
            transform = transform * Matrix44.from_scale(self.scale)

        return transform

    def __repr__(self):
        status = "valid" if self.is_valid else "invalid"
        visible = "visible" if self.visible else "hidden"
        return f"<PlacementPreview {status} {visible} pos={self.position}>"
