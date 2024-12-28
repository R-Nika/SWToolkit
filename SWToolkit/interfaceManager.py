import bpy

class SWToolkitPanel(bpy.types.Panel):
    bl_label = "SW Toolkit"
    bl_idname = "SW_PT_Toolkit"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "SW Toolkit"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Header for the collapsible section
        layout.label(text="Welcome to the SW Toolkit!")

        # Collapsible box section Material to Vertex Color
        row = layout.row()
        row.prop(context.scene, "sw_toolkit_mat_to_vert_collapsed", text="Material to Vertex Color", icon='TRIA_DOWN' if not context.scene.sw_toolkit_mat_to_vert_collapsed else 'TRIA_RIGHT')
        if not context.scene.sw_toolkit_mat_to_vert_collapsed:
            # This is the content of the collapsible section
            box = layout.box()
            box.operator("object.mat_to_vert")

        # Optional: Add some spacing
        layout.separator()

        # Collapsible box section Vertex Color Split & Optimize
        row = layout.row()
        row.prop(context.scene, "sw_toolkit_split_optimize_collapsed", text="Vertex Color Split & Optimize", icon='TRIA_DOWN' if not context.scene.sw_toolkit_split_optimize_collapsed else 'TRIA_RIGHT')
        if not context.scene.sw_toolkit_split_optimize_collapsed:
            # This is the content of the collapsible section
            box = layout.box()

            # Place the operator button **before** the Merge Options
            box.operator("object.separate_by_vertex_color")  # Vertex Split Operator

            # Merge Options
            box.label(text="Merge Options")
            box.prop(scene, "merge_by_distance", text="Merge by Distance")
            if scene.merge_by_distance:
                box.prop(scene, "merge_distance_threshold", text="Merge Threshold")

            # Limited Dissolve Options
            box.label(text="Limited Dissolve Options")
            box.prop(scene, "limited_dissolve", text="Limited Dissolve")
            if scene.limited_dissolve:
                box.prop(scene, "limited_dissolve_degrees", text="Dissolve Degrees")

            # Triangulation & Edge Split Options
            box.label(text="Post-Processing Options")
            box.prop(scene, "triangulate", text="Triangulate")
            box.prop(scene, "edge_split", text="Edge Split")
            box.prop(scene, "join_objects", text="Join Objects")


# Add properties to the scene (same as in vertexcolorsplitter.py)
def add_scene_properties():
    bpy.types.Scene.merge_by_distance = bpy.props.BoolProperty(name="Merge by Distance", default=False)
    bpy.types.Scene.merge_distance_threshold = bpy.props.FloatProperty(name="Merge Threshold", default=0.001, min=0.0)
    bpy.types.Scene.limited_dissolve = bpy.props.BoolProperty(name="Limited Dissolve", default=False)
    bpy.types.Scene.limited_dissolve_degrees = bpy.props.FloatProperty(name="Dissolve Degrees", default=30.0, min=0.0)
    bpy.types.Scene.triangulate = bpy.props.BoolProperty(name="Triangulate", default=False)
    bpy.types.Scene.edge_split = bpy.props.BoolProperty(name="Edge Split", default=False)
    bpy.types.Scene.join_objects = bpy.props.BoolProperty(name="Join Objects", default=False)

# Register and Unregister Functions (keep them the same)
def register():
    bpy.utils.register_class(SWToolkitPanel)
    bpy.types.Scene.sw_toolkit_mat_to_vert_collapsed = bpy.props.BoolProperty(name="Collapsible Section", default=False)
    bpy.types.Scene.sw_toolkit_split_optimize_collapsed = bpy.props.BoolProperty(name="Collapsible Section", default=False)
    add_scene_properties()

def unregister():
    bpy.utils.unregister_class(SWToolkitPanel)
    del bpy.types.Scene.sw_toolkit_mat_to_vert_collapsed
    del bpy.types.Scene.sw_toolkit_split_optimize_collapsed
    remove_scene_properties()

def remove_scene_properties():
    del bpy.types.Scene.merge_by_distance
    del bpy.types.Scene.merge_distance_threshold
    del bpy.types.Scene.limited_dissolve
    del bpy.types.Scene.limited_dissolve_degrees
    del bpy.types.Scene.triangulate
    del bpy.types.Scene.edge_split
    del bpy.types.Scene.join_objects

if __name__ == "__main__":
    register()
