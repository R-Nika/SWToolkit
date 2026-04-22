import bpy
import urllib.request
import json
import textwrap
from . import CURRENT_VERSION

# ------------------------------------------------------------------------
# Helper: Multiline Label
# ------------------------------------------------------------------------
def _label_multiline(context, text, parent):
    chars = int(context.region.width / 14)
    wrapper = textwrap.TextWrapper(width=chars, break_long_words=True, expand_tabs=False)
    text_lines = wrapper.wrap(text=text)
    for text_line in text_lines:
        parent.label(text=text_line)

# ------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------
GITHUB_API_RELEASES_URL = "https://api.github.com/repos/R-Nika/SWToolkit/releases/latest"

# Store update info globally
UPDATE_AVAILABLE = False
LATEST_VERSION = None

# ------------------------------------------------------------------------
# Prerelease Setting
# ------------------------------------------------------------------------
# Set this to True for prerelease versions that shouldn't be distributed
PRERELEASE = False

# ------------------------------------------------------------------------
# Check for updates (runs once on load)
# ------------------------------------------------------------------------
def check_for_update():
    global UPDATE_AVAILABLE, LATEST_VERSION
    
    # Don't check for updates if this is a prerelease
    if PRERELEASE:
        print("[SWToolkit] Prerelease mode active - update checking disabled")
        return
        
    try:
        with urllib.request.urlopen(GITHUB_API_RELEASES_URL) as response:
            data = json.loads(response.read().decode())
            latest_version = data.get("tag_name", "").lstrip("v")

            if latest_version and latest_version != CURRENT_VERSION:
                UPDATE_AVAILABLE = True
                LATEST_VERSION = latest_version

                # Show popup notification
                def notify():
                    bpy.context.window_manager.popup_menu(
                        lambda self, context: self.layout.label(
                            text=f"A new version ({latest_version}) of SW Toolkit is available!"
                        ),
                        title="SW Toolkit Update",
                        icon='INFO'
                    )
                bpy.app.timers.register(notify, first_interval=1.0)

                # Force UI refresh to show warning
                def redraw_ui():
                    for window in bpy.context.window_manager.windows:
                        for area in window.screen.areas:
                            if area.type == 'VIEW_3D':
                                area.tag_redraw()
                    return None
                bpy.app.timers.register(redraw_ui, first_interval=1.0)

    except Exception as e:
        print(f"[SWToolkit] Update check failed: {e}")

# ------------------------------------------------------------------------
# UI Panel
# ------------------------------------------------------------------------
class SWToolkitPanel(bpy.types.Panel):
    bl_label = "SW Toolkit"
    bl_idname = "VIEW3D_PT_sw_toolkit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SW Toolkit"

    def draw(self, context):
        layout = self.layout
        
        # Main outer box
        outer_box = layout.box()
        
        # Show prerelease warning if enabled
        if PRERELEASE:
            prerelease_box = outer_box.box()
            prerelease_box.scale_y = 0.8
            prerelease_box.alert = True
            warn_row = prerelease_box.row()
            warn_row.label(text="⚠️ PRERELEASE VERSION ⚠️", icon='ERROR')
            warn_row = prerelease_box.row()
            warn_row.label(text="EXPECT BUGS, PLEASE REPORT", icon='CANCEL')
            
            # Add a separator
            outer_box.separator()
        
        # Nested box containing both version text and button
        inner_box = outer_box.box()
        version_row = inner_box.row()
        
        # Show version with prerelease indicator
        if PRERELEASE:
            version_row.label(text=f"[PRERELEASE] SW Toolkit v{CURRENT_VERSION}", icon='ERROR')
        else:
            version_row.label(text=f"SW Toolkit v{CURRENT_VERSION}", icon='FILE_TICK')
            
        inner_box.operator("wm.url_open", text="Join the SMF Discord", icon='URL').url = "https://discord.gg/mFY8Wuk"

        # Show warning if update available (in a nested box)
        global UPDATE_AVAILABLE, LATEST_VERSION
        if UPDATE_AVAILABLE and LATEST_VERSION:
            warning_box = outer_box.box()
            warn_row = warning_box.row()
            warn_row.label(text=f"Update available: v{LATEST_VERSION}", icon='ERROR')
            link_row = warning_box.row()
            op = link_row.operator("wm.url_open", text="Get Latest on GitHub", icon='URL')
            op.url = "https://github.com/R-Nika/SWToolkit/releases/latest"

# ------------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------------
def register():
    bpy.utils.register_class(SWToolkitPanel)
    
    # Only check for updates if not a prerelease
    if not PRERELEASE:
        bpy.app.timers.register(check_for_update, first_interval=2.0)
    else:
        print("[SWToolkit] Running in PRERELEASE mode - DO NOT DISTRIBUTE")

def unregister():
    bpy.utils.unregister_class(SWToolkitPanel)

if __name__ == "__main__":
    register()