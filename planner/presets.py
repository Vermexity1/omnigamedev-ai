from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GamePreset:
    name: str
    triggers: tuple[str, ...]
    modules: tuple[str, ...]
    systems: tuple[str, ...]
    assets: tuple[str, ...]


PRESETS: tuple[GamePreset, ...] = (
    GamePreset(
        name="dungeon crawler",
        triggers=("dungeon", "rogue", "roguelike", "boss", "rpg"),
        modules=("procedural dungeon map", "enemy AI", "boss encounter system"),
        systems=("AI steering", "combat resolution"),
        assets=("room and corridor tiles", "boss placeholder model", "dungeon wall texture"),
    ),
    GamePreset(
        name="platformer",
        triggers=("platformer", "platform", "jump", "side scroller"),
        modules=("jump controller", "platform collision", "checkpoint system"),
        systems=("gravity", "hazard resolution"),
        assets=("platform collision", "checkpoint marker", "hazard marker"),
    ),
    GamePreset(
        name="fps",
        triggers=("fps", "shooter", "gun", "weapon"),
        modules=("camera controller", "weapon controller", "target spawner"),
        systems=("raycast combat", "ammo state"),
        assets=("weapon placeholder", "target material", "crosshair"),
    ),
    GamePreset(
        name="puzzle",
        triggers=("puzzle", "logic", "match", "board"),
        modules=("board state", "move validator", "win condition"),
        systems=("undo stack", "hint scoring"),
        assets=("tile set", "success marker", "blocked marker"),
    ),
    GamePreset(
        name="racing",
        triggers=("racing", "race", "car", "vehicle"),
        modules=("vehicle controller", "lap timer", "checkpoint gates"),
        systems=("track boundaries", "drift scoring"),
        assets=("vehicle placeholder", "track markers", "checkpoint texture"),
    ),
)


def preset_for_request(request: str) -> GamePreset:
    lowered = request.lower()
    for preset in PRESETS:
        if any(trigger in lowered for trigger in preset.triggers):
            return preset
    return GamePreset(
        name="arcade",
        triggers=(),
        modules=("score system", "restart flow"),
        systems=("arcade state machine",),
        assets=("score badge",),
    )
