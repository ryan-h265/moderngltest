#version 410

// Deferred Rendering - Ambient Lighting Fragment Shader
// Adds base ambient lighting with optional SSAO

// G-Buffer textures
uniform sampler2D gPosition;
uniform sampler2D gNormal;
uniform sampler2D gAlbedo;

// SSAO texture (optional)
uniform sampler2D ssaoTexture;
uniform bool ssaoEnabled;
uniform float ssaoIntensity;

// Ambient strength
uniform float ambient_strength;

// Camera + fog uniforms
uniform mat4 inverse_view;
uniform vec3 camera_pos;
uniform bool fog_enabled;
uniform vec3 fog_color;
uniform float fog_density;
uniform float fog_start_distance;
uniform float fog_end_distance;
uniform float fog_base_height;
uniform float fog_height_falloff;
uniform float fog_noise_scale;
uniform float fog_noise_strength;
uniform float fog_noise_speed;
uniform vec3 fog_wind_direction;
uniform float fog_time;
uniform float fog_detail_scale;
uniform float fog_detail_strength;
uniform float fog_warp_strength;

// Input from vertex shader
in vec2 v_texcoord;

// Output
out vec4 f_color;

// Improved 3D pseudo-Perlin noise function
vec3 hash3(vec3 p){
    p=fract(p*vec3(443.897,441.423,437.195));
    p+=dot(p,p.yxz+19.19);
    return fract(vec3((p.x+p.y)*p.z,(p.x+p.z)*p.y,(p.y+p.z)*p.x));
}

float noise3d(vec3 p){
    vec3 i=floor(p);
    vec3 f=fract(p);
    
    // Quintic interpolation for smoother results
    vec3 u=f*f*f*(f*(f*6.-15.)+10.);
    
    // Sample 8 corners of the cube
    float n000=dot(hash3(i+vec3(0,0,0))-.5,f-vec3(0,0,0));
    float n100=dot(hash3(i+vec3(1,0,0))-.5,f-vec3(1,0,0));
    float n010=dot(hash3(i+vec3(0,1,0))-.5,f-vec3(0,1,0));
    float n110=dot(hash3(i+vec3(1,1,0))-.5,f-vec3(1,1,0));
    float n001=dot(hash3(i+vec3(0,0,1))-.5,f-vec3(0,0,1));
    float n101=dot(hash3(i+vec3(1,0,1))-.5,f-vec3(1,0,1));
    float n011=dot(hash3(i+vec3(0,1,1))-.5,f-vec3(0,1,1));
    float n111=dot(hash3(i+vec3(1,1,1))-.5,f-vec3(1,1,1));
    
    // Trilinear interpolation
    return mix(
        mix(mix(n000,n100,u.x),mix(n010,n110,u.x),u.y),
        mix(mix(n001,n101,u.x),mix(n011,n111,u.x),u.y),
        u.z
    );
}

// Fractional Brownian Motion - multiple octaves of noise
float fbm(vec3 p,int octaves){
    float value=0.;
    float amplitude=.5;
    float frequency=1.;
    float total_amplitude=0.;
    
    for(int i=0;i<octaves;i++){
        value+=amplitude*noise3d(p*frequency);
        total_amplitude+=amplitude;
        amplitude*=.5;
        frequency*=2.;
    }
    
    return value/total_amplitude;
}

float compute_fog_factor(vec3 world_pos){
    if(!fog_enabled){
        return 0.;
    }
    
    float distance_to_camera=length(camera_pos-world_pos);
    float range=max(fog_end_distance-fog_start_distance,.001);
    float distance_factor=clamp((distance_to_camera-fog_start_distance)/range,0.,1.);
    
    float height_offset=max(world_pos.y-fog_base_height,0.);
    float height_factor=exp(-height_offset*fog_height_falloff);
    
    // Base animated position with wind
    vec3 animated_pos=world_pos*fog_noise_scale+fog_wind_direction*(fog_time*fog_noise_speed);
    
    // Domain warping: use one noise field to distort another for organic flow
    vec3 warp_offset=vec3(
        fbm(animated_pos+vec3(0.,0.,0.),2),
        fbm(animated_pos+vec3(5.2,1.3,8.4),2),
        fbm(animated_pos+vec3(3.7,9.1,2.8),2)
    )*fog_warp_strength;
    
    vec3 warped_pos=animated_pos+warp_offset;
    
    // Main fog density with 5 octaves for smooth, organic variation
    float base_noise=fbm(warped_pos,5);
    
    // Add a second layer moving at different speed for depth
    vec3 detail_pos=world_pos*fog_detail_scale+fog_wind_direction*(fog_time*fog_noise_speed*1.7);
    float detail_noise=fbm(detail_pos,3);
    
    // Combine base and detail layers
    float combined_noise=base_noise+detail_noise*fog_detail_strength;
    
    // Normalize to [0, 1] range
    float noise_normalized=combined_noise*.5+.5;
    
    // Apply smoothstep for even softer transitions
    noise_normalized=smoothstep(.1,.9,noise_normalized);
    
    // Create more pronounced variation for wispy effect
    float variation=mix(1.-fog_noise_strength,1.+fog_noise_strength*1.5,noise_normalized);
    
    // Apply variation to density with height falloff
    float density=fog_density*variation*height_factor;
    
    // Exponential fog with distance
    float fog_amount=1.-exp(-distance_to_camera*density);
    
    return clamp(fog_amount*distance_factor,0.,1.);
}

void main(){
    // Sample albedo + baked AO from G-Buffer
    vec3 view_position=texture(gPosition,v_texcoord).rgb;
    vec4 albedo_ao=texture(gAlbedo,v_texcoord);
    vec3 base_color=albedo_ao.rgb;
    float baked_ao=albedo_ao.a;// Baked occlusion from GLTF texture (1.0 if none)
    vec3 normal=texture(gNormal,v_texcoord).rgb;
    
    // Early exit for background pixels (no geometry)
    if(length(normal)<.1){
        // Background color (dark blue)
        f_color=vec4(.1,.1,.15,1.);
        return;
    }
    
    // Get SSAO occlusion factor (screen-space, dynamic)
    float ssao=1.;
    if(ssaoEnabled){
        float ssao_sample=texture(ssaoTexture,v_texcoord).r;
        // Mix between full occlusion and no occlusion
        ssao=mix(1.-ssaoIntensity,1.,ssao_sample);
    }
    
    // Combine baked AO and SSAO (multiply for best results)
    // - Baked AO: High-quality, fine detail (crevices, seams)
    // - SSAO: Dynamic, large-scale occlusion (nearby geometry)
    float combined_ao=baked_ao*ssao;
    
    // Ambient lighting modulated by combined AO
    vec3 ambient=ambient_strength*base_color*combined_ao;
    
    vec3 world_position=(inverse_view*vec4(view_position,1.)).xyz;
    float fog_factor=compute_fog_factor(world_position);
    vec3 final_color=mix(ambient,fog_color,fog_factor);
    
    f_color=vec4(final_color,1.);
}
