"""
Model

Represents a loaded GLTF/GLB model with meshes and materials.
"""

from typing import List, Tuple, Optional, Dict
from pyrr import Matrix44, Vector3, Quaternion
from .material import Material


class Mesh:
    """
    Single mesh with geometry and material.

    Each mesh represents a renderable piece of geometry with:
    - VAO (Vertex Array Object) for rendering
    - Material for shading
    - Local transform (relative to parent model)
    """

    def __init__(self, vao, material: Material, local_transform: Matrix44 = None, node_name: str = None, parent_transform: Matrix44 = None):
        """
        Initialize mesh.

        Args:
            vao: Vertex Array Object
            material: Material for this mesh
            local_transform: Local transformation matrix (relative to parent)
            node_name: Name of the GLTF node this mesh came from (for animations)
            parent_transform: Accumulated transform from parent nodes (for animations)
        """
        self.vao = vao
        self.material = material
        self.local_transform = Matrix44(local_transform) if local_transform is not None else Matrix44.identity()
        self.node_name = node_name
        
        # For node animations: track parent hierarchy transform and base local matrix
        if parent_transform is not None:
            self.parent_transform = Matrix44(parent_transform)
        else:
            self.parent_transform = Matrix44.identity()
        self.base_local_transform = Matrix44(self.local_transform)
        self.mesh_index = None
        self.node_index = None
        self.base_translation = Vector3([0.0, 0.0, 0.0])
        self.base_rotation = Quaternion([1.0, 0.0, 0.0, 0.0])
        self.base_scale = Vector3([1.0, 1.0, 1.0])
        
        # Skinning data (set by loader if this is a skinned mesh)
        self.is_skinned = False
        self.skin = None

    def render(self, program, parent_transform: Matrix44 = None, ctx=None):
        """
        Render this mesh with optional parent transform.

        Args:
            program: Shader program to use
            parent_transform: Parent model matrix (applied before local transform)
            ctx: ModernGL context (for face culling control)
        """
        # Handle double-sided materials (disable backface culling)
        restore_culling = False
        if ctx and self.material.double_sided:
            # Check if culling is currently enabled
            import moderngl
            if ctx.front_face == 'ccw':  # Default state has culling enabled
                ctx.disable(moderngl.CULL_FACE)
                restore_culling = True

        # Calculate final transform (row-major matrices; GPU treats transpose as column-major)
        final_transform = self.local_transform @ self.parent_transform
        if parent_transform is not None:
            final_transform = final_transform @ parent_transform

        if 'model' in program:
            program['model'].write(final_transform.astype('f4').tobytes())

        # Bind material textures
        self.material.bind_textures(program)

        # Render geometry
        self.vao.render(program)

        # Restore culling state
        if restore_culling:
            import moderngl
            ctx.enable(moderngl.CULL_FACE)


class Model:
    """
    Represents a complete GLTF/GLB model with multiple meshes.

    Compatible with SceneObject interface for rendering in Scene.
    """

    def __init__(self, meshes: List[Mesh], position: Vector3 = None,
                 rotation: Vector3 = None, scale: Vector3 = None,
                 name: str = "Model"):
        """
        Initialize model.

        Args:
            meshes: List of Mesh objects
            position: World space position (default: origin)
            rotation: Rotation in radians (yaw, pitch, roll)
            scale: Scale factors (default: uniform 1.0)
            name: Model name for debugging
        """
        self.meshes = meshes
        self.position = position if position is not None else Vector3([0.0, 0.0, 0.0])
        self.rotation = rotation if rotation is not None else Vector3([0.0, 0.0, 0.0])
        self.scale = scale if scale is not None else Vector3([1.0, 1.0, 1.0])
        self.name = name
        self.orientation: Optional[Quaternion] = None

        # For frustum culling (SceneObject compatibility)
        self.bounding_radius = 2.0  # Default, should be calculated from model bounds

        # Flag to identify this as a Model (not a primitive SceneObject)
        self.is_model = True

        # Animation data (set by loader)
        self.skeleton = None  # Skeleton instance
        self.skins = []  # List of Skin instances
        self.animations: Dict[str, 'Animation'] = {}  # Animation name -> Animation
        self.animation_controller = None  # AnimationController instance (for skeletal animations)
        
        # Node animation data (for non-skeletal animations)
        self.current_node_animation = None
        self.node_animation_time = 0.0
        self.node_animation_playing = False
        self.node_animation_loop = True

    def get_model_matrix(self) -> Matrix44:
        """
        Get the model transformation matrix.

        Returns:
            4x4 transformation matrix
        """
        # Start with translation
        matrix = Matrix44.from_translation(self.position)

        # Apply rotation (yaw, pitch, roll)
        if self.orientation is not None:
            matrix = matrix * Matrix44.from_quaternion(self.orientation)
        else:
            if self.rotation.x != 0.0:
                matrix = matrix * Matrix44.from_y_rotation(self.rotation.x)
            if self.rotation.y != 0.0:
                matrix = matrix * Matrix44.from_x_rotation(self.rotation.y)
            if self.rotation.z != 0.0:
                matrix = matrix * Matrix44.from_z_rotation(self.rotation.z)

        # Apply scale
        if self.scale != Vector3([1.0, 1.0, 1.0]):
            matrix = matrix * Matrix44.from_scale(self.scale)

        return matrix

    def is_visible(self, frustum) -> bool:
        """
        Test if this model is visible in the given frustum.

        Args:
            frustum: View frustum to test against

        Returns:
            True if model is visible
        """
        return frustum.contains_sphere(self.position, self.bounding_radius)

    def apply_physics_transform(
        self,
        position,
        orientation,
    ) -> None:
        """Apply a transform from the physics simulation to this model."""

        self.position = Vector3(position)
        self.orientation = Quaternion(orientation).normalised
        self.rotation = Vector3([0.0, 0.0, 0.0])

    def render(self, program, ctx=None):
        """
        Render all meshes in this model.

        Args:
            program: Shader program to use
            ctx: ModernGL context (for face culling control)
        """
        # Get parent model matrix (position, rotation, scale of the whole model)
        parent_matrix = self.get_model_matrix()

        # Render each mesh with its local transform
        for mesh in self.meshes:
            mesh.render(program, parent_transform=parent_matrix, ctx=ctx)

    def update(self, delta_time: float) -> bool:
        """
        Update model animations.

        Args:
            delta_time: Time elapsed since last frame (seconds)

        Returns:
            True if the model applied animation updates this frame
        """
        animated = False

        # Update skeletal animations
        if self.animation_controller:
            was_playing = bool(self.animation_controller.current_animation and self.animation_controller.is_playing)
            self.animation_controller.update(delta_time)
            if was_playing:
                animated = True

            # Update skin joint matrices
            for skin in self.skins:
                skin.update_joint_matrices()
        
        # Reset mesh local transforms to bind pose before applying node animations
        for mesh in self.meshes:
            mesh.local_transform = Matrix44(mesh.base_local_transform)
        
        # Update node animations (for non-skeletal animations)
        if self.node_animation_playing and self.current_node_animation:
            from pyrr import Quaternion
            
            # Advance time
            self.node_animation_time += delta_time
            
            # Handle looping
            if self.node_animation_time >= self.current_node_animation.duration:
                if self.node_animation_loop:
                    self.node_animation_time = self.node_animation_time % self.current_node_animation.duration
                else:
                    self.node_animation_time = self.current_node_animation.duration
                    self.node_animation_playing = False
            
            # Sample animation at current time
            sampled_data = self.current_node_animation.sample_all(self.node_animation_time)
            
            # Apply to meshes by node name
            for mesh in self.meshes:
                if mesh.node_name is None:
                    continue
                
                # Check if this node has any animation data
                has_animation_for_node = False
                for (node_name, property_type), value in sampled_data.items():
                    if node_name == mesh.node_name:
                        has_animation_for_node = True
                        break
                
                if not has_animation_for_node:
                    # No animation for this node, keep base transform
                    continue
                
                # Gather transforms for this node
                translation = None
                rotation = None
                scale = None
                
                from ..animation.animation import AnimationTarget
                for (node_name, property_type), value in sampled_data.items():
                    if node_name != mesh.node_name:
                        continue
                    
                    if property_type == AnimationTarget.TRANSLATION:
                        translation = value
                    elif property_type == AnimationTarget.ROTATION:
                        rotation = value
                    elif property_type == AnimationTarget.SCALE:
                        scale = value
                
                # Fallback to bind pose components when animation omits them
                translation = translation if translation is not None else mesh.base_translation
                rotation = rotation if rotation is not None else mesh.base_rotation
                scale = scale if scale is not None else mesh.base_scale

                # Build transformation matrix from T/R/S
                mat = Matrix44.identity()

                # Apply scale first (match loader order)
                if scale is not None:
                    scale_vec = scale if isinstance(scale, Vector3) else Vector3(scale)
                    mat = mat @ Matrix44.from_scale(scale_vec)

                # Apply rotation
                if rotation is not None:
                    if isinstance(rotation, (list, tuple)):
                        rot_quat = Quaternion(rotation)
                    elif isinstance(rotation, Quaternion):
                        rot_quat = rotation
                    else:
                        rot_quat = Quaternion(rotation)
                    mat = mat @ rot_quat.matrix44

                # Apply translation last
                if translation is not None:
                    trans_vec = translation if isinstance(translation, Vector3) else Vector3(translation)
                    mat = mat @ Matrix44.from_translation(trans_vec)
                
                # Update the local transform for this mesh (parent applied during render)
                mesh.local_transform = mat

            animated = True

        return animated

    def play_animation(self, name: str, loop: bool = True):
        """
        Play an animation by name.

        Args:
            name: Animation name
            loop: Whether to loop the animation
        """
        if name not in self.animations:
            return
        
        # Check if this is a skeletal animation or node animation
        if self.animation_controller:
            # Try skeletal animation first
            self.animation_controller.play(self.animations[name], loop)
        else:
            # Use node animation system
            self.current_node_animation = self.animations[name]
            self.node_animation_time = 0.0
            self.node_animation_playing = True
            self.node_animation_loop = loop

    def stop_animation(self):
        """Stop current animation."""
        if self.animation_controller:
            self.animation_controller.stop()

    def release(self):
        """Release GPU resources"""
        for mesh in self.meshes:
            mesh.vao.release()
            mesh.material.release()
