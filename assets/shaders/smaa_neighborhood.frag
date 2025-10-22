#version 330 core

in vec2 uv;
in vec4 offset;

out vec4 fragColor;

uniform sampler2D colorTex;
uniform sampler2D blendTex;
uniform vec4 SMAA_RT_METRICS; // (1/width, 1/height, width, height)

vec4 SMAANeighborhoodBlending(vec2 texcoord, vec4 offset, sampler2D colorTex, sampler2D blendTex) {
    // Get blending weights from the blending weight calculation pass
    vec4 weights = texture(blendTex, texcoord);
    
    // Early exit if no blending is needed
    if (dot(weights, vec4(1.0)) < 1e-5) {
        return texture(colorTex, texcoord);
    }
    
    // Sample neighbors based on weights
    vec4 color = texture(colorTex, texcoord);
    
    // Horizontal blending (weights.r and weights.b)
    if (weights.r > 0.0) {
        vec2 coord = texcoord - SMAA_RT_METRICS.xy * vec2(1.0, 0.0);
        vec4 left = texture(colorTex, coord);
        color = mix(color, left, weights.r);
    }
    
    if (weights.b > 0.0) {
        vec2 coord = texcoord + SMAA_RT_METRICS.xy * vec2(1.0, 0.0);
        vec4 right = texture(colorTex, coord);
        color = mix(color, right, weights.b);
    }
    
    // Vertical blending (weights.g and weights.a)
    if (weights.g > 0.0) {
        vec2 coord = texcoord - SMAA_RT_METRICS.xy * vec2(0.0, 1.0);
        vec4 top = texture(colorTex, coord);
        color = mix(color, top, weights.g);
    }
    
    if (weights.a > 0.0) {
        vec2 coord = texcoord + SMAA_RT_METRICS.xy * vec2(0.0, 1.0);
        vec4 bottom = texture(colorTex, coord);
        color = mix(color, bottom, weights.a);
    }
    
    return color;
}

void main() {
    fragColor = SMAANeighborhoodBlending(uv, offset, colorTex, blendTex);
}