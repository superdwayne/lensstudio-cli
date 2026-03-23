"""Action registry — collects available actions from all 3 layers.

Each action is described with its name, parameters, description, and
which layer handles it. This registry is used by the planner to know
what operations are available.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class ActionDef:
    """Definition of an available action."""

    name: str
    layer: str  # "cli", "bridge", "gui"
    domain: str  # e.g., "project", "scene", "asset"
    description: str
    parameters: dict[str, str] = field(default_factory=dict)  # param_name -> description
    required_params: list[str] = field(default_factory=list)
    handler: Optional[Callable] = None

    def to_tool_schema(self) -> dict[str, Any]:
        """Convert to an Anthropic tool-use compatible schema."""
        properties = {}
        for param, desc in self.parameters.items():
            properties[param] = {"type": "string", "description": desc}

        return {
            "name": self.name,
            "description": f"[{self.layer}/{self.domain}] {self.description}",
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": self.required_params,
            },
        }


class ActionRegistry:
    """Registry of all available actions across layers."""

    def __init__(self):
        self._actions: dict[str, ActionDef] = {}
        self._register_defaults()

    @property
    def actions(self) -> dict[str, ActionDef]:
        return dict(self._actions)

    def register(self, action: ActionDef):
        self._actions[action.name] = action

    def get(self, name: str) -> Optional[ActionDef]:
        return self._actions.get(name)

    def list_by_layer(self, layer: str) -> list[ActionDef]:
        return [a for a in self._actions.values() if a.layer == layer]

    def list_by_domain(self, domain: str) -> list[ActionDef]:
        return [a for a in self._actions.values() if a.domain == domain]

    def to_tool_schemas(self) -> list[dict]:
        """Convert all actions to Anthropic tool schemas for the planner."""
        return [a.to_tool_schema() for a in self._actions.values()]

    def summary(self) -> list[dict[str, str]]:
        """Return a concise summary of all actions."""
        return [
            {"name": a.name, "layer": a.layer, "domain": a.domain, "description": a.description}
            for a in self._actions.values()
        ]

    def _register_defaults(self):
        """Register all built-in actions."""
        self._register_cli_actions()
        self._register_bridge_actions()
        self._register_prefab_actions()
        self._register_gui_actions()

    def _register_cli_actions(self):
        """Register actions handled by the CLI (file-based operations)."""
        self.register(ActionDef(
            name="cli.project.create",
            layer="cli", domain="project",
            description="Create a new Lens Studio project",
            parameters={"name": "Project name", "template": "Template name", "directory": "Target directory"},
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="cli.project.open",
            layer="cli", domain="project",
            description="Open an existing project file",
            parameters={"path": "Path to .esproj file"},
            required_params=["path"],
        ))
        self.register(ActionDef(
            name="cli.scene.add",
            layer="cli", domain="scene",
            description="Add a scene object to the project (file-based)",
            parameters={"name": "Object name", "parent": "Parent object name", "project": "Project path"},
            required_params=["name", "project"],
        ))
        self.register(ActionDef(
            name="cli.asset.import",
            layer="cli", domain="asset",
            description="Import an asset file into the project (file-based)",
            parameters={"path": "Asset file path", "project": "Project path"},
            required_params=["path", "project"],
        ))
        self.register(ActionDef(
            name="cli.lens.validate",
            layer="cli", domain="lens",
            description="Validate a project for submission readiness",
            parameters={"project": "Project path"},
            required_params=["project"],
        ))
        self.register(ActionDef(
            name="cli.lens.build",
            layer="cli", domain="lens",
            description="Build a lens (file-based bundle or backend)",
            parameters={"project": "Project path", "output": "Output path", "target": "Build target"},
            required_params=["project", "output"],
        ))

    def _register_bridge_actions(self):
        """Register actions handled by the bridge plugin (Editor API)."""
        self.register(ActionDef(
            name="bridge.scene.add",
            layer="bridge", domain="scene",
            description="Add a scene object in the live Lens Studio editor",
            parameters={"name": "Object name", "parent": "Parent object", "components": "Component types (comma-sep)"},
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.scene.remove",
            layer="bridge", domain="scene",
            description="Remove a scene object from the live editor",
            parameters={"name": "Object name or ID"},
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.scene.list",
            layer="bridge", domain="scene",
            description="List all scene objects in the live editor",
            parameters={},
        ))
        self.register(ActionDef(
            name="bridge.component.add",
            layer="bridge", domain="component",
            description="Add a component to a scene object in the live editor",
            parameters={"target": "Scene object name", "type": "Component type", "properties": "JSON properties"},
            required_params=["target", "type"],
        ))
        self.register(ActionDef(
            name="bridge.script.create",
            layer="bridge", domain="script",
            description="Create a new script file in the live editor project",
            parameters={"name": "Script name", "template": "Script template"},
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.script.attach",
            layer="bridge", domain="script",
            description="Attach a script to a scene object as a ScriptComponent",
            parameters={"target": "Scene object name", "script": "Script path"},
            required_params=["target", "script"],
        ))
        self.register(ActionDef(
            name="bridge.material.create",
            layer="bridge", domain="material",
            description="Create a new material in the live editor",
            parameters={"name": "Material name", "type": "Material type"},
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.asset.import",
            layer="bridge", domain="asset",
            description="Import an external asset file into the live editor",
            parameters={"path": "File path to import"},
            required_params=["path"],
        ))
        self.register(ActionDef(
            name="bridge.query.scene_tree",
            layer="bridge", domain="query",
            description="Get the full scene hierarchy tree from the live editor",
            parameters={},
        ))
        self.register(ActionDef(
            name="bridge.query.ping",
            layer="bridge", domain="query",
            description="Check bridge connection health",
            parameters={},
        ))

    def _register_prefab_actions(self):
        """Register high-level prefab commands that create complete lens elements."""
        # ── Face Effects ────────────────────────────────────────────
        self.register(ActionDef(
            name="bridge.prefab.face_mesh",
            layer="bridge", domain="prefab",
            description="Create a face mesh with Head tracking, FaceMask, RenderMeshVisual, face mesh resource, and FaceMesh material",
            parameters={
                "name": "Object name",
                "material_type": "Material type: FaceMesh (default), FacePaint",
                "parent": "Parent object name",
            },
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.prefab.face_stretch",
            layer="bridge", domain="prefab",
            description="Create a face stretch/distortion effect with Head tracking and FaceStretch",
            parameters={
                "name": "Object name",
                "intensity": "Stretch intensity (0.0-1.0)",
                "parent": "Parent object name",
            },
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.prefab.face_inset",
            layer="bridge", domain="prefab",
            description="Create a face inset (eye/mouth cutout) with Head tracking, FaceInset, and mesh",
            parameters={
                "name": "Object name",
                "region": "Face region: eyes, mouth, nose",
                "parent": "Parent object name",
            },
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.prefab.face_retouch",
            layer="bridge", domain="prefab",
            description="Create a skin smoothing/beauty effect with Head tracking and RetouchVisual (soft skin, eye sharpen, teeth whitening)",
            parameters={
                "name": "Object name",
                "intensity": "Retouch intensity (0.0-1.0, default 0.5)",
                "parent": "Parent object name",
            },
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.prefab.face_liquify",
            layer="bridge", domain="prefab",
            description="Create a face warping/liquify effect with Head tracking and LiquifyVisual",
            parameters={
                "name": "Object name",
                "intensity": "Liquify intensity (0.0-1.0, default 0.3)",
                "parent": "Parent object name",
            },
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.prefab.eye_color",
            layer="bridge", domain="prefab",
            description="Create an eye color change effect with Head tracking and EyeColorVisual",
            parameters={"name": "Object name", "parent": "Parent object name"},
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.prefab.hair_color",
            layer="bridge", domain="prefab",
            description="Create a hair color change effect with Head tracking and HairVisual",
            parameters={"name": "Object name", "parent": "Parent object name"},
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.prefab.head_attached_3d",
            layer="bridge", domain="prefab",
            description="Create a 3D object attached to head (hats, glasses, horns) with mesh and PBR material",
            parameters={
                "name": "Object name",
                "mesh_type": "Mesh shape: sphere (default), cube, plane",
                "attachment": "Head attachment point: center, forehead, nose",
                "scale": "Object scale (default 0.3)",
                "parent": "Parent object name",
            },
            required_params=["name"],
        ))

        # ── World AR ────────────────────────────────────────────────
        self.register(ActionDef(
            name="bridge.prefab.world_object",
            layer="bridge", domain="prefab",
            description="Create a world-tracked 3D object with DeviceTracking, mesh, and PBR material",
            parameters={
                "name": "Object name",
                "mesh_type": "Mesh shape: cube (default), sphere, plane",
                "parent": "Parent object name",
            },
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.prefab.ground_plane",
            layer="bridge", domain="prefab",
            description="Create a world-tracked ground plane with DeviceTracking, plane mesh, and PBR material",
            parameters={"name": "Object name", "parent": "Parent object name"},
            required_params=["name"],
        ))

        # ── Visual Effects ──────────────────────────────────────────
        self.register(ActionDef(
            name="bridge.prefab.post_effect",
            layer="bridge", domain="prefab",
            description="Create a camera post-processing effect (auto-parents to Camera) with PostEffectVisual and Graph material",
            parameters={"name": "Object name", "parent": "Parent object name"},
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.prefab.color_correction",
            layer="bridge", domain="prefab",
            description="Create a color correction/grading post-effect (auto-parents to Camera)",
            parameters={"name": "Object name", "parent": "Parent object name"},
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.prefab.particles",
            layer="bridge", domain="prefab",
            description="Create a particle system with ParticlesVisual and Unlit material",
            parameters={"name": "Object name", "parent": "Parent object name"},
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.prefab.segmentation",
            layer="bridge", domain="prefab",
            description="Create a segmentation effect (background/sky/person) with texture provider and image",
            parameters={
                "name": "Object name",
                "segmentation_type": "Segmentation type: Background (default), Sky, Person",
                "parent": "Parent object name",
            },
            required_params=["name"],
        ))

        # ── Common Elements ─────────────────────────────────────────
        self.register(ActionDef(
            name="bridge.prefab.screen_image",
            layer="bridge", domain="prefab",
            description="Create a 2D screen image (auto-parents to Orthographic Camera) with ScreenTransform and Image",
            parameters={
                "name": "Object name",
                "texture": "Texture asset name to display",
                "parent": "Parent object name",
            },
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.prefab.text_overlay",
            layer="bridge", domain="prefab",
            description="Create a 2D text overlay (auto-parents to Orthographic Camera) with ScreenTransform and Text",
            parameters={
                "name": "Object name",
                "text": "Initial text content",
                "font_size": "Font size",
                "parent": "Parent object name",
            },
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.prefab.light",
            layer="bridge", domain="prefab",
            description="Create a light source with intensity and positioned above scene for directional lights",
            parameters={
                "name": "Object name",
                "light_type": "Light type: Directional (default), Point, Spot",
                "intensity": "Light intensity (default 1.0)",
                "parent": "Parent object name",
            },
            required_params=["name"],
        ))
        self.register(ActionDef(
            name="bridge.prefab.camera",
            layer="bridge", domain="prefab",
            description="Create a camera with configurable type and clip planes",
            parameters={
                "name": "Object name",
                "camera_type": "Camera type: Perspective (default), Orthographic",
                "near": "Near clip plane",
                "far": "Far clip plane",
                "parent": "Parent object name",
            },
            required_params=["name"],
        ))

    def _register_gui_actions(self):
        """Register actions handled by GUI automation."""
        self.register(ActionDef(
            name="gui.lens.build",
            layer="gui", domain="lens",
            description="Build a lens using the Lens Studio GUI (macOS only)",
            parameters={"output": "Output file path", "target": "Build target"},
        ))
        self.register(ActionDef(
            name="gui.lens.export",
            layer="gui", domain="lens",
            description="Export a lens via the GUI export dialog (macOS only)",
            parameters={"output": "Output file path"},
        ))
        self.register(ActionDef(
            name="gui.project.open",
            layer="gui", domain="project",
            description="Open a project in Lens Studio GUI (macOS only)",
            parameters={"path": "Project file path"},
            required_params=["path"],
        ))
        self.register(ActionDef(
            name="gui.preview.start",
            layer="gui", domain="preview",
            description="Start lens preview via GUI (macOS only)",
            parameters={"device": "Preview device"},
        ))
