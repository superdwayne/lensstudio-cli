# HARNESS.md — Lens Studio Agent Harness Playbook

## Overview

This document defines the standard operating procedure for the `cli-anything-lens-studio` agent harness. It encodes the proven patterns from the CLI-Anything methodology adapted specifically for Snap Lens Studio.

## Core Principles

1. **Authentic Software Integration** — The CLI generates valid `.lsproj` project files and delegates rendering/building to the real Lens Studio application. We build structured interfaces *to* Lens Studio, not replacements.

2. **Dual Interaction Modes** — Subcommand interface for scripting/pipelines + REPL mode for interactive agent sessions.

3. **Agent-Native by Default** — Every command has `--json` output. Agents discover capabilities via `--help`. Structured data eliminates parsing complexity.

4. **Lens Studio Domain Model** — The CLI respects Lens Studio's architecture: SceneObjects with Components, asset pipeline, material system, and script attachments.

## Domain Model

### Project Structure
- `.lsproj` files are JSON documents containing scene graph, asset refs, materials, scripts
- Projects live in directories with standardized subdirs: `Scripts/`, `Textures/`, `Materials/`, `Meshes/`, `Audio/`, `Prefabs/`

### Scene Graph
- Tree of `SceneObject` nodes
- Each object has: transform (position, rotation, scale), components, enabled state
- Objects can be reparented, duplicated, enabled/disabled

### Components
- Attached to SceneObjects to add behavior
- 35+ built-in types: Camera, MeshVisual, Image, Text, tracking components, effects, etc.
- Some are singletons (Camera, DeviceTracking), others allow multiples

### Assets
- Imported files: textures (.png, .jpg), meshes (.fbx, .glb), audio (.mp3, .wav), scripts (.js, .ts)
- Automatically categorized and placed in appropriate subdirectories
- Referenced by ID in components

### Materials
- Define surface appearance: Default, Unlit, PBR, FacePaint, FaceMesh, Occluder, Graph
- PBR materials have: baseColor, metallic, roughness, normalMap, emissive
- Assigned to visual components (MeshVisual, Image, etc.)

### Scripts
- JavaScript or TypeScript files with Lens Studio API
- Templates: blank, update, tap, tween, behavior, typescript
- Attached to objects via ScriptComponent
- Support `@input` declarations for inspector properties

## Command Architecture

### Global Options
- `--project <path>` — Set active project for all subcommands
- `--json` — Structured JSON output on all commands
- `--version` — Version info

### Command Groups
| Group | Responsibility |
|-------|---------------|
| `project` | CRUD on .lsproj files and directories |
| `scene` | Scene graph mutations (add, remove, transform, reparent) |
| `asset` | Import, list, remove assets with auto-categorization |
| `script` | Create from templates, attach/detach to objects, read/write content |
| `material` | Create typed materials, edit properties, assign to visuals |
| `component` | Add/remove/configure components on scene objects |
| `lens` | Build, validate, preview, export |
| `template` | Browse and apply 16 built-in project templates |

## Testing Strategy

### Unit Tests (synthetic data)
- Project creation, loading, saving, round-trip
- Scene graph operations (add, remove, transform, reparent, duplicate)
- Asset import, categorization, removal
- Script CRUD, template expansion, attach/detach
- Material creation, editing, assignment
- Component management, singleton enforcement
- Validation logic

### CLI Tests (Click test runner)
- All subcommands produce correct exit codes
- JSON mode produces valid JSON with expected keys
- Error cases produce non-zero exit codes

### Integration Tests (real Lens Studio)
- Build lens from project file
- Preview launch
- Validate against Lens Studio binary

## Critical Lessons

1. **Lens Studio projects are JSON** — Work directly with the JSON structure for maximum flexibility
2. **Components define behavior** — SceneObjects are containers; components are what matters
3. **Scripts use Lens Studio API** — Not standard browser/Node.js JS; `@input` decorators, `script.createEvent()`, etc.
4. **Face effects need Head component** — Not just face tracking; the attachment point matters
5. **8MB lens size limit** — Validate asset sizes before building
6. **Template variety** — 16 templates cover face, world, hand, body, marker, segmentation, and more
