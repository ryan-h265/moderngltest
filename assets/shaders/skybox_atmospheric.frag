#version 410

/**
 * Atmospheric Scattering Skybox Shader
 *
 * Implements physically-based atmospheric scattering using the Preetham model
 * with Rayleigh and Mie scattering for realistic sky rendering.
 *
 * Industry-standard approach used in games and real-time rendering.
 */

in vec3 v_texcoord;
out vec4 fragColor;

// Basic uniforms
uniform float intensity;
uniform samplerCube skybox_texture;

// Time of day uniforms
uniform float u_time_of_day;  // 0.0-1.0
uniform vec3 u_sun_direction;
uniform vec3 u_sun_color;
uniform float u_sun_intensity;
uniform vec3 u_moon_direction;
uniform vec3 u_moon_color;
uniform float u_moon_intensity;

// Atmospheric scattering uniforms
uniform vec3 u_rayleigh_coefficient;  // Wavelength-dependent scattering
uniform float u_mie_coefficient;       // Aerosol scattering
uniform float u_sun_brightness;
uniform float u_turbidity;             // Atmosphere haziness

// Star field uniforms
uniform float u_star_visibility;
uniform float u_star_brightness;
uniform int u_star_density;

// Sky color uniforms (from time-of-day system)
uniform vec3 u_sky_color_zenith;
uniform vec3 u_sky_color_horizon;

// Constants
const float PI = 3.14159265359;
const float RAYLEIGH_ZENITH_LENGTH = 8.4e3;
const float MIE_ZENITH_LENGTH = 1.25e3;
const vec3 UP = vec3(0.0, 1.0, 0.0);

// Preetham atmospheric scattering model
vec3 totalRayleigh(vec3 lambda) {
    return (8.0 * pow(PI, 3.0) * pow(pow(1.00029, 2.0) - 1.0, 2.0) * (6.0 + 3.0 * 0.035))
           / (3.0 * 2.545e25 * pow(lambda, vec3(4.0)) * (6.0 - 7.0 * 0.035));
}

float rayleighPhase(float cosTheta) {
    return (3.0 / (16.0 * PI)) * (1.0 + pow(cosTheta, 2.0));
}

vec3 totalMie(vec3 lambda, vec3 K, float T) {
    float c = (0.2 * T) * 10e-18;
    return 0.434 * c * PI * pow((2.0 * PI) / lambda, vec3(0.84)) * K;
}

float hgPhase(float cosTheta, float g) {
    float g2 = pow(g, 2.0);
    return (1.0 / (4.0 * PI)) * ((1.0 - g2) / pow(1.0 - 2.0 * g * cosTheta + g2, 1.5));
}

float sunIntensity(float zenithAngleCos) {
    zenithAngleCos = clamp(zenithAngleCos, -1.0, 1.0);
    return u_sun_brightness * max(0.0, 1.0 - exp(-((1.0 - zenithAngleCos) * 0.5 * u_turbidity)));
}

// Simple star field generation
float random(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

float stars(vec3 dir) {
    if (u_star_visibility <= 0.0) return 0.0;

    // Use spherical coordinates for star generation
    vec3 p = normalize(dir) * 1000.0;
    vec3 fp = floor(p);
    vec3 pp = p - fp;

    float star = 0.0;
    for (int x = -1; x <= 1; x++) {
        for (int y = -1; y <= 1; y++) {
            for (int z = -1; z <= 1; z++) {
                vec3 offset = vec3(float(x), float(y), float(z));
                vec3 cell = fp + offset;
                float h = random(cell.xy + cell.z);

                if (h < float(u_star_density) / 10000.0) {
                    vec3 starPos = cell + vec3(
                        random(cell.xy * 1.1),
                        random(cell.yz * 1.2),
                        random(cell.xz * 1.3)
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

void main() {
    vec3 direction = normalize(v_texcoord);

    // Calculate view angle
    float cosViewSunAngle = dot(direction, normalize(u_sun_direction));
    float cosMoonAngle = dot(direction, normalize(u_moon_direction));
    float elevation = dot(direction, UP);

    // Atmospheric scattering calculation
    vec3 lambda = vec3(680e-9, 550e-9, 450e-9);  // RGB wavelengths

    // Calculate scattering coefficients
    vec3 betaR = totalRayleigh(lambda) * u_rayleigh_coefficient;
    vec3 betaM = totalMie(lambda, vec3(u_mie_coefficient), u_turbidity) * 0.1;

    // Calculate optical depth
    float zenithAngle = acos(max(0.0, dot(UP, normalize(u_sun_direction))));
    float sunE = sunIntensity(dot(UP, normalize(u_sun_direction)));

    // Path length through atmosphere
    float rayleighOpticalDepth = RAYLEIGH_ZENITH_LENGTH / (elevation + 0.15);
    float mieOpticalDepth = MIE_ZENITH_LENGTH / (elevation + 0.15);

    // Extinction (light absorbed and scattered out)
    vec3 fex = exp(-(betaR * rayleighOpticalDepth + betaM * mieOpticalDepth));

    // In-scattering
    float rayleighPhaseValue = rayleighPhase(cosViewSunAngle);
    float miePhaseValue = hgPhase(cosViewSunAngle, 0.85);

    vec3 betaRTheta = betaR * rayleighPhaseValue;
    vec3 betaMTheta = betaM * miePhaseValue;

    vec3 Lin = pow(sunE * ((betaRTheta + betaMTheta) / (betaR + betaM)) * (1.0 - fex), vec3(1.5));
    Lin *= mix(vec3(1.0), pow(sunE * ((betaRTheta + betaMTheta) / (betaR + betaM)) * fex, vec3(0.5)), clamp(pow(1.0 - dot(UP, normalize(u_sun_direction)), 5.0), 0.0, 1.0));

    // Blend with time-of-day colors for smooth transitions
    vec3 skyColor = mix(u_sky_color_horizon, u_sky_color_zenith, smoothstep(0.0, 0.5, elevation));

    // Daytime: use atmospheric scattering
    // Night: use dark sky colors
    float dayNightBlend = smoothstep(-0.1, 0.2, dot(UP, normalize(u_sun_direction)));
    vec3 atmosphereColor = mix(skyColor * 0.1, Lin * 2.0, dayNightBlend);

    // Add sun disc
    float sunDisc = smoothstep(0.9998, 0.9999, cosViewSunAngle) * u_sun_intensity;
    atmosphereColor += u_sun_color * sunDisc * 10.0;

    // Add moon disc
    float moonDisc = smoothstep(0.999, 0.9995, cosMoonAngle) * u_moon_intensity;
    atmosphereColor += u_moon_color * moonDisc * 5.0;

    // Add stars
    float starField = stars(direction);
    atmosphereColor += vec3(1.0, 1.0, 0.95) * starField;

    // Apply intensity
    atmosphereColor *= intensity;

    // Tone mapping (simple Reinhard)
    atmosphereColor = atmosphereColor / (atmosphereColor + vec3(1.0));

    // Gamma correction
    atmosphereColor = pow(atmosphereColor, vec3(1.0 / 2.2));

    fragColor = vec4(atmosphereColor, 1.0);
}
