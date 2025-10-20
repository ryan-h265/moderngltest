"""Tests for Camera class"""

import pytest
import numpy as np
from pyrr import Vector3

from src.gamelib.core.camera import Camera


def test_camera_initialization():
    """Test camera initialization"""
    pos = Vector3([0.0, 5.0, 10.0])
    cam = Camera(pos)

    assert np.allclose(cam.position, pos)
    assert cam.yaw == -90.0
    assert cam.pitch == -20.0


def test_camera_update_vectors():
    """Test camera vector updates"""
    cam = Camera(Vector3([0.0, 0.0, 0.0]))
    cam.yaw = 0.0
    cam.pitch = 0.0
    cam.update_vectors()

    # Should be looking along positive X axis
    assert cam._front[0] > 0.9
    assert abs(cam._front[1]) < 0.1
    assert abs(cam._front[2]) < 0.1


def test_camera_mouse_movement():
    """Test mouse movement updates yaw and pitch"""
    cam = Camera(Vector3([0.0, 0.0, 0.0]))
    initial_yaw = cam.yaw
    initial_pitch = cam.pitch

    cam.process_mouse_movement(10, 10)

    # Mouse movement should change yaw and pitch
    assert cam.yaw != initial_yaw
    assert cam.pitch != initial_pitch


def test_camera_pitch_constraint():
    """Test pitch is constrained to prevent flipping"""
    cam = Camera(Vector3([0.0, 0.0, 0.0]))

    # Try to pitch beyond limits
    cam.pitch = 100.0
    cam.process_mouse_movement(0, 0)  # Process to apply constraints

    assert cam.pitch <= 89.0
    assert cam.pitch >= -89.0


def test_camera_matrices():
    """Test camera matrix generation"""
    cam = Camera(Vector3([0.0, 5.0, 10.0]))

    view = cam.get_view_matrix()
    projection = cam.get_projection_matrix(16/9)

    # Should return 4x4 matrices
    assert view.shape == (4, 4)
    assert projection.shape == (4, 4)
