from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLUT import GLUT_BITMAP_HELVETICA_18
from OpenGL.GLUT import GLUT_BITMAP_9_BY_15
from OpenGL.GLU import *
from math import sin, cos, pi, radians
import random
import sys
import copy

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 700
CAR_WIDTH = 2.0
CAR_DEPTH = 4.0
ROAD_WIDTH = 60
ROAD_MIN_X = 20
ROAD_MAX_X = ROAD_MIN_X + ROAD_WIDTH
TREE_ZONE_LEFT = ROAD_MIN_X - 5
TREE_ZONE_RIGHT = ROAD_MAX_X + 5
COLLISION_MESSAGE_DURATION = 90
road_scroll_z = 0.0
MIN_SPEED_MULT = 0.5
MAX_SPEED_MULT = 3.0
SPEED_STEP = 0.15


TARGET_FPS = 60
FRAME_TIME = 1.0 / TARGET_FPS
last_time = 0.0

VIEW_FIRST_PERSON = 0
VIEW_THIRD_PERSON_ORBIT = 1
VIEW_THIRD_PERSON_FIXED = 2
currentViewMode = VIEW_THIRD_PERSON_ORBIT
camera_angle = 0.0          # rotation around car (radians)
camera_distance = 18.0      # zoom
camera_height = 8.0         # vertical offset
CAMERA_ROTATE_SPEED = 0.05
CAMERA_ZOOM_SPEED = 1.0
CAMERA_HEIGHT_SPEED = 0.5


fixedCameraHeight = 15.0
fixedCameraDistance = 20.0

car_position_x = (ROAD_MIN_X + ROAD_MAX_X) / 2
base_speed_multiplier = 1.0
acceleration_boost = 0.0
accelerate_key_down = False
lane_change_speed = 1.5

environment_scroll_speed = 0.9
points_speed = 0.55
diamond_speed = 0.60
obstacles_speed = 0.78

cheat_mode = False

trees_left_z = [i * 20 for i in range(6)]
trees_right_z = [i * 20 for i in range(6)]
lane_markers_z = [i * 15 for i in range(8)]

MAX_CAMERAS_PER_LEVEL = {
    1: [VIEW_FIRST_PERSON, VIEW_THIRD_PERSON_ORBIT, VIEW_THIRD_PERSON_FIXED],
    2: [VIEW_FIRST_PERSON, VIEW_THIRD_PERSON_ORBIT],
    3: [VIEW_FIRST_PERSON]
}


points = []
num_points = 15

def initialize_points():
    global points
    points = []
    for _ in range(num_points):
        points.append({
            'x': random.uniform(ROAD_MIN_X + 5, ROAD_MAX_X - 5),
            'y': 1,
            'z': random.uniform(-60, -30),
            'active': True
        })

diamond = {}
def initialize_diamond():
    global diamond
    diamond = {
        'x': random.uniform(ROAD_MIN_X + 10, ROAD_MAX_X - 10),
        'y': 1,
        'z': -70,
        'width': 1.5, 'height': 1.5, 'depth': 1.5,
        'active': True
    }

BASE_OBSTACLE_TYPES = {
    'rock':    {'width': 2.0, 'height': 2.0, 'depth': 2.0, 'penalty': 5,  'life_penalty': 1, 'color': (0.5, 0.5, 0.5)},
    'pothole': {'width': 3.0, 'height': 0.2, 'depth': 3.0, 'penalty': 10, 'life_penalty': 1, 'color': (0.36, 0.25, 0.20)},
    'barrier': {'width': 5.0, 'height': 2.5, 'depth': 1.5, 'penalty': 8,  'life_penalty': 2, 'color': (1.0, 0.5, 0.0)}
}
current_obstacle_types = copy.deepcopy(BASE_OBSTACLE_TYPES)

difficulty_level = 0

base_num_obstacles = 6
obstacle_increase_per_level = 1
obstacle_size_scale_per_level = 1.05
# base_speed_multiplier = 1.0 + difficulty_level * 0.15
obstacles = []
num_obstacles = base_num_obstacles
obstacle_initial_spacing = 40
possible_lanes = [ROAD_MIN_X + 10, (ROAD_MIN_X + ROAD_MAX_X)/2, ROAD_MAX_X - 10]
obstacle_reset_counter = 0

def update_difficulty_scaling():
    global current_obstacle_types, num_obstacles, base_speed_multiplier
    target_num = base_num_obstacles + difficulty_level * obstacle_increase_per_level
    num_obstacles = min(target_num, 20)
    scale_factor = obstacle_size_scale_per_level ** difficulty_level
    for name, base_info in BASE_OBSTACLE_TYPES.items():
        scaled_info = copy.deepcopy(base_info)
        scaled_info['width'] *= scale_factor
        scaled_info['height'] *= scale_factor
        current_obstacle_types[name] = scaled_info

def initialize_obstacles():
    global obstacles, obstacle_reset_counter
    obstacles = []
    obstacle_reset_counter = 0
    update_difficulty_scaling()
    for i in range(num_obstacles):
        obstacle_type_name = random.choice(list(current_obstacle_types.keys()))
        obstacle_info = current_obstacle_types[obstacle_type_name]
        z_pos = -40 - i * 25
        is_fake_obstacle = (obstacle_reset_counter % 3) < 2
        obstacle_reset_counter += 1
        obstacles.append({
            'x': random.choice(possible_lanes),
            'y': 0,
            'z': z_pos,
            'type': obstacle_type_name,
            'width': obstacle_info['width'],
            'height': obstacle_info['height'],
            'depth': obstacle_info['depth'],
            'penalty': obstacle_info['penalty'],
            'color': obstacle_info['color'],
            'is_fake': is_fake_obstacle,
            'active': True
        })

score = 0
MAX_LIVES = 5
lives = MAX_LIVES
game_paused = False
game_over = False
collision_message = ""
collision_message_timer = 0

class AABB:
    def __init__(self, center_x, center_y, center_z, width, height, depth):
        self.cx = center_x
        self.cy = center_y
        self.cz = center_z
        self.hw = width / 2.0
        self.hh = height / 2.0
        self.hd = depth / 2.0

    def collides_with(self, other):
        x_overlap = abs(self.cx - other.cx) * 2 < (self.hw * 2 + other.hw * 2)
        self_y_min = self.cy - self.hh
        self_y_max = self.cy + self.hh
        other_y_min = other.cy - other.hh
        other_y_max = other.cy + other.hh
        y_overlap = (self_y_max > other_y_min) and (self_y_min < other_y_max)
        z_overlap = abs(self.cz - other.cz) * 2 < (self.hd * 2 + other.hd * 2)
        return x_overlap and y_overlap and z_overlap

def render_text(x, y, z, text, r=1.0, g=1.0, b=1.0, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(r, g, b)
    if z is not None:
        glRasterPos3f(x, y, z)
    else:
        glWindowPos2f(x, y)
    for char in text:
        glutBitmapCharacter(font, ord(char))

def get_car_aabb():
    car_center_y = 0.6
    car_collision_height = 1.0
    return AABB(car_position_x, car_center_y, -5 + CAR_DEPTH / 2.0, CAR_WIDTH, car_collision_height, CAR_DEPTH)

def get_object_aabb(obj_dict):
    center_y = obj_dict['y'] + obj_dict['height'] / 2.0
    return AABB(obj_dict['x'], center_y, obj_dict['z'], obj_dict['width'], obj_dict['height'], obj_dict['depth'])

def get_point_aabb(point_dict):
    size = 0.6
    return AABB(point_dict['x'], point_dict['y'], point_dict['z'], size, size, size)

def setup_camera():
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    car_z = -5

    if currentViewMode == VIEW_FIRST_PERSON:
        # Camera on the car
        gluLookAt(
            car_position_x, 1.8, car_z + 1.0,     # eye
            car_position_x, 1.5, car_z - 20.0,    # look forward
            0, 1, 0
        )

    elif currentViewMode == VIEW_THIRD_PERSON_FIXED:
        # Camera behind & above the car (VERTICAL VIEW)
        gluLookAt(
            car_position_x, 12.0, car_z + 18.0,   # eye (behind)
            car_position_x, 1.0, car_z - 10.0,    # look forward
            0, 1, 0
        )

    else:  # VIEW_THIRD_PERSON_ORBIT → FREE ORBIT CAMERA
        cam_x = car_position_x + camera_distance * sin(camera_angle)
        cam_z = car_z + camera_distance * cos(camera_angle)

        gluLookAt(
            cam_x, camera_height, cam_z,   # camera position
            car_position_x, 1.0, car_z,    # look at the car
            0, 1, 0
        )



def draw_road():
    glColor3f(0.4, 0.4, 0.4)
    glBegin(GL_QUADS)
    road_length_segments = 40
    segment_length = 10
    for i in range(-road_length_segments // 2, road_length_segments // 2):
        z = i * segment_length - road_scroll_z
        glVertex3f(ROAD_MIN_X, 0, z)
        glVertex3f(ROAD_MAX_X, 0, z)
        glVertex3f(ROAD_MAX_X, 0, z + segment_length)
        glVertex3f(ROAD_MIN_X, 0, z + segment_length)
    glEnd()
    glColor3f(1.0, 1.0, 1.0)
    glLineWidth(2.0)
    glBegin(GL_LINES)
    mid_lane_x = (ROAD_MIN_X + ROAD_MAX_X) / 2
    dash_length = 4
    gap_length = 6
    pattern_length = dash_length + gap_length
    num_dashes_render = 20
    scroll_offset = (lane_markers_z[0] % pattern_length) if lane_markers_z else 0
    for i in range(num_dashes_render * 2):
        z_start = -num_dashes_render * pattern_length + i * pattern_length - scroll_offset
        z_end = z_start + dash_length
        if z_end < 10 and z_start > -200:
             glVertex3f(mid_lane_x, 0.05, z_start)
             glVertex3f(mid_lane_x, 0.05, z_end)
    glEnd()

def draw_car(x, y, z):
    glPushMatrix()
    glTranslatef(x, y + 0.15, z)

    # --- Car body ---
    glColor3f(0.9, 0.1, 0.1)
    glPushMatrix()
    glScalef(CAR_WIDTH, 0.6, CAR_DEPTH)
    glutSolidCube(1.0)
    glPopMatrix()

    # --- Cabin ---
    glColor3f(0.8, 0.8, 0.9)
    glPushMatrix()
    glTranslatef(0, 0.5, -0.3)
    glScalef(CAR_WIDTH * 0.6, 0.5, CAR_DEPTH * 0.4)
    glutSolidCube(1.0)
    glPopMatrix()

    # --- Wheels ---
    glColor3f(0.1, 0.1, 0.1)
    wheel_radius = 0.35
    wheel_width = 0.15

    wheel_positions = [
        (-CAR_WIDTH/2, 0.0, -CAR_DEPTH/2 + 0.6),
        ( CAR_WIDTH/2, 0.0, -CAR_DEPTH/2 + 0.6),
        (-CAR_WIDTH/2, 0.0,  CAR_DEPTH/2 - 0.6),
        ( CAR_WIDTH/2, 0.0,  CAR_DEPTH/2 - 0.6),
    ]

    for wx, wy, wz in wheel_positions:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glRotatef(90, 0, 1, 0)
        glutSolidTorus(wheel_width, wheel_radius, 8, 16)
        glPopMatrix()

    glPopMatrix()


def draw_tree(x, z):
    glPushMatrix()
    glTranslatef(x, 0.01, z)
    glColor3f(0.545, 0.271, 0.075)
    glPushMatrix()
    glRotatef(-90, 1, 0, 0)
    trunk_radius = 0.4
    trunk_height = 3.0
    quadric = gluNewQuadric()
    gluCylinder(quadric, trunk_radius, trunk_radius, trunk_height, 16, 1)
    gluDeleteQuadric(quadric)
    glPopMatrix()
    glColor3f(0.1, 0.6, 0.1)
    glTranslatef(0, trunk_height + 0.5, 0)
    glutSolidSphere(1.5, 16, 16)
    glPopMatrix()

def draw_point_object(point_dict):
    if not point_dict['active']: return
    glColor3f(1.0, 0.843, 0.0)
    glPushMatrix()
    glTranslatef(point_dict['x'], point_dict['y'], point_dict['z'])
    glutSolidSphere(0.4, 12, 12)
    glPopMatrix()

def draw_diamond_object(dia_dict):
    if not dia_dict['active']: return
    glColor3f(0.6, 1.0, 0.6)
    glPushMatrix()
    glTranslatef(dia_dict['x'], dia_dict['y'] + dia_dict['height']/2, dia_dict['z'])
    glRotatef(45, 0, 1, 0)
    glScalef(dia_dict['width'], dia_dict['height'], dia_dict['depth'])
    glutSolidOctahedron()
    glPopMatrix()

def draw_obstacle(obs_dict):
    if not obs_dict['active']: return
    if obs_dict['is_fake']:
        glColor4f(0.2, 0.8, 1.0, 0.5)   # 🔵 Fake → blue & transparent
    else:
        r, g, b = obs_dict['color']
        glColor4f(r, g, b, 1.0)        # 🔴 Real → solid

    glPushMatrix()
    glTranslatef(obs_dict['x'], obs_dict['y'], obs_dict['z'])
    otype = obs_dict['type']
    if otype == 'rock':
        glTranslatef(0, obs_dict['height'] / 2.0, 0)
        glutSolidSphere(obs_dict['width'] / 2.0, 16, 16)
    elif otype == 'pothole':
        glTranslatef(0, obs_dict['height'] / 2.0 - 0.05, 0)
        glRotatef(-90, 1, 0, 0)
        quadric = gluNewQuadric()
        gluCylinder(quadric, obs_dict['width']/2.0, obs_dict['width']/2.0, obs_dict['height'], 16, 1)
        gluDisk(quadric, 0, obs_dict['width']/2.0, 16, 1)
        glTranslatef(0, 0, obs_dict['height'])
        gluDisk(quadric, 0, obs_dict['width']/2.0, 16, 1)
        gluDeleteQuadric(quadric)
    elif otype == 'barrier':
        glTranslatef(0, obs_dict['height'] / 2.0, 0)
        glScalef(obs_dict['width'], obs_dict['height'], obs_dict['depth'])
        glutSolidCube(1.0)
    else:
        glTranslatef(0, obs_dict['height'] / 2.0, 0)
        glScalef(obs_dict['width'], obs_dict['height'], obs_dict['depth'])
        glutSolidCube(1.0)
    glPopMatrix()
    glColor4f(1.0, 1.0, 1.0, 1.0)

def draw_health_bar(current_lives, max_lives):
    bar_x, bar_y = 20, 55
    bar_max_width, bar_height = 100, 15
    padding = 2
    health_percentage = max(0.0, float(current_lives) / max_lives)
    current_width = bar_max_width * health_percentage
    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(bar_x - padding, bar_y - padding)
    glVertex2f(bar_x + bar_max_width + padding, bar_y - padding)
    glVertex2f(bar_x + bar_max_width + padding, bar_y + bar_height + padding)
    glVertex2f(bar_x - padding, bar_y + bar_height + padding)
    glEnd()
    glColor3f(0.0, 1.0, 0.0)
    glBegin(GL_QUADS)
    glVertex2f(bar_x, bar_y)
    glVertex2f(bar_x + current_width, bar_y)
    glVertex2f(bar_x + current_width, bar_y + bar_height)
    glVertex2f(bar_x, bar_y + bar_height)
    glEnd()

def display():
    global score, lives, game_over, game_paused, collision_message, collision_message_timer, difficulty_level
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    setup_camera()
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    draw_road()
    for z in trees_left_z:
        draw_tree(ROAD_MIN_X - 6, z)
        draw_tree(ROAD_MAX_X + 6, z)

    # for z in trees_right_z: draw_tree(TREE_ZONE_RIGHT, z)
    for point in points: draw_point_object(point)
    draw_diamond_object(diamond)
    for obstacle in obstacles: draw_obstacle(obstacle)
    draw_car(car_position_x, 0.0, -5)
    glDisable(GL_BLEND)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    render_text(20, WINDOW_HEIGHT - 30, None, f"Score: {score}", 1.0, 1.0, 0.0)
    render_text(20, 30, None, f"Lives: {lives}", 1.0, 1.0, 1.0)
    draw_health_bar(lives, MAX_LIVES)
    render_text(20, WINDOW_HEIGHT - 50, None, f"Level: {difficulty_level + 1}", 0.8, 0.8, 1.0)
    if collision_message_timer > 0:
        render_text(20, WINDOW_HEIGHT - 75, None, collision_message, 1.0, 0.2, 0.2)
    # penalty_ui_x = WINDOW_WIDTH - 230
    # penalty_ui_y = WINDOW_HEIGHT - 30
    # line_height = 18
    # penalty_font = GLUT_BITMAP_9_BY_15
    # render_text(penalty_ui_x, penalty_ui_y, None, "Base Penalties:", 1.0, 1.0, 1.0, font=penalty_font)
    # penalty_ui_y -= line_height + 5
    # max_name_len = max(len(name) for name in BASE_OBSTACLE_TYPES.keys()) if BASE_OBSTACLE_TYPES else 0
    # for name, info in BASE_OBSTACLE_TYPES.items():
    #      life_pen = info.get('life_penalty', 1)
    #      life_text = f"{life_pen} {'Life' if life_pen == 1 else 'Lives'}"
    #      penalty_text = f" - {name.capitalize().ljust(max_name_len + 2)}: -{info['penalty']} Score, -{life_text}"
    #      render_text(penalty_ui_x, penalty_ui_y, None, penalty_text, 1.0, 1.0, 1.0, font=penalty_font)
    #      penalty_ui_y -= line_height
    if game_over:
        render_text(WINDOW_WIDTH / 2 - 50, WINDOW_HEIGHT / 2 + 10, None, "GAME OVER", 1.0, 0.0, 0.0)
        render_text(WINDOW_WIDTH / 2 - 60, WINDOW_HEIGHT / 2 - 10, None, f"Final Score: {score}", 1.0, 1.0, 1.0)
        render_text(WINDOW_WIDTH / 2 - 100, WINDOW_HEIGHT / 2 - 30, None, "Right-Click to RESTART", 0.8, 0.8, 0.8)
    elif game_paused:
        render_text(WINDOW_WIDTH / 2 - 40, WINDOW_HEIGHT / 2, None, "PAUSED", 1.0, 1.0, 1.0)
        render_text(WINDOW_WIDTH / 2 - 90, WINDOW_HEIGHT / 2 - 20, None, "Left-Click or 'P' to Resume", 0.8, 0.8, 0.8)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glutSwapBuffers()

def animation(value):
    global road_scroll_z
    global score, lives, game_over, game_paused, difficulty_level, base_speed_multiplier
    global car_position_x
    global trees_left_z, trees_right_z, lane_markers_z
    global points, diamond, obstacles, obstacle_reset_counter
    global acceleration_boost
    global collision_message, collision_message_timer
    global currentViewMode   # 🔥 THIS IS THE FIX


    if collision_message_timer > 0:
        collision_message_timer -= 1
        if collision_message_timer == 0:
             collision_message = ""
    if game_paused or game_over:
        glutTimerFunc(16, animation, 0)
        glutPostRedisplay()
        return
    # ----- Difficulty & Level Progression -----
    if score >= 50:
        new_difficulty_level = 2
    elif score >= 20:
        new_difficulty_level = 1
    else:
        new_difficulty_level = 0

    if new_difficulty_level > difficulty_level:
        difficulty_level = new_difficulty_level

        # Increase speed per level
        base_speed_multiplier = 1.0 + difficulty_level * 0.15

        # Scale obstacles
        update_difficulty_scaling()

        print(f"Level Up! Reached Level {difficulty_level + 1}")
        print(f"Speed multiplier: {base_speed_multiplier}")
    
    import time
    global last_time

    now = time.time()
    dt = now - last_time
    if dt < FRAME_TIME:
        return
    last_time = now

    current_speed_mult = base_speed_multiplier + acceleration_boost

    scroll_delta = environment_scroll_speed * current_speed_mult * dt * 60
    scroll_delta_points = points_speed * current_speed_mult * dt * 60
    scroll_delta_diamond = diamond_speed * current_speed_mult * dt * 60
    scroll_delta_obstacles = obstacles_speed * current_speed_mult * dt * 60


    # MOVE THE WORLD
    road_scroll_z += scroll_delta
    if road_scroll_z > 10:
        road_scroll_z = 0

    allowed = MAX_CAMERAS_PER_LEVEL.get(difficulty_level + 1, [VIEW_FIRST_PERSON])
    if currentViewMode not in allowed:
        currentViewMode = VIEW_FIRST_PERSON

    current_speed_mult = base_speed_multiplier + acceleration_boost
    scroll_delta = environment_scroll_speed * current_speed_mult
    scroll_delta_points = points_speed * current_speed_mult
    scroll_delta_diamond = diamond_speed * current_speed_mult
    scroll_delta_obstacles = obstacles_speed * current_speed_mult
    trees_left_z = [(z + scroll_delta) % 120 - 20 for z in trees_left_z]
    trees_right_z = [(z + scroll_delta) % 120 - 20 for z in trees_right_z]
    lane_markers_z = [(z + scroll_delta) for z in lane_markers_z]
    if lane_markers_z and lane_markers_z[0] > 50:
        lane_markers_z = [z - 120 for z in lane_markers_z]
    for point in points:
        point['z'] += scroll_delta_points
        if point['z'] > 10:
            point['z'] = random.uniform(-150, -100)
            point['x'] = random.uniform(ROAD_MIN_X + 5, ROAD_MAX_X - 5)
            point['active'] = True
    diamond['z'] += scroll_delta_diamond
    if diamond['z'] > 10:
        diamond['z'] = random.uniform(-200, -150)
        diamond['x'] = random.uniform(ROAD_MIN_X + 10, ROAD_MAX_X - 10)
        diamond['active'] = True
    active_obstacle_zs = [obs['z'] for obs in obstacles if obs['active']]
    farthest_active_z = min(active_obstacle_zs) if active_obstacle_zs else -80
    current_active_obstacles = sum(1 for obs in obstacles if obs['active'])
    for i, obstacle in enumerate(obstacles):
        needs_reset = False
        if obstacle['active']:
            obstacle['z'] += scroll_delta_obstacles
            if obstacle['z'] > 10:
                obstacle['active'] = False
                needs_reset = True
        elif not obstacle['active'] and obstacle['z'] < -400:
             needs_reset = True
        should_activate_more = current_active_obstacles < num_obstacles
        if needs_reset or (not obstacle['active'] and should_activate_more):
            other_active_zs = [obs['z'] for idx, obs in enumerate(obstacles) if obs['active'] and idx != i]
            current_farthest_z = min(other_active_zs) if other_active_zs else farthest_active_z
            reset_z = current_farthest_z - random.uniform(30, 60)
            obstacle['z'] = max(reset_z, -350)
            obstacle['x'] = random.choice(possible_lanes)
            new_type_name = random.choice(list(current_obstacle_types.keys()))
            new_info = current_obstacle_types[new_type_name]
            obstacle['type'] = new_type_name
            obstacle['width'] = new_info['width']
            obstacle['height'] = new_info['height']
            obstacle['depth'] = new_info['depth']
            obstacle['penalty'] = new_info['penalty']
            obstacle['color'] = new_info['color']
            obstacle['is_fake'] = (obstacle_reset_counter % 3) < 2
            obstacle_reset_counter += 1
            obstacle['active'] = True
            if needs_reset:
                pass
            elif should_activate_more:
                 current_active_obstacles += 1
    car_aabb = get_car_aabb()
    for point in points:
        if point['active']:
            point_aabb = get_point_aabb(point)
            if car_aabb.collides_with(point_aabb):
                point['active'] = False
                score += 1
                point['z'] = random.uniform(-150, -100)
                point['x'] = random.uniform(ROAD_MIN_X + 5, ROAD_MAX_X - 5)
    if diamond['active']:
        diamond_aabb = get_object_aabb(diamond)
        if car_aabb.collides_with(diamond_aabb):
            diamond['active'] = False
            if lives < MAX_LIVES:
                lives += 1
            diamond['z'] = random.uniform(-200, -150)
            diamond['x'] = random.uniform(ROAD_MIN_X + 10, ROAD_MAX_X - 10)
    for obstacle in obstacles:
        if not obstacle['active']:
            continue

        obstacle_aabb = get_object_aabb(obstacle)

        # --- Collision ---
        if car_aabb.collides_with(obstacle_aabb):
            if not obstacle['is_fake']:
                score_penalty = obstacle['penalty']
                life_penalty_value = BASE_OBSTACLE_TYPES[obstacle['type']].get('life_penalty', 1)
                score = max(0, score - score_penalty)
                lives -= life_penalty_value
                collision_message = f"Hit! -{score_penalty} Score, -{life_penalty_value} Life"
                collision_message_timer = COLLISION_MESSAGE_DURATION

                if lives <= 0:
                    lives = 0
                    game_over = True

            obstacle['active'] = False
            obstacle['z'] = -500
            continue

        # --- Passed safely ---
        if obstacle['z'] > -3 and not obstacle['is_fake']:
            obstacle['active'] = False
            score += 1

    if cheat_mode:
        SAFE_DISTANCE = 20  # look ahead
        nearest_obstacle = None
        nearest_z = -9999

        for obstacle in obstacles:
            if not obstacle['active'] or obstacle['is_fake']:
                continue

            # Only consider obstacles in front of the car
            if -SAFE_DISTANCE < obstacle['z'] < 0:
                if obstacle['z'] > nearest_z:
                    nearest_z = obstacle['z']
                    nearest_obstacle = obstacle

        if nearest_obstacle:
            # Choose safest lane
            safe_lanes = [lane for lane in possible_lanes if lane != nearest_obstacle['x']]
            target_x = min(safe_lanes, key=lambda l: abs(l - car_position_x))

            # Smooth movement
            if abs(target_x - car_position_x) > 0.1:
                direction = 1 if target_x > car_position_x else -1
                car_position_x += direction * lane_change_speed * 0.5

        # 🚧 HARD CLAMP: never leave road
        car_position_x = max(
            ROAD_MIN_X + CAR_WIDTH / 2,
            min(ROAD_MAX_X - CAR_WIDTH / 2, car_position_x)
        )


    # clamp car to road (VERY IMPORTANT)
    car_position_x = max(
        ROAD_MIN_X + CAR_WIDTH / 2,
        min(ROAD_MAX_X - CAR_WIDTH / 2, car_position_x)
    )

    glutPostRedisplay()
    glutTimerFunc(16, animation, 0)

def keyboard_action(key, x, y):
    global game_paused, currentViewMode, cheat_mode
    global base_speed_multiplier   # ✅ REQUIRED

    try:
        key_char = key.decode("utf-8").lower()
    except UnicodeDecodeError:
        return

    if game_over:
        return

    if key_char == 'p':
        game_paused = not game_paused

    elif key_char == 'v':
        if not game_paused:
            allowed = MAX_CAMERAS_PER_LEVEL.get(difficulty_level + 1, [VIEW_FIRST_PERSON])
            idx = allowed.index(currentViewMode) if currentViewMode in allowed else 0
            currentViewMode = allowed[(idx + 1) % len(allowed)]

    elif key_char == 'w':
        if not game_paused:
            base_speed_multiplier = min(
                base_speed_multiplier + SPEED_STEP,
                MAX_SPEED_MULT
            )

    elif key_char == 's':
        if not game_paused:
            base_speed_multiplier = max(
                base_speed_multiplier - SPEED_STEP,
                MIN_SPEED_MULT
            )

    elif key_char == 'c':
        cheat_mode = not cheat_mode

    glutPostRedisplay()

def keyboard_up_action(key, x, y):
    global accelerate_key_down, acceleration_boost
    try: key_char = key.decode("utf-8").lower()
    except UnicodeDecodeError: key_char = ''
    if key_char == 'w':
        accelerate_key_down = False
        acceleration_boost = 0.0

def special_key_action(key, x, y):
    global car_position_x, cameraAngle, cameraRadius, cameraHeight, currentViewMode
    if game_paused or game_over: return
    move_distance = lane_change_speed * (1.2 if accelerate_key_down else 1.0)
    if key == GLUT_KEY_LEFT:
        car_position_x = max(ROAD_MIN_X + CAR_WIDTH / 2 + 0.5, car_position_x - move_distance)
    elif key == GLUT_KEY_RIGHT:
        car_position_x = min(ROAD_MAX_X - CAR_WIDTH / 2 - 0.5, car_position_x + move_distance)
    # if currentViewMode == VIEW_THIRD_PERSON_ORBIT:
    #     if key == GLUT_KEY_UP: cameraHeight += 0.5
    #     elif key == GLUT_KEY_DOWN: cameraHeight = max(1.0, cameraHeight - 0.5)
    glutPostRedisplay()

def reset_game():
    global score, lives, game_over, game_paused, difficulty_level
    global car_position_x, base_speed_multiplier, acceleration_boost, accelerate_key_down
    global points, diamond, obstacles, obstacle_reset_counter
    global collision_message, collision_message_timer
    global road_scroll_z, lane_markers_z, trees_left_z, trees_right_z, last_time
    global cheat_mode, currentViewMode

    print("Resetting game...")

    # --- Reset world motion ---
    road_scroll_z = 0.0
    lane_markers_z = [i * 15 for i in range(8)]
    trees_left_z = [i * 20 for i in range(6)]
    trees_right_z = [i * 20 for i in range(6)]
    last_time = 0.0

    # --- Reset game state ---
    score = 0
    lives = MAX_LIVES
    game_over = False
    game_paused = False
    difficulty_level = 0

    # --- Reset player ---
    car_position_x = (ROAD_MIN_X + ROAD_MAX_X) / 2
    base_speed_multiplier = 1.0
    acceleration_boost = 0.0
    accelerate_key_down = False

    # --- Reset modes ---
    cheat_mode = False
    currentViewMode = VIEW_THIRD_PERSON_ORBIT

    # --- UI / messages ---
    collision_message = ""
    collision_message_timer = 0

    # --- Reset obstacles & collectibles ---
    obstacle_reset_counter = 0
    initialize_points()
    initialize_diamond()
    initialize_obstacles()

    print("Game Reset!")
    glutPostRedisplay()

def mouse_action(button, state, x, y):
    global game_paused, game_over
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        if not game_over:
            game_paused = not game_paused
    elif button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        if game_over:
            reset_game()

def init_gl():
    glClearColor(0.5, 0.7, 1.0, 1.0)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    light_ambient = [0.3, 0.3, 0.3, 1.0]
    light_diffuse = [0.8, 0.8, 0.8, 1.0]
    light_specular = [0.5, 0.5, 0.5, 1.0]
    light_position = [50.0, 50.0, 50.0, 1.0]
    glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
    glLightfv(GL_LIGHT0, GL_SPECULAR, light_specular)
    glLightfv(GL_LIGHT0, GL_POSITION, light_position)
    glEnable(GL_NORMALIZE)

def reshape(w, h):
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    aspect_ratio = w / h if h > 0 else 1
    gluPerspective(60.0, aspect_ratio, 1.0, 500.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Simple 3D Driving Game - Enhanced")
    init_gl()
    reset_game()
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard_action)
    glutKeyboardUpFunc(keyboard_up_action)
    glutSpecialFunc(special_key_action)
    glutMouseFunc(mouse_action)
    glutIdleFunc(lambda: animation(0))
    print("\n================ GAME CONTROLS ================")
    print("Steering:")
    print("  ← / →        : Move car left / right")

    print("\nSpeed Control:")
    print("  W            : Increase speed")
    print("  S            : Decrease speed")

    print("\nCamera:")
    print("  V            : Switch camera view")
    print("  (Orbit View Only)")
    print("    A / D      : Rotate camera around car")
    print("    W / S      : Zoom in / out")
    print("    Q / E      : Move camera up / down")

    print("\nGameplay:")
    print("  C            : Toggle CHEAT MODE (auto-avoid obstacles)")
    print("  P / Left Click : Pause / Resume")
    print("  Right Click  : Restart (after Game Over)")

    print("\n================ GAME RULES ===================")
    print("  - Avoid REAL obstacles:")
    print("      • Rocks")
    print("      • Potholes")
    print("      • Barriers (cost 2 lives)")
    print("  - FAKE obstacles are semi-transparent and harmless")
    print("  - Collect GOLD spheres to gain score")
    print("  - Collect GREEN diamonds to gain extra lives")
    print("  - Game ends when all lives are lost")
    print("  - Difficulty increases with score (speed & obstacles)")
    print("================================================\n")

    glutMainLoop()

if __name__ == "__main__":
    main()
