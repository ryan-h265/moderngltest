"""
Object Selector - Raycasting and Object Selection

Handles clicking on 3D objects in the scene to select them for editing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple
import math

from pyrr import Vector3

if TYPE_CHECKING:
    from ..core.camera import Camera
    from ..core.scene import SceneObject, Scene


class ObjectSelector:
    """Handles raycasting and object selection in the editor."""

    def __init__(self, raycast_range: float = 1000.0):
        """
        Initialize object selector.

        Args:
            raycast_range: Maximum distance for raycasting
        """
        self.raycast_range = raycast_range
        self.selected_object: Optional[SceneObject] = None

    def select_from_screen_position(
        self,
        camera: Camera,
        scene: Scene,
        screen_x: float,
        screen_y: float,
        screen_width: int,
        screen_height: int,
    ) -> Optional[SceneObject]:
        """
        Select object from screen position using raycasting.

        Args:
            camera: Camera for raycasting
            scene: Scene containing objects
            screen_x: Screen X coordinate (0 = left)
            screen_y: Screen Y coordinate (0 = top)
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels

        Returns:
            Selected SceneObject or None
        """
        # Convert screen coordinates to normalized device coordinates
        ndc_x = (2.0 * screen_x) / screen_width - 1.0
        ndc_y = 1.0 - (2.0 * screen_y) / screen_height

        # Get ray from camera through screen position
        ray_origin = camera.position
        ray_direction = self._get_ray_direction(camera, ndc_x, ndc_y)

        # Find closest object along ray
        closest_object = None
        closest_distance = float('inf')

        if hasattr(scene, 'objects') and scene.objects:
            for obj in scene.objects:
                # Skip invisible objects
                if hasattr(obj, 'visible') and not obj.visible:
                    continue

                distance = self._raycast_sphere(
                    ray_origin,
                    ray_direction,
                    obj.position,
                    obj.bounding_radius if hasattr(obj, 'bounding_radius') else 1.0
                )

                if distance is not None and distance < closest_distance:
                    closest_distance = distance
                    closest_object = obj

        self.selected_object = closest_object
        return closest_object

    def _get_ray_direction(
        self,
        camera: Camera,
        ndc_x: float,
        ndc_y: float,
    ) -> Vector3:
        """
        Get ray direction from camera through normalized device coordinates.

        Args:
            camera: Camera
            ndc_x: Normalized device coordinate X (-1 to 1)
            ndc_y: Normalized device coordinate Y (-1 to 1)

        Returns:
            Ray direction vector
        """
        # Get camera forward (front), right, and up vectors
        forward = camera.front
        right = camera.right
        up = camera.up

        # Camera field of view (default 45 degrees)
        fov_rad = math.radians(45.0)
        aspect = 16.0 / 9.0  # Default aspect ratio

        # Calculate ray direction based on NDC coordinates
        tan_half_fov = math.tan(fov_rad / 2.0)

        ray_dir = (
            forward +
            right * ndc_x * tan_half_fov * aspect +
            up * ndc_y * tan_half_fov
        )

        # Normalize
        ray_length = math.sqrt(
            ray_dir.x * ray_dir.x +
            ray_dir.y * ray_dir.y +
            ray_dir.z * ray_dir.z
        )

        if ray_length > 0:
            ray_dir = Vector3([
                ray_dir.x / ray_length,
                ray_dir.y / ray_length,
                ray_dir.z / ray_length,
            ])

        return ray_dir

    def _raycast_sphere(
        self,
        ray_origin: Vector3,
        ray_direction: Vector3,
        sphere_center: Vector3,
        sphere_radius: float,
    ) -> Optional[float]:
        """
        Test ray intersection with sphere using geometric method.

        Args:
            ray_origin: Ray starting point
            ray_direction: Ray direction (normalized)
            sphere_center: Sphere center position
            sphere_radius: Sphere radius

        Returns:
            Distance to intersection or None if no hit
        """
        # Vector from ray origin to sphere center
        oc = sphere_center - ray_origin

        # Project oc onto ray direction
        t = oc.dot(ray_direction)

        # If t is negative, sphere is behind ray
        if t < 0:
            return None

        # Closest point on ray to sphere center
        closest_point = ray_origin + ray_direction * t

        # Distance from closest point to sphere center
        distance_to_center = (sphere_center - closest_point).magnitude

        # Check if ray intersects sphere
        if distance_to_center > sphere_radius:
            return None

        # Calculate intersection distance
        # Distance to nearest intersection point
        inside_sphere_distance = math.sqrt(
            sphere_radius * sphere_radius -
            distance_to_center * distance_to_center
        )

        intersection_distance = t - inside_sphere_distance

        # Only return if intersection is positive and within raycast range
        if intersection_distance >= 0 and intersection_distance <= self.raycast_range:
            return intersection_distance

        return None

    def get_selected_object(self) -> Optional[SceneObject]:
        """
        Get currently selected object.

        Returns:
            Selected SceneObject or None
        """
        return self.selected_object

    def deselect(self) -> None:
        """Deselect current object."""
        self.selected_object = None
