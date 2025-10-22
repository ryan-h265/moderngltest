"""
GLTF/GLB Loader

Loads GLTF and GLB models into ModernGL-compatible format.
"""

import os
import struct
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from PIL import Image
import pygltflib
import moderngl
from moderngl_window.opengl.vao import VAO
from pyrr import Vector3

from .material import Material
from .model import Model, Mesh


class GltfLoader:
    """
    Loads GLTF/GLB models and converts them to ModernGL format.
    """

    def __init__(self, ctx: moderngl.Context):
        """
        Initialize loader.

        Args:
            ctx: ModernGL context for creating GPU resources
        """
        self.ctx = ctx

    def load(self, filepath: str) -> Model:
        """
        Load a GLTF or GLB model.

        Args:
            filepath: Path to .gltf or .glb file

        Returns:
            Model object ready for rendering
        """
        filepath = Path(filepath)
        print(f"Loading model: {filepath}")

        # Load GLTF data
        gltf = pygltflib.GLTF2().load(str(filepath))

        # Parse materials first (needed for meshes)
        materials = self._parse_materials(gltf, filepath.parent)

        # Parse meshes
        meshes = self._parse_meshes(gltf, materials)

        # Calculate bounding sphere
        bounding_radius = self._calculate_bounding_radius(gltf)

        # Create model
        model = Model(
            meshes=meshes,
            name=filepath.stem,
        )
        model.bounding_radius = bounding_radius

        print(f"  Loaded {len(meshes)} meshes, bounding radius: {bounding_radius:.2f}")

        return model

    def _parse_meshes(self, gltf: pygltflib.GLTF2, materials: List[Material]) -> List[Mesh]:
        """
        Parse all meshes from GLTF.

        Args:
            gltf: GLTF data
            materials: List of parsed materials

        Returns:
            List of Mesh objects
        """
        meshes = []

        for mesh_idx, gltf_mesh in enumerate(gltf.meshes):
            # Each mesh can have multiple primitives
            for prim_idx, primitive in enumerate(gltf_mesh.primitives):
                mesh_name = f"{gltf_mesh.name or 'Mesh'}_{prim_idx}"

                # Get material
                mat_idx = primitive.material if primitive.material is not None else 0
                material = materials[mat_idx] if mat_idx < len(materials) else Material()

                # Extract vertex data
                vertex_data = self._extract_vertex_data(gltf, primitive)

                if vertex_data is None:
                    print(f"  Warning: Skipping mesh {mesh_name} (failed to extract data)")
                    continue

                # Create VAO
                vao = self._create_vao(vertex_data)

                # Create mesh
                mesh = Mesh(vao=vao, material=material, name=mesh_name)
                mesh.vertex_count = vertex_data['count']
                meshes.append(mesh)

                print(f"  Mesh: {mesh_name}, vertices: {mesh.vertex_count}")

        return meshes

    def _extract_vertex_data(self, gltf: pygltflib.GLTF2, primitive) -> Optional[Dict]:
        """
        Extract vertex data from a primitive.

        Args:
            gltf: GLTF data
            primitive: Mesh primitive

        Returns:
            Dictionary with vertex data arrays
        """
        # Get positions (required)
        if 'POSITION' not in primitive.attributes.__dict__:
            return None

        positions = self._get_accessor_data(gltf, primitive.attributes.POSITION)
        if positions is None:
            return None

        vertex_count = len(positions) // 3

        # Get normals (required for lighting)
        normals = None
        if hasattr(primitive.attributes, 'NORMAL') and primitive.attributes.NORMAL is not None:
            normals = self._get_accessor_data(gltf, primitive.attributes.NORMAL)

        # Generate normals if not provided
        if normals is None:
            print("    Generating flat normals...")
            normals = self._generate_flat_normals(positions)

        # Get texture coordinates (optional)
        texcoords = None
        if hasattr(primitive.attributes, 'TEXCOORD_0') and primitive.attributes.TEXCOORD_0 is not None:
            texcoords = self._get_accessor_data(gltf, primitive.attributes.TEXCOORD_0)

        # Get tangents (optional, for normal mapping)
        tangents = None
        if hasattr(primitive.attributes, 'TANGENT') and primitive.attributes.TANGENT is not None:
            tangents = self._get_accessor_data(gltf, primitive.attributes.TANGENT)

        # Get indices (optional)
        indices = None
        if primitive.indices is not None:
            indices = self._get_accessor_data(gltf, primitive.indices)

        return {
            'positions': positions,
            'normals': normals,
            'texcoords': texcoords,
            'tangents': tangents,
            'indices': indices,
            'count': vertex_count,
        }

    def _get_accessor_data(self, gltf: pygltflib.GLTF2, accessor_idx: int) -> Optional[np.ndarray]:
        """
        Get data from an accessor.

        Args:
            gltf: GLTF data
            accessor_idx: Accessor index

        Returns:
            Numpy array with data
        """
        accessor = gltf.accessors[accessor_idx]
        buffer_view = gltf.bufferViews[accessor.bufferView]
        buffer = gltf.buffers[buffer_view.buffer]

        # Get buffer data
        if buffer.uri:
            # External buffer file
            buffer_data = gltf.get_data_from_buffer_uri(buffer.uri)
        else:
            # Embedded buffer (GLB)
            buffer_data = gltf.binary_blob()

        # Calculate offset and stride
        offset = (buffer_view.byteOffset or 0) + (accessor.byteOffset or 0)
        stride = buffer_view.byteStride or 0

        # Determine component type and count
        component_type_sizes = {
            5120: 1,  # BYTE
            5121: 1,  # UNSIGNED_BYTE
            5122: 2,  # SHORT
            5123: 2,  # UNSIGNED_SHORT
            5125: 4,  # UNSIGNED_INT
            5126: 4,  # FLOAT
        }

        component_counts = {
            'SCALAR': 1,
            'VEC2': 2,
            'VEC3': 3,
            'VEC4': 4,
            'MAT2': 4,
            'MAT3': 9,
            'MAT4': 16,
        }

        component_size = component_type_sizes[accessor.componentType]
        component_count = component_counts[accessor.type]
        element_size = component_size * component_count

        # Extract data
        if stride == 0 or stride == element_size:
            # Tightly packed
            end_offset = offset + accessor.count * element_size
            data = buffer_data[offset:end_offset]
        else:
            # Strided data
            data = bytearray()
            for i in range(accessor.count):
                element_offset = offset + i * stride
                data.extend(buffer_data[element_offset:element_offset + element_size])

        # Convert to numpy array
        dtype_map = {
            5120: np.int8,
            5121: np.uint8,
            5122: np.int16,
            5123: np.uint16,
            5125: np.uint32,
            5126: np.float32,
        }

        dtype = dtype_map[accessor.componentType]
        array = np.frombuffer(bytes(data), dtype=dtype)

        # Reshape for multi-component types
        if component_count > 1:
            array = array.reshape(-1, component_count)

        return array.flatten().astype('f4')

    def _generate_flat_normals(self, positions: np.ndarray) -> np.ndarray:
        """
        Generate flat normals for a mesh (face normals).

        Args:
            positions: Vertex positions

        Returns:
            Normal array (same size as positions)
        """
        positions_3d = positions.reshape(-1, 3)
        normals = []

        # Process each triangle
        for i in range(0, len(positions_3d), 3):
            if i + 2 >= len(positions_3d):
                break

            v0 = positions_3d[i]
            v1 = positions_3d[i + 1]
            v2 = positions_3d[i + 2]

            # Calculate normal
            edge1 = v1 - v0
            edge2 = v2 - v0
            normal = np.cross(edge1, edge2)
            norm = np.linalg.norm(normal)
            if norm > 0:
                normal = normal / norm
            else:
                normal = np.array([0.0, 1.0, 0.0])

            # Duplicate for all three vertices
            normals.extend([normal] * 3)

        return np.array(normals, dtype='f4').flatten()

    def _create_vao(self, vertex_data: Dict) -> VAO:
        """
        Create a ModernGL VAO from vertex data.

        Args:
            vertex_data: Dictionary with vertex arrays

        Returns:
            VAO object
        """
        positions = vertex_data['positions']
        normals = vertex_data['normals']
        texcoords = vertex_data['texcoords']
        indices = vertex_data['indices']

        # If we have indices, expand vertex data first
        # (moderngl_window VAO doesn't support index buffers directly)
        if indices is not None:
            indices_int = indices.astype('i4')
            expanded_positions = []
            expanded_normals = []
            expanded_texcoords = [] if texcoords is not None else None

            # Expand vertices according to indices
            for idx in indices_int:
                # Positions
                expanded_positions.extend(positions[idx * 3:(idx + 1) * 3])
                # Normals
                expanded_normals.extend(normals[idx * 3:(idx + 1) * 3])
                # Texcoords
                if texcoords is not None:
                    expanded_texcoords.extend(texcoords[idx * 2:(idx + 1) * 2])

            positions = np.array(expanded_positions, dtype='f4')
            normals = np.array(expanded_normals, dtype='f4')
            if texcoords is not None:
                texcoords = np.array(expanded_texcoords, dtype='f4')

        # Build interleaved vertex buffer
        vertex_count = len(positions) // 3

        # Create interleaved array
        if texcoords is not None:
            # Interleave: pos, norm, uv
            interleaved = np.zeros(vertex_count * 8, dtype='f4')
            for i in range(vertex_count):
                base = i * 8
                interleaved[base:base + 3] = positions[i * 3:(i + 1) * 3]
                interleaved[base + 3:base + 6] = normals[i * 3:(i + 1) * 3]
                interleaved[base + 6:base + 8] = texcoords[i * 2:(i + 1) * 2]
            format_str = '3f 3f 2f'
            attributes = ['in_position', 'in_normal', 'in_texcoord']
        else:
            # Interleave: pos, norm
            interleaved = np.zeros(vertex_count * 6, dtype='f4')
            for i in range(vertex_count):
                base = i * 6
                interleaved[base:base + 3] = positions[i * 3:(i + 1) * 3]
                interleaved[base + 3:base + 6] = normals[i * 3:(i + 1) * 3]
            format_str = '3f 3f'
            attributes = ['in_position', 'in_normal']

        # Create VAO
        vao = VAO(name="gltf_mesh", mode=moderngl.TRIANGLES)

        # Set vertex data (no index buffer needed since we expanded)
        vao.buffer(interleaved, format_str, attributes)

        return vao

    def _parse_materials(self, gltf: pygltflib.GLTF2, model_dir: Path) -> List[Material]:
        """
        Parse all materials from GLTF.

        Args:
            gltf: GLTF data
            model_dir: Directory containing the model file

        Returns:
            List of Material objects
        """
        materials = []

        if not gltf.materials:
            # Create default material
            materials.append(Material("Default"))
            return materials

        for mat_idx, gltf_mat in enumerate(gltf.materials):
            mat_name = gltf_mat.name or f"Material_{mat_idx}"
            material = Material(mat_name)

            # Parse PBR metallic roughness
            if gltf_mat.pbrMetallicRoughness:
                pbr = gltf_mat.pbrMetallicRoughness

                # Base color texture
                if pbr.baseColorTexture:
                    tex_idx = pbr.baseColorTexture.index
                    material.base_color_texture = self._load_texture(gltf, tex_idx, model_dir)

                # Base color factor
                if pbr.baseColorFactor:
                    material.base_color_factor = tuple(pbr.baseColorFactor)

                # Metallic/roughness texture
                if pbr.metallicRoughnessTexture:
                    tex_idx = pbr.metallicRoughnessTexture.index
                    material.metallic_roughness_texture = self._load_texture(gltf, tex_idx, model_dir)

                # Metallic/roughness factors
                if pbr.metallicFactor is not None:
                    material.metallic_factor = pbr.metallicFactor
                if pbr.roughnessFactor is not None:
                    material.roughness_factor = pbr.roughnessFactor

            # Normal map
            if gltf_mat.normalTexture:
                tex_idx = gltf_mat.normalTexture.index
                material.normal_texture = self._load_texture(gltf, tex_idx, model_dir)

            # Emissive texture
            if gltf_mat.emissiveTexture:
                tex_idx = gltf_mat.emissiveTexture.index
                material.emissive_texture = self._load_texture(gltf, tex_idx, model_dir)

            materials.append(material)
            print(f"  Material: {mat_name}")

        return materials

    def _load_texture(self, gltf: pygltflib.GLTF2, texture_idx: int, model_dir: Path) -> Optional[moderngl.Texture]:
        """
        Load a texture from GLTF.

        Args:
            gltf: GLTF data
            texture_idx: Texture index
            model_dir: Directory containing the model

        Returns:
            ModernGL texture or None
        """
        if texture_idx >= len(gltf.textures):
            return None

        texture = gltf.textures[texture_idx]
        if texture.source is None:
            return None

        image = gltf.images[texture.source]

        # Load image data
        if image.uri:
            # External image file
            image_path = model_dir / image.uri
            if not image_path.exists():
                print(f"    Warning: Texture not found: {image_path}")
                return None

            img = Image.open(image_path)
        else:
            # Embedded image (buffer view)
            buffer_view = gltf.bufferViews[image.bufferView]
            buffer = gltf.buffers[buffer_view.buffer]

            if buffer.uri:
                buffer_data = gltf.get_data_from_buffer_uri(buffer.uri)
            else:
                buffer_data = gltf.binary_blob()

            offset = buffer_view.byteOffset or 0
            length = buffer_view.byteLength
            image_data = buffer_data[offset:offset + length]

            from io import BytesIO
            img = Image.open(BytesIO(image_data))

        # Convert to RGBA
        img = img.convert('RGBA')

        # Create ModernGL texture
        tex = self.ctx.texture(img.size, 4, img.tobytes())
        tex.build_mipmaps()

        # Set filtering
        tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)

        return tex

    def _calculate_bounding_radius(self, gltf: pygltflib.GLTF2) -> float:
        """
        Calculate bounding sphere radius for the model.

        Args:
            gltf: GLTF data

        Returns:
            Bounding radius
        """
        max_radius = 0.0

        for mesh in gltf.meshes:
            for primitive in mesh.primitives:
                if 'POSITION' not in primitive.attributes.__dict__:
                    continue

                positions = self._get_accessor_data(gltf, primitive.attributes.POSITION)
                if positions is None:
                    continue

                # Reshape to 3D points
                points = positions.reshape(-1, 3)

                # Calculate max distance from origin
                for point in points:
                    radius = np.linalg.norm(point)
                    max_radius = max(max_radius, radius)

        return float(max_radius) if max_radius > 0 else 1.0
