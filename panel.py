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

        # ── Object Selectors ──────────────────────────────────
        box = layout.box()
        box.label(text="Objects", icon='OBJECT_DATA')
        box.prop(scene, "procrustes_original_object", text="Original")
        box.prop(scene, "procrustes_target_object", text="Target")

        original = scene.procrustes_original_object
        target = scene.procrustes_target_object
        both_set = (
            original is not None and original.type == 'MESH' and
            target is not None and target.type == 'MESH' and
            original != target
        )

        layout.separator()

        # ── Landmark Creation ─────────────────────────────────
        box = layout.box()
        box.label(text="Landmark Creation", icon='SHADERFX')

        state = scene.procrustes_landmark_state

        if not both_set:
            box.label(text="Set Original and Target objects above", icon='INFO')

        elif state == 'IDLE':
            box.prop(scene, "procrustes_landmark_name", text="Name")
            box.operator("procrustes.start_landmark", text="Select Landmark", icon='VERTEXSEL')

        elif state == 'SELECTING_ORIGINAL':
            col = box.column(align=True)
            col.label(text="Step 1: Select vertex on Original", icon='INFO')
            col.label(text=f"  Object: {original.name}", icon='BLANK1')

            box.prop(scene, "procrustes_landmark_name", text="Name")

            has_sel = False
            if original.mode == 'EDIT':
                try:
                    import bmesh
                    bm = bmesh.from_edit_mesh(original.data)
                    has_sel = any(v.select for v in bm.verts)
                except Exception:
                    pass

            row = box.row()
            row.operator("procrustes.submit_landmark", text="Submit Landmark", icon='CHECKMARK')
            row.enabled = has_sel

            box.operator("procrustes.cancel_landmark", text="Cancel", icon='X')

        elif state == 'SELECTING_TARGET':
            col = box.column(align=True)
            col.label(text="Step 2: Select vertex on Target", icon='INFO')
            col.label(text=f"  Object: {target.name}", icon='BLANK1')
            col.label(text=f"  Landmark: {scene.procrustes_pending_landmark_name}", icon='BLANK1')

            has_sel = False
            if target.mode == 'EDIT':
                try:
                    import bmesh
                    bm = bmesh.from_edit_mesh(target.data)
                    has_sel = any(v.select for v in bm.verts)
                except Exception:
                    pass

            row = box.row()
            row.operator("procrustes.submit_landmark", text="Submit Landmark", icon='CHECKMARK')
            row.enabled = has_sel

            box.operator("procrustes.cancel_landmark", text="Cancel", icon='X')

        # ── Landmark Pairs List ───────────────────────────────
        if both_set:
            orig_lms = {k for k in original.keys() if str(k).startswith("landmark_")}
            tgt_lms = {k for k in target.keys() if str(k).startswith("landmark_")}
            all_lms = sorted(orig_lms | tgt_lms)

            if all_lms:
                box.separator()
                box.label(text="Landmark Pairs:", icon='PRESET')
                for lm in all_lms:
                    orig_vi = original.get(lm)
                    tgt_vi = target.get(lm)
                    orig_str = f"v{orig_vi}" if orig_vi is not None else "—"
                    tgt_str = f"v{tgt_vi}" if tgt_vi is not None else "—"
                    row = box.row(align=True)
                    row.label(text=f"{lm}:  {orig_str} → {tgt_str}")
                    op = row.operator("procrustes.delete_landmark_pair", text="", icon='X')
                    op.landmark_name = lm

        layout.separator()

        # ── Alignment Options ─────────────────────────────────
        box = layout.box()
        box.label(text="Alignment Options", icon='ORIENTATION_GIMBAL')

        box.prop(scene, "procrustes_method", text="Method")

        if scene.procrustes_method == 'PROCRUSTES':
            box.prop(scene, "procrustes_allow_scale", text="Allow Scaling")
            box.prop(scene, "procrustes_allow_reflection", text="Allow Reflection")
        else:  # TPS
            box.prop(scene, "procrustes_tps_smoothing", text="Smoothing")
            box.label(text="Deforms the target mesh geometry", icon='MODIFIER')

        layout.separator()

        # ── Execute Alignment ─────────────────────────────────
        box = layout.box()
        box.label(text="Execute Alignment", icon='ARMATURE_DATA')

        shared_count = 0
        if both_set:
            orig_lms = {k for k in original.keys() if str(k).startswith("landmark_")}
            tgt_lms = {k for k in target.keys() if str(k).startswith("landmark_")}
            shared_count = len(orig_lms & tgt_lms)

        box.label(text=f"Shared landmark pairs: {shared_count}")

        min_pairs = 4 if scene.procrustes_method == 'TPS' else 3

        row = box.row()
        row.operator("procrustes.verify_landmarks", text="Verify Landmarks", icon='VIEWZOOM')
        row.enabled = both_set

        row = box.row()
        row.operator("procrustes.align_objects", text="Align Target to Original", icon='TRACKING')
        row.enabled = both_set and shared_count >= min_pairs

        layout.separator()

        # ── Utilities ────────────────────────────────────────
        box = layout.box()
        box.label(text="Utilities", icon='PREFERENCES')

        row = box.row()
        row.operator("procrustes.clear_landmarks", text="Clear All Landmarks", icon='TRASH')
        row.enabled = both_set

        row = box.row()
        icon = 'HIDE_OFF' if scene.procrustes_preview_active else 'HIDE_ON'
        row.prop(scene, "procrustes_preview_active", text="Landmark Preview", toggle=True, icon=icon)
