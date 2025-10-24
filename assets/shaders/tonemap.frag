#version 410

uniform sampler2D hdr_texture;
uniform float exposure;
uniform int operator_id;

in vec2 v_uv;
out vec4 f_color;

vec3 aces_film(vec3 x) {
    const float a = 2.51;
    const float b = 0.03;
    const float c = 2.43;
    const float d = 0.59;
    const float e = 0.14;
    return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}

vec3 uncharted2_tonemap(vec3 x) {
    const float A = 0.15;
    const float B = 0.50;
    const float C = 0.10;
    const float D = 0.20;
    const float E = 0.02;
    const float F = 0.30;
    const float W = 11.2;

    vec3 curr = ((x * (A * x + C * B) + D * E) / (x * (A * x + B) + D * F)) - E / F;
    vec3 white = ((vec3(W) * (A * vec3(W) + C * B) + D * E) / (vec3(W) * (A * vec3(W) + B) + D * F)) - E / F;
    return clamp(curr / white, 0.0, 1.0);
}

void main() {
    vec3 hdr = texture(hdr_texture, v_uv).rgb;
    vec3 color = hdr * exposure;
    vec3 mapped;

    if (operator_id == 1) {
        mapped = color / (vec3(1.0) + color);
    } else if (operator_id == 2) {
        mapped = uncharted2_tonemap(color);
    } else {
        mapped = aces_film(color);
    }

    mapped = pow(mapped, vec3(1.0 / 2.2));
    f_color = vec4(mapped, 1.0);
}
