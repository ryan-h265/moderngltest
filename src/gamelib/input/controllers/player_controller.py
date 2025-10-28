"""Player character input controller."""

from __future__ import annotations

from ..input_commands import InputCommand


class PlayerController:
    """Translate input commands into `PlayerCharacter` actions."""

    def __init__(self, player, input_manager) -> None:
        self.player = player
        self.input_manager = input_manager

        self.forward_axis = 0.0
        self.right_axis = 0.0

        self._register_handlers()

    def _register_handlers(self) -> None:
        self.input_manager.register_handler(InputCommand.PLAYER_MOVE_FORWARD, self._move_forward)
        self.input_manager.register_handler(InputCommand.PLAYER_MOVE_BACKWARD, self._move_backward)
        self.input_manager.register_handler(InputCommand.PLAYER_MOVE_LEFT, self._move_left)
        self.input_manager.register_handler(InputCommand.PLAYER_MOVE_RIGHT, self._move_right)
        self.input_manager.register_handler(InputCommand.PLAYER_JUMP, self._jump)
        self.input_manager.register_handler(InputCommand.PLAYER_SPRINT, self._toggle_sprint)
        self.input_manager.register_handler(InputCommand.PLAYER_CROUCH, self._toggle_crouch)
        self.input_manager.register_handler(InputCommand.PLAYER_WALK, self._toggle_walk)

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def _move_forward(self, delta_time: float) -> None:
        self.forward_axis += 1.0

    def _move_backward(self, delta_time: float) -> None:
        self.forward_axis -= 1.0

    def _move_left(self, delta_time: float) -> None:
        self.right_axis -= 1.0

    def _move_right(self, delta_time: float) -> None:
        self.right_axis += 1.0

    def _jump(self) -> None:
        self.player.request_jump()

    def _toggle_sprint(self) -> None:
        self.player.set_sprint(not self.player.is_sprinting)

    def _toggle_crouch(self) -> None:
        self.player.set_crouch(not self.player.is_crouching)

    def _toggle_walk(self) -> None:
        self.player.toggle_walk()

    # ------------------------------------------------------------------
    # Frame update
    # ------------------------------------------------------------------
    def update(self) -> None:
        forward = max(-1.0, min(1.0, self.forward_axis))
        right = max(-1.0, min(1.0, self.right_axis))
        self.player.set_movement_intent(forward, right)
        self.forward_axis = 0.0
        self.right_axis = 0.0
