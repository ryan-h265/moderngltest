#version 410

// Forward Rendering - Transparent Objects Vertex Shader
// Used for alpha-blended transparent materials (BLEND mode)

// Camera matrices
uniform mat4 projection;
uniform mat4 view;
uniform mat4 model;

// Vertex attributes
in vec3 in_position;
in vec3 in_normal;
in vec2 in_texcoord;
in vec4 in_tangent;// xyz = tangent, w = handedness
in vec3 in_color;// Vertex color (COLOR_0 from GLTF)

// Outputs to fragment shader
out vec3 v_world_position;// World space position
out vec3 v_world_normal;// World space normal
out vec2 v_texcoord;// Texture coordinates
out mat3 v_TBN;// Tangent-Bitangent-Normal matrix (world space)
out vec3 v_color;// Vertex color

void main(){
    // Transform to world space
    vec4 world_pos=model*vec4(in_position,1.);
    v_world_position=world_pos.xyz;
    
    // Transform normal to world space
    v_world_normal=mat3(model)*in_normal;
    
    // Calculate TBN matrix for normal mapping (in world space)
    vec3 T=normalize(mat3(model)*in_tangent.xyz);
    vec3 N=normalize(v_world_normal);
    // Re-orthogonalize T with respect to N
    T=normalize(T-dot(T,N)*N);
    // Calculate bitangent using cross product and handedness
    vec3 B=cross(N,T)*in_tangent.w;
    // Build TBN matrix (transforms from tangent space to world space)
    v_TBN=mat3(T,B,N);
    
    // Pass through texture coordinates
    v_texcoord=in_texcoord;

    // Pass through vertex color
    v_color=in_color;

    // Transform to clip space for rendering
    gl_Position=projection*view*world_pos;
}
