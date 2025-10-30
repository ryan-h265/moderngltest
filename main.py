#!/usr/bin/env python3
"""
ModernGL 3D Engine - Main Entry Point

A modular 3D game engine with multi-light shadow mapping.
"""

import math

import logging

import moderngl
import moderngl_window as mglw
from moderngl_window import geometry
from pyrr import Vector3

from src.gamelib import (
    # Configuration
    WINDOW_SIZE, ASPECT_RATIO, GL_VERSION, WINDOW_TITLE, RESIZABLE,
    # Core
    Camera, SceneManager, SceneObject,
    CameraRig, FreeFlyRig, FirstPersonRig, ThirdPersonRig,
    # Rendering
    RenderPipeline,
    # UI
    PlayerHUD, UIManager, MainMenu, PauseMenu, SettingsMenu, ObjectInspector, ThumbnailMenu,
    # Gameplay
    PlayerCharacter,
    # Input helpers
    InputContext,
    InputCommand,
)
from src.gamelib.core.skybox import Skybox
from src.gamelib.core.game_state import GameStateManager, GameState

# New input system
from src.gamelib.input.input_manager import InputManager
from src.gamelib.input.controllers import CameraController, PlayerController, RenderingController, ToolController
from src.gamelib.input.object_selector import ObjectSelector

# Tool system
from src.gamelib.tools import ToolManager
from src.gamelib.tools.editor_history import EditorHistory
from src.gamelib.tools.grid_overlay import GridOverlay
from src.gamelib.rendering.selection_highlight import SelectionHighlight
from src.gamelib.rendering.thumbnail_generator import ThumbnailGenerator
from src.gamelib.config.settings import (
    PROJECT_ROOT, UI_THEME, UI_PAUSE_DIM_ALPHA,
    THUMBNAIL_SIZE, THUMBNAIL_VISIBLE_COUNT, BOTTOM_MENU_HEIGHT, TOOL_ICON_SIZE,
    SELECTION_HIGHLIGHT_COLOR, SELECTION_OUTLINE_SCALE, OBJECT_RAYCAST_RANGE,
    LIGHT_PRESETS
)

# Physics
from src.gamelib.physics import PhysicsWorld

# Debug overlay
from src.gamelib.debug import DebugOverlay
from src.gamelib.config.settings import DEBUG_OVERLAY_ENABLED, HUD_ENABLED


logger = logging.getLogger(__name__)


class Game(mglw.WindowConfig):
    """Main game class"""

    gl_version = GL_VERSION
    title = WINDOW_TITLE
    window_size = WINDOW_SIZE
    aspect_ratio = ASPECT_RATIO
    resizable = RESIZABLE

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Enable core GL states
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.CULL_FACE)
        self.ctx.front_face = "ccw"

        # Primary camera used by all rigs
        self.camera = Camera(
            position=Vector3([0.0, 5.0, 10.0]),
            target=Vector3([0.0, 0.0, 0.0]),
        )

        # Input system
        self.input_manager = InputManager(self.wnd.keys)

        # Release mouse for menus
        self.wnd.mouse_exclusivity = False
        self.wnd.cursor = True
        self.wnd.exit_key = self.wnd.keys.Q

        # Rendering pipeline and controllers
        self.render_pipeline = RenderPipeline(self.ctx, self.wnd)

        # Setup physics world (PyBullet)
        try:
            self.physics_world = PhysicsWorld()
        except RuntimeError as exc:  # pragma: no cover - environment dependent
            logger.warning("Physics world disabled: %s", exc)
            self.physics_world = None

        # Game state management
        self.game_state = GameStateManager(physics_world=self.physics_world)
        self.game_state.register_state_change_callback(self._on_game_state_changed)

        # UI Manager (ImGui)
        self.ui_manager = UIManager(self.ctx, self.wnd.size, theme_name=UI_THEME)
        self.ui_manager.set_input_manager(self.input_manager)

        # Scene management
        self.scene_manager = SceneManager(
            self.ctx,
            self.render_pipeline,
            physics_world=self.physics_world,
        )
        # Register scenes with metadata
        self.scene_manager.register_scene(
            "default",
            "assets/scenes/default_scene.json",
            display_name="Default Scene",
            description="Basic test scene",
        )
        self.scene_manager.register_scene(
            "donut_terrain",
            "assets/scenes/donut_terrain_scene.json",
            display_name="Donut Terrain",
            description="Procedural donut-shaped terrain with physics",
        )
        self.scene_manager.register_scene(
            "incline_test",
            "assets/scenes/incline_test_scene.json",
            display_name="Incline Test",
            description="Test scene for slope physics",
        )

        # Initialize menus
        self.main_menu = MainMenu(self.scene_manager)
        self.pause_menu = PauseMenu(self.scene_manager)
        self.settings_menu = SettingsMenu(self.render_pipeline, self.input_manager.key_bindings, self.ui_manager)
        self.object_inspector = ObjectInspector()
        self.pause_menu.settings_menu = self.settings_menu

        # Attribute mode menu and selection (initialized after scene loads)
        self.thumbnail_menu = None
        self.object_selector = None
        self.selection_highlight = None
        self.attribute_mode_active = False

        # Scene will be loaded after main menu selection
        self.scene = None
        self.lights = []
        self.player = None
        self.player_hud = None

        # Time tracking
        self.time = 0.0
        self.camera_rig = None
        self.camera_controller = None
        self.player_controller = None

        # Tool system (initialized after scene loads)
        self.tool_manager = None
        self.editor_history = None
        self.grid_overlay = None
        self.tool_controller = None
        self.tool_left_held = False
        self.tool_right_held = False

        # Register pause command
        self.input_manager.register_handler(InputCommand.SYSTEM_PAUSE, self.toggle_pause)

        # Setup debug overlay (always create, but respect initial visibility setting)
        self.debug_overlay = DebugOverlay(self.render_pipeline, visible=DEBUG_OVERLAY_ENABLED)

        # Setup rendering controller for SSAO toggle, debug overlay, etc.
        self.rendering_controller = RenderingController(
            self.render_pipeline,
            self.input_manager,
            debug_overlay=self.debug_overlay
        )

        # Show main menu
        self.game_state.set_state(GameState.MAIN_MENU)
        self.ui_manager.show_main_menu_screen()

        # Toggle for debug camera context
        self.input_manager.register_handler(InputCommand.SYSTEM_TOGGLE_DEBUG_CAMERA, self.toggle_debug_camera)

        # Register editor mode toggle
        self.input_manager.register_handler(InputCommand.EDITOR_TOGGLE_MODE, self.toggle_editor_mode)

        self.input_manager.register_handler(InputCommand.EDITOR_ATTRIBUTE_MODE, self.toggle_attribute_mode)

    def _on_game_state_changed(self, old_state: GameState, new_state: GameState):
        """Called when game state changes."""
        if new_state == GameState.PLAYING:
            # Capture mouse and hide cursor
            self.wnd.mouse_exclusivity = True
            self.wnd.cursor = False
        elif new_state == GameState.PAUSED:
            # Release mouse and show cursor
            self.wnd.mouse_exclusivity = False
            self.wnd.cursor = True
        elif new_state == GameState.MAIN_MENU:
            # Release mouse for menu
            self.wnd.mouse_exclusivity = False
            self.wnd.cursor = True

    def _load_scene_from_menu(self, scene_id: str) -> bool:
        """
        Load a scene after selection from main menu.

        Args:
            scene_id: ID of scene to load

        Returns:
            True if successful, False otherwise
        """
        try:
            loaded_scene = self.scene_manager.load(scene_id, camera=self.camera)
            self.scene = loaded_scene.scene
            self.lights = loaded_scene.lights

            # Skybox
            skybox = Skybox.aurora(self.ctx, name="Aurora Skybox")
            skybox.intensity = 1.0
            self.scene.set_skybox(skybox)

            # Player character and controllers
            self.player = self._spawn_player()
            if self.player is not None:
                self.scene.add_object(self.player.model)

            # Setup HUD
            if HUD_ENABLED:
                self.player_hud = PlayerHUD(self.render_pipeline)
                self.player_hud.set_health(86, 100)
                self.player_hud.set_minimap_status("no map")
                self.player_hud.set_equipped_tool("None")
                self.player_hud.set_hints([
                    "WASD to move",
                    "Space to jump",
                ])

            # Create camera rig and controllers
            self.camera_rig = self._create_camera_rig()
            self.camera_controller = CameraController(self.camera, self.input_manager, rig=self.camera_rig)
            self.player_controller = PlayerController(self.player, self.input_manager) if self.player else None

            # Tool system initialization
            self.tool_manager = ToolManager(self.ctx)
            self.editor_history = EditorHistory(max_history=100)
            self.grid_overlay = GridOverlay(self.ctx, grid_size=1.0, grid_extent=50)
            self.grid_overlay.set_visible(False)  # Hidden by default

            # Load tools from JSON
            tools_path = PROJECT_ROOT / "assets/config/tools/editor_tools.json"
            self.tool_manager.load_tools_from_json(tools_path)

            # Configure editor tools with scene references
            for tool in self.tool_manager.tools.values():
                if hasattr(tool, 'editor_history'):
                    tool.editor_history = self.editor_history
                if hasattr(tool, 'lights_list'):
                    tool.lights_list = self.lights
                if hasattr(tool, 'render_pipeline'):
                    tool.render_pipeline = self.render_pipeline
                if hasattr(tool, 'input_manager'):
                    tool.input_manager = self.input_manager

            # Create tool controller
            self.tool_controller = ToolController(
                self.tool_manager,
                self.input_manager,
                self.camera,
                self.scene
            )
            self.tool_controller.editor_history = self.editor_history
            self.tool_controller.lights = self.lights

            # Start with first tool equipped
            if self.tool_manager.inventory.get_hotbar_tool(0):
                self.tool_manager.equip_hotbar_slot(0)

            # Initialize thumbnail generator for asset previews
            self.thumbnail_generator = ThumbnailGenerator(self.ctx, thumbnail_size=THUMBNAIL_SIZE)

            # Generate thumbnails for light presets (one-time generation)
            self.thumbnail_generator.generate_light_preset_thumbnails(LIGHT_PRESETS)

            # Initialize attribute mode components
            self.thumbnail_menu = ThumbnailMenu(
                self.tool_manager,
                thumbnail_size=THUMBNAIL_SIZE,
                visible_count=THUMBNAIL_VISIBLE_COUNT,
                bottom_menu_height=BOTTOM_MENU_HEIGHT,
                tool_icon_size=TOOL_ICON_SIZE,
            )
            self.object_selector = ObjectSelector(raycast_range=OBJECT_RAYCAST_RANGE)
            self.selection_highlight = SelectionHighlight(self.ctx)
            self.selection_highlight.set_outline_scale(SELECTION_OUTLINE_SCALE)

            # Populate thumbnail menu from scene with generated thumbnails
            self.thumbnail_menu.populate_from_scene(self.scene)

            # Generate model thumbnails for assets in scene
            if hasattr(self.scene, 'objects'):
                for obj in self.scene.objects:
                    if hasattr(obj, 'is_model') and obj.is_model:
                        # Generate thumbnail for this model if it has a path
                        if hasattr(obj, 'source_path'):
                            self.thumbnail_generator.generate_model_thumbnail(
                                obj.source_path,
                                obj.name
                            )

            # Attribute mode disabled by default
            self.attribute_mode_active = False

            # Switch input context to gameplay
            self.input_manager.context_manager.set_context(InputContext.GAMEPLAY)

            self.game_state.set_state(GameState.PLAYING)
            return True

        except Exception as e:
            logger.error(f"Failed to load scene '{scene_id}': {e}")
            return False

    def toggle_pause(self):
        """Toggle pause state."""
        if self.game_state.is_playing():
            self.game_state.pause()
            self.ui_manager.pause_game()
            self.pause_menu.show = True
            # Release mouse for menu interaction
            self.wnd.mouse_exclusivity = False
            self.wnd.cursor = True
        elif self.game_state.is_paused():
            self.game_state.resume()
            self.ui_manager.resume_game()
            self.pause_menu.show = False
            # Capture mouse for gameplay
            self.wnd.mouse_exclusivity = True
            self.wnd.cursor = False

    def _spawn_player(self) -> PlayerCharacter | None:
        if self.physics_world is None:
            return None

        # Use player spawn position from scene, or default if not specified
        spawn_pos = self.scene_manager.player_spawn_position

        placeholder = SceneObject(
            geometry.cube(size=(0.8, 1.8, 0.8)),
            spawn_pos,
            (0.2, 0.6, 0.9),
            name="Player",
        )

        player = PlayerCharacter(placeholder, self.physics_world, initial_position=spawn_pos)
        player.set_yaw(self.camera.yaw)
        return player

    def _create_camera_rig(self) -> CameraRig:
        if self.player is None:
            return FreeFlyRig(self.camera)
        return FirstPersonRig(self.camera, self.player)

    def toggle_debug_camera(self):
        context_manager = self.input_manager.context_manager
        if context_manager.current_context == InputContext.DEBUG_CAMERA:
            # Return to gameplay
            context_manager.pop_context()
            new_rig = self._create_camera_rig()
            self.camera_rig = new_rig
            if self.player is not None:
                self.camera.position = self.player.get_eye_position()
            self.camera_controller.disable_free_fly(new_rig)
        else:
            # Enter debug free-fly
            context_manager.push_context(InputContext.DEBUG_CAMERA)
            self.camera_controller.enable_free_fly()
            self.camera_rig = self.camera_controller.rig

    def toggle_editor_mode(self):
        """Toggle between GAMEPLAY and LEVEL_EDITOR contexts."""
        context_manager = self.input_manager.context_manager
        current_context = context_manager.current_context
        key_bindings = self.input_manager.key_bindings

        if current_context == InputContext.LEVEL_EDITOR:
            # Return to gameplay mode
            context_manager.set_context(InputContext.GAMEPLAY)
            self.grid_overlay.set_visible(False)

            # Reset tool drag state
            self.tool_left_held = False
            self.tool_right_held = False

            print("Entered GAMEPLAY mode")

            # Rebind WASD back to PLAYER_MOVE commands
            key_bindings.rebind_key(InputCommand.PLAYER_MOVE_FORWARD, key_bindings.keys.W)
            key_bindings.rebind_key(InputCommand.PLAYER_MOVE_BACKWARD, key_bindings.keys.S)
            key_bindings.rebind_key(InputCommand.PLAYER_MOVE_LEFT, key_bindings.keys.A)
            key_bindings.rebind_key(InputCommand.PLAYER_MOVE_RIGHT, key_bindings.keys.D)

            # Rebind Space and Shift back to player actions
            key_bindings.rebind_key(InputCommand.PLAYER_JUMP, key_bindings.keys.SPACE)
            key_bindings.rebind_key(InputCommand.PLAYER_SPRINT, key_bindings.keys.LEFT_SHIFT)

            # Reset camera speed multiplier
            self.camera_controller.speed_multiplier = 1.0

            # Restore appropriate camera rig
            new_rig = self._create_camera_rig()
            self.camera_rig = new_rig
            if self.player is not None:
                self.camera.position = self.player.get_eye_position()
            self.camera_controller.disable_free_fly(new_rig)
        else:
            # Enter level editor mode
            context_manager.set_context(InputContext.LEVEL_EDITOR)
            self.grid_overlay.set_visible(True)
            print("Entered LEVEL EDITOR mode")
            print("Controls:")
            print("  - Tab: Return to gameplay")
            print("  - WASD: Move camera")
            print("  - Space: Move camera up")
            print("  - Shift: Move camera down")
            print("  - X (hold): Double camera speed")
            print("  - Mouse: Look around")
            print("  - 1-9: Select tools")
            print("  - G: Toggle grid snapping")
            print("  - Ctrl+Z/Y: Undo/Redo")
            print("  - Ctrl+S: Save scene")

            # Rebind WASD to CAMERA_MOVE commands
            key_bindings.rebind_key(InputCommand.CAMERA_MOVE_FORWARD, key_bindings.keys.W)
            key_bindings.rebind_key(InputCommand.CAMERA_MOVE_BACKWARD, key_bindings.keys.S)
            key_bindings.rebind_key(InputCommand.CAMERA_MOVE_LEFT, key_bindings.keys.A)
            key_bindings.rebind_key(InputCommand.CAMERA_MOVE_RIGHT, key_bindings.keys.D)

            # Rebind Space/Shift for editor camera controls
            key_bindings.rebind_key(InputCommand.CAMERA_MOVE_UP, key_bindings.keys.SPACE)
            key_bindings.rebind_key(InputCommand.CAMERA_MOVE_DOWN, key_bindings.keys.LEFT_SHIFT)
            key_bindings.rebind_key(InputCommand.CAMERA_SPEED_INCREASE, key_bindings.keys.X)

            # Enable free-fly camera for editor
            self.camera_controller.enable_free_fly()
            self.camera_rig = self.camera_controller.rig

    def toggle_attribute_mode(self):
        """Toggle attribute editing mode (Tab key)."""
        # Only allow in editor mode
        if self.input_manager.get_current_context() != InputContext.LEVEL_EDITOR:
            return

        self.attribute_mode_active = not self.attribute_mode_active

        if self.attribute_mode_active:
            # Enable attribute mode
            print("Entered ATTRIBUTE MODE")
            print("Controls:")
            print("  - Click objects in scene to select and edit")
            print("  - Use thumbnail menu to select assets")
            print("  - WASD: Move camera (mouse look disabled)")
            print("  - Adjust properties in right panel")

            # Release mouse cursor
            self.wnd.mouse_exclusivity = False
            self.wnd.cursor = True

            # Disable camera mouse look (keep WASD movement)
            if self.camera_controller:
                self.camera_controller.mouse_look_enabled = False
        else:
            # Disable attribute mode
            print("Exited ATTRIBUTE MODE")

            # Clear selection
            self.object_selector.deselect()
            self.selection_highlight.set_selected_object(None)
            self.object_inspector.set_selected_object(None)
            self.object_inspector.set_preview_item(None)

            # Restore mouse capture (if in editor and not in attribute mode)
            # Leave cursor visible for editor comfort
            self.wnd.mouse_exclusivity = False
            self.wnd.cursor = True

            # Re-enable camera mouse look
            if self.camera_controller:
                self.camera_controller.mouse_look_enabled = True

    def on_update(self, time, frametime):
        """
        Update game logic.

        Args:
            time: Total elapsed time (seconds)
            frametime: Time since last frame (seconds)
        """
        self.time = time

        # Update input system (processes continuous commands + mouse movement)
        self.input_manager.update(frametime)

        # Handle main menu
        if self.game_state.is_in_menu():
            show_menu, selected_scene = self.main_menu.draw(
                int(self.wnd.width), int(self.wnd.height)
            )
            if selected_scene:
                # Scene selected from menu
                self._load_scene_from_menu(selected_scene)
            elif not show_menu:
                # Exit requested
                raise SystemExit(0)
            return

        # Skip gameplay updates if no scene loaded
        if self.scene is None:
            return

        # Gameplay updates
        if self.player_controller is not None:
            self.player_controller.update()

        if self.player is not None:
            self.player.update(frametime)

        if self.physics_world is not None:
            self.physics_world.step_simulation(frametime)

        if self.player is not None:
            self.player.update_post_physics(frametime)

        if self.camera_rig is not None:
            self.camera_rig.update(frametime)

        # Update animations for all models in the scene
        animated_this_frame = False
        for obj in self.scene.objects:
            # Check if this is a Model with animations
            if hasattr(obj, 'is_model') and obj.is_model:
                animated_this_frame |= obj.update(frametime)

        if animated_this_frame:
            for light in self.lights:
                if light.cast_shadows:
                    light.mark_shadow_dirty()

        # Update tool system (only in LEVEL_EDITOR mode)
        if self.tool_manager and self.input_manager.get_current_context() == InputContext.LEVEL_EDITOR:
            self.tool_manager.update(frametime, self.camera, self.scene)

        # Handle pause menu
        if self.game_state.is_paused():
            show_pause, action = self.pause_menu.draw(
                int(self.wnd.width), int(self.wnd.height)
            )
            if action == "resume":
                self.toggle_pause()
            elif action == "main_menu":
                self.game_state.return_to_main_menu()
                self.ui_manager.show_main_menu_screen()
            elif action == "exit":
                raise SystemExit(0)
            return

        # # Update debug overlay
        if self.debug_overlay:
            fps = 1.0 / frametime if frametime > 0 else 0
            self.debug_overlay.update(fps, frametime, self.camera, self.lights, self.scene, self.player)

        # Update HUD and debug overlay
        if self.player_hud:
            # Animate the health bar for demonstration purposes.
            oscillating_health = 70.0 + 30.0 * (0.5 + 0.5 * math.sin(time * 0.35))
            self.player_hud.set_health(oscillating_health, 100.0)
            self.player_hud.update(self.camera, frametime)


    def on_render(self, time, frametime):
        """
        Render a frame.

        Args:
            time: Total elapsed time (seconds)
            frametime: Time since last frame (seconds)
        """
        # Start ImGui frame
        self.ui_manager.start_frame()

        # Update logic
        self.on_update(time, frametime)

        # Skip rendering if in main menu
        if self.game_state.is_in_menu() or self.scene is None:
            # Just render the menu with ImGui
            self.ui_manager.end_frame()
            self.ui_manager.render()
            return

        # Add tool preview to scene before rendering (if in editor mode)
        preview_added = False
        if self.tool_manager and self.input_manager.get_current_context() == InputContext.LEVEL_EDITOR:
            active_tool = self.tool_manager.get_active_tool()
            if active_tool and hasattr(active_tool, 'preview') and active_tool.preview:
                if hasattr(active_tool.preview, 'render_to_scene'):
                    active_tool.preview.render_to_scene(self.scene)
                    preview_added = True

        # Render frame (includes preview if it was added)
        self.render_pipeline.render_frame(self.scene, self.camera, self.lights, time=time)

        # Remove preview from scene after rendering
        if preview_added:
            active_tool = self.tool_manager.get_active_tool()
            if active_tool and hasattr(active_tool, 'preview'):
                if hasattr(active_tool.preview, 'remove_from_scene'):
                    active_tool.preview.remove_from_scene(self.scene)

        # Render editor overlays (after main scene, before UI)
        if self.tool_manager and self.input_manager.get_current_context() == InputContext.LEVEL_EDITOR:
            # Render grid overlay
            self.grid_overlay.render(
                self.camera.get_view_matrix(),
                self.camera.get_projection_matrix(ASPECT_RATIO),
                self.camera.position
            )

            # Render selection highlight in attribute mode
            if self.attribute_mode_active and self.selection_highlight:
                self.selection_highlight.render(
                    self.camera.get_view_matrix(),
                    self.camera.get_projection_matrix(ASPECT_RATIO)
                )

        # Render pause dim overlay (if paused, before ImGui)
        self.ui_manager.render_pause_overlay()

        # Draw attribute mode menus (editor mode only)
        if self.attribute_mode_active and self.input_manager.get_current_context() == InputContext.LEVEL_EDITOR:
            if self.thumbnail_menu:
                # Draw thumbnail menu
                category, item_id, tool_id = self.thumbnail_menu.draw(
                    int(self.wnd.width), int(self.wnd.height)
                )

                # Handle thumbnail menu selections
                if tool_id:
                    # Tool was clicked - already handled by ThumbnailMenu
                    pass
                elif item_id:
                    # Asset was clicked
                    asset = self.thumbnail_menu.assets.get(category, [])
                    for asset_item in asset:
                        if asset_item.id == item_id:
                            # Create preview item dict
                            preview_item = asset_item.to_dict()
                            self.object_inspector.set_preview_item(preview_item)
                            break

        # Draw object inspector (editor mode)
        if self.input_manager.get_current_context() == InputContext.LEVEL_EDITOR:
            # Force show inspector in attribute mode, otherwise only if something selected
            force_show = self.attribute_mode_active
            self.object_inspector.draw(
                int(self.wnd.width), int(self.wnd.height),
                force_show=force_show
            )

        # End ImGui frame and render
        self.ui_manager.end_frame()
        self.ui_manager.render()

    def on_mouse_position_event(self, _x: int, _y: int, dx: int, dy: int):
        """
        Handle mouse movement.

        Args:
            _x, _y: Absolute mouse position (unused)
            dx, dy: Mouse delta
        """
        # Update ImGui mouse position
        self.ui_manager.handle_mouse_position(_x, _y)

        self.input_manager.on_mouse_move(dx, dy)

        # Handle mouse drag for tool operations
        if self.tool_manager and self.input_manager.get_current_context() == InputContext.LEVEL_EDITOR:
            # If a mouse button is held, this is a drag operation
            if self.tool_right_held:
                # Right-click drag: secondary tool action (usually rotate)
                self.tool_manager.use_active_tool_secondary(
                    self.camera,
                    self.scene,
                    mouse_held=True,
                    mouse_delta_x=dx,
                    mouse_delta_y=dy
                )
            elif self.tool_left_held:
                # Left-click drag: primary tool action (usually move)
                self.tool_manager.use_active_tool(
                    self.camera,
                    self.scene,
                    mouse_held=True
                )

    def on_mouse_press_event(self, x: int, y: int, button: int):
        """
        Handle mouse button press.

        Args:
            x, y: Mouse position
            button: Mouse button (1=left, 2=middle, 3=right)
        """
        # Map button numbers: 1=left, 2=right, 3=middle to ImGui: 0=left, 1=right, 2=middle
        imgui_button = button - 1 if button > 0 else 0
        self.ui_manager.handle_mouse_button(imgui_button, True)

        self.input_manager.on_mouse_button_press(button)

        # Handle object selection in attribute mode
        if (self.attribute_mode_active and
            self.input_manager.get_current_context() == InputContext.LEVEL_EDITOR and
            button == 1 and  # Left click only
            self.scene and self.object_selector):

            # Check if click is on UI (ImGui captures it)
            if not self.ui_manager.is_input_captured_by_imgui():
                # Raycast and select object
                selected = self.object_selector.select_from_screen_position(
                    self.camera,
                    self.scene,
                    float(x),
                    float(y),
                    int(self.wnd.width),
                    int(self.wnd.height)
                )

                if selected:
                    # Update inspector to show selected object
                    self.object_inspector.set_selected_object(selected)
                    self.selection_highlight.set_selected_object(selected)
                else:
                    # Deselect if clicking on empty space
                    self.object_inspector.set_selected_object(None)
                    self.selection_highlight.set_selected_object(None)

        # Track mouse button state for tool drag operations
        if self.tool_manager and self.input_manager.get_current_context() == InputContext.LEVEL_EDITOR:
            if button == 1:  # Left button
                self.tool_left_held = True
            elif button == 2:  # Right button
                self.tool_right_held = True

    def on_mouse_release_event(self, x: int, y: int, button: int):
        """
        Handle mouse button release.

        Args:
            x, y: Mouse position
            button: Mouse button (1=left, 2=middle, 3=right)
        """
        # Map button numbers: 1=left, 2=right, 3=middle to ImGui: 0=left, 1=right, 2=middle
        imgui_button = button - 1 if button > 0 else 0
        self.ui_manager.handle_mouse_button(imgui_button, False)

        self.input_manager.on_mouse_button_release(button)

        # Handle mouse button release for tool drag operations
        if self.tool_manager and self.input_manager.get_current_context() == InputContext.LEVEL_EDITOR:
            active_tool = self.tool_manager.get_active_tool()

            if button == 1:  # Left button
                self.tool_left_held = False
                # Finish move operation if tool supports it
                if active_tool and hasattr(active_tool, 'finish_move'):
                    active_tool.finish_move()

            elif button == 2:  # Right button
                self.tool_right_held = False
                # Finish rotate operation if tool supports it
                if active_tool and hasattr(active_tool, 'finish_rotate'):
                    active_tool.finish_rotate()

    def resize(self, width: int, height: int):
        """Handle window resize events by updating render targets."""
        super().resize(width, height)
        self.render_pipeline.resize((width, height))
        self.ui_manager.resize(width, height)

    def on_key_event(self, key, action, modifiers):
        """
        Handle keyboard events.

        Args:
            key: Key code
            action: Action (press, release, repeat)
            modifiers: Modifier keys (shift, ctrl, etc.)
        """
        keys = self.wnd.keys

        # Handle key press/release
        if action == keys.ACTION_PRESS:
            # print(f"Key pressed: {key}")
            self.input_manager.on_key_press(key)

        elif action == keys.ACTION_RELEASE:
            self.input_manager.on_key_release(key)


if __name__ == '__main__':
    Game.run()
