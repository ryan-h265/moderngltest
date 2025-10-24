"""
Skeleton

Represents a hierarchical skeleton structure with joints/bones.
"""

from typing import List, Optional, Dict
from pyrr import Matrix44, Vector3, Quaternion
import numpy as np


class Joint:
    """
    Represents a single joint (bone) in a skeleton hierarchy.

    Each joint has:
    - Local transform (relative to parent)
    - World transform (absolute position in world space)
    - Parent-child relationships
    """

    def __init__(
        self,
        name: str,
        index: int,
        parent: Optional['Joint'] = None
    ):
        """
        Initialize a joint.

        Args:
            name: Joint name (for debugging)
            index: Joint index in skeleton
            parent: Parent joint (None for root)
        """
        self.name = name
        self.index = index
        self.parent = parent
        self.children: List['Joint'] = []

        # Local transform (relative to parent)
        self.local_transform = Matrix44.identity()

        # World transform (absolute, computed from hierarchy)
        self.world_transform = Matrix44.identity()

        # Animated transform (overrides local_transform during animation)
        self.animated_transform: Optional[Matrix44] = None

        # Bind pose defaults used when animation channels omit components
        self.base_translation = Vector3([0.0, 0.0, 0.0])
        self.base_rotation = Quaternion([1.0, 0.0, 0.0, 0.0])
        self.base_scale = Vector3([1.0, 1.0, 1.0])

    def add_child(self, child: 'Joint'):
        """Add a child joint to this joint's hierarchy."""
        self.children.append(child)
        child.parent = self

    def get_animated_local_transform(self) -> Matrix44:
        """Get the current local transform (animated or bind pose)."""
        if self.animated_transform is not None:
            return self.animated_transform
        return self.local_transform

    def __repr__(self):
        return f"Joint(name='{self.name}', index={self.index}, children={len(self.children)})"


class Skeleton:
    """
    Hierarchical skeleton structure.

    Manages the joint hierarchy and provides utilities for:
    - Building skeletons from GLTF data
    - Updating world transforms from local transforms
    - Finding joints by name/index
    """

    def __init__(self, name: str = "Skeleton"):
        """
        Initialize skeleton.

        Args:
            name: Skeleton name for debugging
        """
        self.name = name
        self.joints: List[Joint] = []
        self.root_joints: List[Joint] = []
        self.joint_by_name: Dict[str, Joint] = {}

    def add_joint(self, joint: Joint):
        """
        Add a joint to the skeleton.

        Args:
            joint: Joint to add
        """
        self.joints.append(joint)
        self.joint_by_name[joint.name] = joint

        # If joint has no parent, it's a root joint
        if joint.parent is None:
            self.root_joints.append(joint)

    def get_joint(self, name: str) -> Optional[Joint]:
        """
        Find a joint by name.

        Args:
            name: Joint name

        Returns:
            Joint if found, None otherwise
        """
        return self.joint_by_name.get(name)

    def update_world_transforms(self):
        """
        Update all world transforms from local transforms.

        This recursively walks the hierarchy starting from root joints
        and computes world_transform = local_transform @ parent_world
        (row-major form; equivalent to parent * local in column-major).

        Call this after updating animated transforms.
        """
        for root in self.root_joints:
            self._update_joint_recursive(root, Matrix44.identity())

    def _update_joint_recursive(self, joint: Joint, parent_world: Matrix44):
        """
        Recursively update joint world transforms.

        Args:
            joint: Current joint to update
            parent_world: Parent's world transform
        """
        # Get local transform (animated or bind pose)
        local = joint.get_animated_local_transform()

        # Compute world transform: world = parent_world * local
        joint.world_transform = local @ parent_world

        # Recurse to children
        for child in joint.children:
            self._update_joint_recursive(child, joint.world_transform)

    def reset_animation(self):
        """Reset all joints to bind pose (clear animated transforms)."""
        for joint in self.joints:
            joint.animated_transform = None

    def __repr__(self):
        return f"Skeleton(name='{self.name}', joints={len(self.joints)}, roots={len(self.root_joints)})"
