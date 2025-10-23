"""
Texture Transform

Represents KHR_texture_transform extension for GLTF 2.0.
Allows textures to be offset, scaled, and rotated via UV coordinate transformations.
"""

import numpy as np
from typing import Tuple


class TextureTransform:
    """
    Texture coordinate transformation (KHR_texture_transform).

    Stores offset, scale, rotation, and computes the resulting 3x3 transformation matrix.
    The matrix is applied to UV coordinates in the shader as: uv' = (transform * vec3(uv, 1.0)).xy

    GLTF Spec: https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_texture_transform
    """

    def __init__(
        self,
        offset: Tuple[float, float] = (0.0, 0.0),
        scale: Tuple[float, float] = (1.0, 1.0),
        rotation: float = 0.0,
        texcoord: int = 0
    ):
        """
        Initialize texture transform.

        Args:
            offset: Translation offset (U, V) - default (0, 0)
            scale: Scale factors (U, V) - default (1, 1)
            rotation: Rotation in radians (counter-clockwise) - default 0
            texcoord: Texture coordinate set index - default 0
        """
        self.offset = np.array(offset, dtype='f4')
        self.scale = np.array(scale, dtype='f4')
        self.rotation = rotation
        self.texcoord = texcoord

        # Compute transformation matrix
        self._update_matrix()

    def _update_matrix(self):
        """
        Compute the 3x3 transformation matrix from offset, scale, rotation.

        Order of operations (as per GLTF spec):
        1. Scale
        2. Rotate (around origin)
        3. Translate (offset)

        Matrix form:
        [ cos(r)*sx  -sin(r)*sy  ox ]
        [ sin(r)*sx   cos(r)*sy  oy ]
        [     0           0       1 ]

        Where:
        - sx, sy = scale.x, scale.y
        - r = rotation (radians)
        - ox, oy = offset.x, offset.y
        """
        c = np.cos(self.rotation)
        s = np.sin(self.rotation)
        sx, sy = self.scale
        ox, oy = self.offset

        # Build 3x3 transformation matrix (column-major for OpenGL)
        self.matrix = np.array([
            [c * sx, s * sx, 0.0],
            [-s * sy, c * sy, 0.0],
            [ox, oy, 1.0]
        ], dtype='f4')

    def get_matrix(self) -> np.ndarray:
        """
        Get the 3x3 transformation matrix.

        Returns:
            3x3 numpy array (column-major, ready for OpenGL)
        """
        return self.matrix

    def update(
        self,
        offset: Tuple[float, float] = None,
        scale: Tuple[float, float] = None,
        rotation: float = None
    ):
        """
        Update transformation parameters and recompute matrix.

        Args:
            offset: New offset (if provided)
            scale: New scale (if provided)
            rotation: New rotation (if provided)
        """
        if offset is not None:
            self.offset = np.array(offset, dtype='f4')
        if scale is not None:
            self.scale = np.array(scale, dtype='f4')
        if rotation is not None:
            self.rotation = rotation

        self._update_matrix()

    @staticmethod
    def identity() -> 'TextureTransform':
        """
        Create an identity transform (no transformation).

        Returns:
            TextureTransform with default values
        """
        return TextureTransform()

    def __repr__(self):
        return (f"TextureTransform(offset={tuple(self.offset)}, "
                f"scale={tuple(self.scale)}, rotation={self.rotation:.3f})")
