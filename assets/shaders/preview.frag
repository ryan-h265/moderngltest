#version 410

// Editor Preview Fragment Shader - SIMPLE MVP
// Just output green tinted color with alpha

// Material properties
uniform vec4 baseColorFactor;
uniform vec4 previewTint = vec4(0.2, 1.0, 0.2, 0.5);  // Green with 50% alpha

// Inputs from vertex shader
in vec3 v_color;

// Output color
out vec4 fragColor;

void main(){
    // Simple: use preview tint color directly
    fragColor = previewTint;
}
