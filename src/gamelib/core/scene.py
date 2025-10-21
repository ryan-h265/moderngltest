"""
Scene Management

Handles scene objects and rendering.
"""

from typing import List, Tuple
from pyrr import Matrix44, Vector3
from moderngl_window import geometry
from . import geometry_utils


class SceneObject:
    """
    Represents a renderable object in the scene.

    Each object has:
    - Geometry (VAO from moderngl_window.geometry)
    - Position in world space
    - Color
    """

    def __init__(self, geom, position: Vector3, color: Tuple[float, float, float]):
        """
        Initialize scene object.

        Args:
            geom: Geometry VAO from moderngl_window.geometry
            position: World space position
            color: RGB color tuple (0.0 to 1.0)
        """
        self.geometry = geom
        self.position = position
        self.color = color

    def get_model_matrix(self) -> Matrix44:
        """
        Get the model matrix for this object.

        Returns:
            4x4 transformation matrix (currently just translation)
        """
        return Matrix44.from_translation(self.position)


class Scene:
    """
    Manages all objects in the scene.

    Provides methods to add objects and render them.
    """

    def __init__(self, ctx=None):
        """
        Initialize empty scene.

        Args:
            ctx: ModernGL context (required for custom geometry like pyramids)
        """
        self.objects: List[SceneObject] = []
        self.ctx = ctx

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
        Create the default scene with ground plane and mixed shapes (cubes, spheres, pyramids, cones).

        This is the scene from the original game.py, now with variety in shapes.
        """
        # Ground plane
        ground = SceneObject(
            geometry.cube(size=(20.0, 0.5, 20.0)),
            Vector3([0.0, -0.25, 0.0]),
            (0.3, 0.6, 0.3)  # Green
        )
        self.add_object(ground)

        # Sphere 1 - Red
        sphere1 = SceneObject(
            geometry.sphere(radius=1.0),
            Vector3([-3.0, 1.0, 0.0]),
            (0.8, 0.3, 0.3)
        )
        self.add_object(sphere1)

        # Cube 2 - Blue
        cube2 = SceneObject(
            geometry.cube(size=(1.5, 3.0, 1.5)),
            Vector3([3.0, 1.5, -2.0]),
            (0.3, 0.3, 0.8)
        )
        self.add_object(cube2)

        # Pyramid 3 - Yellow
        pyramid3 = SceneObject(
            geometry_utils.pyramid(base_size=1.0, height=1.5),
            Vector3([0.0, 0.0, 3.0]),
            (0.8, 0.8, 0.3)
        )
        self.add_object(pyramid3)

        # Cube 4 - Orange
        cube4 = SceneObject(
            geometry.cube(size=(1.2, 1.2, 1.2)),
            Vector3([-5.0, 0.6, -4.0]),
            (0.9, 0.5, 0.2)
        )
        self.add_object(cube4)

        # Sphere 5 - Purple
        sphere5 = SceneObject(
            geometry.sphere(radius=1.2),
            Vector3([6.0, 1.25, 3.0]),
            (0.5, 0.2, 0.8)
        )
        self.add_object(sphere5)

        # Pyramid 6 - Cyan
        pyramid6 = SceneObject(
            geometry_utils.pyramid( base_size=1.5, height=2.0),
            Vector3([-2.0, 0.0, -6.0]),
            (0.2, 0.8, 0.8)
        )
        self.add_object(pyramid6)

        # Sphere 7 - Pink
        sphere7 = SceneObject(
            geometry.sphere(radius=0.9),
            Vector3([4.5, 0.9, -5.0]),
            (0.9, 0.3, 0.6)
        )
        self.add_object(sphere7)

        # Cone 8 - Olive
        cone8 = SceneObject(
            geometry_utils.cone( radius=1.0, height=2.0),
            Vector3([1.5, 0.0, 6.0]),
            (0.6, 0.6, 0.2)
        )
        self.add_object(cone8)

        # Sphere 9 - Sea Green
        sphere9 = SceneObject(
            geometry.sphere(radius=0.65),
            Vector3([-7.0, 0.65, 2.0]),
            (0.3, 0.7, 0.4)
        )
        self.add_object(sphere9)

        # Cube 10 - Gold
        cube10 = SceneObject(
            geometry.cube(size=(0.9, 2.0, 0.9)),
            Vector3([2.5, 1.0, -3.0]),
            (0.8, 0.6, 0.3)
        )
        self.add_object(cube10)

        # Pyramid 11 - Maroon
        pyramid11 = SceneObject(
            geometry_utils.pyramid( base_size=1.6, height=1.5),
            Vector3([-4.0, 0.0, 5.0]),
            (0.7, 0.3, 0.3)
        )
        self.add_object(pyramid11)

        # Cube 12 - Steel Blue
        cube12 = SceneObject(
            geometry.cube(size=(1.1, 1.5, 1.1)),
            Vector3([7.5, 0.75, -2.0]),
            (0.4, 0.5, 0.8)
        )
        self.add_object(cube12)

        # Sphere 13 - Peach
        sphere13 = SceneObject(
            geometry.sphere(radius=0.35),
            Vector3([-1.0, 0.35, 7.0]),
            (0.9, 0.7, 0.5)
        )
        self.add_object(sphere13)

        # Cone 14 - Plum
        cone14 = SceneObject(
            geometry_utils.cone( radius=0.7, height=2.0),
            Vector3([5.5, 0.0, 1.0]),
            (0.5, 0.3, 0.6)
        )
        self.add_object(cone14)

        # Sphere 15 - Teal
        sphere15 = SceneObject(
            geometry.sphere(radius=0.9),
            Vector3([-6.0, 0.9, -1.5]),
            (0.3, 0.6, 0.6)
        )
        self.add_object(sphere15)

        # Pyramid 16 - Rust
        pyramid16 = SceneObject(
            geometry_utils.pyramid( base_size=1.0, height=2.5),
            Vector3([3.5, 0.0, 4.5]),
            (0.8, 0.4, 0.2)
        )
        self.add_object(pyramid16)

        # Sphere 17 - Lime
        sphere17 = SceneObject(
            geometry.sphere(radius=0.6),
            Vector3([-3.5, 0.6, -2.5]),
            (0.5, 0.8, 0.3)
        )
        self.add_object(sphere17)

        # Cone 18 - Lavender
        cone18 = SceneObject(
            geometry_utils.cone( radius=0.4, height=1.8),
            Vector3([8.0, 0.0, 4.0]),
            (0.6, 0.4, 0.7)
        )
        self.add_object(cone18)

    def render_all(self, program):
        """
        Render all objects in the scene.

        Args:
            program: Shader program to use for rendering
        """
        for obj in self.objects:
            # Set model matrix
            model = obj.get_model_matrix()
            program['model'].write(model.astype('f4').tobytes())

            # Set color (only if this uniform exists in the shader)
            if 'object_color' in program:
                program['object_color'].write(Vector3(obj.color).astype('f4').tobytes())

            # Render geometry
            obj.geometry.render(program)

    def get_object_count(self) -> int:
        """Get number of objects in scene"""
        return len(self.objects)
