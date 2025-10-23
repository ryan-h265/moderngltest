"""
Scene Management

Handles scene objects and rendering.
"""

from typing import Dict, List, Tuple, Optional
from pyrr import Matrix44, Vector3
from moderngl_window import geometry
from . import geometry_utils
from .frustum import Frustum


class SceneObject:
    """
    Represents a renderable object in the scene.

    Each object has:
    - Geometry (VAO from moderngl_window.geometry)
    - Position in world space
    - Color
    - Bounding sphere for frustum culling
    """

    def __init__(self, geom, position: Vector3, color: Tuple[float, float, float],
                 bounding_radius: float = None, name: str = "Object"):
        """
        Initialize scene object.

        Args:
            geom: Geometry VAO from moderngl_window.geometry
            position: World space position
            color: RGB color tuple (0.0 to 1.0)
            bounding_radius: Radius of bounding sphere (auto-calculated if None)
            name: Debug name for this object
        """
        self.geometry = geom
        self.position = position
        self.color = color
        self.bounding_radius = bounding_radius if bounding_radius is not None else 1.0
        self.name = name

    def get_model_matrix(self) -> Matrix44:
        """
        Get the model matrix for this object.

        Returns:
            4x4 transformation matrix (currently just translation)
        """
        return Matrix44.from_translation(self.position)

    def is_visible(self, frustum: Frustum) -> bool:
        """
        Test if this object is visible in the given frustum.

        Args:
            frustum: View frustum to test against

        Returns:
            True if object is visible (inside or intersecting frustum)
        """
        return frustum.contains_sphere(self.position, self.bounding_radius)


class Scene:
    """
    Manages all objects in the scene.

    Provides methods to add objects and render them.
    """

    def __init__(self, ctx=None):
        """
        Initialize empty scene.

        Args:
            ctx: ModernGL context (required for custom geometry like pyramids and GLTF models)
        """
        self.objects: List[SceneObject] = []  # Can contain both SceneObject and Model instances
        self.ctx = ctx
        self.last_render_stats: Dict[str, Dict[str, object]] = {}

    def add_object(self, obj: SceneObject):
        """
        Add an object to the scene.

        Args:
            obj: SceneObject to add
        """
        self.objects.append(obj)

    def clear(self):
        """Remove all objects from the scene"""
        self.objects.clear()

    def create_default_scene(self):
        """
        Create the default scene with ground plane, mixed shapes, and GLTF models.

        Combines primitive shapes (cubes, spheres, pyramids, cones) with loaded GLTF models.
        """
        # Load GLTF models if context is available
        if self.ctx is not None:
            try:
                from ..loaders import GltfLoader
                from ..config.settings import PROJECT_ROOT
                import math

                loader = GltfLoader(self.ctx)
                models_loaded = 0

                # # 1. Japanese Stone Lantern - Center piece
                # lantern_path = PROJECT_ROOT / "assets/models/props/japanese_stone_lantern/scene.gltf"
                # if lantern_path.exists():
                #     print(f"Loading GLTF model: {lantern_path}")
                #     lantern = loader.load(str(lantern_path))
                #     lantern.position = Vector3([0.0, 0.0, 0.0])
                #     lantern.scale = Vector3([2.0, 2.0, 2.0])
                #     self.add_object(lantern)
                #     models_loaded += 1
                #     print(f"  ✓ Added japanese_stone_lantern ({len(lantern.meshes)} meshes)")

                # 2. Tent - Place to the right
                # tent_path = PROJECT_ROOT / "assets/models/props/tent/scene.gltf"
                # if tent_path.exists():
                #     print(f"Loading GLTF model: {tent_path}")
                #     tent = loader.load(str(tent_path))
                #     tent.position = Vector3([6.0, 0.0, 3.0])
                #     tent.scale = Vector3([1.5, 1.5, 1.5])
                #     tent.rotation = Vector3([0.0, math.radians(-30), 0.0])  # Rotate toward center
                #     self.add_object(tent)
                #     models_loaded += 1
                #     print(f"  ✓ Added tent ({len(tent.meshes)} meshes)")

                # 3. Japanese Bar - Place to the left
                bar_path = PROJECT_ROOT / "assets/models/props/japanese_bar/scene.gltf"
                if bar_path.exists():
                    print(f"Loading GLTF model: {bar_path}")
                    bar = loader.load(str(bar_path))
                    bar.position = Vector3([-7.0, 0.0, -2.0])
                    bar.scale = Vector3([1.2, 1.2, 1.2])
                    bar.rotation = Vector3([0.0, math.radians(20), 0.0])  # Rotate toward center
                    self.add_object(bar)
                    models_loaded += 1
                    print(f"  ✓ Added japanese_bar ({len(bar.meshes)} meshes)")

                print(f"\n=== Loaded {models_loaded} GLTF models successfully ===\n")

            except Exception as e:
                print(f"  Warning: Failed to load GLTF models: {e}")
                import traceback
                traceback.print_exc()

        # Ground plane
        ground = SceneObject(
            geometry.cube(size=(20.0, 0.5, 20.0)),
            Vector3([0.0, -0.25, 0.0]),
            (0.3, 0.6, 0.3),  # Green
            bounding_radius=14.15,  # sqrt(10^2 + 10^2) for ground
            name="Ground"
        )
        self.add_object(ground)

        # Sphere 1 - Red
        sphere1 = SceneObject(
            geometry.sphere(radius=1.0),
            Vector3([-10.0, 1.0, 10.0]),
            (0.8, 0.3, 0.3),
            bounding_radius=1.0,
            name="Sphere1_Red"
        )
        self.add_object(sphere1)

        # # Cube 2 - Blue
        # cube2 = SceneObject(
        #     geometry.cube(size=(1.5, 3.0, 1.5)),
        #     Vector3([3.0, 1.5, -2.0]),
        #     (0.3, 0.3, 0.8),
        #     bounding_radius=1.9,  # Half diagonal of cube
        #     name="Cube2_Blue"
        # )
        # self.add_object(cube2)

        # # Pyramid 3 - Yellow
        # pyramid3 = SceneObject(
        #     geometry_utils.pyramid(base_size=1.0, height=1.5),
        #     Vector3([0.0, 0.0, 3.0]),
        #     (0.8, 0.8, 0.3),
        #     bounding_radius=1.0
        # )
        # self.add_object(pyramid3)

        # # Sphere 5 - Purple
        # sphere5 = SceneObject(
        #     geometry.sphere(radius=1.2),
        #     Vector3([6.0, 1.25, 3.0]),
        #     (0.5, 0.2, 0.8),
        #     bounding_radius=1.2
        # )
        # self.add_object(sphere5)

        # # Pyramid 6 - Cyan
        # pyramid6 = SceneObject(
        #     geometry_utils.pyramid(base_size=1.5, height=2.0),
        #     Vector3([-2.0, 0.0, -6.0]),
        #     (0.2, 0.8, 0.8),
        #     bounding_radius=1.5
        # )
        # self.add_object(pyramid6)

        # # Sphere 7 - Pink
        # sphere7 = SceneObject(
        #     geometry.sphere(radius=0.9),
        #     Vector3([4.5, 0.9, -5.0]),
        #     (0.9, 0.3, 0.6),
        #     bounding_radius=0.9
        # )
        # self.add_object(sphere7)

        # # Sphere 9 - Sea Green
        # sphere9 = SceneObject(
        #     geometry.sphere(radius=0.65),
        #     Vector3([-7.0, 0.65, 2.0]),
        #     (0.3, 0.7, 0.4),
        #     bounding_radius=0.65
        # )
        # self.add_object(sphere9)

        # # Cube 12 - Steel Blue
        # cube12 = SceneObject(
        #     geometry.cube(size=(1.1, 1.5, 1.1)),
        #     Vector3([7.5, 0.75, -2.0]),
        #     (0.4, 0.5, 0.8),
        #     bounding_radius=1.1
        # )
        # self.add_object(cube12)

        # # Sphere 13 - Peach
        # sphere13 = SceneObject(
        #     geometry.sphere(radius=0.35),
        #     Vector3([-1.0, 0.35, 7.0]),
        #     (0.9, 0.7, 0.5),
        #     bounding_radius=0.35
        # )
        # self.add_object(sphere13)

        # # Cone 14 - Plum
        # cone14 = SceneObject(
        #     geometry_utils.cone(radius=0.7, height=2.0),
        #     Vector3([5.5, 0.0, 1.0]),
        #     (0.5, 0.3, 0.6),
        #     bounding_radius=1.2
        # )
        # self.add_object(cone14)


    def render_all(self, program, frustum: Optional[Frustum] = None, debug_label: str = "",
                   textured_program=None):
        """
        Render all objects in the scene.

        Args:
            program: Shader program to use for rendering primitives
            frustum: Optional frustum for culling (if None, all objects rendered)
            debug_label: Label for debug output (e.g., "Main", "Shadow Light 0")
            textured_program: Optional shader program for textured models
        """
        from ..config.settings import DEBUG_FRUSTUM_CULLING, DEBUG_SHOW_CULLED_OBJECTS

        rendered_count = 0
        culled_count = 0
        culled_objects: List[str] = []

        for obj in self.objects:
            # Frustum culling (skip if outside view)
            if frustum is not None and not obj.is_visible(frustum):
                culled_count += 1
                if DEBUG_SHOW_CULLED_OBJECTS:
                    culled_objects.append(f"{obj.name} (pos: {obj.position}, radius: {obj.bounding_radius})")
                continue

            # Check if this is a Model (textured) or SceneObject (primitive)
            is_model = hasattr(obj, 'is_model') and obj.is_model

            if is_model:
                # Model objects need special handling
                if textured_program is not None:
                    # Use textured shader for models (geometry pass)
                    # Note: Camera uniforms are already set by GeometryRenderer
                    active_program = textured_program

                    # Set material defaults
                    if 'baseColorFactor' in active_program:
                        active_program['baseColorFactor'].value = (1.0, 1.0, 1.0, 1.0)
                    if 'hasBaseColorTexture' in active_program:
                        active_program['hasBaseColorTexture'].value = False
                    if 'hasNormalTexture' in active_program:
                        active_program['hasNormalTexture'].value = False
                    if 'hasMetallicRoughnessTexture' in active_program:
                        active_program['hasMetallicRoughnessTexture'].value = False

                    # Model handles its own rendering (sets model matrix, binds materials)
                    obj.render(active_program)
                else:
                    # Shadow pass or other passes without textured shader
                    # Render model using primitive shader (just geometry, no textures)
                    active_program = program

                    # Get parent model matrix
                    parent_matrix = obj.get_model_matrix()

                    # Render each mesh with its local transform
                    for mesh in obj.meshes:
                        mesh.render(active_program, parent_transform=parent_matrix)
            else:
                # Use primitive shader for regular SceneObjects
                active_program = program

                # Set model matrix
                model = obj.get_model_matrix()
                active_program['model'].write(model.astype('f4').tobytes())

                # Set color (only if this uniform exists in the shader)
                if 'object_color' in active_program:
                    active_program['object_color'].write(Vector3(obj.color).astype('f4').tobytes())

                # Render geometry
                obj.geometry.render(active_program)

            rendered_count += 1

        # Debug output
        label_key = debug_label if debug_label else "Main"
        self.last_render_stats[label_key] = {
            'rendered': rendered_count,
            'total': len(self.objects),
            'culled': culled_count,
            'culled_objects': culled_objects if DEBUG_SHOW_CULLED_OBJECTS else None,
            'frustum_applied': frustum is not None,
        }

        if DEBUG_FRUSTUM_CULLING and frustum is not None:
            label = f" [{label_key}]"
            print(f"Frustum Culling{label}: Rendered {rendered_count}/{len(self.objects)}, Culled {culled_count}")

        if DEBUG_SHOW_CULLED_OBJECTS and culled_objects:
            print(f"  Culled objects: {', '.join(culled_objects)}")

        return rendered_count

    def get_object_count(self) -> int:
        """Get number of objects in scene"""
        return len(self.objects)

    def get_visible_objects(self, frustum: Frustum) -> List['SceneObject']:
        """
        Get list of objects visible in frustum.

        Args:
            frustum: View frustum to test against

        Returns:
            List of visible objects
        """
        return [obj for obj in self.objects if obj.is_visible(frustum)]
