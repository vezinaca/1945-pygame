# 1945
# Version 1.0
# Shoot the enemy planes
# Haroon Khalid

import pygame
import random
import math
import sys

# INITIALIZE PYGAME
pygame.init()

# SET WINDOW CAPTION
pygame.display.set_caption("1945")

# SET WINDOW RESOLUTION
resolution = (320, 480)
window_resolution = (768, 1152)
window = pygame.display.set_mode(window_resolution, 0, 32)
screen = pygame.Surface(resolution).convert()

def present_screen():
    pygame.transform.scale(screen, window_resolution, window)
    pygame.display.flip()

# SET UP LISTS
enemies = []
shots = []
explosions = []
players = []
background = []
waters = []
powerups = []
respawn_at = None
RESPAWN_DELAY_MS = 1500
next_formation_at = 4000

class Animation:
 
    # data = [ [time, image], [time, image], ...]
 
    def __init__(self, repeat, data): 
        self.data = data
        self.cur_frame = 0
        self.ticks = pygame.time.get_ticks()
        self.ticks_remaining = data[0][0]
        self.pos = [0, 0]
        self.frames = (len(self.data) - 1)
        self.repeat = repeat
        self.pause = 0
 
    def draw(self, dest): 
        old_ticks = self.ticks
        self.ticks = pygame.time.get_ticks() 
        tick_difference = self.ticks - old_ticks 
        self.ticks_remaining -= tick_difference
 
        while (self.ticks_remaining <= 0): 
            self.cur_frame += 1
            
            if self.cur_frame > self.frames and self.repeat == 0:
                self.pause = 1
                break
            
            self.cur_frame %= len(self.data) 
            self.ticks_remaining += self.data[self.cur_frame][0]

        if self.pause == 0:
            dest.blit(self.data[self.cur_frame][1], self.pos)

class Player(object):
    def __init__(self):
        self.image = p1_plane_1
        self.rect = self.image.get_rect()
        self.rect.x = 130
        self.rect.y = 350
        self.flying = Animation(1, [[30, p1_plane_1],[30, p1_plane_2], [30, p1_plane_3]])
        self.anim = self.flying
        self.shots = 0
        self.score = 0
        self.hits = 0
        self.lives = 3
        self.bombs = 3
        self.spread_shot = False
        self.wingmen = False
        self.wingmen_alive = [False, False]
        self.wingmen_arrived_at = 0
        self.wingman_animations = [
            Animation(1, [[30, frame] for frame in wingman_frames])
            for _ in range(2)]

    def wingman_rects(self):
        progress = min(1, max(0, (pygame.time.get_ticks()
                                  - self.wingmen_arrived_at) / 600))
        distance = 44 + (1 - progress) * resolution[0]
        return [wingman_frames[0].get_rect(center=(
            round(self.rect.centerx + side * distance), self.rect.centery + 10))
            for side in (-1, 1)]
 
    def draw(self, dest): 
        self.anim.pos = self.rect
        self.anim.draw(dest)
        if self.wingmen:
            for index, rect in enumerate(self.wingman_rects()):
                if self.wingmen_alive[index]:
                    animation = self.wingman_animations[index]
                    animation.pos = rect
                    animation.draw(dest)
 
    def update(self):
        
        #Get the current key state.
        key = pygame.key.get_pressed()
        
        #Move left/right
        if key[pygame.K_LEFT]:
            self.rect.x -= 5
        if key[pygame.K_RIGHT]:
            self.rect.x += 5
        if key[pygame.K_UP]:
            self.rect.y -= 5
        if key[pygame.K_DOWN]:
            self.rect.y += 5 
            
        self.rect.clamp_ip(screen.get_rect())
        self.draw(screen)

class Explosion(object):
    def __init__(self,type):
        self.image = explode_1
        self.rect = self.image.get_rect()
        self.exploding = Animation(0, [[50, explode_1],[50, explode_2],[50, explode_3],[50, explode_4],[50, explode_5],[50, explode_6]])
        self.p1_exploding = Animation(0, [[50, p1_explode_1],[50, p1_explode_2],[50, p1_explode_3],[50, p1_explode_4],[50, p1_explode_5],[50, p1_explode_6],[50, p1_explode_7]])
        self.anim = self.p1_exploding if type == 1 else self.exploding
        self.type = type
 
    def draw(self, dest):
        if self.type == 1:
            self.anim = self.p1_exploding
        self.anim.pos = self.rect
        self.anim.draw(dest)
 
    def update(self):
        self.draw(screen)
        
class Enemy(object):
    def __init__(self, kind="fighter"):
        self.kind = kind
        spec = enemy_types[kind]
        self.image = spec['frames'][0]
        self.rect = self.image.get_rect(topleft=(130, 30))
        self.flying = Animation(1, [[30, frame] for frame in spec['frames']])
        self.anim = self.flying
        self.speed = spec['speed']
        self.health = spec['health']
        self.points = spec['points']
        self.damaged_frames = []
        if self.health == 3:
            for frame in spec['frames']:
                damaged = frame.convert_alpha()
                damaged.fill((100, 0, 0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                self.damaged_frames.append(damaged)
        self.age = 0
        self.fired_at = set()
        self.curve = None

    def enable_curve(self):
        self.curve = {
            'origin': self.rect.center, 'distance': 0,
            'turn_y': random.uniform(140, 240),
            'direction': 1 if self.rect.centerx < resolution[0] // 2 else -1,
            'frames': [entry[1] for entry in self.anim.data],
            'damaged': self.damaged_frames[:],
        }

    def advance_curve(self):
        route = self.curve
        route['distance'] += self.speed
        origin_x, origin_y = route['origin']
        straight = max(0, route['turn_y'] - origin_y)
        curved = max(0, route['distance'] - straight)
        angle = min(curved / 80, math.pi / 2)
        heading = math.degrees(angle) * route['direction']
        center = (
            round(origin_x + route['direction'] * (80 * (1 - math.cos(angle))
                  + max(0, curved - 80 * math.pi / 2))),
            round(origin_y + min(route['distance'], straight) + 80 * math.sin(angle)))
        for entry, frame in zip(self.anim.data, route['frames']):
            entry[1] = pygame.transform.rotate(frame, heading)
        self.damaged_frames = [pygame.transform.rotate(frame, heading)
                               for frame in route['damaged']]
        self.rect = self.anim.data[self.anim.cur_frame][1].get_rect(center=center)

    def draw(self, dest):
        self.anim.pos = self.rect
        self.anim.draw(dest)
        if (self.damaged_frames and self.health == 1
                and (pygame.time.get_ticks() // 100) % 2 == 0):
            dest.blit(self.damaged_frames[self.anim.cur_frame], self.rect)

    def update(self):
        if (self.rect.top >= resolution[1] or (self.curve is not None
                and (self.rect.right < 0 or self.rect.left > resolution[0]))):
            enemies.remove(self)
            return
        self.age += 1
        if self.kind == 'scout' and self.curve is None:
            self.rect.x += round(3 * math.sin(self.age / 12))
            self.rect.x = max(0, min(self.rect.x, resolution[0] - self.rect.width))
        firing_heights = {
            'bomber': (100, 220),
            'boat': (60, 160, 260),
        }.get(self.kind, (100,))
        for height in firing_heights:
            if self.rect.y >= height and height not in self.fired_at:
                self.fired_at.add(height)
                offsets = (-18, 18) if self.kind == 'bomber' else (0,)
                for offset in offsets:
                    create_shot(1, self.rect.centerx - 13 + offset,
                                self.rect.bottom - 40)
        if self.curve is not None:
            self.advance_curve()
        else:
            self.rect.y += self.speed
        self.draw(screen)

class FormationPlane(Enemy):
    """Follow the same curved route, spaced eighteen frames apart."""
    def __init__(self, group, index):
        super().__init__('fighter')
        self.image = formation_frames[0]
        self.flying = Animation(1, [[30, frame] for frame in formation_frames])
        self.anim = self.flying
        self.group = group
        self.index = index
        self.base_frames = [entry[1] for entry in self.anim.data]
        self.age = 0
        self.speed = 3
        self.set_position()

    def set_position(self):
        distance = (self.age - self.index * 18) * self.speed
        straight = self.group['turn_y'] + 40
        curved = max(0, distance - straight)
        angle = min(curved / 80, math.pi / 2)
        x = self.group['x'] + self.group['direction'] * (
            80 * (1 - math.cos(angle)) + max(0, curved - 80 * math.pi / 2))
        y = -40 + min(distance, straight) + 80 * math.sin(angle)
        heading = math.degrees(angle) * self.group['direction']
        for entry, frame in zip(self.anim.data, self.base_frames):
            entry[1] = pygame.transform.rotate(frame, heading)
        self.rect = self.anim.data[self.anim.cur_frame][1].get_rect(
            center=(round(x), round(y)))

    def update(self):
        self.age += 1
        self.set_position()
        if self.rect.right < 0 or self.rect.left > resolution[0]:
            self.group['failed'] = True
            enemies.remove(self)
            return
        self.draw(screen)


def spawn_formation():
    if not players:
        return False
    x = max(70, min(p1.rect.centerx, resolution[0] - 70))
    group = {'x': x, 'turn_y': max(100, min(p1.rect.top - 120, 200)),
             'direction': 1 if x < resolution[0] // 2 else -1,
             'shot_down': 0, 'failed': False}
    formation = [FormationPlane(group, index) for index in range(4)]
    if any(plane.rect.inflate(12, 12).colliderect(other.rect)
           for plane in formation for other in enemies):
        return False
    enemies.extend(formation)
    return True


class Water(object):
    def __init__(self):
        self.image = water_bg_ext
        self.x = 0
        self.y = -32
        
    def update(self):
        if self.y > 0:
            self.y = -32
        self.y += 1
        screen.blit(self.image, (self.x, self.y))
        
class Fire(object):
    def __init__(self, type, angle=0):
        self.velocity = (pygame.Vector2(0, 5) if type == 1
                         else pygame.Vector2(0, -20).rotate(angle))
        self.position = None
        self.image = e_shot if type == 1 else pygame.transform.rotate(fire_1, -angle)
        self.rect = self.image.get_rect()
        self.rect.x = 100
        self.rect.y = 100
        self.firing_1 = Animation(1, [[50, self.image]])
        self.e_firing = Animation(1, [[50, e_shot]])
        self.anim = self.e_firing if type == 1 else self.firing_1
        self.type = type
         
    def draw(self, dest): 
        self.anim.pos = self.rect
        self.anim.draw(dest)
 
    def update(self):
        if self.position is None:
            self.position = pygame.Vector2(self.rect.topleft)
        self.position += self.velocity
        self.rect.topleft = (round(self.position.x), round(self.position.y))
        self.draw(screen)


class PowerUp:
    def __init__(self, center=(160, 290), kind=None):
        self.kind = kind if kind is not None else (
            'none' if p1.spread_shot and p1.wingmen else
            'wingmen' if p1.spread_shot else 'spread')
        self.image = pow_image
        self.rect = self.image.get_rect(center=center)
        self.rect.clamp_ip(screen.get_rect())


def reset_powerups():
    powerups[:] = [PowerUp(kind='wingmen')]


def update_powerups():
    for pickup in powerups[:]:
        pickup.rect.y += 1
        if pickup.rect.top >= resolution[1]:
            powerups.remove(pickup)
            continue
        screen.blit(pickup.image, pickup.rect)
        for player in players:
            if player.rect.colliderect(pickup.rect):
                if pickup.kind == 'none' or (player.spread_shot and player.wingmen):
                    powerups.remove(pickup)
                    break
                if pickup.kind == 'wingmen':
                    player.wingmen = True
                    player.wingmen_alive = [True, True]
                    player.wingmen_arrived_at = pygame.time.get_ticks()
                else:
                    player.spread_shot = True
                fusion_snd.play()
                powerups.remove(pickup)
                break


class Background(object):
    def __init__(self, kind=None, y=None):
        self.kind = kind if kind is not None else random.randrange(len(scenery_images))
        self.image = scenery_images[self.kind]
        self.x = random.randrange(8, resolution[0] - self.image.get_width() - 7)
        self.y = -self.image.get_height() if y is None else y

    def update(self):
        self.y += 1
        if self.y >= resolution[1]:
            background.remove(self)
            return
        screen.blit(self.image, (self.x, self.y))

class Menu(object):
    def __init__(self):
        self.press = Animation(1, [[500, press_start_1],[200, press_start_2]])
        self.anim = self.press
        self.exit = 0
        
    def draw(self, dest): 
        self.anim.pos = (80,250)
        self.anim.draw(dest)
        
    def update(self):
        screen.blit(menu_img, (0,0))
        self.draw(screen)
        present_screen()
        pygame.time.delay(25)
                
def create_shot(type, x, y):
    if type == 1:
        f = Fire(type)
        f.rect.x = x + 13
        f.rect.y = y + 40
        shots.append(f)
    else:
        angles = (0, -10, 10) if p1.spread_shot else (0,)
        for angle in angles:
            f = Fire(type, angle)
            f.rect.center = (x + p1.rect.width // 2, y - 4)
            shots.append(f)
        if p1.wingmen and pygame.time.get_ticks() - p1.wingmen_arrived_at >= 600:
            for index, rect in enumerate(p1.wingman_rects()):
                if not p1.wingmen_alive[index]:
                    continue
                f = Fire(0)
                f.rect.center = (rect.centerx, rect.top - 4)
                shots.append(f)

def update_shots():
    for f in shots[:]:
        f.update()
        if (f.rect.bottom <= 0 or f.rect.top >= resolution[1]
                or f.rect.right <= 0 or f.rect.left >= resolution[0]):
            shots.remove(f)
        
def update_players():
    for p in players:
        p.update()
        
def create_enemy():
    kind = random.choices(tuple(enemy_types),
                          weights=tuple(spec['weight'] for spec in enemy_types.values()))[0]
    e = Enemy(kind)
    for _ in range(20):
        e.rect.x = random.randrange(10, resolution[0] - e.rect.width + 1)
        e.rect.y = random.randrange(-500, -10)
        if not any(e.rect.inflate(12, 12).colliderect(other.rect)
                   for other in enemies):
            if kind != 'boat' and random.random() < 0.65:
                e.enable_curve()
            enemies.append(e)
            return
 
def update_enemies():
    for e in enemies[:]:
        e.update()           
        
def create_explosion(type, erectx, erecty):
    x = Explosion(type)
    x.rect.x = erectx
    x.rect.y = erecty
    explosions.append(x)
    
def update_explosions():
    for x in explosions[:]:
        x.update()
        if x.anim.pause:
            explosions.remove(x)

def create_background(kind=None, y=None):
    background.append(Background(kind, y))


def update_background():
    if not background:
        # Start with scenery already visible, including all three terrain sprites.
        for index, y in enumerate((-80, 80, 240, 400)):
            create_background(index % len(scenery_images), y)
    for item in background[:]:
        item.update()
    while len(background) < 4:
        top = min((item.y for item in background), default=0)
        create_background(y=min(-65, top - random.randrange(140, 201)))

def create_water():
    w = Water()
    waters.append(w)
def update_water():
    for w in waters:
        w.update()
    if len(waters) == 0:
        create_water()
          
def draw_stats():
    p1_score_text = custom_font.render("PLAYER 1", True, white)
    high_score_text = custom_font.render("HIGH SCORE", True, gold)
    p1_points_text = custom_font.render(str(p1.score), True, light_grey)
    high_score_points = custom_font.render(str(p1.score), True, light_grey)
    p1_bomb_text = custom_font.render(str(p1.bombs), True, light_grey)
    screen.blit(p1_score_text, (10, 5))
    screen.blit(high_score_text, (187, 5))
    screen.blit(p1_points_text, (10, 20))
    screen.blit(high_score_points, (187, 20))
    
    if p1.bombs == 3:
        screen.blit(p1_bomb, (255,455))
        screen.blit(p1_bomb, (275,455))
        screen.blit(p1_bomb, (295,455))
    elif p1.bombs == 2:
        screen.blit(p1_bomb, (275,455))
        screen.blit(p1_bomb, (295,455))
    elif p1.bombs == 1:
        screen.blit(p1_bomb, (295,455))
        
        
    if p1.lives == 3:
        screen.blit(p1_life, (10,455))
        screen.blit(p1_life, (38,455))
        screen.blit(p1_life, (66,455))
    elif p1.lives == 2:
        screen.blit(p1_life, (10,455))
        screen.blit(p1_life, (38,455))
    elif p1.lives == 1:
        screen.blit(p1_life, (10,455))

def destroy_enemy(enemy, award_points=False, shot_down=False):
    thump_snd.play()
    create_explosion(0, enemy.rect.x, enemy.rect.y)
    enemies.remove(enemy)
    if isinstance(enemy, FormationPlane):
        group = enemy.group
        if shot_down:
            group['shot_down'] += 1
        else:
            group['failed'] = True
        if group['shot_down'] == 4 and not group['failed']:
            powerups.append(PowerUp(enemy.rect.center))
    if award_points:
        p1.hits += 1
        p1.score += enemy.points


def destroy_player(player):
    global respawn_at
    thump_snd.play()
    create_explosion(1, player.rect.x, player.rect.y)
    players.remove(player)
    player.spread_shot = False
    player.wingmen = False
    player.wingmen_alive = [False, False]
    player.lives = max(0, player.lives - 1)
    respawn_at = (pygame.time.get_ticks() + RESPAWN_DELAY_MS
                  if player.lives > 0 else None)


def sprites_overlap(first, second):
    """Collide only visible pixels of the currently displayed frames."""
    first_image = first.anim.data[first.anim.cur_frame][1]
    second_image = second.anim.data[second.anim.cur_frame][1]
    return images_overlap(first_image, first.rect, second_image, second.rect)


def images_overlap(first_image, first_rect, second_image, second_rect):
    if not first_rect.colliderect(second_rect):
        return False
    offset = (second_rect.x - first_rect.x, second_rect.y - first_rect.y)
    return pygame.mask.from_surface(first_image).overlap(
        pygame.mask.from_surface(second_image), offset) is not None


def check_wingman_hit(player, shot):
    if not player.wingmen:
        return False
    for index, rect in enumerate(player.wingman_rects()):
        if not player.wingmen_alive[index]:
            continue
        animation = player.wingman_animations[index]
        image = animation.data[animation.cur_frame][1]
        if images_overlap(image, rect, shot.image, shot.rect):
            player.wingmen_alive[index] = False
            player.wingmen = any(player.wingmen_alive)
            thump_snd.play()
            create_explosion(0, rect.centerx - 16, rect.centery - 16)
            return True
    return False


def check_hit():
    for shot in shots[:]:
        if shot.type == 0:
            for enemy in enemies[:]:
                if enemy.rect.colliderect(shot.rect):
                    enemy.health -= 1
                    if enemy.health <= 0:
                        destroy_enemy(enemy, award_points=True, shot_down=True)
                    shots.remove(shot)
                    break
        else:
            for player in players[:]:
                if check_wingman_hit(player, shot):
                    shots.remove(shot)
                    break
                if sprites_overlap(player, shot):
                    destroy_player(player)
                    shots.remove(shot)
                    break


def use_bomb():
    if not players or p1.bombs <= 0:
        return
    p1.bombs -= 1
    cannon_snd.play()
    for enemy in enemies[:]:
        destroy_enemy(enemy, award_points=True)
    shots[:] = [shot for shot in shots if shot.type == 0]


# Respawn with remaining lives, or start a new game after game over.
def create_player():
    global p1, respawn_at, next_formation_at
    if players:
        return
    if p1.lives == 0:
        enemies.clear()
        shots.clear()
        reset_powerups()
        next_formation_at = pygame.time.get_ticks() + 4000
    previous = p1
    p1 = Player()
    if previous.lives > 0:
        for name in ('score', 'hits', 'shots', 'lives', 'bombs', 'spread_shot'):
            setattr(p1, name, getattr(previous, name))
    players.append(p1)
    respawn_at = None


def respawn_area_clear():
    # Reserve the starting position plus a margin and half a second of travel.
    area = p1.image.get_rect(topleft=(130, 350)).inflate(16, 16)
    for shot in shots:
        if shot.type == 1:
            path = shot.rect.union(shot.rect.move(0, 5 * 20))
            if area.colliderect(path):
                return False
    for enemy in enemies:
        path = enemy.rect.union(enemy.rect.move(0, enemy.speed * 20))
        if (enemy.kind == 'scout' or isinstance(enemy, FormationPlane)
                or enemy.curve is not None):
            path = path.inflate(120, 0)
        if area.colliderect(path):
            return False
    return True


def update_respawn():
    if (not players and respawn_at is not None
            and pygame.time.get_ticks() >= respawn_at
            and respawn_area_clear()):
        create_player()


def draw_game_message():
    if players:
        return
    message = 'GET READY' if p1.lives > 0 else 'GAME OVER'
    text = custom_font.render(message, True, gold)
    screen.blit(text, text.get_rect(center=(resolution[0] // 2,
                                           resolution[1] // 2)))
    if p1.lives == 0:
        prompt = font.render('Press F1 to play again', True, white)
        screen.blit(prompt, prompt.get_rect(center=(resolution[0] // 2,
                                                   resolution[1] // 2 + 30)))

# CREATE ENEMIES
def spawn_enemies():
    global next_formation_at
    now = pygame.time.get_ticks()
    if players and now >= next_formation_at and len(enemies) <= 8:
        if spawn_formation():
            next_formation_at = now + 12000
        else:
            next_formation_at = now + 500
    if len(enemies) < 8:
        create_enemy()
        
def check_plane_hit():
    for player in players[:]:
        for enemy in enemies[:]:
            if sprites_overlap(enemy, player):
                destroy_enemy(enemy)
                destroy_player(player)
                break


def handle_event(event, in_menu=False):
    if event.type == pygame.QUIT or (
        event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
    ):
        pygame.quit()
        sys.exit()
    if event.type != pygame.KEYDOWN:
        return
    if in_menu:
        if event.key == pygame.K_RETURN:
            menu_screen.exit = 1
            start_snd.play()
        return
    if players:
        if event.key == pygame.K_SPACE:
            shot_snd.play()
            create_shot(0, p1.rect.x, p1.rect.y)
            p1.shots += 1
        elif event.key == pygame.K_LCTRL:
            use_bomb()
    if event.key == pygame.K_F1 and not players and p1.lives == 0:
        create_player()

# SET UP THE FONT AND COLOR
default_font = pygame.font.get_default_font()
font = pygame.font.SysFont(default_font, 20)
big_font = pygame.font.SysFont(default_font, 26)
custom_font = pygame.font.Font("imagine_font.ttf", 18)
white = (255,255,255)
light_grey = (191,191,191)
gold = (255,215,0)
          
# LOAD GRAPHICS
sprite_sheet_file = '1945_sprite_sheet.png'
sprite_sheet = pygame.image.load(sprite_sheet_file).convert()
sprite_sheet.set_colorkey((0, 67, 171))
p1_plane_1 = sprite_sheet.subsurface(4, 400, 65, 65)
p1_plane_2 = sprite_sheet.subsurface(70, 400, 65, 65)
p1_plane_3 = sprite_sheet.subsurface(136, 400, 65, 65)
e_plane_1 = sprite_sheet.subsurface(202, 466, 32, 32)
e_plane_2 = sprite_sheet.subsurface(235, 466, 32, 32)
e_plane_3 = sprite_sheet.subsurface(268, 466, 32, 32)
explode_1 = sprite_sheet.subsurface(70, 169, 32, 32)
explode_2 = sprite_sheet.subsurface(103, 169, 32, 32) 
explode_3 = sprite_sheet.subsurface(137, 169, 31, 32) # coordinate is off 1 pixel?
explode_4 = sprite_sheet.subsurface(169, 169, 32, 32)
explode_5 = sprite_sheet.subsurface(202, 169, 32, 32)
explode_6 = sprite_sheet.subsurface(235, 169, 32, 32)
p1_explode_1 = sprite_sheet.subsurface(4, 301, 65, 65)
p1_explode_2 = sprite_sheet.subsurface(70, 301, 65, 65)
p1_explode_3 = sprite_sheet.subsurface(136, 301, 65, 65)
p1_explode_4 = sprite_sheet.subsurface(202, 301, 65, 65)
p1_explode_5 = sprite_sheet.subsurface(268, 301, 65, 65)
p1_explode_6 = sprite_sheet.subsurface(334, 301, 65, 65)
p1_explode_7 = sprite_sheet.subsurface(400, 301, 65, 65)
press_start_1 = sprite_sheet.subsurface(414, 544, 158, 22)
press_start_2 = sprite_sheet.subsurface(4, 546, 1, 1)
def plane_frames(rectangles):
    frames = []
    for rectangle in rectangles:
        frame = pygame.transform.flip(sprite_sheet.subsurface(rectangle), False, True)
        frame.set_colorkey((0, 67, 171))
        frames.append(frame)
    return frames


scout_frames = [sprite_sheet.subsurface(x, 466, 32, 32).copy()
                for x in (4, 37, 70)]
# Camouflaged heavy bombers across the top of the sheet, distinct from the player.
bomber_frames = plane_frames([(x, 4, 98, 98) for x in (598, 697, 796)])
interceptor_frames = plane_frames([(x, 400, 65, 65) for x in (268, 334, 400)])
# This row already faces down toward the player.
blue_frames = [sprite_sheet.subsurface(x, 466, 32, 32).copy()
               for x in (301, 334, 367)]
for frame in blue_frames:
    frame.set_colorkey((0, 67, 171))
silver_frames = plane_frames([(x, 367, 32, 32) for x in (4, 37, 70)])
for frame in scout_frames:
    frame.set_colorkey((0, 67, 171))
# Give the formation a distinctly red body rather than green camouflage.
formation_frames = []
for source in (e_plane_1, e_plane_2, e_plane_3):
    frame = source.copy()
    frame.set_colorkey((0, 67, 171))
    frame = frame.convert_alpha()
    for y in range(frame.get_height()):
        for x in range(frame.get_width()):
            color = frame.get_at((x, y))
            if color.a:
                brightness = max(color.r, color.g, color.b)
                frame.set_at((x, y), (brightness, int(brightness * 0.22),
                                      int(brightness * 0.22), color.a))
    formation_frames.append(frame)
# Patrol boat, including its wake, from the narrow ship row.
boat_frame = pygame.transform.flip(
    sprite_sheet.subsurface(400, 103, 32, 98), False, True)
boat_frame.set_colorkey((0, 67, 171))
enemy_types = {
    'fighter': {'frames': [e_plane_1, e_plane_2, e_plane_3],
                'speed': 3, 'health': 1, 'points': 100, 'weight': 4},
    'scout': {'frames': scout_frames,
              'speed': 4, 'health': 1, 'points': 150, 'weight': 3},
    'bomber': {'frames': bomber_frames,
               'speed': 2, 'health': 3, 'points': 300, 'weight': 2},
    'interceptor': {'frames': interceptor_frames,
                    'speed': 3, 'health': 3, 'points': 250, 'weight': 2},
    'blue_fighter': {'frames': blue_frames,
                     'speed': 4, 'health': 1, 'points': 125, 'weight': 3},
    'silver_diver': {'frames': silver_frames,
                     'speed': 5, 'health': 1, 'points': 175, 'weight': 2},
    'boat': {'frames': [boat_frame],
             'speed': 1, 'health': 4, 'points': 400, 'weight': 2},
}
wingman_frames = [pygame.transform.scale(
    pygame.transform.flip(sprite_sheet.subsurface(x, 499, 32, 32), False, True),
    (20, 20)) for x in (4, 37, 70)]
for frame in wingman_frames:
    frame.set_colorkey((0, 67, 171))
pow_image = sprite_sheet.subsurface(235, 235, 32, 32).copy()
pow_image.set_colorkey((0, 67, 171))
e_shot = sprite_sheet.subsurface(280, 148, 9, 9)
score = sprite_sheet.subsurface(572, 178, 63, 17)
fire_1 = sprite_sheet.subsurface(37, 169, 32, 32)
p1_bomb = sprite_sheet.subsurface(279, 272, 11, 22)
p1_life = sprite_sheet.subsurface(206, 274, 23, 18)
background_1 = sprite_sheet.subsurface(103, 499, 64, 65)
background_2 = sprite_sheet.subsurface(168, 499, 64, 65)
background_3 = sprite_sheet.subsurface(233, 499, 64, 65)
scenery_images = [image.copy() for image in (background_1, background_2, background_3)]
for image in scenery_images:
    image.set_colorkey((0, 67, 171))
menu_graphic = 'menu.png'
water_bg = 'waterbgext.png'
water_bg_ext = pygame.image.load(water_bg).convert()
menu_img = pygame.image.load(menu_graphic).convert()
p1_plane_1.set_colorkey((0, 67, 171))
p1_plane_2.set_colorkey((0, 67, 171))
p1_plane_3.set_colorkey((0, 67, 171))
e_plane_1.set_colorkey((0, 67, 171))
e_plane_2.set_colorkey((0, 67, 171))
e_plane_3.set_colorkey((0, 67, 171))
explode_1.set_colorkey((0, 67, 171))
explode_2.set_colorkey((0, 67, 171))
explode_3.set_colorkey((0, 67, 171))
explode_4.set_colorkey((0, 67, 171))
explode_5.set_colorkey((0, 67, 171))
explode_6.set_colorkey((0, 67, 171))
score.set_colorkey((0, 0, 0))
fire_1.set_colorkey((0, 67, 171))
e_shot.set_colorkey((0, 67, 171))

# LOAD SOUNDS
fusion_snd = pygame.mixer.Sound('fusion.ogg')
shot_snd = pygame.mixer.Sound('shot.ogg')
thump_snd = pygame.mixer.Sound('thump.ogg')
cannon_snd = pygame.mixer.Sound('cannon.ogg')
start_snd = pygame.mixer.Sound('start.ogg')
pygame.mixer.music.load('music_1.ogg')
play_musc = 1

            
# CREATE PLAYER
p1 = Player()
players.append(p1)
reset_powerups()

# CREATE MENU
menu_screen = Menu()
menu_screen.exit = 0


# MAIN MENU LOOP
while menu_screen.exit == 0:
    for event in pygame.event.get():
        handle_event(event, in_menu=True)
    menu_screen.update()

# MAIN GAME LOOP
game_clock = pygame.time.Clock()
while True:
    
    for event in pygame.event.get():
        handle_event(event)

    update_respawn()
    if play_musc == 1:
        pygame.mixer.music.play()
    play_musc = 0
    screen.fill((0,67,171))
    update_water()
    update_background()
    update_players()
    update_powerups()
    spawn_enemies()
    update_enemies()
    update_shots()
    update_explosions()
    check_hit()
    check_plane_hit()
    draw_stats()
    draw_game_message()
    present_screen()
    game_clock.tick(41.6)
