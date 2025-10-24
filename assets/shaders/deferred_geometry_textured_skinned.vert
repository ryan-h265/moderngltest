#version 410

// Deferred Rendering - Geometry Pass Vertex Shader (Skinned Meshes)
// Implements GPU skinning with matrix palette

// Camera matrices
uniform mat4 projection;
uniform mat4 view;
uniform mat4 model;

// Skinning uniforms
const int MAX_JOINTS = 128;
uniform mat4 jointMatrices[MAX_JOINTS];  // Joint matrices for skinning

// Vertex attributes
in vec3 in_position;
in vec3 in_normal;
in vec2 in_texcoord;
in vec4 in_tangent;     // xyz = tangent, w = handedness
in vec3 in_color;       // Vertex color (COLOR_0 from GLTF)
in vec4 in_joints;      // Joint indices (4 bones per vertex)
in vec4 in_weights;     // Joint weights (4 weights per vertex)

// Outputs to fragment shader
out vec3 v_world_position;  // World space position
out vec3 v_view_position;   // View space position
out vec3 v_world_normal;    // World space normal
out vec3 v_view_normal;     // View space normal
out vec2 v_texcoord;        // Texture coordinates
out mat3 v_TBN;             // Tangent-Bitangent-Normal matrix (view space)
out vec3 v_color;           // Vertex color

void main() {
    // Compute skinned position and normal
    // Skinning formula: skinned_pos = sum(weight[i] * jointMatrix[i] * position)

    // Initialize skinned position and normal
    vec4 skinned_pos = vec4(0.0);
    vec4 skinned_normal = vec4(0.0);
    vec4 skinned_tangent = vec4(0.0);

    // Apply skinning for up to 4 joints per vertex
    for (int i = 0; i < 4; i++) {
        int joint_index = int(in_joints[i]);
        float weight = in_weights[i];

        if (weight > 0.0) {
            mat4 joint_matrix = jointMatrices[joint_index];
            skinned_pos += weight * (joint_matrix * vec4(in_position, 1.0));
            skinned_normal += weight * (joint_matrix * vec4(in_normal, 0.0));
            skinned_tangent += weight * (joint_matrix * vec4(in_tangent.xyz, 0.0));
        }
    }

    // Normalize the skinned normal and tangent
    vec3 final_normal = normalize(skinned_normal.xyz);
    vec3 final_tangent = normalize(skinned_tangent.xyz);

    // Transform to world space
    vec4 world_pos = model * skinned_pos;
    v_world_position = world_pos.xyz;

    // Transform to view space
    vec4 view_pos = view * world_pos;
    v_view_position = view_pos.xyz;

    // Transform normal to world space (simplified - assumes uniform scaling)
    v_world_normal = mat3(model) * final_normal;

    // Transform normal to view space
    v_view_normal = mat3(view) * v_world_normal;

    // Calculate TBN matrix for normal mapping (in view space)
    vec3 T = normalize(mat3(view) * mat3(model) * final_tangent);
    vec3 N = normalize(v_view_normal);
    // Re-orthogonalize T with respect to N
    T = normalize(T - dot(T, N) * N);
    // Calculate bitangent using cross product and handedness
    vec3 B = cross(N, T) * in_tangent.w;
    // Build TBN matrix (transforms from tangent space to view space)
    v_TBN = mat3(T, B, N);

    // Pass through texture coordinates
    v_texcoord = in_texcoord;

    // Pass through vertex color
    v_color = in_color;

    // Transform to clip space for rendering
    gl_Position = projection * view_pos;
}
