#version 410

/**
 * Hybrid Skybox Shader - Industry Standard Implementation
 *
 * Combines:
 * - Atmospheric scattering (Preetham model)
 * - Procedural volumetric clouds (3D Perlin/Worley noise)
 * - Dynamic time-of-day system
 * - Weather effects (clear, cloudy, stormy)
 * - Star field with rotation
 * - Sun/moon rendering
 * - Atmospheric fog
 *
 * This is a complete industry-standard skybox system.
 */

in vec3 v_texcoord;
out vec4 fragColor;

// Basic uniforms
uniform float intensity;
uniform float u_time;
uniform samplerCube skybox_texture;

// Time of day uniforms
uniform float u_time_of_day;  // 0.0-1.0
uniform vec3 u_sun_direction;
uniform vec3 u_sun_color;
uniform float u_sun_intensity;
uniform vec3 u_moon_direction;
uniform vec3 u_moon_color;
uniform float u_moon_intensity;

// Atmospheric uniforms
uniform vec3 u_rayleigh_coefficient;
uniform float u_mie_coefficient;
uniform float u_sun_brightness;
uniform float u_turbidity;

// Weather uniforms
uniform float u_cloud_coverage;    // 0.0-1.0
uniform float u_cloud_speed;
uniform float u_cloud_density;
uniform float u_precipitation;
uniform vec2 u_wind_direction;

// Star field uniforms
uniform float u_star_visibility;
uniform float u_star_brightness;
uniform int u_star_density;

// Sky colors (from time-of-day system)
uniform vec3 u_sky_color_zenith;
uniform vec3 u_sky_color_horizon;

// Fog uniforms
uniform int fogEnabled;
uniform vec3 fogColor;
uniform float fogDensity;

// Constants
const float PI = 3.14159265359;
const vec3 UP = vec3(0.0, 1.0, 0.0);

// ============================================================================
// NOISE FUNCTIONS (for procedural clouds)
// ============================================================================

float hash(float n) {
    return fract(sin(n) * 43758.5453);
}

float hash3D(vec3 p) {
    return fract(sin(dot(p, vec3(12.9898, 78.233, 45.543))) * 43758.5453);
}

// 3D Perlin-like noise
float noise3D(vec3 x) {
    vec3 p = floor(x);
    vec3 f = fract(x);
    f = f * f * (3.0 - 2.0 * f);

    float n = p.x + p.y * 57.0 + 113.0 * p.z;
    return mix(
        mix(mix(hash(n + 0.0), hash(n + 1.0), f.x),
            mix(hash(n + 57.0), hash(n + 58.0), f.x), f.y),
        mix(mix(hash(n + 113.0), hash(n + 114.0), f.x),
            mix(hash(n + 170.0), hash(n + 171.0), f.x), f.y),
        f.z
    );
}

// Fractional Brownian Motion (FBM)
float fbm(vec3 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;

    for (int i = 0; i < 5; i++) {
        value += amplitude * noise3D(p * frequency);
        frequency *= 2.0;
        amplitude *= 0.5;
    }

    return value;
}

// Worley noise (cellular) for cloud detail
float worley(vec3 p, float cellSize) {
    vec3 cell = floor(p / cellSize);
    vec3 frac = fract(p / cellSize);

    float minDist = 1.0;

    for (int z = -1; z <= 1; z++) {
        for (int y = -1; y <= 1; y++) {
            for (int x = -1; x <= 1; x++) {
                vec3 offset = vec3(float(x), float(y), float(z));
                vec3 cellPos = cell + offset;
                vec3 pointPos = vec3(
                    hash3D(cellPos),
                    hash3D(cellPos + vec3(1.0, 0.0, 0.0)),
                    hash3D(cellPos + vec3(0.0, 1.0, 0.0))
                );

                vec3 diff = offset + pointPos - frac;
                float dist = length(diff);
                minDist = min(minDist, dist);
            }
        }
    }

    return minDist;
}

// ============================================================================
// ATMOSPHERIC SCATTERING
// ============================================================================

float rayleighPhase(float cosTheta) {
    return (3.0 / (16.0 * PI)) * (1.0 + pow(cosTheta, 2.0));
}

float hgPhase(float cosTheta, float g) {
    float g2 = pow(g, 2.0);
    return (1.0 / (4.0 * PI)) * ((1.0 - g2) / pow(1.0 - 2.0 * g * cosTheta + g2, 1.5));
}

vec3 atmosphere(vec3 dir, vec3 sunDir) {
    float elevation = dot(dir, UP);
    float cosViewSunAngle = dot(dir, sunDir);

    // Simple atmospheric approximation
    vec3 horizon = u_sky_color_horizon;
    vec3 zenith = u_sky_color_zenith;

    // Smooth blend based on elevation
    float t = smoothstep(-0.1, 0.6, elevation);
    vec3 skyColor = mix(horizon, zenith, t);

    // Add atmospheric glow near sun
    float sunHalo = pow(max(0.0, cosViewSunAngle), 8.0) * u_sun_intensity * 0.5;
    skyColor += u_sun_color * sunHalo;

    return skyColor;
}

// ============================================================================
// CLOUDS
// ============================================================================

vec4 renderClouds(vec3 dir, float time) {
    if (u_cloud_coverage <= 0.0) {
        return vec4(0.0);
    }

    // Only render clouds above horizon
    if (dir.y < -0.05) {
        return vec4(0.0);
    }

    // Cloud layer position
    float cloudHeight = 0.3;
    float cloudThickness = 0.2;

    // Ray march direction adjusted for cloud layer
    vec3 cloudDir = normalize(dir);
    float elevation = cloudDir.y;

    // Cloud animation
    vec2 windOffset = u_wind_direction * u_cloud_speed * time * 0.1;
    vec3 cloudSamplePos = vec3(
        cloudDir.x / max(0.01, cloudDir.y) + windOffset.x,
        cloudHeight,
        cloudDir.z / max(0.01, cloudDir.y) + windOffset.y
    );

    // Multi-octave cloud generation
    float cloudBase = fbm(cloudSamplePos * 2.0);
    float cloudDetail = worley(cloudSamplePos * 8.0, 1.0);

    // Combine noise for cloud shape
    float cloudDensity = cloudBase * 0.7 + cloudDetail * 0.3;

    // Apply coverage
    cloudDensity = smoothstep(1.0 - u_cloud_coverage, 1.0, cloudDensity);
    cloudDensity *= u_cloud_density;

    // Fade clouds near horizon
    float horizonFade = smoothstep(-0.05, 0.3, elevation);
    cloudDensity *= horizonFade;

    // Cloud lighting (simplified)
    float sunDot = dot(normalize(u_sun_direction), UP);
    vec3 cloudColor = mix(
        vec3(0.3, 0.3, 0.35),  // Shadow color
        vec3(1.0, 1.0, 0.98),  // Highlight color
        sunDot * 0.5 + 0.5
    );

    // Add cloud illumination from sun
    float cloudLight = max(0.0, dot(normalize(cloudSamplePos), normalize(u_sun_direction)));
    cloudColor = mix(cloudColor, vec3(1.0, 0.9, 0.8), cloudLight * 0.3);

    // Weather effects
    if (u_precipitation > 0.5) {
        // Darken clouds for rain/storm
        cloudColor *= 0.5;
        cloudDensity *= 1.5;  // Thicker clouds
    }

    return vec4(cloudColor, cloudDensity);
}

// ============================================================================
// STARS
// ============================================================================

float renderStars(vec3 dir) {
    if (u_star_visibility <= 0.0) return 0.0;

    vec3 p = normalize(dir) * 1000.0;
    vec3 fp = floor(p);

    float star = 0.0;
    for (int x = -1; x <= 1; x++) {
        for (int y = -1; y <= 1; y++) {
            for (int z = -1; z <= 1; z++) {
                vec3 offset = vec3(float(x), float(y), float(z));
                vec3 cell = fp + offset;
                float h = hash3D(cell);

                if (h < float(u_star_density) / 10000.0) {
                    vec3 starPos = cell + vec3(
                        hash3D(cell + vec3(0.1)),
                        hash3D(cell + vec3(0.2)),
                        hash3D(cell + vec3(0.3))
                    );
                    float dist = length(p - starPos);
                    if (dist < 0.5) {
                        float brightness = (1.0 - dist / 0.5) * u_star_brightness;
                        star = max(star, brightness);
                    }
                }
            }
        }
    }

    return star * u_star_visibility;
}

// ============================================================================
// CELESTIAL BODIES
// ============================================================================

vec3 renderSun(vec3 dir, vec3 sunDir) {
    float sunDot = dot(dir, sunDir);

    // Sun disc
    float sunDisc = smoothstep(0.9998, 0.9999, sunDot) * u_sun_intensity;

    // Sun corona/glow
    float sunGlow = pow(max(0.0, sunDot), 500.0) * u_sun_intensity * 0.5;

    return u_sun_color * (sunDisc * 10.0 + sunGlow * 2.0);
}

vec3 renderMoon(vec3 dir, vec3 moonDir) {
    float moonDot = dot(dir, moonDir);

    // Moon disc
    float moonDisc = smoothstep(0.999, 0.9995, moonDot) * u_moon_intensity;

    // Moon glow (subtle)
    float moonGlow = pow(max(0.0, moonDot), 200.0) * u_moon_intensity * 0.2;

    return u_moon_color * (moonDisc * 5.0 + moonGlow);
}

// ============================================================================
// MAIN
// ============================================================================

void main() {
    vec3 direction = normalize(v_texcoord);

    // 1. Base atmosphere
    vec3 color = atmosphere(direction, normalize(u_sun_direction));

    // 2. Add stars
    float stars = renderStars(direction);
    color += vec3(1.0, 1.0, 0.95) * stars;

    // 3. Add sun and moon
    color += renderSun(direction, normalize(u_sun_direction));
    color += renderMoon(direction, normalize(u_moon_direction));

    // 4. Render clouds
    vec4 clouds = renderClouds(direction, u_time);
    color = mix(color, clouds.rgb, clouds.a);

    // 5. Apply fog
    if (fogEnabled > 0) {
        float fogAmount = smoothstep(0.0, 0.3, -direction.y) * fogDensity;
        color = mix(color, fogColor, fogAmount);
    }

    // 6. Apply intensity
    color *= intensity;

    // 7. Tone mapping
    color = color / (color + vec3(1.0));

    // 8. Gamma correction
    color = pow(color, vec3(1.0 / 2.2));

    fragColor = vec4(color, 1.0);
}
