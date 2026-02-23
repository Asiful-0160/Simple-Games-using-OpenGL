import sys
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from math import sin, cos, pi
import random
import time


# ---------- Game States (Menu System) ----------
GAME_MENU = 0
GAME_CONTROLS = 1
GAME_PLAYING = 2
GAME_OVER = 3

# ---------- Power-up: Shield ----------
SHIELD_DURATION = 5.0      # seconds
SHIELD_COOLDOWN = 8.0      # seconds after shield ends
SHIELD_MAX_CHARGES = 2




# ---------- Power-up: Nova (rarer than Shield) ----------
NOVA_MAX_CHARGES = 2
# Clears nearby real obstacles when activated.
# (No cooldown required; rarity is via spawn distance.)

class Box:
    def __init__(self, x, y, z, w, h, d):
        self.x = x
        self.y = y
        self.z = z
        self.w = w / 2.0
        self.h = h / 2.0
        self.d = d / 2.0

    def hit(self, other):
        xo = abs(self.x - other.x) * 2 < (self.w * 2 + other.w * 2)

        ymin = self.y - self.h
        ymax = self.y + self.h
        omin = other.y - other.h
        omax = other.y + other.h
        yo = (ymax > omin) and (ymin < omax)

        zo = abs(self.z - other.z) * 2 < (self.d * 2 + other.d * 2)
        return xo and yo and zo


class Game:
    def __init__(self):
        self.w = 800
        self.h = 700

        self.roadw = 60.0
        self.roadx0 = 20.0
        self.roadx1 = self.roadx0 + self.roadw
        self.leftside = self.roadx0 - 5.0
        self.rightside = self.roadx1 + 5.0

        self.carw = 2.2
        self.card = 4.4
        self.carx = (self.roadx0 + self.roadx1) / 2.0
        self.cary = 0.0
        self.carz = -5.0

        self.score = 0
        self.life = 3
        self.maxlife = 3

        self.pause = False
        self.over = False

        # ---------- Explosion VFX (space-shooter style) ----------
        # Expanding + fading spheres at collision points.
        # Each item: {x,y,z, age, dur, r0, r1}
        self.explosions = []



        # ---------- Shield state ----------
        self.shield_on = False
        self.shield_t = 0.0          # remaining active time
        self.shield_cd = 0.0         # remaining cooldown time
        self.shield_charges = 0      # collected charges (press E to use)

        # Shield pickup (power-up object)
        self.shield_pick = {}
        # ---------- Nova state ----------
        self.nova_charges = 0
        self.nova_pick = {}
        # Menu/state machine
        self.state = GAME_MENU
        self.msg = ""
        self.msgt = 0
        self.msgmax = 90

        self.view = 1
        self.camheight = 80.0
        self.fixheight = 15.0
        self.fixdist = 20.0

        self.level = 0
        self.maxlevel = 5
        self.levelstep = 30

        self.base = 1.0
        self.boost = 0.0
        self.booston = False

        self.movex = 1.5

        self.env = 0.50
        self.pts = 0.55
        self.gem = 0.60
        self.obs = 0.78

        self.dash = [i * 15.0 for i in range(10)]


        self.treel = []
        self.treer = []


        self.posts = [i * 8.0 for i in range(80)]
        self.lamps = [i * 35.0 for i in range(14)]
        self.signs = []

        self.pointn = 15
        self.points = []
        self.bonus = {}


        self.types = {
            "rock":    {"w": 2.0, "h": 2.0,  "d": 2.0, "pen": 5,  "life": 1, "c": (0.55, 0.55, 0.55)},
            "hole":    {"w": 3.0, "h": 0.25, "d": 3.0, "pen": 10, "life": 1, "c": (1.00, 0.20, 0.80)},
            "barrier": {"w": 5.0, "h": 2.5,  "d": 1.5, "pen": 8,  "life": 2, "c": (1.00, 0.55, 0.10)}
        }

        self.pool = 6 * (2 ** self.maxlevel)
        self.want = 6
        self.space = 20.0
        self.count = 0
        self.obstacles = []

        self.last = None


        self.front = 100.0
        self.back = -280.0
        self.span = 420.0

        self.reset()


    # ---------------- Explosion helpers ----------------
    def add_explosion(self, x, y, z, dur=0.45, r0=0.6, r1=3.2):
        """Spawn an expanding/fading explosion at world position (x,y,z)."""
        self.explosions.append({
            "x": float(x),
            "y": float(y),
            "z": float(z),
            "age": 0.0,
            "dur": float(dur),
            "r0": float(r0),
            "r1": float(r1),
        })

    def update_explosions(self, dt):
        if not self.explosions:
            return
        alive = []
        for e in self.explosions:
            e["age"] += dt
            if e["age"] < e["dur"]:
                alive.append(e)
        self.explosions = alive

    def draw_explosions(self):
        if not self.explosions:
            return

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Depth test stays ON so the explosion respects scene depth.
        for e in self.explosions:
            t = max(0.0, min(1.0, e["age"] / max(1e-6, e["dur"])))
            r = e["r0"] + (e["r1"] - e["r0"]) * t
            a = 1.0 - t  # fade out

            glPushMatrix()
            glTranslatef(e["x"], e["y"], e["z"])
            glColor4f(1.0, 0.6, 0.1, a)
            glutSolidSphere(r, 14, 14)

            # small bright core for a nicer punch
            glColor4f(1.0, 1.0, 0.4, a)
            glutSolidSphere(max(0.2, r * 0.35), 12, 12)
            glPopMatrix()

        glDisable(GL_BLEND)


    def spawnpoints(self):
        self.points = []
        for _ in range(self.pointn):
            self.points.append({
                "x": random.uniform(self.roadx0 + 5.0, self.roadx1 - 5.0),
                "y": 1.0,
                "z": random.uniform(-150.0, -50.0),
                "on": True
            })

    def spawnbonus(self):
        self.bonus = {
            "x": random.uniform(self.roadx0 + 10.0, self.roadx1 - 10.0),
            "y": 1.0,
            "z": -120.0,
            "w": 1.5, "h": 1.5, "d": 1.5,
            "on": True
        }

    def spawnshield(self):
        # Shield pickup (cyan orb). Collect to gain a shield charge (press E to activate).
        self.shield_pick = {
            "x": random.uniform(self.roadx0 + 10.0, self.roadx1 - 10.0),
            "y": 1.0,
            "z": random.uniform(-260.0, -200.0),
            "w": 1.6, "h": 1.6, "d": 1.6,
            "on": True
        }


    def spawnnova(self):
        # Nova pickup (purple orb). Collect to gain a nova charge (press F to use).
        # Nova is rarer than shield: it respawns farther back.
        self.nova_pick = {
            "x": random.uniform(self.roadx0 + 10.0, self.roadx1 - 10.0),
            "y": 1.0,
            "z": random.uniform(-520.0, -440.0),
            "w": 1.7, "h": 1.7, "d": 1.7,
            "on": True
        }

    def spawnsigns(self):
        self.signs = []
        for i in range(10):
            self.signs.append({
                "x": random.choice([self.roadx0 - 10.0, self.roadx1 + 10.0]),
                "z": -40.0 - i * 55.0,
                "r": random.uniform(0.2, 1.0),
                "g": random.uniform(0.2, 1.0),
                "b": random.uniform(0.2, 1.0)
            })

    def spawntrees(self):

        self.treel = []
        self.treer = []
        z = self.back
        while z <= self.front:
            self.treel.append(z)
            self.treer.append(z + random.uniform(-5.0, 5.0))
            z += 22.0

    def randx(self, w):
        m = 1.0
        a = self.roadx0 + (w / 2.0) + m
        b = self.roadx1 - (w / 2.0) - m
        if a >= b:
            return (self.roadx0 + self.roadx1) / 2.0
        return random.uniform(a, b)

    def scale(self):
        self.base = float(2 ** self.level)
        self.want = min(6 * (2 ** self.level), self.pool)

    def spawnobstacles(self):
        self.obstacles = []
        self.count = 0
        self.scale()

        keys = list(self.types.keys())
        for i in range(self.pool):
            name = random.choice(keys)
            info = self.types[name]
            z = -80.0 - i * self.space

            fake = (self.count % 3) < 2
            self.count += 1

            on = (i < self.want)
            self.obstacles.append({
                "x": self.randx(info["w"]),
                "y": 0.0,
                "z": z if on else (-600.0 - i * 5.0),
                "t": name,
                "w": info["w"], "h": info["h"], "d": info["d"],
                "pen": info["pen"],
                "life": info["life"],
                "c": info["c"],
                "fake": fake,
                "on": on
            })


    def carbox(self):
        return Box(self.carx, 0.6, self.carz + self.card / 2.0, self.carw, 1.0, self.card)

    def objbox(self, o):
        return Box(o["x"], o["y"] + o["h"] / 2.0, o["z"], o["w"], o["h"], o["d"])

    def pointbox(self, p):
        s = 0.6
        return Box(p["x"], p["y"], p["z"], s, s, s)


    def text(self, x, y, s, font=GLUT_BITMAP_HELVETICA_18, r=1.0, g=1.0, b=1.0):
        glColor3f(r, g, b)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, self.w, 0, self.h)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glRasterPos2f(x, y)
        for ch in s:
            glutBitmapCharacter(font, ord(ch))

        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)



    def text_width(self, text, font=GLUT_BITMAP_HELVETICA_18):
        width = 0
        for ch in text:
            width += glutBitmapWidth(font, ord(ch))
        return width

    def camera(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        a = (self.w / self.h) if self.h > 0 else 1.0
        gluPerspective(60.0, a, 0.1, 300.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        cz = self.carz
        if self.view == 0:
            cx, cy, cz2 = self.carx, 1.8, cz + 1.0
            lx, ly, lz = self.carx, 1.5, cz - 15.0
            gluLookAt(cx, cy, cz2, lx, ly, lz, 0, 1, 0)
        elif self.view == 2:
            cx, cy, cz2 = self.carx, self.fixheight, cz + self.fixdist
            lx, ly, lz = self.carx, 1.0, cz
            gluLookAt(cx, cy, cz2, lx, ly, lz, 0, 1, 0)
        else:
            side = 15.0
            cx, cy, cz2 = self.carx - side, self.camheight, cz
            lx, ly, lz = self.carx, 1.5, cz
            gluLookAt(cx, cy, cz2, lx, ly, lz, 0, 1, 0)


    def cap(self, r, z, n=16):
        step = (2.0 * pi) / float(n)
        glBegin(GL_TRIANGLES)
        for i in range(n):
            a = i * step
            b = (i + 1) * step
            glVertex3f(0.0, 0.0, z)
            glVertex3f(r * cos(a), r * sin(a), z)
            glVertex3f(r * cos(b), r * sin(b), z)
        glEnd()

    def wheel(self, r, w):
        q = gluNewQuadric()
        gluCylinder(q, r, r, w, 14, 1)
        self.cap(r, 0.0, 16)
        self.cap(r, w, 16)


    def road(self):
        glColor3f(0.40, 0.40, 0.40)
        glBegin(GL_QUADS)

        seg = 10.0
        n = 50
        for i in range(-n // 2, n // 2):
            z = i * seg
            glVertex3f(self.roadx0, 0.0, z)
            glVertex3f(self.roadx1, 0.0, z)
            glVertex3f(self.roadx1, 0.0, z + seg)
            glVertex3f(self.roadx0, 0.0, z + seg)

        glEnd()

        mid = (self.roadx0 + self.roadx1) / 2.0
        dash = 4.0
        gap = 6.0
        pat = dash + gap
        cnt = 22
        off = (self.dash[0] % pat) if self.dash else 0.0

        glColor3f(1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        for i in range(cnt * 2):
            a = -cnt * pat + i * pat - off
            b = a + dash
            if b < 10.0 and a > -260.0:
                w = 0.25
                y = 0.03
                glVertex3f(mid - w, y, a)
                glVertex3f(mid + w, y, a)
                glVertex3f(mid + w, y, b)
                glVertex3f(mid - w, y, b)
        glEnd()

    def tree(self, x, z):
        glPushMatrix()
        glTranslatef(x, 0.0, z)

        glColor3f(0.545, 0.271, 0.075)
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        q = gluNewQuadric()
        gluCylinder(q, 0.4, 0.4, 3.0, 10, 1)
        glPopMatrix()

        glColor3f(0.10, 0.60, 0.10)
        glTranslatef(0.0, 3.5, 0.0)
        q2 = gluNewQuadric()
        gluSphere(q2, 1.5, 10, 10)

        glPopMatrix()

    def post(self, x, z):
        glPushMatrix()
        glTranslatef(x, 0.35, z)

        glColor3f(0.80, 0.80, 0.85)
        glPushMatrix()
        glScalef(0.35, 0.7, 0.35)
        glutSolidCube(1.0)
        glPopMatrix()

        glTranslatef(0.0, 0.55, 0.0)
        glColor3f(0.60, 0.60, 0.70)
        glPushMatrix()
        glScalef(1.0, 0.2, 0.8)
        glutSolidCube(1.0)
        glPopMatrix()

        glPopMatrix()

    def lamp(self, x, z):
        glPushMatrix()
        glTranslatef(x, 0.0, z)

        glColor3f(0.25, 0.25, 0.28)
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        q = gluNewQuadric()
        gluCylinder(q, 0.12, 0.12, 5.5, 10, 1)
        glPopMatrix()

        glTranslatef(0.0, 5.6, 0.0)
        glColor3f(1.0, 1.0, 0.70)
        q2 = gluNewQuadric()
        gluSphere(q2, 0.35, 10, 10)

        glPopMatrix()

    def sign(self, s):
        glPushMatrix()
        glTranslatef(s["x"], 0.0, s["z"])

        glColor3f(0.25, 0.25, 0.25)
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        q = gluNewQuadric()
        gluCylinder(q, 0.18, 0.18, 3.2, 10, 1)
        glPopMatrix()

        glTranslatef(0.0, 3.6, 0.0)
        glColor3f(s["r"], s["g"], s["b"])
        glPushMatrix()
        glScalef(3.8, 1.4, 0.2)
        glutSolidCube(1.0)
        glPopMatrix()

        glPopMatrix()

    def coin(self, p):
        if not p["on"]:
            return
        glColor3f(1.0, 0.85, 0.0)
        glPushMatrix()
        glTranslatef(p["x"], p["y"], p["z"])
        q = gluNewQuadric()
        gluSphere(q, 0.4, 10, 10)
        glPopMatrix()

    def lifeorb(self, o):
        if not o["on"]:
            return
        glColor3f(0.6, 1.0, 0.6)
        glPushMatrix()
        glTranslatef(o["x"], o["y"] + o["h"] / 2.0, o["z"])
        q = gluNewQuadric()
        gluSphere(q, 0.7, 10, 10)
        glPopMatrix()

    def shieldorb(self, o):
        if not o.get("on", False):
            return
        glColor3f(0.2, 0.9, 1.0)
        glPushMatrix()
        glTranslatef(o["x"], o["y"] + o["h"] / 2.0, o["z"])
        q = gluNewQuadric()
        gluSphere(q, 0.75, 12, 12)
        glPopMatrix()


    def novaorb(self, o):
        if not o.get("on", False):
            return
        glColor3f(0.75, 0.35, 1.0)
        glPushMatrix()
        glTranslatef(o["x"], o["y"] + o["h"] / 2.0, o["z"])
        q = gluNewQuadric()
        gluSphere(q, 0.8, 12, 12)
        glPopMatrix()

    def obstacle(self, o):
        if not o["on"]:
            return


        if o["t"] == "hole":
            glColor3f(1.0, 0.2, 0.8)
        else:
            r, g, b = o["c"]
            if o["fake"]:
                r = 0.6 * r + 0.4
                g = 0.6 * g + 0.4
                b = 0.6 * b + 0.4
            glColor3f(r, g, b)

        glPushMatrix()
        glTranslatef(o["x"], o["y"], o["z"])

        if o["t"] == "rock":
            glTranslatef(0.0, o["h"] / 2.0, 0.0)
            q = gluNewQuadric()
            gluSphere(q, o["w"] / 2.0, 12, 12)
        elif o["t"] == "hole":
            glTranslatef(0.0, 0.02, 0.0)
            glRotatef(-90, 1, 0, 0)
            q = gluNewQuadric()
            gluCylinder(q, o["w"] / 2.0, o["w"] / 2.0, 0.12, 12, 1)
        else:
            glTranslatef(0.0, o["h"] / 2.0, 0.0)
            glScalef(o["w"], o["h"], o["d"])
            glutSolidCube(1.0)

        glPopMatrix()

    def car(self):
        x, y, z = self.carx, self.cary, self.carz
        w, d = self.carw, self.card

        wheelr = 0.45
        wheelw = 0.22

        ch = 0.45
        hh = 0.28
        cab = 0.55

        chy = wheelr + (ch / 2.0) + 0.05
        hhy = chy + (ch / 2.0) + (hh / 2.0) - 0.10
        cby = chy + (ch / 2.0) + (cab / 2.0) - 0.05

        hhz = -0.22 * d
        cbz = 0.12 * d

        wx = (w / 2.0) + (wheelw / 2.0) - 0.03
        fz = -(d * 0.35)
        rz = (d * 0.35)

        glPushMatrix()
        glTranslatef(x, y, z)

        glColor3f(0.85, 0.05, 0.05)
        glPushMatrix()
        glTranslatef(0.0, chy, 0.0)
        glScalef(w * 1.05, ch, d * 1.05)
        glutSolidCube(1.0)
        glPopMatrix()

        glColor3f(0.75, 0.03, 0.03)
        glPushMatrix()
        glTranslatef(0.0, hhy, hhz)
        glScalef(w * 0.95, hh, d * 0.45)
        glutSolidCube(1.0)
        glPopMatrix()

        glColor3f(0.90, 0.10, 0.10)
        glPushMatrix()
        glTranslatef(0.0, cby, cbz)
        glScalef(w * 0.80, cab, d * 0.55)
        glutSolidCube(1.0)
        glPopMatrix()

        glColor3f(0.07, 0.09, 0.12)
        glPushMatrix()
        glTranslatef(0.0, cby + 0.05, cbz)
        glScalef(w * 0.72, cab * 0.55, d * 0.45)
        glutSolidCube(1.0)
        glPopMatrix()

        def drawwheel(px, pz):
            glColor3f(0.0, 0.0, 0.0)
            glPushMatrix()
            glTranslatef(px, wheelr, pz)
            glRotatef(90, 0, 1, 0)
            glTranslatef(0.0, 0.0, -wheelw / 2.0)
            self.wheel(wheelr, wheelw)
            glPopMatrix()

        drawwheel(-wx, fz)
        drawwheel(wx, fz)
        drawwheel(-wx, rz)
        drawwheel(wx, rz)

        glPopMatrix()


    def draw(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glViewport(0, 0, self.w, self.h)

        # --------- GAMEPLAY / BACKGROUND RENDER ---------
        # We always render the 3D world. Menus are drawn as a 2D overlay on top.

        # --------- GAMEPLAY RENDER ---------
        self.camera()
        self.road()

        lx = self.roadx0 - 1.2
        rx = self.roadx1 + 1.2

        for z in self.posts:
            if -260.0 <= z <= 80.0:
                self.post(lx, z)
                self.post(rx, z)

        for i, z in enumerate(self.lamps):
            if -260.0 <= z <= 90.0:
                x = (self.roadx0 - 12.0) if (i % 2 == 0) else (self.roadx1 + 12.0)
                self.lamp(x, z)

        for s in self.signs:
            if -280.0 <= s["z"] <= 90.0:
                self.sign(s)


        for z in self.treel:
            if -260.0 <= z <= 80.0:
                self.tree(self.leftside, z)
        for z in self.treer:
            if -260.0 <= z <= 80.0:
                self.tree(self.rightside, z)

        for p in self.points:
            self.coin(p)
        self.lifeorb(self.bonus)
        self.shieldorb(self.shield_pick)
        self.novaorb(self.nova_pick)

        obs = sorted(self.obstacles, key=lambda o: o["z"])
        for o in obs:
            self.obstacle(o)

        # draw explosions after obstacles so they appear on top
        self.draw_explosions()

        self.car()

        if self.state == GAME_PLAYING:
            # Shield visual (translucent bubble around car)
            if self.shield_on:
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                glColor4f(0.2, 0.9, 1.0, 0.25)
                glPushMatrix()
                glTranslatef(self.carx, 1.0, self.carz + self.card / 2.0)
                glutSolidSphere(2.2, 16, 16)
                glPopMatrix()
                glDisable(GL_BLEND)

            self.text(20, self.h - 30, f"Score: {self.score}", r=1.0, g=1.0, b=0.0)
            self.text(20, 30, f"Lives: {self.life}", r=1.0, g=1.0, b=1.0)
            # Shield HUD
            if self.shield_on:
                self.text(20, 70, f"Shield: ON ({self.shield_t:.1f}s)", r=0.2, g=0.9, b=1.0, font=GLUT_BITMAP_9_BY_15)
            else:
                cd_txt = f"{self.shield_cd:.1f}s" if self.shield_cd > 0.0 else "Ready"
                self.text(20, 70, f"Shield Charges: {self.shield_charges} | Cooldown: {cd_txt}", r=0.2, g=0.9, b=1.0, font=GLUT_BITMAP_9_BY_15)
            # Nova HUD
            self.text(20, 55, f"Nova Charges: {self.nova_charges} (F to use)", r=0.85, g=0.45, b=1.0, font=GLUT_BITMAP_9_BY_15)

            self.text(20, self.h - 50, f"Level: {self.level + 1}", r=0.8, g=0.8, b=1.0)
            self.text(20, self.h - 70, f"Speed x{int(self.base)}", r=0.8, g=1.0, b=0.8)
            self.text(20, self.h - 90, f"Obstacles x{int(2 ** self.level)}", r=0.8, g=1.0, b=0.8)

            if self.msgt > 0:
                self.text(20, self.h - 110, self.msg, r=1.0, g=0.2, b=0.2)

            if self.pause:
                self.text(self.w / 2 - 40, self.h / 2, "PAUSED", r=1.0, g=1.0, b=1.0)
                self.text(self.w / 2 - 120, self.h / 2 - 20, "Left-Click or 'P' to Resume", r=0.8, g=0.8, b=0.8)

        else:
            # --------- MENU / CONTROLS / GAME OVER OVERLAY ---------
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            gluOrtho2D(0, self.w, 0, self.h)
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()
            glDisable(GL_DEPTH_TEST)
            was_lighting = glIsEnabled(GL_LIGHTING)
            if was_lighting:
                glDisable(GL_LIGHTING)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glColor4f(0.0, 0.0, 0.0, 0.55)
            glBegin(GL_QUADS)
            glVertex2f(0, 0)
            glVertex2f(self.w, 0)
            glVertex2f(self.w, self.h)
            glVertex2f(0, self.h)
            glEnd()
            glDisable(GL_BLEND)

            title_y = self.h - 120
            if self.state == GAME_MENU:
                lines = [
                    ("3D DRIVING GAME", (1.0, 1.0, 0.2), GLUT_BITMAP_HELVETICA_18),
                    ("G : Start Game", (1.0, 1.0, 1.0), GLUT_BITMAP_HELVETICA_18),
                    ("Z : Controls", (0.9, 0.9, 0.9), GLUT_BITMAP_HELVETICA_18),
                    ("Q / ESC : Quit", (0.9, 0.9, 0.9), GLUT_BITMAP_HELVETICA_18),
                    ("Background is live (menu overlay)", (0.7, 0.9, 0.7), GLUT_BITMAP_9_BY_15),
                ]
                y = title_y
                for i, (line, col, font) in enumerate(lines):
                    x = self.w//2 - self.text_width(line, font)//2
                    r, g, b = col
                    self.text(x, y - i*30, line, r=r, g=g, b=b, font=font)
            elif self.state == GAME_CONTROLS:
                self.text(self.w/2 - 90, title_y, "CONTROLS", r=1.0, g=1.0, b=0.2)
                y = title_y - 45
                lh = 22
                lines = [
                    "Arrow Left/Right : Move car",
                    "W                : Toggle boost",
                    "P or Left Click  : Pause / Resume",
                    "V                : Change camera view",
                    "E                : Activate Shield (if charged)",
                    "F                : Activate NOVA (all on-screen)",
                    "Up/Down (View 2) : Camera height",
                    "Right Click      : Restart after Game Over",
                    "B                : Back to Menu",
                ]
                for line in lines:
                    self.text(self.w/2 - 220, y, line, r=1.0, g=1.0, b=1.0)
                    y -= lh
            elif self.state == GAME_OVER:
                self.text(self.w/2 - 70, title_y, "GAME OVER", r=1.0, g=0.2, b=0.2)
                self.text(self.w/2 - 110, title_y - 40, f"Final Score: {self.score}", r=1.0, g=1.0, b=1.0)
                self.text(self.w/2 - 220, title_y - 75, "Right Click : Restart", r=0.9, g=0.9, b=0.9)
                self.text(self.w/2 - 220, title_y - 100, "B : Back to Menu", r=0.9, g=0.9, b=0.9)

            if was_lighting:
                glEnable(GL_LIGHTING)
            glEnable(GL_DEPTH_TEST)
            glPopMatrix()
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
        glutSwapBuffers()


    def scroll_world(self, dt):
        # Scroll / move the world forward (used both in gameplay and as animated background for the menu).
        speed = self.base + self.boost
        mul = dt * 60.0

        dz = self.env * speed * mul
        dzp = self.pts * speed * mul
        dzg = self.gem * speed * mul
        dzo = self.obs * speed * mul

        # Lane dashes
        self.dash = [z + dz for z in self.dash]
        if self.dash and self.dash[0] > 50.0:
            self.dash = [z - 120.0 for z in self.dash]

        # Trees
        for i in range(len(self.treel)):
            self.treel[i] += dz
            if self.treel[i] > self.front:
                self.treel[i] -= self.span + random.uniform(0.0, 25.0)

        for i in range(len(self.treer)):
            self.treer[i] += dz
            if self.treer[i] > self.front:
                self.treer[i] -= self.span + random.uniform(0.0, 25.0)

        # Roadside props
        self.posts = [z + dz for z in self.posts]
        for i in range(len(self.posts)):
            if self.posts[i] > 90.0:
                self.posts[i] -= 600.0

        self.lamps = [z + dz for z in self.lamps]
        for i in range(len(self.lamps)):
            if self.lamps[i] > 100.0:
                self.lamps[i] -= 600.0

        for s in self.signs:
            s["z"] += dz
            if s["z"] > 100.0:
                s["z"] -= 600.0
                s["x"] = random.choice([self.roadx0 - 10.0, self.roadx1 + 10.0])
                s["r"] = random.uniform(0.2, 1.0)
                s["g"] = random.uniform(0.2, 1.0)
                s["b"] = random.uniform(0.2, 1.0)

        # Golden orbs (score points)
        for p in self.points:
            p["z"] += dzp
            if p["z"] > 10.0:
                p["z"] = random.uniform(-160.0, -110.0)
                p["x"] = random.uniform(self.roadx0 + 5.0, self.roadx1 - 5.0)
                p["on"] = True

        # Life orb
        self.bonus["z"] += dzg
        if self.bonus["z"] > 10.0:
            self.bonus["z"] = random.uniform(-220.0, -160.0)
            self.bonus["x"] = random.uniform(self.roadx0 + 10.0, self.roadx1 - 10.0)
            self.bonus["on"] = True

        # Shield pickup (same spawn style as life orb)
        self.shield_pick["z"] += dzg
        if self.shield_pick["z"] > 10.0:
            self.shield_pick["z"] = random.uniform(-260.0, -200.0)
            self.shield_pick["x"] = random.uniform(self.roadx0 + 10.0, self.roadx1 - 10.0)
            self.shield_pick["on"] = True

        # Nova pickup (rarer)
        self.nova_pick["z"] += dzg
        if self.nova_pick["z"] > 10.0:
            self.nova_pick["z"] = random.uniform(-520.0, -440.0)
            self.nova_pick["x"] = random.uniform(self.roadx0 + 10.0, self.roadx1 - 10.0)
            self.nova_pick["on"] = True

        # Obstacles
        activez = [o["z"] for o in self.obstacles if o["on"]]
        far = min(activez) if activez else -80.0
        now = sum(1 for o in self.obstacles if o["on"])
        keys = list(self.types.keys())

        for i, o in enumerate(self.obstacles):
            reset = False
            if o["on"]:
                o["z"] += dzo
                if o["z"] > 10.0:
                    o["on"] = False
                    reset = True
            else:
                # drift it further away while inactive so it doesn't get immediately re-used
                o["z"] -= 0.2 * dzo

            needmore = (now < self.want)
            if reset or (not o["on"] and needmore):
                other = [b["z"] for j, b in enumerate(self.obstacles) if b["on"] and j != i]
                far2 = min(other) if other else far
                newz = far2 - random.uniform(18.0, 35.0)
                o["z"] = max(newz, -520.0)

                name = random.choice(keys)
                info = self.types[name]
                o["t"] = name
                o["w"], o["h"], o["d"] = info["w"], info["h"], info["d"]
                o["pen"] = info["pen"]
                o["life"] = info["life"]
                o["c"] = info["c"]
                o["x"] = self.randx(info["w"])

                o["fake"] = (self.count % 3) < 2
                self.count += 1
                o["on"] = True
                if needmore:
                    now += 1

    def update_background(self, dt):
        # Background animation for MENU/CONTROLS: scroll the world without gameplay (no collisions, no scoring).
        self.update_explosions(dt)
        if self.msgt > 0:
            self.msgt -= 1
            if self.msgt == 0:
                self.msg = ""
        if self.pause or self.over:
            return
        self.scroll_world(dt)
    def update(self, dt):
        # Update VFX
        self.update_explosions(dt)
        if self.msgt > 0:
            self.msgt -= 1
            if self.msgt == 0:
                self.msg = ""

        if self.pause or self.over:
            return

        # ---------- Shield timers ----------
        if self.shield_cd > 0.0:
            self.shield_cd = max(0.0, self.shield_cd - dt)

        if self.shield_on:
            self.shield_t -= dt
            if self.shield_t <= 0.0:
                self.shield_on = False
                self.shield_t = 0.0
                # start cooldown when shield ends
                self.shield_cd = max(self.shield_cd, SHIELD_COOLDOWN)

        nxt = min(self.score // self.levelstep, self.maxlevel)
        if nxt > self.level:
            self.level = nxt
            self.scale()

        speed = self.base + self.boost
        mul = dt * 60.0

        dz = self.env * speed * mul
        dzp = self.pts * speed * mul
        dzg = self.gem * speed * mul
        dzo = self.obs * speed * mul

        self.dash = [z + dz for z in self.dash]
        if self.dash and self.dash[0] > 50.0:
            self.dash = [z - 120.0 for z in self.dash]


        for i in range(len(self.treel)):
            self.treel[i] += dz
            if self.treel[i] > self.front:
                self.treel[i] -= self.span + random.uniform(0.0, 25.0)

        for i in range(len(self.treer)):
            self.treer[i] += dz
            if self.treer[i] > self.front:
                self.treer[i] -= self.span + random.uniform(0.0, 25.0)

        self.posts = [z + dz for z in self.posts]
        for i in range(len(self.posts)):
            if self.posts[i] > 90.0:
                self.posts[i] -= 600.0

        self.lamps = [z + dz for z in self.lamps]
        for i in range(len(self.lamps)):
            if self.lamps[i] > 100.0:
                self.lamps[i] -= 600.0

        for s in self.signs:
            s["z"] += dz
            if s["z"] > 100.0:
                s["z"] -= 600.0
                s["x"] = random.choice([self.roadx0 - 10.0, self.roadx1 + 10.0])
                s["r"] = random.uniform(0.2, 1.0)
                s["g"] = random.uniform(0.2, 1.0)
                s["b"] = random.uniform(0.2, 1.0)

        for p in self.points:
            p["z"] += dzp
            if p["z"] > 10.0:
                p["z"] = random.uniform(-160.0, -110.0)
                p["x"] = random.uniform(self.roadx0 + 5.0, self.roadx1 - 5.0)
                p["on"] = True

        self.bonus["z"] += dzg
        if self.bonus["z"] > 10.0:
            self.bonus["z"] = random.uniform(-220.0, -160.0)
            self.bonus["x"] = random.uniform(self.roadx0 + 10.0, self.roadx1 - 10.0)
            self.bonus["on"] = True
        # Move shield pickup (power-up) -- same scroll logic as life orb
        self.shield_pick["z"] += dzg
        if self.shield_pick["z"] > 10.0:
            self.shield_pick["z"] = random.uniform(-260.0, -200.0)
            self.shield_pick["x"] = random.uniform(self.roadx0 + 10.0, self.roadx1 - 10.0)
            self.shield_pick["on"] = True

        # Move nova pickup (rarer than shield) -- same scroll logic as life orb
        self.nova_pick["z"] += dzg
        if self.nova_pick["z"] > 10.0:
            self.nova_pick["z"] = random.uniform(-520.0, -440.0)
            self.nova_pick["x"] = random.uniform(self.roadx0 + 10.0, self.roadx1 - 10.0)
            self.nova_pick["on"] = True


        activez = [o["z"] for o in self.obstacles if o["on"]]
        far = min(activez) if activez else -80.0
        now = sum(1 for o in self.obstacles if o["on"])
        keys = list(self.types.keys())

        for i, o in enumerate(self.obstacles):
            reset = False
            if o["on"]:
                o["z"] += dzo
                if o["z"] > 10.0:
                    o["on"] = False
                    reset = True
            else:
                o["z"] -= 0.2 * dzo

            needmore = (now < self.want)
            if reset or (not o["on"] and needmore):
                other = [b["z"] for j, b in enumerate(self.obstacles) if b["on"] and j != i]
                far2 = min(other) if other else far
                newz = far2 - random.uniform(18.0, 35.0)
                o["z"] = max(newz, -520.0)

                name = random.choice(keys)
                info = self.types[name]
                o["t"] = name
                o["w"], o["h"], o["d"] = info["w"], info["h"], info["d"]
                o["pen"] = info["pen"]
                o["life"] = info["life"]
                o["c"] = info["c"]
                o["x"] = self.randx(info["w"])

                o["fake"] = (self.count % 3) < 2
                self.count += 1
                o["on"] = True
                if needmore:
                    now += 1

        car = self.carbox()

        for p in self.points:
            if p["on"] and car.hit(self.pointbox(p)):
                p["on"] = False
                self.score += 1

        if self.bonus["on"] and car.hit(self.objbox(self.bonus)):
            self.bonus["on"] = False
            if self.life < self.maxlife:
                self.life += 1
        if self.shield_pick.get("on", False) and car.hit(self.objbox(self.shield_pick)):
            self.shield_pick["on"] = False
            self.shield_charges = min(SHIELD_MAX_CHARGES, self.shield_charges + 1)
            self.msg = f"Shield charge +1 (E to use). Charges: {self.shield_charges}"
            self.msgt = self.msgmax

        if self.nova_pick.get("on", False) and car.hit(self.objbox(self.nova_pick)):
            self.nova_pick["on"] = False
            self.nova_charges = min(NOVA_MAX_CHARGES, self.nova_charges + 1)
            self.msg = f"Nova charge +1 (F to use). Charges: {self.nova_charges}"
            self.msgt = self.msgmax

        for o in self.obstacles:
            if o["on"] and car.hit(self.objbox(o)):
                # Explosion at obstacle position (space-shooter style feedback)
                self.add_explosion(o["x"], o["y"] + max(0.8, o["h"] * 0.6), o["z"])

                o["on"] = False
                o["z"] = -700.0

                if not o["fake"]:
                    if self.shield_on:
                        # Shield absorbs the hit (no penalty)
                        self.msg = "Shield absorbed the hit!"
                        self.msgt = self.msgmax
                    else:
                        self.score = max(0, self.score - o["pen"])
                        self.life -= o["life"]

                    word = "Life" if o["life"] == 1 else "Lives"
                    self.msg = f"Hit! -{o['pen']} Score, -{o['life']} {word}"
                    self.msgt = self.msgmax

                    if self.life <= 0:
                        self.life = 0
                        # Big explosion on the car when game ends
                        self.add_explosion(self.carx, 1.0, self.carz, dur=0.75, r0=1.0, r1=5.0)
                        self.over = True
                        self.state = GAME_OVER
                        break


    def idle(self):
        now = time.perf_counter()
        if self.last is None:
            self.last = now
        dt = now - self.last
        self.last = now
        if dt > 0.05:
            dt = 0.05

        if self.state == GAME_PLAYING:
            self.update(dt)
        elif self.state in (GAME_MENU, GAME_CONTROLS):
            self.update_background(dt)

        glutPostRedisplay()

    def key(self, key, x, y):
        try:
            k = key.decode("utf-8").lower()
        except Exception:
            k = ""

        # Quit anytime
        if k in ("q", "\x1b"):  # q or ESC
            sys.exit(0)

        # Back to menu from controls/over
        if k == "b" and self.state in (GAME_CONTROLS, GAME_OVER):
            self.state = GAME_MENU
            return

        # Menu screens
        if self.state == GAME_MENU:
            if k == "g":
                self.reset()
                self.state = GAME_PLAYING
            elif k == "z":
                self.state = GAME_CONTROLS
            return

        if self.state == GAME_CONTROLS:
            if k == "g":
                self.reset()
                self.state = GAME_PLAYING
            return

        if self.state == GAME_OVER:
            if k == "g":
                self.reset()
                self.state = GAME_PLAYING
            return

        # ---------------- Gameplay keys (state == GAME_PLAYING) ----------------
        if k == "p":
            self.pause = not self.pause
            return

        if self.pause or self.over:
            return

        if k == "e":
            # Activate Shield
            if self.shield_on:
                self.msg = "Shield already active!"
                self.msgt = self.msgmax
            elif self.shield_cd > 0.0:
                self.msg = f"Shield cooling down ({self.shield_cd:.1f}s)"
                self.msgt = self.msgmax
            elif self.shield_charges <= 0:
                self.msg = "No shield charges. Collect the cyan orb!"
                self.msgt = self.msgmax
            else:
                self.shield_charges -= 1
                self.shield_on = True
                self.shield_t = SHIELD_DURATION
                self.msg = f"Shield ON ({SHIELD_DURATION:.0f}s)"
                self.msgt = self.msgmax
            return

        if k == "f":
            # NOVA: clears ALL on-screen obstacles and auto-collects on-screen orbs/powerups.
            if self.nova_charges <= 0:
                self.msg = "No nova charges. Collect the purple orb!"
                self.msgt = self.msgmax
                return

            self.nova_charges -= 1

            Z_MIN, Z_MAX = -260.0, 20.0  # "on screen" band (matches your camera ranges)
            cleared_obs = 0
            collected_pts = 0
            collected_life = 0
            collected_shield = 0
            collected_nova = 0

            # Clear REAL obstacles
            for o in self.obstacles:
                if o.get("on", False) and (not o.get("fake", False)) and (Z_MIN <= o["z"] <= Z_MAX):
                    self.add_explosion(o["x"], o["y"] + max(0.8, o["h"] * 0.6), o["z"], dur=0.60, r0=0.9, r1=5.2)
                    o["on"] = False
                    o["z"] = -700.0
                    cleared_obs += 1

            # Collect ALL point orbs (gold)
            for p in self.points:
                if p.get("on", False) and (Z_MIN <= p["z"] <= Z_MAX):
                    p["on"] = False
                    self.score += 1
                    collected_pts += 1

            # Collect life orb
            if self.bonus.get("on", False) and (Z_MIN <= self.bonus["z"] <= Z_MAX):
                self.bonus["on"] = False
                if self.life < self.maxlife:
                    self.life += 1
                    collected_life = 1

            # Collect shield pickup
            if self.shield_pick.get("on", False) and (Z_MIN <= self.shield_pick["z"] <= Z_MAX):
                self.shield_pick["on"] = False
                before = self.shield_charges
                self.shield_charges = min(SHIELD_MAX_CHARGES, self.shield_charges + 1)
                collected_shield = 1 if self.shield_charges > before else 0

            # Collect nova pickup too (counts as "other powerup")
            if self.nova_pick.get("on", False) and (Z_MIN <= self.nova_pick["z"] <= Z_MAX):
                self.nova_pick["on"] = False
                before = self.nova_charges
                self.nova_charges = min(NOVA_MAX_CHARGES, self.nova_charges + 1)
                collected_nova = 1 if self.nova_charges > before else 0

            self.msg = (
                f"NOVA! Cleared {cleared_obs} obstacles, "
                f"+{collected_pts} score"
                + (", +1 life" if collected_life else "")
                + (", +1 shield" if collected_shield else "")
                + (", +1 nova" if collected_nova else "")
                + "."
            )
            self.msgt = self.msgmax
            return

        if k == "v":
            self.view = (self.view + 1) % 3
            return

        if k == "w":
            self.booston = not self.booston
            self.boost = 2.0 if self.booston else 0.0
            return


    def arrow(self, key, x, y):
        if self.state != GAME_PLAYING:
            return
        if self.pause or self.over:
            return

        step = self.movex * (1.2 if self.booston else 1.0)

        if key == GLUT_KEY_LEFT:
            self.carx = max(self.roadx0 + self.carw / 2.0 + 0.5, self.carx - step)
        elif key == GLUT_KEY_RIGHT:
            self.carx = min(self.roadx1 - self.carw / 2.0 - 0.5, self.carx + step)

        if self.view == 1:
            if key == GLUT_KEY_UP:
                self.camheight += 0.5
            elif key == GLUT_KEY_DOWN:
                self.camheight = max(1.0, self.camheight - 0.5)


    def mouse(self, button, state, x, y):
        if state != GLUT_DOWN:
            return

        # Menu clicks: left click = start, right click = controls
        if self.state == GAME_MENU:
            if button == GLUT_LEFT_BUTTON:
                self.reset()
                self.state = GAME_PLAYING
            elif button == GLUT_RIGHT_BUTTON:
                self.state = GAME_CONTROLS
            return

        if self.state == GAME_CONTROLS:
            if button == GLUT_RIGHT_BUTTON:
                self.state = GAME_MENU
            return

        if self.state == GAME_OVER:
            if button == GLUT_RIGHT_BUTTON:
                self.reset()
                self.state = GAME_PLAYING
            elif button == GLUT_LEFT_BUTTON:
                self.state = GAME_MENU
            return

        # Gameplay mouse
        if button == GLUT_LEFT_BUTTON:
            if not self.over:
                self.pause = not self.pause
        elif button == GLUT_RIGHT_BUTTON:
            if self.over:
                self.reset()
                self.state = GAME_PLAYING
    def size(self, w, h):
        if h <= 0:
            h = 1
        self.w = w
        self.h = h


    def reset(self):
        self.score = 0
        self.life = self.maxlife
        self.pause = False
        self.over = False
        self.msg = ""
        self.msgt = 0

        # Clear VFX
        self.explosions = []


        # Reset shield / power-ups
        self.shield_on = False
        self.shield_t = 0.0
        self.shield_cd = 0.0
        self.shield_charges = 0
        self.nova_charges = 0
        self.level = 0
        self.base = 1.0
        self.boost = 0.0
        self.booston = False
        self.want = 6

        self.carx = (self.roadx0 + self.roadx1) / 2.0

        self.dash = [i * 15.0 for i in range(10)]
        self.posts = [i * 8.0 for i in range(80)]
        self.lamps = [i * 35.0 for i in range(14)]
        self.spawnsigns()
        self.spawntrees()

        self.spawnpoints()
        self.spawnbonus()
        self.spawnshield()
        self.spawnnova()
        self.spawnobstacles()
        self.last = None

    def run(self):
        glutInit()
        glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
        glutInitWindowSize(self.w, self.h)
        glutInitWindowPosition(100, 80)
        glutCreateWindow(b"3D Driving Game")

        glutDisplayFunc(lambda: self.draw())
        glutKeyboardFunc(lambda k, x, y: self.key(k, x, y))
        glutSpecialFunc(lambda k, x, y: self.arrow(k, x, y))
        glutMouseFunc(lambda b, s, x, y: self.mouse(b, s, x, y))
        glutIdleFunc(lambda: self.idle())

        glutReshapeFunc(lambda w, h: self.size(w, h))

        glutMainLoop()


if __name__ == "__main__":
    Game().run()