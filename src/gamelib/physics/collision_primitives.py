"""Reusable collision mesh generators for primitive shapes."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Sequence, Tuple


def _write_obj(path: Path, vertices: Sequence[Iterable[float]], faces: Sequence[Tuple[int, int, int]]) -> None:
    """Write a simple OBJ file containing only vertices and triangle faces."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii") as handle:
        handle.write("# Auto-generated collision mesh\n")
        handle.write(f"# Vertices: {len(vertices)}\n")
        handle.write(f"# Faces: {len(faces)}\n")
        for vx, vy, vz in vertices:
            handle.write(f"v {vx:.6f} {vy:.6f} {vz:.6f}\n")
        for a, b, c in faces:
            handle.write(f"f {a} {b} {c}\n")


def export_cone_collision(
    out_path: Path,
    *,
    segments: int = 32,
) -> None:
    """
    Generate a unit cone collision mesh aligned on the Y axis.

    The resulting mesh has its apex at y=1 and base radius of 1 at y=0,
    intended to be scaled by PyBullet's meshScale parameter.
    """

    if segments < 3:
        raise ValueError("Cone collision mesh requires at least 3 segments")

    vertices = [(0.0, 1.0, 0.0)]  # Apex

    # Base ring vertices
    for index in range(segments):
        angle = 2.0 * math.pi * index / segments
        x = math.cos(angle)
        z = math.sin(angle)
        vertices.append((x, 0.0, z))

    # Base centre
    vertices.append((0.0, 0.0, 0.0))

    apex_idx = 1  # OBJ indexing (1-based)
    base_start = 2
    base_center = len(vertices)

    faces: list[Tuple[int, int, int]] = []

    # Side faces
    for index in range(segments):
        next_index = (index + 1) % segments
        v_current = base_start + index
        v_next = base_start + next_index
        faces.append((apex_idx, v_current, v_next))

    # Base faces (fan)
    for index in range(segments):
        next_index = (index + 1) % segments
        v_current = base_start + index
        v_next = base_start + next_index
        faces.append((base_center, v_next, v_current))

    _write_obj(out_path, vertices, faces)
