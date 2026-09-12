"""拡張ブリッジ型設計: 鼻本体・鼻栓・フレームを組み合わせ、1つのSceneにまとめる。"""

import trimesh

from commons.nose_model import NoseParams, build_nose_body
from commons.plug_model import PlugParams, build_plug_pair
from dilator.frame_model import FrameParams, build_frame


def build_full_scene(frame: FrameParams | None = None) -> trimesh.Scene:
    """鼻本体・鼻栓・フレームを組み合わせたSceneを返す。

    frameを省略するとFrameParamsの既定値を使う。earrings/spiralと異なり
    フレームは左右一体の単一メッシュ(dilator.frame_model.build_frame
    参照)なので、Sceneには"frame"の1キーだけを登録する
    (commons.viewer.DRAW_ORDER_PREFIXESの"frame"プレフィックスに一致する)。
    """
    params = NoseParams()
    body = build_nose_body(params)

    plug = PlugParams()
    plug_left, plug_right = build_plug_pair(
        plug, gap=params.nostril_gap, depth_front=params.tip_depth_front
    )

    frame = frame or FrameParams()
    frame_mesh = build_frame(frame, plug, params)

    return trimesh.Scene(
        {
            "frame": frame_mesh,
            "plug_left": plug_left,
            "plug_right": plug_right,
            "body": body,
        }
    )
