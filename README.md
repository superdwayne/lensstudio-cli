# CLI-Anything Lens Studio

**Agent-native CLI for Snap Lens Studio** — part of the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) ecosystem.

> Make Lens Studio agent-ready for Claude Code, Cursor, OpenClaw, nanobot, and any AI agent.

## Why?

Lens Studio is a powerful GUI tool for creating AR lenses for Snapchat and Spectacles. But AI agents can't click buttons. This CLI bridges the gap — giving agents structured, scriptable access to Lens Studio's full capabilities through three automation layers:

- **CLI** — File-based project operations (always works, no Lens Studio needed)
- **Bridge** — Live editor control via a plugin that runs inside Lens Studio
- **GUI** — macOS accessibility automation for build/export dialogs

## Quick Start

### Install

```bash
cd LS-CLI
pip install -e ".[gui,agent]"
```

Optional extras:
- `[gui]` — macOS GUI automation (PyObjC)
- `[agent]` — AI planner with LLM support (Anthropic, OpenAI/Ollama)

### Verify Installation

```bash
ls-cli --version
ls-cli --help
```

### Bridge Plugin Setup

The bridge plugin enables live communication with a running Lens Studio instance:

```bash
# Install the plugin into Lens Studio
ls-cli bridge install

# Restart Lens Studio, then check connection
ls-cli bridge status

# Run diagnostics
ls-cli bridge doctor
```

### Create Your First Lens with AI

```bash
# Let the AI agent plan and build a lens
ls-cli auto run "create a clown lens with face paint and a red nose"

# Use a local model via Ollama
ls-cli auto run "add sparkle particles to my scene" --model ollama:qwen3

# Plan first, review, then execute
ls-cli auto plan "create a beauty filter"
ls-cli auto run "create a beauty filter"
```

## Commands

| Command | Description |
|---------|-------------|
| `project` | Create, open, list, delete projects |
| `scene` | Scene graph: add, remove, transform, reparent objects |
| `asset` | Import and manage textures, meshes, audio, etc. |
| `script` | Create, attach, edit JavaScript/TypeScript scripts |
| `material` | Create and assign PBR, Unlit, FacePaint materials |
| `component` | Add Camera, MeshVisual, Text, tracking components |
| `lens` | Build, validate, preview, export lenses |
| `template` | Browse and apply 16 built-in templates |
| `bridge` | Install, status, send commands to the live editor plugin |
| `auto` | AI-powered lens creation — plan and run natural language requests |

## Prefab Commands

Prefabs are high-level commands that create fully-configured lens elements in a single call. They handle the scene object, components, mesh resources, materials, and property setup automatically.

Use them via the bridge:

```bash
# Face effects
ls-cli bridge send prefab face_mesh --params '{"name": "My Face Mesh"}'
ls-cli bridge send prefab face_stretch --params '{"name": "Big Smile", "intensity": "0.5"}'
ls-cli bridge send prefab face_retouch --params '{"name": "Beauty", "intensity": "0.7"}'
ls-cli bridge send prefab head_attached_3d --params '{"name": "Clown Nose", "mesh_type": "sphere", "scale": "0.2"}'

# World AR
ls-cli bridge send prefab world_object --params '{"name": "Cube", "mesh_type": "cube"}'
ls-cli bridge send prefab ground_plane --params '{"name": "Floor"}'

# Visual effects
ls-cli bridge send prefab post_effect --params '{"name": "Blur"}'
ls-cli bridge send prefab particles --params '{"name": "Sparkles"}'

# Screen overlays
ls-cli bridge send prefab text_overlay --params '{"name": "Title", "text": "Hello World!"}'
ls-cli bridge send prefab screen_image --params '{"name": "Logo"}'
```

### Available Prefabs

| Prefab | What it creates |
|--------|----------------|
| **Face Effects** | |
| `prefab.face_mesh` | Head + FaceMask + RenderMeshVisual + FaceMesh material |
| `prefab.face_stretch` | Head + FaceStretch with configurable intensity |
| `prefab.face_inset` | Head + FaceInset for eye/mouth cutouts |
| `prefab.face_retouch` | Head + RetouchVisual (skin smooth, eye sharpen, teeth whiten) |
| `prefab.face_liquify` | Head + LiquifyVisual for face warping |
| `prefab.eye_color` | Head + EyeColorVisual + material |
| `prefab.hair_color` | Head + HairVisual + material |
| `prefab.head_attached_3d` | Head tracking + child mesh (hats, glasses, horns) with PBR material |
| **World AR** | |
| `prefab.world_object` | DeviceTracking (World) + mesh + PBR material |
| `prefab.ground_plane` | DeviceTracking (World) + plane mesh at y=0 |
| **Visual Effects** | |
| `prefab.post_effect` | PostEffectVisual under Camera + Graph material |
| `prefab.color_correction` | PostEffectVisual for color grading |
| `prefab.particles` | ParticlesVisual + Unlit material |
| `prefab.segmentation` | SegmentationTextureProvider + Image |
| **Common Elements** | |
| `prefab.screen_image` | ScreenTransform + Image under Orthographic Camera |
| `prefab.text_overlay` | ScreenTransform + Text with configurable content |
| `prefab.light` | LightSource (Directional/Point/Spot) with intensity |
| `prefab.camera` | Camera with configurable type and clip planes |

The AI agent uses prefabs automatically — `auto run "create a clown lens"` will plan with `bridge.prefab.face_mesh`, `bridge.prefab.head_attached_3d`, etc. instead of low-level scene.add + component.add.

## Usage Examples

### Subcommand Mode (for scripts & pipelines)

```bash
# Create a project from template
ls-cli project new -n ARGame -t world-ar

# Set project path for subsequent commands
PROJECT=~/LensStudio/Projects/ARGame/ARGame.esproj

# Add scene objects
ls-cli --project $PROJECT scene add -n "Player"
ls-cli --project $PROJECT scene add -n "Score Display"

# Add components
ls-cli --project $PROJECT component add --to <object-id> -t MeshVisual
ls-cli --project $PROJECT component add --to <object-id> -t Text -p '{"text":"Score: 0","size":48}'

# Create and attach a script
ls-cli --project $PROJECT script create -n GameLogic -t update
ls-cli --project $PROJECT script attach --script GameLogic --to <object-id>

# Create materials
ls-cli --project $PROJECT material create -n PlayerMat -t PBR --color 0.2 0.5 1.0 1.0 --metallic 0.8

# Validate before building
ls-cli --project $PROJECT lens validate

# JSON mode for agent consumption
ls-cli --project $PROJECT --json scene list
ls-cli --project $PROJECT --json lens validate
```

### REPL Mode (for interactive agent sessions)

```bash
$ ls-cli
lens-studio> project new -n CoolLens -t face-effects
lens-studio> --project ~/LensStudio/Projects/CoolLens/CoolLens.esproj scene list
lens-studio> exit
```

## Templates

| Template | Description |
|----------|-------------|
| `blank` | Empty project with a single camera |
| `face-effects` | Face tracking with face mesh and effects |
| `world-ar` | World tracking with ground plane detection |
| `hand-tracking` | Hand tracking with hand mesh |
| `body-tracking` | Full body tracking template |
| `marker-tracking` | Image marker tracking template |
| `segmentation` | Background segmentation template |
| `landmarker` | Location-based AR experience |
| `connected-lens` | Multiplayer connected lens |
| `interactive` | Touch and gesture interaction |
| `3d-object` | 3D object placement template |
| `particle-system` | Particle effects template |
| `audio-reactive` | Audio-reactive visual effects |
| `ml-template` | Machine learning integration |
| `snap-spectacles` | Spectacles AR glasses template |

## Architecture

```
cli_anything/lens_studio/
├── cli.py                  # Main entry point (Click + REPL)
├── core/                   # Business logic (file-based)
│   ├── project.py          # Project CRUD (.esproj files)
│   ├── scene.py            # Scene graph operations
│   ├── asset.py            # Asset pipeline
│   ├── script.py           # JS/TS script management
│   ├── material.py         # Material creation & assignment
│   ├── component.py        # Component management
│   ├── lens.py             # Build, validate, export
│   └── template.py         # Template system
├── commands/               # Click CLI command groups
│   ├── project_cmd.py
│   ├── scene_cmd.py
│   ├── asset_cmd.py
│   ├── script_cmd.py
│   ├── material_cmd.py
│   ├── component_cmd.py
│   ├── lens_cmd.py
│   ├── template_cmd.py
│   ├── bridge_cmd.py       # Bridge plugin management
│   └── auto_cmd.py         # AI agent commands
├── bridge/                 # Live editor IPC layer
│   ├── client.py           # File-based IPC client
│   ├── protocol.py         # Command/response schemas
│   └── installer.py        # Plugin installation
├── agent/                  # AI planner layer
│   ├── planner.py          # LLM-powered action planning
│   ├── executor.py         # Sequential step execution
│   ├── capabilities.py     # Action registry (CLI + Bridge + Prefab + GUI)
│   └── prompts.py          # System prompts and few-shot examples
├── gui/                    # macOS GUI automation
│   └── actions.py          # Accessibility API actions
└── utils/
    ├── config.py           # Paths, constants, asset types
    ├── formatter.py        # Rich output + JSON formatting
    └── logging.py          # Structured logging

ls_bridge_plugin/           # Lens Studio plugin (installed into editor)
├── module.json             # Plugin manifest
└── bridge.js               # CoreService with IPC + prefab handlers
```

## Running Tests

```bash
pip install -e ".[gui,agent]"
pytest tests/ -v
```

228 tests covering all layers.

## Requirements

- **Python 3.9+**
- **Lens Studio** (optional — for bridge/build/preview; CLI works without it for project management)
- Core: `click`, `rich`, `prompt-toolkit`, `pyyaml`
- Optional `[gui]`: `pyobjc` (macOS only)
- Optional `[agent]`: `anthropic` SDK (or `openai` for Ollama)

## License

MIT
