import bpy
import bmesh
from mathutils import Vector, Matrix
import numpy as np


class PROCRUSTES_OT_select_landmark(bpy.types.Operator):
    """Enter Edit Mode to select a vertex as landmark"""
    bl_idname = "procrustes.select_landmark"
    bl_label = "Select Landmark Vertex"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Please select a mesh object")
            return {'CANCELLED'}
        
        # Enter edit mode with vertex selection
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(type='VERT')
        
        self.report({'INFO'}, "Select a vertex and press Submit Landmark")
        return {'FINISHED'}


class PROCRUSTES_OT_submit_landmark(bpy.types.Operator):
    """Submit the selected vertex as a landmark"""
    bl_idname = "procrustes.submit_landmark"
    bl_label = "Submit Landmark"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        scene = context.scene
        
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}
        # Prefer reading selection from BMesh when in Edit Mode (reliable)
        mesh = obj.data
        selected_verts = []
        try:
            if obj.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(mesh)
                selected_verts = [v for v in bm.verts if v.select]
            else:
                # Fallback to object-mode vertex select flags
                selected_verts = [v for v in mesh.vertices if v.select]
        except Exception:
            # Generic fallback
            selected_verts = [v for v in mesh.vertices if v.select]

        if len(selected_verts) == 0:
            self.report({'ERROR'}, "No vertex selected (enter Edit Mode and select a vertex)")
            return {'CANCELLED'}

        if len(selected_verts) > 1:
            self.report({'WARNING'}, "Multiple vertices selected. Using the first one.")

        # Get the vertex coordinates in world space
        vert = selected_verts[0]
        # If it's a BMesh vert it has .co; mesh.vertex also has .co
        world_coord = obj.matrix_world @ vert.co
        
        # Store as custom property
        # Create a unique landmark name if needed
        landmark_name = scene.procrustes_landmark_name or "landmark"
        base_name = landmark_name
        # If property already exists on object, append numeric suffix
        counter = 1
        unique_name = base_name
        while unique_name in obj.keys():
            unique_name = f"{base_name}_{counter}"
            counter += 1

        obj[unique_name] = [world_coord.x, world_coord.y, world_coord.z]

        landmark_name = unique_name
        
        self.report({'INFO'}, f"Landmark '{landmark_name}' created at {world_coord}")
        
        # Keep the user's mode unchanged (we didn't change modes)
        # Optionally update the scene's landmark name base to suggest the next name
        scene.procrustes_landmark_name = f"{base_name}"
        
        return {'FINISHED'}


class PROCRUSTES_OT_delete_landmark(bpy.types.Operator):
    """Delete a landmark from the active object"""
    bl_idname = "procrustes.delete_landmark"
    bl_label = "Delete Landmark"
    bl_options = {'REGISTER', 'UNDO'}
    
    landmark_name: bpy.props.StringProperty()
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj:
            return {'CANCELLED'}
        
        if self.landmark_name in obj.keys():
            del obj[self.landmark_name]
            self.report({'INFO'}, f"Deleted landmark '{self.landmark_name}'")
        
        return {'FINISHED'}


class PROCRUSTES_OT_clear_landmarks(bpy.types.Operator):
    """Clear all landmarks from the active object"""
    bl_idname = "procrustes.clear_landmarks"
    bl_label = "Clear All Landmarks"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj:
            self.report({'ERROR'}, "No object selected")
            return {'CANCELLED'}
        
        landmarks = [key for key in obj.keys() if key.startswith("landmark_")]
        
        for lm in landmarks:
            del obj[lm]
        
        self.report({'INFO'}, f"Cleared {len(landmarks)} landmarks")
        return {'FINISHED'}


class PROCRUSTES_OT_align_objects(bpy.types.Operator):
    """Align selected objects using Procrustes analysis"""
    bl_idname = "procrustes.align_objects"
    bl_label = "Align Objects with Procrustes"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from .procrustes_utils import procrustes_alignment
        
        scene = context.scene
        selected_objects = [o for o in context.selected_objects if o.type == 'MESH']
        
        if len(selected_objects) < 2:
            self.report({'ERROR'}, "Select at least 2 mesh objects with landmarks")
            return {'CANCELLED'}
        
        # Extract landmarks from all objects
        objects_landmarks = {}
        
        for obj in selected_objects:
            landmarks = {}
            for key in obj.keys():
                if key.startswith("landmark_"):
                    landmarks[key] = Vector(obj[key])
            
            if len(landmarks) == 0:
                self.report({'ERROR'}, f"Object '{obj.name}' has no landmarks")
                return {'CANCELLED'}
            
            objects_landmarks[obj.name] = {
                'object': obj,
                'landmarks': landmarks
            }
        
        # Check that all objects have the same landmarks
        landmark_names = None
        for obj_name, data in objects_landmarks.items():
            if landmark_names is None:
                landmark_names = set(data['landmarks'].keys())
            else:
                if set(data['landmarks'].keys()) != landmark_names:
                    self.report({'ERROR'}, 
                               f"All objects must have the same landmark names. "
                               f"Check object '{obj_name}'")
                    return {'CANCELLED'}
        
        if len(landmark_names) < 3:
            self.report({'ERROR'}, "Need at least 3 landmarks for alignment")
            return {'CANCELLED'}
        
        # Determine reference: either a chosen object or midpoint
        ref_obj = getattr(scene, 'procrustes_reference_object', None)
        reference_landmarks = None
        reference_obj_name = None

        if ref_obj and ref_obj.name in objects_landmarks:
            reference_obj_name = ref_obj.name
            reference_landmarks = objects_landmarks[reference_obj_name]['landmarks']
            self.report({'INFO'}, f"Using '{reference_obj_name}' as reference (will remain fixed)")
        else:
            # If no reference object chosen or it's not in selection, use mean of points
            self.report({'INFO'}, "No reference object chosen or not in selection — using mean shape as reference")
            # Build mean points across objects
            landmark_names_sorted = sorted(list(landmark_names))
            mean_points = []
            for lm_name in landmark_names_sorted:
                pts = []
                for obj_name, data in objects_landmarks.items():
                    pts.append(np.array(list(data['landmarks'][lm_name])))
                mean = np.mean(np.vstack(pts), axis=0)
                mean_points.append(mean)
            reference_landmarks = {lm: Vector(pt) for lm, pt in zip(landmark_names_sorted, mean_points)}
            # For the mean-based reference we won't skip any objects; all will be transformed

        # Align each other object to the reference (or to mean reference)
        for obj_name, data in objects_landmarks.items():
            # If there is a chosen reference object, keep it fixed
            if reference_obj_name is not None and obj_name == reference_obj_name:
                continue
            
            obj = data['object']
            target_landmarks = data['landmarks']
            
            # Prepare landmark arrays in the same order
            ref_points = []
            tgt_points = []
            
            for lm_name in sorted(landmark_names):
                ref_points.append(reference_landmarks[lm_name])
                tgt_points.append(target_landmarks[lm_name])
            
            # Calculate Procrustes transformation
            success, transform_matrix, scale = procrustes_alignment(
                np.array([list(p) for p in ref_points]),
                np.array([list(p) for p in tgt_points]),
                allow_scale=scene.procrustes_allow_scale,
                allow_reflection=scene.procrustes_allow_reflection
            )
            
            if not success:
                self.report({'ERROR'}, f"Failed to align '{obj_name}'")
                continue
            
            # Convert numpy matrix to Blender Matrix
            blender_matrix = Matrix(transform_matrix.tolist())
            
            # Apply transformation to object
            obj.matrix_world = blender_matrix @ obj.matrix_world
            
            self.report({'INFO'}, 
                       f"Aligned '{obj_name}' to reference (scale: {scale:.3f})")
        
        return {'FINISHED'}
