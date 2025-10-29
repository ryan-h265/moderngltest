"""
Game State Management

Manages overall game state (main menu, playing, paused, etc.)
and coordinates state transitions with physics, animations, and input.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Optional, Callable

from ..input.input_context import InputContext

if TYPE_CHECKING:
    from ..physics import PhysicsWorld
    from .scene import Scene


class GameState(Enum):
    """Top-level game states."""

    MAIN_MENU = auto()     # Pre-game scene selection
    LOADING = auto()       # Loading scene
    PLAYING = auto()       # Active gameplay
    PAUSED = auto()        # Game paused (menu visible)
    EDITOR = auto()        # Level editor mode
    SHUTDOWN = auto()      # Shutting down


class GameStateManager:
    """
    Manages game state transitions and coordinates pause/resume behavior.

    Features:
    - State machine for game lifecycle
    - Pause/resume with physics synchronization
    - State change callbacks
    """

    def __init__(self, physics_world: Optional[PhysicsWorld] = None):
        """
        Initialize game state manager.

        Args:
            physics_world: Physics world reference for pause/resume
        """
        self.current_state = GameState.MAIN_MENU
        self.physics_world = physics_world
        self.active_scene: Optional[Scene] = None

        # Callbacks for state changes
        self._on_state_changed: list[Callable[[GameState, GameState], None]] = []

    def register_state_change_callback(
        self, callback: Callable[[GameState, GameState], None]
    ) -> None:
        """
        Register a callback for state changes.

        Callback signature: callback(old_state: GameState, new_state: GameState)

        Args:
            callback: Callable that receives old and new state
        """
        self._on_state_changed.append(callback)

    def _notify_state_changed(self, old_state: GameState, new_state: GameState) -> None:
        """Notify all registered callbacks of state change."""
        for callback in self._on_state_changed:
            try:
                callback(old_state, new_state)
            except Exception as e:
                print(f"Error in state change callback: {e}")

    def set_state(self, new_state: GameState) -> None:
        """
        Set game state directly (clears any intermediate states).

        Use this for major transitions (e.g., main menu → gameplay).

        Args:
            new_state: New game state
        """
        if new_state == self.current_state:
            return

        old_state = self.current_state

        # Handle state-specific logic
        if old_state == GameState.PAUSED and new_state == GameState.PLAYING:
            self._handle_resume()
        elif old_state == GameState.PLAYING and new_state == GameState.PAUSED:
            self._handle_pause()

        self.current_state = new_state
        self._notify_state_changed(old_state, new_state)

    def pause(self) -> None:
        """Pause the game (freeze physics and animations)."""
        if self.current_state != GameState.PLAYING:
            return
        self.set_state(GameState.PAUSED)

    def resume(self) -> None:
        """Resume the game (unfreeze physics and animations)."""
        if self.current_state != GameState.PAUSED:
            return
        self.set_state(GameState.PLAYING)

    def start_game(self) -> None:
        """Start gameplay from main menu."""
        if self.current_state != GameState.MAIN_MENU:
            return
        self.set_state(GameState.PLAYING)

    def return_to_main_menu(self) -> None:
        """Return to main menu (unload scene)."""
        self.active_scene = None
        self.set_state(GameState.MAIN_MENU)

    def begin_loading(self) -> None:
        """Begin scene loading transition."""
        self.set_state(GameState.LOADING)

    def finish_loading(self) -> None:
        """Finish scene loading and start gameplay."""
        self.set_state(GameState.PLAYING)

    def toggle_editor_mode(self) -> None:
        """Toggle between gameplay and editor mode."""
        if self.current_state == GameState.PLAYING:
            self.set_state(GameState.EDITOR)
        elif self.current_state == GameState.EDITOR:
            self.set_state(GameState.PLAYING)

    def _handle_pause(self) -> None:
        """Handle pause logic (freeze physics, etc.)."""
        if self.physics_world is not None:
            self.physics_world.pause()

    def _handle_resume(self) -> None:
        """Handle resume logic (unfreeze physics, etc.)."""
        if self.physics_world is not None:
            self.physics_world.resume()

    def get_state(self) -> GameState:
        """Get current game state."""
        return self.current_state

    def is_playing(self) -> bool:
        """Check if game is actively playing."""
        return self.current_state == GameState.PLAYING

    def is_paused(self) -> bool:
        """Check if game is paused."""
        return self.current_state == GameState.PAUSED

    def is_in_menu(self) -> bool:
        """Check if in main menu."""
        return self.current_state == GameState.MAIN_MENU

    def is_loading(self) -> bool:
        """Check if loading scene."""
        return self.current_state == GameState.LOADING

    def is_editing(self) -> bool:
        """Check if in editor mode."""
        return self.current_state == GameState.EDITOR

    def is_active(self) -> bool:
        """Check if game is active (not in main menu or shutdown)."""
        return self.current_state in (
            GameState.PLAYING,
            GameState.PAUSED,
            GameState.EDITOR,
            GameState.LOADING,
        )
