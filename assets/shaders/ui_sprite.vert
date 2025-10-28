#version 410

// UI Sprite Vertex Shader
// Renders textured quads for HUD icons using screen-space coordinates.

in vec2 in_position; // Screen-space position (pixels)
in vec2 in_uv;       // Texture coordinates
in vec4 in_color;    // Vertex tint color

out vec2 v_uv;
out vec4 v_color;

uniform mat4 projection; // Orthographic projection matrix

void main(){
    gl_Position = projection * vec4(in_position, 0.0, 1.0);
    v_uv = in_uv;
    v_color = in_color;
}
