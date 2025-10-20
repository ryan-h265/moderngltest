"""Tests for Light class"""

import pytest
import numpy as np
from pyrr import Vector3

from src.gamelib.core.light import Light


def test_light_initialization():
    """Test light initialization"""
    pos = Vector3([5.0, 10.0, 5.0])
    target = Vector3([0.0, 0.0, 0.0])
    color = Vector3([1.0, 1.0, 1.0])

    light = Light(
        position=pos,
        target=target,
        color=color,
        intensity=1.0
    )

    assert np.allclose(light.position, pos)
    assert np.allclose(light.target, target)
    assert np.allclose(light.color, color)
    assert light.intensity == 1.0


def test_light_matrix():
    """Test light matrix generation"""
    light = Light(
        position=Vector3([5.0, 10.0, 5.0]),
        target=Vector3([0.0, 0.0, 0.0]),
        color=Vector3([1.0, 1.0, 1.0]),
        intensity=1.0
    )

    matrix = light.get_light_matrix()

    # Should return 4x4 matrix
    assert matrix.shape == (4, 4)


def test_light_animate_rotation():
    """Test light rotation animation"""
    light = Light(
        position=Vector3([0.0, 0.0, 0.0]),
        target=Vector3([0.0, 0.0, 0.0]),
        color=Vector3([1.0, 1.0, 1.0]),
        intensity=1.0
    )

    # Animate for 0 seconds (should be at angle 0)
    light.animate_rotation(0.0, radius=10.0, height=5.0)
    assert np.isclose(light.position.x, 10.0)
    assert np.isclose(light.position.y, 5.0)
    assert np.isclose(light.position.z, 0.0)


def test_light_setters():
    """Test light property setters"""
    light = Light(
        position=Vector3([0.0, 0.0, 0.0]),
        target=Vector3([0.0, 0.0, 0.0]),
        color=Vector3([1.0, 1.0, 1.0]),
        intensity=1.0
    )

    light.set_position(1.0, 2.0, 3.0)
    assert np.isclose(light.position.x, 1.0)
    assert np.isclose(light.position.y, 2.0)
    assert np.isclose(light.position.z, 3.0)

    light.set_color(0.5, 0.6, 0.7)
    assert np.isclose(light.color.x, 0.5)
    assert np.isclose(light.color.y, 0.6)
    assert np.isclose(light.color.z, 0.7)

    light.set_intensity(0.8)
    assert light.intensity == 0.8
