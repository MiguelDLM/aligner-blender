import bpy


class PROCRUSTES_PT_panel(bpy.types.Panel):
    """Main panel for Procrustes alignment addon"""
    bl_idname = "PROCRUSTES_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Procrustes Aligner"
    bl_category = "Procrustes"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.active_object
        
        # Landmark Selection Section
        box = layout.box()
        box.label(text="Landmark Creation", icon='SHADERFX')
        
        if obj and obj.type == 'MESH':
            row = box.row()
            row.label(text=f"Active Object: {obj.name}", icon='OBJECT_DATA')
            
            row = box.row()
            row.operator("procrustes.select_landmark", text="Select Landmark", icon='VERTEXSEL')
            
            row = box.row()
            row.prop(scene, "procrustes_landmark_name", text="Name")
            
            row = box.row()
            submit = row.operator("procrustes.submit_landmark", text="Submit Landmark", icon='CHECKMARK')
            # Enable if in Edit Mode and there is at least one selected vertex
            is_edit = (obj.mode == 'EDIT')
            has_sel = False
            try:
                if is_edit:
                    # count selected vertices via BMesh
                    import bmesh
                    bm = bmesh.from_edit_mesh(obj.data)
                    has_sel = any(v.select for v in bm.verts)
                else:
                    has_sel = any(v.select for v in obj.data.vertices)
            except Exception:
                has_sel = any(v.select for v in obj.data.vertices)

            row.enabled = is_edit and has_sel
            
            # Display existing landmarks
            if obj:
                landmarks = [key for key in obj.keys() if str(key).startswith("landmark_")]
                if landmarks:
                    box.separator()
                    box.label(text="Existing Landmarks:", icon='PRESET')
                    
                    for lm in sorted(landmarks):
                        try:
                            coords = obj[lm]
                            coords = list(coords)
                            row = box.row(align=True)
                            row.label(text=f"{lm}: ({coords[0]:.3f}, {coords[1]:.3f}, {coords[2]:.3f})")
                            # Delete button for each landmark
                            op = row.operator("procrustes.delete_landmark", text="", icon='X')
                            op.landmark_name = lm
                        except Exception:
                            row = box.row()
                            row.label(text=f"{lm}: <invalid>")
        else:
            row = box.row()
            row.label(text="Select a mesh object", icon='INFO')
        
        layout.separator()
        
        # Alignment Options Section
        box = layout.box()
        box.label(text="Alignment Options", icon='ORIENTATION_GIMBAL')
        
        row = box.row()
        row.prop(scene, "procrustes_allow_scale", text="Allow Scaling")
        
        row = box.row()
        row.prop(scene, "procrustes_allow_reflection", text="Allow Reflection")

        row = box.row()
        row.prop(scene, "procrustes_reference_object", text="Reference Object")

        layout.separator()
        
        # Alignment Execution Section
        box = layout.box()
        box.label(text="Execute Alignment", icon='ARMATURE_DATA')
        
        selected_objects = [o for o in context.selected_objects if o.type == 'MESH']
        row = box.row()
        row.label(text=f"Selected Objects: {len(selected_objects)}")
        
        row = box.row()
        row.operator("procrustes.align_objects", text="Align Objects", icon='TRACKING')
        row.enabled = len(selected_objects) >= 2
        
        layout.separator()
        
        # Utilities Section
        box = layout.box()
        box.label(text="Utilities", icon='PREFERENCES')
        
        row = box.row()
        if obj and obj.type == 'MESH':
            row.operator("procrustes.clear_landmarks", text="Clear All Landmarks", icon='TRASH')
        else:
            row.label(text="Select a mesh to clear landmarks")

        row = box.row()
        icon = 'HIDE_OFF' if scene.procrustes_preview_active else 'HIDE_ON'
        row.prop(scene, "procrustes_preview_active", text="Landmark Preview", toggle=True, icon=icon)
