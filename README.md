# ModernGL 3D Game Engine

An actively developed Python 3.12 engine built on ModernGL. It ships with a deferred/forward hybrid render pipeline, a PyBullet-backed player controller, an in-engine level editor, and a configurable ImGui interface.

## Feature Highlights
- **Rendering pipeline** – Forward and deferred paths with multi-light PCF shadows, SSAO, bloom, transparent pass, skybox rendering, thumbnail generation, and runtime toggles for FXAA/SMAA/MSAA plus light gizmos and debug overlays.
- **Scene & asset system** – JSON-driven scenes (`assets/scenes/*.json`), procedural primitives (donut, cone, heightmap terrain), GLTF/GLB loader with PBR materials, skeletal animation support, skybox helpers, and selection highlighting.
- **Tooling & UI** – ImGui main/pause/settings menus, a HUD, thumbnail browser, object inspector, undo/redo history, grid overlay, and bundled editor tools (model placement, object edit, light edit, delete) defined in `assets/config/tools/editor_tools.json`.
- **Input system** – Command-pattern `InputManager` with stackable contexts (gameplay, editor, debug), rebindable key bindings persisted to `keybindings.json`, and controllers for camera, player, rendering toggles, UI, and tools.
- **Physics integration** – PyBullet world with kinematic capsule player, collision mesh pipeline (`tools/export_collision_meshes.py`), slope/incline test content, and graceful fallback when PyBullet is unavailable.
- **Procedural content** – Fractal/Perlin terrain generation utilities, donut terrain builder, OBJ exporters, and scripts for generating scenes, thumbnails, and debug visualisations.
- **Tests & documentation** – Pytest suite covering core maths and terrain helpers plus extensive docs under `docs/` (rendering, input, lighting, tool system, optimisation roadmaps).

## Requirements
- Python >=3.12
- I could only get PyBullet working with conda on arm macos:
   - `conda 
- GPU and drivers with OpenGL 4.1 support (ModernGL windowing uses GLFW via moderngl-window).
- `pip install -r requirements.txt` ensures ModernGL, moderngl-window, pyrr, numpy, Pillow, pygltflib, pybullet, and imgui are available. Optional developer extras live in `requirements-dev.txt`.

## Setup
```bash
# optional virtualenv
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt
# optional: linting/tests
pip install -r requirements-dev.txt
```

On first launch the engine writes `keybindings.json` in the project root so you can customise bindings without touching code.

## Running
```bash
python main.py
```
- The app boots into the ImGui main menu. Select a scene such as **Default Scene**, **Donut Terrain**, or **Incline Test** to start.
- Scenes mix primitives, GLTF assets, procedural terrain, and light definitions. Files live in `assets/scenes`.
- If PyBullet fails to initialise (e.g., headless machine) the engine logs a warning and continues with rendering/editor features minus physics-driven movement.

## Default Controls
Gameplay:
- `W/A/S/D` move the player capsule; `Space` jump; `Left Shift` sprint; `Left Ctrl` crouch; `C` toggles walk speed.
- Mouse look controls the active camera rig; `F2` toggles the free-fly debug camera; `Esc` opens the pause menu.
- Rendering toggles: `T` switches SSAO, `L` toggles light gizmos, `F3` shows the debug overlay, `F7` cycles AA modes, `F8` toggles MSAA, `F9` toggles SMAA, `F1` saves a screenshot.

Level editor (press `Enter` to switch from gameplay):
- `W/A/S/D` plus mouse for free-fly movement; `Space`/`Shift` adjust altitude; hold `X` to temporarily boost camera speed.
- Number keys `1-9` switch tools on the hotbar (model placement, object editor, light editor, delete by default).
- `Left click` uses the current tool, `Right click` triggers the secondary action (e.g., rotate, adjust lights).
- `G` toggles the grid overlay, `R` rotates selections, `Delete/Backspace` removes objects, `Z`/`Y` undo/redo, `B` opens the asset browser, `Tab` enables attribute mode for the thumbnail menu and inspector.
- Tap `Enter` again to return to gameplay. Context switching updates key bindings automatically (e.g., WASD back to player movement).

Controls are context-aware; if you modify `keybindings.json` a restart rebuilds the mapping.

## Project Layout
```
assets/                # shaders, models, scenes, collision meshes, textures, UI assets, configs
docs/                  # architecture, rendering, input, lighting, tool system, terrain guides
examples/              # scene/terrain generation scripts
src/gamelib/           # engine modules (config, core, rendering, input, physics, gameplay, tools, ui)
tests/                 # pytest suite
tools/                 # content pipeline helpers (collision mesh export, incline generator)
main.py                # ModernGL WindowConfig entry point
```

Key modules:
- `src/gamelib/rendering/render_pipeline.py` orchestrates shadow, geometry, lighting, SSAO, bloom, transparent, UI, and post-process passes.
- `src/gamelib/core/scene_manager.py` and `scene.py` load JSON scenes, create objects/lights, attach physics bodies, and manage skyboxes.
- `src/gamelib/input` implements the command-pattern input stack with controllers for camera, player, rendering switches, tools, and UI.
- `src/gamelib/tools` contains editor tool logic, undo/redo history, grid overlay renderer, placement previews, and thumbnail menu handling.
- `src/gamelib/physics` wraps PyBullet APIs, collision mesh resolution, and the kinematic player controller.
- `src/gamelib/ui` integrates ImGui themes (`assets/config/themes/*.json`), menus, HUD, thumbnail browser, and debug overlay.

## Utilities & Content Pipeline
- `examples/generate_fractal_scene.py` builds heightmaps and scene JSON from fractal noise presets (see `docs/FRACTAL_TERRAIN_GENERATION.md`).
- `tools/export_collision_meshes.py` resolves `collision_mesh` definitions in scenes and refreshes OBJ files under `assets/collision`.
- `generate_thumbnails.py` and `src/gamelib/rendering/thumbnail_generator.py` prepare preview sprites for the editor’s asset browser.
- `examples` and `docs/DONUT_TERRAIN_USAGE.md` cover donut terrain creation; `debug_frustum.py` and `check_shadow_resolutions.py` assist when tuning culling and shadow cascades.
- Lighting presets live in `assets/config/lights/light_presets.json`; adjust `src/gamelib/config/settings.py` for global defaults (window size, shaders, player tuning, UI theme, AA mode, etc.).

## Testing
```bash
python -m pytest
```
Requires packages from `requirements-dev.txt`. The suite exercises camera maths, light setup, scene loading, fractal terrain, and integration helpers. Rendering-heavy tests rely on ModernGL contexts; run them on a machine with GPU access.

## Documentation
Primary references:
- `docs/ARCHITECTURE.md` – high-level structure (core/input/rendering).
- `docs/DEFERRED_RENDERING.md`, `docs/MULTI_LIGHT_IMPLEMENTATION.md`, `docs/ANTIALIASING_IMPLEMENTATION.md`, `docs/SMAA_IMPLEMENTATION.md` – rendering deep dives.
- `docs/INPUT_SYSTEM.md` and `docs/TOOL_SYSTEM_INTEGRATION.md` – control flow and editor tooling.
- `docs/FRACTAL_TERRAIN_GENERATION.md`, `docs/ROADMAP.md`, `docs/OPTIMIZATIONS.md`, `docs/LIGHTING.md` – content pipelines and future work.

Older quickstart notes may still mention `game.py`; treat this README and `main.py` as the canonical source.

## Status & Contribution Notes
The engine is functional but still evolving. Gameplay-specific controllers (`GameController`), advanced UI flows, and some editor niceties are scoped for future passes. When adding features:
- Update or create docs under `docs/`.
- Add tests in `tests/` where practical.
- Keep configs in `assets/config` in sync with new tools, lights, or themes.

Roadmaps and known issues live in `TODO.md`, `docs/ROADMAP.md`, and per-feature plans inside `docs/`. Issues, ideas, and regressions are easiest to track there or alongside pull requests.
