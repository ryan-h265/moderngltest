"""
Frustum Culling

Extracts view frustum planes from camera projection matrix.
Used for culling lights outside camera view.
"""

import numpy as np
from pyrr import Vector3, Matrix44


class Frustum:
    """
    View frustum defined by 6 planes.

    Planes are extracted from view-projection matrix.
    Used for visibility culling (lights, objects outside view).
    """

    def __init__(self, view_projection_matrix: Matrix44):
        """
        Extract frustum planes from view-projection matrix.

        Args:
            view_projection_matrix: Combined projection * view matrix
        """
        self.planes = self._extract_planes(view_projection_matrix)

    def _extract_planes(self, vp: Matrix44) -> list:
        """
        Extract 6 frustum planes from view-projection matrix.

        Plane format: [A, B, C, D] where Ax + By + Cz + D = 0
        Planes: left, right, bottom, top, near, far

        Args:
            vp: View-projection matrix

        Returns:
            List of 6 plane equations [A, B, C, D]
        """
        # Convert to numpy and transpose to get row-major format
        # pyrr matrices are column-major, but plane extraction uses rows
        m = np.array(vp, dtype='f4').T

        planes = []

        # Left plane: row3 + row0
        planes.append(self._normalize_plane(m[3] + m[0]))

        # Right plane: row3 - row0
        planes.append(self._normalize_plane(m[3] - m[0]))

        # Bottom plane: row3 + row1
        planes.append(self._normalize_plane(m[3] + m[1]))

        # Top plane: row3 - row1
        planes.append(self._normalize_plane(m[3] - m[1]))

        # Near plane: row3 + row2
        planes.append(self._normalize_plane(m[3] + m[2]))

        # Far plane: row3 - row2
        planes.append(self._normalize_plane(m[3] - m[2]))

        return planes

    def _normalize_plane(self, plane: np.ndarray) -> np.ndarray:
        """
        Normalize a plane equation.

        Args:
            plane: Plane coefficients [A, B, C, D]

        Returns:
            Normalized plane
        """
        length = np.linalg.norm(plane[:3])
        if length > 0:
            return plane / length
        return plane

    def contains_sphere(self, center: Vector3, radius: float) -> bool:
        """
        Test if a sphere is inside or intersects the frustum.

        Args:
            center: Sphere center position
            radius: Sphere radius

        Returns:
            True if sphere is visible (inside or intersecting frustum)
        """
        # Convert Vector3 to numpy array
        center_arr = np.array([center.x, center.y, center.z], dtype='f4')

        # Test against all 6 planes
        for plane in self.planes:
            # Distance from plane to sphere center
            # plane = [A, B, C, D], distance = Ax + By + Cz + D
            distance = (
                plane[0] * center_arr[0] +
                plane[1] * center_arr[1] +
                plane[2] * center_arr[2] +
                plane[3]
            )

            # If sphere is completely behind any plane, it's outside
            if distance < -radius:
                return False

        # Sphere is inside or intersecting frustum
        return True

    def contains_point(self, point: Vector3) -> bool:
        """
        Test if a point is inside the frustum.

        Args:
            point: Point position

        Returns:
            True if point is inside frustum
        """
        return self.contains_sphere(point, 0.0)
