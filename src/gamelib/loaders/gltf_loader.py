"""
GLTF/GLB Loader

Loads GLTF and GLB models into ModernGL-compatible format.
"""

import numpy as np
from pathlib import Path
from typing import List, Optional, Dict
from PIL import Image
import pygltflib
import moderngl
from moderngl_window.opengl.vao import VAO
from pyrr import Matrix44, Vector3, Quaternion

from .material import Material
from .model import Model, Mesh
from .texture_transform import TextureTransform
from ..animation import (
    Skeleton, Joint, Skin, Animation, AnimationChannel,
    AnimationController, Keyframe, AnimationTarget, InterpolationType
)


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

        # Load skeleton if present (needed for skins)
        skeleton = None
        if gltf.skins:
            skeleton = self._load_skeleton(gltf)
            print(f"  Loaded skeleton with {len(skeleton.joints)} joints")

        # Parse node hierarchy and extract meshes with transforms
        meshes = self._parse_scene_hierarchy(gltf, materials)

        # Load skins if present
        skins = []
        if gltf.skins and skeleton:
            skins = self._load_skins(gltf, skeleton, meshes)
            print(f"  Loaded {len(skins)} skins")

        # Load animations if present
        animations = {}
        if gltf.animations:
            animations = self._load_animations(gltf, skeleton if skeleton else None)
            print(f"  Loaded {len(animations)} animations")

        # Calculate bounding sphere
        bounding_radius = self._calculate_bounding_radius(gltf)

        # Create model
        model = Model(
            meshes=meshes,
            name=filepath.stem,
        )
        model.bounding_radius = bounding_radius
        model.skeleton = skeleton
        model.skins = skins
        model.animations = animations

        # Create animation controller if there are animations
        if animations and skeleton:
            model.animation_controller = AnimationController(skeleton)

        print(f"  Loaded {len(meshes)} meshes, bounding radius: {bounding_radius:.2f}")

        return model

    def _parse_scene_hierarchy(self, gltf: pygltflib.GLTF2, materials: List[Material]) -> List[Mesh]:
        """
        Parse the GLTF scene hierarchy and extract meshes with transforms.

        Args:
            gltf: GLTF data
            materials: List of parsed materials

        Returns:
            List of Mesh objects with local transforms
        """
        meshes = []

        # Get the default scene (or first scene if no default)
        scene_idx = gltf.scene if gltf.scene is not None else 0
        if scene_idx >= len(gltf.scenes):
            print("  Warning: No valid scene found, falling back to direct mesh parsing")
            return self._parse_meshes(gltf, materials)

        scene = gltf.scenes[scene_idx]

        # Process each root node in the scene
        for node_idx in scene.nodes:
            self._process_node(gltf, node_idx, Matrix44.identity(), materials, meshes)

        return meshes

    def _process_node(self, gltf: pygltflib.GLTF2, node_idx: int,
                     parent_transform: 'Matrix44', materials: List[Material],
                     meshes: List[Mesh]):
        """
        Recursively process a node and its children, accumulating transforms.

        Args:
            gltf: GLTF data
            node_idx: Index of current node
            parent_transform: Accumulated transform from parent nodes
            materials: List of materials
            meshes: Output list to append meshes to
        """

        node = gltf.nodes[node_idx]

        # Get local transform for this node
        local_transform = self._get_node_transform(node)

        # Accumulate with parent transform
        world_transform = local_transform @ parent_transform

        # If this node has a mesh, create Mesh objects for each primitive
        if node.mesh is not None:
            gltf_mesh = gltf.meshes[node.mesh]

            for prim_idx, primitive in enumerate(gltf_mesh.primitives):
                mesh_name = f"{node.name or gltf_mesh.name or 'Mesh'}_{prim_idx}"

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

                # Create mesh with world transform from node hierarchy
                node_name = node.name if node.name else f"Node_{node_idx}"
                mesh = Mesh(
                    vao=vao,
                    material=material,
                    local_transform=local_transform,
                    node_name=node_name,
                    parent_transform=parent_transform
                )
                mesh.vertex_count = vertex_data['count']
                mesh.mesh_index = node.mesh
                mesh.node_index = node_idx
                local_array = np.array(local_transform)

                # Store base TRS components for node animations
                if node.translation is not None:
                    mesh.base_translation = Vector3(node.translation)
                else:
                    mesh.base_translation = Vector3(local_array[3, :3])

                if node.rotation is not None:
                    q = node.rotation  # (x, y, z, w)
                    mesh.base_rotation = Quaternion([q[3], q[0], q[1], q[2]])

                if node.scale is not None:
                    mesh.base_scale = Vector3(node.scale)

                meshes.append(mesh)

                print(f"  Mesh: {mesh_name}, vertices: {mesh.vertex_count}")

        # Process children recursively
        if node.children:
            for child_idx in node.children:
                self._process_node(gltf, child_idx, world_transform, materials, meshes)

    def _get_node_transform(self, node) -> 'Matrix44':
        """
        Extract transformation matrix from a GLTF node.

        Args:
            node: GLTF node

        Returns:
            4x4 transformation matrix
        """
        from pyrr import Quaternion
        import numpy as np

        # Check if node has a matrix property
        if node.matrix is not None and len(node.matrix) == 16:
            # Matrix is provided directly (column-major)
            matrix = np.array(node.matrix, dtype='f4').reshape(4, 4)
            # GLTF uses column-major, pyrr uses row-major, so transpose
            result = Matrix44(matrix.T)
            return result

        # Otherwise, compose from TRS (Translation, Rotation, Scale)
        matrix = Matrix44.identity()

        # Apply scale
        if node.scale is not None:
            s = node.scale
            matrix = matrix @ Matrix44.from_scale([s[0], s[1], s[2]])

        # Apply rotation (quaternion)
        if node.rotation is not None:
            q = node.rotation  # [x, y, z, w]
            # Create quaternion and convert to matrix
            quat = Quaternion([q[3], q[0], q[1], q[2]])  # pyrr uses [w, x, y, z]
            matrix = matrix @ Matrix44.from_quaternion(quat)

        # Apply translation
        if node.translation is not None:
            t = node.translation
            matrix = matrix @ Matrix44.from_translation([t[0], t[1], t[2]])

        return matrix

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
        else:
            # Generate default UVs (all zeros)
            print("    No texture coordinates found, using default UVs...")
            texcoords = np.zeros(vertex_count * 2, dtype='f4')

        # Get tangents (optional, for normal mapping)
        tangents = None
        if hasattr(primitive.attributes, 'TANGENT') and primitive.attributes.TANGENT is not None:
            tangents = self._get_accessor_data(gltf, primitive.attributes.TANGENT)

        # Generate tangents if missing (and we have texcoords for normal mapping)
        if tangents is None and texcoords is not None and normals is not None:
            print("    Generating tangents for normal mapping...")
            tangents = self._generate_tangents(positions, normals, texcoords)

        # Get vertex colors (optional, COLOR_0 attribute)
        colors = None
        if hasattr(primitive.attributes, 'COLOR_0') and primitive.attributes.COLOR_0 is not None:
            colors = self._get_accessor_data(gltf, primitive.attributes.COLOR_0)
            print("    Found vertex colors (COLOR_0)")

            # Ensure colors are in RGB format (convert RGBA to RGB if needed)
            # GLTF allows VEC3 or VEC4, we'll use VEC3 in shaders
            if colors is not None:
                # Reshape to per-vertex format
                colors_per_vertex = len(colors) // vertex_count
                if colors_per_vertex == 4:
                    # RGBA -> RGB (discard alpha)
                    colors = colors.reshape(-1, 4)[:, :3].flatten()
                elif colors_per_vertex != 3:
                    print(f"    Warning: Unexpected color format, ignoring")
                    colors = None

        # Get joint indices (for skinned meshes)
        joints = None
        if hasattr(primitive.attributes, 'JOINTS_0') and primitive.attributes.JOINTS_0 is not None:
            joints = self._get_accessor_data(gltf, primitive.attributes.JOINTS_0)

        # Get joint weights (for skinned meshes)
        weights = None
        if hasattr(primitive.attributes, 'WEIGHTS_0') and primitive.attributes.WEIGHTS_0 is not None:
            weights = self._get_accessor_data(gltf, primitive.attributes.WEIGHTS_0)

        # Get indices (optional)
        indices = None
        if primitive.indices is not None:
            indices = self._get_accessor_data(gltf, primitive.indices)

        return {
            'positions': positions,
            'normals': normals,
            'texcoords': texcoords,
            'tangents': tangents,
            'colors': colors,
            'joints': joints,
            'weights': weights,
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

    def _generate_tangents(self, positions: np.ndarray, normals: np.ndarray, texcoords: np.ndarray) -> np.ndarray:
        """
        Generate tangents using Lengyel's method.

        Reference: http://www.terathon.com/code/tangent.html

        Args:
            positions: Vertex positions (flat array, 3 floats per vertex)
            normals: Vertex normals (flat array, 3 floats per vertex)
            texcoords: Texture coordinates (flat array, 2 floats per vertex)

        Returns:
            Tangent array (flat array, 4 floats per vertex: xyz + handedness)
        """
        vertex_count = len(positions) // 3
        positions_3d = positions.reshape(-1, 3)
        normals_3d = normals.reshape(-1, 3)
        texcoords_2d = texcoords.reshape(-1, 2)

        # Initialize tangent and bitangent accumulators
        tan1 = np.zeros_like(positions_3d)
        tan2 = np.zeros_like(positions_3d)

        # Calculate tangents for each triangle
        for i in range(0, vertex_count, 3):
            if i + 2 >= vertex_count:
                break

            # Triangle vertices
            v0 = positions_3d[i]
            v1 = positions_3d[i + 1]
            v2 = positions_3d[i + 2]

            # UV coordinates
            uv0 = texcoords_2d[i]
            uv1 = texcoords_2d[i + 1]
            uv2 = texcoords_2d[i + 2]

            # Edge vectors
            edge1 = v1 - v0
            edge2 = v2 - v0

            # UV deltas
            duv1 = uv1 - uv0
            duv2 = uv2 - uv0

            # Calculate tangent and bitangent
            r = 1.0 / (duv1[0] * duv2[1] - duv1[1] * duv2[0] + 1e-6)  # Avoid division by zero
            sdir = (edge1 * duv2[1] - edge2 * duv1[1]) * r
            tdir = (edge2 * duv1[0] - edge1 * duv2[0]) * r

            # Accumulate for all vertices of this triangle
            tan1[i] += sdir
            tan1[i + 1] += sdir
            tan1[i + 2] += sdir

            tan2[i] += tdir
            tan2[i + 1] += tdir
            tan2[i + 2] += tdir

        # Orthogonalize and calculate handedness for each vertex
        tangents = []
        for i in range(vertex_count):
            n = normals_3d[i]
            t = tan1[i]

            # Gram-Schmidt orthogonalize
            t_ortho = t - n * np.dot(n, t)
            t_norm = np.linalg.norm(t_ortho)
            if t_norm > 1e-6:
                t_ortho = t_ortho / t_norm
            else:
                # Fallback: use perpendicular vector
                t_ortho = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
                t_ortho = t_ortho - n * np.dot(n, t_ortho)
                t_ortho = t_ortho / (np.linalg.norm(t_ortho) + 1e-6)

            # Calculate handedness (w component)
            handedness = 1.0 if np.dot(np.cross(n, t), tan2[i]) > 0.0 else -1.0

            # Store as vec4 (xyz + w)
            tangents.extend([t_ortho[0], t_ortho[1], t_ortho[2], handedness])

        return np.array(tangents, dtype='f4')

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
        tangents = vertex_data['tangents']
        colors = vertex_data.get('colors', None)
        joints = vertex_data.get('joints', None)
        weights = vertex_data.get('weights', None)
        indices = vertex_data['indices']

        # If we have indices, expand vertex data first
        # (moderngl_window VAO doesn't support index buffers directly)
        if indices is not None:
            indices_int = indices.astype('i4')
            expanded_positions = []
            expanded_normals = []
            expanded_texcoords = [] if texcoords is not None else None
            expanded_tangents = [] if tangents is not None else None
            expanded_colors = [] if colors is not None else None
            expanded_joints = [] if joints is not None else None
            expanded_weights = [] if weights is not None else None

            # Expand vertices according to indices
            for idx in indices_int:
                # Positions
                expanded_positions.extend(positions[idx * 3:(idx + 1) * 3])
                # Normals
                expanded_normals.extend(normals[idx * 3:(idx + 1) * 3])
                # Texcoords
                if texcoords is not None:
                    expanded_texcoords.extend(texcoords[idx * 2:(idx + 1) * 2])
                # Tangents (vec4)
                if tangents is not None:
                    expanded_tangents.extend(tangents[idx * 4:(idx + 1) * 4])
                # Colors (vec3)
                if colors is not None:
                    expanded_colors.extend(colors[idx * 3:(idx + 1) * 3])
                # Joints (vec4 - 4 joint indices)
                if joints is not None:
                    expanded_joints.extend(joints[idx * 4:(idx + 1) * 4])
                # Weights (vec4 - 4 weights)
                if weights is not None:
                    expanded_weights.extend(weights[idx * 4:(idx + 1) * 4])

            positions = np.array(expanded_positions, dtype='f4')
            normals = np.array(expanded_normals, dtype='f4')
            if texcoords is not None:
                texcoords = np.array(expanded_texcoords, dtype='f4')
            if tangents is not None:
                tangents = np.array(expanded_tangents, dtype='f4')
            if colors is not None:
                colors = np.array(expanded_colors, dtype='f4')
            if joints is not None:
                joints = np.array(expanded_joints, dtype='f4')
            if weights is not None:
                weights = np.array(expanded_weights, dtype='f4')

        # Build interleaved vertex buffer
        vertex_count = len(positions) // 3

        # Always create full interleaved array with all attributes
        # If tangents are missing, generate dummy ones
        if tangents is None:
            print("    Generating default tangents...")
            tangents = np.tile([1.0, 0.0, 0.0, 1.0], vertex_count).astype('f4')

        # If colors are missing, generate default white
        if colors is None:
            colors = np.tile([1.0, 1.0, 1.0], vertex_count).astype('f4')

        # If joints/weights are missing, generate dummy ones (for non-skinned meshes)
        if joints is None:
            joints = np.tile([0.0, 0.0, 0.0, 0.0], vertex_count).astype('f4')
        if weights is None:
            weights = np.tile([1.0, 0.0, 0.0, 0.0], vertex_count).astype('f4')

        # Interleave: pos (3f), norm (3f), uv (2f), tangent (4f), color (3f), joints (4f), weights (4f) = 23 floats per vertex
        interleaved = np.zeros(vertex_count * 23, dtype='f4')
        for i in range(vertex_count):
            base = i * 23
            interleaved[base:base + 3] = positions[i * 3:(i + 1) * 3]
            interleaved[base + 3:base + 6] = normals[i * 3:(i + 1) * 3]
            interleaved[base + 6:base + 8] = texcoords[i * 2:(i + 1) * 2]
            interleaved[base + 8:base + 12] = tangents[i * 4:(i + 1) * 4]
            interleaved[base + 12:base + 15] = colors[i * 3:(i + 1) * 3]
            interleaved[base + 15:base + 19] = joints[i * 4:(i + 1) * 4]
            interleaved[base + 19:base + 23] = weights[i * 4:(i + 1) * 4]

        format_str = '3f 3f 2f 4f 3f 4f 4f'
        attributes = ['in_position', 'in_normal', 'in_texcoord', 'in_tangent', 'in_color', 'in_joints', 'in_weights']

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
                    # Load texture transform if present
                    material.base_color_transform = self._load_texture_transform(pbr.baseColorTexture)

                # Base color factor
                if pbr.baseColorFactor:
                    material.base_color_factor = tuple(pbr.baseColorFactor)

                # Metallic/roughness texture
                if pbr.metallicRoughnessTexture:
                    tex_idx = pbr.metallicRoughnessTexture.index
                    material.metallic_roughness_texture = self._load_texture(gltf, tex_idx, model_dir)
                    # Load texture transform if present
                    material.metallic_roughness_transform = self._load_texture_transform(pbr.metallicRoughnessTexture)

                # Metallic/roughness factors
                if pbr.metallicFactor is not None:
                    material.metallic_factor = pbr.metallicFactor
                if pbr.roughnessFactor is not None:
                    material.roughness_factor = pbr.roughnessFactor

            # Normal map
            if gltf_mat.normalTexture:
                tex_idx = gltf_mat.normalTexture.index
                material.normal_texture = self._load_texture(gltf, tex_idx, model_dir)
                # Load texture transform if present
                material.normal_transform = self._load_texture_transform(gltf_mat.normalTexture)
                # Load normal scale (optional, defaults to 1.0)
                if hasattr(gltf_mat.normalTexture, 'scale') and gltf_mat.normalTexture.scale is not None:
                    material.normal_scale = gltf_mat.normalTexture.scale

            # Occlusion texture
            if gltf_mat.occlusionTexture:
                tex_idx = gltf_mat.occlusionTexture.index
                material.occlusion_texture = self._load_texture(gltf, tex_idx, model_dir)
                # Load texture transform if present
                material.occlusion_transform = self._load_texture_transform(gltf_mat.occlusionTexture)
                # Load occlusion strength (optional, defaults to 1.0)
                if hasattr(gltf_mat.occlusionTexture, 'strength') and gltf_mat.occlusionTexture.strength is not None:
                    material.occlusion_strength = gltf_mat.occlusionTexture.strength

            # Emissive texture
            if gltf_mat.emissiveTexture:
                tex_idx = gltf_mat.emissiveTexture.index
                material.emissive_texture = self._load_texture(gltf, tex_idx, model_dir)
                # Load texture transform if present
                material.emissive_transform = self._load_texture_transform(gltf_mat.emissiveTexture)

            # Emissive factor
            if gltf_mat.emissiveFactor is not None:
                material.emissive_factor = tuple(gltf_mat.emissiveFactor)

            # Alpha mode and cutoff
            if hasattr(gltf_mat, 'alphaMode') and gltf_mat.alphaMode:
                material.alpha_mode = gltf_mat.alphaMode  # "OPAQUE", "MASK", or "BLEND"
            if hasattr(gltf_mat, 'alphaCutoff') and gltf_mat.alphaCutoff is not None:
                material.alpha_cutoff = gltf_mat.alphaCutoff

            # Double-sided rendering
            if hasattr(gltf_mat, 'doubleSided') and gltf_mat.doubleSided:
                material.double_sided = True

            materials.append(material)
            print(f"  Material: {mat_name}")

            # Check for extensions (moved after material append for proper ordering)
            if hasattr(gltf_mat, 'extensions') and gltf_mat.extensions:
                # KHR_materials_unlit
                if 'KHR_materials_unlit' in gltf_mat.extensions:
                    material.unlit = True
                    print(f"    Unlit: True (KHR_materials_unlit)")

                # KHR_materials_emissive_strength
                if 'KHR_materials_emissive_strength' in gltf_mat.extensions:
                    emissive_ext = gltf_mat.extensions['KHR_materials_emissive_strength']
                    # Extension data is a dict, not an object
                    if isinstance(emissive_ext, dict) and 'emissiveStrength' in emissive_ext:
                        material.emissive_strength = emissive_ext['emissiveStrength']
                        print(f"    Emissive Strength: {material.emissive_strength} (KHR_materials_emissive_strength)")
            if material.emissive_texture or material.emissive_factor != (0.0, 0.0, 0.0):
                print(f"    Emissive: factor={material.emissive_factor}, texture={material.emissive_texture is not None}")

        return materials

    def _load_texture_transform(self, texture_info) -> Optional[TextureTransform]:
        """
        Load texture transform from GLTF texture info (KHR_texture_transform extension).

        Args:
            texture_info: GLTF texture info object (e.g., baseColorTexture, normalTexture, etc.)

        Returns:
            TextureTransform object if extension exists, None otherwise
        """
        if not hasattr(texture_info, 'extensions') or not texture_info.extensions:
            return None

        if 'KHR_texture_transform' not in texture_info.extensions:
            return None

        transform_data = texture_info.extensions['KHR_texture_transform']

        # Extract offset, scale, rotation from extension data
        offset = transform_data.get('offset', [0.0, 0.0])
        scale = transform_data.get('scale', [1.0, 1.0])
        rotation = transform_data.get('rotation', 0.0)
        texcoord = transform_data.get('texCoord', 0)

        return TextureTransform(
            offset=tuple(offset),
            scale=tuple(scale),
            rotation=rotation,
            texcoord=texcoord
        )

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
        Calculate bounding sphere radius for the model with node transforms applied.

        Args:
            gltf: GLTF data

        Returns:
            Bounding radius
        """
        max_radius = 0.0

        # Get the default scene (or first scene if no default)
        scene_idx = gltf.scene if gltf.scene is not None else 0
        if scene_idx >= len(gltf.scenes):
            # Fallback to simple calculation
            return self._calculate_bounding_radius_simple(gltf)

        scene = gltf.scenes[scene_idx]

        # Process each root node in the scene
        for node_idx in scene.nodes:
            max_radius = max(max_radius, self._calculate_node_bounding_radius(gltf, node_idx, Matrix44.identity()))

        return float(max_radius) if max_radius > 0 else 1.0

    def _compute_node_world_transforms(self, gltf: pygltflib.GLTF2) -> Dict[int, Matrix44]:
        """
        Compute world transforms for all nodes, including non-joint ancestors.

        Args:
            gltf: GLTF data

        Returns:
            Dictionary mapping node index to world transform (Matrix44)
        """
        node_world: Dict[int, Matrix44] = {}

        def traverse(node_idx: int, parent_transform: Matrix44):
            node = gltf.nodes[node_idx]
            local_transform = self._get_node_transform(node)
            world_transform = local_transform @ parent_transform
            node_world[node_idx] = world_transform
            if node.children:
                for child_idx in node.children:
                    traverse(child_idx, world_transform)

        if gltf.scenes:
            scene_indices = []
            if gltf.scene is not None and gltf.scene < len(gltf.scenes):
                scene_indices = [gltf.scene]
            else:
                scene_indices = list(range(len(gltf.scenes)))

            for scene_idx in scene_indices:
                scene = gltf.scenes[scene_idx]
                for node_idx in scene.nodes:
                    traverse(node_idx, Matrix44.identity())
        else:
            # Fallback: traverse any nodes not already visited
            for node_idx in range(len(gltf.nodes)):
                if node_idx not in node_world:
                    traverse(node_idx, Matrix44.identity())

        return node_world

    def _calculate_node_bounding_radius(self, gltf: pygltflib.GLTF2, node_idx: int, parent_transform: 'Matrix44') -> float:
        """
        Recursively calculate bounding radius for a node and its children.

        Args:
            gltf: GLTF data
            node_idx: Node index
            parent_transform: Parent transformation matrix

        Returns:
            Maximum bounding radius for this node and children
        """
        node = gltf.nodes[node_idx]
        max_radius = 0.0

        # Get local transform for this node
        local_transform = self._get_node_transform(node)

        # Accumulate with parent transform
        world_transform = parent_transform @ local_transform

        # If this node has a mesh, calculate its bounding radius with transform
        if node.mesh is not None:
            gltf_mesh = gltf.meshes[node.mesh]

            for primitive in gltf_mesh.primitives:
                if 'POSITION' not in primitive.attributes.__dict__:
                    continue

                positions = self._get_accessor_data(gltf, primitive.attributes.POSITION)
                if positions is None:
                    continue

                # Reshape to 3D points
                points = positions.reshape(-1, 3)

                # Apply world transform to each point and calculate distance from origin
                for point in points:
                    # Transform point to world space
                    point_4d = np.array([point[0], point[1], point[2], 1.0], dtype='f4')
                    transformed = world_transform @ point_4d

                    # Calculate distance from origin
                    radius = np.linalg.norm(transformed[:3])
                    max_radius = max(max_radius, radius)

        # Process children recursively
        if node.children:
            for child_idx in node.children:
                child_radius = self._calculate_node_bounding_radius(gltf, child_idx, world_transform)
                max_radius = max(max_radius, child_radius)

        return max_radius

    def _calculate_bounding_radius_simple(self, gltf: pygltflib.GLTF2) -> float:
        """
        Simple bounding radius calculation without transforms (fallback).

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

    def _load_skeleton(self, gltf: pygltflib.GLTF2) -> Skeleton:
        """
        Load skeleton from GLTF skins and nodes.

        Args:
            gltf: GLTF data

        Returns:
            Skeleton with joint hierarchy
        """
        skeleton = Skeleton()

        # Precompute world transforms for all nodes (including non-joint ancestors)
        node_world_transforms = self._compute_node_world_transforms(gltf)

        # Build parent map for nodes
        parent_map: Dict[int, int] = {}
        for idx, node in enumerate(gltf.nodes):
            if node.children:
                for child_idx in node.children:
                    parent_map[child_idx] = idx

        # GLTF stores joints as indices into the nodes array
        # We need to build the skeleton from all joints referenced by skins
        joint_indices = set()
        for skin in gltf.skins:
            joint_indices.update(skin.joints)

        # Create Joint objects for each joint node
        joint_map: Dict[int, Joint] = {}
        for joint_idx in sorted(joint_indices):
            node = gltf.nodes[joint_idx]
            joint = Joint(
                name=node.name if node.name else f"Joint_{joint_idx}",
                index=joint_idx,
                parent=None  # Set later
            )

            # Set local transform from node
            joint.local_transform = self._get_node_transform(node)
            local_array = np.array(joint.local_transform)
            joint.base_translation = Vector3(node.translation) if node.translation is not None else Vector3(local_array[3, :3])
            if node.rotation is not None:
                quat = node.rotation
                joint.base_rotation = Quaternion([quat[3], quat[0], quat[1], quat[2]])
            if node.scale is not None:
                joint.base_scale = Vector3(node.scale)

            joint_map[joint_idx] = joint
            skeleton.add_joint(joint)

        # Build parent-child relationships
        for joint_idx, joint in joint_map.items():
            node = gltf.nodes[joint_idx]

            # Check if this node has children that are also joints
            if node.children:
                for child_idx in node.children:
                    if child_idx in joint_map:
                        child_joint = joint_map[child_idx]
                        joint.add_child(child_joint)
                        child_joint.parent = joint

        # Rebuild root joints list now that hierarchy is set up
        skeleton.root_joints = [j for j in skeleton.joints if j.parent is None]

        # Assign root parent transforms (non-joint ancestors) for root joints
        for joint_idx, joint in joint_map.items():
            if joint.parent is not None:
                continue

            parent_idx = parent_map.get(joint_idx)
            root_parent_transform = Matrix44.identity()
            if parent_idx is not None and parent_idx not in joint_map:
                root_parent_transform = node_world_transforms.get(parent_idx, Matrix44.identity())
            joint.root_parent_transform = root_parent_transform
        
        # Initialize world transforms from bind pose
        skeleton.update_world_transforms()

        return skeleton

    def _load_skins(self, gltf: pygltflib.GLTF2, skeleton: Skeleton, meshes: List[Mesh]) -> List[Skin]:
        """
        Load skins from GLTF.

        Args:
            gltf: GLTF data
            skeleton: Loaded skeleton
            meshes: List of loaded meshes

        Returns:
            List of Skin objects
        """
        skins = []

        for skin_idx, gltf_skin in enumerate(gltf.skins):
            skin = Skin(name=gltf_skin.name if gltf_skin.name else f"Skin_{skin_idx}")

            # Get inverse bind matrices
            inv_bind_matrices = None
            if gltf_skin.inverseBindMatrices is not None:
                inv_bind_data = self._get_accessor_data(gltf, gltf_skin.inverseBindMatrices)
                if inv_bind_data is not None:
                    # Reshape to 4x4 matrices
                    num_joints = len(gltf_skin.joints)
                    inv_bind_matrices = inv_bind_data.reshape(num_joints, 4, 4)

            # Add joints to skin
            for i, joint_idx in enumerate(gltf_skin.joints):
                # Find joint by index property (not list position)
                joint = None
                for j in skeleton.joints:
                    if j.index == joint_idx:
                        joint = j
                        break

                if joint is None:
                    print(f"  Warning: Joint index {joint_idx} not found in skeleton")
                    continue

                # Get inverse bind matrix for this joint
                if inv_bind_matrices is not None:
                    inv_bind_matrix = Matrix44(inv_bind_matrices[i])
                else:
                    # Default to identity if not provided
                    inv_bind_matrix = Matrix44.identity()

                skin.add_joint(joint, inv_bind_matrix)

            # Initialize joint matrices with bind pose
            skin.update_joint_matrices()

            skins.append(skin)

            # Associate skin with meshes that use it
            # Find which mesh nodes reference this skin
            for node_idx, node in enumerate(gltf.nodes):
                if getattr(node, 'skin', None) != skin_idx:
                    continue

                for mesh in meshes:
                    if getattr(mesh, 'node_index', None) == node_idx:
                        mesh.skin = skin
                        mesh.is_skinned = True

        return skins

    def _load_animations(self, gltf: pygltflib.GLTF2, skeleton: Skeleton = None) -> Dict[str, Animation]:
        """
        Load animations from GLTF.

        Args:
            gltf: GLTF data
            skeleton: Loaded skeleton (optional, for skeletal animations)

        Returns:
            Dictionary mapping animation name to Animation object
        """
        animations = {}

        for anim_idx, gltf_anim in enumerate(gltf.animations):
            anim_name = gltf_anim.name if gltf_anim.name else f"Animation_{anim_idx}"
            animation = Animation(anim_name)

            # Process each channel in the animation
            for channel in gltf_anim.channels:
                # Get the sampler for this channel
                sampler = gltf_anim.samplers[channel.sampler]

                # Get target node (joint)
                target_node_idx = channel.target.node
                target_node = gltf.nodes[target_node_idx]
                target_node_name = target_node.name if target_node.name else f"Joint_{target_node_idx}"

                # Get target property (translation, rotation, scale, weights)
                target_path = channel.target.path
                if target_path == "translation":
                    target_property = AnimationTarget.TRANSLATION
                elif target_path == "rotation":
                    target_property = AnimationTarget.ROTATION
                elif target_path == "scale":
                    target_property = AnimationTarget.SCALE
                elif target_path == "weights":
                    target_property = AnimationTarget.WEIGHTS
                else:
                    print(f"  Warning: Unknown animation target path: {target_path}")
                    continue

                # Get interpolation type
                interp_str = sampler.interpolation if sampler.interpolation else "LINEAR"
                if interp_str == "LINEAR":
                    interpolation = InterpolationType.LINEAR
                elif interp_str == "STEP":
                    interpolation = InterpolationType.STEP
                elif interp_str == "CUBICSPLINE":
                    interpolation = InterpolationType.CUBICSPLINE
                else:
                    interpolation = InterpolationType.LINEAR

                # Create animation channel
                anim_channel = AnimationChannel(
                    target_node_name=target_node_name,
                    target_property=target_property,
                    interpolation=interpolation
                )

                # Load keyframe data
                times = self._get_accessor_data(gltf, sampler.input)
                values = self._get_accessor_data(gltf, sampler.output)

                if times is None or values is None:
                    print(f"  Warning: Missing keyframe data for channel {target_node_name}.{target_path}")
                    continue

                # Determine value size based on property type
                if target_property == AnimationTarget.TRANSLATION:
                    value_size = 3  # Vector3
                elif target_property == AnimationTarget.ROTATION:
                    value_size = 4  # Quaternion (x, y, z, w)
                elif target_property == AnimationTarget.SCALE:
                    value_size = 3  # Vector3
                elif target_property == AnimationTarget.WEIGHTS:
                    # Morph target weights - variable size
                    value_size = len(values) // len(times)
                else:
                    value_size = 1

                # Reshape values
                values = values.reshape(-1, value_size)

                # Add keyframes
                for i, time in enumerate(times):
                    value = values[i]

                    # Convert to appropriate type
                    if target_property == AnimationTarget.ROTATION:
                        # GLTF quaternions are (x, y, z, w)
                        value = Quaternion([value[3], value[0], value[1], value[2]])  # pyrr uses (w, x, y, z)
                    elif target_property in (AnimationTarget.TRANSLATION, AnimationTarget.SCALE):
                        value = Vector3(value)

                    anim_channel.add_keyframe(float(time), value)

                # Add channel to animation
                animation.add_channel(anim_channel)

            animations[anim_name] = animation

        return animations
