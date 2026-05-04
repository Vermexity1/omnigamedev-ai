# OmniGameDev AI Benchmark Results

This file records real local benchmark results only. It does not invent scores for GPT-5.2 or any other OpenAI model.

## Suite

- Name: `game_edit_semantics_v1`
- Target: project-level game code editing
- Agent: OmniGameDev deterministic semantic editor
- Cases:
  - first-person camera request
  - green wall material request
  - blue enemy material request
  - faster player movement request

## Latest Local Result

Run date: 2026-05-04

```json
{
  "suite": "game_edit_semantics_v1",
  "agent": "OmniGameDev deterministic semantic editor",
  "passed": 4,
  "total": 4,
  "score": 1.0,
  "cases": [
    {
      "case": "first_person_camera",
      "instruction": "change the game to first person",
      "passed": true,
      "changed_files": ["src/main.js", "src/style.css"],
      "failed_checks": [],
      "notes": ["Changed camera, mouse-look, and WASD movement to first-person controls."]
    },
    {
      "case": "green_walls",
      "instruction": "make the walls green",
      "passed": true,
      "changed_files": ["src/main.js"],
      "failed_checks": [],
      "notes": ["Changed the wall material color to 0x22c55e."]
    },
    {
      "case": "blue_enemies",
      "instruction": "make enemies blue",
      "passed": true,
      "changed_files": ["src/main.js"],
      "failed_checks": [],
      "notes": ["Changed the enemy material color to 0x3b82f6."]
    },
    {
      "case": "faster_player",
      "instruction": "make the player faster",
      "passed": true,
      "changed_files": ["src/main.js"],
      "failed_checks": [],
      "notes": ["Changed player movement speed to 6.2."]
    }
  ],
  "openai_model_comparison": {
    "status": "not_run",
    "reason": "No OpenAI API model calls were run in this benchmark. Do not infer GPT-5.2 or other model scores from this local test."
  }
}
```

Re-run:

```powershell
cd "C:\Users\prave\Downloads\omnigamedev-ai"
.\.venv\Scripts\python.exe benchmarks\game_edit_benchmark.py
```

## OpenAI Model Comparison

Status: `not_run`

Reason: No OpenAI API model calls were run for this benchmark. Accurate comparison against OpenAI models requires model API access, identical prompts, identical project fixtures, deterministic scoring rules, and recorded raw outputs. This project must not claim GPT-5.2, GPT-5.4, GPT-5.5, or any other OpenAI model benchmark scores until those runs are actually executed.
