#version 410

// Unlit Vertex Shader (KHR_materials_unlit)
// Identical to textured geometry vertex shader

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

in vec3 in_position;
in vec3 in_normal;
in vec2 in_texcoord;
in vec4 in_tangent;
in vec3 in_color;  // Vertex color (COLOR_0 from GLTF)

out vec3 v_world_position;
out vec3 v_view_position;
out vec3 v_world_normal;
out vec3 v_view_normal;
out vec2 v_texcoord;
out mat3 v_TBN;
out vec3 v_color;  // Vertex color

void main(){
    // Transform position to world space
    vec4 world_pos=model*vec4(in_position,1.);
    v_world_position=world_pos.xyz;
    
    // Transform position to view space
    vec4 view_pos=view*world_pos;
    v_view_position=view_pos.xyz;
    
    // Transform normal to world space
    mat3 normal_matrix=transpose(inverse(mat3(model)));
    v_world_normal=normalize(normal_matrix*in_normal);
    
    // Transform normal to view space
    mat3 view_normal_matrix=mat3(view);
    v_view_normal=normalize(view_normal_matrix*v_world_normal);
    
    // Build TBN matrix in view space (for normal mapping)
    vec3 T=normalize(view_normal_matrix*normalize(normal_matrix*in_tangent.xyz));
    vec3 N=v_view_normal;
    vec3 B=cross(N,T)*in_tangent.w;
    v_TBN=mat3(T,B,N);
    
    // Pass through texture coordinates
    v_texcoord=in_texcoord;

    // Pass through vertex color
    v_color=in_color;

    // Final position in clip space
    gl_Position=projection*view_pos;
}
