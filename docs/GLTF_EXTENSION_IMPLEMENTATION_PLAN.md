# glTF Extension Implementation Plan

This document defines a concrete, incremental plan to implement parsing and integration for the following glTF extensions in this renderer project:

- `KHR_xmp_json_ld`
- `KHR_materials_diffuse_transmission`
- `KHR_materials_volume`
- `KHR_materials_dispersion`
- `KHR_materials_volume_scatter`
- `KHR_materials_ior`

Goals
-------
- Parse these extensions from glTF/GLB files and store their information in the existing renderer data model (primarily `Material` and `Model`).
- Keep parsing and storage separate from rendering logic so parsing can be landed quickly and safely.
- Provide a clear, incremental roadmap to wire extension data into shaders and runtime behavior (Fresnel/IOR, transmission/refraction, dispersion, and volumetrics).
- Deliver unit tests, docs, and a small set of sample assets (optional) to validate behavior.

Scope & priorities
-------------------
1. Parsing & data model (high priority)
   - Add fields to `Material` (and `Model` for asset-level metadata) to store extension values and textures.
   - Implement parsing in `src/gamelib/loaders/gltf_loader.py` (use existing helpers: `_load_texture`, `_load_texture_transform`).

2. Tests & docs (high priority)
   - Unit tests for parsing correctness.
   - Documentation describing supported fields and limitations.

3. Shader integration (medium priority — iterative)
   - Wire IOR into Fresnel calculation and support optional transmission/refraction in `main_lighting` as a gated branch.
   - Provide optional dispersion support in transmission path (cheap approximation first).
   - Treat volumetrics/volume scattering as separate render paths / shader variants (multi-pass or object-space raymarching) — can be planned and implemented later.

Extensions — parsing details
---------------------------
For each extension we will parse extension payloads (dict or pygltflib objects) and store them on the `Material` object (or `Model` for asset-level `KHR_xmp_json_ld`).

- KHR_xmp_json_ld
  - What: JSON-LD metadata. Can appear at asset, material, or image levels.
  - Parse: If present at `gltf.asset.extensions` or `gltf.materials[].extensions['KHR_xmp_json_ld']`, parse the JSON-LD block. The extension payload may be a dict or a JSON string — support both.
  - Store: `Model.metadata['xmp_json_ld']` and `Material.xmp_json_ld` (dict). For images, store metadata on the `Material` image object if present.
  - Shader: none.

- KHR_materials_ior
  - What: Index of refraction (scalar or texture).
  - Parse: extract numeric `ior` or texture index; if there is a texture, use `_load_texture` and `_load_texture_transform`.
  - Store: `Material.ior` (float), `Material.ior_texture` (Texture), `Material.ior_transform` (TextureTransform)
  - Shader: integrate into Fresnel / refraction calculations.

- KHR_materials_diffuse_transmission
  - What: Transmission for thin materials (transparency / diffuse transmission factor + texture).
  - Parse: `transmissionFactor` (float), `transmissionTexture` (texture index). Load texture and transform.
  - Store: `Material.transmission_factor`, `Material.transmission_texture`, `Material.transmission_transform`.
  - Shader: optional refraction/transmission path (environment or screen-space sampling). Start with cheap approximation (blend environment sample by factor).

- KHR_materials_dispersion
  - What: Parameters to produce wavelength-dependent refraction (chromatic dispersion).
  - Parse: store raw fields present in the extension (e.g., `strength`, `texture` if present) — different exporters may supply different fields; keep a flexible container like `Material.dispersion = dict(...)`.
  - Shader: optional: approximate by offsetting refraction per-channel or post-process chromatic aberration for performance.

- KHR_materials_volume
  - What: Volume attenuation parameters (attenuationDistance, attenuationColor, thicknessFactor, thicknessTexture, etc.).
  - Parse: extract numeric fields and textures. Fields include `attenuationDistance`, `attenuationColor`, `thicknessFactor`, `thicknessTexture`.
  - Store: `Material.volume = { 'attenuation_distance': float, 'attenuation_color': (r,g,b), 'thickness_factor': float, 'thickness_texture': Texture, 'thickness_transform': TextureTransform }
  - Shader: requires separate render approach (object-space raymarch or thickness map compose). Mark as a separate implementation step.

- KHR_materials_volume_scatter
  - What: Scattering coefficients, anisotropy, color/texture describing scattering within the volume.
  - Parse: extract fields such as `scatterDistance`, `scatterColor`, `anisotropy` and any texture references.
  - Store: `Material.volume_scatter = { ... }` (flexible dict). Use Texture + TextureTransform for textures.
  - Shader: volumetric scattering is expensive — plan for an approximated single-scattering model initially (separate shader/pass).

Data model changes (concrete)
----------------------------
- Files to modify:
  - `src/gamelib/loaders/material.py` — add typed fields with sensible defaults and docstrings for:
    - transmission_factor: float = 0.0
    - transmission_texture: Optional[Texture]
    - transmission_transform: Optional[TextureTransform]
    - ior: float = 1.0
    - ior_texture: Optional[Texture]
    - ior_transform: Optional[TextureTransform]
    - dispersion: Optional[Dict]
    - volume: Optional[Dict]
    - volume_scatter: Optional[Dict]
    - xmp_json_ld: Optional[Dict]
  - `src/gamelib/loaders/gltf_loader.py` — update `_parse_materials` (and possibly `_load_texture_transform`) to populate these fields.

Parsing considerations and helpers
---------------------------------
- Reuse `_load_texture(gltf, tex_idx, model_dir)` to load textures and `_load_texture_transform(...)` for transforms.
- Extension payloads may be returned as Python dicts or as pygltflib objects. Use `isinstance(ext, dict)` or `getattr(ext, 'property', None)` patterns; prefer dict access when available.
- Use safe defaults and log informative warnings if expected fields are missing or indices are out of range.

Shader integration plan — recommended incremental approach
-------------------------------------------------------
1. IOR and Fresnel (low cost)
   - Add a uniform `u_material_ior` (float) and optional sampler `u_material_ior_tex` plus a flag `u_has_ior_tex`.
   - Replace or augment the current Fresnel computation to accept IOR when present. Keep default behavior unchanged when IOR is not set.

2. Diffuse transmission/refraction (medium cost)
   - Add `u_transmission_factor`, `u_transmission_tex`, `u_has_transmission_tex`.
   - Implement a cheap refraction: sample environment cubemap or screen texture with a refracted direction and blend with surface shading by `transmission_factor`.

3. Dispersion (optional, medium cost)
   - Add `u_dispersion_strength` and optional `u_dispersion_tex`.
   - Approximate dispersion by offsetting refraction per-channel; only enable when extension is present.

4. Volume & volume scatter (high cost)
   - Implement as separate shader(s) and/or a special render path (object proxy, raymarch per-pixel, or thickness-buffer compose).
   - Provide `u_volume_*` uniforms and sample `thickness_texture` if present.
   - Initially implement a single-scattering approximation to keep performance acceptable.

Implementation tasks (concrete, ordered)
-------------------------------------
Phase A — Parsing + model changes (safe, small PRs)

1. Review `src/gamelib/loaders/material.py` and decide field names and default values. (See todo list item 1.)
2. Add fields to `Material` with docstrings. Provide a small convenience constructor for nested dict fields. (todo list item 2)
3. Update `_parse_materials` in `src/gamelib/loaders/gltf_loader.py` to detect and parse each extension. Reuse `_load_texture` and `_load_texture_transform` for textures. (todo list items 3–8)
4. Add unit tests `tests/test_gltf_extensions.py` to verify parsing of each extension field (happy path + missing fields). (todo list item 9)
5. Add docs (this file) and a short changelog entry. (todo item 10)

Phase B — Low-cost shader wiring (small PR)

1. Wire `Material.ior` -> uniform `u_material_ior` and use it in Fresnel calc.
2. Wire `Material.transmission_factor` -> uniform `u_transmission_factor` and implement cheap transmission/refraction in `main_lighting.frag` gated by a define or runtime flag.
3. Add uniform binding and texture-set helpers in the Python draw path to avoid sampling textures when not present.

Phase C — Dispersion + volumetrics (larger tasks)

1. Implement dispersion approximation inside transmission code path (toggleable) — medium complexity.
2. Design and implement volumetric shader(s)/render path (requires more design choices: proxy geometry, thickness buffer, or raymarching). Provide toggles for sample count/quality.
3. Add integration tests and example assets to validate volumetrics.

Testing & QA
------------
- Unit tests will mock small pygltflib structures or create minimal glTF JSON snippets to exercise extension parsing logic without large binary assets.
- Run project's test suite and fix any regressions.
- Manual validation: add or download small sample glTF files that include the extension fields to `assets/` and load them in the renderer; verify `Material` fields are populated.

Deliverables
------------
- `docs/GLTF_EXTENSION_IMPLEMENTATION_PLAN.md` (this file)
- Modified `src/gamelib/loaders/material.py` (new fields + docstrings)
- Modified `src/gamelib/loaders/gltf_loader.py` (`_parse_materials` extension parsing)
- Unit tests: `tests/test_gltf_extensions.py`
- Short shader changes in `shaders/main_lighting.frag` (IOR + cheap transmission) — optional initial PR
- Additional docs: `docs/GLTF_EXTENSION_SUPPORT.md` (or update `MODEL_LOADING.md`) listing supported fields and limitations

Assumptions & notes
--------------------
- This plan focuses first on safe parsing and storing of extension data. Full visual correctness (especially volumetrics and dispersion) requires shader work and potentially renderer architectural changes (extra passes, buffers) which are planned but out-of-scope for the initial parsing PR.
- The current loader already has helpers to load textures and texture transforms — these will be reused.
- Some extension payloads vary between exporters. Parsing code should be defensive: accept dicts or objects and fallback to defaults.

Estimated timeline (per-person, approximate)
-----------------------------------------
- Phase A (parsing + tests + docs): 1–3 days
- Phase B (IOR + cheap transmission shader wiring): 1–2 days
- Phase C (dispersion + volumetrics): 3–10+ days depending on desired accuracy and renderer changes

Next actions (pick one)
-----------------------
1. I will implement Phase A (parsing + material fields + tests) and open a small PR. This is low risk and gives an immediate value.
2. I will implement Phase B (IOR + cheap transmission) after Phase A lands.

If you want me to begin, tell me which next action to take and I will start implementing Phase A now.

— End of plan
