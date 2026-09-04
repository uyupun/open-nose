"""鼻本体・鼻栓など各パーツを組み合わせ、1つのSceneにまとめる。"""

import trimesh

from .frame_model import FrameParams, build_frame_pair
from .nose_model import NoseParams, build_nose_body
from .plug_model import PlugParams, build_plug_pair


def build_full_scene(frame: FrameParams | None = None) -> trimesh.Scene:
    """鼻本体・鼻栓・フレームを組み合わせたSceneを返す。

    frameを省略するとFrameParamsの既定値を使う。NSGA-IIが見つけた候補
    (scripts/optimize.pyの出力する設計変数の組)を実際の形状として見たい
    場合は、呼び出し側(view_nose.py等)から具体的なFrameParamsを渡す。
    """
    params = NoseParams()
    body = build_nose_body(params)

    plug = PlugParams()
    plug_left, plug_right = build_plug_pair(
        plug, gap=params.nostril_gap, depth_front=params.tip_depth_front
    )

    frame = frame or FrameParams()
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
