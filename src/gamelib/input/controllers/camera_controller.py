"""
Camera Controller

Translates input commands to camera actions.
"""

from ...core.camera import Camera
from ..input_commands import InputCommand
from ..input_manager import InputManager


class CameraController:
    """
    Controller for camera input.

    Registers handlers with InputManager and translates commands to camera actions.

    Usage:
        camera = Camera(position)
        input_manager = InputManager()
        controller = CameraController(camera, input_manager)
    """

    def __init__(self, camera: Camera, input_manager: InputManager):
        """
        Initialize camera controller.

        Args:
            camera: Camera instance to control
            input_manager: InputManager to register handlers with
        """
        self.camera = camera
        self.input_manager = input_manager

        # Register handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register input handlers with InputManager"""
        # Movement (continuous)
        self.input_manager.register_handler(
            InputCommand.CAMERA_MOVE_FORWARD,
            self.move_forward
        )
        self.input_manager.register_handler(
            InputCommand.CAMERA_MOVE_BACKWARD,
            self.move_backward
        )
        self.input_manager.register_handler(
            InputCommand.CAMERA_MOVE_LEFT,
            self.move_left
        )
        self.input_manager.register_handler(
            InputCommand.CAMERA_MOVE_RIGHT,
            self.move_right
        )
        self.input_manager.register_handler(
            InputCommand.CAMERA_MOVE_UP,
            self.move_up
        )
        self.input_manager.register_handler(
            InputCommand.CAMERA_MOVE_DOWN,
            self.move_down
        )

        # Look (axis)
        self.input_manager.register_handler(
            InputCommand.CAMERA_LOOK,
            self.rotate
        )

        # System commands
        self.input_manager.register_handler(
            InputCommand.SYSTEM_TOGGLE_MOUSE,
            self.toggle_mouse_capture
        )

    def move_forward(self, delta_time: float):
        """Move camera forward"""
        movement = self.camera.speed * delta_time
        self.camera.position += self.camera._front * movement

    def move_backward(self, delta_time: float):
        """Move camera backward"""
        movement = self.camera.speed * delta_time
        self.camera.position -= self.camera._front * movement

    def move_left(self, delta_time: float):
        """Move camera left (strafe)"""
        movement = self.camera.speed * delta_time
        self.camera.position -= self.camera._right * movement

    def move_right(self, delta_time: float):
        """Move camera right (strafe)"""
        movement = self.camera.speed * delta_time
        self.camera.position += self.camera._right * movement

    def move_up(self, delta_time: float):
        """Move camera up"""
        movement = self.camera.speed * delta_time
        self.camera.position.y += movement

    def move_down(self, delta_time: float):
        """Move camera down"""
        movement = self.camera.speed * delta_time
        self.camera.position.y -= movement

    def rotate(self, dx: float, dy: float):
        """
        Rotate camera based on mouse movement.

        Args:
            dx: Mouse delta X
            dy: Mouse delta Y
        """
        # Apply sensitivity
        from ...config.settings import INVERT_MOUSE_Y, MIN_PITCH, MAX_PITCH

        x_offset = dx * self.camera.sensitivity
        y_offset = -dy * self.camera.sensitivity if not INVERT_MOUSE_Y else dy * self.camera.sensitivity

        # Update yaw and pitch
        self.camera.yaw += x_offset
        self.camera.pitch += y_offset

        # Constrain pitch to prevent camera flipping
        self.camera.pitch = max(MIN_PITCH, min(MAX_PITCH, self.camera.pitch))

        # Update camera vectors
        self.camera.update_vectors()

    def toggle_mouse_capture(self):
        """Toggle mouse capture (ESC key)"""
        # This is handled by InputManager, but we return the state
        # to allow main.py to update window cursor state
        return self.input_manager.toggle_mouse_capture()
