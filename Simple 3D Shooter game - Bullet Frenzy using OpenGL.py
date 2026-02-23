
# =============================================================
# Assignment 3 : Bullet Frenzy (3D OpenGL)
# Student Name : Asiful Kanzan Auishik
# ID           : 19101628
#
# This program implements a 3D shooting game using PyOpenGL.
# All animation is handled using the GLUT idle loop.
# No glutTimerFunc or extra OpenGL utilities are used.
#
# Core Features:
# - Player movement and gun rotation
# - Orbit and first-person camera modes
# - Bullet firing and collision detection
# - Enemy chasing and pulsing animation
# - Cheat mode with auto-rotation and auto-fire
# - Game over, restart, and HUD feedback
# =============================================================

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

# import time
import math
import random


#flags

is_game_running = True
bullet_hit_flag = False
is_cheat_mode = False
is_first_person = False
auto_shoot_enabled = True
end = False

#arrays
enemies = [] #to store 5 enemies
bullets = [] 

#globals
player_yaw_deg = 270 #player player_yaw_deg 

camera_yaw_deg = 90
camera_radius = 500
camera_height = 420

fovY = 122
TILE_SIZE = 90
ENEMY_COUNT  = 5
player_lives  = 5
missed_bullets = 0
score = 0
player_x ,player_y = 0, 0 #player x and y position

NUM_TILES = 13
BOARD_SIZE = TILE_SIZE * NUM_TILES
HALF_BOARD = BOARD_SIZE // 2    
ENEMY_SPAWN_MARGIN = 55 # keep enemies a bit inside the wall


#draw text in is_game_running
def draw_text(x, y, text, font):
    p,q = x,y
    glColor3f(.9,.9,1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(p,q)
    for i in text:
        glutBitmapCharacter(font, ord(i))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


#grid floor drawing 13x13
def draw_checkerboard():
    global TILE_SIZE
    half = (13 * TILE_SIZE) // 2

    for r in range(13):
        for j in range(13):
            x1 = -half + j * TILE_SIZE
            y1 = -half + r * TILE_SIZE
            x2 = x1 + TILE_SIZE
            y2 = y1 + TILE_SIZE

            glBegin(GL_QUADS)
            if (r + j) % 2 == 0:
                glColor3f(1, 1, 1) # white
            else:
                glColor3f(0.7, 0.5, 0.95) # purple
            glVertex3f(x1, y1, 0)
            glVertex3f(x2, y1, 0)
            glVertex3f(x2, y2, 0)
            glVertex3f(x1, y2, 0)
            glEnd()



def draw_walls():
    ht = TILE_SIZE * 1.5
    glBegin(GL_QUADS)
    # Left wall
    glColor3f(0, 1, 0)
    glVertex3f(-HALF_BOARD, -HALF_BOARD, 0)
    glVertex3f(-HALF_BOARD,  HALF_BOARD, 0)
    glVertex3f(-HALF_BOARD,  HALF_BOARD, ht)
    glVertex3f(-HALF_BOARD, -HALF_BOARD, ht)
    # Right wall
    glColor3f(0, 0, 1)
    glVertex3f( HALF_BOARD, -HALF_BOARD, 0)
    glVertex3f( HALF_BOARD,  HALF_BOARD, 0)
    glVertex3f( HALF_BOARD,  HALF_BOARD, ht)
    glVertex3f( HALF_BOARD, -HALF_BOARD, ht)
    # Bottom wall
    glColor3f(0, 1, 1)
    glVertex3f(-HALF_BOARD, -HALF_BOARD, 0)
    glVertex3f( HALF_BOARD, -HALF_BOARD, 0)
    glVertex3f( HALF_BOARD, -HALF_BOARD, ht)
    glVertex3f(-HALF_BOARD, -HALF_BOARD, ht)
    # Top wall
    glColor3f(1, 1, 1)
    glVertex3f(-HALF_BOARD,  HALF_BOARD, 0)
    glVertex3f( HALF_BOARD,  HALF_BOARD, 0)
    glVertex3f( HALF_BOARD,  HALF_BOARD, ht)
    glVertex3f(-HALF_BOARD,  HALF_BOARD, ht)
    glEnd()


def draw_player():
    global player_x,player_y,is_game_running,player_yaw_deg,bullet_hit_flag,player_lives

    #player_model
    glPushMatrix()
    glTranslatef(player_x,player_y,0)
    glRotatef(player_yaw_deg, 0, 0, 1)  
    if is_game_running==False :
        glRotatef(90,0,1,0) #laying down the player in floor

    #leg
    glColor3f(0, 0, 1)
    glTranslatef(0,-15,-90)
    glRotatef(180, 0, 1, 0)
    gluCylinder(gluNewQuadric(), 15, 7, 80, 10, 10) #quadric, base radius, top radius, height, slices, stacks
    glColor3f(0, 0, 1)
    glTranslatef(0,-75,0)
    gluCylinder(gluNewQuadric(), 15, 7, 80, 10, 10) 

    #body
    glColor3f(0.4, 0.5, 0)
    glTranslatef(0, 35, -10)
    glutSolidCube(70)

    #gun
    glColor3f(0.5, 0.5, 0.5)
    glTranslatef(0, 0, 15)
    glTranslatef(30, 0, -40) 
    glRotatef(90, 0, 1, 0)
    gluCylinder(gluNewQuadric(), 15, 3, 100, 10, 10) 
  

    #hand
    glColor3f(1, 0.7, 0.6)
    glTranslatef(0, -25, 0)
    gluCylinder(gluNewQuadric(), 12, 5, 50, 10, 10) 

    glColor3f(1, 0.7, 0.6)
    glTranslatef(0, 50, 0)
    gluCylinder(gluNewQuadric(), 12, 5, 50, 10, 10) 

    # head
    glColor3f(0, 0, 0)
    glTranslatef(40,-25, -18)
    gluSphere(gluNewQuadric(), 28, 10, 10)

    glPopMatrix()

#ememies maker
def draw_enemy(e):
    x,y,s = e[0],e[1],e[3]
    glPushMatrix()
    glTranslatef(x, y, 0)
    glScalef(s, s, s)
    
    glColor3f(1, 0, 0)
    glTranslatef(0, 0, 40)
    gluSphere(gluNewQuadric(), 40, 21, 21)

    glColor3f(0,0,0)
    glTranslatef(0, 0, 45)
    gluSphere(gluNewQuadric(), 19, 11, 11)
    glPopMatrix()

def spawn_enemy(): #enemies spawn
    y = (HALF_BOARD - ENEMY_SPAWN_MARGIN)
    while True:
        x = random.randint(-(HALF_BOARD - ENEMY_SPAWN_MARGIN), (HALF_BOARD - ENEMY_SPAWN_MARGIN))
        if abs(x) > 150 or abs(y) > 150:
            break
    return [x, y, 0, 1.1, .003]

#assigning x and y pos of five enemies
for i in range(ENEMY_COUNT):
    enemies.append(spawn_enemy())

#bullets
def draw_bullets():
    global bullets,is_cheat_mode
    glColor3f(1, 0, 0)
    for i in bullets:
        x,y,z = i[0],i[1],i[2]
        glPushMatrix()
        glTranslatef(x,y,z)
        if is_cheat_mode:
            glutSolidCube(8)
        else:
            glutSolidCube(15)

        glPopMatrix()

#brush fire
def update_bullets():
    global bullets, is_game_running, missed_bullets, player_lives, enemies, is_cheat_mode, bullet_hit_flag,score
    for shot in bullets:
            shot[0] += shot[3] * 15
            shot[1] += shot[4] * 15

    k = 0
    while k < len(bullets):
        if abs(bullets[k][0]) >= HALF_BOARD or abs(bullets[k][1]) >= HALF_BOARD:
            bullets.pop(k)
            if  not is_cheat_mode and not bullet_hit_flag and missed_bullets<=10:
                missed_bullets += 1
                print(f'Missed fire : {missed_bullets}')
              # Increment missed bullets count
        else:
            k += 1
    
    if missed_bullets >= 10 or player_lives == 0:
            is_game_running = False
            enemies.clear()


#enemies attack
#animate the hero
def update_enemies():
    global  missed_bullets, score, player_lives, is_game_running, player_x, player_y,enemies,end

    for i in enemies:
        dx = player_x - i[0]
        dy = player_y - i[1]
        distance = (dx**2 + dy**2)**.5

        if distance > 1:
            i[0] += (dx / distance) * 0.05
            i[1] += (dy / distance) * 0.05

        i[3] += i[4]
        if i[3] >= 1.4 :
            i[4] = -i[4]
        elif i[3] <= 0.6:
            i[4] = -i[4]

    if is_game_running==True:
        for e in enemies:
            x,y,z = player_x - e[0],player_y - e[1],0-e[2]
            if abs(x) < 50 and abs(y) < 50 and abs(z)<50:
                if player_lives > 0:
                    player_lives -= 1
                    print(f'Remainig life : {player_lives}')
                    enemies.remove(e)
                    enemies.append(spawn_enemy())
                    if player_lives<=0:
                        enemies.clear()
                        is_game_running = False
                        

                        break
      
    glutPostRedisplay()

#to deploy cheat mode
def update_cheat_mode():
    global is_first_person,is_game_running,player_yaw_deg,player_x,player_y,bullets,score,bullet_hit_flag

    if is_cheat_mode==True and is_game_running!=False:
            player_yaw_deg+=0.7
            player_yaw_deg%= 360
            angle_rad = math.radians(player_yaw_deg)
            x_dir = -math.cos(angle_rad)
            y_dir = -math.sin(angle_rad)
            bx = player_x + 50 * math.sin(angle_rad) + x_dir * 140
            by = player_y - 50 * math.cos(angle_rad) + y_dir * 140 
            bz = 10
            # bullets.append([bx, by, bz, x_dir, y_dir, 0])

            for j in enemies[:]:
                distn = ((j[0] - bx)**2 + (j[1] - by)**2)**.5
                if distn == 0:
                    continue
                dt = x_dir * (j[0] - bx) / distn + y_dir * (j[1] - by) / distn


                if dt > 0.99 and distn <= 450 :
                    dx, dy, dz = j[0] - bx, j[1] - by, j[2] - bz
                    len = (dx**2 + dy**2 + dz**2)**.5
                    if len == 0:
                        continue

                    x,y,z = (dx / len, dy / len, dz / len)
                    temp = [bx, by, bz, x, y, z]
                    bullets.append(temp)

                    score += 1
                    print(f'Bullet fired')
                    enemies.remove(j)
                    
                    enemies.append(spawn_enemy())
                    break
    glutPostRedisplay()


def handle_bullet_enemy_hits():
    global bullets, score, enemies, player_lives, is_game_running

    bulremove = []
    new = []

    for i in enemies:
        fired = False
        for j in bullets:
            x = j[0] - i[0]
            y = j[1] - i[1]
            z = j[2] - i[2]

            if abs(x) < 35 and abs(y) < 35 and abs(z) < 35:
                fired = True
                score += 1
                print('Bullet fired')
                bulremove.append(j)
                break

        if fired:
            new.append(spawn_enemy())
        else:
            new.append(i)

    for t in bulremove:
        if t in bullets:
            bullets.remove(t)

    enemies[:] = new

#is_game_running controller buttons
def on_keyboard(key, x, y):
    global player_x,player_y,player_yaw_deg,is_first_person,is_cheat_mode,is_game_running,auto_shoot_enabled,ENEMY_COUNT,bullet_hit_flag,score,missed_bullets,player_lives
    speed= 5
    
    if key == b'w' and is_game_running:
        i = player_x-math.cos(math.radians(player_yaw_deg)) * speed
        j = player_y- math.sin(math.radians(player_yaw_deg)) * speed
        if -HALF_BOARD <= i <= HALF_BOARD and -HALF_BOARD <= j <= HALF_BOARD:

            player_x = i
            player_y = j
        
    elif key == b's' and is_game_running:
        i = player_x+math.cos(math.radians(player_yaw_deg)) * speed
        j = player_y+ math.sin(math.radians(player_yaw_deg)) * speed
        if -HALF_BOARD <= i <= HALF_BOARD and -HALF_BOARD <= j <= HALF_BOARD:

             player_x = i
             player_y = j
            
    elif key == b'a' and is_game_running:
        player_yaw_deg+=5

    elif key == b'd' and is_game_running:
        player_yaw_deg-=5

    elif key == b'v' and is_cheat_mode and is_game_running:
        is_first_person = not is_first_person

    elif key == b"c" and is_game_running: #cheat mode
        is_cheat_mode = not is_cheat_mode
        if is_cheat_mode :
            update_cheat_mode()     
        else:
            bullets.clear()
            glutPostRedisplay()

        
    elif key == b'r' and is_game_running==False: #restart
        bullets.clear()
        enemies.clear()
        for i in range(ENEMY_COUNT):
            new = spawn_enemy()
            enemies.append(new)

        score = 0
        missed_bullets = 0
        player_lives = 5
        is_game_running = True
        player_yaw_deg = 0
        print("Game restarted!")
        bullet_hit_flag = False
        glutPostRedisplay()
    
    glutPostRedisplay()


def on_special_keys(key, x, y):
    global camera_yaw_deg, camera_height
    if key == GLUT_KEY_LEFT:  camera_yaw_deg += 2
    elif key == GLUT_KEY_RIGHT: camera_yaw_deg -= 2
    elif key == GLUT_KEY_UP:    camera_height += 10
    elif key == GLUT_KEY_DOWN:  camera_height -= 10
    glutPostRedisplay()


def on_mouse(button, state, x, y):
    global is_first_person,is_game_running,player_yaw_deg,player_x,player_y,bullets
    if is_game_running==True:
        if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
            angle_rad = math.radians(player_yaw_deg)
            x_dir = -math.cos(angle_rad)
            y_dir = -math.sin(angle_rad)
            bx = player_x + 50 * math.sin(angle_rad) + x_dir * 140
            by = player_y - 50 * math.cos(angle_rad) + y_dir * 140 
            bz = 10
            bullets.append([bx, by, bz, x_dir, y_dir, 0])

    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN :
        if is_game_running:
            is_first_person = not is_first_person
        glutPostRedisplay()

def setup_camera():
    glMatrixMode(GL_PROJECTION)  
    glLoadIdentity()  
    gluPerspective(fovY, 1.25, 0.1, 1500) 
    glMatrixMode(GL_MODELVIEW) 
    glLoadIdentity() 
    global is_first_person, player_x, player_y, player_yaw_deg

    if is_first_person:
        n_x = player_x - math.cos(math.radians(player_yaw_deg)) * 25
        n_y = player_y - math.sin(math.radians(player_yaw_deg)) * 25
        n_z = 40
        x = player_x - math.cos(math.radians(player_yaw_deg)) * 90
        y = player_y - math.sin(math.radians(player_yaw_deg)) * 90
        z = 35
        gluLookAt(n_x, n_y, n_z, 
                  x, y, z, 
                  0, 0, 1)
        
    else:
        yaw = math.radians(camera_yaw_deg)
        x = camera_radius * math.cos(yaw)
        y = camera_radius * math.sin(yaw)
        z = camera_height
        gluLookAt(x, y, z, 0, 0, 0, 0, 0, 1)


def idle():
    update_enemies()
    handle_bullet_enemy_hits()
    update_bullets()
    update_cheat_mode()
    glutPostRedisplay()


def render_frame():
    global player_lives, missed_bullets, score , enemies,player_lives,is_cheat_mode
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity() 
    glViewport(0, 0, 1000, 800)  
    setup_camera() 
    draw_checkerboard()
    draw_walls()
    draw_player()
    draw_bullets()

    for i in enemies:
        draw_enemy(i)
   
    if is_game_running:
        draw_text(10, 790, f"Player Life Remainig: {player_lives}",GLUT_BITMAP_TIMES_ROMAN_24)
        draw_text(10, 760, f"Game Score  : {score} ",GLUT_BITMAP_TIMES_ROMAN_24)
        if is_cheat_mode:
            draw_text(10, 730, f"Player Bullet Missed : {0} ",GLUT_BITMAP_TIMES_ROMAN_24)
        else:
            draw_text(10, 730, f"Player Bullet Missed : {missed_bullets} ",GLUT_BITMAP_TIMES_ROMAN_24)


    else:
        draw_text(10, 790, f"Game is Over. Score is {score}.",GLUT_BITMAP_TIMES_ROMAN_24)
        draw_text(10, 760, f'Press <R> to RESTART',GLUT_BITMAP_TIMES_ROMAN_24)

    glutSwapBuffers()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)  
    glutInitWindowSize(1050, 850)  
    glutInitWindowPosition(0, 0)  
    wind = glutCreateWindow(b"-PUBG-")  

    glutDisplayFunc(render_frame)  
    glutKeyboardFunc(on_keyboard)  
    glutSpecialFunc(on_special_keys)
    glutMouseFunc(on_mouse)
    glutIdleFunc(idle)  
    glutMainLoop()  

if __name__ == "__main__":
    main()