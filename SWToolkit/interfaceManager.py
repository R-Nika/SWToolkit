import bpy

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
        version_box.label(text="Version: 1.0.0", icon='FILE_TICK')  # Version with icon

        # GitHub and Discord links inside their own box
        links_box = main_box.box()  # Create a box for the GitHub and Discord links
        links_box.operator("wm.url_open", text="Visit GitHub").url = "https://github.com/R-Nika/SWToolkit"
        links_box.operator("wm.url_open", text="Join the SMF Discord").url = "https://discord.gg/mFY8Wuk"

# Register and unregister functions
def register():
    bpy.utils.register_class(SWToolkitPanel)

def unregister():
    bpy.utils.unregister_class(SWToolkitPanel)

if __name__ == "__main__":
    register()
