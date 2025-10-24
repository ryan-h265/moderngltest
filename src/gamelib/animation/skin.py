"""
Skin

Handles skinning data for skeletal animation.
"""

from typing import List
from pyrr import Matrix44
import numpy as np
from .skeleton import Skeleton, Joint


class Skin:
    """
    Skin binds a skeleton to a mesh.

    Contains:
    - List of joints that influence the mesh
    - Inverse bind matrices (transform from world space to joint's local space)
    - Joint matrices (computed during animation for shader upload)
    """

    def __init__(self, name: str = "Skin"):
        """
        Initialize skin.

        Args:
            name: Skin name for debugging
        """
        self.name = name
        self.joints: List[Joint] = []
        self.inverse_bind_matrices: List[Matrix44] = []
        self.joint_matrices: List[Matrix44] = []  # Computed for shader

    def add_joint(self, joint: Joint, inverse_bind_matrix: Matrix44):
        """
        Add a joint to the skin.

        Args:
            joint: Joint that influences this skin
            inverse_bind_matrix: Transforms from mesh space to joint's local space
        """
        self.joints.append(joint)
        self.inverse_bind_matrices.append(inverse_bind_matrix)

    def update_joint_matrices(self):
        """
        Compute joint matrices for shader upload.

        Joint matrix formula:
        jointMatrix = jointWorldTransform * inverseBindMatrix

        This transforms vertices from bind pose to current animated pose.
        """
        self.joint_matrices = []
        for i, joint in enumerate(self.joints):
            # Get inverse bind matrix for this joint
            inv_bind = self.inverse_bind_matrices[i]

            # Get current world transform (animated)
            world_transform = joint.world_transform

            # Compute final joint matrix
            joint_matrix = world_transform @ inv_bind

            self.joint_matrices.append(joint_matrix)

    def get_joint_matrices_array(self) -> np.ndarray:
        """
        Get joint matrices as a numpy array for shader upload.

        Returns:
            Numpy array of shape (num_joints, 4, 4) with dtype float32
        """
        if not self.joint_matrices:
            return np.array([], dtype='f4')

        # Stack matrices into array
        matrices = np.array([m.astype('f4') for m in self.joint_matrices], dtype='f4')
        return matrices

    def __repr__(self):
        return f"Skin(name='{self.name}', joints={len(self.joints)})"
