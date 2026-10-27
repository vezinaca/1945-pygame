"""Headless regression checks; run with .venv/bin/python -m unittest discover -s tests."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame


class GameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.previous_cwd = Path.cwd()
        os.chdir(root)
        cls.game = {}
        source = (root / 'game.py').read_text().split('# MAIN MENU LOOP')[0]
        exec(compile(source, 'game.py', 'exec'), cls.game)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()
        os.chdir(cls.previous_cwd)

    def setUp(self):
        g = self.game
        for name in ('players', 'enemies', 'shots', 'explosions', 'background'):
            g[name].clear()
        g['p1'] = g['Player']()
        g['respawn_at'] = None
        g['players'].append(g['p1'])
        g['reset_powerups']()

    def enemy(self, position):
        enemy = self.game['Enemy']()
        enemy.rect.topleft = position
        self.game['enemies'].append(enemy)
        return enemy

    def shot(self, kind, position):
        shot = self.game['Fire'](kind)
        shot.rect.topleft = position
        self.game['shots'].append(shot)
        return shot

    def test_enemy_bullet_does_not_hit_enemy(self):
        g = self.game
        self.enemy((10, 10))
        self.shot(1, (10, 10))
        g['check_hit']()
        self.assertEqual(len(g['enemies']), 1)
        self.assertEqual(g['p1'].score, 0)

    def test_player_bullet_hits_once_and_all_shots_processed(self):
        g = self.game
        for pos in ((10, 10), (100, 10)):
            self.enemy(pos)
            self.shot(0, pos)
        g['check_hit']()
        self.assertEqual(g['p1'].score, 200)
        self.assertFalse(g['enemies'])
        self.assertFalse(g['shots'])

    def test_enemy_bullet_hits_without_enemies(self):
        g = self.game
        self.shot(1, g['p1'].rect.center)
        g['check_hit']()
        self.assertFalse(g['players'])
        self.assertEqual(g['p1'].lives, 2)

    def test_bullet_in_transparent_corner_does_not_hit_player(self):
        g = self.game
        shot = self.shot(1, g['p1'].rect.topleft)
        self.assertTrue(g['p1'].rect.colliderect(shot.rect))
        g['check_hit']()
        self.assertEqual(g['players'], [g['p1']])
        self.assertEqual(g['p1'].lives, 3)
        self.assertIn(shot, g['shots'])

    def test_player_bullet_cannot_hit_player(self):
        g = self.game
        self.shot(0, g['p1'].rect.topleft)
        g['check_hit']()
        self.assertEqual(len(g['players']), 1)

    def test_respawn_preserves_enemies_and_stats(self):
        g = self.game
        g['p1'].score = 500
        g['destroy_player'](g['p1'])
        for i in range(4):
            self.enemy((i * 40, 20))
        surviving_enemies = g['enemies'][:]
        surviving_shot = self.shot(1, (0, 0))
        g['create_player']()
        self.assertIs(g['p1'], g['players'][0])
        self.assertEqual((g['p1'].score, g['p1'].lives), (500, 2))
        self.assertEqual(g['enemies'], surviving_enemies)
        self.assertEqual(g['shots'], [surviving_shot])
        g['destroy_player'](g['p1'])
        g['create_player']()
        g['destroy_player'](g['p1'])
        g['create_player']()
        self.assertEqual((g['p1'].score, g['p1'].lives), (0, 3))
        self.assertFalse(g['enemies'])

    def test_cleanup(self):
        g = self.game
        for i in range(4):
            self.shot(i % 2, (0, -100 if i % 2 == 0 else 500))
            self.enemy((0, 500))
            g['create_explosion'](i % 2, 0, 0)
        for explosion in g['explosions']:
            explosion.anim.ticks -= 1000
        g['update_shots']()
        g['update_enemies']()
        g['update_explosions']()
        for name in ('shots', 'enemies', 'explosions'):
            self.assertFalse(g[name], name)

    def test_bombs(self):
        g = self.game
        g['p1'].bombs = 1
        for i in range(4):
            self.enemy((i * 40, 20))
            self.shot(1, (i * 40, 60))
        friendly = self.shot(0, (0, 200))
        g['use_bomb']()
        g['use_bomb']()
        self.assertEqual(g['p1'].bombs, 0)
        self.assertEqual(g['p1'].score, 400)
        self.assertFalse(g['enemies'])
        self.assertEqual(g['shots'], [friendly])

    def test_bounds_and_rendering(self):
        g = self.game
        for position in ((-100, -100), (500, 600)):
            g['p1'].rect.topleft = position
            g['p1'].update()
            self.assertTrue(g['screen'].get_rect().contains(g['p1'].rect))
        g['menu_screen'].update()
        g['draw_stats']()
        g['present_screen']()
        self.assertEqual(g['window'].get_size(), (768, 1152))

    def test_bomber_health_and_score(self):
        g = self.game
        enemy = g['Enemy']('bomber')
        enemy.rect.topleft = (10, 10)
        g['enemies'].append(enemy)
        for hit in range(3):
            self.shot(0, (10, 10))
            g['check_hit']()
            self.assertEqual(enemy.health, 2 - hit)
            self.assertEqual(g['p1'].score, 300 if hit == 2 else 0)
        self.assertFalse(g['enemies'])

    def test_bomber_flashes_red_with_one_hit_remaining(self):
        g = self.game
        bomber = g['Enemy']('bomber')
        bomber.rect.topleft = (0, 0)
        bomber.health = 1
        # Keep the animation fixed while comparing the two flash phases.
        bomber.anim.ticks = 100
        bomber.anim.ticks_remaining = 1000
        normal = pygame.Surface(bomber.rect.size)
        flashing = pygame.Surface(bomber.rect.size)
        with patch.object(pygame.time, 'get_ticks', return_value=100):
            bomber.draw(normal)
        with patch.object(pygame.time, 'get_ticks', return_value=200):
            bomber.draw(flashing)
        normal_pixels = pygame.image.tobytes(normal, 'RGB')
        flash_pixels = pygame.image.tobytes(flashing, 'RGB')
        self.assertGreater(sum(flash_pixels[0::3]), sum(normal_pixels[0::3]))
        self.assertEqual(flash_pixels[1::3], normal_pixels[1::3])
        self.assertEqual(flash_pixels[2::3], normal_pixels[2::3])
        for frame, damaged in zip(g['enemy_types']['bomber']['frames'],
                                  bomber.damaged_frames):
            self.assertEqual(pygame.mask.from_surface(frame).count(),
                             pygame.mask.from_surface(damaged).count())

    def test_large_enemy_planes_are_distinct_and_take_three_hits(self):
        g = self.game
        player_pixels = pygame.image.tobytes(g['p1'].image, 'RGB')
        for kind in ('bomber', 'interceptor'):
            enemy = g['Enemy'](kind)
            self.assertNotEqual(pygame.image.tobytes(enemy.image, 'RGB'), player_pixels)
            self.assertEqual(enemy.health, 3)
            self.assertEqual(len(enemy.damaged_frames), 3)
            enemy.rect.topleft = (10, 10)
            g['enemies'].append(enemy)
            for remaining in (2, 1, 0):
                self.shot(0, (10, 10))
                g['check_hit']()
                self.assertEqual(enemy.health, remaining)
                self.assertEqual(enemy in g['enemies'], remaining > 0)

    def test_enemy_variants_move_fire_and_spawn(self):
        g = self.game
        for kind, spec in g['enemy_types'].items():
            g['shots'].clear()
            enemy = g['Enemy'](kind)
            enemy.rect.topleft = (100, 100)
            for _ in range(3):
                enemy.update()
            self.assertEqual(enemy.rect.y, 100 + 3 * spec['speed'])
            self.assertEqual(len(g['shots']), 2 if kind == 'bomber' else 1)
            if kind == 'scout':
                self.assertNotEqual(enemy.rect.x, 100)
            if kind == 'bomber':
                enemy.rect.y = 220
                enemy.update()
                self.assertEqual(len(g['shots']), 4)
            with patch.object(g['random'], 'choices', return_value=[kind]):
                g['create_enemy']()
            spawned = g['enemies'][-1]
            self.assertEqual(spawned.kind, kind)
            self.assertGreaterEqual(spawned.rect.left, 0)
            self.assertLessEqual(spawned.rect.right, 320)

    def test_boat_health_firing_and_bomb(self):
        g = self.game
        boat = g['Enemy']('boat')
        g['enemies'].append(boat)
        for height in (60, 160, 260):
            boat.rect.topleft = (50, height)
            boat.update()
        self.assertEqual(len(g['shots']), 3)
        for _ in range(3):
            self.shot(0, boat.rect.topleft)
            g['check_hit']()
        self.assertEqual(boat.health, 1)
        self.assertIn(boat, g['enemies'])
        self.assertEqual(g['p1'].score, 0)
        g['use_bomb']()
        self.assertFalse(g['enemies'])
        self.assertFalse(g['shots'])
        self.assertEqual(g['p1'].score, 400)

    def test_automatic_respawn_delay(self):
        g = self.game
        g['p1'].score = 250
        with patch.object(pygame.time, 'get_ticks', return_value=1000):
            g['destroy_player'](g['p1'])
        self.assertEqual(g['respawn_at'], 2500)
        with patch.object(pygame.time, 'get_ticks', return_value=2499):
            g['update_respawn']()
            g['draw_game_message']()
            g['handle_event'](pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1))
            self.assertFalse(g['players'])
        with patch.object(pygame.time, 'get_ticks', return_value=2500):
            g['update_respawn']()
        self.assertEqual(g['players'], [g['p1']])
        self.assertEqual((g['p1'].lives, g['p1'].score), (2, 250))
        self.assertIsNone(g['respawn_at'])

    def test_spawn_rejects_occupied_positions(self):
        g = self.game
        existing = self.enemy((10, -100))
        with patch.object(g['random'], 'randrange', side_effect=[10, -100] * 20):
            g['create_enemy']()
        self.assertEqual(g['enemies'], [existing])
        for _ in range(50):
            g['create_enemy']()
        for index, enemy in enumerate(g['enemies']):
            for other in g['enemies'][index + 1:]:
                self.assertFalse(enemy.rect.colliderect(other.rect))

    def test_respawn_waits_for_approaching_bullets_and_enemies(self):
        g = self.game
        with patch.object(pygame.time, 'get_ticks', return_value=1000):
            g['destroy_player'](g['p1'])
        bullet = self.shot(1, (150, 260))
        with patch.object(pygame.time, 'get_ticks', return_value=3000):
            g['update_respawn']()
            self.assertFalse(g['players'])
            bullet.rect.y = 440
            enemy = self.enemy((140, 330))
            g['update_respawn']()
            self.assertFalse(g['players'])
            enemy.rect.y = 440
            g['update_respawn']()
        self.assertEqual(g['players'], [g['p1']])
        self.assertIn(bullet, g['shots'])
        self.assertIn(enemy, g['enemies'])

    def test_game_over_stays_until_restart(self):
        g = self.game
        g['p1'].lives = 1
        g['destroy_player'](g['p1'])
        with patch.object(pygame.time, 'get_ticks', return_value=999999):
            g['update_respawn']()
            g['draw_game_message']()
        self.assertFalse(g['players'])
        self.assertIsNone(g['respawn_at'])
        g['handle_event'](pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1))
        self.assertEqual(g['p1'].lives, 3)
        self.assertEqual(g['players'], [g['p1']])

    def test_scenery_scrolls_and_recycles(self):
        g = self.game
        g['update_water']()
        g['update_background']()
        self.assertEqual(len(g['background']), 4)
        self.assertEqual({item.kind for item in g['background']}, {0, 1, 2})
        for item in g['background']:
            self.assertEqual(item.image.get_size(), (64, 65))
            self.assertGreaterEqual(item.x, 0)
            self.assertLessEqual(item.x + item.image.get_width(), 320)
        departing = g['background'][-1]
        departing.y = 480
        g['update_background']()
        self.assertNotIn(departing, g['background'])
        self.assertEqual(len(g['background']), 4)
        self.assertLess(g['background'][-1].y, 0)
        for _ in range(1200):
            g['update_background']()
        self.assertEqual(len(g['background']), 4)
        self.assertEqual(len(g['enemies']), 0)

    def test_pow_pickup_and_three_way_fire(self):
        g = self.game
        g['powerups'][:] = [g['PowerUp']()]
        g['create_shot'](0, 130, 350)
        self.assertEqual(len(g['shots']), 1)
        g['shots'].clear()
        g['update_powerups']()
        self.assertFalse(g['p1'].spread_shot)
        g['p1'].rect.center = g['powerups'][0].rect.center
        g['update_powerups']()
        self.assertTrue(g['p1'].spread_shot)
        self.assertFalse(g['powerups'])
        g['handle_event'](pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertEqual(len(g['shots']), 3)
        for shot in g['shots']:
            self.assertAlmostEqual(shot.velocity.length(), 20)
            self.assertLess(shot.velocity.y, 0)
            if shot.velocity.x:
                self.assertAlmostEqual(
                    abs(pygame.Vector2(0, -1).angle_to(shot.velocity)), 10)
        self.assertEqual(sum(shot.velocity.x == 0 for shot in g['shots']), 1)
        self.assertTrue(any(shot.velocity.x < 0 for shot in g['shots']))
        self.assertTrue(any(shot.velocity.x > 0 for shot in g['shots']))
        g['destroy_player'](g['p1'])
        self.assertFalse(g['p1'].spread_shot)
        g['create_player']()
        self.assertFalse(g['p1'].spread_shot)
        g['p1'].lives = 1
        g['destroy_player'](g['p1'])
        g['create_player']()
        self.assertFalse(g['p1'].spread_shot)
        self.assertEqual(len(g['powerups']), 1)

    def test_pow_scrolls_with_background_and_leaves_screen(self):
        g = self.game
        pickup = g['powerups'][0]
        original_y = pickup.rect.y
        g['update_powerups']()
        self.assertEqual(pickup.rect.y, original_y + 1)
        pickup.rect.top = 479
        g['update_powerups']()
        self.assertNotIn(pickup, g['powerups'])

    def test_starting_pow_grants_animated_wingmen(self):
        g = self.game
        self.assertEqual(g['powerups'][0].kind, 'wingmen')
        g['p1'].rect.center = g['powerups'][0].rect.center
        with patch.object(pygame.time, 'get_ticks', return_value=1000):
            g['update_powerups']()
            incoming = g['p1'].wingman_rects()
            self.assertTrue(g['p1'].wingmen)
            self.assertFalse(g['p1'].spread_shot)
            self.assertLess(incoming[0].right, 0)
            self.assertGreater(incoming[1].left, 320)
        with patch.object(pygame.time, 'get_ticks', return_value=1600):
            rects = g['p1'].wingman_rects()
            self.assertLess(rects[0].centerx, g['p1'].rect.centerx)
            self.assertGreater(rects[1].centerx, g['p1'].rect.centerx)
            g['p1'].draw(g['screen'])
            g['create_shot'](0, g['p1'].rect.x, g['p1'].rect.y)
            self.assertEqual(len(g['shots']), 3)
            self.assertTrue(all(shot.velocity.x == 0 for shot in g['shots']))
            self.assertEqual([shot.rect.centerx for shot in g['shots'][1:]],
                             [rect.centerx for rect in rects])
            g['p1'].spread_shot = True
            g['shots'].clear()
            g['create_shot'](0, g['p1'].rect.x, g['p1'].rect.y)
            self.assertEqual(len(g['shots']), 5)
        for animation in g['p1'].wingman_animations:
            self.assertEqual(len(animation.data), 3)
            self.assertTrue(all(frame.get_size() == (20, 20)
                                for _, frame in animation.data))
        g['destroy_player'](g['p1'])
        g['create_player']()
        self.assertFalse(g['p1'].wingmen)

    def test_enemy_bullets_destroy_wingmen_individually(self):
        g = self.game
        player = g['p1']
        player.rect.center = g['powerups'][0].rect.center
        with patch.object(pygame.time, 'get_ticks', return_value=1000):
            g['update_powerups']()
        with patch.object(pygame.time, 'get_ticks', return_value=1600):
            for index in range(2):
                rect = player.wingman_rects()[index]
                shot = self.shot(1, rect.topleft)
                shot.rect.center = rect.center
                g['check_hit']()
                self.assertFalse(player.wingmen_alive[index])
                self.assertNotIn(shot, g['shots'])
                self.assertEqual(player.lives, 3)
                self.assertEqual(g['players'], [player])
                self.assertEqual(player.wingmen, index == 0)
                g['create_shot'](0, player.rect.x, player.rect.y)
                self.assertEqual(len(g['shots']), 2 if index == 0 else 1)
                g['shots'].clear()
                player.draw(g['screen'])
        self.assertEqual(len(g['explosions']), 2)

    def test_new_pow_offers_complementary_upgrade(self):
        g = self.game
        player = g['p1']
        self.assertEqual(g['powerups'][0].kind, 'wingmen')
        player.spread_shot = True
        pickup = g['PowerUp'](center=player.rect.center)
        self.assertEqual(pickup.kind, 'wingmen')
        g['powerups'][:] = [pickup]
        g['update_powerups']()
        self.assertTrue(player.wingmen)
        self.assertTrue(player.spread_shot)
        player.spread_shot = False
        pickup = g['PowerUp'](center=player.rect.center)
        self.assertEqual(pickup.kind, 'spread')
        g['powerups'][:] = [pickup]
        g['update_powerups']()
        self.assertTrue(player.spread_shot)
        self.assertTrue(player.wingmen)

    def test_pow_has_no_effect_with_both_upgrades(self):
        g = self.game
        player = g['p1']
        player.spread_shot = True
        player.wingmen = True
        player.wingmen_alive = [True, False]
        player.wingmen_arrived_at = 123
        pickup = g['PowerUp'](center=player.rect.center)
        self.assertEqual(pickup.kind, 'none')
        g['powerups'][:] = [pickup]
        g['update_powerups']()
        self.assertFalse(g['powerups'])
        self.assertTrue(player.spread_shot)
        self.assertTrue(player.wingmen)
        self.assertEqual(player.wingmen_alive, [True, False])
        self.assertEqual(player.wingmen_arrived_at, 123)

    def test_spread_bullets_removed_at_side_edges(self):
        g = self.game
        for x, angle in ((-40, -45), (340, 45)):
            shot = g['Fire'](0, angle)
            shot.rect.topleft = (x, 200)
            g['shots'].append(shot)
        g['update_shots']()
        self.assertFalse(g['shots'])

    def test_formation_flies_single_file_and_turns_horizontal(self):
        g = self.game
        self.assertTrue(g['spawn_formation']())
        planes = g['enemies'][:]
        self.assertEqual(len(planes), 4)
        for plane in planes:
            for frame in plane.base_frames:
                opaque_colors = [frame.get_at((x, y))
                                 for y in range(frame.get_height())
                                 for x in range(frame.get_width())
                                 if frame.get_at((x, y)).a]
                self.assertTrue(any(color.r > color.g for color in opaque_colors))
                self.assertTrue(all(color.r >= color.g and color.r >= color.b
                                    for color in opaque_colors))
        self.assertEqual(len({plane.rect.centerx for plane in planes}), 1)
        for first, second in zip(planes, planes[1:]):
            self.assertEqual(first.rect.centery - second.rect.centery, 54)
            self.assertFalse(first.rect.colliderect(second.rect))
        leader = planes[0]
        for _ in range(125):
            leader.update()
        previous = leader.rect.center
        leader.update()
        self.assertEqual(leader.rect.centery, previous[1])
        self.assertEqual(abs(leader.rect.centerx - previous[0]), 3)

    def test_shooting_all_four_formation_planes_drops_pow(self):
        g = self.game
        g['powerups'].clear()
        g['spawn_formation']()
        for index, plane in enumerate(g['enemies'][:]):
            plane.rect.topleft = (60, 100)
            self.shot(0, plane.rect.topleft)
            g['check_hit']()
            self.assertEqual(len(g['powerups']), 1 if index == 3 else 0)
        self.assertEqual(g['powerups'][0].rect.center, (76, 116))

    def test_formation_bomb_or_escape_prevents_reward(self):
        g = self.game
        for failure in ('bomb', 'escape'):
            g['enemies'].clear()
            g['powerups'].clear()
            g['spawn_formation']()
            first = g['enemies'][0]
            if failure == 'bomb':
                g['use_bomb']()
            else:
                first.age = 500
                first.update()
                for plane in g['enemies'][:]:
                    g['destroy_enemy'](plane, award_points=True, shot_down=True)
            self.assertFalse(g['powerups'])

    def test_regular_planes_curve_then_fly_horizontal_and_exit(self):
        g = self.game
        for kind in ('scout', 'bomber', 'blue_fighter', 'silver_diver'):
            enemy = g['Enemy'](kind)
            enemy.rect.center = (80, -40)
            enemy.enable_curve()
            enemy.curve['turn_y'] = 140
            g['enemies'].append(enemy)
            while enemy.curve['distance'] < 180 + 80 * 3.141592653589793 / 2:
                enemy.update()
            previous = enemy.rect.center
            enemy.update()
            self.assertEqual(enemy.rect.centery, previous[1])
            self.assertEqual(enemy.rect.centerx - previous[0], enemy.speed)
            if enemy.damaged_frames:
                self.assertEqual(enemy.damaged_frames[0].get_size(),
                                 enemy.anim.data[0][1].get_size())
            for _ in range(150):
                if enemy not in g['enemies']:
                    break
                enemy.update()
            self.assertNotIn(enemy, g['enemies'])

    def test_events_and_plane_collision(self):
        g = self.game
        g['handle_event'](pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN), True)
        self.assertEqual(g['menu_screen'].exit, 1)
        self.enemy(g['p1'].rect.topleft)
        self.enemy(g['p1'].rect.topleft)
        g['check_plane_hit']()
        self.assertEqual(g['p1'].lives, 2)
        self.assertFalse(g['players'])
        for menu in (True, False):
            for event in (pygame.event.Event(pygame.QUIT),
                          pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)):
                with patch.object(pygame, 'quit'), self.assertRaises(SystemExit):
                    g['handle_event'](event, menu)


if __name__ == '__main__':
    unittest.main()
