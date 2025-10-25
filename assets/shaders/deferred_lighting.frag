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
uniform mat4 light_matrix;

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
        
        vec3 animated_pos=position*fog_noise_scale+fog_wind_direction*(fog_time*fog_noise_speed);
        float trig_noise=sin(animated_pos.x)+sin(animated_pos.y*1.3+animated_pos.z*.7)+sin(animated_pos.z*1.7-animated_pos.x*.5);
        trig_noise=trig_noise/3.;
        float noise_normalized=trig_noise*.5+.5;
        float variation=mix(1.-fog_noise_strength,1.+fog_noise_strength,noise_normalized);
        
        float fog_density_world=fog_density*variation*height_factor;
        fog_factor=clamp((1.-exp(-distance_to_camera*fog_density_world))*distance_factor,0.,1.);
    }
    
    vec3 lighting=light_intensity*attenuation*(1.-shadow)*brdf*ao;
    vec3 final_lighting=mix(lighting,vec3(0.),fog_factor);
    
    // Output this light's contribution (will be additively blended)
    f_color=vec4(final_lighting,1.);
}
