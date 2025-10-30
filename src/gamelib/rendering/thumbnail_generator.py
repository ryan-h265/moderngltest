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
    out vec3 out_world_pos;

    void main() {
        vec4 world_pos = model * vec4(in_position, 1.0);
        gl_Position = projection * view * world_pos;
        out_position = world_pos.xyz;
        out_world_pos = world_pos.xyz;
        out_normal = normalize((model * vec4(in_normal, 0.0)).xyz);
    }
    """

    THUMB_FRAGMENT_SHADER = """
    #version 410

    in vec3 out_normal;
    in vec3 out_position;
    in vec3 out_world_pos;

    out vec4 out_color;

    uniform vec3 light_dir;
    uniform vec3 object_color;
    uniform vec3 camera_pos;

    void main() {
        vec3 norm = normalize(out_normal);
        vec3 light_direction = normalize(light_dir);

        // Diffuse
        float diff = max(dot(norm, light_direction), 0.0);
        vec3 diffuse = diff * object_color * 0.8;

        // Ambient
        vec3 ambient = 0.4 * object_color;

        // Specular
        vec3 view_dir = normalize(camera_pos - out_world_pos);
        vec3 reflect_dir = reflect(-light_direction, norm);
        float spec = pow(max(dot(view_dir, reflect_dir), 0.0), 16.0);
        vec3 specular = spec * vec3(0.3, 0.3, 0.3);

        vec3 final_color = ambient + diffuse + specular;
        out_color = vec4(final_color, 1.0);
    }
    """

    def __init__(self, ctx: moderngl.Context, thumbnail_size: int = 128):
        """
        Initialize thumbnail generator.

        Args:
            ctx: ModernGL context
            thumbnail_size: Size of generated thumbnails (width and height)
        """
        print(f"[ThumbnailGenerator] __init__: Starting initialization")
        self.ctx = ctx
        self.thumbnail_size = thumbnail_size
        self.thumbs_dir = Path(__file__).parent.parent.parent.parent / "assets" / "ui" / "thumbs"
        self.thumbs_dir.mkdir(parents=True, exist_ok=True)

        # Separate directories for different asset types
        self.models_dir = self.thumbs_dir / "models"
        self.lights_dir = self.thumbs_dir / "lights"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.lights_dir.mkdir(parents=True, exist_ok=True)

        print(f"[ThumbnailGenerator] Initialized successfully")
        print(f"  Thumbnails directory: {self.thumbs_dir}")
        print(f"  Models directory: {self.models_dir}")
        print(f"  Lights directory: {self.lights_dir}")

        # Compile shader program
        print(f"[ThumbnailGenerator] Compiling shader programs...")
        try:
            self.program = self.ctx.program(
                vertex_shader=self.THUMB_VERTEX_SHADER,
                fragment_shader=self.THUMB_FRAGMENT_SHADER
            )
            print(f"[ThumbnailGenerator] Shader program compiled successfully")
        except Exception as e:
            print(f"[ThumbnailGenerator] WARNING: Failed to compile thumbnail shader: {e}")
            self.program = None

        # Create framebuffer for rendering
        print(f"[ThumbnailGenerator] Creating framebuffer...")
        self.fbo = None
        self.texture = None
        self._create_framebuffer()

    def _create_framebuffer(self) -> None:
        """Create framebuffer and texture for thumbnail rendering."""
        try:
            print(f"[ThumbnailGenerator] Creating framebuffer ({self.thumbnail_size}x{self.thumbnail_size})...")
            # Create color texture
            self.texture = self.ctx.texture(
                (self.thumbnail_size, self.thumbnail_size),
                4,
                dtype='f1'
            )

            # Create depth renderbuffer for depth testing
            depth_rb = self.ctx.renderbuffer((self.thumbnail_size, self.thumbnail_size))

            # Create framebuffer
            self.fbo = self.ctx.framebuffer(
                color_attachments=[self.texture],
                depth_attachment=depth_rb
            )
            print(f"[ThumbnailGenerator] Framebuffer created successfully")
        except Exception as e:
            print(f"[ThumbnailGenerator] ERROR: Failed to create framebuffer: {e}")
            import traceback
            traceback.print_exc()
            # Try fallback without depth attachment
            try:
                print(f"[ThumbnailGenerator] Trying framebuffer without depth attachment...")
                self.fbo = self.ctx.framebuffer(
                    color_attachments=[self.texture]
                )
                print(f"[ThumbnailGenerator] Framebuffer created successfully (no depth)")
            except Exception as e2:
                print(f"[ThumbnailGenerator] ERROR: Failed to create framebuffer (no depth): {e2}")
                import traceback
                traceback.print_exc()
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
            print(f"[ThumbnailGenerator] ERROR: No framebuffer available")
            return None

        # Sanitize filename
        safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in model_name)
        thumb_path = self.models_dir / f"{safe_name}.png"

        # Skip if already exists
        if thumb_path.exists() and not force_regenerate:
            print(f"[ThumbnailGenerator] [SKIP] {model_name}: thumbnail already exists at {thumb_path}")
            return thumb_path

        print(f"[ThumbnailGenerator] [GENERATING] {model_name}...")
        try:
            # Import here to avoid circular dependency
            from ..loaders import GltfLoader

            print(f"  Loading model from: {model_path}")
            loader = GltfLoader(self.ctx)
            model = loader.load(model_path)
            print(f"  Model loaded successfully")

            # Render thumbnail
            print(f"  Rendering thumbnail...")
            self._render_model_thumbnail(model)

            # Save to file
            print(f"  Saving to: {thumb_path}")
            self._save_framebuffer_to_png(thumb_path)
            print(f"[ThumbnailGenerator] [SUCCESS] {model_name}: {thumb_path}")

            return thumb_path

        except Exception as e:
            print(f"[ThumbnailGenerator] [ERROR] {model_name}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_light_preset_thumbnails(self, light_presets: dict) -> dict:
        """
        Generate thumbnails for light presets.

        Args:
            light_presets: Dict of light presets from settings

        Returns:
            Dict mapping preset names to thumbnail paths
        """
        print(f"[ThumbnailGenerator] Generating light preset thumbnails for {len(light_presets)} presets")
        results = {}

        for preset_name, preset_data in light_presets.items():
            thumb_path = self.lights_dir / f"{preset_name}.png"

            # Skip if already exists
            if thumb_path.exists():
                print(f"  [SKIP] {preset_name}: thumbnail already exists at {thumb_path}")
                results[preset_name] = thumb_path
                continue

            # Skip generation if framebuffer failed
            if not self.fbo:
                print(f"  [SKIP] {preset_name}: framebuffer not available (rendering disabled)")
                results[preset_name] = None
                continue

            try:
                print(f"  [GENERATING] {preset_name}...")
                color = preset_data.get("color", (1.0, 1.0, 1.0))
                self._render_light_thumbnail(color)
                self._save_framebuffer_to_png(thumb_path)
                results[preset_name] = thumb_path
                print(f"  [SUCCESS] {preset_name}: saved to {thumb_path}")
            except Exception as e:
                print(f"  [ERROR] {preset_name}: {e}")
                import traceback
                traceback.print_exc()
                results[preset_name] = None

        print(f"[ThumbnailGenerator] Light thumbnail generation complete")
        return results

    def _render_model_thumbnail(self, model) -> None:
        """
        Render model to thumbnail framebuffer by loading and rendering the actual model geometry.

        Args:
            model: Model object with geometry to render
        """
        # Set up viewport and clear
        self.ctx.viewport = (0, 0, self.thumbnail_size, self.thumbnail_size)
        self.fbo.use()
        self.ctx.clear(0.15, 0.15, 0.18, 1.0)  # Dark background
        self.ctx.enable(moderngl.DEPTH_TEST)

        if not self.program:
            return

        try:
            # Calculate model bounds to frame it properly
            bounds = self._calculate_model_bounds(model)
            if bounds is None:
                # Fallback if we can't calculate bounds
                bounds = ((-2, -2, -2), (2, 2, 2))

            min_pt, max_pt = bounds
            center = np.array([(min_pt[i] + max_pt[i]) / 2 for i in range(3)], dtype=np.float32)
            size = np.array([max_pt[i] - min_pt[i] for i in range(3)], dtype=np.float32)
            max_size = max(size) if max(size) > 0 else 4.0

            # Position camera to see the entire model
            distance = max_size * 1.5
            camera_pos = center + np.array([distance * 0.6, distance * 0.5, distance * 0.8], dtype=np.float32)

            view = Matrix44.look_at(
                tuple(camera_pos),
                tuple(center),
                (0, 1, 0)
            )

            # Orthographic projection framed around the model
            half_size = max_size * 0.8
            projection = Matrix44.orthogonal_projection(
                -half_size, half_size,
                -half_size, half_size,
                0.1, 1000
            )

            # Identity model matrix (model already at origin)
            model_matrix = Matrix44.identity()

            # Set up shader uniforms
            self.program['model'].write(np.array(model_matrix, dtype=np.float32))
            self.program['view'].write(np.array(view, dtype=np.float32))
            self.program['projection'].write(np.array(projection, dtype=np.float32))
            self.program['light_dir'].write(np.array([1.0, 0.8, 0.6], dtype=np.float32))
            self.program['object_color'].write(np.array([0.7, 0.7, 0.7], dtype=np.float32))
            self.program['camera_pos'].write(np.array(camera_pos, dtype=np.float32))

            # Render all meshes of the model
            if hasattr(model, 'meshes'):
                for mesh in model.meshes:
                    if hasattr(mesh, 'render'):
                        # Pass model matrix as parent transform and context
                        mesh.render(self.program, parent_transform=model_matrix, ctx=self.ctx)
            elif hasattr(model, 'render'):
                # Fallback: try to render the model directly
                model.render(self.program)
            elif hasattr(model, 'geometry') and hasattr(model.geometry, 'render'):
                # Another fallback for SceneObjects
                model.geometry.render(self.program)

        except Exception as e:
            print(f"[ThumbnailGenerator] Warning: Failed to render model thumbnail: {e}")
            import traceback
            traceback.print_exc()

    def _calculate_model_bounds(self, model) -> tuple:
        """
        Calculate bounding box of a model.

        Returns:
            Tuple of (min_point, max_point) or None if calculation fails
        """
        try:
            if hasattr(model, 'meshes'):
                all_vertices = []
                for mesh in model.meshes:
                    if hasattr(mesh, 'vertices'):
                        all_vertices.extend(mesh.vertices)
                    elif hasattr(mesh, 'vao') and hasattr(mesh.vao, 'vertices'):
                        # Try to get vertices from VAO
                        pass

                if all_vertices:
                    vertices = np.array(all_vertices)
                    min_pt = tuple(np.min(vertices, axis=0)[:3])
                    max_pt = tuple(np.max(vertices, axis=0)[:3])
                    return (min_pt, max_pt)

            # Fallback default bounds
            return ((-2, -2, -2), (2, 2, 2))
        except Exception as e:
            print(f"[ThumbnailGenerator] Warning: Could not calculate model bounds: {e}")
            return None

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
        sphere = geometry.sphere(radius=1.0, sectors=16, rings=8)

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

        # Set up lighting - convert to numpy arrays for ModernGL
        self.program['model'].write(np.array(model, dtype=np.float32))
        self.program['view'].write(np.array(view, dtype=np.float32))
        self.program['projection'].write(np.array(projection, dtype=np.float32))
        self.program['light_dir'].write(np.array([1.0, 1.0, 1.0], dtype=np.float32))
        self.program['object_color'].write(np.array(color, dtype=np.float32))

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
            self.program['model'].write(np.array(model_matrix, dtype=np.float32))
            self.program['view'].write(np.array(view, dtype=np.float32))
            self.program['projection'].write(np.array(projection, dtype=np.float32))
            self.program['light_dir'].write(np.array([1.0, 1.0, 1.0], dtype=np.float32))
            color_val = model.color if hasattr(model, 'color') else (0.8, 0.8, 0.8)
            self.program['object_color'].write(np.array(color_val, dtype=np.float32))

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
        try:
            # Read pixel data from texture
            print(f"  [PNG] Reading texture data ({self.thumbnail_size}x{self.thumbnail_size})...")
            data = self.texture.read()

            # Convert to numpy array
            image_data = np.frombuffer(data, dtype=np.uint8)
            image_data = image_data.reshape((self.thumbnail_size, self.thumbnail_size, 4))

            # Flip vertically (OpenGL origin is bottom-left)
            image_data = np.flipud(image_data)

            # Write simple PNG (uncompressed for now)
            print(f"  [PNG] Writing PNG file ({len(image_data)} bytes)...")
            self._write_png(path, image_data)
            print(f"  [PNG] File written successfully to {path}")
        except Exception as e:
            print(f"  [PNG] ERROR: {e}")
            import traceback
            traceback.print_exc()

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
