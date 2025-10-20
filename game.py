"""
ModernGL 3D Game with Shadow Mapping
A starter project demonstrating shadow mapping with a simple scene
"""

import moderngl
import moderngl_window as mglw
from moderngl_window import geometry
import numpy as np
from pyrr import Matrix44, Vector3, vector
from dataclasses import dataclass

@dataclass
class Light:
    """Represents a shadow-casting light source"""
    position: Vector3
    target: Vector3
    color: Vector3
    intensity: float
    shadow_map: moderngl.Texture = None
    shadow_fbo: moderngl.Framebuffer = None
    light_type: str = 'directional'  # 'directional', 'point', or 'spot'

    def get_light_matrix(self) -> Matrix44:
        """Calculate light projection and view matrix"""
        # Orthographic projection for directional light
        light_projection = Matrix44.orthogonal_projection(
            left=-15, right=15, bottom=-15, top=15, near=0.1, far=50.0
        )

        # Light view matrix
        light_view = Matrix44.look_at(
            self.position,
            self.target,
            Vector3([0.0, 1.0, 0.0])
        )

        return light_projection * light_view

class Game(mglw.WindowConfig):
    gl_version = (4, 1)  # Max version for macOS
    title = "ModernGL Shadow Mapping Demo"
    window_size = (1280, 720)
    aspect_ratio = 16 / 9
    resizable = True
    
    # Shadow map resolution
    SHADOW_SIZE = 2048
    NUM_LIGHTS = 2  # Number of shadow-casting lights

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

        # Keyboard state tracking
        self.keys_pressed = set()

        # Mouse state tracking
        self.mouse_captured = True
        self.first_mouse = True

        # Capture mouse cursor
        self.wnd.mouse_exclusivity = True
        self.wnd.cursor = False

        # Load shaders
        self.load_shaders()

        # Setup lights and shadow mapping
        self.setup_lights()

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
        
        # Main render shader with multi-light shadow mapping
        self.main_program = self.ctx.program(
            vertex_shader='''
                #version 410

                #define MAX_LIGHTS 2

                uniform mat4 projection;
                uniform mat4 view;
                uniform mat4 model;
                uniform mat4 light_matrices[MAX_LIGHTS];

                in vec3 in_position;
                in vec3 in_normal;

                out vec3 v_position;
                out vec3 v_normal;
                out vec4 v_light_space_pos[MAX_LIGHTS];

                void main() {
                    vec4 world_pos = model * vec4(in_position, 1.0);
                    v_position = world_pos.xyz;
                    v_normal = mat3(model) * in_normal;

                    // Transform to each light's space
                    for (int i = 0; i < MAX_LIGHTS; i++) {
                        v_light_space_pos[i] = light_matrices[i] * world_pos;
                    }

                    gl_Position = projection * view * world_pos;
                }
            ''',
            fragment_shader='''
                #version 410

                #define MAX_LIGHTS 2

                uniform vec3 light_positions[MAX_LIGHTS];
                uniform vec3 light_colors[MAX_LIGHTS];
                uniform float light_intensities[MAX_LIGHTS];
                uniform vec3 camera_pos;
                uniform vec3 object_color;
                uniform sampler2D shadow_maps[MAX_LIGHTS];

                in vec3 v_position;
                in vec3 v_normal;
                in vec4 v_light_space_pos[MAX_LIGHTS];

                out vec4 f_color;

                float calculate_shadow(int light_index, vec4 light_space_pos, sampler2D shadow_map) {
                    // Perspective divide
                    vec3 proj_coords = light_space_pos.xyz / light_space_pos.w;

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
                    vec3 view_dir = normalize(camera_pos - v_position);

                    // Ambient - only affected once, not per light
                    float ambient_strength = 0.2;
                    vec3 ambient = ambient_strength * object_color;

                    // Accumulate lighting from all lights
                    vec3 total_lighting = vec3(0.0);

                    for (int i = 0; i < MAX_LIGHTS; i++) {
                        vec3 light_dir = normalize(light_positions[i] - v_position);

                        // Diffuse
                        float diff = max(dot(normal, light_dir), 0.0);
                        vec3 diffuse = diff * object_color * light_colors[i];

                        // Specular
                        vec3 halfway_dir = normalize(light_dir + view_dir);
                        float spec = pow(max(dot(normal, halfway_dir), 0.0), 32.0);
                        vec3 specular = vec3(0.3) * spec * light_colors[i];

                        // Calculate shadow for this light
                        float shadow = calculate_shadow(i, v_light_space_pos[i], shadow_maps[i]);

                        // Add this light's contribution (attenuated by intensity and shadow)
                        total_lighting += light_intensities[i] * (1.0 - shadow) * (diffuse + specular);
                    }

                    // Combine ambient + all lights
                    vec3 final_color = ambient + total_lighting;

                    f_color = vec4(final_color, 1.0);
                }
            '''
        )
        
    def setup_lights(self):
        """Create multiple lights with shadow maps"""
        self.lights = []

        # Light 1: Rotating sun (white directional light)
        light1 = Light(
            position=Vector3([5.0, 10.0, 5.0]),
            target=Vector3([0.0, 0.0, 0.0]),
            color=Vector3([1.0, 1.0, 1.0]),
            intensity=1.0,
            light_type='directional'
        )

        # Light 2: Static side light (warm orange-red)
        light2 = Light(
            position=Vector3([8.0, 6.0, 8.0]),
            target=Vector3([0.0, 0.0, 0.0]),
            color=Vector3([1.0, 0.7, 0.5]),
            intensity=0.8,
            light_type='directional'
        )

        # Create shadow maps for each light
        for light in [light1, light2]:
            # Create depth texture
            light.shadow_map = self.ctx.depth_texture((self.SHADOW_SIZE, self.SHADOW_SIZE))
            light.shadow_map.compare_func = ''  # Disable comparison for sampling
            light.shadow_map.repeat_x = False
            light.shadow_map.repeat_y = False

            # Create framebuffer
            light.shadow_fbo = self.ctx.framebuffer(depth_attachment=light.shadow_map)

            self.lights.append(light)
        
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

        # Additional 15 cubes
        self.cube4 = geometry.cube(size=(1.2, 1.2, 1.2))
        self.cube4_pos = Vector3([-5.0, 0.6, -4.0])
        self.cube4_color = (0.9, 0.5, 0.2)  # Orange

        self.cube5 = geometry.cube(size=(0.8, 2.5, 0.8))
        self.cube5_pos = Vector3([6.0, 1.25, 3.0])
        self.cube5_color = (0.5, 0.2, 0.8)  # Purple

        self.cube6 = geometry.cube(size=(1.5, 1.0, 1.5))
        self.cube6_pos = Vector3([-2.0, 0.5, -6.0])
        self.cube6_color = (0.2, 0.8, 0.8)  # Cyan

        self.cube7 = geometry.cube(size=(1.0, 1.8, 1.0))
        self.cube7_pos = Vector3([4.5, 0.9, -5.0])
        self.cube7_color = (0.9, 0.3, 0.6)  # Pink

        self.cube8 = geometry.cube(size=(2.0, 0.8, 2.0))
        self.cube8_pos = Vector3([1.5, 0.4, 6.0])
        self.cube8_color = (0.6, 0.6, 0.2)  # Olive

        self.cube9 = geometry.cube(size=(1.3, 1.3, 1.3))
        self.cube9_pos = Vector3([-7.0, 0.65, 2.0])
        self.cube9_color = (0.3, 0.7, 0.4)  # Sea Green

        self.cube10 = geometry.cube(size=(0.9, 2.0, 0.9))
        self.cube10_pos = Vector3([2.5, 1.0, -3.0])
        self.cube10_color = (0.8, 0.6, 0.3)  # Gold

        self.cube11 = geometry.cube(size=(1.6, 1.2, 1.6))
        self.cube11_pos = Vector3([-4.0, 0.6, 5.0])
        self.cube11_color = (0.7, 0.3, 0.3)  # Maroon

        self.cube12 = geometry.cube(size=(1.1, 1.5, 1.1))
        self.cube12_pos = Vector3([7.5, 0.75, -2.0])
        self.cube12_color = (0.4, 0.5, 0.8)  # Steel Blue

        self.cube13 = geometry.cube(size=(0.7, 0.7, 0.7))
        self.cube13_pos = Vector3([-1.0, 0.35, 7.0])
        self.cube13_color = (0.9, 0.7, 0.5)  # Peach

        self.cube14 = geometry.cube(size=(1.4, 1.6, 1.4))
        self.cube14_pos = Vector3([5.5, 0.8, 1.0])
        self.cube14_color = (0.5, 0.3, 0.6)  # Plum

        self.cube15 = geometry.cube(size=(1.8, 1.0, 1.8))
        self.cube15_pos = Vector3([-6.0, 0.5, -1.5])
        self.cube15_color = (0.3, 0.6, 0.6)  # Teal

        self.cube16 = geometry.cube(size=(1.0, 2.2, 1.0))
        self.cube16_pos = Vector3([3.5, 1.1, 4.5])
        self.cube16_color = (0.8, 0.4, 0.2)  # Rust

        self.cube17 = geometry.cube(size=(1.2, 0.9, 1.2))
        self.cube17_pos = Vector3([-3.5, 0.45, -2.5])
        self.cube17_color = (0.5, 0.8, 0.3)  # Lime

        self.cube18 = geometry.cube(size=(0.8, 1.4, 0.8))
        self.cube18_pos = Vector3([8.0, 0.7, 4.0])
        self.cube18_color = (0.6, 0.4, 0.7)  # Lavender

        # Store all objects for easy iteration
        self.objects = [
            (self.ground, self.ground_pos, self.ground_color),
            (self.cube1, self.cube1_pos, self.cube1_color),
            (self.cube2, self.cube2_pos, self.cube2_color),
            (self.cube3, self.cube3_pos, self.cube3_color),
            (self.cube4, self.cube4_pos, self.cube4_color),
            (self.cube5, self.cube5_pos, self.cube5_color),
            (self.cube6, self.cube6_pos, self.cube6_color),
            (self.cube7, self.cube7_pos, self.cube7_color),
            (self.cube8, self.cube8_pos, self.cube8_color),
            (self.cube9, self.cube9_pos, self.cube9_color),
            (self.cube10, self.cube10_pos, self.cube10_color),
            (self.cube11, self.cube11_pos, self.cube11_color),
            (self.cube12, self.cube12_pos, self.cube12_color),
            (self.cube13, self.cube13_pos, self.cube13_color),
            (self.cube14, self.cube14_pos, self.cube14_color),
            (self.cube15, self.cube15_pos, self.cube15_color),
            (self.cube16, self.cube16_pos, self.cube16_color),
            (self.cube17, self.cube17_pos, self.cube17_color),
            (self.cube18, self.cube18_pos, self.cube18_color),
        ]

    def update_camera_vectors(self):
        """Update camera target based on yaw and pitch"""
        # Convert yaw and pitch to radians
        yaw_rad = np.radians(self.camera_yaw)
        pitch_rad = np.radians(self.camera_pitch)

        # Calculate the new front vector
        front = Vector3([
            np.cos(yaw_rad) * np.cos(pitch_rad),
            np.sin(pitch_rad),
            np.sin(yaw_rad) * np.cos(pitch_rad)
        ])

        # Normalize and set camera target
        front = vector.normalise(front)
        self.camera_target = self.camera_pos + front

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
        
    def render_scene(self, program):
        """Render all scene objects with given shader program"""
        for obj, pos, color in self.objects:
            # Model matrix (translation)
            model = Matrix44.from_translation(pos)

            # Set uniforms
            program['model'].write(model.astype('f4').tobytes())

            # Set color only for main render pass
            if program == self.main_program:
                program['object_color'].write(Vector3(color).astype('f4').tobytes())

            # Render
            obj.render(program)
    
    def on_update(self, time, frametime):
        """Update game logic (called each frame before rendering)"""
        self.time = time

        # Animate first light (rotating sun)
        angle = time * 0.5  # Rotate at 0.5 radians per second
        radius = 12.0  # Distance from center
        height = 10.0  # Height above ground
        self.lights[0].position.x = radius * np.cos(angle)
        self.lights[0].position.z = radius * np.sin(angle)
        self.lights[0].position.y = height
        # Light 2 stays static (already positioned in setup_lights)

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
                self.camera_pos += forward * movement
            if keys.S in self.keys_pressed:
                self.camera_pos -= forward * movement
            if keys.A in self.keys_pressed:
                self.camera_pos -= right * movement
            if keys.D in self.keys_pressed:
                self.camera_pos += right * movement
            if keys.Q in self.keys_pressed:
                self.camera_pos.y -= movement
            if keys.E in self.keys_pressed:
                self.camera_pos.y += movement

            # Update camera target again after position changes
            self.update_camera_vectors()

    def on_render(self, time, frametime):
        """Main render function called each frame"""
        # Update game logic first
        self.on_update(time, frametime)

        # Get camera matrices
        view = self.get_view_matrix()
        projection = self.get_projection_matrix()

        # ============ PASS 1: Render shadow maps for each light ============
        for i, light in enumerate(self.lights):
            # Use this light's framebuffer
            light.shadow_fbo.use()
            light.shadow_fbo.clear()
            self.ctx.viewport = (0, 0, self.SHADOW_SIZE, self.SHADOW_SIZE)

            # Get light matrix
            light_matrix = light.get_light_matrix()

            # Set shadow program uniforms
            self.shadow_program['light_matrix'].write(light_matrix.astype('f4').tobytes())

            # Render scene from this light's perspective
            self.render_scene(self.shadow_program)

        # ============ PASS 2: Render main scene ============
        self.ctx.screen.use()
        self.ctx.clear(0.1, 0.1, 0.15)  # Dark blue background
        self.ctx.viewport = self.wnd.viewport

        # Bind all shadow map textures
        for i, light in enumerate(self.lights):
            light.shadow_map.use(location=i)

        # Prepare light data arrays
        light_positions = np.array([light.position for light in self.lights], dtype='f4')
        light_colors = np.array([light.color for light in self.lights], dtype='f4')
        light_intensities = np.array([light.intensity for light in self.lights], dtype='f4')
        light_matrices = np.array([light.get_light_matrix() for light in self.lights], dtype='f4')

        # Set main program uniforms
        self.main_program['projection'].write(projection.astype('f4').tobytes())
        self.main_program['view'].write(view.astype('f4').tobytes())
        self.main_program['camera_pos'].write(self.camera_pos.astype('f4').tobytes())

        # Set light uniforms
        self.main_program['light_positions'].write(light_positions.tobytes())
        self.main_program['light_colors'].write(light_colors.tobytes())
        self.main_program['light_intensities'].write(light_intensities.tobytes())
        self.main_program['light_matrices'].write(light_matrices.tobytes())

        # Bind shadow map samplers (OpenGL requires array of ints for sampler arrays)
        shadow_map_locations = np.array([i for i in range(len(self.lights))], dtype='i4')
        self.main_program['shadow_maps'].write(shadow_map_locations.tobytes())

        # Render scene from camera's perspective
        self.render_scene(self.main_program)
        
    def on_mouse_position_event(self, _x: int, _y: int, dx: int, dy: int):
        """Handle mouse movement for FPS-style camera control"""
        if not self.mouse_captured:
            return

        # Handle first mouse movement to avoid jump
        if self.first_mouse:
            self.first_mouse = False
            return

        # Calculate mouse offset using delta values (dx, dy are mouse movement deltas)
        x_offset = dx * self.mouse_sensitivity
        y_offset = -dy * self.mouse_sensitivity  # Reversed since y-coordinates go from bottom to top

        # Update yaw and pitch
        self.camera_yaw += x_offset
        self.camera_pitch += y_offset

        # Constrain pitch to prevent camera flipping
        self.camera_pitch = max(-89.0, min(89.0, self.camera_pitch))

    def on_key_event(self, key, action, modifiers):
        """Handle keyboard input"""
        keys = self.wnd.keys

        # Toggle mouse capture with ESC
        if key == keys.ESCAPE and action == keys.ACTION_PRESS:
            self.mouse_captured = not self.mouse_captured
            self.wnd.mouse_exclusivity = self.mouse_captured
            self.wnd.cursor = not self.mouse_captured
            self.first_mouse = True
            return

        if action == keys.ACTION_PRESS:
            self.keys_pressed.add(key)
        elif action == keys.ACTION_RELEASE:
            self.keys_pressed.discard(key)


        # # Camera movement (WASD + QE for up/down)
        # if action == keys.ACTION_PRESS:
        #     direction = Vector3([0.0, 0.0, 0.0])

        #     # Calculate forward/right vectors
        #     forward = vector.normalise(self.camera_target - self.camera_pos)
        #     up = Vector3([0.0, 1.0, 0.0])
        #     right = vector.normalise(np.cross(forward, up))

        #     # Light movement (Arrow keys + ZX for up/down)
        #     if key == keys.UP:
        #         self.light_pos.z -= 1.0
        #     if key == keys.DOWN:
        #         self.light_pos.z += 1.0
        #     if key == keys.LEFT:
        #         self.light_pos.x -= 1.0
        #     if key == keys.RIGHT:
        #         self.light_pos.x += 1.0
        #     if key == keys.Z:
        #         self.light_pos.y -= 1.0
        #     if key == keys.X:
        #         self.light_pos.y += 1.0

    # def on_mouse_position_event(self, x, y, dx, dy):
    #     print("Mouse position:", x, y, dx, dy)


if __name__ == '__main__':
    Game.run()
