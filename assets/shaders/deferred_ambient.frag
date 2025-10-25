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

// Skybox uniforms
uniform bool skybox_enabled;
uniform samplerCube skybox_texture;
uniform mat4 inverse_projection;
uniform float skybox_intensity;
uniform mat4 skybox_rotation;
uniform float u_time;
uniform vec2 u_resolution;
uniform vec3 u_cameraPos;
uniform vec3 u_auroraDir;
uniform float u_transitionAlpha;
uniform int u_useProceduralSky;
uniform int fogEnabled;
uniform vec3 fogColor;
uniform float fogStart;
uniform float fogEnd;
uniform float fogStrength;

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

mat2 mm2(float a){
    float c=cos(a),s=sin(a);
    return mat2(c,s,-s,c);
}

mat2 m2=mat2(.95534,.29552,-.29552,.95534);

float tri(float x){return clamp(abs(fract(x)-.5),.01,.49);}

vec2 tri2(vec2 p){return vec2(tri(p.x)+tri(p.y),tri(p.y+tri(p.x)));}

float triNoise2d(vec2 p,float spd,float time){
    float z=1.8;
    float z2=2.5;
    float rz=0.;
    p*=mm2(p.x*.06);
    vec2 bp=p;
    for(float i=0.;i<5.;i++){
        vec2 dg=tri2(bp*1.85)*.75;
        dg*=mm2(time*spd);
        p-=dg/z2;
        bp*=1.3;
        z2*=.45;
        z*=.42;
        p*=1.21+(rz-1.)*.02;
        rz+=tri(p.x+tri(p.y))*z;
        p*=-m2;
    }
    return clamp(1./pow(rz*29.,1.3),0.,.55);
}

vec3 nmzHash33(vec3 q){
    uvec3 p=uvec3(ivec3(q));
    p=p*uvec3(374761393U,1103515245U,668265263U)+p.zxy+p.yzx;
    p=p.yzx*(p.zxy^(p>>3U));
    return vec3(p^(p>>16U))*(1./4294967295.);
}

vec4 aurora(vec3 ro,vec3 rd,float time){
    vec4 col=vec4(0.);
    vec4 avgCol=vec4(0.);
    for(float i=0.;i<50.;i++){
        float pt=((.8+pow(i,1.4)*.002)-ro.y)/(rd.y*2.+.4);
        vec3 bpos=ro+pt*rd;
        vec2 p=bpos.zx;
        float rzt=triNoise2d(p,.06,time);
        vec4 col2=vec4(0.);
        col2.a=rzt;
        col2.rgb=(sin(1.-vec3(2.15,-.5,1.2)+i*.043)*.5+.5)*rzt;
        avgCol=mix(avgCol,col2,.5);
        col+=avgCol*exp2(-i*.065-2.5)*smoothstep(0.,5.,i);
    }
    col*=clamp(rd.y*15.+.4,0.,1.);
    return col*1.8;
}

vec3 stars(vec3 p){
    vec3 c=vec3(0.);
    float res=max(u_resolution.x,1.);
    for(float i=0.;i<4.;i++){
        vec3 q=fract(p*(.15*res))-.5;
        vec3 id=floor(p*(.15*res));
        vec2 rn=nmzHash33(id).xy;
        float c2=1.-smoothstep(0.,.6,length(q));
        c2*=step(rn.x,.0005+i*i*.001);
        c+=c2*(mix(vec3(1.,.49,.1),vec3(.75,.9,1.),rn.y)*.1+.9);
        p*=1.3;
    }
    return c*c*.8;
}

vec3 background_color(vec3 rd){
    float sd=dot(normalize(u_auroraDir),rd)*.5+.5;
    sd=pow(sd,5.);
    vec3 col=mix(vec3(.05,.1,.2),vec3(.1,.05,.2),sd);
    return col*.63;
}

vec3 compute_aurora_sky(vec3 dir){
    vec3 rd=dir.xzy;
    rd=vec3(rd.x,rd.z,-rd.y);
    vec3 ro=vec3(0.);
    
    float fade=smoothstep(0.,.01,abs(rd.y))*.1+.9;
    vec3 col=background_color(rd)*fade;
    
    if(rd.y>0.){
        vec4 aur=smoothstep(0.,1.5,aurora(ro,rd,u_time))*fade;
        col+=stars(rd);
        col=col*(1.-aur.a)+aur.rgb;
    }else{
        rd.y=abs(rd.y);
        col=background_color(rd)*fade*.6;
        vec4 aur=smoothstep(0.,2.5,aurora(ro,rd,u_time));
        col+=stars(rd)*.1;
        col=col*(1.-aur.a)+aur.rgb;
        vec3 pos=ro+((.5-ro.y)/rd.y)*rd;
        float nz2=triNoise2d(pos.xz*vec2(.5,.7),0.,u_time);
        col+=mix(vec3(.2,.25,.5)*.08,vec3(.3,.3,.5)*.7,nz2*.4);
    }
    
    if(fogEnabled==1){
        float horizonFog=pow(clamp(1.-abs(rd.y),0.,1.),1.2);
        float fogFactor=clamp(horizonFog*fogStrength,0.,1.);
        col=mix(col,fogColor,fogFactor);
    }
    
    return col;
}

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
        if(skybox_enabled){
            vec2 ndc=v_texcoord*2.-1.;
            vec4 clip=vec4(ndc,1.,1.);
            vec4 view_dir=inverse_projection*clip;
            vec3 dir=normalize(view_dir.xyz/view_dir.w);
            vec3 world_dir=mat3(inverse_view)*dir;
            vec3 rotated_dir=mat3(skybox_rotation)*world_dir;
            
            if(u_useProceduralSky==1){
                vec3 aurora_color=compute_aurora_sky(rotated_dir);
                f_color=vec4(aurora_color*skybox_intensity,u_transitionAlpha);
            }else{
                vec3 sky_color=texture(skybox_texture,rotated_dir).rgb*skybox_intensity;
                f_color=vec4(sky_color,1.);
            }
        }else{
            f_color=vec4(.1,.1,.15,1.);
        }
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
