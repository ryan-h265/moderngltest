Lighting Review

src/gamelib/core/light.py:79 only implements directional lights; point and spot types immediately raise NotImplementedError, and LightingRenderer still feeds every light through the same positional uniform block (src/gamelib/rendering/lighting_renderer.py:288), so there is no real support for spot cones, point attenuation, or type-specific shading.
Deferred lighting currently treats every light as an unbounded point with no distance falloff (assets/shaders/deferred_lighting.frag:151); intensities are raw multipliers, so you get non-physical illumination and cannot tune radius/range as required for AAA pipelines.
Shadowing is hard-coded to a single orthographic map per light via Light.get_light_matrix() (src/gamelib/core/light.py:79) and ShadowRenderer.render_single_shadow_map() (src/gamelib/rendering/shadow_renderer.py:205); there is no cascaded shadow mapping for directionals, no cube-map or dual-paraboloid support for points, and no perspective projection/frustum trimming for spots, which caps shadow quality.
Default light setup flags directional lights (main.py:115) but the shader still subtracts world positions (assets/shaders/deferred_lighting.frag:151), so sun/sky lights behave like close point sources—this causes wrong specular response and makes large-scale lighting impossible.
There is no evidence of clustered/tiled light culling, volumetric lighting, light cookies, area lights, reflection probes, or image-based lighting (no environment map sampling anywhere in assets/shaders), all of which are standard expectations in modern AAA engines.
AAA Feature Targets

Core light types: implement true spotlights with inner/outer cones and depth-projected shadow maps, finish point lights with cubemap shadows and physically correct attenuation, and add directional-light parameters for sun-sky models plus cascaded shadow maps.
Physically based controls: support photometric intensity units (lumens, candelas), color temperature curves, and HDR buffer/tonemapping so bloom, exposure, and emissive materials integrate correctly.
Shadow fidelity: add PCSS/contact-hardening kernels, percentage-closer soft shadows with variable filter size, cached shadow map atlases, and per-light bias tuning; directional lights need cascades and stabilization.
Advanced emitters: introduce analytic area lights (rect, disk, sphere) with LTC/approx BRDFs, emissive mesh lighting, and light cookies/masks for texture-driven beams.
Global & indirect lighting: hook in reflection probes, prefiltered environment maps for IBL, and plan for real-time GI (SSGI, DDGI, or probe grids) to avoid purely direct lighting.
Atmospheric effects: volumetric fog/lighting, god rays, shadowed fog integration, and screen-space contact shadows close to the camera.
Performance scalability: move deferred pass from fullscreen quad per light to clustered or tiled shading, or at least volume bounds, so hundreds of lights stay affordable.
Suggested Next Steps

- [x] Finalize light data model: extend Light with type-specific parameters (direction, cone angles, range, attenuation) and plumb them through the renderer/shaders.
- [ ] Rework shadow subsystem: add perspective shadow matrices for spots, cube-map generation path for points, and cascaded shadow mapping for directional lights.
- [x] Introduce physically based lighting units/HDR pipeline so bloom/exposure respond correctly and artists can rely on real-world intensities. *(Lights now accept lumens/lux, deferred pipeline renders into an HDR buffer with ACES/Reinhard/Uncharted tone mapping and manual exposure control.)*
- [ ] Plan for IBL/reflection probes and volumetrics to close the gap between current direct-light-only look and modern AAA scene lighting.
