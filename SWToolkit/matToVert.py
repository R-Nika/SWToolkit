import bpy

class SimpleOperator(bpy.types.Operator):
    bl_idname = "object.mat_to_vert"  # Operator ID
    bl_label = "Material to Vertex"   # Label for the button

    def execute(self, context):
        print("Converting material to vertex groups...")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(SimpleOperator)

def unregister():
    bpy.utils.unregister_class(SimpleOperator)
