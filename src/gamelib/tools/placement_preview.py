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

    def render_to_scene(self, scene: "Scene"):
        """
        Add preview model to scene for rendering via normal pipeline.

        This is the simplest approach - let the main rendering pipeline
        handle the preview just like any other object.

        Args:
            scene: Scene to add preview model to
        """
        if not self.visible:
            return

        if self.model is None and self.scene_object is None:
            return

        # Temporarily add preview to scene with modified alpha/color
        if self.model:
            # Add model to scene with reduced alpha for transparency
            self.model.position = Vector3(self.position)
            self.model.rotation = self.rotation
            self.model.scale = Vector3(self.scale)

            # Determine tint color based on validity
            if self.is_valid:
                tint_color = Vector3([0.2, 1.0, 0.2])  # Green for valid
            else:
                tint_color = Vector3([1.0, 0.2, 0.2])  # Red for invalid

            # Store original colors to restore later
            original_colors = []
            for mesh in self.model.meshes:
                if hasattr(mesh.material, 'base_color_factor'):
                    original_colors.append(mesh.material.base_color_factor)
                    # Multiply the base color by the tint color
                    current_color = mesh.material.base_color_factor
                    tinted = Vector3([
                        current_color[0] * tint_color[0],
                        current_color[1] * tint_color[1],
                        current_color[2] * tint_color[2]
                    ])
                    # Keep alpha at 0.5 for semi-transparency
                    mesh.material.base_color_factor = (tinted[0], tinted[1], tinted[2], 0.5)

                    # Store the original color for restoration
                    self._original_colors = original_colors
                else:
                    original_colors.append(None)

                # Set alpha mode to BLEND for transparency
                if hasattr(mesh.material, 'alpha_mode'):
                    mesh.material.alpha_mode = 2  # BLEND mode

            # Add to scene (caller will render and then remove)
            scene.add_object(self.model)

        elif self.scene_object:
            # For primitives, modify color
            if self.is_valid:
                self.scene_object.color = (0.2, 1.0, 0.2)  # Green
            else:
                self.scene_object.color = (1.0, 0.2, 0.2)  # Red

            # Add to scene
            scene.add_object(self.scene_object)

    def remove_from_scene(self, scene: "Scene"):
        """
        Remove preview model from scene after rendering.

        Args:
            scene: Scene to remove preview model from
        """
        if self.model:
            # Restore original colors before removing
            if hasattr(self, '_original_colors'):
                for i, mesh in enumerate(self.model.meshes):
                    if i < len(self._original_colors) and self._original_colors[i] is not None:
                        if hasattr(mesh.material, 'base_color_factor'):
                            mesh.material.base_color_factor = self._original_colors[i]

            if self.model in scene.objects:
                scene.objects.remove(self.model)

        elif self.scene_object:
            if self.scene_object in scene.objects:
                scene.objects.remove(self.scene_object)

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
