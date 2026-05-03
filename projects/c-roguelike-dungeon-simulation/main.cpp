#include <chrono>
#include <cmath>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

struct Actor {
    std::string name;
    float x;
    float y;
    float health;
    float speed;
};

static const char* PROJECT_NAME = "c-roguelike-dungeon-simulation";

void smoke() {
    std::cout << "{\"ok\":true,\"engine\":\"Basic C++ Engine\",\"project\":\"" << PROJECT_NAME << "\"}" << std::endl;
}

void simulate() {
    Actor player{"player", 1.0f, 1.0f, 100.0f, 1.6f};
    std::vector<Actor> enemies = {
        {"enemy-a", 7.0f, 2.0f, 35.0f, 0.9f},
        {"enemy-b", 4.0f, 5.0f, 35.0f, 0.9f},
        {"boss", 9.0f, 4.0f, 180.0f, 0.5f},
    };

    std::cout << PROJECT_NAME << " simulation starting" << std::endl;
    for (int frame = 0; frame < 12; ++frame) {
        player.x += 0.35f;
        for (auto& enemy : enemies) {
            float dx = player.x - enemy.x;
            float dy = player.y - enemy.y;
            float distance = std::sqrt(dx * dx + dy * dy);
            if (distance > 0.01f) {
                enemy.x += dx / distance * enemy.speed * 0.1f;
                enemy.y += dy / distance * enemy.speed * 0.1f;
            }
            if (distance < 1.4f) {
                player.health -= 2.0f;
            }
        }
        std::cout << "frame=" << frame << " player=(" << player.x << "," << player.y << ") hp=" << player.health << std::endl;
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
}

int main(int argc, char** argv) {
    if (argc > 1 && std::string(argv[1]) == "--smoke") {
        smoke();
        return 0;
    }
    simulate();
    return 0;
}
