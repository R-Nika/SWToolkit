import bpy
import urllib.request
import json
import textwrap

from . import CURRENT_VERSION


# ------------------------------------------------------------------------
# Helper: Multiline Label
# ------------------------------------------------------------------------

def _label_multiline(context, text, parent):
    chars = max(20, int(context.region.width / 14))

    wrapper = textwrap.TextWrapper(
        width=chars,
        break_long_words=True,
        expand_tabs=False
    )

    text_lines = wrapper.wrap(text=text)

    for text_line in text_lines:
        parent.label(text=text_line)


# ------------------------------------------------------------------------
# Release Notes Parser
# ------------------------------------------------------------------------

def parse_release_notes(markdown):
    """
    Extract the 'Changes' section from GitHub release notes.

    Expected format:

    ## Changes

    ### Added
    - Something new

    ### Improved
    - Something improved

    ### Fixed
    - Something fixed

    Everything after the next ## section is ignored.
    """

    lines = markdown.splitlines()

    in_changes = False
    result = []

    for line in lines:
        stripped = line.strip()

        # Start of Changes section
        if stripped.lower() == "## changes":
            in_changes = True
            continue

        # Stop at the next major section
        if in_changes and stripped.startswith("## "):
            break

        if not in_changes:
            continue

        # Empty line
        if not stripped:
            if result and result[-1] != "":
                result.append("")
            continue

        # Category heading
        if stripped.startswith("### "):
            category = stripped[4:].strip()
            result.append(category)
            continue

        # Bullet point
        if stripped.startswith("- "):
            result.append("• " + stripped[2:])
            continue

        # Other text
        result.append(stripped)

    # Remove trailing blank lines
    while result and result[-1] == "":
        result.pop()

    return result


# ------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------

GITHUB_API_RELEASES_URL = (
    "https://api.github.com/repos/R-Nika/SWToolkit/releases/latest"
)


# ------------------------------------------------------------------------
# Update State
# ------------------------------------------------------------------------

UPDATE_AVAILABLE = False
LATEST_VERSION = None
RELEASE_NOTES = []
RELEASE_URL = ""

PRERELEASE = False


# ------------------------------------------------------------------------
# Version Helper
# ------------------------------------------------------------------------

def version_tuple(version):
    """
    Convert a version string such as '0.3.10'
    into a tuple that can be compared correctly.
    """

    try:
        return tuple(
            int(x)
            for x in version.split(".")
        )
    except ValueError:
        return (0,)


# ------------------------------------------------------------------------
# Check for Updates
# ------------------------------------------------------------------------

def check_for_update():
    global UPDATE_AVAILABLE
    global LATEST_VERSION
    global RELEASE_NOTES
    global RELEASE_URL

    if PRERELEASE:
        print(
            "[SWToolkit] Prerelease mode active - "
            "update checking disabled"
        )
        return None

    try:
        with urllib.request.urlopen(
            GITHUB_API_RELEASES_URL,
            timeout=5
        ) as response:

            data = json.loads(
                response.read().decode()
            )

        latest_version = data.get(
            "tag_name",
            ""
        ).lstrip("v")

        release_notes = data.get(
            "body",
            ""
        )

        release_url = data.get(
            "html_url",
            ""
        )

        if not latest_version:
            return None

        installed = version_tuple(
            CURRENT_VERSION
        )

        latest = version_tuple(
            latest_version
        )

        # Only show an update when the GitHub version
        # is actually newer than the installed version.
        if latest > installed:

            UPDATE_AVAILABLE = True
            LATEST_VERSION = latest_version
            RELEASE_NOTES = parse_release_notes(
                release_notes
            )
            RELEASE_URL = release_url

            # --------------------------------------------------------
            # Popup notification
            # --------------------------------------------------------

            bpy.context.window_manager.popup_menu(
                lambda self, context: self.layout.label(
                    text=(
                        f"A new version "
                        f"({latest_version}) of "
                        f"SW Toolkit is available!"
                    )
                ),
                title="SW Toolkit Update",
                icon='INFO'
            )

            # --------------------------------------------------------
            # Refresh UI
            # --------------------------------------------------------

            for window in (
                bpy.context.window_manager.windows
            ):
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()

    except Exception as e:
        print(
            f"[SWToolkit] Update check failed: {e}"
        )

    # Returning None means the timer does not repeat.
    return None


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

        # ------------------------------------------------------------
        # Prerelease Warning
        # ------------------------------------------------------------

        if PRERELEASE:

            prerelease_box = outer_box.box()
            prerelease_box.scale_y = 0.8
            prerelease_box.alert = True

            warn_row = prerelease_box.row()
            warn_row.label(
                text="PRERELEASE VERSION",
                icon='ERROR'
            )

            warn_row = prerelease_box.row()
            warn_row.label(
                text="EXPECT BUGS, PLEASE REPORT",
                icon='CANCEL'
            )

            outer_box.separator()

        # ------------------------------------------------------------
        # Version + Discord
        # ------------------------------------------------------------

        inner_box = outer_box.box()

        version_row = inner_box.row()

        if PRERELEASE:

            version_row.label(
                text=(
                    f"[PRERELEASE] "
                    f"SW Toolkit v{CURRENT_VERSION}"
                ),
                icon='ERROR'
            )

        else:

            version_row.label(
                text=f"SW Toolkit v{CURRENT_VERSION}",
                icon='FILE_TICK'
            )

        inner_box.operator(
            "wm.url_open",
            text="Join the SMF Discord",
            icon='URL'
        ).url = "https://discord.gg/mFY8Wuk"

        # ------------------------------------------------------------
        # Update Available
        # ------------------------------------------------------------

        if UPDATE_AVAILABLE and LATEST_VERSION:

            update_box = outer_box.box()

            # --------------------------------------------------------
            # Update Header
            # --------------------------------------------------------

            header_row = update_box.row()
            header_row.alert = True

            header_row.label(
                text=f"Update available: v{LATEST_VERSION}",
                icon='ERROR'
            )

            # --------------------------------------------------------
            # View Release
            # --------------------------------------------------------

            if RELEASE_URL:

                release_row = update_box.row()

                release_row.operator(
                    "wm.url_open",
                    text="View Release",
                    icon='URL'
                ).url = RELEASE_URL

            # --------------------------------------------------------
            # What's New
            # --------------------------------------------------------

            whats_new_row = update_box.row()

            icon = (
                "TRIA_DOWN"
                if context.scene.sw_toolkit_show_whats_new
                else "TRIA_RIGHT"
            )

            whats_new_row.prop(
                context.scene,
                "sw_toolkit_show_whats_new",
                text="",
                icon=icon,
                emboss=False
            )

            whats_new_row.label(
                text="What's New"
            )

            # --------------------------------------------------------
            # Release Notes
            # --------------------------------------------------------

            if context.scene.sw_toolkit_show_whats_new:

                notes_box = update_box.box()

                if RELEASE_NOTES:

                    for line in RELEASE_NOTES:

                        # Blank line
                        if not line:

                            notes_box.separator()
                            continue

                        # Bullet point
                        if line.startswith("• "):

                            _label_multiline(
                                context,
                                line,
                                notes_box
                            )

                        # Category heading
                        else:

                            category_row = notes_box.row()
                            category_row.label(
                                text=line
                            )

                else:

                    notes_box.label(
                        text="No changes listed."
                    )


# ------------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------------

def register():

    bpy.utils.register_class(
        SWToolkitPanel
    )

    bpy.types.Scene.sw_toolkit_show_whats_new = (
        bpy.props.BoolProperty(
            name="What's New",
            description="Show the latest release changes",
            default=False
        )
    )

    # ------------------------------------------------------------
    # Update Check
    # ------------------------------------------------------------

    if not PRERELEASE:

        if not bpy.app.timers.is_registered(
            check_for_update
        ):

            bpy.app.timers.register(
                check_for_update,
                first_interval=2.0
            )

    else:

        print(
            "[SWToolkit] Running in PRERELEASE mode - "
            "DO NOT DISTRIBUTE"
        )


# ------------------------------------------------------------------------
# Unregistration
# ------------------------------------------------------------------------

def unregister():

    # Stop update timer if it is still registered
    if bpy.app.timers.is_registered(
        check_for_update
    ):

        bpy.app.timers.unregister(
            check_for_update
        )

    # Remove Scene property
    if hasattr(
        bpy.types.Scene,
        "sw_toolkit_show_whats_new"
    ):

        del bpy.types.Scene.sw_toolkit_show_whats_new

    # Unregister panel
    bpy.utils.unregister_class(
        SWToolkitPanel
    )


# ------------------------------------------------------------------------
# Standalone Execution
# ------------------------------------------------------------------------

if __name__ == "__main__":
    register()