#version 330 core

in vec2 in_position;
in vec2 in_texcoord;

out vec2 uv;
out vec2 pixcoord;
out vec4 offset[3];

uniform vec4 SMAA_RT_METRICS; // (1/width, 1/height, width, height)

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    uv = in_texcoord;
    pixcoord = uv * SMAA_RT_METRICS.zw;
    
    // Calculate offsets for pattern matching
    offset[0] = uv.xyxy + SMAA_RT_METRICS.xyxy * vec4(-0.25, -0.125, 1.25, -0.125);
    offset[1] = uv.xyxy + SMAA_RT_METRICS.xyxy * vec4(-0.125, -0.25, -0.125, 1.25);
    offset[2] = uv.xyxy + SMAA_RT_METRICS.xyxy * vec4(-2.0, 2.0, -2.0, 2.0) * SMAA_RT_METRICS.xyxy;
}