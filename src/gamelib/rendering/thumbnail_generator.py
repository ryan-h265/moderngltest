"""
Thumbnail Generator - Creates preview images for assets

Renders 3D models and light presets to small PNG thumbnails for use in the
attribute editor menus. Caches generated thumbnails to disk to avoid regeneration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, TYPE_CHECKING
import struct

import moderngl
import numpy as np
from pyrr import Matrix44, Vector3

if TYPE_CHECKING:
    from ..core.camera import Camera
    from ..core.scene import Scene, SceneObject
    from ..loaders import GltfLoader


class ThumbnailGenerator:
    """Generates and caches thumbnail images for assets."""

    THUMB_VERTEX_SHADER = """
    #version 410

    in vec3 in_position;
    in vec3 in_normal;

    uniform mat4 model;
    uniform mat4 view;
    uniform mat4 projection;

    out vec3 out_normal;
    out vec3 out_position;

    void main() {
        gl_Position = projection * view * model * vec4(in_position, 1.0);
        out_position = (model * vec4(in_position, 1.0)).xyz;
        out_normal = normalize((model * vec4(in_normal, 0.0)).xyz);
    }
    """

    THUMB_FRAGMENT_SHADER = """
    #version 410

    in vec3 out_normal;
    in vec3 out_position;

    out vec4 out_color;

    uniform vec3 light_dir;
    uniform vec3 object_color;

    void main() {
        vec3 norm = normalize(out_normal);
        vec3 light_direction = normalize(light_dir);

        float diff = max(dot(norm, light_direction), 0.0);
        vec3 diffuse = diff * object_color;

        vec3 ambient = 0.3 * object_color;
        out_color = vec4(ambient + diffuse, 1.0);
    }
    """

    def __init__(self, ctx: moderngl.Context, thumbnail_size: int = 128):
        """
        Initialize thumbnail generator.

        Args:
            ctx: ModernGL context
            thumbnail_size: Size of generated thumbnails (width and height)
        """
        self.ctx = ctx
        self.thumbnail_size = thumbnail_size
        self.thumbs_dir = Path(__file__).parent.parent.parent.parent / "assets" / "ui" / "thumbs"
        self.thumbs_dir.mkdir(parents=True, exist_ok=True)

        # Separate directories for different asset types
        self.models_dir = self.thumbs_dir / "models"
        self.lights_dir = self.thumbs_dir / "lights"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.lights_dir.mkdir(parents=True, exist_ok=True)

        # Compile shader program
        try:
            self.program = self.ctx.program(
                vertex_shader=self.THUMB_VERTEX_SHADER,
                fragment_shader=self.THUMB_FRAGMENT_SHADER
            )
        except Exception as e:
            print(f"Warning: Failed to compile thumbnail shader: {e}")
            self.program = None

        # Create framebuffer for rendering
        self.fbo = None
        self.texture = None
        self._create_framebuffer()

    def _create_framebuffer(self) -> None:
        """Create framebuffer and texture for thumbnail rendering."""
        try:
            # Create color texture
            self.texture = self.ctx.texture(
                (self.thumbnail_size, self.thumbnail_size),
                4,
                dtype='f1'
            )

            # Create depth texture
            depth_texture = self.ctx.texture(
                (self.thumbnail_size, self.thumbnail_size),
                1,
                dtype='f4'
            )

            # Create framebuffer
            self.fbo = self.ctx.framebuffer(
                color_attachments=[self.texture],
                depth_attachment=depth_texture
            )
        except Exception as e:
            print(f"Warning: Failed to create thumbnail framebuffer: {e}")
            self.fbo = None

    def generate_model_thumbnail(
        self,
        model_path: str,
        model_name: str,
        force_regenerate: bool = False,
    ) -> Optional[Path]:
        """
        Generate thumbnail for a 3D model.

        Args:
            model_path: Path to model file (GLTF/GLB)
            model_name: Name of model (used for filename)
            force_regenerate: If True, regenerate even if cached

        Returns:
            Path to thumbnail image or None if generation failed
        """
        if not self.fbo:
            return None

        # Sanitize filename
        safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in model_name)
        thumb_path = self.models_dir / f"{safe_name}.png"

        # Skip if already exists
        if thumb_path.exists() and not force_regenerate:
            return thumb_path

        try:
            # Import here to avoid circular dependency
            from ..loaders import GltfLoader

            loader = GltfLoader(self.ctx)
            model = loader.load(model_path)

            # Render thumbnail
            self._render_model_thumbnail(model)

            # Save to file
            self._save_framebuffer_to_png(thumb_path)
            print(f"Generated thumbnail: {thumb_path}")

            return thumb_path

        except Exception as e:
            print(f"Warning: Failed to generate thumbnail for {model_name}: {e}")
            return None

    def generate_light_preset_thumbnails(self, light_presets: dict) -> dict:
        """
        Generate thumbnails for light presets.

        Args:
            light_presets: Dict of light presets from settings

        Returns:
            Dict mapping preset names to thumbnail paths
        """
        results = {}

        for preset_name, preset_data in light_presets.items():
            thumb_path = self.lights_dir / f"{preset_name}.png"

            # Skip if already exists
            if thumb_path.exists():
                results[preset_name] = thumb_path
                continue

            try:
                color = preset_data.get("color", (1.0, 1.0, 1.0))
                self._render_light_thumbnail(color)
                self._save_framebuffer_to_png(thumb_path)
                results[preset_name] = thumb_path
                print(f"Generated light thumbnail: {thumb_path}")
            except Exception as e:
                print(f"Warning: Failed to generate light thumbnail for {preset_name}: {e}")
                results[preset_name] = None

        return results

    def _render_model_thumbnail(self, model: SceneObject) -> None:
        """
        Render model to thumbnail framebuffer.

        Args:
            model: SceneObject to render
        """
        # Set up viewport and clear
        self.ctx.viewport = (0, 0, self.thumbnail_size, self.thumbnail_size)
        self.fbo.use()
        self.ctx.clear(0.15, 0.15, 0.18, 1.0)  # Dark background
        self.ctx.enable(moderngl.DEPTH_TEST)

        # Simple orthographic view centered on model
        view = Matrix44.look_at(
            (5, 5, 5),  # Camera position
            (0, 0, 0),  # Look at center
            (0, 1, 0)   # Up vector
        )

        projection = Matrix44.orthogonal_projection(
            -10, 10,  # left, right
            -10, 10,  # bottom, top
            0.1, 100  # near, far
        )

        # Reset model transform for thumbnail
        model.position = Vector3([0, 0, 0])
        model.rotation = Vector3([0.5, 0.5, 0])  # Slight rotation for better view
        model.scale = Vector3([1.0, 1.0, 1.0])

        # Render
        if hasattr(model, 'render'):
            try:
                model.render(view, projection, [])
            except Exception as e:
                # Fallback: just render with basic shader if available
                if self.program:
                    self._render_with_basic_shader(model, view, projection)

    def _render_light_thumbnail(self, color: tuple) -> None:
        """
        Render light preset thumbnail (colored sphere).

        Args:
            color: RGB color as tuple
        """
        # Set up viewport and clear
        self.ctx.viewport = (0, 0, self.thumbnail_size, self.thumbnail_size)
        self.fbo.use()
        self.ctx.clear(0.15, 0.15, 0.18, 1.0)  # Dark background
        self.ctx.enable(moderngl.DEPTH_TEST)

        if not self.program:
            return

        # Create a simple sphere geometry
        from moderngl_window import geometry
        sphere = geometry.sphere(radius=1.0, sectors=16, stacks=8)

        # Set up matrices
        model = Matrix44.identity()
        view = Matrix44.look_at(
            (3, 3, 3),
            (0, 0, 0),
            (0, 1, 0)
        )
        projection = Matrix44.orthogonal_projection(
            -3, 3, -3, 3, 0.1, 100
        )

        # Set up lighting
        self.program['model'].write(model)
        self.program['view'].write(view)
        self.program['projection'].write(projection)
        self.program['light_dir'].write((1.0, 1.0, 1.0))
        self.program['object_color'].write(color)

        # Render sphere
        try:
            sphere.render(self.program)
        except Exception as e:
            print(f"Warning: Failed to render light thumbnail: {e}")

    def _render_with_basic_shader(
        self,
        model: SceneObject,
        view: Matrix44,
        projection: Matrix44,
    ) -> None:
        """Fallback rendering using basic shader."""
        if not self.program:
            return

        try:
            model_matrix = self._build_model_matrix(model)
            self.program['model'].write(model_matrix)
            self.program['view'].write(view)
            self.program['projection'].write(projection)
            self.program['light_dir'].write((1.0, 1.0, 1.0))
            self.program['object_color'].write(model.color if hasattr(model, 'color') else (0.8, 0.8, 0.8))

            if hasattr(model, 'geometry') and hasattr(model.geometry, 'render'):
                model.geometry.render(self.program)
        except Exception as e:
            print(f"Warning: Fallback shader rendering failed: {e}")

    def _build_model_matrix(self, obj: SceneObject) -> Matrix44:
        """Build model matrix from object transform."""
        translation = Matrix44.from_translation(obj.position)
        rot_x = Matrix44.from_x_rotation(obj.rotation.x)
        rot_y = Matrix44.from_y_rotation(obj.rotation.y)
        rot_z = Matrix44.from_z_rotation(obj.rotation.z)
        rotation = rot_x * rot_y * rot_z
        scale = Matrix44.from_scale(obj.scale)
        return translation * rotation * scale

    def _save_framebuffer_to_png(self, path: Path) -> None:
        """
        Save framebuffer contents to PNG file.

        Args:
            path: Output file path
        """
        # Read pixel data from texture
        data = self.texture.read()

        # Convert to numpy array
        image_data = np.frombuffer(data, dtype=np.uint8)
        image_data = image_data.reshape((self.thumbnail_size, self.thumbnail_size, 4))

        # Flip vertically (OpenGL origin is bottom-left)
        image_data = np.flipud(image_data)

        # Write simple PNG (uncompressed for now)
        self._write_png(path, image_data)

    def _write_png(self, path: Path, image_data: np.ndarray) -> None:
        """
        Write simple PNG file (without external PNG library).

        Args:
            path: Output file path
            image_data: RGBA image data as numpy array
        """
        try:
            import zlib

            height, width, channels = image_data.shape

            # PNG signature
            png_data = b'\x89PNG\r\n\x1a\n'

            # IHDR chunk (image header)
            ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
            ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
            png_data += struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)

            # IDAT chunk (image data)
            raw_data = b''
            for y in range(height):
                raw_data += b'\x00'  # Filter type 0 (None)
                raw_data += image_data[y].tobytes()

            compressed = zlib.compress(raw_data, 9)
            idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
            png_data += struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)

            # IEND chunk (image end)
            iend_crc = zlib.crc32(b'IEND') & 0xffffffff
            png_data += struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)

            # Write file
            path.write_bytes(png_data)

        except Exception as e:
            print(f"Warning: Failed to write PNG: {e}")
