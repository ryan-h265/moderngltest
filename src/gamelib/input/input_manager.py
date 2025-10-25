"""
Input Manager

Central coordinator for the input system. Translates raw input events to commands,
filters by context, and dispatches to registered controllers.
"""

from typing import Dict, Set, Optional, Callable
from moderngl_window.context.base.keys import BaseKeys
from .input_commands import InputCommand, InputType, get_command_type
from .input_context import InputContextManager, InputContext
from .key_bindings import KeyBindings


class InputManager:
    """
    Central input coordinator.

    Responsibilities:
    - Capture raw input (keyboard, mouse)
    - Translate to InputCommands via KeyBindings
    - Filter by InputContext
    - Dispatch to registered controllers
    - Handle mouse capture state
    - Manage continuous vs instant commands

    Usage:
        manager = InputManager()
        manager.register_handler(InputCommand.CAMERA_MOVE_FORWARD, camera_controller.move_forward)
        manager.on_key_press(119)  # W key
    """

    def __init__(self, keys: BaseKeys, key_bindings: Optional[KeyBindings] = None):
        """
        Initialize input manager.

        Args:
            key_bindings: Custom key bindings (default: creates new KeyBindings)
        """
        self.key_bindings = key_bindings or KeyBindings(keys)
        self.context_manager = InputContextManager()

        # Command → Handler callbacks
        self.handlers: Dict[InputCommand, Callable] = {}

        # Currently pressed keys (for continuous commands)
        self.pressed_keys: Set[int] = set()

        # Mouse capture state
        self.mouse_captured = True

        # Mouse delta accumulator (for AXIS commands)
        self.mouse_delta_x = 0.0
        self.mouse_delta_y = 0.0

    def register_handler(self, command: InputCommand, handler: Callable):
        """
        Register a handler for a command.

        Args:
            command: The command to handle
            handler: Callable to invoke when command is triggered
                    - For CONTINUOUS/INSTANT: handler() with no args
                    - For AXIS: handler(dx, dy) with delta values

        Example:
            manager.register_handler(InputCommand.CAMERA_MOVE_FORWARD, camera.move_forward)
            manager.register_handler(InputCommand.CAMERA_LOOK, camera.rotate)
        """
        self.handlers[command] = handler

    def unregister_handler(self, command: InputCommand):
        """
        Unregister a handler for a command.

        Args:
            command: The command to unregister
        """
        if command in self.handlers:
            del self.handlers[command]

    def on_key_press(self, key: int):
        """
        Handle key press event.

        Args:
            key: Key code (e.g., 87 for W)
        """
        # Add to pressed keys
        self.pressed_keys.add(key)

        # Get command for this key
        command = self.key_bindings.get_command(key, is_mouse=False)

        # print(f"Key pressed in InputManager: {key}, command: {command}")

        if command is None:
            return

        # Check if command is allowed in current context
        if not self.context_manager.is_command_allowed(command):
            print(f"Command not allowed in current context: {command}")
            return

        # Handle based on command type
        command_type = get_command_type(command)

        if command_type == InputType.INSTANT or command_type == InputType.TOGGLE:
            # Execute immediately on press
            self._execute_command(command)

        # CONTINUOUS commands are handled in update()

    def on_key_release(self, key: int):
        """
        Handle key release event.

        Args:
            key: Key code
        """
        # Remove from pressed keys
        self.pressed_keys.discard(key)

    def on_mouse_move(self, dx: float, dy: float):
        """
        Handle mouse movement event.

        Args:
            dx: Delta X (horizontal movement)
            dy: Delta Y (vertical movement)
        """
        if not self.mouse_captured:
            return

        # Accumulate deltas for update()
        self.mouse_delta_x += dx
        self.mouse_delta_y += dy

    def on_mouse_button_press(self, button: int):
        """
        Handle mouse button press.

        Args:
            button: Mouse button (1=left, 2=right, 3=middle)
        """
        # Get command for this mouse button
        command = self.key_bindings.get_command(button, is_mouse=True)
        if command is None:
            return

        # Check if command is allowed in current context
        if not self.context_manager.is_command_allowed(command):
            return

        # Execute command
        self._execute_command(command)

    def on_mouse_button_release(self, button: int):
        """
        Handle mouse button release.

        Args:
            button: Mouse button
        """
        # Currently we don't track mouse button state
        # Add if needed for continuous mouse button commands
        pass

    def update(self, delta_time: float):
        """
        Update continuous commands and dispatch accumulated input.

        Call this every frame to process held keys and mouse movement.

        Args:
            delta_time: Time since last update (for scaling movement)
        """
        # Process continuous (held) keys
        for key in self.pressed_keys:
            command = self.key_bindings.get_command(key, is_mouse=False)
            if command is None:
                continue

            # Check if command is allowed in current context
            if not self.context_manager.is_command_allowed(command):
                continue

            # Only process continuous commands
            if get_command_type(command) == InputType.CONTINUOUS:
                self._execute_command(command, delta_time)

        # Process accumulated mouse movement (AXIS commands)
        if self.mouse_captured and (self.mouse_delta_x != 0 or self.mouse_delta_y != 0):
            # Get camera look command (hardcoded for now, could be rebindable)
            if self.context_manager.is_command_allowed(InputCommand.CAMERA_LOOK):
                self._execute_axis_command(
                    InputCommand.CAMERA_LOOK,
                    self.mouse_delta_x,
                    self.mouse_delta_y
                )

            # Reset deltas
            self.mouse_delta_x = 0.0
            self.mouse_delta_y = 0.0

    def _execute_command(self, command: InputCommand, delta_time: float = 0.0):
        """
        Execute a command by calling its handler.

        Args:
            command: Command to execute
            delta_time: Time delta (for continuous commands)
        """
        handler = self.handlers.get(command)
        if handler is None:
            return

        # Call handler (continuous commands may use delta_time)
        try:
            # Try calling with delta_time for continuous commands
            if get_command_type(command) == InputType.CONTINUOUS:
                handler(delta_time)
            else:
                handler()
        except TypeError:
            # Handler doesn't accept arguments, call without
            handler()

    def _execute_axis_command(self, command: InputCommand, dx: float, dy: float):
        """
        Execute an axis command (like mouse look).

        Args:
            command: Command to execute
            dx: Delta X
            dy: Delta Y
        """
        handler = self.handlers.get(command)
        if handler is None:
            return

        # Call handler with deltas
        handler(dx, dy)

    def toggle_mouse_capture(self) -> bool:
        """
        Toggle mouse capture state.

        Returns:
            New mouse capture state (True if captured)
        """
        self.mouse_captured = not self.mouse_captured

        # Clear mouse deltas when toggling
        self.mouse_delta_x = 0.0
        self.mouse_delta_y = 0.0

        return self.mouse_captured

    def set_mouse_capture(self, captured: bool):
        """
        Set mouse capture state explicitly.

        Args:
            captured: True to capture mouse, False to release
        """
        self.mouse_captured = captured

        if not captured:
            self.mouse_delta_x = 0.0
            self.mouse_delta_y = 0.0

    def push_context(self, context: InputContext):
        """
        Push a new input context (e.g., open menu).

        Args:
            context: Context to push
        """
        self.context_manager.push_context(context)

    def pop_context(self):
        """
        Pop the current input context (e.g., close menu).

        Returns:
            The popped context
        """
        return self.context_manager.pop_context()

    def get_current_context(self) -> InputContext:
        """
        Get the current input context.

        Returns:
            Current context
        """
        return self.context_manager.get_current_context()

    def clear_all_input(self):
        """
        Clear all input state (pressed keys, mouse deltas).

        Useful when changing contexts to prevent stuck keys.
        """
        self.pressed_keys.clear()
        self.mouse_delta_x = 0.0
        self.mouse_delta_y = 0.0
