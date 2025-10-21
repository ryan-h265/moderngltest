#version 410

// Deferred Rendering - Lighting Pass Fragment Shader
// Calculates lighting for a single light using G-Buffer data

// G-Buffer textures
uniform sampler2D gPosition;// World position
uniform sampler2D gNormal;// World normal
uniform sampler2D gAlbedo;// Base color + specular

// Light properties
uniform vec3 light_position;
uniform vec3 light_color;
uniform float light_intensity;

// Shadow map for this light
uniform sampler2D shadow_map;
uniform mat4 light_matrix;

// Camera
uniform vec3 camera_pos;

// Input from vertex shader
in vec2 v_texcoord;

// Output
out vec4 f_color;

/**
* Calculate shadow factor for the light
* Returns: 0.0 = no shadow, 1.0 = full shadow
*/
float calculate_shadow(vec3 position){
    // Transform position to light space
    vec4 light_space_pos=light_matrix*vec4(position,1.);
    
    // Perspective divide
    vec3 proj_coords=light_space_pos.xyz/light_space_pos.w;
    
    // Transform from [-1,1] to [0,1] for texture coordinates
    proj_coords=proj_coords*.5+.5;
    
    // Outside shadow map bounds = no shadow
    if(proj_coords.z>1.||proj_coords.x<0.||proj_coords.x>1.
    ||proj_coords.y<0.||proj_coords.y>1.){
        return 0.;
    }
    
    // Get depth from shadow map
    float closest_depth=texture(shadow_map,proj_coords.xy).r;
    float current_depth=proj_coords.z;
    
    // Bias to prevent shadow acne
    float bias=.005;
    
    // PCF (Percentage Closer Filtering) for soft shadows
    float shadow=0.;
    vec2 texel_size=1./textureSize(shadow_map,0);
    for(int x=-1;x<=1;++x){
        for(int y=-1;y<=1;++y){
            float pcf_depth=texture(shadow_map,proj_coords.xy+vec2(x,y)*texel_size).r;
            shadow+=current_depth-bias>pcf_depth?1.:0.;
        }
    }
    shadow/=9.;// Average of 9 samples
    
    return shadow;
}

void main(){
    // Sample G-Buffer
    vec3 position=texture(gPosition,v_texcoord).rgb;
    vec3 normal=texture(gNormal,v_texcoord).rgb;
    vec4 albedo=texture(gAlbedo,v_texcoord);
    
    // Extract material properties
    vec3 base_color=albedo.rgb;
    float specular_intensity=albedo.a;
    
    // Early exit for background pixels (no geometry)
    if(length(normal)<.1){
        f_color=vec4(0.,0.,0.,0.);
        return;
    }
    
    // Lighting calculations
    vec3 light_dir=normalize(light_position-position);
    vec3 view_dir=normalize(camera_pos-position);
    
    // Diffuse (Lambert)
    float diff=max(dot(normal,light_dir),0.);
    vec3 diffuse=diff*base_color*light_color;
    
    // Specular (Blinn-Phong)
    vec3 halfway_dir=normalize(light_dir+view_dir);
    float spec=pow(max(dot(normal,halfway_dir),0.),32.);
    vec3 specular=specular_intensity*spec*light_color;
    
    // Calculate shadow
    float shadow=calculate_shadow(position);
    
    // DEBUG MODE: Visualize shadows
    // Uncomment one of these to debug:
    // f_color=vec4(vec3(shadow),1.);return;// Show shadow mask (white=shadowed)
    // f_color=vec4(vec3(1.-shadow),1.);return;// Show lighting mask (white=lit)
    
    // Combine lighting (attenuated by intensity and shadow)
    vec3 lighting=light_intensity*(1.-shadow)*(diffuse+specular);
    
    // Output this light's contribution (will be additively blended)
    f_color=vec4(lighting,1.);
}
