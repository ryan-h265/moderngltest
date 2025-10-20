"""
Input Handler

Handles keyboard and mouse input events.
"""

from ..core.camera import Camera
from moderngl_window.context.base.keys import BaseKeys

class InputHandler:
    """
    Manages keyboard and mouse input for camera control.

    Features:
    - Keyboard state tracking (for continuous movement)
    - Mouse capture toggle
    - First-mouse movement filtering
    """

    def __init__(self, camera: Camera, keys: BaseKeys):
        """
        Initialize input handler.

        Args:
            camera: Camera to control
        """
        self.camera = camera
        self.keys = keys
        self.keys_pressed = set()

        # Mouse state
        self.mouse_captured = True
        self.first_mouse = True

    def on_key_press(self, key: int):
        """
        Handle key press event.

        Args:
            key: Key code (moderngl_window constant)
        """
        self.keys_pressed.add(key)

    def on_key_release(self, key: int):
        """
        Handle key release event.

        Args:
            key: Key code (moderngl_window constant)
        """
        self.keys_pressed.discard(key)

    def on_mouse_move(self, dx: int, dy: int):
        """
        Handle mouse movement event.

        Args:
            dx: Mouse delta X
            dy: Mouse delta Y
        """
        if not self.mouse_captured:
            return

        # Skip first mouse movement to avoid jump
        if self.first_mouse:
            self.first_mouse = False
            return

        # Process camera look
        self.camera.process_mouse_movement(dx, dy)

    def update(self, frametime: float, key_constants=None):
        """
        Update continuous input (movement).

        Call this every frame.

        Args:
            frametime: Time since last frame (seconds)
            key_constants: Optional key constants object (not used, camera handles key codes directly)
        """
        if frametime > 0:
            self.camera.process_keyboard(self.keys_pressed, frametime)

    def toggle_mouse_capture(self):
        """
        Toggle mouse capture on/off.

        Returns:
            New capture state (True = captured, False = released)
        """
        self.mouse_captured = not self.mouse_captured
        self.first_mouse = True  # Reset first mouse to avoid jump
        return self.mouse_captured

    def set_mouse_capture(self, captured: bool):
        """
        Set mouse capture state.

        Args:
            captured: True to capture, False to release
        """
        self.mouse_captured = captured
        if captured:
            self.first_mouse = True

    def is_mouse_captured(self) -> bool:
        """Check if mouse is currently captured"""
        return self.mouse_captured

    def clear_keys(self):
        """Clear all pressed keys (useful when losing focus)"""
        self.keys_pressed.clear()
