"""Camera Controller with rig delegation."""

from __future__ import annotations

from ...core.camera import Camera
from ...core.camera_rig import CameraRig, FreeFlyRig
from ..input_commands import InputCommand
from ..input_manager import InputManager


class CameraController:
    """Handles camera-related input commands."""

    def __init__(self, camera: Camera, input_manager: InputManager, rig: CameraRig | None = None) -> None:
        self.camera = camera
        self.input_manager = input_manager
        self.rig: CameraRig = rig or FreeFlyRig(camera)
        self.free_fly_mode = isinstance(self.rig, FreeFlyRig)

        self._register_handlers()

    def _register_handlers(self) -> None:
        self.input_manager.register_handler(InputCommand.CAMERA_MOVE_FORWARD, self.move_forward)
        self.input_manager.register_handler(InputCommand.CAMERA_MOVE_BACKWARD, self.move_backward)
        self.input_manager.register_handler(InputCommand.CAMERA_MOVE_LEFT, self.move_left)
        self.input_manager.register_handler(InputCommand.CAMERA_MOVE_RIGHT, self.move_right)
        self.input_manager.register_handler(InputCommand.CAMERA_MOVE_UP, self.move_up)
        self.input_manager.register_handler(InputCommand.CAMERA_MOVE_DOWN, self.move_down)
        self.input_manager.register_handler(InputCommand.CAMERA_LOOK, self.rotate)
        self.input_manager.register_handler(InputCommand.SYSTEM_TOGGLE_MOUSE, self.toggle_mouse_capture)

    # ------------------------------------------------------------------
    # Rig management
    # ------------------------------------------------------------------
    def set_rig(self, rig: CameraRig) -> None:
        self.rig.disable()
        self.rig = rig
        self.rig.enable()
        self.free_fly_mode = isinstance(rig, FreeFlyRig)

    def enable_free_fly(self) -> None:
        self.set_rig(FreeFlyRig(self.camera))

    def disable_free_fly(self, rig: CameraRig) -> None:
        self.set_rig(rig)

    # ------------------------------------------------------------------
    # Movement handlers (active only for free-fly)
    # ------------------------------------------------------------------
    def move_forward(self, delta_time: float) -> None:
        if not self.free_fly_mode:
            return
        movement = self.camera.speed * delta_time
        self.camera.position += self.camera._front * movement

    def move_backward(self, delta_time: float) -> None:
        if not self.free_fly_mode:
            return
        movement = self.camera.speed * delta_time
        self.camera.position -= self.camera._front * movement

    def move_left(self, delta_time: float) -> None:
        if not self.free_fly_mode:
            return
        movement = self.camera.speed * delta_time
        self.camera.position -= self.camera._right * movement

    def move_right(self, delta_time: float) -> None:
        if not self.free_fly_mode:
            return
        movement = self.camera.speed * delta_time
        self.camera.position += self.camera._right * movement

    def move_up(self, delta_time: float) -> None:
        if not self.free_fly_mode:
            return
        movement = self.camera.speed * delta_time
        self.camera.position.y += movement

    def move_down(self, delta_time: float) -> None:
        if not self.free_fly_mode:
            return
        movement = self.camera.speed * delta_time
        self.camera.position.y -= movement

    def rotate(self, dx: float, dy: float) -> None:
        self.rig.apply_look_input(dx, dy)

    def toggle_mouse_capture(self):
        return self.input_manager.toggle_mouse_capture()
