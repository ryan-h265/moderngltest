#version 410

// Editor Preview Vertex Shader - SIMPLE MVP
// Just transform vertices to clip space

// Vertex attributes
in vec3 in_position;
in vec3 in_normal;
in vec3 in_tangent;
in vec2 in_texcoord;
in vec3 in_color;

// Uniforms
uniform mat4 projection;
uniform mat4 view;
uniform mat4 model;

void main(){
    // Transform to clip space
    gl_Position = projection * view * model * vec4(in_position, 1.0);
}
