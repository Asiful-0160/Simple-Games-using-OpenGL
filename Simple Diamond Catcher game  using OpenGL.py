from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random
import time

# variables
W_Width, W_Height = 500, 700                        # window size
score = 0                                           # score
diamond_x = random.randint(-235, 235)               # diamond x vals for random pos
down = 50                                           # diamond y vals for animate
n_x = 0                                             # catcher x vals to move
speed1 = 1                                          # diamond speed (vertical)
max_speed = 12                                      # adjust difficulty here
speed2 = 15                                         # catcher speed (horizontal)
r_d, g_d, b_d = random.uniform(0.1, 1), random.uniform(0.1, 1), random.uniform(0.1, 1)
last = time.time()

# flags
pause = False       # pause?
end = False         # cross button exit
new_game = False    # arrow button new start
c_c = False         # checked collision of diamond and catcher yet?
game = True         # game running?
cheat = False       # cheat mode on or off?


# for drawing line using Midpoint algorithm
def zone_change(point, zone1, zone2):
    x, y = point
    if zone1 == 0:
        current_zone = zone2
        if current_zone == 0:
            return (x, y)
        elif current_zone == 1:
            return (y, x)
        elif current_zone == 2:
            return (-y, x)
        elif current_zone == 3:
            return (-x, y)
        elif current_zone == 4:
            return (-x, -y)
        elif current_zone == 5:
            return (-y, -x)
        elif current_zone == 6:
            return (y, -x)
        elif current_zone == 7:
            return (x, -y)
    else:
        current_zone = zone1
        if current_zone == 0:
            return (x, y)
        elif current_zone == 1:
            return (y, x)
        elif current_zone == 2:
            return (y, -x)
        elif current_zone == 3:
            return (-x, y)
        elif current_zone == 4:
            return (-x, -y)
        elif current_zone == 5:
            return (-y, -x)
        elif current_zone == 6:
            return (-y, x)
        elif current_zone == 7:
            return (x, -y)


def detect_zone(x0, y0, x1, y1):
    dx = x1 - x0
    dy = y1 - y0
    if abs(dx) <= abs(dy):
        if dx > 0:
            if dy <= 0:
                return 6
            else:
                return 1
        else:
            if dy <= 0:
                return 5
            else:
                return 2
    else:
        if dx <= 0:
            if dy > 0:
                return 3
            else:
                return 4
        else:
            if dy > 0:
                return 0
            else:
                return 7


def middle_point(x0, y0, x1, y1, r, g, b, p=3):
    glColor3f(r, g, b)
    glPointSize(p)
    zone = detect_zone(x0, y0, x1, y1)
    x0, y0 = zone_change((x0, y0), zone, 0)
    x1, y1 = zone_change((x1, y1), zone, 0)
    dx = x1 - x0
    dy = y1 - y0
    x, y = x0, y0
    NE = 2 * dy - 2 * dx
    E = 2 * dy
    D = 2 * dy - dx

    while x <= x1:
        pnt_x, pnt_y = zone_change((x, y), 0, zone)
        glBegin(GL_POINTS)
        glVertex2f(pnt_x, pnt_y)
        glEnd()
        x += 1
        if D > 0:
            D += NE
            y += 1
        else:
            D += E


def convert_coordinate(x, y):
    global W_Width, W_Height
    a = x - (W_Width / 2)
    b = (W_Height / 2) - y
    return a, b


# collision detect 
def collision(b1x, b1y, b1w, b1h, b2x, b2y, b2w, b2h):
    if (b1x < (b2x + b2w)) and ((b1x + b1w) > b2x) and (b1y < (b2y + b2h)) and ((b1y + b1h) > b2y):
        return True
    else:
        return False


# game elements
def drawShapes():
    global pause
    # pause or running
    if pause is False:
        # pause icon 
        middle_point(-10, 300, -10, 345, .8, .6, .09)
        middle_point(10, 300, 10, 345, .8, .6, .09)
    else:
        # play icon 
        middle_point(-15, 300, -15, 345, .8, .6, .09)
        middle_point(-15, 300, 15, 322, .8, .6, .09)
        middle_point(15, 322, -15, 345, .8, .6, .09)

    # restart icon
    middle_point(-240, 322, -210, 322, .03, .7, .9)
    middle_point(-240, 322, -225, 300, .03, .7, .9)
    middle_point(-240, 322, -225, 345, .03, .7, .9)

    # cross icon
    middle_point(245, 300, 210, 345, .9, .2, .03)
    middle_point(245, 345, 210, 300, .9, .2, .03)


def diamond_basket():
    global diamond_x, down, n_x, r_d, g_d, b_d, game

    # diamond
    if game is True:
        middle_point(-10 + diamond_x, 330 - down, 0 + diamond_x, 345 - down, r_d, g_d, b_d)
        middle_point(0 + diamond_x, 315 - down, -10 + diamond_x, 330 - down, r_d, g_d, b_d)
        middle_point(0 + diamond_x, 315 - down, 10 + diamond_x, 330 - down, r_d, g_d, b_d)
        middle_point(10 + diamond_x, 330 - down, 0 + diamond_x, 345 - down, r_d, g_d, b_d)

    # basket
    if not game:
        r, g, b = 0.9, 0.2, 0.03  # game over = red
    else:
        r, g, b = 1.0, 1.0, 1.0  # normal = white

    middle_point(-50 + n_x, -345, 50 + n_x, -345, r, g, b)
    middle_point(-50 + n_x, -345, -60 + n_x, -330, r, g, b)
    middle_point(50 + n_x, -345, 60 + n_x, -330, r, g, b)
    middle_point(60 + n_x, -330, -60 + n_x, -330, r, g, b)


# game actions
def specialKeyListener(key, x, y):
    global n_x, speed2
    if game is True and pause is False and cheat is False:  
        if key == GLUT_KEY_RIGHT:
            if 60 + n_x <= 250:
                n_x += speed2

        if key == GLUT_KEY_LEFT:
            if -60 + n_x >= -250:
                n_x -= speed2
        glutPostRedisplay()


# cheat mode toggle
def keyboardListener(key, x, y):
    global cheat
    if key == b'c' or key == b'C':
        cheat = not cheat
        if cheat:
            print("Cheat Mode ON")
        else:
            print("Cheat Mode OFF")
    glutPostRedisplay()


def mouseListener(button, state, x, y):
    global pause, new_game, end, game, score, diamond_x, down, n_x, speed1, speed2, c_c, r_d, g_d, b_d, last, cheat
    if button == GLUT_LEFT_BUTTON:
        if state == GLUT_DOWN:
            c_X, c_Y = convert_coordinate(x, y)

            # pause/play
            if -15 <= c_X <= 15 and 300 <= c_Y <= 345 and game is True:
                pause = not pause

            # restart
            if -240 <= c_X <= -210 and 300 <= c_Y <= 345:
                new_game = True

            # exit
            if 210 <= c_X <= 245 and 300 <= c_Y <= 345:
                end = True

    if end:
        print(f'GoodBye! Score = {score}')
        glutLeaveMainLoop()

    if new_game:
        print("Starting Over!")
        pause = False
        end = False
        new_game = False
        cheat = False
        score = 0
        diamond_x = random.randint(-235, 235)
        r_d, g_d, b_d = random.uniform(0.1, 1), random.uniform(0.1, 1), random.uniform(0.1, 1)
        down = 50
        n_x = 0
        game = True
        speed1 = 1
        speed2 = 15
        last = time.time()
        c_c = False

    glutPostRedisplay()


# game play / game logic
def run():
    global pause, new_game, end, game, score, diamond_x, down, n_x, speed1, speed2, c_c, r_d, g_d, b_d
    drawShapes()
    diamond_basket()

    # diamond measure
    current_x = -10 + diamond_x
    current_y = 315 - down

    # bowl measure
    cur_x = -60 + n_x
    cur_y = -345

    # check collision 
    if current_y <= -345 and c_c is False:
        j = collision(current_x, current_y, 20, 45, cur_x, cur_y, 120, 15)
        if j is True:
            pause = False
            end = False
            new_game = False
            score += 1
            r_d, g_d, b_d = random.uniform(0.1, 1), random.uniform(0.1, 1), random.uniform(0.1, 1)
            print(f"Score: {score}")
            diamond_x = random.randint(-235, 235)
            down = 50
            game = True
            c_c = False
            speed1 = min(speed1 + 0.15, max_speed)  # increase difficulty
        else:
            print(f'Game over! Score {score}')
            game = False
            c_c = True


def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glClearColor(0, 0, 0, 0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(0, 0, 200, 0, 0, 0, 0, 1, 0)
    glMatrixMode(GL_MODELVIEW)
    iterate()
    run()
    glutSwapBuffers()


def animate():
    global down, speed1, pause, game, last, n_x, cheat, speed2, diamond_x

    current = time.time()
    delta = current - last
    last = current

    # vertical movement of diamond
    if pause is False and game is True:
        if 350 - down > -350:
            down += speed1 * delta * 144
        else:
            pass

    # cheat mode 
    if cheat and pause is False and game is True:
        target_x = diamond_x
        move_amount = speed2 * delta * 144  

        if n_x < target_x:
            n_x = min(n_x + move_amount, target_x)
        elif n_x > target_x:
            n_x = max(n_x - move_amount, target_x)

        # bound to screen
        if 60 + n_x > 250:
            n_x = 250 - 60
        if -60 + n_x < -250:
            n_x = -250 + 60

    glutPostRedisplay()


def iterate():
    glViewport(0, 0, 500, 700)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(-250, 250, -350, 350, 0.0, 1.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


# GLUT
glutInit()
glutInitDisplayMode(GLUT_DEPTH | GLUT_DOUBLE | GLUT_RGB)
glutInitWindowSize(500, 700)
glutInitWindowPosition(0, 0)
wind = glutCreateWindow(b"Catch the Diamonds!")
glutDisplayFunc(display)
glutIdleFunc(animate)
glutSpecialFunc(specialKeyListener)
glutKeyboardFunc(keyboardListener)  
glutMouseFunc(mouseListener)
glutMainLoop()
