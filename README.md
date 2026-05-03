# OmniGameDev AI

OmniGameDev AI is a modular AI coding-agent platform for generating complete game project scaffolds from natural language prompts. It includes a Python agent core, deterministic planner, optional LLM API abstraction, multi-language code generators, execution/smoke testing, self-healing fixes, persistent retrieval memory, and a React/FastAPI web IDE.

## Folder Structure

```text
omnigamedev-ai/
  agent/                 AI orchestration and LLM provider abstraction
  planner/               Natural-language task decomposition and project plans
  generator/             File generation, templates, assets, manifests
  executor/              Subprocess execution and self-healing debugger
  memory/                Persistent vector-style retrieval memory
  language_adapters/     Python, JavaScript, C#, and C++ adapters
  plugins/               Engine plugin discovery system
  ide/
    backend/             FastAPI API used by the IDE
    frontend/            React + Monaco editor IDE
  projects/              Generated game projects
  main.py                CLI entrypoint
  training_context.md    Seed memory and training examples
```

## What Works Now

- Natural-language prompt to structured JSON plan.
- Engine/language selection for Three.js, Pygame, Unity C# scripts, and basic C++ projects.
- File-by-file project generation with manifests and placeholder assets.
- Smoke-test execution through subprocesses.
- Deterministic self-healing rules for common dependency, metadata, and syntax issues.
- Persistent memory seeded from `training_context.md` and updated after each project.
- React IDE with file explorer, Monaco editor, AI chat, terminal output, run button, preview iframe, and ZIP export.
- Open Folder import flow for bringing existing local game folders into the IDE workspace.
- AI Review, Improve, and Edit File actions for working on existing code.
- Game preset registry for dungeon crawler, platformer, FPS, puzzle, and racing requests.
- Plugin discovery with an example Phaser 2D plugin.

## LLM Configuration

The platform runs without an API key using local deterministic planning. To enable an OpenAI-compatible chat model:

```powershell
$env:OPENAI_API_KEY="your-key"
$env:OMNIGAMEDEV_MODEL="gpt-4o-mini"
# Optional for non-default compatible APIs:
$env:LLM_BASE_URL="https://api.openai.com/v1"
```

The planner asks the model for JSON only and keeps reasoning summarized instead of exposing private scratchpad text.

## Setup

From the repository root:

```powershell
cd "C:\Users\prave\OneDrive\Documents\New project 4\omnigamedev-ai"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

For the IDE frontend:

```powershell
cd "C:\Users\prave\OneDrive\Documents\New project 4\omnigamedev-ai\ide\frontend"
npm install
```

## Run Locally

Start the backend:

```powershell
cd "C:\Users\prave\OneDrive\Documents\New project 4\omnigamedev-ai"
.\.venv\Scripts\Activate.ps1
python -m uvicorn ide.backend.app:app --reload --host 127.0.0.1 --port 8787
```

Start the frontend:

```powershell
cd "C:\Users\prave\OneDrive\Documents\New project 4\omnigamedev-ai\ide\frontend"
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

If `5173` is already busy, use another port:

```powershell
npm run dev -- --host 127.0.0.1 --port 5174
```

## IDE Workflow

Use the left panel project selector to switch projects. Use **Open** to import a local folder path into `projects/` as a safe working copy. Type natural language instructions in the prompt box, then choose:

- **Generate** to create a new game.
- **Review** to find likely mistakes and run smoke checks.
- **Improve** to apply safe project upgrades, such as better Three.js graphics.
- **Edit File** to modify the currently selected file using the prompt.

The bug icon in the editor toolbar also runs a project review.

## Vercel Hosting

The hosted Vercel site serves the web IDE. The real agent backend is a FastAPI server because it edits files, opens folders, runs subprocess smoke tests, and stores generated projects on disk.

Current public frontend:

```text
https://frontend-eight-psi-41.vercel.app
```

The current production frontend points at this temporary public backend tunnel:

```text
https://pubs-game-endorsed-seats.trycloudflare.com
```

That tunnel stays online only while this computer, the local backend, and `cloudflared` are running. The public backend should use an access code because it can edit and run generated code. Permanent backend hosting instructions are in `PUBLIC_BACKEND_HOSTING.md`.

To restart the local backend:

```powershell
cd "C:\Users\prave\Downloads\omnigamedev-ai"
.\tools\start_backend.ps1 -AccessCode "your-access-code"
```

To restart the public tunnel:

```powershell
cd "C:\Users\prave\Downloads\omnigamedev-ai"
.\tools\start_public_backend_tunnel.ps1
```

## CLI Example

Generate and smoke-test a Three.js dungeon project:

```powershell
cd "C:\Users\prave\Downloads\omnigamedev-ai"
python main.py "build a 3D dungeon game with bosses" --json
```

Generate a Pygame project:

```powershell
python main.py "build a 2D pygame platformer with enemies and a boss"
```

Generate Unity scripts:

```powershell
python main.py "build a Unity dungeon RPG with boss fights"
```

Generate a basic C++ engine project:

```powershell
python main.py "build a C++ roguelike dungeon simulation"
```

## Generated Project Commands

Generated projects include their own `README.md`, `.omnigamedev/plan.json`, `.omnigamedev/manifest.json`, and placeholder assets.

For Three.js projects:

```powershell
cd projects\<project-name>
npm install
npm run dev
```

For Pygame projects:

```powershell
cd projects\<project-name>
pip install -r requirements.txt
python main.py
```

For C++ projects:

```powershell
cd projects\<project-name>
python tools/smoke.py
```

For Unity projects, copy or open the generated folder in Unity and attach the generated scripts as described in `Assets/OmniGameDev/SceneSetup.md`.

## Memory

On first startup, the agent chunks `training_context.md` into persistent memory. After every build, it stores the project pattern, smoke result, and any self-heal fixes. Set this to use Chroma when installed:

```powershell
$env:OMNIGAMEDEV_MEMORY_BACKEND="chroma"
```

Without Chroma, the local hashed vector store in `.memory/records.jsonl` remains fully functional.

To ingest user-approved web documentation into memory:

```powershell
python main.py --ingest-url "https://threejs.org/docs/" --ingest-only
```

Or set comma-separated URLs before startup:

```powershell
$env:OMNIGAMEDEV_INGEST_URLS="https://threejs.org/docs/,https://www.pygame.org/docs/"
```

## Plugin System

Add engine plugins under:

```text
plugins/<plugin-name>/plugin.json
plugins/<plugin-name>/adapter.py
```

The `PluginManager` discovers metadata now. Adapter registration can be extended by loading plugin modules into `CodeGenerator` and `ExecutionEngine`.

The included example plugin lives at:

```text
plugins/phaser2d/
```

## Testing

Run the standard-library test suite:

```powershell
cd "C:\Users\prave\OneDrive\Documents\New project 4\omnigamedev-ai"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Build the frontend:

```powershell
cd "C:\Users\prave\OneDrive\Documents\New project 4\omnigamedev-ai\ide\frontend"
npm run build
```

Or run the combined check script:

```powershell
cd "C:\Users\prave\OneDrive\Documents\New project 4\omnigamedev-ai"
.\.venv\Scripts\python.exe tools\run_checks.py
```
