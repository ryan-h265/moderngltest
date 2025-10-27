"""Generate fractal terrain heightmaps and a scene JSON referencing them.

Usage (example):
    python examples/generate_fractal_scene.py --preset mountainous --res 100 --out assets/heightmaps

Exports:
 - compressed .npz heightmap files in the output directory
 - optional .obj mesh
 - scene JSON in assets/scenes/fractal_terrain_scene.json that references a chosen heightmap
"""

import argparse
import os
import json
from pathlib import Path

import numpy as np

from src.gamelib.fractal_perlin import generate_noise_grid, save_heightmap, export_obj, PRESETS


def make_scene_json(scene_path: str, heightmap_relpath: str, metadata: dict):
    scene = {
        'type': 'fractal_terrain_scene',
        'heightmap': heightmap_relpath,
        'metadata': metadata,
        'objects': []
    }

    os.makedirs(os.path.dirname(scene_path), exist_ok=True)
    with open(scene_path, 'w') as fh:
        json.dump(scene, fh, indent=2)

    print(f"Wrote scene JSON: {scene_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--preset', default='mountainous', choices=list(PRESETS.keys()))
    p.add_argument('--res', type=int, default=100, help='Resolution (per axis) for heightmap')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--world-size', type=float, default=400.0)
    p.add_argument('--out', default='assets/heightmaps')
    p.add_argument('--name', default=None, help='Base name for outputs (defaults to generated)')
    p.add_argument('--obj', action='store_true', help='Export an OBJ mesh as well')
    p.add_argument('--json', action='store_true', help='Also write a small JSON metadata alongside the .npz')

    args = p.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    name = args.name or f"fractal_{args.preset}_r{args.res}_s{args.seed}"
    npz_path = out_dir / f"{name}.npz"

    print(f"Generating heightmap: preset={args.preset}, res={args.res}, seed={args.seed}")
    heights, meta = generate_noise_grid(args.res, scale=PRESETS[args.preset]['scale'],
                                       world_size=args.world_size, preset=args.preset,
                                       seed=args.seed)

    save_heightmap(str(npz_path), heights, meta, json_fallback=args.json)
    print(f"Wrote heightmap: {npz_path} (shape={heights.shape})")

    if args.obj:
        obj_path = out_dir / f"{name}.obj"
        export_obj(str(obj_path), heights, args.world_size)
        print(f"Wrote OBJ mesh: {obj_path}")

    # Write a scene JSON referencing the heightmap (relative path from assets/scenes)
    scene_dir = Path('assets/scenes')
    scene_dir.mkdir(parents=True, exist_ok=True)
    # Compute relative path used by scene file
    # store relative path from scenes to heightmap
    rel_path = os.path.relpath(npz_path, scene_dir)
    scene_path = scene_dir / 'fractal_terrain_scene.json'
    make_scene_json(str(scene_path), rel_path, meta)


if __name__ == '__main__':
    main()
