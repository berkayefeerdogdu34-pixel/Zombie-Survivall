import array
import json
import math
import os
import random
import pygame

# -----------------------------------------------------------------------------
# 1. BAŞLATMA VE VERİ YÖNETİMİ
# -----------------------------------------------------------------------------
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.init()

info = pygame.display.Info()
BASE_WIDTH, BASE_HEIGHT = info.current_w, info.current_h
MAP_WIDTH, MAP_HEIGHT = 8000, 8000

screen = pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("ULTIMATE ZOMBIE SURVIVAL: EXTREME REALISM")
clock = pygame.time.Clock()

USER_DATA_FILE = "users.json"


def load_user_data():
    if not os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_user_data(data):
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


user_db = load_user_data()
current_user = None

# GELİŞMİŞ GÖLGELİ VE NEON RENK PALETİ
BG_COLOR = (6, 8, 12)
ROAD_COLOR = (14, 16, 22)
BUILDING_COLOR = (18, 22, 30)
BUILDING_WALL = (45, 55, 70)
CONCRETE_COLOR = (30, 35, 45)
WHITE = (245, 245, 245)
RED = (230, 35, 35)
BLOOD_RED = (110, 6, 10)
GREEN = (35, 220, 80)
YELLOW = (255, 210, 40)
BRASS = (215, 175, 45)
BLACK = (0, 0, 0)
GRAY = (120, 120, 130)
DARK_GRAY = (30, 35, 45)
PURPLE = (160, 35, 235)
CYAN = (0, 220, 255)
ACID_GREEN = (85, 250, 25)
ORANGE = (250, 140, 0)
BUTTON_COLOR = (16, 20, 30)
BUTTON_HOVER = (35, 45, 65)

font_title = pygame.font.SysFont("Impact", 60)
font_large = pygame.font.SysFont("Arial", 30, bold=True)
font_med = pygame.font.SysFont("Arial", 18, bold=True)
font_small = pygame.font.SysFont("Arial", 13, bold=True)


# -----------------------------------------------------------------------------
# 2. METİN GİRDİ KUTUSU
# -----------------------------------------------------------------------------
class InputBox:

    def __init__(self, x, y, w, h, is_password=False, placeholder=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = DARK_GRAY
        self.text = ""
        self.active = False
        self.is_password = is_password
        self.placeholder = placeholder

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self.color = CYAN if self.active else DARK_GRAY
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key not in (pygame.K_RETURN, pygame.K_TAB, pygame.K_ESCAPE):
                if len(self.text) < 18:
                    self.text += event.unicode

    def draw(self, surface):
        pygame.draw.rect(surface, BUTTON_COLOR, self.rect, border_radius=6)
        pygame.draw.rect(surface, self.color, self.rect, 2, border_radius=6)
        display_str = "*" * len(self.text) if self.is_password else self.text
        if not self.text and not self.active:
            txt_surface = font_med.render(self.placeholder, True, GRAY)
        else:
            txt_surface = font_med.render(display_str, True, WHITE)
        surface.blit(
            txt_surface,
            (
                self.rect.x + 10,
                self.rect.y
                + (self.rect.height - txt_surface.get_height()) // 2,
            ),
        )


# -----------------------------------------------------------------------------
# 3. SES ÜRETİCİ
# -----------------------------------------------------------------------------
sfx_volume = 0.8
master_volume = 0.7


def create_sound(samples):
    buf = array.array("h", [int(max(-32767, min(32767, s))) for s in samples])
    return pygame.mixer.Sound(buffer=buf)


def generate_gunshot(pitch=1.0, duration=0.15, noise_weight=0.2):
    samples = []
    n_samples = int(44100 * duration)
    for i in range(n_samples):
        t = i / 44100.0
        decay = math.exp(-t * (35 / pitch))
        bass = math.sin(2 * math.pi * (60 * pitch) * t) * 0.7
        noise = random.uniform(-noise_weight, noise_weight)
        val = (bass + noise) * decay * 30000
        samples.append(int(val))
        samples.append(int(val))
    snd = create_sound(samples)
    snd.set_volume(sfx_volume * master_volume)
    return snd


def generate_explosion_sound():
    samples = []
    n_samples = int(44100 * 0.4)
    for i in range(n_samples):
        t = i / 44100.0
        decay = math.exp(-t * 10)
        noise = random.uniform(-0.9, 0.9)
        bass = math.sin(2 * math.pi * 35 * t)
        val = (noise * 0.75 + bass * 0.25) * decay * 32000
        samples.append(int(val))
        samples.append(int(val))
    snd = create_sound(samples)
    snd.set_volume(sfx_volume * master_volume)
    return snd


snd_pistol = generate_gunshot(1.3, 0.12, 0.15)
snd_rifle = generate_gunshot(1.0, 0.15, 0.25)
snd_shotgun = generate_gunshot(0.6, 0.25, 0.4)
snd_sniper = generate_gunshot(0.4, 0.35, 0.1)
snd_explosion = generate_explosion_sound()

# -----------------------------------------------------------------------------
# 4. SİLAHLAR, KARAKTERLER VE PERKLER
# -----------------------------------------------------------------------------
CHARACTERS = {
    "Commando": {
        "desc": "Taktiksel Piyade. Yüksek hız, dengeli hasar ve hassas vuruş.",
        "hp_mult": 1.0,
        "speed_mult": 1.05,
        "dmg_mult": 1.15,
        "badge": "ELİT",
        "color": (40, 110, 180),
    },
    "Scout": {
        "desc": "Öncü Gözcü. Çarpıcı hız, hafif yapı ve seri hareket kabiliyeti.",
        "hp_mult": 0.8,
        "speed_mult": 1.35,
        "dmg_mult": 1.0,
        "badge": "HIZLI",
        "color": (30, 170, 90),
    },
    "Juggernaut": {
        "desc": "Zırhlı Dev. Maksimum dayanıklılık, durdurulamaz tank gücü.",
        "hp_mult": 2.2,
        "speed_mult": 0.80,
        "dmg_mult": 1.05,
        "badge": "TANK",
        "color": (160, 50, 50),
    },
}

WEAPONS = {
    "Pistol": {
        "damage": 25,
        "fire_rate": 10,
        "clip_size": 12,
        "total_ammo": 120,
        "reload_time": 40,
        "spread": 0.02,
        "cost": 0,
        "ammo_cost": 15,
        "owned": True,
        "sound": snd_pistol,
        "type": "single",
        "info": "Temel silah. Seri doldurulur, yakın mesafe için ideal.",
    },
    "SMG": {
        "damage": 18,
        "fire_rate": 4,
        "clip_size": 35,
        "total_ammo": 210,
        "reload_time": 55,
        "spread": 0.07,
        "cost": 450,
        "ammo_cost": 40,
        "owned": False,
        "sound": snd_pistol,
        "type": "auto",
        "info": "Yüksek atış hızına sahip hafif makineli tüfek. Kalabalık temizler.",
    },
    "Shotgun": {
        "damage": 20,
        "fire_rate": 32,
        "clip_size": 8,
        "total_ammo": 48,
        "reload_time": 80,
        "spread": 0.18,
        "cost": 900,
        "ammo_cost": 60,
        "owned": False,
        "sound": snd_shotgun,
        "type": "single",
        "pellets": 8,
        "info": "Geniş açılı saçma atar. Çoklu hasar ve yüksek yakın mesafe gücü.",
    },
    "Rifle": {
        "damage": 35,
        "fire_rate": 7,
        "clip_size": 30,
        "total_ammo": 180,
        "reload_time": 70,
        "spread": 0.04,
        "cost": 1400,
        "ammo_cost": 75,
        "owned": False,
        "sound": snd_rifle,
        "type": "auto",
        "info": "Orta/uzak mesafe piyade tüfeği. Dengeli hasar ve menzil.",
    },
    "Sniper": {
        "damage": 170,
        "fire_rate": 45,
        "clip_size": 5,
        "total_ammo": 30,
        "reload_time": 90,
        "spread": 0.001,
        "cost": 2200,
        "ammo_cost": 120,
        "owned": False,
        "sound": snd_sniper,
        "type": "single",
        "info": "Tek atışta devasa hasar. Uzaktaki tehlikeleri anında yok eder.",
    },
}

PERKS = {
    "Quick Hands": {
        "cost": 600,
        "owned": False,
        "desc": "Dolum hızını %40 artırır.",
    },
    "Vampire": {
        "cost": 1000,
        "owned": False,
        "desc": "Öldürülen her zombiden az miktarda can yeniler.",
    },
    "Scavenger": {
        "cost": 750,
        "owned": False,
        "desc": "Zombilerden daha fazla para düşmesini sağlar.",
    },
}


class Camera:

    def __init__(self):
        self.x, self.y, self.shake_amount = 0, 0, 0

    def add_shake(self, amount):
        self.shake_amount = min(35, self.shake_amount + amount)

    def update(self, target, screen_w, screen_h):
        self.x = -target.x + screen_w // 2
        self.y = -target.y + screen_h // 2
        self.x = min(0, max(-(MAP_WIDTH - screen_w), self.x))
        self.y = min(0, max(-(MAP_HEIGHT - screen_h), self.y))
        if self.shake_amount > 0:
            self.x += random.randint(
                -int(self.shake_amount), int(self.shake_amount)
            )
            self.y += random.randint(
                -int(self.shake_amount), int(self.shake_amount)
            )
            self.shake_amount *= 0.85
            if self.shake_amount < 0.5:
                self.shake_amount = 0

    def apply_pos(self, pos):
        return (pos[0] + self.x, pos[1] + self.y)

    def apply_rect(self, rect):
        return rect.move(self.x, self.y)


class FloatingText:

    def __init__(self, x, y, text, color=RED):
        self.x, self.y, self.text, self.color = x, y, str(text), color
        self.lifetime = 35

    def update(self):
        self.y -= 1.2
        self.lifetime -= 1

    def draw(self, surface, camera):
        px, py = camera.apply_pos((self.x, self.y))
        surf = font_small.render(self.text, True, self.color)
        surface.blit(surf, (px, py))


class ShellCasing:

    def __init__(self, x, y, angle):
        self.x, self.y = x, y
        e_angle = angle + math.pi / 2 + random.uniform(-0.3, 0.3)
        sp = random.uniform(3, 7)
        self.dx, self.dy = math.cos(e_angle) * sp, math.sin(e_angle) * sp
        self.rotation = random.uniform(0, 360)
        self.rot_speed = random.uniform(-20, 20)
        self.lifetime = 140

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.dx *= 0.86
        self.dy *= 0.86
        self.rotation += self.rot_speed
        self.lifetime -= 1

    def draw(self, surface, camera):
        if self.lifetime <= 0:
            return
        px, py = camera.apply_pos((self.x, self.y))
        c_surf = pygame.Surface((6, 3), pygame.SRCALPHA)
        c_surf.fill(BRASS)
        pygame.draw.rect(c_surf, (150, 110, 15), (0, 0, 2, 3))
        rot_s = pygame.transform.rotate(c_surf, self.rotation)
        surface.blit(
            rot_s,
            (px - rot_s.get_width() // 2, py - rot_s.get_height() // 2),
        )


class Particle:

    def __init__(self, x, y, color, speed=None, size=3, lifetime=25):
        self.x, self.y, self.color, self.size = x, y, color, size
        angle = random.uniform(0, math.pi * 2)
        sp = speed if speed is not None else random.uniform(2, 7)
        self.dx, self.dy = math.cos(angle) * sp, math.sin(angle) * sp
        self.lifetime = self.max_life = lifetime

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.lifetime -= 1

    def draw(self, surface, camera):
        px, py = camera.apply_pos((self.x, self.y))
        pygame.draw.circle(
            surface,
            self.color,
            (int(px), int(py)),
            max(1, int(self.size * (self.lifetime / self.max_life))),
        )


class BloodDecal:

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.radius = random.randint(14, 30)
        self.points = [
            (
                x + random.randint(-self.radius, self.radius),
                y + random.randint(-self.radius, self.radius),
            )
            for _ in range(6)
        ]

    def draw(self, surface, camera):
        px, py = camera.apply_pos((self.x, self.y))
        pygame.draw.circle(surface, BLOOD_RED, (int(px), int(py)), self.radius)
        for pt in self.points:
            ppx, ppy = camera.apply_pos(pt)
            pygame.draw.circle(
                surface, BLOOD_RED, (int(ppx), int(ppy)), max(3, self.radius // 3)
            )


class MedKit:

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.radius = 12
        self.heal_amount = 35

    def draw(self, surface, camera):
        px, py = camera.apply_pos((self.x, self.y))
        pygame.draw.circle(surface, WHITE, (int(px), int(py)), self.radius)
        pygame.draw.circle(surface, RED, (int(px), int(py)), self.radius - 2)
        pygame.draw.rect(surface, WHITE, (px - 2, py - 6, 4, 12))
        pygame.draw.rect(surface, WHITE, (px - 6, py - 2, 12, 4))


class AmmoBox:

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.radius = 12

    def draw(self, surface, camera):
        px, py = camera.apply_pos((self.x, self.y))
        pygame.draw.rect(surface, (80, 70, 40), (px - 10, py - 8, 20, 16), border_radius=3)
        pygame.draw.rect(surface, BRASS, (px - 8, py - 6, 16, 12), 2, border_radius=2)
        pygame.draw.line(surface, YELLOW, (px - 6, py), (px + 6, py), 2)


class Grenade:
    def __init__(self, x, y, target_x, target_y):
        self.x, self.y = x, y
        self.start_x, self.start_y = x, y
        self.target_x, self.target_y = target_x, target_y
        self.distance = math.hypot(target_x - x, target_y - y)
        self.angle = math.atan2(target_y - y, target_x - x)
        self.speed = 12.0
        self.timer = 60  # 1 saniye sonra patlar

    def update(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.timer -= 1

    def draw(self, surface, camera):
        px, py = camera.apply_pos((self.x, self.y))
        pygame.draw.circle(surface, BLACK, (int(px), int(py)), 6)
        pygame.draw.circle(surface, RED, (int(px), int(py)), 3)


class LandMine:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.radius = 14
        self.active = True

    def draw(self, surface, camera):
        if not self.active:
            return
        px, py = camera.apply_pos((self.x, self.y))
        pygame.draw.circle(surface, DARK_GRAY, (int(px), int(py)), self.radius)
        pygame.draw.circle(surface, RED, (int(px), int(py)), 5)


def draw_detailed_weapon(surface, px, py, angle, w_type, muzzle_flash):
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    perp_x, perp_y = -sin_a, cos_a

    def to_screen(fwd, side):
        return (
            px + cos_a * fwd + perp_x * side,
            py + sin_a * fwd + perp_y * side,
        )

    if w_type == "Pistol":
        p1 = to_screen(12, 3)
        p2 = to_screen(26, 3)
        p3 = to_screen(26, -3)
        p4 = to_screen(12, -3)
        pygame.draw.polygon(surface, (45, 50, 60), [p1, p2, p3, p4])
        pygame.draw.polygon(surface, (15, 15, 20), [p1, p2, p3, p4], 1)
        pygame.draw.line(surface, DARK_GRAY, to_screen(12, 0), to_screen(24, 0), 2)
        laser_end = to_screen(500, 0)
        pygame.draw.line(surface, (255, 0, 0, 120), to_screen(26, 0), laser_end, 1)
    elif w_type == "SMG":
        p1 = to_screen(10, 5)
        p2 = to_screen(30, 5)
        p3 = to_screen(30, -5)
        p4 = to_screen(10, -5)
        pygame.draw.polygon(surface, (30, 35, 45), [p1, p2, p3, p4])
        pygame.draw.line(surface, BLACK, to_screen(30, 0), to_screen(36, 0), 3)
    elif w_type == "Shotgun":
        b1 = to_screen(8, 5)
        b2 = to_screen(38, 4)
        b3 = to_screen(38, -4)
        b4 = to_screen(8, -5)
        pygame.draw.polygon(surface, (95, 50, 20), [b1, b2, b3, b4])
        pygame.draw.line(surface, (70, 75, 85), to_screen(22, 0), to_screen(42, 0), 5)
    elif w_type == "Rifle":
        p1 = to_screen(8, 6)
        p2 = to_screen(36, 5)
        p3 = to_screen(36, -5)
        p4 = to_screen(8, -6)
        pygame.draw.polygon(surface, (40, 45, 50), [p1, p2, p3, p4])
        pygame.draw.line(surface, (15, 15, 15), to_screen(36, 0), to_screen(46, 0), 4)
    elif w_type == "Sniper":
        p1 = to_screen(6, 6)
        p2 = to_screen(40, 4)
        p3 = to_screen(40, -4)
        p4 = to_screen(6, -6)
        pygame.draw.polygon(surface, (25, 30, 35), [p1, p2, p3, p4])
        pygame.draw.line(surface, (10, 10, 10), to_screen(40, 0), to_screen(58, 0), 5)
        sc1 = to_screen(16, -8)
        sc2 = to_screen(30, -8)
        pygame.draw.line(surface, (10, 10, 10), sc1, sc2, 6)
        pygame.draw.circle(surface, CYAN, (int(sc2[0]), int(sc2[1])), 3)

    if muzzle_flash > 0:
        tip_x, tip_y = to_screen(
            48 if w_type in ["Rifle", "Sniper"] else 32, 0
        )
        pygame.draw.circle(
            surface, YELLOW, (int(tip_x), int(tip_y)), random.randint(12, 18)
        )
        pygame.draw.circle(
            surface, WHITE, (int(tip_x), int(tip_y)), random.randint(5, 9)
        )


class Player:

    def __init__(self, x, y, char_type="Commando"):
        self.x, self.y, self.radius = x, y, 20
        self.char_type = char_type
        stats = CHARACTERS[char_type]
        self.base_speed = 5.2 * stats["speed_mult"]
        self.max_health = int(100 * stats["hp_mult"])
        self.health = self.max_health
        self.dmg_mult = stats["dmg_mult"]
        self.money = 600
        self.angle = 0
        self.current_weapon = "Pistol"
        self.ammo = {w: WEAPONS[w]["clip_size"] for w in WEAPONS}
        self.total_ammo = {w: WEAPONS[w]["total_ammo"] for w in WEAPONS}
        self.grenades, self.mines, self.barricades = 6, 5, 5
        self.shoot_cooldown, self.reloading, self.reload_timer, self.muzzle_flash = (
            0,
            False,
            0,
            0,
        )
        self.dash_cooldown, self.is_dashing, self.dash_timer = 0, False, 0

    def get_rect(self):
        return pygame.Rect(
            self.x - self.radius,
            self.y - self.radius,
            self.radius * 2,
            self.radius * 2,
        )

    def take_damage(self, amount):
        self.health -= amount

    def move(self, keys, obstacles, barricades):
        current_speed = self.base_speed * 2.2 if self.is_dashing else self.base_speed
        dx, dy = 0, 0
        if keys[pygame.K_w]:
            dy -= current_speed
        if keys[pygame.K_s]:
            dy += current_speed
        if keys[pygame.K_a]:
            dx -= current_speed
        if keys[pygame.K_d]:
            dx += current_speed
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        self.x += dx
        self.x = max(self.radius, min(MAP_WIDTH - self.radius, self.x))
        p_rect = self.get_rect()
        for obs in obstacles + [b for b in barricades if b.active]:
            if obs.rect.colliderect(p_rect):
                if dx > 0:
                    self.x = obs.rect.left - self.radius
                elif dx < 0:
                    self.x = obs.rect.right + self.radius

        self.y += dy
        self.y = max(self.radius, min(MAP_HEIGHT - self.radius, self.y))
        p_rect = self.get_rect()
        for obs in obstacles + [b for b in barricades if b.active]:
            if obs.rect.colliderect(p_rect):
                if dy > 0:
                    self.y = obs.rect.top - self.radius
                elif dy < 0:
                    self.y = obs.rect.bottom + self.radius

    def update(self):
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1
        if self.is_dashing:
            self.dash_timer -= 1
            if self.dash_timer <= 0:
                self.is_dashing = False
        if self.reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                self.reloading = False
                w_info = WEAPONS[self.current_weapon]
                needed = w_info["clip_size"] - self.ammo[self.current_weapon]
                available = min(needed, self.total_ammo[self.current_weapon])
                self.ammo[self.current_weapon] += available
                self.total_ammo[self.current_weapon] -= available

    def start_dash(self):
        if self.dash_cooldown <= 0 and not self.is_dashing:
            self.is_dashing = True
            self.dash_timer = 12
            self.dash_cooldown = 70

    def reload(self):
        w_info = WEAPONS[self.current_weapon]
        if (
            not self.reloading
            and self.ammo[self.current_weapon] < w_info["clip_size"]
            and self.total_ammo[self.current_weapon] > 0
        ):
            self.reloading = True
            r_time = w_info["reload_time"]
            if PERKS["Quick Hands"]["owned"]:
                r_time = int(r_time * 0.6)
            self.reload_timer = r_time

    def draw(self, surface, camera, mouse_screen_pos):
        px, py = camera.apply_pos((self.x, self.y))
        self.angle = math.atan2(
            mouse_screen_pos[1] - py, mouse_screen_pos[0] - px
        )

        shadow_surf = pygame.Surface(
            (self.radius * 2 + 16, self.radius * 2 + 16), pygame.SRCALPHA
        )
        pygame.draw.ellipse(
            shadow_surf,
            (0, 0, 0, 160),
            (0, 0, self.radius * 2 + 12, self.radius * 2 + 4),
        )
        surface.blit(shadow_surf, (px - self.radius - 6, py - self.radius + 6))

        c_data = CHARACTERS.get(self.char_type, CHARACTERS["Commando"])
        base_color = c_data["color"]

        pygame.draw.circle(
            surface, (base_color[0] // 3, base_color[1] // 3, base_color[2] // 3), (int(px), int(py)), self.radius + 3
        )
        pygame.draw.circle(surface, base_color, (int(px), int(py)), self.radius)
        pygame.draw.circle(surface, (15, 20, 30), (int(px), int(py)), self.radius - 4)

        cos_a, sin_a = math.cos(self.angle), math.sin(self.angle)
        bx_back = px - cos_a * 8
        by_back = py - sin_a * 8
        pygame.draw.circle(surface, (40, 45, 55), (int(bx_back), int(by_back)), 7)
        pygame.draw.circle(surface, (20, 25, 35), (int(bx_back), int(by_back)), 4)

        shoulder_left = (px - sin_a * 11, py + cos_a * 11)
        shoulder_right = (px + sin_a * 11, py - cos_a * 11)
        pygame.draw.circle(surface, (base_color[0] + 35, base_color[1] + 35, base_color[2] + 35), (int(shoulder_left[0]), int(shoulder_left[1])), 5)
        pygame.draw.circle(surface, (base_color[0] + 35, base_color[1] + 35, base_color[2] + 35), (int(shoulder_right[0]), int(shoulder_right[1])), 5)

        visor_x = px + cos_a * 9
        visor_y = py + sin_a * 9
        pygame.draw.circle(surface, CYAN, (int(visor_x), int(visor_y)), 3)
        pygame.draw.circle(surface, WHITE, (int(visor_x + cos_a*1), int(visor_y + sin_a*1)), 1)

        draw_detailed_weapon(
            surface, px, py, self.angle, self.current_weapon, self.muzzle_flash
        )
        if self.muzzle_flash > 0:
            self.muzzle_flash -= 1

        # Şarjör dolum göstergesi dairesi
        if self.reloading:
            w_info = WEAPONS[self.current_weapon]
            r_time = w_info["reload_time"]
            if PERKS["Quick Hands"]["owned"]:
                r_time = int(r_time * 0.6)
            progress = 1.0 - (self.reload_timer / r_time)
            pygame.draw.arc(surface, CYAN, (px - 25, py - 25, 50, 50), 0, math.pi * 2 * progress, 3)


class Zombie:

    def __init__(self, x, y, z_type="normal"):
        self.x, self.y, self.type, self.angle, self.attack_cooldown = (
            x,
            y,
            z_type,
            0,
            0,
        )
        self.knockback_x, self.knockback_y = 0.0, 0.0

        if z_type == "runner":
            self.radius, self.speed, self.health, self.color, self.reward, self.damage = (
                16,
                random.uniform(4.6, 5.4),
                55,
                (230, 40, 40),
                40,
                10,
            )
        elif z_type == "tank":
            self.radius, self.speed, self.health, self.color, self.reward, self.damage = (
                34,
                random.uniform(1.3, 1.7),
                350,
                (35, 70, 50),
                90,
                30,
            )
        elif z_type == "spitter":
            self.radius, self.speed, self.health, self.color, self.reward, self.damage = (
                18,
                2.6,
                80,
                ACID_GREEN,
                55,
                15,
            )
        elif z_type == "exploder":
            self.radius, self.speed, self.health, self.color, self.reward, self.damage = (
                23,
                3.0,
                70,
                (255, 120, 10),
                70,
                80,
            )
        elif z_type == "boss":
            self.radius, self.speed, self.health, self.color, self.reward, self.damage = (
                50,
                1.7,
                1400,
                PURPLE,
                700,
                50,
            )
        else:
            self.radius, self.speed, self.health, self.color, self.reward, self.damage = (
                20,
                random.uniform(2.4, 3.2),
                100,
                (55, 115, 60),
                30,
                15,
            )
        self.max_health = self.health

    def get_rect(self):
        return pygame.Rect(
            self.x - self.radius,
            self.y - self.radius,
            self.radius * 2,
            self.radius * 2,
        )

    def apply_knockback(self, angle, force):
        self.knockback_x += math.cos(angle) * force
        self.knockback_y += math.sin(angle) * force

    def update(self, player, obstacles, barricades, acid_projectiles):
        if abs(self.knockback_x) > 0.1 or abs(self.knockback_y) > 0.1:
            self.x += self.knockback_x
            self.y += self.knockback_y
            self.knockback_x *= 0.8
            self.knockback_y *= 0.8
            return

        rel_x, rel_y = player.x - self.x, player.y - self.y
        dist = math.hypot(rel_x, rel_y)
        self.angle = math.atan2(rel_y, rel_x)
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        if self.type == "spitter" and dist < 550 and self.attack_cooldown <= 0:
            self.attack_cooldown = 90
            acid_projectiles.append(AcidProjectile(self.x, self.y, player.x, player.y))
            return

        dx, dy = math.cos(self.angle) * self.speed, math.sin(self.angle) * self.speed
        self.x += dx
        z_rect = self.get_rect()
        for obs in obstacles + [b for b in barricades if b.active]:
            if obs.rect.colliderect(z_rect):
                if isinstance(obs, Barricade):
                    obs.health -= 0.8
                if dx > 0:
                    self.x = obs.rect.left - self.radius
                elif dx < 0:
                    self.x = obs.rect.right + self.radius

        self.y += dy
        z_rect = self.get_rect()
        for obs in obstacles + [b for b in barricades if b.active]:
            if obs.rect.colliderect(z_rect):
                if isinstance(obs, Barricade):
                    obs.health -= 0.8
                if dy > 0:
                    self.y = obs.rect.top - self.radius
                elif dy < 0:
                    self.y = obs.rect.bottom + self.radius

    def draw(self, surface, camera):
        px, py = camera.apply_pos((self.x, self.y))
        
        pygame.draw.circle(surface, (8, 10, 14), (int(px + 4), int(py + 4)), self.radius + 3)
        pygame.draw.circle(surface, (25, 12, 15), (int(px), int(py)), self.radius + 2)
        pygame.draw.circle(surface, self.color, (int(px), int(py)), self.radius)
        
        cos_a, sin_a = math.cos(self.angle), math.sin(self.angle)
        eye1 = (px + cos_a * (self.radius - 6) - sin_a * 5, py + sin_a * (self.radius - 6) + cos_a * 5)
        eye2 = (px + cos_a * (self.radius - 6) + sin_a * 5, py + sin_a * (self.radius - 6) - cos_a * 5)
        
        pygame.draw.circle(surface, YELLOW, (int(eye1[0]), int(eye1[1])), 3)
        pygame.draw.circle(surface, YELLOW, (int(eye2[0]), int(eye2[1])), 3)
        pygame.draw.circle(surface, RED, (int(eye1[0]), int(eye1[1])), 1)
        pygame.draw.circle(surface, RED, (int(eye2[0]), int(eye2[1])), 1)

        if self.health < self.max_health:
            bar_w = self.radius * 2
            bar_h = 4
            hp_pct = max(0, self.health / self.max_health)
            pygame.draw.rect(surface, BLACK, (px - bar_w//2, py - self.radius - 10, bar_w, bar_h))
            pygame.draw.rect(surface, RED, (px - bar_w//2, py - self.radius - 10, int(bar_w * hp_pct), bar_h))


class AcidProjectile:

    def __init__(self, x, y, tx, ty):
        self.x, self.y = x, y
        angle = math.atan2(ty - y, tx - x)
        self.dx, self.dy = math.cos(angle) * 8.0, math.sin(angle) * 8.0
        self.lifetime = 90

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.lifetime -= 1

    def draw(self, surface, camera):
        px, py = camera.apply_pos((self.x, self.y))
        pygame.draw.circle(surface, ACID_GREEN, (int(px), int(py)), 7)


class Bullet:

    def __init__(self, x, y, angle, damage):
        self.x, self.y = x, y
        self.angle = angle
        self.dx, self.dy = math.cos(angle) * 26, math.sin(angle) * 26
        self.damage, self.lifetime = damage, 45

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.lifetime -= 1

    def draw(self, surface, camera):
        px, py = camera.apply_pos((self.x, self.y))
        pygame.draw.line(
            surface,
            YELLOW,
            (px, py),
            (px - self.dx * 0.5, py - self.dy * 0.5),
            3,
        )


class Barricade:

    def __init__(self, x, y):
        self.rect = pygame.Rect(x - 28, y - 28, 56, 56)
        self.health = self.max_health = 250
        self.active = True

    def draw(self, surface, camera):
        if not self.active:
            return
        cam_rect = camera.apply_rect(self.rect)
        pygame.draw.rect(surface, (130, 85, 45), cam_rect)
        pygame.draw.rect(surface, (55, 35, 15), cam_rect, 3)


class Obstacle:

    def __init__(self, x, y, w, h, obs_type="building"):
        self.rect = pygame.Rect(x, y, w, h)
        self.type = obs_type

    def draw(self, surface, camera):
        cam_rect = camera.apply_rect(self.rect)
        if self.type == "building":
            pygame.draw.rect(surface, BUILDING_COLOR, cam_rect)
            pygame.draw.rect(surface, BUILDING_WALL, cam_rect, 5)
        elif self.type == "cover":
            pygame.draw.rect(surface, CONCRETE_COLOR, cam_rect)
            pygame.draw.rect(surface, DARK_GRAY, cam_rect, 3)


def build_expanded_map():
    obstacles = []
    for bx in range(1000, MAP_WIDTH - 1000, 1200):
        for by in range(1000, MAP_HEIGHT - 1000, 1200):
            obstacles.append(Obstacle(bx, by, 700, 700, "building"))
            obstacles.append(Obstacle(bx - 120, by - 120, 90, 40, "cover"))
            obstacles.append(Obstacle(bx + 730, by + 400, 40, 90, "cover"))
    return obstacles


def render_dynamic_atmosphere(
    surface, camera, player, screen_w, screen_h, is_night
):
    if not is_night:
        return
    night_alpha = 230
    darkness = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
    darkness.fill((4, 6, 10, night_alpha))
    px, py = camera.apply_pos((player.x, player.y))
    sight_radius = 230
    for r in range(sight_radius, 0, -10):
        alpha = int(night_alpha * (r / sight_radius) ** 2.2)
        pygame.draw.circle(darkness, (4, 6, 10, alpha), (int(px), int(py)), r)
    surface.blit(darkness, (0, 0))


def draw_minimap(surface, player, zombies, map_w, map_h, screen_w):
    mm_size = 140
    mm_x, mm_y = screen_w - mm_size - 20, 20
    mm_surf = pygame.Surface((mm_size, mm_size))
    mm_surf.set_alpha(200)
    mm_surf.fill((10, 14, 22))
    pygame.draw.rect(mm_surf, CYAN, (0, 0, mm_size, mm_size), 2)

    m_px = int((player.x / map_w) * mm_size)
    m_py = int((player.y / map_h) * mm_size)
    pygame.draw.circle(mm_surf, GREEN, (m_px, m_py), 3)

    for z in zombies:
        m_zx = int((z.x / map_w) * mm_size)
        m_zy = int((z.y / map_h) * mm_size)
        pygame.draw.circle(mm_surf, RED, (m_zx, m_zy), 2)

    surface.blit(mm_surf, (mm_x, mm_y))


def reset_game(selected_char):
    for w in WEAPONS:
        if w != "Pistol":
            WEAPONS[w]["owned"] = False
    for p in PERKS:
        PERKS[p]["owned"] = False
    player = Player(MAP_WIDTH // 2, MAP_HEIGHT // 2, selected_char)
    camera = Camera()
    obstacles = build_expanded_map()
    # Hata düzeltildi: Tam olarak 15 eleman döndürülüyor ve eşitleniyor.
    return (
        player,
        camera,
        obstacles,
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )


def draw_ui_button(surface, text, rect, mouse_pos):
    hover = rect.collidepoint(mouse_pos)
    pygame.draw.rect(
        surface,
        BUTTON_HOVER if hover else BUTTON_COLOR,
        rect,
        border_radius=8,
    )
    pygame.draw.rect(surface, CYAN if hover else WHITE, rect, 2, border_radius=8)
    t_surf = font_med.render(text, True, WHITE)
    surface.blit(
        t_surf,
        (
            rect.centerx - t_surf.get_width() // 2,
            rect.centery - t_surf.get_height() // 2,
        ),
    )
    return hover


def update_user_stats(username, cur_kills):
    if not username or username not in user_db:
        return
    user_db[username]["total_kills"] = (
        user_db[username].get("total_kills", 0) + cur_kills
    )
    save_user_data(user_db)


# -----------------------------------------------------------------------------
# 5. ANA OYUN DÖNGÜSÜ VE MENÜLER
# -----------------------------------------------------------------------------
def main():
    global current_user, user_db
    game_state = "LOGIN"
    selected_char = "Commando"
    shop_tab = "GUNS"

    username_box = InputBox(
        BASE_WIDTH // 2 - 150, BASE_HEIGHT // 2 - 60, 300, 45, False, "Kullanıcı Adı"
    )
    password_box = InputBox(
        BASE_WIDTH // 2 - 150, BASE_HEIGHT // 2 + 10, 300, 45, True, "Şifre"
    )

    player, camera, obstacles = None, None, None
    bullets, zombies, particles, blood_pool, float_texts, casings = (
        [],
        [],
        [],
        [],
        [],
        [],
    )
    barricades, acid_projectiles, medkits, ammoboxes, grenades, landmines = [], [], [], [], [], []
    
    is_night = True
    night_timer = 120 * 60
    spawn_timer = 0
    kills = 0

    while True:
        screen.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            if game_state == "LOGIN":
                username_box.handle_event(event)
                password_box.handle_event(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    uname = username_box.text.strip()
                    pwd = password_box.text.strip()
                    if uname and pwd:
                        if uname not in user_db:
                            user_db[uname] = {
                                "password": pwd,
                                "total_kills": 0,
                            }
                            save_user_data(user_db)
                        if user_db[uname]["password"] == pwd:
                            current_user = uname
                            game_state = "CHAR_SELECT"

            elif game_state == "CHAR_SELECT":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    comm_rect = pygame.Rect(
                        BASE_WIDTH // 2 - 380, BASE_HEIGHT // 2 - 100, 230, 200
                    )
                    scout_rect = pygame.Rect(
                        BASE_WIDTH // 2 - 115, BASE_HEIGHT // 2 - 100, 230, 200
                    )
                    jugg_rect = pygame.Rect(
                        BASE_WIDTH // 2 + 150, BASE_HEIGHT // 2 - 100, 230, 200
                    )
                    
                    def apply_selection(c_type):
                        nonlocal player, camera, obstacles, bullets, zombies, particles, blood_pool, float_texts, casings, barricades, acid_projectiles, medkits, ammoboxes, grenades, landmines
                        (
                            player,
                            camera,
                            obstacles,
                            bullets,
                            zombies,
                            particles,
                            blood_pool,
                            float_texts,
                            casings,
                            barricades,
                            acid_projectiles,
                            medkits,
                            ammoboxes,
                            grenades,
                            landmines,
                        ) = reset_game(c_type)

                    if comm_rect.collidepoint(event.pos):
                        selected_char = "Commando"
                        apply_selection(selected_char)
                        game_state = "PLAYING"
                        is_night = True
                        night_timer = 120 * 60
                    elif scout_rect.collidepoint(event.pos):
                        selected_char = "Scout"
                        apply_selection(selected_char)
                        game_state = "PLAYING"
                        is_night = True
                        night_timer = 120 * 60
                    elif jugg_rect.collidepoint(event.pos):
                        selected_char = "Juggernaut"
                        apply_selection(selected_char)
                        game_state = "PLAYING"
                        is_night = True
                        night_timer = 120 * 60

            elif game_state == "PLAYING":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        player.current_weapon = "Pistol"
                    elif event.key == pygame.K_2:
                        if WEAPONS["SMG"]["owned"]:
                            player.current_weapon = "SMG"
                    elif event.key == pygame.K_3:
                        if WEAPONS["Shotgun"]["owned"]:
                            player.current_weapon = "Shotgun"
                    elif event.key == pygame.K_4:
                        if WEAPONS["Rifle"]["owned"]:
                            player.current_weapon = "Rifle"
                    elif event.key == pygame.K_5:
                        if WEAPONS["Sniper"]["owned"]:
                            player.current_weapon = "Sniper"
                    elif event.key == pygame.K_r:
                        player.reload()
                    elif event.key == pygame.K_SPACE:
                        player.start_dash()
                    elif event.key == pygame.K_b and player.barricades > 0:
                        player.barricades -= 1
                        barricades.append(Barricade(player.x, player.y))
                    elif event.key == pygame.K_g and player.grenades > 0:
                        player.grenades -= 1
                        # Fare konumuna doğru el bombası fırlat
                        mx, my = pygame.mouse.get_pos()
                        world_mx = mx - camera.x
                        world_my = my - camera.y
                        grenades.append(Grenade(player.x, player.y, world_mx, world_my))
                    elif event.key == pygame.K_m and player.mines > 0:
                        player.mines -= 1
                        landmines.append(LandMine(player.x, player.y))
                    elif event.key == pygame.K_e and not is_night:
                        game_state = "SHOP"

            elif game_state == "SHOP":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    tab_guns_rect = pygame.Rect(BASE_WIDTH // 2 - 210, 115, 200, 40)
                    tab_cls_rect = pygame.Rect(BASE_WIDTH // 2 + 10, 115, 200, 40)
                    if tab_guns_rect.collidepoint(event.pos):
                        shop_tab = "GUNS"
                    elif tab_cls_rect.collidepoint(event.pos):
                        shop_tab = "CLASSES"

        if game_state == "LOGIN":
            title_surf = font_title.render("ULTIMATE ZOMBIE SURVIVAL", True, RED)
            screen.blit(
                title_surf,
                (
                    BASE_WIDTH // 2 - title_surf.get_width() // 2,
                    BASE_HEIGHT // 2 - 180,
                ),
            )
            sub_surf = font_med.render(
                "Giriş yapmak için kullanıcı adı ve şifre girip ENTER'a basın",
                True,
                GRAY,
            )
            screen.blit(
                sub_surf,
                (
                    BASE_WIDTH // 2 - sub_surf.get_width() // 2,
                    BASE_HEIGHT // 2 - 120,
                ),
            )
            username_box.draw(screen)
            password_box.draw(screen)

        elif game_state == "CHAR_SELECT":
            t_surf = font_title.render("KARAKTERİNİZİ SEÇİN", True, WHITE)
            screen.blit(
                t_surf,
                (
                    BASE_WIDTH // 2 - t_surf.get_width() // 2,
                    BASE_HEIGHT // 2 - 240,
                ),
            )

            c_keys = list(CHARACTERS.keys())
            rects = [
                pygame.Rect(
                    BASE_WIDTH // 2 - 380, BASE_HEIGHT // 2 - 120, 230, 240
                ),
                pygame.Rect(
                    BASE_WIDTH // 2 - 115, BASE_HEIGHT // 2 - 120, 230, 240
                ),
                pygame.Rect(
                    BASE_WIDTH // 2 + 150, BASE_HEIGHT // 2 - 120, 230, 240
                ),
            ]
            for i, c_name in enumerate(c_keys):
                r = rects[i]
                hover = r.collidepoint(mouse_pos)
                pygame.draw.rect(
                    screen,
                    BUTTON_HOVER if hover else BUTTON_COLOR,
                    r,
                    border_radius=12,
                )
                pygame.draw.rect(
                    screen,
                    CYAN if hover else DARK_GRAY,
                    r,
                    3,
                    border_radius=12,
                )

                badge_rect = pygame.Rect(r.centerx - 45, r.y + 15, 90, 24)
                pygame.draw.rect(screen, CHARACTERS[c_name]["color"], badge_rect, border_radius=6)
                badge_surf = font_small.render(CHARACTERS[c_name]["badge"], True, WHITE)
                screen.blit(badge_surf, (badge_rect.centerx - badge_surf.get_width() // 2, badge_rect.centery - badge_surf.get_height() // 2))

                name_surf = font_large.render(c_name, True, WHITE)
                screen.blit(
                    name_surf,
                    (r.centerx - name_surf.get_width() // 2, r.y + 50),
                )

                desc = CHARACTERS[c_name]["desc"]
                words = desc.split(" ")
                line1, line2 = "", ""
                for w in words:
                    if len(line1) < 22:
                        line1 += w + " "
                    else:
                        line2 += w + " "
                
                d1_surf = font_small.render(line1.strip(), True, GRAY)
                d2_surf = font_small.render(line2.strip(), True, GRAY)
                screen.blit(d1_surf, (r.centerx - d1_surf.get_width() // 2, r.y + 110))
                screen.blit(d2_surf, (r.centerx - d2_surf.get_width() // 2, r.y + 130))

                hp_txt = f"Can Çarpanı: x{CHARACTERS[c_name]['hp_mult']}"
                spd_txt = f"Hız Çarpanı: x{CHARACTERS[c_name]['speed_mult']}"
                h_surf = font_small.render(hp_txt, True, GREEN)
                s_surf = font_small.render(spd_txt, True, YELLOW)
                screen.blit(h_surf, (r.centerx - h_surf.get_width() // 2, r.y + 170))
                screen.blit(s_surf, (r.centerx - s_surf.get_width() // 2, r.y + 195))

        elif game_state == "PLAYING":
            keys = pygame.key.get_pressed()
            player.move(keys, obstacles, barricades)
            player.update()

            if is_night:
                night_timer -= 1
                if night_timer <= 0:
                    is_night = False
                    zombies.clear()

            if pygame.mouse.get_pressed()[0]:
                w_info = WEAPONS[player.current_weapon]
                if player.shoot_cooldown <= 0 and not player.reloading:
                    if player.ammo[player.current_weapon] > 0:
                        player.ammo[player.current_weapon] -= 1
                        player.shoot_cooldown = w_info["fire_rate"]
                        player.muzzle_flash = 3
                        w_info["sound"].play()
                        camera.add_shake(
                            4 if player.current_weapon != "Sniper" else 15
                        )

                        if player.current_weapon == "Shotgun":
                            pellets = w_info.get("pellets", 6)
                            for _ in range(pellets):
                                spread_angle = player.angle + random.uniform(
                                    -w_info["spread"], w_info["spread"]
                                )
                                bullets.append(
                                    Bullet(
                                        player.x,
                                        player.y,
                                        spread_angle,
                                        player.dmg_mult * w_info["damage"],
                                    )
                                )
                        else:
                            spread_angle = player.angle + random.uniform(
                                -w_info["spread"], w_info["spread"]
                            )
                            bullets.append(
                                Bullet(
                                    player.x,
                                    player.y,
                                    spread_angle,
                                    player.dmg_mult * w_info["damage"],
                                )
                            )

                        casings.append(ShellCasing(player.x, player.y, player.angle))
                    else:
                        player.reload()

            if is_night:
                spawn_timer += 1
                if spawn_timer > 35 and len(zombies) < 45:
                    spawn_timer = 0
                    angle = random.uniform(0, math.pi * 2)
                    dist = random.uniform(1200, 1800)
                    zx = player.x + math.cos(angle) * dist
                    zy = player.y + math.sin(angle) * dist
                    z_types = ["normal", "runner", "tank", "spitter", "exploder"]
                    weights = [50, 25, 10, 10, 5]
                    chosen_type = random.choices(z_types, weights=weights)[0]
                    zombies.append(Zombie(zx, zy, chosen_type))

            # El Bombası Güncelleme
            for g in grenades[:]:
                g.update()
                if g.timer <= 0:
                    snd_explosion.play()
                    camera.add_shake(20)
                    for z in zombies[:]:
                        if math.hypot(g.x - z.x, g.y - z.y) < 180:
                            z.health -= 250
                            if z.health <= 0:
                                zombies.remove(z)
                                kills += 1
                                player.money += z.reward
                    grenades.remove(g)

            # Mayın Kontrolü
            for m in landmines[:]:
                if not m.active:
                    continue
                for z in zombies[:]:
                    if math.hypot(m.x - z.x, m.y - z.y) < m.radius + z.radius:
                        snd_explosion.play()
                        camera.add_shake(15)
                        m.active = False
                        for z2 in zombies[:]:
                            if math.hypot(m.x - z2.x, m.y - z2.y) < 140:
                                z2.health -= 200
                                if z2.health <= 0:
                                    zombies.remove(z2)
                                    kills += 1
                                    player.money += z2.reward
                        break
                if not m.active and m in landmines:
                    landmines.remove(m)

            for b in bullets[:]:
                b.update()
                if b.lifetime <= 0:
                    bullets.remove(b)
                    continue
                hit = False
                for z in zombies[:]:
                    if math.hypot(b.x - z.x, b.y - z.y) < z.radius + 4:
                        z.health -= b.damage
                        z.apply_knockback(b.angle, 3.5)
                        float_texts.append(
                            FloatingText(z.x, z.y - z.radius, int(b.damage), YELLOW)
                        )
                        for _ in range(3):
                            particles.append(
                                Particle(z.x, z.y, BLOOD_RED, speed=3, size=4)
                            )
                        if z.health <= 0:
                            zombies.remove(z)
                            kills += 1
                            reward = z.reward
                            if PERKS["Scavenger"]["owned"]:
                                reward = int(reward * 1.35)
                            player.money += reward
                            if PERKS["Vampire"]["owned"]:
                                player.health = min(
                                    player.max_health, player.health + 4
                                )
                            blood_pool.append(BloodDecal(z.x, z.y))
                            
                            if random.random() < 0.22:
                                medkits.append(MedKit(z.x, z.y))
                            elif random.random() < 0.25:
                                ammoboxes.append(AmmoBox(z.x, z.y))

                        hit = True
                        break
                if hit:
                    bullets.remove(b)

            for mk in medkits[:]:
                if math.hypot(player.x - mk.x, player.y - mk.y) < player.radius + mk.radius:
                    player.health = min(player.max_health, player.health + mk.heal_amount)
                    float_texts.append(FloatingText(player.x, player.y - 25, f"+{mk.heal_amount} CAN", GREEN))
                    medkits.remove(mk)

            for ab in ammoboxes[:]:
                if math.hypot(player.x - ab.x, player.y - ab.y) < player.radius + ab.radius:
                    for w in player.total_ammo:
                        player.total_ammo[w] += WEAPONS[w]["clip_size"] * 2
                    float_texts.append(FloatingText(player.x, player.y - 25, "+MERMİ", YELLOW))
                    ammoboxes.remove(ab)

            for z in zombies[:]:
                z.update(player, obstacles, barricades, acid_projectiles)
                if (
                    math.hypot(player.x - z.x, player.y - z.y)
                    < player.radius + z.radius
                ):
                    player.take_damage(0.6)
                    if player.health <= 0:
                        update_user_stats(current_user, kills)
                        game_state = "GAMEOVER"

            for ap in acid_projectiles[:]:
                ap.update()
                if ap.lifetime <= 0:
                    acid_projectiles.remove(ap)
                    continue
                if (
                    math.hypot(player.x - ap.x, player.y - ap.y)
                    < player.radius + 7
                ):
                    player.take_damage(15)
                    acid_projectiles.remove(ap)

            camera.update(player, BASE_WIDTH, BASE_HEIGHT)

            for bp in blood_pool:
                bp.draw(screen, camera)
            for mk in medkits:
                mk.draw(screen, camera)
            for ab in ammoboxes:
                ab.draw(screen, camera)
            for lm in landmines:
                lm.draw(screen, camera)
            for g in grenades:
                g.draw(screen, camera)
            for obs in obstacles:
                obs.draw(screen, camera)
            for bar in barricades:
                bar.draw(screen, camera)
            for z in zombies:
                z.draw(screen, camera)
            player.draw(screen, camera, mouse_pos)
            for b in bullets:
                b.draw(screen, camera)
            for ap in acid_projectiles:
                ap.draw(screen, camera)
            for ft in float_texts[:]:
                ft.update()
                ft.draw(screen, camera)
                if ft.lifetime <= 0:
                    float_texts.remove(ft)

            render_dynamic_atmosphere(
                screen, camera, player, BASE_WIDTH, BASE_HEIGHT, is_night
            )
            draw_minimap(
                screen, player, zombies, MAP_WIDTH, MAP_HEIGHT, BASE_WIDTH
            )

            hp_surf = font_med.render(
                f"CAN: {int(player.health)}/{player.max_health}", True, RED
            )
            ammo_surf = font_med.render(
                f"MERMI: {player.ammo[player.current_weapon]}/{player.total_ammo[player.current_weapon]}",
                True,
                YELLOW,
            )
            money_surf = font_med.render(f"PARA: ${player.money}", True, GREEN)
            gear_surf = font_med.render(f"BOMBA: [G]{player.grenades} | MAYIN: [M]{player.mines} | BARR: [B]{player.barricades}", True, CYAN)
            
            if is_night:
                rem_secs = max(0, night_timer // 60)
                mins = rem_secs // 60
                secs = rem_secs % 60
                time_surf = font_med.render(f"GECE KALAN: {mins:02d}:{secs:02d}", True, CYAN)
            else:
                time_surf = font_med.render("SABAH: Market Açık (E tuşuna bas)", True, GREEN)

            screen.blit(hp_surf, (20, 20))
            screen.blit(ammo_surf, (20, 50))
            screen.blit(money_surf, (20, 80))
            screen.blit(gear_surf, (20, 110))
            screen.blit(time_surf, (BASE_WIDTH - time_surf.get_width() - 20, 20))

            if not is_night:
                tc = font_large.render(
                    "SABAH OLDU! Markete gitmek için 'E' tuşuna basabilirsin.",
                    True,
                    GREEN,
                )
                screen.blit(tc, (BASE_WIDTH // 2 - tc.get_width() // 2, 80))

        elif game_state == "SHOP":
            t_surf = font_title.render("MAĞAZA VE KONTROL MERKEZİ", True, WHITE)
            screen.blit(
                t_surf,
                (BASE_WIDTH // 2 - t_surf.get_width() // 2, 25),
            )

            m_surf = font_large.render(f"Bakiyeniz: ${player.money}", True, GREEN)
            screen.blit(
                m_surf,
                (BASE_WIDTH // 2 - m_surf.get_width() // 2, 80),
            )

            tab_guns_rect = pygame.Rect(BASE_WIDTH // 2 - 210, 125, 200, 40)
            tab_cls_rect = pygame.Rect(BASE_WIDTH // 2 + 10, 125, 200, 40)

            pygame.draw.rect(screen, BUTTON_HOVER if shop_tab == "GUNS" else BUTTON_COLOR, tab_guns_rect, border_radius=6)
            pygame.draw.rect(screen, CYAN if shop_tab == "GUNS" else DARK_GRAY, tab_guns_rect, 2, border_radius=6)
            tg_txt = font_med.render("SİLAHLAR & MERMİ", True, WHITE)
            screen.blit(tg_txt, (tab_guns_rect.centerx - tg_txt.get_width() // 2, tab_guns_rect.centery - tg_txt.get_height() // 2))

            pygame.draw.rect(screen, BUTTON_HOVER if shop_tab == "CLASSES" else BUTTON_COLOR, tab_cls_rect, border_radius=6)
            pygame.draw.rect(screen, CYAN if shop_tab == "CLASSES" else DARK_GRAY, tab_cls_rect, 2, border_radius=6)
            tc_txt = font_med.render("KARAKTER BİLGİLERİ", True, WHITE)
            screen.blit(tc_txt, (tab_cls_rect.centerx - tc_txt.get_width() // 2, tab_cls_rect.centery - tc_txt.get_height() // 2))

            if shop_tab == "GUNS":
                y_off = 185
                for w_name, w_data in WEAPONS.items():
                    rect = pygame.Rect(BASE_WIDTH // 2 - 320, y_off, 640, 65)
                    pygame.draw.rect(screen, BUTTON_COLOR, rect, border_radius=8)
                    pygame.draw.rect(
                        screen,
                        CYAN if rect.collidepoint(mouse_pos) else DARK_GRAY,
                        rect,
                        2,
                        border_radius=8,
                    )

                    title_txt = font_med.render(f"{w_name}", True, WHITE)
                    info_txt = font_small.render(w_data["info"], True, GRAY)
                    screen.blit(title_txt, (rect.x + 15, rect.y + 10))
                    screen.blit(info_txt, (rect.x + 15, rect.y + 35))

                    if not w_data["owned"]:
                        b_rect = pygame.Rect(rect.right - 215, rect.y + 15, 100, 35)
                        buy_hover = b_rect.collidepoint(mouse_pos)
                        pygame.draw.rect(
                            screen,
                            GREEN if buy_hover else DARK_GRAY,
                            b_rect,
                            border_radius=6,
                        )
                        b_txt = font_small.render(
                            f"${w_data['cost']}", True, BLACK if buy_hover else WHITE
                        )
                        screen.blit(
                            b_txt,
                            (
                                b_rect.centerx - b_txt.get_width() // 2,
                                b_rect.centery - b_txt.get_height() // 2,
                            ),
                        )

                        for event in events:
                            if event.type == pygame.MOUSEBUTTONDOWN and buy_hover:
                                if player.money >= w_data["cost"]:
                                    player.money -= w_data["cost"]
                                    w_data["owned"] = True

                    ammo_btn_rect = pygame.Rect(rect.right - 105, rect.y + 15, 95, 35)
                    ammo_hover = ammo_btn_rect.collidepoint(mouse_pos)
                    pygame.draw.rect(
                        screen,
                        YELLOW if ammo_hover else DARK_GRAY,
                        ammo_btn_rect,
                        border_radius=6,
                    )
                    ammo_txt = font_small.render(
                        f"MERMİ ${w_data['ammo_cost']}", True, BLACK if ammo_hover else WHITE
                    )
                    screen.blit(
                        ammo_txt,
                        (
                            ammo_btn_rect.centerx - ammo_txt.get_width() // 2,
                            ammo_btn_rect.centery - ammo_txt.get_height() // 2,
                        ),
                    )

                    for event in events:
                        if event.type == pygame.MOUSEBUTTONDOWN and ammo_hover:
                            if player.money >= w_data["ammo_cost"]:
                                player.money -= w_data["ammo_cost"]
                                player.total_ammo[w_name] += w_data["clip_size"] * 3

                    y_off += 75

            elif shop_tab == "CLASSES":
                y_off = 190
                for c_name, c_info in CHARACTERS.items():
                    c_rect = pygame.Rect(BASE_WIDTH // 2 - 320, y_off, 640, 95)
                    is_current = (player.char_type == c_name)
                    pygame.draw.rect(screen, BUTTON_COLOR, c_rect, border_radius=8)
                    pygame.draw.rect(
                        screen,
                        GREEN if is_current else DARK_GRAY,
                        c_rect,
                        2,
                        border_radius=8,
                    )

                    c_title = font_med.render(f"{c_name} {'(AKTİF)' if is_current else ''}", True, WHITE)
                    c_desc = font_small.render(c_info["desc"], True, GRAY)
                    c_stats = font_small.render(f"Can Çarpanı: x{c_info['hp_mult']} | Hız Çarpanı: x{c_info['speed_mult']} | Hasar Çarpanı: x{c_info['dmg_mult']}", True, CYAN)

                    screen.blit(c_title, (c_rect.x + 20, c_rect.y + 12))
                    screen.blit(c_desc, (c_rect.x + 20, c_rect.y + 38))
                    screen.blit(c_stats, (c_rect.x + 20, c_rect.y + 64))

                    y_off += 110

            exit_rect = pygame.Rect(
                BASE_WIDTH // 2 - 100, BASE_HEIGHT - 80, 200, 45
            )
            if draw_ui_button(screen, "GECEYE BAŞLA", exit_rect, mouse_pos):
                for event in events:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        game_state = "PLAYING"
                        is_night = True
                        night_timer = 120 * 60

        elif game_state == "GAMEOVER":
            go_surf = font_title.render("ÖLDÜNÜZ", True, RED)
            screen.blit(
                go_surf,
                (
                    BASE_WIDTH // 2 - go_surf.get_width() // 2,
                    BASE_HEIGHT // 2 - 80,
                ),
            )

            res_rect = pygame.Rect(
                BASE_WIDTH // 2 - 125, BASE_HEIGHT // 2 + 20, 250, 50
            )
            if draw_ui_button(screen, "YENİDEN BAŞLA", res_rect, mouse_pos):
                for event in events:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        (
                            player,
                            camera,
                            obstacles,
                            bullets,
                            zombies,
                            particles,
                            blood_pool,
                            float_texts,
                            casings,
                            barricades,
                            acid_projectiles,
                            medkits,
                            ammoboxes,
                            grenades,
                            landmines,
                        ) = reset_game(selected_char)
                        game_state = "PLAYING"
                        is_night = True
                        night_timer = 120 * 60

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
