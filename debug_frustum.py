#!/usr/bin/env python3
"""
Debug script for frustum culling.

Run this to test frustum culling with a specific camera position/orientation.
"""

import numpy as np
from pyrr import Vector3, Matrix44
from src.gamelib.core.camera import Camera
from src.gamelib.core.frustum import Frustum

def test_frustum_culling():
    """Test frustum culling with test positions"""

    # Test objects with known positions
    test_objects = [
        ("Center", Vector3([0.0, 0.0, 0.0]), 1.0),
        ("Front", Vector3([0.0, 0.0, -5.0]), 1.0),
        ("Behind Camera", Vector3([0.0, 5.0, 15.0]), 1.0),
        ("Far Behind", Vector3([0.0, 0.0, 50.0]), 1.0),
        ("Left", Vector3([-5.0, 0.0, 0.0]), 1.0),
        ("Right", Vector3([5.0, 0.0, 0.0]), 1.0),
        ("Far Away", Vector3([0.0, 0.0, -50.0]), 1.0),
        ("Way Left", Vector3([-50.0, 0.0, 0.0]), 1.0),
    ]

    # Create camera looking down -Z axis
    camera = Camera(
        position=Vector3([0.0, 5.0, 10.0]),
        target=Vector3([0.0, 0.0, 0.0])
    )

    print(f"Camera position: {camera.position}")
    print(f"Camera target: {camera.target}")
    print(f"Camera front: {camera._front}")
    print()

    # Get frustum
    aspect_ratio = 16.0 / 9.0
    frustum = camera.get_frustum(aspect_ratio)

    print("Testing object visibility:")
    print("-" * 80)

    for name, pos, radius in test_objects:
        is_visible = frustum.contains_sphere(pos, radius)
        status = "VISIBLE" if is_visible else "CULLED"
        print(f"{name:20s} at {str(pos):35s} radius={radius:5.2f}  [{status}]")

    print()
    print("View-Projection Matrix:")
    print("-" * 80)
    view_proj = camera.get_projection_matrix(aspect_ratio) @ camera.get_view_matrix()
    print(view_proj)

    print()
    print("Frustum plane details:")
    print("-" * 80)
    plane_names = ["Left", "Right", "Bottom", "Top", "Near", "Far"]
    for i, (name, plane) in enumerate(zip(plane_names, frustum.planes)):
        print(f"{name:10s}: [{plane[0]:7.3f}, {plane[1]:7.3f}, {plane[2]:7.3f}, {plane[3]:7.3f}]")

    print()
    print("=== Manual test of specific object ===")
    # Test the ground object specifically
    ground_pos = Vector3([0.0, -0.25, 0.0])
    ground_radius = 14.15
    is_visible = frustum.contains_sphere(ground_pos, ground_radius)
    print(f"Ground at {ground_pos} with radius {ground_radius}: {'VISIBLE' if is_visible else 'CULLED'}")

    # Check each plane distance
    print("\nGround distance from each plane:")
    for name, plane in zip(plane_names, frustum.planes):
        distance = (
            plane[0] * ground_pos.x +
            plane[1] * ground_pos.y +
            plane[2] * ground_pos.z +
            plane[3]
        )
        behind = distance < -ground_radius
        print(f"  {name:10s}: distance={distance:8.3f}, behind={behind}")

if __name__ == "__main__":
    test_frustum_culling()
