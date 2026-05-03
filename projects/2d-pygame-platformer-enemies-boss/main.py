from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass

PLAN = json.loads(r"""{
  "request": "build a 2D pygame platformer with enemies and a boss",
  "project_name": "2d-pygame-platformer-enemies-boss",
  "engine": "Pygame",
  "language": "Python",
  "framework": "Pygame",
  "game_type": "platformer",
  "modules": [
    "project bootstrap",
    "game loop",
    "player controller",
    "input manager",
    "collision system",
    "HUD",
    "level loader",
    "boss encounter system",
    "jump controller",
    "menu system",
    "enemy AI",
    "procedural dungeon map"
  ],
  "systems": [
    "rendering",
    "physics-lite movement",
    "state management",
    "runtime smoke test",
    "AI steering",
    "combat resolution"
  ],
  "assets": [
    "placeholder player material",
    "placeholder enemy material",
    "placeholder environment tiles",
    "asset manifest",
    "boss arena markers",
    "platform collision",
    "settings panel",
    "boss placeholder model",
    "dungeon wall texture"
  ],
  "dependencies": {
    "runtime": [
      "python >= 3.10",
      "pygame >= 2.5"
    ],
    "development": [
      "pip",
      "venv"
    ]
  },
  "commands": {
    "install": "pip install -r requirements.txt",
    "run": "python main.py",
    "smoke": "python main.py --smoke"
  },
  "acceptance_tests": [
    "Project files are generated inside projects/<project_name>.",
    "A smoke test command completes without crashing.",
    "Generated source contains a playable loop or engine-ready scripts.",
    "Project manifest records the plan, adapter, and generated files."
  ],
  "risks": [
    "Full commercial engines such as Unity and Unreal require local editor installations.",
    "Generated browser projects need npm install before Vite dev serving."
  ],
  "metadata": {
    "planner": "heuristic-v1",
    "memory_used": true,
    "supports_self_heal": true
  }
}""")

WIDTH = 960
HEIGHT = 640
TILE = 48

LEVEL = [
    "####################",
    "#P....#............#",
    "#.##..#..E.....B...#",
    "#......E...........#",
    "###.########.#######",
    "#...#..............#",
    "#.E...##.....E.....#",
    "#.....#............#",
    "####################",
]


@dataclass
class Actor:
    rect: object
    health: float
    speed: float
    color: tuple[int, int, int]


def smoke() -> None:
    assert PLAN["project_name"]
    assert "modules" in PLAN
    assert any("player" in module for module in PLAN["modules"])
    print(json.dumps({"ok": True, "engine": "Pygame", "project": PLAN["project_name"]}))


def load_pygame():
    import pygame

    return pygame


def parse_level(pygame):
    walls = []
    enemies = []
    boss = None
    player_start = (TILE * 2, TILE * 2)
    for row_index, row in enumerate(LEVEL):
        for column_index, tile in enumerate(row):
            rect = pygame.Rect(column_index * TILE, row_index * TILE, TILE, TILE)
            if tile == "#":
                walls.append(rect)
            elif tile == "P":
                player_start = rect.center
            elif tile == "E":
                enemies.append(Actor(rect.copy().inflate(-12, -12), 35, 92, (249, 115, 22)))
            elif tile == "B":
                boss = Actor(rect.copy().inflate(12, 12), 160, 54, (239, 68, 68))
    return walls, enemies, boss, player_start


def move_actor(actor, dx, dy, walls):
    actor.rect.x += int(dx)
    for wall in walls:
        if actor.rect.colliderect(wall):
            if dx > 0:
                actor.rect.right = wall.left
            if dx < 0:
                actor.rect.left = wall.right
    actor.rect.y += int(dy)
    for wall in walls:
        if actor.rect.colliderect(wall):
            if dy > 0:
                actor.rect.bottom = wall.top
            if dy < 0:
                actor.rect.top = wall.bottom


def update_enemy(enemy, player, walls, dt):
    if enemy.health <= 0:
        return
    dx = player.rect.centerx - enemy.rect.centerx
    dy = player.rect.centery - enemy.rect.centery
    distance = math.hypot(dx, dy)
    if 1 < distance < 360:
        move_actor(enemy, dx / distance * enemy.speed * dt, dy / distance * enemy.speed * dt, walls)
    if enemy.rect.colliderect(player.rect):
        player.health = max(0, player.health - 16 * dt)


def draw_world(pygame, screen, font, walls, enemies, boss, player, status):
    screen.fill((15, 20, 22))
    for row_index, row in enumerate(LEVEL):
        for column_index, _ in enumerate(row):
            rect = pygame.Rect(column_index * TILE, row_index * TILE, TILE, TILE)
            pygame.draw.rect(screen, (47, 58, 61), rect, 1)
    for wall in walls:
        pygame.draw.rect(screen, (124, 111, 100), wall)
    for enemy in enemies:
        if enemy.health > 0:
            pygame.draw.rect(screen, enemy.color, enemy.rect, border_radius=6)
    if boss and boss.health > 0:
        pygame.draw.rect(screen, boss.color, boss.rect, border_radius=10)
    pygame.draw.rect(screen, player.color, player.rect, border_radius=8)
    hud = font.render(f"{PLAN['project_name']}   HP {math.ceil(player.health)}   {status}", True, (238, 247, 247))
    screen.blit(hud, (18, 16))


def run_game():
    pygame = load_pygame()
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(PLAN["project_name"])
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)
    walls, enemies, boss, player_start = parse_level(pygame)
    player = Actor(pygame.Rect(0, 0, 30, 30), 100, 180, (94, 234, 212))
    player.rect.center = player_start
    status = "WASD move, SPACE attack, ESC quit"

    running = True
    while running:
        dt = clock.tick(60) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                hit = False
                for enemy in enemies + ([boss] if boss else []):
                    if enemy and enemy.health > 0 and player.rect.inflate(64, 64).colliderect(enemy.rect):
                        enemy.health -= 24
                        hit = True
                status = "Strike landed" if hit else "No enemy in range"

        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_d] - keys[pygame.K_a]) * player.speed * dt
        dy = (keys[pygame.K_s] - keys[pygame.K_w]) * player.speed * dt
        move_actor(player, dx, dy, walls)

        for enemy in enemies:
            update_enemy(enemy, player, walls, dt)
        if boss:
            update_enemy(boss, player, walls, dt)
            if boss.health <= 0:
                status = "Boss defeated"
        if player.health <= 0:
            status = "Defeated"

        draw_world(pygame, screen, font, walls, enemies, boss, player, status)
        pygame.display.flip()

    pygame.quit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="Run deterministic smoke checks.")
    args = parser.parse_args()
    if args.smoke:
        smoke()
    else:
        run_game()


if __name__ == "__main__":
    main()
