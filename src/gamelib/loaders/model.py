"""
Model

Represents a loaded GLTF/GLB model with meshes and materials.
"""

from typing import List, Tuple, Optional
from pyrr import Matrix44, Vector3
from .material import Material


class Mesh:
    """
    Represents a single mesh within a model.

    Each mesh has its own VAO and material.
    """

    def __init__(self, vao, material: Material, name: str = "Mesh"):
        """
        Initialize mesh.

        Args:
            vao: ModernGL VAO object
            material: Material for this mesh
            name: Mesh name for debugging
        """
        self.vao = vao
        self.material = material
        self.name = name
        self.vertex_count = 0  # Set by loader

    def render(self, program):
        """
        Render this mesh.

        Args:
            program: Shader program to use
        """
        # Bind material textures
        self.material.bind_textures(program)

        # Render geometry
        self.vao.render(program)


class Model:
    """
    Represents a complete GLTF/GLB model with multiple meshes.

    Compatible with SceneObject interface for rendering in Scene.
    """

    def __init__(self, meshes: List[Mesh], position: Vector3 = None,
                 rotation: Vector3 = None, scale: Vector3 = None,
                 name: str = "Model"):
        """
        Initialize model.

        Args:
            meshes: List of Mesh objects
            position: World space position (default: origin)
            rotation: Rotation in radians (yaw, pitch, roll)
            scale: Scale factors (default: uniform 1.0)
            name: Model name for debugging
        """
        self.meshes = meshes
        self.position = position if position is not None else Vector3([0.0, 0.0, 0.0])
        self.rotation = rotation if rotation is not None else Vector3([0.0, 0.0, 0.0])
        self.scale = scale if scale is not None else Vector3([1.0, 1.0, 1.0])
        self.name = name

        # For frustum culling (SceneObject compatibility)
        self.bounding_radius = 2.0  # Default, should be calculated from model bounds

        # Flag to identify this as a Model (not a primitive SceneObject)
        self.is_model = True

    def get_model_matrix(self) -> Matrix44:
        """
        Get the model transformation matrix.

        Returns:
            4x4 transformation matrix
        """
        # Start with translation
        matrix = Matrix44.from_translation(self.position)

        # Apply rotation (yaw, pitch, roll)
        if self.rotation.x != 0.0:
            matrix = matrix * Matrix44.from_y_rotation(self.rotation.x)
        if self.rotation.y != 0.0:
            matrix = matrix * Matrix44.from_x_rotation(self.rotation.y)
        if self.rotation.z != 0.0:
            matrix = matrix * Matrix44.from_z_rotation(self.rotation.z)

        # Apply scale
        if self.scale != Vector3([1.0, 1.0, 1.0]):
            matrix = matrix * Matrix44.from_scale(self.scale)

        return matrix

    def is_visible(self, frustum) -> bool:
        """
        Test if this model is visible in the given frustum.

        Args:
            frustum: View frustum to test against

        Returns:
            True if model is visible
        """
        return frustum.contains_sphere(self.position, self.bounding_radius)

    def render(self, program):
        """
        Render all meshes in this model.

        Args:
            program: Shader program to use
        """
        # Set model matrix once for all meshes
        model_matrix = self.get_model_matrix()
        if 'model' in program:
            program['model'].write(model_matrix.astype('f4').tobytes())

        # Render each mesh
        for mesh in self.meshes:
            mesh.render(program)

    def release(self):
        """Release GPU resources"""
        for mesh in self.meshes:
            mesh.vao.release()
            mesh.material.release()
