# 🔮 CLI-Anything Lens Studio

**Agent-native CLI for Snap Lens Studio** — part of the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) ecosystem.

> Make Lens Studio agent-ready for Claude Code, Cursor, OpenClaw, nanobot, and any AI agent.

## Why?

Lens Studio is a powerful GUI tool for creating AR lenses for Snapchat and Spectacles. But AI agents can't click buttons. This CLI bridges the gap — giving agents structured, scriptable access to Lens Studio's full capabilities through the command line.

## Quick Start

### Install

```bash
cd LS-CLI
pip install -e .
```

### Verify Installation

```bash
ls-cli --version
ls-cli --help
```

### Create Your First Project

```bash
# Create a face effects project
ls-cli project new -n MyFaceLens -t face-effects

# Check project info
ls-cli --project ~/LensStudio/Projects/MyFaceLens/MyFaceLens.lsproj project info

# JSON mode for agent consumption
ls-cli --project ~/LensStudio/Projects/MyFaceLens/MyFaceLens.lsproj project info --json
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

## Usage Examples

### Subcommand Mode (for scripts & pipelines)

```bash
# Create a project from template
ls-cli project new -n ARGame -t world-ar

# Set project path for subsequent commands
PROJECT=~/LensStudio/Projects/ARGame/ARGame.lsproj

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

# Build the lens
ls-cli --project $PROJECT lens build -o game.lens -t snapchat

# JSON mode for agent consumption
ls-cli --project $PROJECT --json scene list
ls-cli --project $PROJECT --json lens validate
```

### REPL Mode (for interactive agent sessions)

```bash
$ ls-cli
╔══════════════════════════════════════════════╗
║  cli-anything-lens-studio v1.0.0            ║
║  Lens Studio CLI for AI Agents              ║
║  Type 'help' for commands, 'exit' to quit   ║
╚══════════════════════════════════════════════╝
lens-studio> project new -n CoolLens -t face-effects
✓ Created face-effects project: CoolLens

lens-studio> --project ~/LensStudio/Projects/CoolLens/CoolLens.lsproj scene list
┌──────────────┬──────────┬────────────┬─────────┐
│ Name         │ ID       │ Components │ Enabled │
├──────────────┼──────────┼────────────┼─────────┤
│ Scene        │ abc12345 │ -          │ Yes     │
│   Camera     │ def67890 │ Camera     │ Yes     │
│   Face Effects│ ghi11213 │ Head, ...  │ Yes     │
└──────────────┴──────────┴────────────┴─────────┘

lens-studio> exit
Goodbye! 👋
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

## Agent-Native Design

Every command supports `--json` for structured machine output:

```bash
$ ls-cli --json template list
{
  "templates": [
    {"name": "blank", "description": "Empty project with a single camera"},
    {"name": "face-effects", "description": "Face tracking with face mesh and effects"},
    ...
  ],
  "count": 16
}
```

Agents discover capabilities via standard `--help`:

```bash
$ ls-cli --help
$ ls-cli scene --help
$ ls-cli component list-types --json
```

## Architecture

```
cli_anything/lens_studio/
├── cli.py              # Main entry point (Click + REPL)
├── core/               # Business logic
│   ├── project.py      # Project CRUD (.lsproj files)
│   ├── scene.py        # Scene graph operations
│   ├── asset.py        # Asset pipeline
│   ├── script.py       # JS/TS script management
│   ├── material.py     # Material creation & assignment
│   ├── component.py    # Component management
│   ├── lens.py         # Build, validate, export
│   └── template.py     # Template system
├── commands/           # Click CLI command groups
│   ├── project_cmd.py
│   ├── scene_cmd.py
│   ├── asset_cmd.py
│   ├── script_cmd.py
│   ├── material_cmd.py
│   ├── component_cmd.py
│   ├── lens_cmd.py
│   └── template_cmd.py
└── utils/
    ├── backend.py      # Lens Studio application wrapper
    ├── config.py       # Paths, constants, asset types
    ├── formatter.py    # Rich output + JSON formatting
    └── repl_skin.py    # Interactive REPL interface
```

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Requirements

- **Python 3.9+**
- **Lens Studio** (optional — for build/preview/export; CLI works without it for project management)
- Dependencies: `click`, `rich`, `prompt-toolkit`

## License

MIT
