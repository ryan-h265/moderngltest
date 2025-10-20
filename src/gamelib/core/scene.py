"""
Scene Management

Handles scene objects and rendering.
"""

from typing import List, Tuple
from pyrr import Matrix44, Vector3
from moderngl_window import geometry


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

    def __init__(self):
        """Initialize empty scene"""
        self.objects: List[SceneObject] = []

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
        Create the default scene with ground plane and 18 cubes.

        This is the scene from the original game.py.
        """
        # Ground plane
        ground = SceneObject(
            geometry.cube(size=(20.0, 0.5, 20.0)),
            Vector3([0.0, -0.25, 0.0]),
            (0.3, 0.6, 0.3)  # Green
        )
        self.add_object(ground)

        # Cube 1 - Red
        cube1 = SceneObject(
            geometry.cube(size=(2.0, 2.0, 2.0)),
            Vector3([-3.0, 1.0, 0.0]),
            (0.8, 0.3, 0.3)
        )
        self.add_object(cube1)

        # Cube 2 - Blue
        cube2 = SceneObject(
            geometry.cube(size=(1.5, 3.0, 1.5)),
            Vector3([3.0, 1.5, -2.0]),
            (0.3, 0.3, 0.8)
        )
        self.add_object(cube2)

        # Cube 3 - Yellow
        cube3 = SceneObject(
            geometry.cube(size=(1.0, 1.0, 1.0)),
            Vector3([0.0, 0.5, 3.0]),
            (0.8, 0.8, 0.3)
        )
        self.add_object(cube3)

        # Cube 4 - Orange
        cube4 = SceneObject(
            geometry.cube(size=(1.2, 1.2, 1.2)),
            Vector3([-5.0, 0.6, -4.0]),
            (0.9, 0.5, 0.2)
        )
        self.add_object(cube4)

        # Cube 5 - Purple
        cube5 = SceneObject(
            geometry.cube(size=(0.8, 2.5, 0.8)),
            Vector3([6.0, 1.25, 3.0]),
            (0.5, 0.2, 0.8)
        )
        self.add_object(cube5)

        # Cube 6 - Cyan
        cube6 = SceneObject(
            geometry.cube(size=(1.5, 1.0, 1.5)),
            Vector3([-2.0, 0.5, -6.0]),
            (0.2, 0.8, 0.8)
        )
        self.add_object(cube6)

        # Cube 7 - Pink
        cube7 = SceneObject(
            geometry.cube(size=(1.0, 1.8, 1.0)),
            Vector3([4.5, 0.9, -5.0]),
            (0.9, 0.3, 0.6)
        )
        self.add_object(cube7)

        # Cube 8 - Olive
        cube8 = SceneObject(
            geometry.cube(size=(2.0, 0.8, 2.0)),
            Vector3([1.5, 0.4, 6.0]),
            (0.6, 0.6, 0.2)
        )
        self.add_object(cube8)

        # Cube 9 - Sea Green
        cube9 = SceneObject(
            geometry.cube(size=(1.3, 1.3, 1.3)),
            Vector3([-7.0, 0.65, 2.0]),
            (0.3, 0.7, 0.4)
        )
        self.add_object(cube9)

        # Cube 10 - Gold
        cube10 = SceneObject(
            geometry.cube(size=(0.9, 2.0, 0.9)),
            Vector3([2.5, 1.0, -3.0]),
            (0.8, 0.6, 0.3)
        )
        self.add_object(cube10)

        # Cube 11 - Maroon
        cube11 = SceneObject(
            geometry.cube(size=(1.6, 1.2, 1.6)),
            Vector3([-4.0, 0.6, 5.0]),
            (0.7, 0.3, 0.3)
        )
        self.add_object(cube11)

        # Cube 12 - Steel Blue
        cube12 = SceneObject(
            geometry.cube(size=(1.1, 1.5, 1.1)),
            Vector3([7.5, 0.75, -2.0]),
            (0.4, 0.5, 0.8)
        )
        self.add_object(cube12)

        # Cube 13 - Peach
        cube13 = SceneObject(
            geometry.cube(size=(0.7, 0.7, 0.7)),
            Vector3([-1.0, 0.35, 7.0]),
            (0.9, 0.7, 0.5)
        )
        self.add_object(cube13)

        # Cube 14 - Plum
        cube14 = SceneObject(
            geometry.cube(size=(1.4, 1.6, 1.4)),
            Vector3([5.5, 0.8, 1.0]),
            (0.5, 0.3, 0.6)
        )
        self.add_object(cube14)

        # Cube 15 - Teal
        cube15 = SceneObject(
            geometry.cube(size=(1.8, 1.0, 1.8)),
            Vector3([-6.0, 0.5, -1.5]),
            (0.3, 0.6, 0.6)
        )
        self.add_object(cube15)

        # Cube 16 - Rust
        cube16 = SceneObject(
            geometry.cube(size=(1.0, 2.2, 1.0)),
            Vector3([3.5, 1.1, 4.5]),
            (0.8, 0.4, 0.2)
        )
        self.add_object(cube16)

        # Cube 17 - Lime
        cube17 = SceneObject(
            geometry.cube(size=(1.2, 0.9, 1.2)),
            Vector3([-3.5, 0.45, -2.5]),
            (0.5, 0.8, 0.3)
        )
        self.add_object(cube17)

        # Cube 18 - Lavender
        cube18 = SceneObject(
            geometry.cube(size=(0.8, 1.4, 0.8)),
            Vector3([8.0, 0.7, 4.0]),
            (0.6, 0.4, 0.7)
        )
        self.add_object(cube18)

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
