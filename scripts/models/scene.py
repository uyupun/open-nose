"""鼻本体・鼻栓など各パーツを組み合わせ、1つのSceneにまとめる。"""

import trimesh

from .frame_model import FrameParams, build_frame_pair
from .nose_model import NoseParams, build_nose_body
from .plug_model import PlugParams, build_plug_pair


def build_full_scene() -> trimesh.Scene:
    params = NoseParams()
    body = build_nose_body(params)

    plug = PlugParams()
    plug_left, plug_right = build_plug_pair(
        plug, gap=params.nostril_gap, depth_front=params.tip_depth_front
    )

    frame = FrameParams()
    frame_left, frame_right = build_frame_pair(frame, plug, params)

    return trimesh.Scene(
        {
            "body": body,
            "plug_left": plug_left,
            "plug_right": plug_right,
            "frame_left": frame_left,
            "frame_right": frame_right,
        }
    )
