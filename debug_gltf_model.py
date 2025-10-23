#!/usr/bin/env python3
"""
GLTF Model Diagnostic Tool

Analyzes GLTF/GLB models to detect common issues like:
- Extreme transform values
- Incorrect coordinate systems
- Baked-in scaling/transforms
- Node hierarchy problems
- Material/texture issues

Usage:
    python debug_gltf_model.py path/to/model.gltf
"""

import sys
import numpy as np
from pathlib import Path
import pygltflib
from pyrr import Matrix44, Quaternion


class GltfDiagnostics:
    """Diagnostic tool for analyzing GLTF models."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        
    def analyze_model(self, filepath: str):
        """Analyze a GLTF model and report issues."""
        filepath = Path(filepath)
        print(f"🔍 Analyzing GLTF model: {filepath}")
        print("=" * 60)
        
        if not filepath.exists():
            print(f"❌ ERROR: File not found: {filepath}")
            return False
            
        try:
            gltf = pygltflib.GLTF2().load(str(filepath))
        except Exception as e:
            print(f"❌ ERROR: Failed to load GLTF: {e}")
            return False
            
        # Basic model info
        self._analyze_basic_info(gltf)
        
        # Scene hierarchy
        self._analyze_scene_hierarchy(gltf)
        
        # Materials and textures
        self._analyze_materials(gltf)
        
        # Summary
        self._print_summary()
        
        return len(self.issues) == 0
    
    def _analyze_basic_info(self, gltf):
        """Analyze basic model information."""
        print("\n📊 Basic Information:")
        print(f"   Scenes: {len(gltf.scenes) if gltf.scenes else 0}")
        print(f"   Nodes: {len(gltf.nodes) if gltf.nodes else 0}")
        print(f"   Meshes: {len(gltf.meshes) if gltf.meshes else 0}")
        print(f"   Materials: {len(gltf.materials) if gltf.materials else 0}")
        print(f"   Textures: {len(gltf.textures) if gltf.textures else 0}")
        
        # Check for empty model
        if not gltf.meshes or len(gltf.meshes) == 0:
            self.issues.append("Model has no meshes")
            
    def _analyze_scene_hierarchy(self, gltf):
        """Analyze scene hierarchy and node transforms."""
        print("\n🌳 Scene Hierarchy:")
        
        if not gltf.scenes:
            self.issues.append("Model has no scenes")
            return
            
        scene_idx = gltf.scene if gltf.scene is not None else 0
        if scene_idx >= len(gltf.scenes):
            self.issues.append("Invalid default scene index")
            return
            
        scene = gltf.scenes[scene_idx]
        print(f"   Default scene: {scene_idx}")
        print(f"   Root nodes: {len(scene.nodes)}")
        
        # Analyze each root node
        for node_idx in scene.nodes:
            self._analyze_node_hierarchy(gltf, node_idx, Matrix44.identity(), 0)
    
    def _analyze_node_hierarchy(self, gltf, node_idx, parent_transform, depth):
        """Recursively analyze node hierarchy."""
        if node_idx >= len(gltf.nodes):
            self.issues.append(f"Invalid node index: {node_idx}")
            return
            
        node = gltf.nodes[node_idx]
        node_name = getattr(node, 'name', f'Node_{node_idx}')
        indent = "   " + "  " * depth
        
        print(f"{indent}📦 Node {node_idx}: '{node_name}'")
        
        # Get local transform
        local_transform = self._get_node_transform(node)
        world_transform = parent_transform @ local_transform
        
        # Analyze transform properties
        self._analyze_transform(local_transform, world_transform, indent, node_name)
        
        # Check if node has mesh
        if hasattr(node, 'mesh') and node.mesh is not None:
            if node.mesh >= len(gltf.meshes):
                self.issues.append(f"Node '{node_name}' references invalid mesh: {node.mesh}")
            else:
                mesh = gltf.meshes[node.mesh]
                vertex_count = self._count_mesh_vertices(gltf, mesh)
                print(f"{indent}  🔺 Mesh: {len(mesh.primitives)} primitives, ~{vertex_count} vertices")
        
        # Process children
        if hasattr(node, 'children') and node.children:
            for child_idx in node.children:
                self._analyze_node_hierarchy(gltf, child_idx, world_transform, depth + 1)
    
    def _analyze_transform(self, local_transform, world_transform, indent, node_name):
        """Analyze transform matrices for issues."""
        # Check local transform
        local_flat = local_transform.flatten()
        local_max = max(abs(x) for x in local_flat)
        local_det = np.linalg.det(local_transform[:3, :3])
        
        print(f"{indent}  📐 Transform max: {local_max:.3f}, det: {local_det:.3f}")
        
        # Check for extreme values
        if local_max > 100:
            issue = f"Node '{node_name}' has extreme transform values (max: {local_max:.1f})"
            self.issues.append(issue)
            print(f"{indent}  ❌ {issue}")
            
        # Check for extreme scaling
        if abs(local_det) > 1000:
            issue = f"Node '{node_name}' has extreme scaling (det: {local_det:.1f})"
            self.issues.append(issue)
            print(f"{indent}  ❌ {issue}")
        elif abs(local_det) < 0.001:
            issue = f"Node '{node_name}' has near-zero scaling (det: {local_det:.6f})"
            self.issues.append(issue)
            print(f"{indent}  ❌ {issue}")
            
        # Check for negative scaling (mirroring)
        if local_det < 0:
            warning = f"Node '{node_name}' has negative scaling (mirrored geometry)"
            self.warnings.append(warning)
            print(f"{indent}  ⚠️  {warning}")
            
        # Check world transform accumulation
        world_flat = world_transform.flatten()
        world_max = max(abs(x) for x in world_flat)
        if world_max > 200:
            issue = f"Node '{node_name}' accumulated extreme world transform (max: {world_max:.1f})"
            self.issues.append(issue)
            print(f"{indent}  ❌ {issue}")
    
    def _get_node_transform(self, node):
        """Extract transformation matrix from a GLTF node."""
        # Check if node has a matrix property
        if hasattr(node, 'matrix') and node.matrix is not None and len(node.matrix) == 16:
            # Matrix is provided directly (column-major)
            matrix = np.array(node.matrix, dtype='f4').reshape(4, 4)
            # GLTF uses column-major, pyrr uses row-major, so transpose
            return Matrix44(matrix.T)

        # Otherwise, compose from TRS (Translation, Rotation, Scale)
        matrix = Matrix44.identity()

        # Apply scale
        if hasattr(node, 'scale') and node.scale is not None:
            s = node.scale
            matrix = matrix @ Matrix44.from_scale([s[0], s[1], s[2]])

        # Apply rotation (quaternion)
        if hasattr(node, 'rotation') and node.rotation is not None:
            q = node.rotation  # [x, y, z, w]
            # Create quaternion and convert to matrix
            quat = Quaternion([q[3], q[0], q[1], q[2]])  # pyrr uses [w, x, y, z]
            matrix = matrix @ Matrix44.from_quaternion(quat)

        # Apply translation
        if hasattr(node, 'translation') and node.translation is not None:
            t = node.translation
            matrix = matrix @ Matrix44.from_translation([t[0], t[1], t[2]])

        return matrix
    
    def _count_mesh_vertices(self, gltf, mesh):
        """Estimate vertex count for a mesh."""
        total_vertices = 0
        for primitive in mesh.primitives:
            if hasattr(primitive.attributes, 'POSITION') and primitive.attributes.POSITION is not None:
                accessor = gltf.accessors[primitive.attributes.POSITION]
                total_vertices += accessor.count
        return total_vertices
    
    def _analyze_materials(self, gltf):
        """Analyze materials and textures."""
        print("\n🎨 Materials & Textures:")
        
        if not gltf.materials:
            self.warnings.append("Model has no materials (will use default)")
            print("   ⚠️  No materials defined")
            return
            
        for i, material in enumerate(gltf.materials):
            mat_name = getattr(material, 'name', f'Material_{i}')
            print(f"   🎭 Material {i}: '{mat_name}'")
            
            # Check PBR properties
            if hasattr(material, 'pbrMetallicRoughness') and material.pbrMetallicRoughness:
                pbr = material.pbrMetallicRoughness
                if hasattr(pbr, 'baseColorTexture') and pbr.baseColorTexture:
                    print(f"      📷 Base color texture: {pbr.baseColorTexture.index}")
                if hasattr(pbr, 'metallicRoughnessTexture') and pbr.metallicRoughnessTexture:
                    print(f"      📷 Metallic/Roughness texture: {pbr.metallicRoughnessTexture.index}")
                    
            # Check normal map
            if hasattr(material, 'normalTexture') and material.normalTexture:
                print(f"      📷 Normal map: {material.normalTexture.index}")
    
    def _print_summary(self):
        """Print analysis summary."""
        print("\n" + "=" * 60)
        print("📋 Analysis Summary:")
        
        if not self.issues and not self.warnings:
            print("   ✅ No issues found! Model looks good.")
        else:
            if self.issues:
                print(f"   ❌ {len(self.issues)} Critical Issues:")
                for issue in self.issues:
                    print(f"      • {issue}")
                    
            if self.warnings:
                print(f"   ⚠️  {len(self.warnings)} Warnings:")
                for warning in self.warnings:
                    print(f"      • {warning}")
        
        # Recommendations
        if self.issues:
            print("\n💡 Recommendations:")
            has_transform_issues = any("transform" in issue.lower() or "scaling" in issue.lower() 
                                     for issue in self.issues)
            if has_transform_issues:
                print("   • Re-export the model with 'Apply All Transforms' in Blender")
                print("   • Ensure proper coordinate system (Y-up) during export")
                print("   • Avoid baking extreme scales into node hierarchy")


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python debug_gltf_model.py path/to/model.gltf")
        sys.exit(1)
    
    model_path = sys.argv[1]
    diagnostics = GltfDiagnostics()
    
    success = diagnostics.analyze_model(model_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()