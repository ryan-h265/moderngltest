#version 330 core

in vec2 uv;
in vec4 offset[3];

out vec4 fragColor;

uniform sampler2D colorTex;
uniform vec4 SMAA_RT_METRICS; // (1/width, 1/height, width, height)

// SMAA Edge Detection Settings
#define SMAA_THRESHOLD 0.1
#define SMAA_DEPTH_THRESHOLD 0.01

float SMAALuma(vec3 color) {
    return dot(color, vec3(0.2126, 0.7152, 0.0722));
}

vec2 SMAAColorEdgeDetection(vec2 texcoord, vec4 offset[3], sampler2D colorTex) {
    // Get center pixel
    vec3 C = texture(colorTex, texcoord).rgb;
    
    // Get neighbor pixels using precomputed offsets
    vec3 Cleft = texture(colorTex, offset[0].xy).rgb;
    vec3 Ctop = texture(colorTex, offset[0].zw).rgb;
    vec3 Cright = texture(colorTex, offset[1].xy).rgb;
    vec3 Cbottom = texture(colorTex, offset[1].zw).rgb;
    
    // Calculate deltas
    vec4 delta;
    delta.x = abs(SMAALuma(C) - SMAALuma(Cleft));
    delta.y = abs(SMAALuma(C) - SMAALuma(Ctop));
    delta.z = abs(SMAALuma(C) - SMAALuma(Cright));
    delta.w = abs(SMAALuma(C) - SMAALuma(Cbottom));
    
    // Check threshold
    vec2 edges = step(SMAA_THRESHOLD, delta.xy);
    
    if (dot(edges, vec2(1.0)) == 0.0)
        return vec2(0.0);
    
    // More accurate edge detection for diagonal edges
    vec3 Cleftleft = texture(colorTex, offset[2].xy).rgb;
    vec3 Ctoptop = texture(colorTex, offset[2].zw).rgb;
    
    // Calculate more deltas for better edge detection
    delta.z = abs(SMAALuma(Cleft) - SMAALuma(Cleftleft));
    delta.w = abs(SMAALuma(Ctop) - SMAALuma(Ctoptop));
    
    // Refine edge detection
    vec2 maxDelta = max(delta.xy, delta.zw);
    edges.xy *= step(maxDelta, vec2(0.25 * maxDelta));
    
    return edges;
}

void main() {
    vec2 edges = SMAAColorEdgeDetection(uv, offset, colorTex);
    fragColor = vec4(edges, 0.0, 1.0);
}