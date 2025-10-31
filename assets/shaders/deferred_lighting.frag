#version 410

// Deferred Rendering - Lighting Pass Fragment Shader
// Calculates lighting for a single light using G-Buffer data

// G-Buffer textures (NOTE: position and normal are in VIEW SPACE)
uniform sampler2D gPosition;// View space position
uniform sampler2D gNormal;// View space normal
uniform sampler2D gAlbedo;// Base color (RGB) + AO (A)
uniform sampler2D gMaterial;// Metallic (R) + Roughness (G)

// Transform from view space to world space
uniform mat4 inverse_view;

// Light properties
uniform vec3 light_position;
uniform vec3 light_color;
uniform float light_intensity;
uniform int light_type;// 0=directional, 1=point, 2=spot
uniform float light_range;// Effective radius for point/spot (0 = infinite)
uniform vec3 light_direction;// Direction light is pointing (normalized)
uniform float spot_inner_cos;// Cosine of inner cone angle (spot)
uniform float spot_outer_cos;// Cosine of outer cone angle (spot)

// Shadow map for this light
uniform sampler2D shadow_map;
uniform samplerCube shadow_cube_map;
uniform mat4 light_matrix;
uniform int shadow_map_type; // 0=none, 1=2D, 2=cubemap
uniform vec2 shadow_clip;    // Near/far planes for perspective shadows
uniform float shadow_bias;
uniform float point_shadow_bias;

// Camera
uniform vec3 camera_pos;

// Input from vertex shader
in vec2 v_texcoord;

// Output
out vec4 f_color;

// Fog parameters
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

/**
* Calculate shadow factor for the light
* Returns: 0.0 = no shadow, 1.0 = full shadow
*/
float linearize_depth(float depth_value, vec2 clip_planes){
    float near_plane=clip_planes.x;
    float far_plane=clip_planes.y;
    return (2.*near_plane*far_plane)/(far_plane+near_plane-depth_value*(far_plane-near_plane));
}

float calculate_projected_shadow(vec3 position){
    vec4 light_space_pos=light_matrix*vec4(position,1.);
    vec3 proj_coords=light_space_pos.xyz/light_space_pos.w;
    proj_coords=proj_coords*.5+.5;

    if(proj_coords.z>1.||proj_coords.x<0.||proj_coords.x>1.
    ||proj_coords.y<0.||proj_coords.y>1.){
        return 0.;
    }

    float current_depth=proj_coords.z;
    float bias=shadow_bias;

    float shadow=0.;
    vec2 texel_size=1./textureSize(shadow_map,0);
    for(int x=-1;x<=1;++x){
        for(int y=-1;y<=1;++y){
            float pcf_depth=texture(shadow_map,proj_coords.xy+vec2(x,y)*texel_size).r;
            shadow+=current_depth-bias>pcf_depth?1.:0.;
        }
    }
    shadow/=9.;

    return shadow;
}

float calculate_point_shadow(vec3 position){
    vec3 to_fragment=position-light_position;
    float distance_to_light=length(to_fragment);

    float far_plane=shadow_clip.y;
    if(far_plane<=0.){
        return 0.;
    }
    if(distance_to_light>far_plane){
        return 0.;
    }

    float bias=point_shadow_bias;
    float shadow=0.;

    const int sample_count=20;
    vec3 sample_offset_directions[20]=vec3[](
        vec3( 1,  1,  1), vec3( -1,  1,  1), vec3( 1, -1,  1), vec3( -1, -1,  1),
        vec3( 1,  1, -1), vec3( -1,  1, -1), vec3( 1, -1, -1), vec3( -1, -1, -1),
        vec3( 1,  0,  0), vec3(-1,  0,  0), vec3( 0,  1,  0), vec3( 0, -1,  0),
        vec3( 0,  0,  1), vec3( 0,  0, -1), vec3( 1,  1,  0), vec3(-1,  1,  0),
        vec3( 1, -1,  0), vec3(-1, -1,  0), vec3( 1,  0,  1), vec3(-1,  0,  1)
    );

    float current_depth=distance_to_light;
    float closest_depth=linearize_depth(texture(shadow_cube_map,normalize(to_fragment)).r,shadow_clip);
    shadow+=(current_depth-bias>closest_depth)?1.:0.;

    float view_distance=length(camera_pos-position);
    float disk_radius=(1.+view_distance/far_plane)*0.05;

    for(int i=0;i<sample_count;i++){
        vec3 sample_dir=normalize(to_fragment+sample_offset_directions[i]*disk_radius);
        float depth_sample=texture(shadow_cube_map,sample_dir).r;
        float closest=linearize_depth(depth_sample,shadow_clip);
        shadow+=(current_depth-bias>closest)?1.:0.;
    }

    shadow/=float(sample_count+1);
    return shadow;
}

float calculate_shadow(vec3 position){
    if(shadow_map_type==0){
        return 0.;
    }
    if(shadow_map_type==2){
        return calculate_point_shadow(position);
    }
    return calculate_projected_shadow(position);
}

/**
* Fresnel-Schlick approximation
* Returns the ratio of reflected light based on view angle
* f0: Base reflectivity at normal incidence (0° angle)
* cosTheta: cos(angle between halfway vector and view direction)
*/
vec3 fresnelSchlick(float cosTheta, vec3 f0) {
    return f0 + (1.0 - f0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

/**
* GGX (Trowbridge-Reitz) Normal Distribution Function
* Models the distribution of microfacet normals
* Returns: Higher values = more microfacets aligned with halfway vector
*/
float DistributionGGX(vec3 N, vec3 H, float roughness) {
    float a = roughness * roughness;
    float a2 = a * a;
    float NdotH = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;
    
    float num = a2;
    float denom = (NdotH2 * (a2 - 1.0) + 1.0);
    denom = 3.14159265359 * denom * denom;
    
    return num / denom;
}

/**
* Smith's Geometry Function with GGX
* Models self-shadowing of microfacets (geometric attenuation)
*/
float GeometrySchlickGGX(float NdotV,float roughness){
    float r=(roughness+1.);
    float k=(r*r)/8.;
    
    float num=NdotV;
    float denom=NdotV*(1.-k)+k;
    
    return num/denom;
}

float GeometrySmith(vec3 N,vec3 V,vec3 L,float roughness){
    float NdotV=max(dot(N,V),0.);
    float NdotL=max(dot(N,L),0.);
    float ggx2=GeometrySchlickGGX(NdotV,roughness);
    float ggx1=GeometrySchlickGGX(NdotL,roughness);
    
    return ggx1*ggx2;
}

void main(){
    // Sample G-Buffer (view space data)
    vec3 view_position=texture(gPosition,v_texcoord).rgb;
    vec3 view_normal=texture(gNormal,v_texcoord).rgb;
    vec4 albedo=texture(gAlbedo,v_texcoord);
    vec2 material=texture(gMaterial,v_texcoord).rg;
    
    // Extract material properties
    vec3 base_color=albedo.rgb;
    float ao=albedo.a;// Ambient occlusion (currently unused, set to 1.0)
    float metallic=material.r;
    float roughness=material.g;
    
    // Early exit for background pixels (no geometry)
    if(length(view_normal)<.1){
        f_color=vec4(0.,0.,0.,0.);
        return;
    }
    
    // Transform position and normal back to world space
    vec3 position=(inverse_view*vec4(view_position,1.)).xyz;
    vec3 normal=normalize(mat3(inverse_view)*view_normal);
    
    // Lighting calculations
    vec3 N=normal;
    vec3 V=normalize(camera_pos-position);
    
    // Evaluate light direction and attenuation by type
    vec3 L;// Direction from fragment to light
    float attenuation=1.;
    float distance=0.;
    
    if(light_type==0){
        // Directional light: direction is constant, no attenuation
        vec3 dir=normalize(light_direction);
        L=-dir;
    }else{
        vec3 to_light=light_position-position;
        distance=length(to_light);
        if(distance<1e-4){
            f_color=vec4(0.,0.,0.,0.);
            return;
        }
        L=to_light/distance;
        
        // Inverse-square attenuation
        attenuation=1./max(distance*distance,1e-4);
        
        if(light_range>0.){
            float normalized=clamp(distance/light_range,0.,1.);
            float smooth_factor=1.-normalized*normalized;
            attenuation*=smooth_factor*smooth_factor;
            if(normalized>=1.){
                f_color=vec4(0.,0.,0.,0.);
                return;
            }
        }
        
        if(light_type==2){
            vec3 spot_dir=normalize(light_direction);
            float cos_angle=dot(-L,spot_dir);
            float spot_factor=clamp((cos_angle-spot_outer_cos)/max(spot_inner_cos-spot_outer_cos,1e-4),0.,1.);
            attenuation*=spot_factor;
            if(attenuation<=0.){
                f_color=vec4(0.,0.,0.,0.);
                return;
            }
        }
    }
    
    vec3 H=normalize(V+L);
    
    // Calculate base reflectivity (f0)
    // For dielectrics (non-metals): f0 = 0.04 (4% reflection)
    // For metals: f0 = albedo color (they have no diffuse, only specular)
    vec3 f0=vec3(.04);
    f0=mix(f0,base_color,metallic);
    
    // Cook-Torrance BRDF
    float NDF=DistributionGGX(N,H,roughness);
    float G=GeometrySmith(N,V,L,roughness);
    vec3 F=fresnelSchlick(max(dot(H,V),0.),f0);
    
    // Calculate specular component
    vec3 numerator=NDF*G*F;
    float denominator=4.*max(dot(N,V),0.)*max(dot(N,L),0.)+.0001;
    vec3 specular=numerator/denominator;
    
    // Energy conservation: kS (specular) + kD (diffuse) = 1.0
    vec3 kS=F;// Fresnel tells us the specular contribution
    vec3 kD=vec3(1.)-kS;
    
    // Metals have no diffuse lighting (energy goes to specular only)
    kD*=1.-metallic;
    
    // Lambert diffuse
    float NdotL=max(dot(N,L),0.);
    vec3 diffuse=kD*base_color/3.14159265359;
    
    // Combine diffuse and specular
    vec3 brdf=(diffuse+specular)*light_color*NdotL;
    
    // Calculate shadow
    float shadow=calculate_shadow(position);
    
    // DEBUG MODE: Visualize shadows
    // Uncomment one of these to debug:
    // f_color=vec4(vec3(shadow),1.);return;// Show shadow mask (white=shadowed)
    // f_color=vec4(vec3(1.-shadow),1.);return;// Show lighting mask (white=lit)
    
    // Apply shadow, light intensity, and baked AO to BRDF result
    // Note: Baked AO affects direct lighting (darkens crevices for all lights)
    float fog_factor=0.;
    if(fog_enabled){
        float fog_range=max(fog_end_distance-fog_start_distance,.001);
        float distance_to_camera=length(camera_pos-position);
        float distance_factor=clamp((distance_to_camera-fog_start_distance)/fog_range,0.,1.);
        
        float height_offset=max(position.y-fog_base_height,0.);
        float height_factor=exp(-height_offset*fog_height_falloff);
        
        // Base animated position with wind
        vec3 animated_pos=position*fog_noise_scale+fog_wind_direction*(fog_time*fog_noise_speed);
        
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
        vec3 detail_pos=position*fog_detail_scale+fog_wind_direction*(fog_time*fog_noise_speed*1.7);
        float detail_noise=fbm(detail_pos,3);
        
        // Combine base and detail layers
        float combined_noise=base_noise+detail_noise*fog_detail_strength;
        
        // Normalize to [0, 1] range
        float noise_normalized=combined_noise*.5+.5;
        
        // Apply smoothstep for even softer transitions
        noise_normalized=smoothstep(.1,.9,noise_normalized);
        
        // Create more pronounced variation for wispy effect
        float variation=mix(1.-fog_noise_strength,1.+fog_noise_strength*1.5,noise_normalized);
        
        float fog_density_world=fog_density*variation*height_factor;
        fog_factor=clamp((1.-exp(-distance_to_camera*fog_density_world))*distance_factor,0.,1.);
    }
    
    vec3 lighting=light_intensity*attenuation*(1.-shadow)*brdf*ao;
    vec3 final_lighting=mix(lighting,vec3(0.),fog_factor);
    
    // Output this light's contribution (will be additively blended)
    f_color=vec4(final_lighting,1.);
}
