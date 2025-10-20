"""Tests for Scene classes"""

import pytest
from pyrr import Vector3

from src.gamelib.core.scene import Scene, SceneObject


def test_scene_initialization():
    """Test scene initialization"""
    scene = Scene()
    assert len(scene.objects) == 0


def test_scene_add_object():
    """Test adding objects to scene"""
    scene = Scene()

    obj = SceneObject(
        geom=None,  # Mock geometry
        position=Vector3([0.0, 0.0, 0.0]),
        color=(1.0, 0.0, 0.0)
    )

    scene.add_object(obj)
    assert len(scene.objects) == 1
    assert scene.get_object_count() == 1


def test_scene_clear():
    """Test clearing scene"""
    scene = Scene()

    for i in range(5):
        obj = SceneObject(None, Vector3([0.0, 0.0, 0.0]), (1.0, 0.0, 0.0))
        scene.add_object(obj)

    assert scene.get_object_count() == 5

    scene.clear()
    assert scene.get_object_count() == 0


def test_scene_default_scene():
    """Test default scene creation"""
    scene = Scene()
    scene.create_default_scene()

    # Should have ground + 18 cubes = 19 objects
    assert scene.get_object_count() == 19


def test_scene_object_model_matrix():
    """Test scene object model matrix generation"""
    obj = SceneObject(
        geom=None,
        position=Vector3([1.0, 2.0, 3.0]),
        color=(1.0, 0.0, 0.0)
    )

    matrix = obj.get_model_matrix()

    # Should return 4x4 matrix
    assert matrix.shape == (4, 4)

    # Translation should match position
    assert matrix[3, 0] == 1.0
    assert matrix[3, 1] == 2.0
    assert matrix[3, 2] == 3.0
