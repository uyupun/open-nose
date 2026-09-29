"""水引型設計: 鼻本体・鼻栓・器具を組み合わせ、1つのSceneにまとめる。"""

import trimesh

from commons.nose_model import NoseParams, build_nose_body
from commons.plug_model import build_plug_pair
from mizuhiki.frame_model import MizuhikiParams, build_piece, plug_params


def build_full_scene(frame: MizuhikiParams | None = None) -> trimesh.Scene:
    """鼻本体・鼻栓・左右の器具を組み合わせたSceneを返す。

    鼻栓は、外側の端を輪の下端にそろえて置く(frame_model.plug_params)。
    器具は"frame_mizuhiki_left"・"frame_mizuhiki_right"として登録する
    (commons.viewer.DRAW_ORDER_PREFIXESの"frame"に一致させる)。
    """
    frame = frame or MizuhikiParams()
    params = NoseParams()
    body = build_nose_body(params)
    plug_left, plug_right = build_plug_pair(
        plug_params(frame, params), gap=params.nostril_gap, depth_front=params.tip_depth_front
    )
    return trimesh.Scene(
        {
            "frame_mizuhiki_left": build_piece(frame, params, -1, body),
            "frame_mizuhiki_right": build_piece(frame, params, 1, body),
            "plug_left": plug_left,
            "plug_right": plug_right,
            "body": body,
        }
    )
