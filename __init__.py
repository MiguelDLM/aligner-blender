# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
from .operators import (
    PROCRUSTES_OT_start_landmark,
    PROCRUSTES_OT_submit_landmark,
    PROCRUSTES_OT_cancel_landmark,
    PROCRUSTES_OT_delete_landmark_pair,
    PROCRUSTES_OT_verify_landmarks,
    PROCRUSTES_OT_align_objects,
    PROCRUSTES_OT_clear_landmarks,
)
from .panel import PROCRUSTES_PT_panel
from .preview import preview_toggle_update, cleanup as preview_cleanup


def register():
    bpy.utils.register_class(PROCRUSTES_OT_start_landmark)
    bpy.utils.register_class(PROCRUSTES_OT_submit_landmark)
    bpy.utils.register_class(PROCRUSTES_OT_cancel_landmark)
    bpy.utils.register_class(PROCRUSTES_OT_delete_landmark_pair)
    bpy.utils.register_class(PROCRUSTES_OT_verify_landmarks)
    bpy.utils.register_class(PROCRUSTES_OT_align_objects)
    bpy.utils.register_class(PROCRUSTES_OT_clear_landmarks)
    bpy.utils.register_class(PROCRUSTES_PT_panel)

    bpy.types.Scene.procrustes_original_object = bpy.props.PointerProperty(
        name="Original Object",
        description="The reference mesh object (stays fixed during alignment)",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH',
    )

    bpy.types.Scene.procrustes_target_object = bpy.props.PointerProperty(
        name="Target Object",
        description="The mesh object that will be aligned to the Original",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH',
    )

    bpy.types.Scene.procrustes_landmark_state = bpy.props.EnumProperty(
        name="Landmark State",
        items=[
            ('IDLE', "Idle", ""),
            ('SELECTING_ORIGINAL', "Selecting Original", ""),
            ('SELECTING_TARGET', "Selecting Target", ""),
        ],
        default='IDLE',
    )

    bpy.types.Scene.procrustes_pending_landmark_name = bpy.props.StringProperty(
        name="Pending Landmark Name",
        description="Internal: name of the landmark pair currently being created",
        default="",
    )

    bpy.types.Scene.procrustes_landmark_name = bpy.props.StringProperty(
        name="Landmark Name",
        description="Name for the next landmark pair",
        default="landmark_1",
    )

    bpy.types.Scene.procrustes_method = bpy.props.EnumProperty(
        name="Method",
        description="Alignment method",
        items=[
            ('PROCRUSTES', "Procrustes (rigid)",
             "Rigid alignment: rotation, translation and one global scale. "
             "Landmarks are matched in a least-squares sense (best compromise)"),
            ('TPS', "Thin-Plate Spline (warp)",
             "Non-rigid warp: deforms the target mesh so each landmark lands "
             "exactly on its match, with smooth deformation in between"),
        ],
        default='PROCRUSTES',
    )

    bpy.types.Scene.procrustes_tps_smoothing = bpy.props.FloatProperty(
        name="TPS Smoothing",
        description="Regularization for TPS. 0 = exact match; higher values "
                    "relax the fit so noisy/mis-clicked landmarks are not "
                    "matched exactly",
        default=0.0,
        min=0.0,
        soft_max=10.0,
    )

    bpy.types.Scene.procrustes_allow_scale = bpy.props.BoolProperty(
        name="Allow Scale",
        description="Allow scaling during Procrustes alignment",
        default=True,
    )

    bpy.types.Scene.procrustes_allow_reflection = bpy.props.BoolProperty(
        name="Allow Reflection",
        description="Allow reflection during Procrustes alignment",
        default=False,
    )

    bpy.types.Scene.procrustes_preview_active = bpy.props.BoolProperty(
        name="Preview Active",
        description="Display landmark preview overlay in the 3D View",
        default=False,
        update=preview_toggle_update,
    )


def unregister():
    bpy.utils.unregister_class(PROCRUSTES_OT_start_landmark)
    bpy.utils.unregister_class(PROCRUSTES_OT_submit_landmark)
    bpy.utils.unregister_class(PROCRUSTES_OT_cancel_landmark)
    bpy.utils.unregister_class(PROCRUSTES_OT_delete_landmark_pair)
    bpy.utils.unregister_class(PROCRUSTES_OT_verify_landmarks)
    bpy.utils.unregister_class(PROCRUSTES_OT_align_objects)
    bpy.utils.unregister_class(PROCRUSTES_OT_clear_landmarks)
    bpy.utils.unregister_class(PROCRUSTES_PT_panel)

    del bpy.types.Scene.procrustes_original_object
    del bpy.types.Scene.procrustes_target_object
    del bpy.types.Scene.procrustes_landmark_state
    del bpy.types.Scene.procrustes_pending_landmark_name
    del bpy.types.Scene.procrustes_landmark_name
    del bpy.types.Scene.procrustes_method
    del bpy.types.Scene.procrustes_tps_smoothing
    del bpy.types.Scene.procrustes_allow_scale
    del bpy.types.Scene.procrustes_allow_reflection

    preview_cleanup()
    del bpy.types.Scene.procrustes_preview_active
