import * as THREE from "three";

const PLAN = {
  "request": "build a 3D dungeon game with bosses",
  "project_name": "3d-dungeon-bosses",
  "engine": "Three.js",
  "language": "JavaScript",
  "framework": "Three.js",
  "game_type": "dungeon crawler",
  "modules": [
    "project bootstrap",
    "game loop",
    "player controller",
    "input manager",
    "collision system",
    "HUD",
    "level loader",
    "procedural dungeon map",
    "enemy AI",
    "boss encounter system"
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
    "room and corridor tiles",
    "boss placeholder model",
    "dungeon wall texture"
  ],
  "dependencies": {
    "runtime": [
      "node >= 18",
      "three.js"
    ],
    "development": [
      "vite",
      "npm"
    ]
  },
  "commands": {
    "install": "npm install",
    "run": "npm run dev",
    "smoke": "node --check src/main.js"
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
    "preset": "dungeon crawler",
    "memory_used": true,
    "supports_self_heal": true
  }
};

const dungeonLayout = [
  "############",
  "#P....#....#",
  "#.##..#..B.#",
  "#......E...#",
  "###.####.###",
  "#...#......#",
  "#.E...##...#",
  "#.....#....#",
  "############",
];

const keys = new Set();
const clock = new THREE.Clock();

class Combatant {
  constructor(mesh, health, speed) {
    this.mesh = mesh;
    this.health = health;
    this.maxHealth = health;
    this.speed = speed;
  }
}

function material(color, roughness = 0.78) {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness: 0.04 });
}

function emissiveMaterial(color, intensity = 0.8) {
  return new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: intensity, roughness: 0.45 });
}

function createTorch(scene, x, z) {
  const group = new THREE.Group();
  const post = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.12, 1.2, 8), material(0x3b2f2f));
  const flame = new THREE.Mesh(new THREE.SphereGeometry(0.22, 14, 10), emissiveMaterial(0xfacc15, 1.4));
  const light = new THREE.PointLight(0xf59e0b, 2.6, 7, 1.7);
  post.position.y = 0.6;
  flame.position.y = 1.35;
  light.position.y = 1.35;
  group.add(post, flame, light);
  group.position.set(x, 0, z);
  scene.add(group);
  return { group, flame, light, seed: Math.random() * 100 };
}

function createPickup(scene, x, z, index) {
  const gem = new THREE.Mesh(new THREE.OctahedronGeometry(0.34), emissiveMaterial(index % 2 ? 0x5eead4 : 0xfacc15, 0.9));
  gem.position.set(x, 0.7, z);
  gem.castShadow = true;
  scene.add(gem);
  return gem;
}

function createPortal(scene) {
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.78, 0.08, 12, 32), emissiveMaterial(0x8b5cf6, 1.1));
  ring.position.set(8, 1.0, 6);
  ring.rotation.x = Math.PI / 2;
  scene.add(ring);
  return ring;
}

function tileToWorld(x, z) {
  return new THREE.Vector3((x - 6) * 2, 0, (z - 4) * 2);
}

function buildDungeon(scene) {
  const wallMaterial = material(0x7c6f64);
  const floorMaterial = material(0x2f3a3d);
  const enemyMaterial = material(0xf97316);
  const bossMaterial = material(0xef4444);
  const walls = [];
  const enemies = [];
  const decorativeLights = [];
  const pickups = [];
  let portal = null;
  let playerStart = new THREE.Vector3(0, 0, 0);
  let boss = null;

  const floor = new THREE.Mesh(new THREE.BoxGeometry(26, 0.18, 20), floorMaterial);
  floor.position.y = -0.12;
  floor.receiveShadow = true;
  scene.add(floor);

  decorativeLights.push(createTorch(scene, -8, -6), createTorch(scene, 8, -6), createTorch(scene, -8, 6), createTorch(scene, 8, 6));
  pickups.push(createPickup(scene, -4, -2, 0), createPickup(scene, 2, 4, 1), createPickup(scene, 6, -2, 2));
  portal = createPortal(scene);

  dungeonLayout.forEach((row, z) => {
    [...row].forEach((tile, x) => {
      const position = tileToWorld(x, z);
      if (tile === "#") {
        const wall = new THREE.Mesh(new THREE.BoxGeometry(2, 2.8, 2), wallMaterial);
        wall.position.set(position.x, 1.25, position.z);
        wall.castShadow = true;
        wall.receiveShadow = true;
        scene.add(wall);
        walls.push(wall);
      }
      if (tile === "P") {
        playerStart = position.clone();
      }
      if (tile === "E") {
        const enemy = new THREE.Mesh(new THREE.BoxGeometry(1.1, 1.1, 1.1), enemyMaterial);
        enemy.position.set(position.x, 0.55, position.z);
        enemy.castShadow = true;
        scene.add(enemy);
        enemies.push(new Combatant(enemy, 40, 1.1));
      }
      if (tile === "B") {
        const bossMesh = new THREE.Mesh(new THREE.BoxGeometry(1.8, 1.8, 1.8), bossMaterial);
        bossMesh.position.set(position.x, 0.9, position.z);
        bossMesh.castShadow = true;
        scene.add(bossMesh);
        boss = new Combatant(bossMesh, 180, 0.7);
      }
    });
  });

  return { walls, enemies, boss, playerStart, decorativeLights, pickups, portal };
}

function createHud(root) {
  const hud = document.createElement("div");
  hud.className = "hud";
  hud.innerHTML = `
    <strong>${PLAN.project_name}</strong>
    <span id="status">Explore the dungeon</span>
    <span id="health">HP 100</span>
  `;
  root.appendChild(hud);
  return {
    status: hud.querySelector("#status"),
    health: hud.querySelector("#health"),
  };
}

function updateCamera(camera, player) {
  const target = player.mesh.position;
  camera.position.lerp(new THREE.Vector3(target.x + 6, 7, target.z + 8), 0.08);
  camera.lookAt(target.x, 0.6, target.z);
}

function moveWithCollision(entity, deltaMove, walls) {
  const next = entity.mesh.position.clone().add(deltaMove);
  const blocked = walls.some((wall) => next.distanceTo(wall.position) < 1.35);
  if (!blocked) {
    entity.mesh.position.copy(next);
  }
}

function updateEnemies(player, enemies, boss, walls, delta) {
  const allEnemies = boss ? [...enemies, boss] : enemies;
  allEnemies.forEach((enemy) => {
    if (enemy.health <= 0) {
      enemy.mesh.visible = false;
      return;
    }
    const toPlayer = player.mesh.position.clone().sub(enemy.mesh.position);
    const distance = toPlayer.length();
    if (distance < 8) {
      toPlayer.normalize();
      moveWithCollision(enemy, toPlayer.multiplyScalar(enemy.speed * delta), walls);
    }
    enemy.mesh.rotation.y += delta * 1.8;
    if (distance < 1.25) {
      player.health = Math.max(0, player.health - delta * 12);
    }
  });
}

function updatePlayer(player, walls, delta) {
  const direction = new THREE.Vector3();
  if (keys.has("KeyW") || keys.has("ArrowUp")) direction.z -= 1;
  if (keys.has("KeyS") || keys.has("ArrowDown")) direction.z += 1;
  if (keys.has("KeyA") || keys.has("ArrowLeft")) direction.x -= 1;
  if (keys.has("KeyD") || keys.has("ArrowRight")) direction.x += 1;
  if (direction.length() > 0) {
    direction.normalize().multiplyScalar(player.speed * delta);
    moveWithCollision(player, direction, walls);
  }
  player.mesh.rotation.y += delta * 1.5;
}

function updateDecorations(decorativeLights, pickups, portal, delta) {
  decorativeLights.forEach((torch) => {
    torch.flame.scale.setScalar(0.85 + Math.sin(performance.now() * 0.007 + torch.seed) * 0.12);
    torch.light.intensity = 2.2 + Math.sin(performance.now() * 0.006 + torch.seed) * 0.5;
  });
  pickups.forEach((pickup, index) => {
    if (!pickup.visible) return;
    pickup.rotation.y += delta * (1.8 + index * 0.2);
    pickup.position.y = 0.7 + Math.sin(performance.now() * 0.003 + index) * 0.12;
  });
  if (portal) {
    portal.rotation.z += delta * 1.3;
  }
}

function collectPickups(player, pickups, hud) {
  pickups.forEach((pickup) => {
    if (pickup.visible && pickup.position.distanceTo(player.mesh.position) < 1.2) {
      pickup.visible = false;
      player.health = Math.min(player.maxHealth, player.health + 12);
      hud.status.textContent = "Relic collected";
    }
  });
}

function attack(player, enemies, boss, hud) {
  const targets = boss ? [...enemies, boss] : enemies;
  let hit = false;
  targets.forEach((enemy) => {
    if (enemy.health <= 0) return;
    const distance = enemy.mesh.position.distanceTo(player.mesh.position);
    if (distance < 2.4) {
      enemy.health -= 22;
      enemy.mesh.scale.setScalar(Math.max(0.25, enemy.health / enemy.maxHealth));
      hit = true;
    }
  });
  hud.status.textContent = hit ? "Strike landed" : "No enemy in range";
}

export function createGame(root = document.getElementById("app")) {
  root.innerHTML = "";

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x101416);
  scene.fog = new THREE.Fog(0x101416, 12, 34);

  const camera = new THREE.PerspectiveCamera(60, root.clientWidth / root.clientHeight, 0.1, 100);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(root.clientWidth, root.clientHeight);
  renderer.shadowMap.enabled = true;
  root.appendChild(renderer.domElement);

  const ambient = new THREE.HemisphereLight(0xdff7ff, 0x1c1917, 1.2);
  scene.add(ambient);
  const keyLight = new THREE.DirectionalLight(0xfff7cc, 2.5);
  keyLight.position.set(4, 10, 6);
  keyLight.castShadow = true;
  scene.add(keyLight);

  const { walls, enemies, boss, playerStart, decorativeLights, pickups, portal } = buildDungeon(scene);
  const playerMesh = new THREE.Mesh(new THREE.CapsuleGeometry(0.42, 0.7, 6, 12), material(0x5eead4));
  playerMesh.position.set(playerStart.x, 0.75, playerStart.z);
  playerMesh.castShadow = true;
  scene.add(playerMesh);

  const player = new Combatant(playerMesh, 100, 4.2);
  const hud = createHud(root);

  function resize() {
    camera.aspect = root.clientWidth / root.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(root.clientWidth, root.clientHeight);
  }

  function animate() {
    const delta = Math.min(clock.getDelta(), 0.033);
    updatePlayer(player, walls, delta);
    updateEnemies(player, enemies, boss, walls, delta);
    updateDecorations(decorativeLights, pickups, portal, delta);
    collectPickups(player, pickups, hud);
    updateCamera(camera, player);

    hud.health.textContent = `HP ${Math.ceil(player.health)}`;
    if (player.health <= 0) hud.status.textContent = "Defeated - refresh to retry";
    if (boss && boss.health <= 0) hud.status.textContent = "Boss defeated";

    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }

  window.addEventListener("resize", resize);
  window.addEventListener("keydown", (event) => {
    keys.add(event.code);
    if (event.code === "Space") attack(player, enemies, boss, hud);
  });
  window.addEventListener("keyup", (event) => keys.delete(event.code));

  resize();
  animate();
  return { scene, camera, renderer, plan: PLAN };
}

if (typeof window !== "undefined") {
  window.omniGame = createGame();
}
