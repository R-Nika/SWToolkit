import bpy
import bmesh

def rgb_to_hex(color):
    """Convert 3-tuple RGB (0..1) to hex string."""
    return "#{:02X}{:02X}{:02X}".format(
        int(color[0] * 255),
        int(color[1] * 255),
        int(color[2] * 255)
    )


import bpy
import bmesh
import math

def rgb_to_hex(color):
    return ''.join(f'{int(c*255):02X}' for c in color)

class OBJECT_OT_separate_by_vertex_color(bpy.types.Operator):
    bl_idname = "object.separate_by_vertex_color"
    bl_label = "Separate by Vertex Color"
    bl_description = "Separate mesh into multiple objects based on vertex colors"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Ensure we're in Object Mode
        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}

        color_attr = obj.data.color_attributes.get("Col")
        if not color_attr:
            self.report({'ERROR'}, "Vertex color attribute 'Col' not found")
            return {'CANCELLED'}

        bm = bmesh.new()
        bm.from_mesh(obj.data)

        loop_layer = None
        if color_attr.domain == 'CORNER':
            loop_layer = bm.loops.layers.color.get("Col")
            if not loop_layer:
                self.report({'ERROR'}, "Loop color layer 'Col' not found in BMesh")
                return {'CANCELLED'}

        def get_loop_color(loop):
            if color_attr.domain == 'CORNER':
                return loop[loop_layer][:3]
            else:
                idx = loop.vert.index
                return color_attr.data[idx].color[:3]

        # Group faces by average color AND their original material indices
        color_faces = {}
        for face in bm.faces:
            colors = [get_loop_color(loop) for loop in face.loops]
            avg_color = tuple(round(sum(c[i] for c in colors) / len(colors), 3) for i in range(3))
            
            # Store both the faces and their original material indices
            if avg_color not in color_faces:
                color_faces[avg_color] = {'faces': [], 'material_indices': []}
            color_faces[avg_color]['faces'].append(face)
            color_faces[avg_color]['material_indices'].append(face.material_index)

        created_objects = []

        # Check if original object has materials
        original_has_materials = len(obj.data.materials) > 0

        transfer_warning_shown = False  

        # Create new objects per color
        for color, data in color_faces.items():
            faces = data['faces']
            material_indices = data['material_indices']
            
            hex_color = rgb_to_hex(color)
            name_rgb = f"{int(color[0]*255)},{int(color[1]*255)},{int(color[2]*255)}"
            obj_name = f"{obj.name} | {hex_color} | {name_rgb}"

            new_mesh = bpy.data.meshes.new(obj_name)
            new_obj = bpy.data.objects.new(new_mesh.name, new_mesh)
            context.collection.objects.link(new_obj)
            created_objects.append(new_obj)
            new_obj.matrix_world = obj.matrix_world.copy()

            bm_new = bmesh.new()
            vert_map = {}  # Maps original BMesh verts to new BMesh verts
            loop_colors = []
            new_face_material_indices = []  # Store material index for each new face

            for i, face in enumerate(faces):
                verts = []
                face_colors = []
                for loop in face.loops:
                    v = loop.vert
                    if v not in vert_map:
                        vert_map[v] = bm_new.verts.new(v.co)
                    verts.append(vert_map[v])
                    face_colors.append(get_loop_color(loop))
                try:
                    new_face = bm_new.faces.new(verts)
                    # Store the material index for this new face
                    new_face_material_indices.append(material_indices[i])
                except ValueError:
                    pass
                loop_colors.extend([(*c, 1.0) for c in face_colors])

            bm_new.to_mesh(new_mesh)
            bm_new.free()

            # Use the selected domain for the new color attribute
            selected_domain = context.scene.vertex_color_domain
            new_color_attr = new_mesh.color_attributes.new(name="Col", type='FLOAT_COLOR', domain=selected_domain)
            
            if selected_domain == 'CORNER':
                # Set colors for each loop (corner domain)
                for i, col in enumerate(loop_colors):
                    new_color_attr.data[i].color = col
            else:
                # Set colors for each vertex (point domain)
                # Create a mapping from original vertices to their colors
                vert_colors = {}
                vert_color_counts = {}
                
                # Collect all colors for each original vertex
                for face in faces:
                    for loop in face.loops:
                        orig_vert = loop.vert
                        color = get_loop_color(loop)
                        if orig_vert not in vert_colors:
                            vert_colors[orig_vert] = [0, 0, 0]
                            vert_color_counts[orig_vert] = 0
                        vert_colors[orig_vert][0] += color[0]
                        vert_colors[orig_vert][1] += color[1]
                        vert_colors[orig_vert][2] += color[2]
                        vert_color_counts[orig_vert] += 1
                
                # Average the colors for each original vertex and assign to new mesh vertices
                bm_temp = bmesh.new()
                bm_temp.from_mesh(new_mesh)
                
                # Create a mapping from position to original vertex
                position_to_color = {}
                for orig_vert, color_sum in vert_colors.items():
                    count = vert_color_counts[orig_vert]
                    avg_color = (
                        color_sum[0] / count,
                        color_sum[1] / count,
                        color_sum[2] / count,
                        1.0
                    )
                    # Use rounded position as key to avoid floating point precision issues
                    pos_key = tuple(round(coord, 6) for coord in orig_vert.co)
                    position_to_color[pos_key] = avg_color
                
                # Assign colors to new mesh vertices based on position
                for i, vert in enumerate(bm_temp.verts):
                    pos_key = tuple(round(coord, 6) for coord in vert.co)
                    if pos_key in position_to_color:
                        new_color_attr.data[i].color = position_to_color[pos_key]
                    else:
                        # Fallback: use default color
                        new_color_attr.data[i].color = (1.0, 1.0, 1.0, 1.0)
                
                bm_temp.free()

            # MATERIAL HANDLING: Based on transfer_materials and link_materials settings
            if original_has_materials and context.scene.transfer_materials:
                # Get unique material indices used by this specific object's faces
                used_material_indices = set(new_face_material_indices)
                
                if context.scene.link_materials:
                    # LINK MATERIALS: Share material references, but only add used materials
                    material_mapping = {}  # Map original index to new index
                    
                    for orig_index in used_material_indices:
                        if orig_index < len(obj.data.materials):
                            mat = obj.data.materials[orig_index]
                            new_obj.data.materials.append(mat)
                            material_mapping[orig_index] = len(new_obj.data.materials) - 1
                    
                    # Assign the correct material indices to each face
                    for poly_index, material_index in enumerate(new_face_material_indices):
                        if (poly_index < len(new_mesh.polygons) and 
                            material_index in material_mapping):
                            new_mesh.polygons[poly_index].material_index = material_mapping[material_index]
                
                else:
                    # DON'T LINK MATERIALS: Create new material copies, only for used materials
                    material_mapping = {}  # Map original material indices to new material indices
                    
                    for orig_index in used_material_indices:
                        if orig_index < len(obj.data.materials):
                            original_mat = obj.data.materials[orig_index]
                            # Create a copy of the material with a new name
                            new_mat = original_mat.copy()
                            new_mat.name = f"{original_mat.name} | {hex_color}"
                            new_obj.data.materials.append(new_mat)
                            material_mapping[orig_index] = len(new_obj.data.materials) - 1
                    
                    # Assign the new material index to the face
                    for poly_index, material_index in enumerate(new_face_material_indices):
                        if (poly_index < len(new_mesh.polygons) and 
                            material_index in material_mapping):
                            new_mesh.polygons[poly_index].material_index = material_mapping[material_index]

            elif context.scene.transfer_materials and not original_has_materials and not transfer_warning_shown:
                self.report({'WARNING'}, "Transfer Materials enabled but original model has no materials")
                transfer_warning_shown = True

            # If transfer_materials is FALSE: No materials on separated objects
            # Do nothing - object will have no materials

        # Hide original
        obj.hide_set(True)
        obj.hide_render = True

        # --- Processing order ---
        for new_obj in created_objects:
            bpy.context.view_layer.objects.active = new_obj
            new_obj.select_set(True)

            # --- Merge by Distance ---
            if context.scene.merge_by_distance_after_separate:
                bm_merge = bmesh.new()
                bm_merge.from_mesh(new_obj.data)
                bmesh.ops.remove_doubles(bm_merge, verts=bm_merge.verts, dist=0.0001)
                bm_merge.to_mesh(new_obj.data)
                new_obj.data.update()
                bm_merge.free()

            # --- Limited Dissolve ---
            if context.scene.limited_dissolve_after_separate:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.dissolve_limited(angle_limit=math.radians(5.0))  # 5 degrees default
                bpy.ops.object.mode_set(mode='OBJECT')

        # --- Join objects ---
        if context.scene.join_after_separate and created_objects:
            bpy.ops.object.select_all(action='DESELECT')
            for o in created_objects:
                o.select_set(True)
            bpy.context.view_layer.objects.active = created_objects[0]
            bpy.ops.object.join()
            combined_obj = context.active_object
            combined_obj.name = f"{obj.name} | Combined"
            created_objects = [combined_obj]

        # --- Triangulate ---
        if context.scene.triangulate_after_separate:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.quads_convert_to_tris()
            bpy.ops.object.mode_set(mode='OBJECT')

        # --- Edge Split ---
        if context.scene.edgesplit_after_separate:
            bm_split = bmesh.new()
            bm_split.from_mesh(created_objects[0].data)
            edges_to_split = [e for e in bm_split.edges if len(e.link_faces) > 1]
            if edges_to_split:
                bmesh.ops.split_edges(bm_split, edges=edges_to_split)
                bm_split.to_mesh(created_objects[0].data)
            bm_split.free()

        bm.free()
        self.report({'INFO'}, f"Separated mesh into {len(created_objects)} object(s) by vertex color.")
        return {'FINISHED'}

class VIEW3D_PT_separate_by_vertex_color_panel(bpy.types.Panel):
    bl_label = "Separate by Vertex Color"
    bl_idname = "VIEW3D_PT_separate_by_vertex_color"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SW Toolkit'

    def draw(self, context):
        layout = self.layout
        
        # Main outer box
        outer_box = layout.box()
        
        # Operator button inside inner box
        inner_box = outer_box.box()
        inner_box.operator(
            OBJECT_OT_separate_by_vertex_color.bl_idname,
            text="Separate by Vertex Color",
            icon="MESH_CUBE"
        )

        # Settings collapsible area INSIDE the outer box
        settings_box = outer_box.box()
        row = settings_box.row()
        icon = "TRIA_DOWN" if context.scene.show_separate_settings else "TRIA_RIGHT"
        row.prop(context.scene, "show_separate_settings", text="", icon=icon, emboss=False)
        row.label(text="Settings")

        if context.scene.show_separate_settings:
            # Box for Domain settings
            domain_box = settings_box.box()
            header_row = domain_box.row()
            header_row.alignment = 'CENTER'
            header_row.label(text="Color Settings")
            domain_box.prop(context.scene, "vertex_color_domain", text="Domain")
            domain_box.prop(context.scene, "transfer_materials", text="Transfer Materials")
            
            # Show Link Materials only if Transfer Materials is enabled
            if context.scene.transfer_materials:
                domain_box.prop(context.scene, "link_materials", text="Link Materials")
            
            # Box for Geometry processing settings
            geometry_box = settings_box.box()
            header_row = geometry_box.row()
            header_row.alignment = 'CENTER'
            header_row.label(text="Geometry Processing")
            geometry_box.prop(context.scene, "join_after_separate", text="Join Resulting Objects")
            geometry_box.prop(context.scene, "triangulate_after_separate", text="Triangulate")
            geometry_box.prop(context.scene, "edgesplit_after_separate", text="Edge Split")
            geometry_box.prop(context.scene, "merge_by_distance_after_separate", text="Merge by Distance")
            geometry_box.prop(context.scene, "limited_dissolve_after_separate", text="Limited Dissolve")


# Registration
classes = (
    OBJECT_OT_separate_by_vertex_color,
    VIEW3D_PT_separate_by_vertex_color_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.vertex_color_domain = bpy.props.EnumProperty(
        name="Domain",
        description="Vertex color domain to use for separation",
        items=[
            ('CORNER', "Corner", "Use corner domain (per-face vertex colors)"),
            ('POINT', "Point", "Use point domain (per-vertex colors)")
        ],
        default='CORNER'
    )
    bpy.types.Scene.transfer_materials = bpy.props.BoolProperty(
        name="Transfer Materials",
        description="Copy materials from original to separated objects",
        default=False
    )
    bpy.types.Scene.link_materials = bpy.props.BoolProperty(
        name="Link Materials",
        description="Share materials between original and separated objects",
        default=True
    )
    bpy.types.Scene.join_after_separate = bpy.props.BoolProperty(
        name="Join Resulting Objects",
        description="Join all separated objects into one after splitting",
        default=False
    )
    bpy.types.Scene.triangulate_after_separate = bpy.props.BoolProperty(
        name="Triangulate",
        description="Triangulate resulting meshes after separation",
        default=False
    )
    bpy.types.Scene.edgesplit_after_separate = bpy.props.BoolProperty(
        name="Edge Split",
        description="Split faces by edges shared by multiple faces",
        default=False
    )
    bpy.types.Scene.merge_by_distance_after_separate = bpy.props.BoolProperty(
        name="Merge by Distance",
        description="Merge overlapping vertices after separation",
        default=False
    )
    bpy.types.Scene.limited_dissolve_after_separate = bpy.props.BoolProperty(
        name="Limited Dissolve",
        description="Perform limited dissolve on resulting meshes",
        default=False
    )
    bpy.types.Scene.show_separate_settings = bpy.props.BoolProperty(
        name="Show Tool Settings",
        description="Expand or collapse settings for separation",
        default=False
    )


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.vertex_color_domain
    del bpy.types.Scene.transfer_materials
    del bpy.types.Scene.link_materials
    del bpy.types.Scene.join_after_separate
    del bpy.types.Scene.triangulate_after_separate
    del bpy.types.Scene.edgesplit_after_separate
    del bpy.types.Scene.merge_by_distance_after_separate
    del bpy.types.Scene.limited_dissolve_after_separate
    del bpy.types.Scene.show_separate_settings


if __name__ == "__main__":
    register()