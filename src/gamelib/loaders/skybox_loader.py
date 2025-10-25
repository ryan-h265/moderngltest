"""Utilities for loading skybox cube maps."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image
import moderngl

from ..core.skybox import Skybox


class SkyboxLoader:
    """Load skybox cube maps from image files."""

    FACE_CANDIDATES: Sequence[Sequence[str]] = (
        ("posx", "px", "right"),
        ("negx", "nx", "left"),
        ("posy", "py", "top", "up"),
        ("negy", "ny", "bottom", "down"),
        ("posz", "pz", "front"),
        ("negz", "nz", "back"),
    )
    SUPPORTED_EXTENSIONS: Sequence[str] = (".png", ".jpg", ".jpeg", ".hdr", ".tga", ".bmp")

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx

    def load_from_directory(
        self,
        directory: Path | str,
        name: str | None = None,
        vertical_flip: bool = True,
    ) -> Skybox:
        """Load a cube map using common face naming conventions."""
        dir_path = Path(directory)
        if not dir_path.exists():
            raise FileNotFoundError(f"Skybox directory not found: {dir_path}")

        face_images: list[bytes] = []
        face_size: tuple[int, int] | None = None

        for index, candidates in enumerate(self.FACE_CANDIDATES):
            image_path = self._find_face_file(dir_path, candidates)
            if image_path is None:
                names = ", ".join(candidates)
                raise FileNotFoundError(
                    f"Missing cubemap face for {names} in {dir_path}"
                )

            with Image.open(image_path) as img:
                img = img.convert("RGB")
                if vertical_flip:
                    img = img.transpose(Image.FLIP_TOP_BOTTOM)
                if face_size is None:
                    face_size = img.size
                elif img.size != face_size:
                    raise ValueError(
                        f"All cubemap faces must share the same dimensions: expected {face_size}, got {img.size}"
                    )
                face_images.append(img.tobytes())

        assert face_size is not None

        texture = self.ctx.texture_cube(face_size, components=3)
        for face_index, data in enumerate(face_images):
            texture.write(face_index, data)
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        texture.build_mipmaps()

        return Skybox(texture=texture, name=name or dir_path.name)

    def _find_face_file(
        self,
        directory: Path,
        candidates: Iterable[str],
    ) -> Path | None:
        for stem in candidates:
            for ext in self.SUPPORTED_EXTENSIONS:
                candidate = directory / f"{stem}{ext}"
                if candidate.exists():
                    return candidate
        return None
