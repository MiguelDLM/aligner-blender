import bpy
import bmesh
import re
from mathutils import Vector, Matrix
import numpy as np


def get_vertex_world_coord(obj, vert_index):
    if obj.type != 'MESH':
        return None
    mesh = obj.data
    if vert_index < 0 or vert_index >= len(mesh.vertices):
        return None
    return obj.matrix_world @ mesh.vertices[vert_index].co


class PROCRUSTES_OT_start_landmark(bpy.types.Operator):
    """Enter Edit Mode on the Original object to select a landmark vertex"""
    bl_idname = "procrustes.start_landmark"
    bl_label = "Select Landmark"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        original = scene.procrustes_original_object
        target = scene.procrustes_target_object

        if not original or original.type != 'MESH':
            self.report({'ERROR'}, "Set a valid Original mesh object first")
            return {'CANCELLED'}
        if not target or target.type != 'MESH':
            self.report({'ERROR'}, "Set a valid Target mesh object first")
            return {'CANCELLED'}
        if original == target:
            self.report({'ERROR'}, "Original and Target must be different objects")
            return {'CANCELLED'}

        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        original.select_set(True)
        context.view_layer.objects.active = original
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(type='VERT')

        scene.procrustes_landmark_state = 'SELECTING_ORIGINAL'
        self.report({'INFO'}, "Select a vertex on the Original object, then click Submit Landmark")
        return {'FINISHED'}


class PROCRUSTES_OT_submit_landmark(bpy.types.Operator):
    """Submit the selected vertex as a landmark"""
    bl_idname = "procrustes.submit_landmark"
    bl_label = "Submit Landmark"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        state = scene.procrustes_landmark_state

        if state == 'SELECTING_ORIGINAL':
            return self._submit_original(context, scene)
        elif state == 'SELECTING_TARGET':
            return self._submit_target(context, scene)
        else:
            self.report({'ERROR'}, "Not in landmark selection mode")
            return {'CANCELLED'}

    def _submit_original(self, context, scene):
        original = scene.procrustes_original_object
        target = scene.procrustes_target_object

        if not original or original.type != 'MESH':
            self.report({'ERROR'}, "Original object not set")
            return {'CANCELLED'}
        if original.mode != 'EDIT':
            self.report({'ERROR'}, "Original object must be in Edit Mode")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(original.data)
        selected = [v for v in bm.verts if v.select]

        if not selected:
            self.report({'ERROR'}, "Select a vertex on the Original object first")
            return {'CANCELLED'}
        if len(selected) > 1:
            self.report({'WARNING'}, "Multiple vertices selected; using the first one")

        vert_index = selected[0].index

        # Build unique landmark name
        base_name = scene.procrustes_landmark_name or "landmark_1"
        unique_name = base_name
        counter = 1
        while unique_name in original.keys():
            unique_name = f"{base_name}_{counter}"
            counter += 1

        original[unique_name] = vert_index
        scene.procrustes_pending_landmark_name = unique_name

        # Switch to target in edit mode
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        target.select_set(True)
        context.view_layer.objects.active = target
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(type='VERT')

        scene.procrustes_landmark_state = 'SELECTING_TARGET'
        self.report({'INFO'}, f"Landmark '{unique_name}' saved on Original. Select equivalent vertex on Target.")
        return {'FINISHED'}

    def _submit_target(self, context, scene):
        target = scene.procrustes_target_object
        landmark_name = scene.procrustes_pending_landmark_name

        if not target or target.type != 'MESH':
            self.report({'ERROR'}, "Target object not set")
            return {'CANCELLED'}
        if target.mode != 'EDIT':
            self.report({'ERROR'}, "Target object must be in Edit Mode")
            return {'CANCELLED'}
        if not landmark_name:
            self.report({'ERROR'}, "No pending landmark name")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(target.data)
        selected = [v for v in bm.verts if v.select]

        if not selected:
            self.report({'ERROR'}, "Select a vertex on the Target object first")
            return {'CANCELLED'}
        if len(selected) > 1:
            self.report({'WARNING'}, "Multiple vertices selected; using the first one")

        target[landmark_name] = selected[0].index

        bpy.ops.object.mode_set(mode='OBJECT')

        scene.procrustes_landmark_state = 'IDLE'
        scene.procrustes_pending_landmark_name = ""

        # Auto-increment trailing number in landmark name
        match = re.match(r'^(.*?)(\d+)$', scene.procrustes_landmark_name)
        if match:
            prefix, num = match.group(1), int(match.group(2))
            scene.procrustes_landmark_name = f"{prefix}{num + 1}"

        self.report({'INFO'}, f"Landmark pair '{landmark_name}' created!")
        return {'FINISHED'}


class PROCRUSTES_OT_cancel_landmark(bpy.types.Operator):
    """Cancel the current landmark selection and reset state"""
    bl_idname = "procrustes.cancel_landmark"
    bl_label = "Cancel"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene

        # If cancelled mid-pair, remove the original landmark already saved
        if scene.procrustes_landmark_state == 'SELECTING_TARGET':
            original = scene.procrustes_original_object
            pending = scene.procrustes_pending_landmark_name
            if original and pending and pending in original.keys():
                del original[pending]

        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        scene.procrustes_landmark_state = 'IDLE'
        scene.procrustes_pending_landmark_name = ""
        self.report({'INFO'}, "Landmark selection cancelled")
        return {'FINISHED'}


class PROCRUSTES_OT_delete_landmark_pair(bpy.types.Operator):
    """Delete a landmark pair from both Original and Target objects"""
    bl_idname = "procrustes.delete_landmark_pair"
    bl_label = "Delete Landmark Pair"
    bl_options = {'REGISTER', 'UNDO'}

    landmark_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        original = scene.procrustes_original_object
        target = scene.procrustes_target_object

        for obj in [original, target]:
            if obj and self.landmark_name in obj.keys():
                del obj[self.landmark_name]

        self.report({'INFO'}, f"Deleted landmark pair '{self.landmark_name}'")
        return {'FINISHED'}


class PROCRUSTES_OT_clear_landmarks(bpy.types.Operator):
    """Clear all landmarks from both Original and Target objects"""
    bl_idname = "procrustes.clear_landmarks"
    bl_label = "Clear All Landmark Pairs"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        original = scene.procrustes_original_object
        target = scene.procrustes_target_object

        count = 0
        for obj in [original, target]:
            if obj:
                lms = [k for k in obj.keys() if str(k).startswith("landmark_")]
                for lm in lms:
                    del obj[lm]
                    count += 1

        self.report({'INFO'}, f"Cleared {count} landmarks")
        return {'FINISHED'}


def gather_landmark_pairs(original, target):
    """Collect world coordinates for landmark pairs shared by both objects.

    Returns (names, ref_points, tgt_points) where ref/tgt are Nx3 numpy arrays
    of world coordinates (original = reference, target = source to be moved).
    Pairs with invalid/out-of-range vertex data are skipped.
    """
    orig_lms = {k: original[k] for k in original.keys() if str(k).startswith("landmark_")}
    tgt_lms = {k: target[k] for k in target.keys() if str(k).startswith("landmark_")}
    shared = sorted(set(orig_lms.keys()) & set(tgt_lms.keys()))

    names, ref_points, tgt_points = [], [], []
    for lm_name in shared:
        try:
            orig_coord = get_vertex_world_coord(original, int(orig_lms[lm_name]))
            tgt_coord = get_vertex_world_coord(target, int(tgt_lms[lm_name]))
        except (ValueError, TypeError):
            continue
        if orig_coord is None or tgt_coord is None:
            continue
        names.append(lm_name)
        ref_points.append(list(orig_coord))
        tgt_points.append(list(tgt_coord))

    return names, np.array(ref_points), np.array(tgt_points)


def validate_landmarks(scene):
    """Run a battery of checks on the current landmark configuration.

    Returns (errors, warnings) as lists of human-readable strings. Errors must
    block alignment; warnings are advisory (e.g. a likely mis-clicked vertex).
    """
    from .procrustes_utils import procrustes_alignment

    errors, warnings = [], []
    original = scene.procrustes_original_object
    target = scene.procrustes_target_object

    if not original or original.type != 'MESH':
        errors.append("Original object is not set or is not a mesh")
    if not target or target.type != 'MESH':
        errors.append("Target object is not set or is not a mesh")
    if errors:
        return errors, warnings
    if original == target:
        errors.append("Original and Target are the same object")
        return errors, warnings

    orig_lms = {k: original[k] for k in original.keys() if str(k).startswith("landmark_")}
    tgt_lms = {k: target[k] for k in target.keys() if str(k).startswith("landmark_")}

    # Unpaired landmarks (exist on only one object)
    for k in sorted(set(orig_lms) - set(tgt_lms)):
        warnings.append(f"'{k}' exists only on Original — it will be ignored")
    for k in sorted(set(tgt_lms) - set(orig_lms)):
        warnings.append(f"'{k}' exists only on Target — it will be ignored")

    # Per-object integrity: invalid indices, duplicate vertices (the v0 mis-click)
    for label, obj, lms in (("Original", original, orig_lms), ("Target", target, tgt_lms)):
        n_verts = len(obj.data.vertices)
        seen = {}
        for k in sorted(lms):
            try:
                idx = int(lms[k])
            except (ValueError, TypeError):
                errors.append(f"{label} '{k}' has non-integer data")
                continue
            if idx < 0 or idx >= n_verts:
                errors.append(f"{label} '{k}' points to vertex {idx}, out of range (0..{n_verts - 1})")
                continue
            if idx in seen:
                warnings.append(
                    f"{label}: '{k}' and '{seen[idx]}' use the SAME vertex (v{idx}) — likely a mis-click")
            else:
                seen[idx] = k

    names, ref, tgt = gather_landmark_pairs(original, target)
    n = len(names)

    method = getattr(scene, 'procrustes_method', 'PROCRUSTES')
    min_pairs = 4 if method == 'TPS' else 3
    if n < min_pairs:
        errors.append(f"Need at least {min_pairs} valid landmark pairs for "
                      f"{'TPS' if method == 'TPS' else 'Procrustes'} (found {n})")
        return errors, warnings

    # Degenerate configuration: collinear (and, for TPS, coplanar) landmarks
    centered = ref - ref.mean(axis=0)
    sv = np.linalg.svd(centered, compute_uv=False)
    tol = 1e-6 * (sv[0] if sv[0] > 0 else 1.0)
    rank = int(np.sum(sv > tol))
    if rank < 2:
        errors.append("Landmarks are collinear — cannot determine an orientation")
    elif rank < 3:
        msg = "Landmarks are coplanar (all on one plane)"
        if method == 'TPS':
            errors.append(msg + " — TPS needs non-coplanar landmarks")
        else:
            warnings.append(msg + " — rotation about that plane is ambiguous")

    # Per-pair residual outliers after a rigid fit: flags a wrong vertex pick
    ok, T, _scale = procrustes_alignment(
        ref, tgt,
        allow_scale=getattr(scene, 'procrustes_allow_scale', True),
        allow_reflection=getattr(scene, 'procrustes_allow_reflection', False),
    )
    if ok:
        tgt_h = np.hstack([tgt, np.ones((n, 1))])
        moved = (T @ tgt_h.T).T[:, :3]
        resid = np.sqrt(np.sum((ref - moved) ** 2, axis=1))
        mean, std = resid.mean(), resid.std()
        if std > 1e-9:
            for name, rr in zip(names, resid):
                if rr > mean + 2.0 * std and rr > 2.0 * mean:
                    warnings.append(
                        f"'{name}' has an unusually large residual ({rr:.3f}) — "
                        f"possible wrong/mismatched vertex")

    return errors, warnings


class PROCRUSTES_OT_verify_landmarks(bpy.types.Operator):
    """Check landmark pairs for common mistakes (mis-clicks, bad indices, outliers)"""
    bl_idname = "procrustes.verify_landmarks"
    bl_label = "Verify Landmarks"
    bl_options = {'REGISTER'}

    def execute(self, context):
        errors, warnings = validate_landmarks(context.scene)

        def draw(menu, _ctx):
            layout = menu.layout
            if not errors and not warnings:
                layout.label(text="All landmark pairs look good.", icon='CHECKMARK')
                return
            for e in errors:
                layout.label(text=e, icon='ERROR')
            for w in warnings:
                layout.label(text=w, icon='INFO')

        context.window_manager.popup_menu(draw, title="Landmark Verification", icon='VIEWZOOM')

        if errors:
            self.report({'WARNING'}, f"{len(errors)} error(s), {len(warnings)} warning(s) found")
        elif warnings:
            self.report({'WARNING'}, f"{len(warnings)} warning(s) found")
        else:
            self.report({'INFO'}, "All landmark pairs look good")
        return {'FINISHED'}


class PROCRUSTES_OT_align_objects(bpy.types.Operator):
    """Align Target to Original using the selected method on shared landmark pairs"""
    bl_idname = "procrustes.align_objects"
    bl_label = "Align Target to Original"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        original = scene.procrustes_original_object
        target = scene.procrustes_target_object

        # Block on errors, surface warnings but proceed
        errors, warnings = validate_landmarks(scene)
        for w in warnings:
            self.report({'WARNING'}, w)
        if errors:
            for e in errors:
                self.report({'ERROR'}, e)
            return {'CANCELLED'}

        method = scene.procrustes_method
        if method == 'TPS':
            return self._align_tps(scene, original, target)
        return self._align_procrustes(scene, original, target)

    def _align_procrustes(self, scene, original, target):
        from .procrustes_utils import procrustes_alignment

        _names, ref, tgt = gather_landmark_pairs(original, target)

        success, transform_matrix, scale = procrustes_alignment(
            ref, tgt,
            allow_scale=scene.procrustes_allow_scale,
            allow_reflection=scene.procrustes_allow_reflection,
        )
        if not success:
            self.report({'ERROR'}, "Procrustes alignment failed")
            return {'CANCELLED'}

        target.matrix_world = Matrix(transform_matrix.tolist()) @ target.matrix_world
        self.report({'INFO'}, f"Aligned target to original (Procrustes, scale: {scale:.3f}, {len(ref)} pairs)")
        return {'FINISHED'}

    def _align_tps(self, scene, original, target):
        from .procrustes_utils import tps_fit, tps_apply

        _names, ref, tgt = gather_landmark_pairs(original, target)

        # Fit warp: move target landmarks (source) onto original landmarks (dest)
        success, params = tps_fit(tgt, ref, smoothing=scene.procrustes_tps_smoothing)
        if not success:
            self.report({'ERROR'}, "TPS fit failed (check for duplicate or coplanar landmarks)")
            return {'CANCELLED'}

        mesh = target.data
        n_verts = len(mesh.vertices)
        if n_verts == 0:
            self.report({'ERROR'}, "Target mesh has no vertices")
            return {'CANCELLED'}

        # Read local coords, take to world, warp, bring back to local
        co = np.empty(n_verts * 3, dtype=np.float64)
        mesh.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)

        mw = np.array(target.matrix_world)
        world = co @ mw[:3, :3].T + mw[:3, 3]

        warped = tps_apply(params, tgt, world)

        mwi = np.array(target.matrix_world.inverted())
        new_local = warped @ mwi[:3, :3].T + mwi[:3, 3]

        mesh.vertices.foreach_set('co', new_local.ravel())
        mesh.update()

        self.report({'INFO'},
                    f"Warped target onto original (TPS, {len(ref)} pairs, "
                    f"smoothing: {scene.procrustes_tps_smoothing:.2f}) — mesh geometry modified")
        return {'FINISHED'}
