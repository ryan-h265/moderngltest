#!/usr/bin/env python3
"""
Check shadow map resolutions assigned to lights.

Shows the adaptive resolution system in action.
"""

import numpy as np
from pyrr import Vector3
from src.gamelib.core.light import Light
from src.gamelib.config.settings import (
    SHADOW_MAP_SIZE_LOW,
    SHADOW_MAP_SIZE_MED,
    SHADOW_MAP_SIZE_HIGH,
)

def calculate_importance(light, camera_pos):
    """Calculate light importance score"""
    distance = np.linalg.norm(light.position - camera_pos)
    distance = max(distance, 0.1)
    importance = light.intensity / (distance * distance)
    return importance, distance

def main():
    # Simulate the same setup as main.py
    camera_pos = Vector3([0.0, 5.0, 10.0])

    # Create 3 lights like in main.py
    import math
    lights = []
    num_lights = 3

    for i in range(num_lights):
        angle = (i / num_lights) * 2 * math.pi
        radius = 12.0
        height = 8.0 + (i % 3) * 2.0

        x = radius * math.cos(angle)
        z = radius * math.sin(angle)

        hue = i / num_lights
        if hue < 1/3:
            color = Vector3([1.0 - 3*hue*0.5, 0.5 + 3*hue*0.5, 0.3])
        elif hue < 2/3:
            color = Vector3([0.3, 1.0 - 3*(hue-1/3)*0.5, 0.5 + 3*(hue-1/3)*0.5])
        else:
            color = Vector3([0.5 + 3*(hue-2/3)*0.5, 0.3, 1.0 - 3*(hue-2/3)*0.5])

        color = color / max(color)

        light = Light(
            position=Vector3([x, height, z]),
            target=Vector3([0.0, 0.0, 0.0]),
            color=color,
            intensity=0.3 + (i % 3) * 0.2,
            light_type='directional'
        )
        lights.append(light)

    print("=" * 80)
    print("SHADOW MAP RESOLUTION ASSIGNMENT")
    print("=" * 80)
    print(f"Camera position: {camera_pos}")
    print()
    print("Resolution Tiers:")
    print(f"  HIGH: {SHADOW_MAP_SIZE_HIGH}x{SHADOW_MAP_SIZE_HIGH} (importance > 0.01)")
    print(f"  MED:  {SHADOW_MAP_SIZE_MED}x{SHADOW_MAP_SIZE_MED}  (importance > 0.001)")
    print(f"  LOW:  {SHADOW_MAP_SIZE_LOW}x{SHADOW_MAP_SIZE_LOW}   (importance ≤ 0.001)")
    print()
    print("-" * 80)

    total_pixels_old = 0
    total_pixels_new = 0

    for i, light in enumerate(lights):
        importance, distance = calculate_importance(light, camera_pos)

        # Determine resolution tier
        if importance > 0.01:
            resolution = SHADOW_MAP_SIZE_HIGH
            tier = "HIGH"
        elif importance > 0.001:
            resolution = SHADOW_MAP_SIZE_MED
            tier = "MED"
        else:
            resolution = SHADOW_MAP_SIZE_LOW
            tier = "LOW"

        pixels = resolution * resolution
        total_pixels_old += SHADOW_MAP_SIZE_HIGH * SHADOW_MAP_SIZE_HIGH
        total_pixels_new += pixels

        print(f"Light {i}:")
        print(f"  Position: {light.position}")
        print(f"  Intensity: {light.intensity:.2f}")
        print(f"  Distance from camera: {distance:.2f} units")
        print(f"  Importance score: {importance:.6f}")
        print(f"  Resolution tier: {tier} ({resolution}x{resolution} = {pixels/1_000_000:.2f}M pixels)")
        print()

    print("-" * 80)
    print("PERFORMANCE IMPACT:")
    print(f"  Old (all HIGH): {total_pixels_old/1_000_000:.2f}M pixels/frame")
    print(f"  New (adaptive): {total_pixels_new/1_000_000:.2f}M pixels/frame")
    reduction = (1 - total_pixels_new/total_pixels_old) * 100
    print(f"  Reduction: {reduction:.1f}%")
    print("=" * 80)

if __name__ == "__main__":
    main()
