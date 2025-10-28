#!/usr/bin/env python3
"""
Generate a test heightmap with flat plane and multiple inclines of increasing steepness.

This creates a terrain with:
- A flat starting area
- Multiple ramp sections with increasing angles (10°, 20°, 30°, 40°, 50°)
- Flat landing areas between ramps for testing
"""

import numpy as np
import json
from pathlib import Path

# Configuration
RESOLUTION = 256  # Grid resolution (256x256 vertices)
WORLD_SIZE = 400.0  # Total world size in units
RAMP_LENGTH = 50.0  # Length of each ramp section
FLAT_LENGTH = 30.0  # Length of flat areas between ramps
START_FLAT = 40.0  # Initial flat area length

# Incline angles in degrees
INCLINE_ANGLES = [10, 20, 30, 40, 50]

# Output paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "assets" / "heightmaps"
OUTPUT_PATH = OUTPUT_DIR / "incline_test.npz"


def generate_incline_heightmap():
    """Generate heightmap with progressive inclines."""

    # Initialize flat heightmap
    heights = np.zeros((RESOLUTION, RESOLUTION), dtype=np.float32)

    # Calculate grid spacing
    dx = WORLD_SIZE / (RESOLUTION - 1)

    # Build height profile along X axis (left to right)
    # We'll apply this profile to all Z rows

    current_x = 0.0  # Current position in world units
    current_height = 0.0  # Current height

    height_profile = np.zeros(RESOLUTION, dtype=np.float32)

    # Starting flat area
    start_end = START_FLAT

    for i in range(RESOLUTION):
        world_x = (i * dx) - (WORLD_SIZE / 2.0)

        if world_x < -WORLD_SIZE/2 + START_FLAT:
            # Initial flat area
            height_profile[i] = 0.0
            current_height = 0.0
            current_x = world_x
        else:
            # Determine which section we're in
            section_start = -WORLD_SIZE/2 + START_FLAT
            section_x = world_x - section_start

            # Calculate which ramp/flat we're on
            section_length = RAMP_LENGTH + FLAT_LENGTH
            total_sections = len(INCLINE_ANGLES)

            # Find current section
            ramp_idx = 0
            accumulated_distance = 0.0
            found = False

            for ramp_idx in range(total_sections):
                # Check if we're on this ramp
                ramp_start = accumulated_distance
                ramp_end = ramp_start + RAMP_LENGTH

                if section_x >= ramp_start and section_x < ramp_end:
                    # On a ramp
                    ramp_progress = (section_x - ramp_start) / RAMP_LENGTH
                    angle_rad = np.radians(INCLINE_ANGLES[ramp_idx])
                    ramp_height = RAMP_LENGTH * np.tan(angle_rad) * ramp_progress

                    # Calculate base height (sum of previous ramps)
                    base_height = 0.0
                    for j in range(ramp_idx):
                        base_height += RAMP_LENGTH * np.tan(np.radians(INCLINE_ANGLES[j]))

                    height_profile[i] = base_height + ramp_height
                    found = True
                    break

                # Check if we're on the flat after this ramp
                flat_start = ramp_end
                flat_end = flat_start + FLAT_LENGTH

                if section_x >= flat_start and section_x < flat_end:
                    # On a flat section
                    # Height is the top of the current ramp
                    base_height = 0.0
                    for j in range(ramp_idx + 1):
                        base_height += RAMP_LENGTH * np.tan(np.radians(INCLINE_ANGLES[j]))

                    height_profile[i] = base_height
                    found = True
                    break

                accumulated_distance += section_length

            if not found:
                # Past all ramps, stay at final height
                final_height = 0.0
                for j in range(len(INCLINE_ANGLES)):
                    final_height += RAMP_LENGTH * np.tan(np.radians(INCLINE_ANGLES[j]))
                height_profile[i] = final_height

    # Apply profile to all rows (constant across Z)
    for i in range(RESOLUTION):
        for j in range(RESOLUTION):
            heights[i, j] = height_profile[i]

    return heights


def main():
    """Generate and save the incline test heightmap."""

    print("Generating incline test heightmap...")
    print(f"  Resolution: {RESOLUTION}x{RESOLUTION}")
    print(f"  World size: {WORLD_SIZE}")
    print(f"  Incline angles: {INCLINE_ANGLES}°")

    # Generate heightmap
    heights = generate_incline_heightmap()

    # Calculate statistics
    min_height = np.min(heights)
    max_height = np.max(heights)

    print(f"\nHeightmap statistics:")
    print(f"  Min height: {min_height:.2f}")
    print(f"  Max height: {max_height:.2f}")
    print(f"  Height range: {max_height - min_height:.2f}")

    # Create metadata
    metadata = {
        "resolution": RESOLUTION,
        "world_size": WORLD_SIZE,
        "preset": "incline_test",
        "description": "Test terrain with progressive inclines",
        "incline_angles": INCLINE_ANGLES,
        "ramp_length": RAMP_LENGTH,
        "flat_length": FLAT_LENGTH,
        "start_flat": START_FLAT,
    }

    # Save heightmap
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUTPUT_PATH,
        heights=heights,
        meta=json.dumps(metadata)
    )

    print(f"\nHeightmap saved to: {OUTPUT_PATH}")
    print(f"  File size: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")

    return OUTPUT_PATH


if __name__ == "__main__":
    main()
