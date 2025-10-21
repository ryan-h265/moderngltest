"""
UI Controller (Placeholder)

Future: Handles UI navigation and interactions.
"""

from ..input_commands import InputCommand
from ..input_manager import InputManager


class UIController:
    """
    Controller for UI interactions.

    Currently a placeholder for future implementation.

    Future functionality:
    - Menu navigation (up, down, left, right)
    - Confirm, cancel, tab switching
    - Inventory management
    - Dialog choices
    """

    def __init__(self, input_manager: InputManager):
        """
        Initialize UI controller.

        Args:
            input_manager: InputManager to register handlers with
        """
        self.input_manager = input_manager

        # Register handlers when UI is implemented
        # self._register_handlers()

    def _register_handlers(self):
        """Register input handlers (placeholder)"""
        # Example future handlers:
        # self.input_manager.register_handler(InputCommand.UI_NAVIGATE_UP, self.navigate_up)
        # self.input_manager.register_handler(InputCommand.UI_CONFIRM, self.confirm)
        # self.input_manager.register_handler(InputCommand.UI_CANCEL, self.cancel)
        pass

    # Future methods:
    # def navigate_up(self):
    #     """Navigate menu up"""
    #     pass
    #
    # def confirm(self):
    #     """Confirm selection"""
    #     pass
    #
    # def cancel(self):
    #     """Cancel/back"""
    #     pass
