#!/usr/bin/env python3
"""
Generate collision meshes for complex scene assets.

Creates OBJ files under ``assets/collision`` for:
* Donut terrain (heightfield mesh)
* GLTF-based props that should participate in physics
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import struct
from pathlib import Path
import sys
from typing import Dict, Iterable, Iterator, List, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
COLLISION_DIR = ASSETS / "collision"

SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# GLTF helpers -----------------------------------------------------------------

COMPONENT_INFO: Dict[int, Tuple[str, int]] = {
    5120: ("b", 1),   # BYTE
    5121: ("B", 1),   # UNSIGNED_BYTE
    5122: ("h", 2),   # SHORT
    5123: ("H", 2),   # UNSIGNED_SHORT
    5125: ("I", 4),   # UNSIGNED_INT
    5126: ("f", 4),   # FLOAT
}

TYPE_COMPONENTS: Dict[str, int] = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT4": 16,
}


def _ensure_collision_dir() -> None:
    COLLISION_DIR.mkdir(parents=True, exist_ok=True)


def _write_obj(path: Path, vertices: Sequence[Iterable[float]], faces: Sequence[Iterable[int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii") as handle:
        handle.write("# Generated collision mesh\n")
        handle.write(f"# Vertices: {len(vertices)}\n")
        handle.write(f"# Faces: {len(faces)}\n")
        for vx, vy, vz in vertices:
            handle.write(f"v {vx:.6f} {vy:.6f} {vz:.6f}\n")
        for a, b, c in faces:
            handle.write(f"f {a} {b} {c}\n")


# Donut terrain -----------------------------------------------------------------

def export_donut_collision(
    out_path: Path,
    *,
    resolution: int = 128,
    outer_radius: float = 200.0,
    inner_radius: float = 80.0,
    height: float = 50.0,
    rim_width: float = 40.0,
    seed: int = 42,
) -> None:
    """Export the procedurally generated donut terrain to an OBJ mesh."""

    from gamelib.core.terrain_generation import generate_donut_height_data

    heights = generate_donut_height_data(
        resolution=resolution,
        outer_radius=outer_radius,
        inner_radius=inner_radius,
        height=height,
        rim_width=rim_width,
        seed=seed,
    )

    world_size = outer_radius * 2.2
    spacing = world_size / (resolution - 1)
    offset = world_size / 2

    vertices: List[Tuple[float, float, float]] = []
    for x in range(resolution):
        for z in range(resolution):
            world_x = (x * spacing) - offset
            world_z = (z * spacing) - offset
            world_y = float(heights[x][z])
            vertices.append((world_x, world_y, world_z))

    faces: List[Tuple[int, int, int]] = []
    for x in range(resolution - 1):
        for z in range(resolution - 1):
            top_left = x * resolution + z
            top_right = (x + 1) * resolution + z
            bottom_left = x * resolution + (z + 1)
            bottom_right = (x + 1) * resolution + (z + 1)

            faces.append((
                top_left + 1,
                bottom_left + 1,
                top_right + 1,
            ))
            faces.append((
                top_right + 1,
                bottom_left + 1,
                bottom_right + 1,
            ))

    _write_obj(out_path, vertices, faces)


# GLTF extraction ---------------------------------------------------------------

def _load_gltf(path: Path) -> Tuple[Dict, List[bytes]]:
    if path.suffix == ".gltf":
        data = json.loads(path.read_text(encoding="utf-8"))
        buffers: List[bytes] = []
        for buffer in data.get("buffers", []):
            uri = buffer.get("uri", "")
            if uri.startswith("data:"):
                header, _, payload = uri.partition(",")
                if ";base64" not in header:
                    raise ValueError(f"Unsupported inline buffer encoding: {header}")
                buffers.append(base64.b64decode(payload))
            else:
                buffer_path = (path.parent / uri).resolve()
                buffers.append(buffer_path.read_bytes())
        return data, buffers

    if path.suffix == ".glb":
        raw = path.read_bytes()
        if len(raw) < 12:
            raise ValueError("Invalid GLB file (too small)")
        magic, version, length = struct.unpack_from("<4sII", raw, 0)
        if magic != b"glTF":
            raise ValueError("Not a valid GLB (magic mismatch)")
        offset = 12
        json_chunk = None
        bin_chunks: List[bytes] = []
        while offset < length:
            chunk_length, chunk_type = struct.unpack_from("<II", raw, offset)
            offset += 8
            chunk_data = raw[offset : offset + chunk_length]
            offset += chunk_length
            if chunk_type == 0x4E4F534A:  # JSON
                json_chunk = chunk_data
            elif chunk_type == 0x004E4942:  # BIN
                bin_chunks.append(chunk_data)
        if json_chunk is None:
            raise ValueError("GLB file missing JSON chunk")
        data = json.loads(json_chunk.decode("utf-8"))
        buffers = bin_chunks
        return data, buffers

    raise ValueError(f"Unsupported GLTF extension: {path.suffix}")


def _read_accessor(data: Dict, buffers: List[bytes], accessor_index: int) -> np.ndarray:
    accessor = data["accessors"][accessor_index]
    buffer_view = data["bufferViews"][accessor["bufferView"]]

    fmt_char, comp_size = COMPONENT_INFO[accessor["componentType"]]
    components = TYPE_COMPONENTS[accessor["type"]]
    count = accessor["count"]
    stride = buffer_view.get("byteStride") or (comp_size * components)

    buffer_data = buffers[buffer_view["buffer"]]
    start = buffer_view.get("byteOffset", 0) + accessor.get("byteOffset", 0)

    dtype = np.dtype(f"<{fmt_char}")
    raw = np.frombuffer(buffer_data, dtype=dtype, count=(stride // comp_size) * count, offset=start)
    raw = raw.reshape((count, stride // comp_size))[:, :components]
    return raw.astype(np.float32, copy=False)


def _traverse_nodes(data: Dict) -> List[Tuple[int, np.ndarray]]:
    def compose_matrix(node: Dict) -> np.ndarray:
        if "matrix" in node:
            return np.array(node["matrix"], dtype=np.float32).reshape(4, 4)

        translation = np.array(node.get("translation", [0.0, 0.0, 0.0]), dtype=np.float32)
        scale = np.array(node.get("scale", [1.0, 1.0, 1.0]), dtype=np.float32)
        rotation = np.array(node.get("rotation", [0.0, 0.0, 0.0, 1.0]), dtype=np.float32)

        tx, ty, tz = translation
        sx, sy, sz = scale
        x, y, z, w = rotation

        # Rotation matrix from quaternion
        rot = np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w),     2 * (x * z + y * w),     0.0],
            [2 * (x * y + z * w),     1 - 2 * (x * x + z * z), 2 * (y * z - x * w),     0.0],
            [2 * (x * z - y * w),     2 * (y * z + x * w),     1 - 2 * (x * x + y * y), 0.0],
            [0.0,                     0.0,                     0.0,                     1.0],
        ], dtype=np.float32)

        scale_m = np.diag([sx, sy, sz, 1.0]).astype(np.float32)
        trans_m = np.eye(4, dtype=np.float32)
        trans_m[:3, 3] = [tx, ty, tz]

        return trans_m @ rot @ scale_m

    world_mats: Dict[int, np.ndarray] = {}

    def recurse(node_index: int, parent: np.ndarray) -> None:
        node = data["nodes"][node_index]
        local = compose_matrix(node)
        world = parent @ local
        world_mats[node_index] = world
        for child in node.get("children", []):
            recurse(child, world)

    scene_index = data.get("scene", 0)
    scene = data["scenes"][scene_index]
    identity = np.eye(4, dtype=np.float32)
    for node_index in scene.get("nodes", []):
        recurse(node_index, identity)

    return list(world_mats.items())


def export_gltf_collision(source: Path, destination: Path) -> None:
    data, buffers = _load_gltf(source)

    vertices: List[Tuple[float, float, float]] = []
    faces: List[Tuple[int, int, int]] = []

    node_transforms = dict(_traverse_nodes(data))

    for node_index, world in node_transforms.items():
        node = data["nodes"][node_index]
        if "mesh" not in node:
            continue
        mesh = data["meshes"][node["mesh"]]
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) != 4:
                continue  # Only handle triangles
            attributes = primitive.get("attributes", {})
            if "POSITION" not in attributes:
                continue

            positions = _read_accessor(data, buffers, attributes["POSITION"])
            homogenous = np.c_[positions, np.ones(len(positions))]
            transformed = (world @ homogenous.T).T[:, :3]

            base_index = len(vertices)
            vertices.extend(map(tuple, transformed.tolist()))

            if "indices" in primitive:
                indices = _read_accessor(data, buffers, primitive["indices"]).astype(np.int64).flatten()
            else:
                indices = np.arange(len(positions), dtype=np.int64)

            for i in range(0, len(indices), 3):
                a = base_index + int(indices[i]) + 1
                b = base_index + int(indices[i + 1]) + 1
                c = base_index + int(indices[i + 2]) + 1
                faces.append((a, b, c))

    if not vertices:
        raise ValueError(f"No mesh data found in {source}")

    _write_obj(destination, vertices, faces)


# Entry point -------------------------------------------------------------------


def _collect_scene_paths(paths: Sequence[str] | None) -> List[Path]:
    if not paths:
        return sorted((ASSETS / "scenes").glob("*.json"))
    results: List[Path] = []
    for item in paths:
        path = Path(item)
        if not path.is_absolute():
            path = (ROOT / item).resolve()
        if path.is_dir():
            results.extend(sorted(path.glob("*.json")))
        else:
            results.append(path)
    return results


def _iter_collision_definitions(scene_path: Path) -> Iterator[Tuple[Path, Dict, str]]:
    payload = json.loads(scene_path.read_text(encoding="utf-8"))
    objects = payload.get("objects", [])
    base_path = scene_path.parent
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        physics = obj.get("physics")
        if not isinstance(physics, dict):
            continue
        collision = physics.get("collision_mesh")
        if not isinstance(collision, dict):
            continue
        yield base_path, collision, obj.get("name", "Unnamed")


def cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate collision meshes referenced by scene physics definitions.",
    )
    parser.add_argument(
        "--scene",
        action="append",
        help="Specific scene file or directory to process (defaults to all scenes).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild collision meshes even when outputs appear up-to-date.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress logs for meshes that are already up-to-date.",
    )
    args = parser.parse_args(argv)

    try:
        from gamelib.physics.collision_meshes import resolve_collision_mesh
    except ImportError as exc:  # pragma: no cover - handled at runtime
        parser.error(f"Unable to import collision resolver: {exc}")
        return 2

    scenes = _collect_scene_paths(args.scene)
    if not scenes:
        if not args.quiet:
            print("No scenes found.")
        return 0

    processed = 0
    rebuilt = 0
    up_to_date = 0
    for scene_path in scenes:
        for base_path, definition, obj_name in _iter_collision_definitions(scene_path):
            result = resolve_collision_mesh(definition, base_path=base_path, force_rebuild=args.force)
            processed += 1
            relative_output = result.path.relative_to(ROOT)
            if result.rebuilt:
                rebuilt += 1
                print(f"[rebuilt] {relative_output}  <- {scene_path.name}:{obj_name}")
            elif not args.quiet:
                up_to_date += 1
                print(f"[ok]      {relative_output}")

    if not args.quiet:
        print(f"Processed {processed} collision mesh request(s); rebuilt {rebuilt}, up-to-date {up_to_date}.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI-compatible entry point."""

    return cli(argv)


if __name__ == "__main__":
    raise SystemExit(cli())
