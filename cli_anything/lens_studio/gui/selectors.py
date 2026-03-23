"""Version-keyed selectors for Lens Studio UI elements.

Menu paths, button titles, and AX element identifiers that may change
between Lens Studio versions. Centralised here for maintainability.
"""

# Menu bar paths — each entry is a list of menu item titles to navigate
MENU_PATHS = {
    "file_open": ["File", "Open Project..."],
    "file_save": ["File", "Save Project"],
    "file_save_as": ["File", "Save Project As..."],
    "file_new": ["File", "New Project"],
    "file_export": ["File", "Export Lens..."],
    "build": ["File", "Build Lens"],
    "preview_start": ["Preview", "Start Preview"],
    "preview_stop": ["Preview", "Stop Preview"],
    "preview_pair": ["Preview", "Pair Device..."],
    "edit_undo": ["Edit", "Undo"],
    "edit_redo": ["Edit", "Redo"],
    "scene_add_object": ["Scene", "Add Object"],
}

# Dialog button titles
DIALOG_BUTTONS = {
    "ok": "OK",
    "cancel": "Cancel",
    "save": "Save",
    "dont_save": "Don't Save",
    "export": "Export",
    "build": "Build",
    "open": "Open",
}

# Window title patterns (substring match)
WINDOW_PATTERNS = {
    "main": "Lens Studio",
    "preview": "Preview",
    "export_dialog": "Export",
    "build_dialog": "Build",
    "open_dialog": "Open",
    "save_dialog": "Save",
}

# AX roles used for finding elements
AX_ROLES = {
    "button": "AXButton",
    "menu_bar": "AXMenuBar",
    "menu": "AXMenu",
    "menu_item": "AXMenuItem",
    "window": "AXWindow",
    "text_field": "AXTextField",
    "sheet": "AXSheet",
    "dialog": "AXDialog",
    "toolbar": "AXToolbar",
    "group": "AXGroup",
}

# Build/export target options (for dropdown selection)
BUILD_TARGETS = {
    "snapchat": "Snapchat",
    "spectacles": "Spectacles",
    "web": "Web",
}
