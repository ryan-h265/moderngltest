"""
ModernGL 3D Game with Shadow Mapping
A starter project demonstrating shadow mapping with a simple scene
"""

import moderngl
import moderngl_window as mglw
from moderngl_window import geometry
import numpy as np
from pyrr import Matrix44, Vector3, vector

class Game(mglw.WindowConfig):
    gl_version = (4, 1)  # Max version for macOS
    title = "ModernGL Shadow Mapping Demo"
    window_size = (1280, 720)
    aspect_ratio = 16 / 9
    resizable = True
    
    # Shadow map resolution
    SHADOW_SIZE = 2048
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Enable depth testing
        self.ctx.enable(moderngl.DEPTH_TEST)

        # Camera setup
        self.camera_pos = Vector3([0.0, 5.0, 10.0])
        self.camera_target = Vector3([0.0, 0.0, 0.0])
        self.camera_yaw = -90.0
        self.camera_pitch = -20.0
        self.camera_speed = 5.0
        self.mouse_sensitivity = 0.1

        # Light setup (directional light from above)
        self.light_pos = Vector3([5.0, 10.0, 5.0])
        self.light_target = Vector3([0.0, 0.0, 0.0])

        # Keyboard state tracking
        self.keys_pressed = set()

        # Load shaders
        self.load_shaders()

        # Setup shadow mapping
        self.setup_shadow_map()

        # Create scene geometry
        self.create_scene()

        # Time tracking
        self.time = 0
        
    def load_shaders(self):
        """Load all shader programs"""
        # Shadow map shader (depth only)
        self.shadow_program = self.ctx.program(
            vertex_shader='''
                #version 410
                
                uniform mat4 light_matrix;
                uniform mat4 model;
                
                in vec3 in_position;
                
                void main() {
                    gl_Position = light_matrix * model * vec4(in_position, 1.0);
                }
            ''',
            fragment_shader='''
                #version 410
                
                void main() {
                    // Depth is automatically written
                }
            '''
        )
        
        # Main render shader with shadow mapping
        self.main_program = self.ctx.program(
            vertex_shader='''
                #version 410
                
                uniform mat4 projection;
                uniform mat4 view;
                uniform mat4 model;
                uniform mat4 light_matrix;
                
                in vec3 in_position;
                in vec3 in_normal;
                
                out vec3 v_position;
                out vec3 v_normal;
                out vec4 v_light_space_pos;
                
                void main() {
                    vec4 world_pos = model * vec4(in_position, 1.0);
                    v_position = world_pos.xyz;
                    v_normal = mat3(model) * in_normal;
                    v_light_space_pos = light_matrix * world_pos;
                    
                    gl_Position = projection * view * world_pos;
                }
            ''',
            fragment_shader='''
                #version 410
                
                uniform vec3 light_pos;
                uniform vec3 camera_pos;
                uniform vec3 object_color;
                uniform sampler2D shadow_map;
                
                in vec3 v_position;
                in vec3 v_normal;
                in vec4 v_light_space_pos;
                
                out vec4 f_color;
                
                float calculate_shadow() {
                    // Perspective divide
                    vec3 proj_coords = v_light_space_pos.xyz / v_light_space_pos.w;
                    
                    // Transform to [0,1] range
                    proj_coords = proj_coords * 0.5 + 0.5;
                    
                    // Outside shadow map bounds = no shadow
                    if (proj_coords.z > 1.0 || proj_coords.x < 0.0 || proj_coords.x > 1.0 
                        || proj_coords.y < 0.0 || proj_coords.y > 1.0) {
                        return 0.0;
                    }
                    
                    // Get depth from shadow map
                    float closest_depth = texture(shadow_map, proj_coords.xy).r;
                    float current_depth = proj_coords.z;
                    
                    // Bias to prevent shadow acne
                    float bias = 0.005;
                    
                    // PCF (Percentage Closer Filtering) for soft shadows
                    float shadow = 0.0;
                    vec2 texel_size = 1.0 / textureSize(shadow_map, 0);
                    for(int x = -1; x <= 1; ++x) {
                        for(int y = -1; y <= 1; ++y) {
                            float pcf_depth = texture(shadow_map, proj_coords.xy + vec2(x, y) * texel_size).r;
                            shadow += current_depth - bias > pcf_depth ? 1.0 : 0.0;
                        }
                    }
                    shadow /= 9.0;
                    
                    return shadow;
                }
                
                void main() {
                    vec3 normal = normalize(v_normal);
                    vec3 light_dir = normalize(light_pos - v_position);
                    vec3 view_dir = normalize(camera_pos - v_position);
                    
                    // Ambient
                    float ambient_strength = 0.3;
                    vec3 ambient = ambient_strength * object_color;
                    
                    // Diffuse
                    float diff = max(dot(normal, light_dir), 0.0);
                    vec3 diffuse = diff * object_color;
                    
                    // Specular
                    vec3 halfway_dir = normalize(light_dir + view_dir);
                    float spec = pow(max(dot(normal, halfway_dir), 0.0), 32.0);
                    vec3 specular = vec3(0.3) * spec;
                    
                    // Calculate shadow
                    float shadow = calculate_shadow();
                    
                    // Combine lighting (shadow only affects diffuse and specular)
                    vec3 lighting = ambient + (1.0 - shadow) * (diffuse + specular);
                    
                    f_color = vec4(lighting, 1.0);
                }
            '''
        )
        
    def setup_shadow_map(self):
        """Create shadow map framebuffer and texture"""
        # Create depth texture for shadow map
        self.shadow_depth = self.ctx.depth_texture((self.SHADOW_SIZE, self.SHADOW_SIZE))
        self.shadow_depth.compare_func = ''  # Disable comparison for sampling
        self.shadow_depth.repeat_x = False
        self.shadow_depth.repeat_y = False
        
        # Create framebuffer for rendering shadow map
        self.shadow_fbo = self.ctx.framebuffer(depth_attachment=self.shadow_depth)
        
    def create_scene(self):
        """Create scene geometry"""
        # Ground plane
        self.ground = geometry.cube(size=(20.0, 0.5, 20.0))
        self.ground_pos = Vector3([0.0, -0.25, 0.0])
        self.ground_color = (0.3, 0.6, 0.3)  # Green
        
        # Cubes
        self.cube1 = geometry.cube(size=(2.0, 2.0, 2.0))
        self.cube1_pos = Vector3([-3.0, 1.0, 0.0])
        self.cube1_color = (0.8, 0.3, 0.3)  # Red
        
        self.cube2 = geometry.cube(size=(1.5, 3.0, 1.5))
        self.cube2_pos = Vector3([3.0, 1.5, -2.0])
        self.cube2_color = (0.3, 0.3, 0.8)  # Blue
        
        self.cube3 = geometry.cube(size=(1.0, 1.0, 1.0))
        self.cube3_pos = Vector3([0.0, 0.5, 3.0])
        self.cube3_color = (0.8, 0.8, 0.3)  # Yellow
        
        # Store all objects for easy iteration
        self.objects = [
            (self.ground, self.ground_pos, self.ground_color),
            (self.cube1, self.cube1_pos, self.cube1_color),
            (self.cube2, self.cube2_pos, self.cube2_color),
            (self.cube3, self.cube3_pos, self.cube3_color),
        ]
        
    def get_light_matrix(self):
        """Calculate light projection and view matrix"""
        # Orthographic projection for directional light
        light_projection = Matrix44.orthogonal_projection(
            left=-15, right=15, bottom=-15, top=15, near=0.1, far=50.0
        )
        
        # Light view matrix
        light_view = Matrix44.look_at(
            self.light_pos,
            self.light_target,
            Vector3([0.0, 1.0, 0.0])
        )
        
        return light_projection * light_view
        
    def get_view_matrix(self):
        """Calculate camera view matrix"""
        return Matrix44.look_at(
            self.camera_pos,
            self.camera_target,
            Vector3([0.0, 1.0, 0.0])
        )
        
    def get_projection_matrix(self):
        """Calculate camera projection matrix"""
        return Matrix44.perspective_projection(
            45.0,  # FOV
            self.aspect_ratio,
            0.1,   # Near plane
            100.0  # Far plane
        )
        
    def render_scene(self, program, light_matrix=None):
        """Render all scene objects with given shader program"""
        for obj, pos, color in self.objects:
            # Model matrix (translation)
            model = Matrix44.from_translation(pos)
            
            # Set uniforms
            program['model'].write(model.astype('f4').tobytes())
            
            # Set color and light matrix only for main render pass
            if program == self.main_program:
                program['object_color'].write(Vector3(color).astype('f4').tobytes())
                if light_matrix is not None:
                    program['light_matrix'].write(light_matrix.astype('f4').tobytes())
            
            # Render
            obj.render(program)
    
    def on_render(self, time, frametime):
        """Main render function called each frame"""
        self.time = time

        # Animate light position - rotate around the scene
        angle = time * 0.5  # Rotate at 0.5 radians per second
        radius = 12.0  # Distance from center
        height = 10.0  # Height above ground
        self.light_pos.x = radius * np.cos(angle)
        self.light_pos.z = radius * np.sin(angle)
        self.light_pos.y = height

        # Handle continuous camera movement based on keys pressed
        dt = frametime  # Delta time for frame-independent movement
        if dt > 0:
            keys = self.wnd.keys
            # Calculate forward/right vectors for camera
            forward = vector.normalise(self.camera_target - self.camera_pos)
            up = Vector3([0.0, 1.0, 0.0])
            right = vector.normalise(np.cross(forward, up))

            movement = self.camera_speed * dt
            if keys.W in self.keys_pressed:
                print("Moving Forward")
                self.camera_pos += forward * movement
                self.camera_target += forward * movement
            if keys.S in self.keys_pressed:
                print("Moving Backward")
                self.camera_pos -= forward * movement
                self.camera_target -= forward * movement
            if keys.A in self.keys_pressed:
                print("Moving Left")
                self.camera_pos -= right * movement
                self.camera_target -= right * movement
            if keys.D in self.keys_pressed:
                print("Moving Right")
                self.camera_pos += right * movement
                self.camera_target += right * movement
            if keys.Q in self.keys_pressed:
                print("Moving Up")
                self.camera_pos.y -= movement
                self.camera_target.y -= movement
            if keys.E in self.keys_pressed:
                print("Moving Down")
                self.camera_pos.y += movement
                self.camera_target.y += movement

        # Get matrices
        light_matrix = self.get_light_matrix()
        view = self.get_view_matrix()
        projection = self.get_projection_matrix()
        
        # ============ PASS 1: Render shadow map ============
        self.shadow_fbo.use()
        self.shadow_fbo.clear()
        self.ctx.viewport = (0, 0, self.SHADOW_SIZE, self.SHADOW_SIZE)
        
        # Set shadow program uniforms
        self.shadow_program['light_matrix'].write(light_matrix.astype('f4').tobytes())
        
        # Render scene from light's perspective
        self.render_scene(self.shadow_program)
        
        # ============ PASS 2: Render main scene ============
        self.ctx.screen.use()
        self.ctx.clear(0.1, 0.1, 0.15)  # Dark blue background
        self.ctx.viewport = self.wnd.viewport
        
        # Bind shadow map texture
        self.shadow_depth.use(location=0)
        
        # Set main program uniforms
        self.main_program['projection'].write(projection.astype('f4').tobytes())
        self.main_program['view'].write(view.astype('f4').tobytes())
        self.main_program['light_pos'].write(self.light_pos.astype('f4').tobytes())
        self.main_program['camera_pos'].write(self.camera_pos.astype('f4').tobytes())
        self.main_program['shadow_map'] = 0
        
        # Render scene from camera's perspective
        self.render_scene(self.main_program, light_matrix)
        
    def on_key_event(self, key, action, modifiers):
        """Handle keyboard input"""
        print(f"DEBUG: key_press_event called with key={key}, action={action}")
        keys = self.wnd.keys

        # Camera movement (WASD + QE for up/down)
        if action == keys.ACTION_PRESS:
            direction = Vector3([0.0, 0.0, 0.0])

            # Calculate forward/right vectors
            forward = vector.normalise(self.camera_target - self.camera_pos)
            up = Vector3([0.0, 1.0, 0.0])
            right = vector.normalise(np.cross(forward, up))
            
            if key == keys.W:
                self.camera_pos += forward * self.camera_speed * 0.1
                self.camera_target += forward * self.camera_speed * 0.1
            if key == keys.S:
                self.camera_pos -= forward * self.camera_speed * 0.1
                self.camera_target -= forward * self.camera_speed * 0.1
            if key == keys.A:
                self.camera_pos -= right * self.camera_speed * 0.1
                self.camera_target -= right * self.camera_speed * 0.1
            if key == keys.D:
                self.camera_pos += right * self.camera_speed * 0.1
                self.camera_target += right * self.camera_speed * 0.1
            if key == keys.Q:
                self.camera_pos.y -= self.camera_speed * 0.1
                self.camera_target.y -= self.camera_speed * 0.1
            if key == keys.E:
                self.camera_pos.y += self.camera_speed * 0.1
                self.camera_target.y += self.camera_speed * 0.1
                
            # Light movement (Arrow keys + ZX for up/down)
            if key == keys.UP:
                self.light_pos.z -= 1.0
            if key == keys.DOWN:
                self.light_pos.z += 1.0
            if key == keys.LEFT:
                self.light_pos.x -= 1.0
            if key == keys.RIGHT:
                self.light_pos.x += 1.0
            if key == keys.Z:
                self.light_pos.y -= 1.0
            if key == keys.X:
                self.light_pos.y += 1.0

if __name__ == '__main__':
    Game.run()
