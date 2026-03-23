/**
 * LS-CLI Bridge Plugin — CoreService for Lens Studio
 *
 * Single-file ES module that enables file-based IPC between the CLI and
 * Lens Studio's Editor API. Watches ~/.ls-cli/bridge/commands/ for JSON
 * command files, dispatches them to inlined domain handlers, and writes
 * responses to ~/.ls-cli/bridge/responses/.
 *
 * Module system: ES modules (import/export)
 * API access: pluginSystem.findInterface(Editor.Model.IModel)
 * FileSystem: import * as fs from 'LensStudio:FileSystem'
 */

import { CoreService } from 'LensStudio:CoreService';
import * as fs from 'LensStudio:FileSystem';

const PLUGIN_VERSION = '2.0.0';
const POLL_INTERVAL = 250;
const HEARTBEAT_INTERVAL = 2000;

// ─── Utility: feature detection with fallback chains ────────────────────────

function probeMkdir(path) {
    const fns = [
        () => fs.makeDirectoryRecursive(path),
        () => fs.makeDir(path),
        () => fs.mkdir(path),
    ];
    for (const fn of fns) {
        try { fn(); return true; } catch (_) { /* try next */ }
    }
    return false;
}

function probeWriteFile(path, content) {
    const fns = [
        () => fs.writeFile(path, content),
        () => fs.writeTextFile(path, content),
    ];
    for (const fn of fns) {
        try { fn(); return true; } catch (_) { /* try next */ }
    }
    return false;
}

function probeReadFile(path) {
    const fns = [
        () => fs.readFile(path),
        () => fs.readTextFile(path),
    ];
    for (const fn of fns) {
        try { return fn(); } catch (_) { /* try next */ }
    }
    return null;
}

function probeListDir(path) {
    const fns = [
        () => fs.listDirectory(path),
        () => fs.listDir(path),
        () => fs.readdir(path),
    ];
    for (const fn of fns) {
        try { return fn(); } catch (_) { /* try next */ }
    }
    return [];
}

function probeRemoveFile(path) {
    const fns = [
        () => fs.removeFile(path),
        () => fs.remove(path),
        () => fs.unlink(path),
    ];
    for (const fn of fns) {
        try { fn(); return true; } catch (_) { /* try next */ }
    }
    return false;
}

function probeExpandPath(path) {
    const fns = [
        () => fs.expandPath(path),
    ];
    for (const fn of fns) {
        try { return fn(); } catch (_) { /* try next */ }
    }
    // Fallback: environment or hardcoded
    try {
        if (typeof process !== 'undefined' && process.env && process.env.HOME) {
            return path.replace('~', process.env.HOME);
        }
    } catch (_) { /* ignore */ }
    return null;
}

/**
 * Resolve the plugin's own directory from import.meta.url.
 * Returns the directory containing bridge.js, or null.
 */
function getPluginDir() {
    try {
        // import.meta.url is typically file:///path/to/bridge.js
        let url = import.meta.url || '';
        if (url.startsWith('file://')) {
            url = url.slice(7); // strip file://
        }
        // Remove /bridge.js filename to get directory
        const lastSlash = url.lastIndexOf('/');
        if (lastSlash > 0) {
            return url.substring(0, lastSlash);
        }
    } catch (_) { /* ignore */ }
    return null;
}

/**
 * Read config.json from the plugin directory.
 * Written by `ls-cli bridge install` with absolute paths.
 */
function readPluginConfig(pluginDir) {
    if (!pluginDir) return null;
    const configPath = pluginDir + '/config.json';
    try {
        const content = probeReadFile(configPath);
        if (content) {
            return JSON.parse(content);
        }
    } catch (_) { /* ignore */ }
    return null;
}

// ─── Utility: scene traversal ───────────────────────────────────────────────

function traverse(sceneObjects, fn) {
    for (const so of sceneObjects || []) {
        if (fn(so)) return so;
        const found = traverse(so.children, fn);
        if (found) return found;
    }
    return null;
}

function findObjectByName(scene, name) {
    return traverse(scene.rootSceneObjects, so => so.name === name);
}

function collectAll(sceneObjects) {
    const result = [];
    const walk = (objects) => {
        for (const so of objects || []) {
            result.push(so);
            walk(so.children);
        }
    };
    walk(sceneObjects);
    return result;
}

function serializeObject(so, includeChildren = true) {
    const data = {
        name: so.name,
        components: [],
    };

    try {
        const comps = so.components || [];
        for (const c of comps) {
            try {
                data.components.push(c.getTypeName());
            } catch (_) {
                data.components.push('Unknown');
            }
        }
    } catch (_) { /* no components accessor */ }

    try {
        const t = so.localTransform;
        if (t) {
            data.transform = {
                position: { x: t.position.x, y: t.position.y, z: t.position.z },
                rotation: { x: t.rotation.x, y: t.rotation.y, z: t.rotation.z },
                scale: { x: t.scale.x, y: t.scale.y, z: t.scale.z },
            };
        }
    } catch (_) { /* transform not available */ }

    if (includeChildren) {
        data.children = (so.children || []).map(c => serializeObject(c, true));
    }

    return data;
}

// ─── CoreService ────────────────────────────────────────────────────────────

export class LSCLIBridge extends CoreService {
    static descriptor() {
        return {
            id: 'Com.CLIAnything.LSCLIBridge',
            name: 'LS-CLI Bridge',
            description: 'File-based IPC bridge for CLI-Anything Lens Studio CLI',
        };
    }

    constructor(pluginSystem) {
        super(pluginSystem);
        this._pollTimer = null;
        this._heartbeatTimer = null;
        this._bridgeDir = null;
        this._commandsDir = null;
        this._responsesDir = null;
        this._heartbeatPath = null;
        this._capabilities = {};
    }

    start() {
        console.log('[ls-cli-bridge] Starting v' + PLUGIN_VERSION);

        // Strategy 1: Read config.json written by `ls-cli bridge install`
        const pluginDir = getPluginDir();
        console.log('[ls-cli-bridge] Plugin dir: ' + pluginDir);
        const config = readPluginConfig(pluginDir);

        if (config && config.bridge_dir) {
            console.log('[ls-cli-bridge] Loaded config.json — bridge_dir=' + config.bridge_dir);
            this._bridgeDir = config.bridge_dir;
            this._commandsDir = config.commands_dir || (config.bridge_dir + '/commands');
            this._responsesDir = config.responses_dir || (config.bridge_dir + '/responses');
            this._heartbeatPath = config.heartbeat_path || (config.bridge_dir + '/heartbeat.json');
        } else {
            // Strategy 2: Try fs.expandPath('~')
            const home = probeExpandPath('~');
            if (home) {
                console.log('[ls-cli-bridge] Resolved home via expandPath: ' + home);
                this._bridgeDir = home + '/.ls-cli/bridge';
            } else {
                // Strategy 3: Derive from plugin install path
                // Plugin is at ~/Library/Application Support/Snap/Lens Studio/Plugins/ls-cli-bridge/
                if (pluginDir && pluginDir.includes('/Library/Application Support/')) {
                    const homePath = pluginDir.split('/Library/Application Support/')[0];
                    console.log('[ls-cli-bridge] Derived home from plugin path: ' + homePath);
                    this._bridgeDir = homePath + '/.ls-cli/bridge';
                } else {
                    console.error('[ls-cli-bridge] Cannot determine bridge directory — aborting');
                    console.error('[ls-cli-bridge] Re-run: ls-cli bridge install');
                    return;
                }
            }
            this._commandsDir = this._bridgeDir + '/commands';
            this._responsesDir = this._bridgeDir + '/responses';
            this._heartbeatPath = this._bridgeDir + '/heartbeat.json';
        }

        // Probe capabilities and ensure directories
        this._probeCapabilities();
        this._ensureDirs();

        // Write initial heartbeat
        this._writeHeartbeat();

        // Start polling and heartbeat using setTimeout chains (safe fallback)
        this._startPolling();
        this._startHeartbeat();

        console.log('[ls-cli-bridge] Bridge plugin started — polling ' + this._commandsDir);
    }

    stop() {
        if (this._pollTimer !== null) {
            try { clearTimeout(this._pollTimer); } catch (_) { /* ignore */ }
            this._pollTimer = null;
        }
        if (this._heartbeatTimer !== null) {
            try { clearTimeout(this._heartbeatTimer); } catch (_) { /* ignore */ }
            this._heartbeatTimer = null;
        }
        console.log('[ls-cli-bridge] Bridge plugin stopped');
    }

    // ─── Capabilities probe ─────────────────────────────────────────────

    _probeCapabilities() {
        const caps = {};

        // Probe fs methods
        const fsMethods = [
            'expandPath', 'makeDirectoryRecursive', 'makeDir', 'mkdir',
            'writeFile', 'writeTextFile', 'readFile', 'readTextFile',
            'listDirectory', 'listDir', 'readdir',
            'removeFile', 'remove', 'unlink',
            'fileExists', 'exists',
        ];
        for (const m of fsMethods) {
            caps['fs.' + m] = typeof fs[m] === 'function';
        }

        // Probe Editor APIs
        try {
            caps['Editor.Model.IModel'] = !!Editor.Model.IModel;
        } catch (_) {
            caps['Editor.Model.IModel'] = false;
        }

        try {
            caps['Editor.Transform'] = typeof Editor.Transform === 'function';
        } catch (_) {
            caps['Editor.Transform'] = false;
        }

        try {
            caps['Editor.Path'] = typeof Editor.Path === 'function';
        } catch (_) {
            caps['Editor.Path'] = false;
        }

        try {
            caps['vec3'] = typeof vec3 === 'function';
        } catch (_) {
            caps['vec3'] = false;
        }

        this._capabilities = caps;
        console.log('[ls-cli-bridge] Capabilities: ' + JSON.stringify(caps));
    }

    _ensureDirs() {
        probeMkdir(this._bridgeDir);
        probeMkdir(this._commandsDir);
        probeMkdir(this._responsesDir);
    }

    // ─── Heartbeat ──────────────────────────────────────────────────────

    _writeHeartbeat() {
        try {
            const data = {
                alive: true,
                plugin_version: PLUGIN_VERSION,
                timestamp: new Date().toISOString(),
                capabilities: this._capabilities,
            };

            // Try to get LS version from model
            try {
                const model = this.pluginSystem.findInterface(Editor.Model.IModel);
                if (model && model.project) {
                    data.project_name = model.project.name || null;
                }
            } catch (_) { /* no project open yet */ }

            probeWriteFile(this._heartbeatPath, JSON.stringify(data, null, 2));
        } catch (e) {
            console.error('[ls-cli-bridge] Heartbeat write failed: ' + e);
        }
    }

    _startHeartbeat() {
        const tick = () => {
            this._writeHeartbeat();
            this._heartbeatTimer = setTimeout(tick, HEARTBEAT_INTERVAL);
        };
        this._heartbeatTimer = setTimeout(tick, HEARTBEAT_INTERVAL);
    }

    // ─── Command polling ────────────────────────────────────────────────

    _startPolling() {
        const tick = () => {
            this._processCommands();
            this._pollTimer = setTimeout(tick, POLL_INTERVAL);
        };
        this._pollTimer = setTimeout(tick, POLL_INTERVAL);
    }

    _processCommands() {
        // Since fs.listDirectory is not available in LS runtime, we use a
        // manifest-based approach: the CLI writes pending.json with an array
        // of command IDs, and we process each one by known path.
        const manifestPath = this._commandsDir + '/pending.json';

        try {
            // Check if manifest exists
            let manifestExists = false;
            try { manifestExists = fs.exists(manifestPath); } catch (_) { /* ignore */ }
            if (!manifestExists) return;

            const manifestContent = probeReadFile(manifestPath);
            if (!manifestContent) return;

            let pending;
            try {
                pending = JSON.parse(manifestContent);
            } catch (_) {
                // Corrupt manifest — remove it
                try { fs.remove(manifestPath); } catch (_) { /* ignore */ }
                return;
            }

            if (!Array.isArray(pending) || pending.length === 0) {
                // Empty manifest — clean it up
                try { fs.remove(manifestPath); } catch (_) { /* ignore */ }
                return;
            }

            // Process each command ID from the manifest
            const remaining = [];
            for (const cmdId of pending) {
                const cmdPath = this._commandsDir + '/cmd-' + cmdId + '.json';

                // Check if command file exists
                let cmdExists = false;
                try { cmdExists = fs.exists(cmdPath); } catch (_) { /* ignore */ }
                if (!cmdExists) continue; // Already processed or missing

                try {
                    const content = probeReadFile(cmdPath);
                    if (!content) continue;

                    const cmd = JSON.parse(content);
                    const result = this._dispatch(cmd);
                    this._writeResponse(cmd.id, result);

                    // Remove processed command file
                    try { fs.remove(cmdPath); } catch (_) { /* ignore */ }
                } catch (e) {
                    console.error('[ls-cli-bridge] Error processing cmd-' + cmdId + ': ' + e);
                    // Write error response
                    this._writeResponse(cmdId, { success: false, error: String(e) });
                    // Remove broken command file
                    try { fs.remove(cmdPath); } catch (_) { /* ignore */ }
                }
            }

            // Remove the manifest after processing all entries
            try { fs.remove(manifestPath); } catch (_) { /* ignore */ }
        } catch (_) {
            // Manifest read error — retry next poll
        }
    }

    _writeResponse(commandId, result) {
        if (!commandId) return;

        const response = {
            command_id: commandId,
            success: result.success !== false,
            data: result,
            error: result.error || null,
            timestamp: new Date().toISOString(),
        };

        // Clean up duplicated keys in nested data
        if (response.data) {
            delete response.data.success;
            delete response.data.error;
        }

        const respPath = this._responsesDir + '/resp-' + commandId + '.json';
        probeWriteFile(respPath, JSON.stringify(response, null, 2));
    }

    // ─── Command dispatch ───────────────────────────────────────────────

    _dispatch(cmd) {
        const key = cmd.domain + '.' + cmd.action;
        const params = cmd.params || {};

        try {
            switch (key) {
                // ── Query domain ────────────────────────────────────
                case 'query.ping':
                    return this._queryPing();
                case 'query.project_info':
                    return this._queryProjectInfo();
                case 'query.scene_tree':
                    return this._querySceneTree();
                case 'query.object_info':
                    return this._queryObjectInfo(params);
                case 'query.stats':
                    return this._queryStats();

                // ── Scene domain ────────────────────────────────────
                case 'scene.add':
                    return this._sceneAdd(params);
                case 'scene.remove':
                    return this._sceneRemove(params);
                case 'scene.rename':
                    return this._sceneRename(params);
                case 'scene.reparent':
                    return this._sceneReparent(params);
                case 'scene.list':
                    return this._sceneList();

                // ── Component domain ────────────────────────────────
                case 'component.add':
                    return this._componentAdd(params);
                case 'component.remove':
                    return this._componentRemove(params);
                case 'component.list':
                    return this._componentList(params);

                // ── Asset domain ────────────────────────────────────
                case 'asset.import':
                    return this._assetImport(params);
                case 'asset.list':
                    return this._assetList(params);
                case 'asset.delete':
                    return this._assetDelete(params);

                // ── Material domain ─────────────────────────────────
                case 'material.create':
                    return this._materialCreate(params);
                case 'material.assign':
                    return this._materialAssign(params);
                case 'material.list':
                    return this._materialList();

                // ── Script domain ───────────────────────────────────
                case 'script.create':
                    return this._scriptCreate(params);
                case 'script.attach':
                    return this._scriptAttach(params);

                // ── Prefab domain (high-level element creation) ────
                case 'prefab.face_mesh':
                    return this._prefabFaceMesh(params);
                case 'prefab.face_stretch':
                    return this._prefabFaceStretch(params);
                case 'prefab.face_inset':
                    return this._prefabFaceInset(params);
                case 'prefab.face_retouch':
                    return this._prefabFaceRetouch(params);
                case 'prefab.face_liquify':
                    return this._prefabFaceLiquify(params);
                case 'prefab.eye_color':
                    return this._prefabEyeColor(params);
                case 'prefab.hair_color':
                    return this._prefabHairColor(params);
                case 'prefab.head_attached_3d':
                    return this._prefabHeadAttached3D(params);
                case 'prefab.world_object':
                    return this._prefabWorldObject(params);
                case 'prefab.ground_plane':
                    return this._prefabGroundPlane(params);
                case 'prefab.post_effect':
                    return this._prefabPostEffect(params);
                case 'prefab.color_correction':
                    return this._prefabColorCorrection(params);
                case 'prefab.particles':
                    return this._prefabParticles(params);
                case 'prefab.segmentation':
                    return this._prefabSegmentation(params);
                case 'prefab.screen_image':
                    return this._prefabScreenImage(params);
                case 'prefab.text_overlay':
                    return this._prefabTextOverlay(params);
                case 'prefab.light':
                    return this._prefabLight(params);
                case 'prefab.camera':
                    return this._prefabCamera(params);

                default:
                    return { success: false, error: 'Unknown command: ' + key };
            }
        } catch (e) {
            return { success: false, error: String(e) };
        }
    }

    // ─── Helper: get model safely ───────────────────────────────────────

    _getModel() {
        try {
            return this.pluginSystem.findInterface(Editor.Model.IModel);
        } catch (e) {
            return null;
        }
    }

    _requireModel() {
        const model = this._getModel();
        if (!model || !model.project) {
            throw new Error('No project open in Lens Studio');
        }
        return model;
    }

    // ─── Query handlers ─────────────────────────────────────────────────

    _queryPing() {
        return {
            success: true,
            pong: true,
            plugin_version: PLUGIN_VERSION,
            capabilities: this._capabilities,
        };
    }

    _queryProjectInfo() {
        const model = this._requireModel();
        const project = model.project;

        const info = {
            success: true,
            project_name: project.name || 'Untitled',
        };

        try { info.project_dir = project.directory || null; } catch (_) { /* ignore */ }
        try { info.modified = project.isModified ? project.isModified() : null; } catch (_) { /* ignore */ }
        try {
            const am = project.assetManager;
            if (am && am.getAllAssets) {
                info.asset_count = am.getAllAssets().length;
            }
        } catch (_) { /* ignore */ }

        return info;
    }

    _querySceneTree() {
        const model = this._requireModel();
        const scene = model.project.scene;
        const roots = scene.rootSceneObjects || [];

        return {
            success: true,
            hierarchy: roots.map(so => serializeObject(so, true)),
        };
    }

    _queryObjectInfo(params) {
        if (!params.name) {
            return { success: false, error: 'Parameter "name" is required' };
        }

        const model = this._requireModel();
        const scene = model.project.scene;
        const obj = findObjectByName(scene, params.name);

        if (!obj) {
            return { success: false, error: 'Object not found: ' + params.name };
        }

        return {
            success: true,
            object: serializeObject(obj, false),
        };
    }

    _queryStats() {
        const model = this._requireModel();
        const scene = model.project.scene;
        const all = collectAll(scene.rootSceneObjects || []);

        let componentCount = 0;
        for (const so of all) {
            try {
                componentCount += (so.components || []).length;
            } catch (_) { /* ignore */ }
        }

        const stats = {
            success: true,
            object_count: all.length,
            root_count: (scene.rootSceneObjects || []).length,
            component_count: componentCount,
        };

        try {
            const am = model.project.assetManager;
            if (am && am.getAllAssets) {
                stats.asset_count = am.getAllAssets().length;
            }
        } catch (_) { /* ignore */ }

        return stats;
    }

    // ─── Scene handlers ─────────────────────────────────────────────────

    _sceneAdd(params) {
        const name = params.name || 'New Object';
        const model = this._requireModel();
        const scene = model.project.scene;

        const so = scene.createSceneObject(name);

        // Set parent if specified
        if (params.parent) {
            const parent = findObjectByName(scene, params.parent);
            if (parent) {
                so.parent = parent;
            }
        }

        // Set transform if specified
        if (params.position || params.scale) {
            try {
                const pos = params.position || { x: 0, y: 0, z: 0 };
                const scl = params.scale || { x: 1, y: 1, z: 1 };
                so.localTransform = new Editor.Transform(
                    new vec3(pos.x || 0, pos.y || 0, pos.z || 0),
                    new vec3(0, 0, 0),
                    new vec3(scl.x || 1, scl.y || 1, scl.z || 1)
                );
            } catch (_) { /* Transform API may differ */ }
        }

        return {
            success: true,
            message: 'Created object "' + so.name + '"',
            name: so.name,
        };
    }

    _sceneRemove(params) {
        if (!params.name) {
            return { success: false, error: 'Parameter "name" is required' };
        }

        const model = this._requireModel();
        const scene = model.project.scene;
        const obj = findObjectByName(scene, params.name);

        if (!obj) {
            return { success: false, error: 'Object not found: ' + params.name };
        }

        try {
            obj.destroy();
        } catch (_) {
            // Fallback: try remove
            try { scene.removeSceneObject(obj); } catch (_) { /* ignore */ }
        }

        return {
            success: true,
            message: 'Removed object "' + params.name + '"',
        };
    }

    _sceneRename(params) {
        if (!params.name || !params.new_name) {
            return { success: false, error: 'Parameters "name" and "new_name" are required' };
        }

        const model = this._requireModel();
        const scene = model.project.scene;
        const obj = findObjectByName(scene, params.name);

        if (!obj) {
            return { success: false, error: 'Object not found: ' + params.name };
        }

        obj.name = params.new_name;
        return {
            success: true,
            message: 'Renamed "' + params.name + '" to "' + params.new_name + '"',
        };
    }

    _sceneReparent(params) {
        if (!params.name) {
            return { success: false, error: 'Parameter "name" is required' };
        }

        const model = this._requireModel();
        const scene = model.project.scene;
        const child = findObjectByName(scene, params.name);

        if (!child) {
            return { success: false, error: 'Object not found: ' + params.name };
        }

        if (!params.parent) {
            // Unparent — move to root
            child.parent = null;
            return { success: true, message: 'Unparented "' + params.name + '"' };
        }

        const parent = findObjectByName(scene, params.parent);
        if (!parent) {
            return { success: false, error: 'Parent not found: ' + params.parent };
        }

        child.parent = parent;
        return {
            success: true,
            message: 'Reparented "' + params.name + '" under "' + params.parent + '"',
        };
    }

    _sceneList() {
        const model = this._requireModel();
        const scene = model.project.scene;
        const all = collectAll(scene.rootSceneObjects || []);
        const names = all.map(so => so.name);

        return {
            success: true,
            objects: names,
            count: names.length,
        };
    }

    // ─── Component handlers ─────────────────────────────────────────────

    _componentAdd(params) {
        if (!params.object || !params.type) {
            return { success: false, error: 'Parameters "object" and "type" are required' };
        }

        const model = this._requireModel();
        const scene = model.project.scene;
        const obj = findObjectByName(scene, params.object);

        if (!obj) {
            return { success: false, error: 'Object not found: ' + params.object };
        }

        const comp = obj.addComponent(params.type);

        // Set properties if provided
        if (params.properties && comp) {
            for (const key of Object.keys(params.properties)) {
                try {
                    if (key in comp) comp[key] = params.properties[key];
                } catch (_) { /* ignore property set failures */ }
            }
        }

        return {
            success: true,
            message: 'Added ' + params.type + ' to "' + params.object + '"',
        };
    }

    _componentRemove(params) {
        if (!params.object || !params.type) {
            return { success: false, error: 'Parameters "object" and "type" are required' };
        }

        const model = this._requireModel();
        const scene = model.project.scene;
        const obj = findObjectByName(scene, params.object);

        if (!obj) {
            return { success: false, error: 'Object not found: ' + params.object };
        }

        const comps = obj.components || [];
        const comp = comps.find(c => {
            try { return c.getTypeName() === params.type; } catch (_) { return false; }
        });

        if (!comp) {
            return { success: false, error: 'Component "' + params.type + '" not found on "' + params.object + '"' };
        }

        try {
            obj.removeComponent(comp);
        } catch (_) {
            try { comp.destroy(); } catch (_) { /* ignore */ }
        }

        return {
            success: true,
            message: 'Removed ' + params.type + ' from "' + params.object + '"',
        };
    }

    _componentList(params) {
        if (!params.object) {
            return { success: false, error: 'Parameter "object" is required' };
        }

        const model = this._requireModel();
        const scene = model.project.scene;
        const obj = findObjectByName(scene, params.object);

        if (!obj) {
            return { success: false, error: 'Object not found: ' + params.object };
        }

        const comps = obj.components || [];
        const types = comps.map(c => {
            try { return c.getTypeName(); } catch (_) { return 'Unknown'; }
        });

        return {
            success: true,
            object: params.object,
            components: types,
            count: types.length,
        };
    }

    // ─── Asset handlers ─────────────────────────────────────────────────

    _assetImport(params) {
        if (!params.path) {
            return { success: false, error: 'Parameter "path" is required' };
        }

        const model = this._requireModel();
        const am = model.project.assetManager;

        try {
            // importExternalFileAsync is the documented approach
            am.importExternalFileAsync(params.path);
            return {
                success: true,
                message: 'Importing asset from "' + params.path + '"',
            };
        } catch (e) {
            // Fallback: try synchronous import
            try {
                am.importExternalFile(params.path);
                return {
                    success: true,
                    message: 'Imported asset from "' + params.path + '"',
                };
            } catch (e2) {
                return { success: false, error: 'Import failed: ' + String(e2) };
            }
        }
    }

    _assetList(params) {
        const model = this._requireModel();
        const am = model.project.assetManager;

        if (!am.getAllAssets) {
            return { success: false, error: 'Asset listing not available' };
        }

        const assets = am.getAllAssets();
        const typeFilter = params.type || null;

        const listed = [];
        for (const a of assets) {
            const typeName = (a.getTypeName && a.getTypeName()) || 'Unknown';
            if (typeFilter && typeName !== typeFilter) continue;
            listed.push({
                name: a.name || 'Untitled',
                type: typeName,
            });
        }

        return {
            success: true,
            assets: listed,
            count: listed.length,
        };
    }

    _assetDelete(params) {
        if (!params.name) {
            return { success: false, error: 'Parameter "name" is required' };
        }

        const model = this._requireModel();
        const am = model.project.assetManager;

        if (!am.getAllAssets) {
            return { success: false, error: 'Asset management not available' };
        }

        const assets = am.getAllAssets();
        const asset = assets.find(a => a.name === params.name);

        if (!asset) {
            return { success: false, error: 'Asset not found: ' + params.name };
        }

        try {
            am.deleteAsset(asset);
            return { success: true, message: 'Deleted asset "' + params.name + '"' };
        } catch (e) {
            return { success: false, error: 'Delete failed: ' + String(e) };
        }
    }

    // ─── Material handlers ──────────────────────────────────────────────

    _materialCreate(params) {
        const name = params.name || 'Material';
        const model = this._requireModel();
        const am = model.project.assetManager;

        try {
            const destination = new Editor.Path(params.directory || 'Materials');
            const material = am.createNativeAsset('Material', name, destination);
            return {
                success: true,
                message: 'Created material "' + name + '"',
                material_name: name,
            };
        } catch (e) {
            return { success: false, error: 'Material creation failed: ' + String(e) };
        }
    }

    _materialAssign(params) {
        if (!params.object || !params.material) {
            return { success: false, error: 'Parameters "object" and "material" are required' };
        }

        const model = this._requireModel();
        const scene = model.project.scene;
        const am = model.project.assetManager;

        const obj = findObjectByName(scene, params.object);
        if (!obj) {
            return { success: false, error: 'Object not found: ' + params.object };
        }

        // Find material asset
        if (!am.getAllAssets) {
            return { success: false, error: 'Asset management not available' };
        }

        const assets = am.getAllAssets();
        const material = assets.find(a => a.name === params.material);
        if (!material) {
            return { success: false, error: 'Material not found: ' + params.material };
        }

        // Find RenderMeshVisual component
        const comps = obj.components || [];
        const rmv = comps.find(c => {
            try { return c.getTypeName() === 'RenderMeshVisual'; } catch (_) { return false; }
        });

        if (!rmv) {
            return { success: false, error: 'No RenderMeshVisual on "' + params.object + '"' };
        }

        try {
            rmv.mainMaterial = material;
            return {
                success: true,
                message: 'Assigned material "' + params.material + '" to "' + params.object + '"',
            };
        } catch (e) {
            // Fallback: try .material property
            try {
                rmv.material = material;
                return {
                    success: true,
                    message: 'Assigned material "' + params.material + '" to "' + params.object + '"',
                };
            } catch (e2) {
                return { success: false, error: 'Material assignment failed: ' + String(e2) };
            }
        }
    }

    _materialList() {
        const model = this._requireModel();
        const am = model.project.assetManager;

        if (!am.getAllAssets) {
            return { success: false, error: 'Asset management not available' };
        }

        const assets = am.getAllAssets();
        const materials = [];
        for (const a of assets) {
            try {
                const t = a.getTypeName ? a.getTypeName() : '';
                if (t === 'Material') {
                    materials.push({ name: a.name || 'Untitled' });
                }
            } catch (_) { /* skip */ }
        }

        return {
            success: true,
            materials: materials,
            count: materials.length,
        };
    }

    // ─── Script handlers ────────────────────────────────────────────────

    _scriptCreate(params) {
        if (!params.name) {
            return { success: false, error: 'Parameter "name" is required' };
        }

        const model = this._requireModel();
        const filename = params.name.endsWith('.js') ? params.name : params.name + '.js';
        const content = params.content || '// @input\n// @output\n\nscript.createEvent("OnStartEvent").bind(function() {\n    print("' + params.name + ' started");\n});\n';

        // Write script file to project directory
        try {
            const projectDir = model.project.directory;
            if (!projectDir) {
                return { success: false, error: 'Cannot determine project directory' };
            }

            const scriptsDir = projectDir + '/Scripts';
            probeMkdir(scriptsDir);

            const scriptPath = scriptsDir + '/' + filename;
            probeWriteFile(scriptPath, content);

            // Import into asset system
            try {
                const am = model.project.assetManager;
                am.importExternalFileAsync(scriptPath);
            } catch (_) { /* import may not be needed if inside project */ }

            return {
                success: true,
                message: 'Created script "' + filename + '"',
                path: scriptPath,
            };
        } catch (e) {
            return { success: false, error: 'Script creation failed: ' + String(e) };
        }
    }

    _scriptAttach(params) {
        if (!params.object || !params.script) {
            return { success: false, error: 'Parameters "object" and "script" are required' };
        }

        const model = this._requireModel();
        const scene = model.project.scene;
        const obj = findObjectByName(scene, params.object);

        if (!obj) {
            return { success: false, error: 'Object not found: ' + params.object };
        }

        try {
            const comp = obj.addComponent('ScriptComponent');

            // Try to find the script asset and assign it
            const am = model.project.assetManager;
            if (am.getAllAssets) {
                const assets = am.getAllAssets();
                const scriptAsset = assets.find(a => {
                    const name = a.name || '';
                    return name === params.script || name === params.script.replace('.js', '');
                });
                if (scriptAsset && comp) {
                    try { comp.script = scriptAsset; } catch (_) { /* ignore */ }
                }
            }

            return {
                success: true,
                message: 'Attached ScriptComponent to "' + params.object + '"',
            };
        } catch (e) {
            return { success: false, error: 'Script attach failed: ' + String(e) };
        }
    }

    // ─── Prefab helpers ────────────────────────────────────────────────

    /**
     * Create a scene object with optional parent and return it.
     * Shared by all prefab methods.
     */
    _createObject(scene, name, parentName) {
        const so = scene.createSceneObject(name);
        if (parentName) {
            const parent = findObjectByName(scene, parentName);
            if (parent) so.parent = parent;
        }
        return so;
    }

    /**
     * Safely add a component and set properties. Returns the component or null.
     */
    _addComp(so, type, properties) {
        try {
            const comp = so.addComponent(type);
            if (comp && properties) {
                for (const key of Object.keys(properties)) {
                    try { if (key in comp) comp[key] = properties[key]; } catch (_) { /* skip */ }
                }
            }
            return comp;
        } catch (e) {
            console.error('[ls-cli-bridge] Failed to add component ' + type + ': ' + e);
            return null;
        }
    }

    /**
     * Create a material asset and return it, or null on failure.
     */
    _createMat(am, name, directory) {
        try {
            return am.createNativeAsset('Material', name, new Editor.Path(directory || 'Materials'));
        } catch (e) {
            console.error('[ls-cli-bridge] Failed to create material ' + name + ': ' + e);
            return null;
        }
    }

    /**
     * Assign a material to a component's mainMaterial, with .material fallback.
     */
    _assignMat(comp, mat) {
        if (!comp || !mat) return;
        try { comp.mainMaterial = mat; return; } catch (_) { /* try fallback */ }
        try { comp.material = mat; } catch (_) { /* ignore */ }
    }

    /**
     * Find a mesh asset by name hint (e.g. 'sphere', 'cube', 'plane', 'face').
     * Searches project assets for RenderMesh types matching the hint.
     */
    _findMesh(am, hint) {
        try {
            if (!am.getAllAssets) return null;
            const assets = am.getAllAssets();
            const lower = hint.toLowerCase();
            for (const a of assets) {
                const t = (a.getTypeName && a.getTypeName()) || '';
                const n = (a.name || '').toLowerCase();
                if ((t === 'RenderMesh' || t.endsWith('Mesh')) &&
                    (n.includes(lower) || n.includes('primitive'))) {
                    return a;
                }
            }
        } catch (_) { /* ignore */ }
        return null;
    }

    /**
     * Assign a mesh resource to a RenderMeshVisual component.
     */
    _assignMesh(rmv, am, meshHint) {
        if (!rmv || !am) return false;
        const mesh = this._findMesh(am, meshHint);
        if (mesh) {
            try { rmv.mesh = mesh; return true; } catch (_) { /* ignore */ }
        }
        return false;
    }

    /**
     * Try to set a material's pass/graph type for specific visual styles.
     * Lens Studio materials have mainPass or passInfo properties in some API versions.
     */
    _setMatPass(mat, passName) {
        if (!mat) return;
        const setters = [
            () => { mat.mainPass.baseMaterialName = passName; },
            () => { mat.passInfo = passName; },
            () => { mat.materialType = passName; },
        ];
        for (const fn of setters) {
            try { fn(); return; } catch (_) { /* try next */ }
        }
    }

    _prefabResult(name, type, components) {
        return {
            success: true,
            message: 'Created ' + type + ' "' + name + '"',
            name: name,
            type: type,
            components: components,
        };
    }

    // ─── Face Effects prefabs ──────────────────────────────────────────

    _prefabFaceMesh(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const am = model.project.assetManager;
        const name = params.name || 'Face Mesh';

        const so = this._createObject(scene, name, params.parent);
        const head = this._addComp(so, 'Head', null);
        // Set attachment point to center of face
        if (head) {
            try { head.attachmentPoint = 'center'; } catch (_) { /* ignore */ }
        }
        this._addComp(so, 'FaceMask', null);
        const rmv = this._addComp(so, 'RenderMeshVisual', null);

        // Try to find and assign a face mesh resource
        this._assignMesh(rmv, am, 'face');

        // Create material with FaceMesh pass type
        const mat = this._createMat(am, name + ' Mat', 'Materials');
        this._setMatPass(mat, params.material_type || 'FaceMesh');
        this._assignMat(rmv, mat);

        return this._prefabResult(name, 'face_mesh', ['Head', 'FaceMask', 'RenderMeshVisual']);
    }

    _prefabFaceStretch(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const name = params.name || 'Face Stretch';

        const so = this._createObject(scene, name, params.parent);
        const head = this._addComp(so, 'Head', null);
        if (head) {
            try { head.attachmentPoint = 'center'; } catch (_) { /* ignore */ }
        }
        const fs = this._addComp(so, 'FaceStretch', null);
        // Set a default stretch intensity so the effect is visible
        if (fs && params.intensity) {
            try { fs.intensity = parseFloat(params.intensity); } catch (_) { /* ignore */ }
        }

        return this._prefabResult(name, 'face_stretch', ['Head', 'FaceStretch']);
    }

    _prefabFaceInset(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const am = model.project.assetManager;
        const name = params.name || 'Face Inset';

        const so = this._createObject(scene, name, params.parent);
        const head = this._addComp(so, 'Head', null);
        if (head) {
            try { head.attachmentPoint = 'center'; } catch (_) { /* ignore */ }
        }
        const fi = this._addComp(so, 'FaceInset', null);
        // Set face region if specified (eyes, mouth, etc.)
        if (fi && params.region) {
            try { fi.faceRegion = params.region; } catch (_) { /* ignore */ }
        }

        // Face inset needs a RenderMeshVisual + material to show the cutout
        const rmv = this._addComp(so, 'RenderMeshVisual', null);
        this._assignMesh(rmv, am, 'face');
        const mat = this._createMat(am, name + ' Mat', 'Materials');
        this._setMatPass(mat, 'FaceMesh');
        this._assignMat(rmv, mat);

        return this._prefabResult(name, 'face_inset', ['Head', 'FaceInset', 'RenderMeshVisual']);
    }

    _prefabFaceRetouch(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const name = params.name || 'Face Retouch';

        const so = this._createObject(scene, name, params.parent);
        const head = this._addComp(so, 'Head', null);
        if (head) {
            try { head.attachmentPoint = 'center'; } catch (_) { /* ignore */ }
        }
        const rv = this._addComp(so, 'RetouchVisual', null);
        // Set retouch intensity for visible effect
        if (rv) {
            const intensity = params.intensity ? parseFloat(params.intensity) : 0.5;
            try { rv.softSkinIntensity = intensity; } catch (_) { /* ignore */ }
            try { rv.sharpenEyeIntensity = intensity; } catch (_) { /* ignore */ }
            try { rv.teethWhiteningIntensity = intensity; } catch (_) { /* ignore */ }
        }

        return this._prefabResult(name, 'face_retouch', ['Head', 'RetouchVisual']);
    }

    _prefabFaceLiquify(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const name = params.name || 'Face Liquify';

        const so = this._createObject(scene, name, params.parent);
        const head = this._addComp(so, 'Head', null);
        if (head) {
            try { head.attachmentPoint = 'center'; } catch (_) { /* ignore */ }
        }
        const lv = this._addComp(so, 'LiquifyVisual', null);
        // Set default liquify parameters so the effect is noticeable
        if (lv) {
            const intensity = params.intensity ? parseFloat(params.intensity) : 0.3;
            try { lv.intensity = intensity; } catch (_) { /* ignore */ }
        }

        return this._prefabResult(name, 'face_liquify', ['Head', 'LiquifyVisual']);
    }

    _prefabEyeColor(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const am = model.project.assetManager;
        const name = params.name || 'Eye Color';

        const so = this._createObject(scene, name, params.parent);
        const head = this._addComp(so, 'Head', null);
        if (head) {
            try { head.attachmentPoint = 'center'; } catch (_) { /* ignore */ }
        }
        const ecv = this._addComp(so, 'EyeColorVisual', null);

        const mat = this._createMat(am, name + ' Mat', 'Materials');
        this._setMatPass(mat, 'Unlit');
        this._assignMat(ecv, mat);

        return this._prefabResult(name, 'eye_color', ['Head', 'EyeColorVisual']);
    }

    _prefabHairColor(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const am = model.project.assetManager;
        const name = params.name || 'Hair Color';

        const so = this._createObject(scene, name, params.parent);
        const head = this._addComp(so, 'Head', null);
        if (head) {
            try { head.attachmentPoint = 'center'; } catch (_) { /* ignore */ }
        }
        const hv = this._addComp(so, 'HairVisual', null);

        const mat = this._createMat(am, name + ' Mat', 'Materials');
        this._setMatPass(mat, 'Unlit');
        this._assignMat(hv, mat);

        return this._prefabResult(name, 'hair_color', ['Head', 'HairVisual']);
    }

    _prefabHeadAttached3D(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const am = model.project.assetManager;
        const name = params.name || 'Head Attached 3D';
        const meshType = params.mesh_type || 'sphere';

        // Parent object with head tracking
        const so = this._createObject(scene, name, params.parent);
        const head = this._addComp(so, 'Head', null);
        if (head) {
            try { head.attachmentPoint = params.attachment || 'center'; } catch (_) { /* ignore */ }
        }

        // Child object with visual mesh
        const child = scene.createSceneObject(name + ' Mesh');
        child.parent = so;
        const rmv = this._addComp(child, 'RenderMeshVisual', null);

        // Assign a mesh resource (sphere by default for things like clown nose)
        this._assignMesh(rmv, am, meshType);

        // Scale down for head-attached objects
        try {
            child.localTransform = new Editor.Transform(
                new vec3(params.offset_x || 0, params.offset_y || 0, params.offset_z || 0),
                new vec3(0, 0, 0),
                new vec3(params.scale || 0.3, params.scale || 0.3, params.scale || 0.3)
            );
        } catch (_) { /* ignore */ }

        const mat = this._createMat(am, name + ' Mat', 'Materials');
        this._setMatPass(mat, 'PBR');
        this._assignMat(rmv, mat);

        return this._prefabResult(name, 'head_attached_3d', ['Head', 'RenderMeshVisual']);
    }

    // ─── World AR prefabs ──────────────────────────────────────────────

    _prefabWorldObject(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const am = model.project.assetManager;
        const name = params.name || 'World Object';
        const meshType = params.mesh_type || 'cube';

        // Parent with device tracking
        const so = this._createObject(scene, name, params.parent);
        const dt = this._addComp(so, 'DeviceTracking', null);
        if (dt) {
            try { dt.requestedTrackingMode = 2; } catch (_) { /* ignore */ } // 2 = World
            try { dt.trackingMode = 'World'; } catch (_) { /* ignore */ }
        }

        // Child with visual
        const child = scene.createSceneObject(name + ' Mesh');
        child.parent = so;
        const rmv = this._addComp(child, 'RenderMeshVisual', null);

        // Assign actual mesh resource
        this._assignMesh(rmv, am, meshType);

        const mat = this._createMat(am, name + ' Mat', 'Materials');
        this._setMatPass(mat, 'PBR');
        this._assignMat(rmv, mat);

        return this._prefabResult(name, 'world_object', ['DeviceTracking', 'RenderMeshVisual']);
    }

    _prefabGroundPlane(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const am = model.project.assetManager;
        const name = params.name || 'Ground Plane';

        // Parent with world tracking
        const so = this._createObject(scene, name, params.parent);
        const dt = this._addComp(so, 'DeviceTracking', null);
        if (dt) {
            try { dt.requestedTrackingMode = 2; } catch (_) { /* ignore */ }
            try { dt.trackingMode = 'World'; } catch (_) { /* ignore */ }
        }

        // Child plane at y=0
        const child = scene.createSceneObject(name + ' Surface');
        child.parent = so;
        const rmv = this._addComp(child, 'RenderMeshVisual', null);

        // Assign plane mesh resource
        this._assignMesh(rmv, am, 'plane');

        // Set flat scale for plane appearance
        try {
            child.localTransform = new Editor.Transform(
                new vec3(0, 0, 0),
                new vec3(0, 0, 0),
                new vec3(10, 0.01, 10)
            );
        } catch (_) { /* transform may differ */ }

        const mat = this._createMat(am, name + ' Mat', 'Materials');
        this._setMatPass(mat, 'PBR');
        this._assignMat(rmv, mat);

        return this._prefabResult(name, 'ground_plane', ['DeviceTracking', 'RenderMeshVisual']);
    }

    // ─── Visual Effects prefabs ────────────────────────────────────────

    _prefabPostEffect(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const am = model.project.assetManager;
        const name = params.name || 'Post Effect';

        // Find existing camera or create under it
        let cameraObj = findObjectByName(scene, 'Camera');
        const so = this._createObject(scene, name, cameraObj ? 'Camera' : params.parent);
        const pev = this._addComp(so, 'PostEffectVisual', null);

        const mat = this._createMat(am, name + ' Mat', 'Materials');
        this._setMatPass(mat, 'Graph');
        this._assignMat(pev, mat);

        return this._prefabResult(name, 'post_effect', ['PostEffectVisual']);
    }

    _prefabColorCorrection(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const am = model.project.assetManager;
        const name = params.name || 'Color Correction';

        let cameraObj = findObjectByName(scene, 'Camera');
        const so = this._createObject(scene, name, cameraObj ? 'Camera' : params.parent);
        const ccv = this._addComp(so, 'PostEffectVisual', null);

        const mat = this._createMat(am, name + ' Mat', 'Materials');
        this._setMatPass(mat, 'Graph');
        this._assignMat(ccv, mat);

        return this._prefabResult(name, 'color_correction', ['PostEffectVisual']);
    }

    _prefabParticles(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const am = model.project.assetManager;
        const name = params.name || 'Particles';

        const so = this._createObject(scene, name, params.parent);
        const pv = this._addComp(so, 'ParticlesVisual', null);

        const mat = this._createMat(am, name + ' Mat', 'Materials');
        this._setMatPass(mat, 'Unlit');
        this._assignMat(pv, mat);

        return this._prefabResult(name, 'particles', ['ParticlesVisual']);
    }

    _prefabSegmentation(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const name = params.name || 'Segmentation';
        const segType = params.segmentation_type || 'Background';

        const so = this._createObject(scene, name, params.parent);
        const stp = this._addComp(so, 'SegmentationTextureProvider', null);
        if (stp) {
            try { stp.segmentationType = segType; } catch (_) { /* ignore */ }
        }
        this._addComp(so, 'Image', null);

        return this._prefabResult(name, 'segmentation', ['SegmentationTextureProvider', 'Image']);
    }

    // ─── Common Elements prefabs ───────────────────────────────────────

    _prefabScreenImage(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const am = model.project.assetManager;
        const name = params.name || 'Screen Image';

        // Create under orthographic camera if it exists
        let orthoCamera = findObjectByName(scene, 'Orthographic Camera');
        const so = this._createObject(scene, name, orthoCamera ? 'Orthographic Camera' : params.parent);
        this._addComp(so, 'ScreenTransform', null);
        const img = this._addComp(so, 'Image', null);

        // Try to assign a texture if specified
        if (params.texture && img && am.getAllAssets) {
            try {
                const assets = am.getAllAssets();
                const tex = assets.find(a => (a.name || '') === params.texture);
                if (tex) img.mainPass.baseTex = tex;
            } catch (_) { /* ignore */ }
        }

        return this._prefabResult(name, 'screen_image', ['ScreenTransform', 'Image']);
    }

    _prefabTextOverlay(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const name = params.name || 'Text Overlay';

        let orthoCamera = findObjectByName(scene, 'Orthographic Camera');
        const so = this._createObject(scene, name, orthoCamera ? 'Orthographic Camera' : params.parent);
        this._addComp(so, 'ScreenTransform', null);
        const textComp = this._addComp(so, 'Text', null);

        if (textComp) {
            // Set text content
            if (params.text) {
                try { textComp.text = params.text; } catch (_) { /* ignore */ }
            }
            // Set font size if specified
            if (params.font_size) {
                try { textComp.size = parseFloat(params.font_size); } catch (_) { /* ignore */ }
            }
        }

        return this._prefabResult(name, 'text_overlay', ['ScreenTransform', 'Text']);
    }

    _prefabLight(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const name = params.name || 'Light';
        const lightType = params.light_type || 'Directional';

        const so = this._createObject(scene, name, params.parent);
        const lightComp = this._addComp(so, 'LightSource', null);

        if (lightComp) {
            try { lightComp.lightType = lightType; } catch (_) { /* ignore */ }
            // Set intensity (default 1.0)
            const intensity = params.intensity ? parseFloat(params.intensity) : 1.0;
            try { lightComp.intensity = intensity; } catch (_) { /* ignore */ }
            // Set color if specified (as {r,g,b} 0-1)
            if (params.color) {
                try { lightComp.color = params.color; } catch (_) { /* ignore */ }
            }
        }

        // Position directional lights above the scene
        if (lightType === 'Directional') {
            try {
                so.localTransform = new Editor.Transform(
                    new vec3(0, 10, 0),
                    new vec3(-45, 0, 0),
                    new vec3(1, 1, 1)
                );
            } catch (_) { /* ignore */ }
        }

        return this._prefabResult(name, 'light', ['LightSource']);
    }

    _prefabCamera(params) {
        const model = this._requireModel();
        const scene = model.project.scene;
        const name = params.name || 'Camera';
        const cameraType = params.camera_type || 'Perspective';

        const so = this._createObject(scene, name, params.parent);
        const camComp = this._addComp(so, 'Camera', null);

        if (camComp) {
            try { camComp.cameraType = cameraType; } catch (_) { /* ignore */ }
            // Set near/far clip planes
            if (params.near) {
                try { camComp.near = parseFloat(params.near); } catch (_) { /* ignore */ }
            }
            if (params.far) {
                try { camComp.far = parseFloat(params.far); } catch (_) { /* ignore */ }
            }
        }

        return this._prefabResult(name, 'camera', ['Camera']);
    }
}
