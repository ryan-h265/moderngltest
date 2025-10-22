#version 410

// UI Text Vertex Shader
// Orthographic projection for screen-space text rendering

// Inputs
in vec2 in_position;// Screen-space position (pixels)
in vec4 in_color;// Vertex color (RGBA)

// Outputs
out vec4 v_color;

// Uniforms
uniform mat4 projection;// Orthographic projection matrix

void main(){
    // Transform to clip space using orthographic projection
    gl_Position=projection*vec4(in_position,0.,1.);
    
    // Pass through vertex color
    v_color=in_color;
}
