"""Collision mesh generation and resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

from ..config.settings import ASSETS_DIR, PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    # Tools live outside the package tree, but remain importable when project root is on sys.path.
    from tools import export_collision_meshes as _exporter
except ImportError as exc:  # pragma: no cover - handled at runtime
    _exporter = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

COLLISION_DIR = ASSETS_DIR / "collision"


class CollisionMeshError(RuntimeError):
    """Raised when collision mesh configuration is invalid."""


@dataclass(frozen=True)
class CollisionMeshResult:
    """Information about a resolved collision mesh."""

    path: Path
    rebuilt: bool


def resolve_collision_mesh(
    definition: Dict[str, Any],
    *,
    base_path: Optional[Path] = None,
    force_rebuild: bool = False,
) -> CollisionMeshResult:
    """
    Resolve (and build if necessary) a collision mesh described by ``definition``.

    Args:
        definition: Dictionary describing how to create the collision mesh.
        base_path: Base directory used for resolving relative input paths (e.g. scene location).
        force_rebuild: When True, regenerate even if the output appears up-to-date.

    Returns:
        Path to the generated collision mesh on disk.
    """

    if not isinstance(definition, dict):
        raise CollisionMeshError("collision_mesh definition must be a dictionary")

    if _exporter is None:
        raise CollisionMeshError(
            "Collision mesh exporter module is not available"
        ) from _IMPORT_ERROR

    mesh_type = str(definition.get("type", "")).lower()
    if not mesh_type:
        raise CollisionMeshError("collision_mesh definition requires a 'type' field")

    if mesh_type == "gltf":
        return _resolve_gltf_collision(definition, base_path, force_rebuild)
    if mesh_type in {"generator", "callable"}:
        return _resolve_generator_collision(definition, base_path, force_rebuild)

    raise CollisionMeshError(f"Unsupported collision mesh type: {mesh_type}")


# ---------------------------------------------------------------------------
# GLTF collision meshes
# ---------------------------------------------------------------------------

def _resolve_gltf_collision(
    definition: Dict[str, Any],
    base_path: Optional[Path],
    force_rebuild: bool,
) -> CollisionMeshResult:
    source = definition.get("source")
    if not source:
        raise CollisionMeshError("GLTF collision mesh requires a 'source' path")

    source_path = _resolve_input_path(source, base_path)
    dependencies = [_resolve_input_path(dep, base_path) for dep in definition.get("dependencies", [])]

    default_name = _default_gltf_output_name(source_path)
    output_path = _resolve_output_path(definition, default_name)

    needs_rebuild = _needs_rebuild(output_path, [source_path, *dependencies]) or force_rebuild
    if needs_rebuild:
        _ensure_collision_dir(output_path)
        _exporter.export_gltf_collision(source_path, output_path)

    return CollisionMeshResult(path=output_path, rebuilt=needs_rebuild)


def _default_gltf_output_name(source_path: Path) -> str:
    try:
        relative = source_path.resolve().relative_to(ASSETS_DIR)
    except ValueError:
        try:
            relative = source_path.resolve().relative_to(PROJECT_ROOT)
        except ValueError:
            relative = source_path.resolve()

    parts = [_slugify(part) for part in relative.with_suffix("").parts if part not in {"..", ""}]
    if not parts:
        parts = [_slugify(source_path.stem or "mesh")]
    slug = "_".join(parts)
    return f"{slug}_collision.obj"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _resolve_generator_collision(
    definition: Dict[str, Any],
    base_path: Optional[Path],
    force_rebuild: bool,
) -> CollisionMeshResult:
    target = definition.get("generator") or definition.get("callable")
    if not target:
        raise CollisionMeshError("Generator collision mesh requires a 'generator' reference")

    callback = _import_callable(str(target))
    params = dict(definition.get("params", {}))

    default_name = _default_generator_output_name(definition, target)
    output_path = _resolve_output_path(definition, default_name)

    dependency_values = definition.get("dependencies", [])
    dependency_paths = [_resolve_input_path(dep, base_path) for dep in dependency_values]

    needs_rebuild = force_rebuild or _needs_rebuild(output_path, dependency_paths)
    if needs_rebuild:
        _ensure_collision_dir(output_path)
        call_kwargs = dict(params)
        if definition.get("pass_base_path") and base_path is not None:
            call_kwargs.setdefault("base_path", base_path)
        callback(output_path, **call_kwargs)

    return CollisionMeshResult(path=output_path, rebuilt=needs_rebuild)

def _resolve_input_path(value: str, base_path: Optional[Path]) -> Path:
    raw_path = Path(value)
    if raw_path.is_absolute():
        return raw_path
    candidates = []
    if base_path is not None:
        candidates.append((base_path / raw_path).resolve())
    candidates.append((PROJECT_ROOT / raw_path).resolve())
    for candidate in candidates:
        if candidate.exists():
            return candidate
    # Fall back to first candidate even if it doesn't currently exist
    return candidates[0] if candidates else raw_path.resolve()


def _resolve_output_path(definition: Dict[str, Any], default_name: str) -> Path:
    output = definition.get("output")
    if output:
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = (COLLISION_DIR / output_path).resolve()
    else:
        label = _slugify_path(definition.get("name", ""))
        if label:
            inferred = _ensure_obj_extension(label)
        else:
            inferred = default_name
        output_path = (COLLISION_DIR / inferred).resolve()
    return output_path


def _needs_rebuild(output_path: Path, dependencies: Iterable[Path]) -> bool:
    if not output_path.exists():
        return True
    try:
        output_mtime = output_path.stat().st_mtime
    except FileNotFoundError:
        return True
    for dep in dependencies:
        try:
            if dep.stat().st_mtime > output_mtime:
                return True
        except FileNotFoundError:
            continue
    return False


def _ensure_collision_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _slugify(value: str) -> str:
    filtered = []
    for char in value:
        if char.isalnum():
            filtered.append(char.lower())
        elif char in {"_", "-"}:
            filtered.append(char.lower())
        else:
            filtered.append("_")
    slug = "".join(filtered).strip("_")
    return slug or "mesh"


def _slugify_path(value: str) -> str:
    return "_".join(_slugify(part) for part in Path(value).parts if part not in {"", "."})


def _ensure_obj_extension(label: str) -> str:
    if label.lower().endswith(".obj"):
        return label
    return f"{label}.obj"


def _import_callable(target: str):
    module_path, sep, attr = target.partition(":")
    if not sep:
        module_path, attr = target.rsplit(".", 1)
    module = importlib.import_module(module_path)
    try:
        callback = getattr(module, attr)
    except AttributeError as exc:
        raise CollisionMeshError(f"Callable '{target}' not found") from exc
    if not callable(callback):
        raise CollisionMeshError(f"Target '{target}' is not callable")
    return callback


def _default_generator_output_name(definition: Dict[str, Any], target: Any) -> str:
    name = definition.get("name")
    if name:
        return _ensure_obj_extension(_slugify_path(str(name)))
    return f"{_slugify(str(target))}_collision.obj"
