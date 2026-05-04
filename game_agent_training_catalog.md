# OmniGameDev AI Game Agent Training Catalog

This catalog teaches OmniGameDev AI how to map natural-language game requests to concrete code edits. It is seed context for the retrieval memory and a deterministic engineering guide for the project assistant.

## Core Rule

When a user asks to change gameplay, visuals, camera, controls, physics, materials, or difficulty, edit the implementation files that create those systems. Do not satisfy the request by only changing README text, HUD copy, comments, project descriptions, or labels.

Examples:

- "Make it first person" means camera transform, input/mouse-look, player visibility, and movement vectors.
- "Make walls green" means the wall material, mesh material, tile draw color, or sprite color.
- "Make enemies faster" means enemy speed constants or movement update math.
- "Add jumping" means vertical velocity, grounded checks, gravity, and collision response.
- "Make the game darker" means scene background, fog, lighting intensity, post-processing, or palette.
- "Make movement smoother" means delta-time scaling, acceleration, damping, and collision handling.

## Source File Targeting

For Three.js browser games:

- `src/main.js` usually contains scene, camera, player, enemies, walls, collision, controls, animation loop, materials, and lights.
- `src/style.css` usually contains HUD, canvas, overlay, and responsive layout styles.
- `index.html` should rarely change unless adding import maps, root containers, or scripts.
- `README.md` is documentation only; changing it does not implement gameplay.
- `package.json` is for scripts and dependencies.

For Pygame games:

- `main.py` usually contains the main loop, actor classes, movement, draw calls, colors, collision, and input.
- `requirements.txt` only changes when adding dependencies.
- SVG assets can change visuals, but if walls/enemies are drawn procedurally in code, edit code first.

For Unity games:

- `Assets/Scripts/PlayerController.cs` owns movement, camera-dependent movement, health, attacks, input, and jumping.
- `Assets/Scripts/EnemyAI.cs` owns enemy chase, attack, detection range, boss behavior, and damage.
- Materials belong in Unity assets, but generated script-only projects often need exposed color fields or setup notes.

For C++ prototypes:

- `main.cpp` owns simulation logic, map layout, actor state, and game loop.
- `CMakeLists.txt` owns build setup only.

## Colors And Materials

Natural language color requests must map to actual render colors.

Common color map:

- green: `0x22c55e`, RGB `(34, 197, 94)`
- lime: `0x84cc16`, RGB `(132, 204, 22)`
- emerald: `0x10b981`, RGB `(16, 185, 129)`
- red: `0xef4444`, RGB `(239, 68, 68)`
- blue: `0x3b82f6`, RGB `(59, 130, 246)`
- cyan: `0x06b6d4`, RGB `(6, 182, 212)`
- teal: `0x14b8a6`, RGB `(20, 184, 166)`
- purple: `0x8b5cf6`, RGB `(139, 92, 246)`
- yellow: `0xfacc15`, RGB `(250, 204, 21)`
- orange: `0xf97316`, RGB `(249, 115, 22)`
- white: `0xf8fafc`, RGB `(248, 250, 252)`
- black: `0x020617`, RGB `(2, 6, 23)`
- gray: `0x64748b`, RGB `(100, 116, 139)`

Three.js material edit examples:

- Wall color: change `const wallMaterial = material(0x...)`.
- Floor color: change `const floorMaterial = material(0x...)`.
- Enemy color: change `const enemyMaterial = material(0x...)`.
- Boss color: change `const bossMaterial = material(0x...)`.
- Player color: change the material passed to the player mesh.
- Background color: change `scene.background = new THREE.Color(0x...)`.
- Fog color: change `scene.fog = new THREE.Fog(0x..., near, far)`.

Pygame color edit examples:

- Procedural walls: change `pygame.draw.rect(screen, (r, g, b), wall)`.
- Player/enemy actor color: change actor color tuples.
- Background: change `screen.fill((r, g, b))`.

Never implement a visual color request by editing only text such as `status = "green walls"` or README descriptions.

## Shapes And Meshes

Shape requests map to geometry or drawing primitives.

Three.js:

- cube/block/box: `THREE.BoxGeometry`
- sphere/orb: `THREE.SphereGeometry`
- capsule/player body: `THREE.CapsuleGeometry`
- cylinder/pillar: `THREE.CylinderGeometry`
- cone/spike: `THREE.ConeGeometry`
- torus/ring/portal: `THREE.TorusGeometry`
- gem/crystal: `THREE.OctahedronGeometry`

Pygame:

- rectangle/block: `pygame.draw.rect`
- circle/orb: `pygame.draw.circle`
- polygon/spike: `pygame.draw.polygon`
- image/sprite: load or generate an asset, then blit it.

If the request says "make enemies spheres," edit enemy mesh creation. If it says "make pickups crystals," use octahedron/gem geometry or a polygon sprite.

## Camera And POV

Third-person camera:

- Camera follows behind and above the player.
- Player mesh remains visible.
- Movement can be world-axis or camera-relative.
- Three.js pattern: `camera.position.lerp(new THREE.Vector3(player.x + offsetX, height, player.z + offsetZ), smoothing)` and `camera.lookAt(player.position)`.

First-person camera:

- Camera sits at player head height.
- Player body is hidden or only hands/weapon are shown.
- Mouse movement controls yaw and pitch.
- WASD movement should be relative to camera yaw, not fixed world axes.
- Pointer lock improves browser mouse look.
- Three.js pattern: store `pointer = { yaw, pitch }`; set `camera.rotation.order = "YXZ"`; set `camera.rotation.y = pointer.yaw`; set `camera.rotation.x = pointer.pitch`.

Top-down camera:

- Camera sits above the world and looks downward.
- Movement is usually screen/world axes.
- Use orthographic camera for tactical/pixel style or perspective for diorama style.

Side-view/platformer camera:

- Camera follows x/y, not z.
- Movement includes gravity and jumping.
- Collision is usually tile/platform based.

Never satisfy a POV request by only changing HUD text. A camera request requires camera transform and usually input math.

## Movement

Movement requests change actor update logic.

WASD:

- W forward, S backward, A strafe/left, D strafe/right.
- In first person, forward/right vectors come from yaw.
- Use delta time: `speed * delta`.

Smoother movement:

- Add velocity vector.
- Accelerate toward desired direction.
- Apply damping/friction when no input.
- Keep collision separate from input.

Faster/slower movement:

- Change player speed constants, not just text.
- Keep speed bounded so collision remains stable.

Jumping:

- Add `velocity.y`.
- Add `isGrounded`.
- Space applies upward impulse only when grounded.
- Gravity decreases vertical velocity over time.
- Resolve vertical collision separately from horizontal collision.

Dash:

- Add cooldown.
- Add burst velocity in facing/input direction.
- Prevent repeated dash every frame.

Swimming/flying:

- Allow vertical movement keys or pitch-relative forward.
- Adjust gravity and damping.

## Collision And Physics

Collision must be functional, not decorative.

Three.js simple dungeon collision:

- Walls are axis-aligned blocks.
- Keep a list of wall meshes or bounding boxes.
- Predict next position and reject/slide if too close.
- Use separate x and z collision for smoother sliding if possible.

Pygame tile collision:

- Move x, resolve x collision.
- Move y, resolve y collision.
- Avoid diagonal tunneling by resolving axes separately.

Physics vocabulary:

- gravity: downward acceleration
- friction/damping: slows velocity
- acceleration: change in velocity over time
- bounce: invert velocity on collision
- knockback: impulse away from attacker

## Combat And AI

Enemy AI requests should edit behavior loops:

- detection range: distance threshold before chase
- chase speed: enemy speed
- attack range: distance threshold for damage
- attack cooldown: time gate between attacks
- patrol: waypoints or wandering direction
- boss phase: behavior changes at health thresholds

Boss requests:

- more health: boss health constant
- stronger: damage constant
- phases: if health less than 50%, increase speed or spawn minions
- arena: layout/map edits

Never implement enemy/boss changes only through labels or README descriptions.

## UI And Feedback

HUD text is useful only as feedback after the real behavior exists.

Good HUD changes:

- show health, ammo, score, objective, cooldown, boss health
- update status when collecting items or winning
- show control hints that match implemented controls

Bad HUD-only changes:

- "first person mode" text without first-person camera
- "green walls" text without green materials
- "jump enabled" text without jump physics

## Asset Generation

Placeholder assets should help the game read visually:

- walls: stone/brick tiles
- floor: darker neutral tile
- enemies: warm high-contrast silhouettes
- player: cool high-contrast silhouette
- boss: larger, threatening color
- pickups: emissive gems or clear icons

When a request asks for graphics, use geometry, materials, lights, sprites, particles, or textures. Documentation is not graphics.

## Verification Rules

After an edit:

- Run syntax/smoke checks.
- Confirm changed files are implementation files.
- If changing POV, verify camera code changed.
- If changing color, verify material/draw constants changed.
- If changing movement, verify movement constants or vector math changed.
- Report changed files and the implemented system.

Benchmark cases for a Three.js dungeon:

1. "Make it first person." Expected: `src/main.js` has first-person camera, pointer yaw/pitch, pointer lock, and camera-relative movement.
2. "Make the walls green." Expected: `wallMaterial` color is `0x22c55e` or another green constant.
3. "Make the player faster." Expected: player speed in `new Combatant(playerMesh, 100, ...)` increases.
4. "Make it darker and spookier." Expected: fog/lighting/background changes, not only text.
5. "Make enemies blue." Expected: enemy material changes to blue.

## Honest Model Boundary

OmniGameDev AI is an agent application, not a foundation model. It can be improved with prompts, retrieval memory, deterministic tools, code analysis, tests, and LLM provider integration. It cannot become GPT-5.2 by writing a markdown file. Any benchmark comparison to OpenAI models must run actual model calls with the same tasks, scoring rules, and environment. If no API key or model access is available, report "not run" instead of inventing scores.
