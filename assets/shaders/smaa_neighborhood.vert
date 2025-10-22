#version 330 core

in vec2 in_position;
in vec2 in_texcoord;

out vec2 uv;
out vec4 offset;

uniform vec4 SMAA_RT_METRICS; // (1/width, 1/height, width, height)

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    uv = in_texcoord;
    
    // Calculate neighbor sampling offsets
    offset = uv.xyxy + SMAA_RT_METRICS.xyxy * vec4(1.0, 0.0, 0.0, 1.0);
}