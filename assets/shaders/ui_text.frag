#version 410

// UI Text Fragment Shader
// Outputs interpolated vertex color

// Inputs from vertex shader
in vec4 v_color;

// Output
out vec4 fragColor;

void main(){
    if(v_color.a<=0.){
        discard;
    }
    
    fragColor=v_color;
}
