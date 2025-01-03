import bpy
from bpy.types import Panel
from bpy.utils import register_class
from bpy.utils import unregister_class

import textwrap

# Function to handle dynamic multiline text
def _label_multiline(context, text, parent):
    # Calculate the number of characters that fit into the panel width
    chars = int(context.region.width / 14)
    wrapper = textwrap.TextWrapper(width=chars, break_long_words=True, expand_tabs=False)

    # Wrap the text into lines that fit the width
    text_lines = wrapper.wrap(text=text)

    # Add each line to the panel as a label
    for text_line in text_lines:
        parent.label(text=text_line)  # Add the line as a label


# The main SWToolkitPanel class
class SWToolkitPanel(bpy.types.Panel):
    bl_label = "SW Toolkit"  # Tab title
    bl_idname = "VIEW3D_PT_sw_toolkit"  # Unique identifier for the panel
    bl_space_type = 'VIEW_3D'  # The space where the panel will be shown
    bl_region_type = 'UI'  # The region where the panel will be placed (UI region)
    bl_category = "SW Toolkit"  # The name of the tab

    def draw(self, context):
        layout = self.layout
        
        # Outer Box
        main_box = layout.box()  # Create the outer box to contain everything

        # Version Section inside a box
        version_box = main_box.box()  # Create a box for the version section
        version_box.label(text="Version: 0.1.0", icon='FILE_TICK')  # Version with icon
        version_box.label(text="In Development", icon='PREFERENCES')  # In Development label with icon

        # GitHub and Discord links inside their own box
        links_box = main_box.box()  # Create a box for the GitHub and Discord links
        links_box.operator("wm.url_open", text="Visit GitHub").url = "https://github.com/R-Nika/SWToolkit"
        links_box.operator("wm.url_open", text="Join the SMF Discord").url = "https://discord.gg/mFY8Wuk"


# Register and unregister functions
def register():
    register_class(SWToolkitPanel)

def unregister():
    unregister_class(SWToolkitPanel)

if __name__ == "__main__":
    register()
